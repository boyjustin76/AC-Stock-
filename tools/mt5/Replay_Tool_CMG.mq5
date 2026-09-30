//+------------------------------------------------------------------+
//| Replay_Tool (차트명가 판) — 원본: Ahmad Arju, MQL5 CodeBase 76669  |
//|   https://www.mql5.com/en/code/76669  (무료·소스 공개)             |
//| 차트명가가 더한 것: 단축키 Z/X(한 봉) · A/S(열 봉) · 스페이스(재생) |
//| 그 밖의 동작은 원본 그대로다.                                      |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//|                                                  Replay Tool.mq5 |
//|                     Market Replay Tool + Long/Short Drawing Tool |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Ahmad Arju"
#property version   "1.00"
#property link "https://www.mql5.com/en/users/arju0612_/"
#property strict

//====================================================================
// [1] INPUT PENGATURAN REPLAY
//====================================================================
input group "=== REPLAY SETTINGS ==="
input string   InpSourceSymbol       = "XAUUSD";            // Original Source Symbol
input datetime InpStartDate          = D'2026.01.01 00:00'; // Fallback Default Date
input int      InpBaseTimerMS        = 200;                 // Base Play Speed (ms) @ 1x
input int      InpDownloadTimeoutSec = 30;                  // Data Download Timeout (sec)
input int      InpMinVisibleBars     = 50;                  // Minimum Visible Bars
input bool     InpAnchorView         = true;               // 차트명가: 되감을 때 화면을 고정한다 (오른쪽이 그만큼 비어 간다)
input int      InpShiftPercent       = 50;                 // 차트명가: 오른쪽 여백 % (0=끔, 최대 50 → 봉이 화면 가운데서 끝난다)

//====================================================================
// [2] INPUT PENGATURAN DRAWING PANEL
//====================================================================
input group "=== DRAWING SETTINGS ==="
input color InpBgColor      = C'30,30,30';       // Panel Background Color
input color InpBtnColor     = C'50,50,50';       // Normal Button Color
input color InpActiveColor  = C'41,98,255';      // Active Button Color
input color InpTextColor    = clrWhite;          // Button Text Color

//--- State Replay
string   g_customSymbol      = "";
string   g_sourceSymbol      = "";
MqlRates g_allRates[];
int      g_totalBars         = 0;
int      g_currentDisplay    = 0;
bool     g_isPlaying         = false;
bool     g_isCustomMode      = false;
bool     g_anchorView        = true;
bool     g_forceRecenter     = true;   // 차트명가: 처음·점프에서만 여백을 기본값으로 되돌린다
int      g_blankBars         = 0;      // 차트명가: 마지막 봉 오른쪽에 비워 둘 칸 수 (되감으면 늘어난다)
int      g_baseTimerMS       = 200;
double   g_speedMult         = 1.0;
int      g_lastRenderedCount = 0;   
bool     g_isVLineVisible    = false;
bool     g_isMouseDragging   = false;
ulong    g_lastPlayMs        = 0;

#define PROGRESS_WIDTH 350
string SPEED_BTNS[6] = {"rep_btn_sp05","rep_btn_sp1","rep_btn_sp2","rep_btn_sp5","rep_btn_sp10","rep_btn_sp20"};
double SPEED_VALS[6] = {0.5, 1.0, 2.0, 5.0, 10.0, 20.0};

//--- State Drawing
string panelPrefix = "TV_Toolbar_";
string drawPrefix  = "TV_Obj_";
string memPrefix   = "TV_Mem_";

int btnWidth = 50;
int btnHeight = 35;
int spacing = 5;
int bottomMargin = 45;
int rightMargin = 20;

string tools[] = {"LONG", "SHORT"}; // HANYA LONG & SHORT

enum ENUM_DRAW_STATE { STATE_IDLE, STATE_WAIT_P1, STATE_WAIT_P2 };
ENUM_DRAW_STATE drawState = STATE_IDLE;
string activeTool = "";
string activeObjName = "";
datetime t1 = 0;
double   global_p1 = 0;
bool     isUpdatingGroup = false;

//--- Proteksi Drawing
bool     g_chartBusy = false;
ulong    g_lastSyncMs = 0;
ulong    g_lastRedrawMs = 0;
bool     g_initialized = false;

struct TradeGroupState
{
   string baseName;
   datetime t0;
   datetime t1;
   double entry;
   double sl;
   double tp;
   bool selected; 
};
TradeGroupState g_tradeStates[];

// Posisi Panel Drawing
int panelStartX = 0;
int panelStartY = 0;
int panelTotalWidth = 0;
int panelTotalHeight = 0;

// Posisi Panel Replay (Untuk proteksi klik)
int repPanelX1 = 10, repPanelY1 = 20, repPanelX2 = 390, repPanelY2 = 255;

//====================================================================
// INIT & DEINIT
//====================================================================
int OnInit()
{
   //--- Bypass untuk Strategy Tester / MQL5 Market Validation
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
   {
      Print("Strategy Tester detected. Bypassing Custom Symbol creation to pass Market Validation.");
      return(INIT_SUCCEEDED);
   }

   g_customSymbol = _Symbol;
   g_isCustomMode = (bool)SymbolInfoInteger(g_customSymbol, SYMBOL_CUSTOM);
   g_baseTimerMS  = InpBaseTimerMS;

   if(!g_isCustomMode)
   {
      g_sourceSymbol = g_customSymbol;
      string targetCustom = g_sourceSymbol + "_REPLAY";

      Print("Creating Custom Replay Symbol for: ", g_sourceSymbol);
      GlobalVariableDel("RepLastTime_" + targetCustom);
      GlobalVariableDel("RepIsPlaying_" + targetCustom);
      GlobalVariableDel("RepStartDate_" + targetCustom);

      ResetLastError();
      if(!SymbolInfoInteger(targetCustom, SYMBOL_CUSTOM))
      {
         if(!CustomSymbolCreate(targetCustom, "Custom\\Replay", g_sourceSymbol))
         {
            Print("Failed to create Custom Symbol! Error: ", GetLastError());
            return(INIT_FAILED);
         }
      }

      CustomSymbolSetInteger(targetCustom, SYMBOL_DIGITS, (int)SymbolInfoInteger(g_sourceSymbol, SYMBOL_DIGITS));
      CustomSymbolSetDouble(targetCustom, SYMBOL_POINT, SymbolInfoDouble(g_sourceSymbol, SYMBOL_POINT));
      CustomSymbolSetDouble(targetCustom, SYMBOL_TRADE_CONTRACT_SIZE, SymbolInfoDouble(g_sourceSymbol, SYMBOL_TRADE_CONTRACT_SIZE));
      SymbolSelect(targetCustom, true);

      LoadSelectedDataInternal(targetCustom);
      return(INIT_SUCCEEDED);
   }
   else
   {
      g_customSymbol = _Symbol;

      int len = StringLen(g_customSymbol);
      if(StringFind(g_customSymbol, "_REPLAY") != -1)
         g_sourceSymbol = StringSubstr(g_customSymbol, 0, len - 7);
      else
         g_sourceSymbol = InpSourceSymbol;

      ApplyGreenOnBlackTheme();

      UpdateStatusLabel("Status: Loading max M1 data...");
      LoadSelectedData();

      if(g_totalBars <= 0)
      {
         CreateUI(0);
         UpdateStatusLabel("Status: FAILED to fetch data. Open source chart briefly.");
         return(INIT_SUCCEEDED);
      }

      datetime targetStart = (g_totalBars > 10000) ? g_allRates[10000].time : g_allRates[0].time; 
      double savedStartD = GlobalVariableGet("RepStartDate_" + g_customSymbol);
      if(savedStartD > 0.0) targetStart = (datetime)savedStartD;
      if(targetStart < g_allRates[0].time) targetStart = g_allRates[0].time;

      CreateUI(targetStart);
      InitStartLine(); 
      CreateToolbar(); // UI Drawing Tool
      ScanExistingTrades();

      ChartSetInteger(0, CHART_EVENT_MOUSE_MOVE, true);
      ChartSetInteger(0, CHART_EVENT_OBJECT_DELETE, true);

      datetime earliestAvail = g_allRates[0].time;
      datetime guiStart = GetGuiStartDate();
      if(guiStart < earliestAvail)
      {
         guiStart = earliestAvail;
         ObjectSetString(0, "rep_edit_startdate", OBJPROP_TEXT, TimeToString(guiStart, TIME_DATE|TIME_MINUTES));
      }

      double savedTimeD = GlobalVariableGet("RepLastTime_" + g_customSymbol);
      if(savedTimeD > 0.0)
      {
         long savedTime = (long)savedTimeD;
         int idx = TFBarEndIndex(savedTime);          // 차트명가: 봉 끝에서 시작
         g_currentDisplay = idx + 1;
      }
      else
      {
         long startLong = (long)guiStart;
         int idx = TFBarEndIndex(startLong);          // 차트명가: 봉 끝에서 시작
         g_currentDisplay = idx + 1;
      }

      int minDisplay = GetMinDisplayBars();
      if(g_currentDisplay < minDisplay && g_totalBars >= minDisplay) g_currentDisplay = minDisplay;
      if(g_currentDisplay > g_totalBars) g_currentDisplay = g_totalBars;

      double savedPlayD = GlobalVariableGet("RepIsPlaying_" + g_customSymbol);
      if(savedPlayD > 0.0 && g_currentDisplay < g_totalBars)
      {
         g_isPlaying = true;
         ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PAUSE");
         ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrFireBrick);
      }
      else g_isPlaying = false;

      //== 차트명가 추가: 마지막 봉을 화면 가운데에 두고 오른쪽을 비운다 (2026-09-29) ==
      //  기본값이면 마지막 봉이 오른쪽 끝에 붙어 '그냥 과거로 스크롤한 화면' 처럼 보인다.
      //  MT5 의 차트 이동(CHART_SHIFT)은 최대 50% 까지 밀 수 있다 — 50 이면 딱 절반이 빈다.
      g_anchorView = InpAnchorView;
      ChartSetInteger(0, CHART_AUTOSCROLL, false);   // 새 봉이 와도 화면이 끌려가지 않게
      if(InpShiftPercent > 0)
      {
         ChartSetInteger(0, CHART_SHIFT, true);
         ChartSetDouble(0, CHART_SHIFT_SIZE, (double)MathMin(50, MathMax(10, InpShiftPercent)));
      }
      else ChartSetInteger(0, CHART_SHIFT, false);

      RenderCurrentView(true);
      
      g_initialized = true;
      g_lastPlayMs = GetTickCount64();
      
      EventSetMillisecondTimer(20); 

      return(INIT_SUCCEEDED);
   }
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   g_chartBusy = true;

   if(g_isCustomMode)
   {
      if(g_currentDisplay > 0 && g_currentDisplay <= g_totalBars) 
      {
         long lastTimeLong = (long)g_allRates[g_currentDisplay - 1].time;
         GlobalVariableSet("RepLastTime_" + g_customSymbol, (double)lastTimeLong);
         GlobalVariableSet("RepIsPlaying_" + g_customSymbol, g_isPlaying ? 1.0 : 0.0);
         GlobalVariableSet("RepStartDate_" + g_customSymbol, (double)GetGuiStartDate());
      }

      ObjectsDeleteAll(0, "rep_");
      
      int total = ObjectsTotal(0, 0, -1);
      for(int i = total - 1; i >= 0; i--)
      {
         string name = ObjectName(0, i, 0, -1);
         if(name != "" && StringFind(name, panelPrefix) == 0)
            ObjectDelete(0, name);
      }

      ChartRedraw(0);
   }
   
   g_initialized = false;
   g_chartBusy = false;
}

//====================================================================
// GLOBAL TIMER ENGINE (REPLAY + WATCHDOG)
//====================================================================
void OnTimer()
{
   if(!g_isCustomMode) return;

   RunWatchdog();

   if(!g_isPlaying || g_totalBars == 0) return;

   ulong now = GetTickCount64();
   ulong interval = (ulong)CurrentIntervalMS();

   if(now - g_lastPlayMs >= interval)
   {
      g_lastPlayMs = now;
      
      int tfSec = PeriodSeconds(_Period);
      if(tfSec <= 0) tfSec = 60;

      if(g_currentDisplay <= 0 || g_currentDisplay > g_totalBars) return;

      long currentM1Time = (long)g_allRates[g_currentDisplay - 1].time;
      long currentBarOpenTF = currentM1Time - (currentM1Time % tfSec);
      long targetTime = currentBarOpenTF + (long)tfSec;

      int idx = TFBarEndIndex(targetTime);          // 차트명가: 재생도 봉 끝에서 끊는다
      int cur = g_currentDisplay - 1;
      if(idx <= cur)                                // 빈 구간이면 다음 있는 봉으로
      {
         int j = FindBarIndexAtOrAfterLong(currentM1Time + 1);
         if(j < g_totalBars) idx = TFBarEndIndex((long)g_allRates[j].time);
      }
      int nextDisplay = ClampIndex(idx) + 1;

      if(nextDisplay > g_currentDisplay && nextDisplay <= g_totalBars)
      {
         g_blankBars -= 1;        // 차트명가: 재생도 한 칸씩 오른쪽을 메운다
         g_currentDisplay = nextDisplay;
         RenderCurrentView(false); 
      }
      else
      {
         g_currentDisplay = g_totalBars;
         RenderCurrentView(false);
         g_isPlaying = false;
         
         ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "FINISH");
         ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrGray);
         UpdateStatusLabel("Status: Replay Finished");
      }
   }
}

//====================================================================
// FUNGSI DRAWING TOOL (LONG & SHORT)
//====================================================================
void RunWatchdog()
{
   if(!g_initialized || isUpdatingGroup) return;

   ulong now = GetTickCount64();
   if(g_chartBusy)
   {
      if(now - g_lastSyncMs < 500) return;
      g_chartBusy = false;
   }

   now = GetTickCount64();
   if(now - g_lastSyncMs < 80) return;
   g_lastSyncMs = now;

   bool anySynced = false;

   for(int i = ArraySize(g_tradeStates) - 1; i >= 0; i--)
   {
      string baseName = g_tradeStates[i].baseName;
      if(baseName == "") continue;

      string master = baseName + "_FSL";

      if(ObjectFind(0, master) < 0)
      {
         UnregisterTradeGroup(baseName);
         continue;
      }

      bool isLong = (StringFind(baseName, "LONG") >= 0);
      SyncTradeFromMaster(baseName, isLong);
      anySynced = true;
   }

   if(anySynced)
   {
      now = GetTickCount64();
      if(now - g_lastRedrawMs >= 80)
      {
         g_lastRedrawMs = now;
         ChartRedraw();
      }
   }
}

void CreateToolbar()
{
   long chartWidth = ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
   long chartHeight = ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS);

   int totalTools = ArraySize(tools);
   panelTotalWidth = (totalTools * btnWidth) + ((totalTools - 1) * spacing);
   panelTotalHeight = btnHeight;
   panelStartX = (int)chartWidth - rightMargin - panelTotalWidth;
   panelStartY = (int)chartHeight - bottomMargin - btnHeight;

   string bgName = panelPrefix + "Bg";
   ObjectCreate(0, bgName, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bgName, OBJPROP_XDISTANCE, panelStartX - 5);
   ObjectSetInteger(0, bgName, OBJPROP_YDISTANCE, panelStartY - 5);
   ObjectSetInteger(0, bgName, OBJPROP_XSIZE, panelTotalWidth + 10);
   ObjectSetInteger(0, bgName, OBJPROP_YSIZE, panelTotalHeight + 10);
   ObjectSetInteger(0, bgName, OBJPROP_BGCOLOR, InpBgColor);
   ObjectSetInteger(0, bgName, OBJPROP_BORDER_COLOR, clrDimGray);
   ObjectSetInteger(0, bgName, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bgName, OBJPROP_BACK, false);
   ObjectSetInteger(0, bgName, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bgName, OBJPROP_ZORDER, 10);

   for(int i = 0; i < totalTools; i++)
   {
      string name = panelPrefix + "Btn_" + tools[i];
      int x = panelStartX + (i * (btnWidth + spacing));
      int y = panelStartY;

      ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE, btnWidth);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, btnHeight);
      ObjectSetString(0, name, OBJPROP_TEXT, tools[i]);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, InpBtnColor);
      ObjectSetInteger(0, name, OBJPROP_COLOR, InpTextColor);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
      ObjectSetString(0, name, OBJPROP_FONT, "Segoe UI");
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 20);
   }
}

void DrawTrade(string pfx, string side, datetime time1, datetime time2, double entry, double sl, double tp)
{
   if(g_chartBusy || pfx == "") return;
   if(!MathIsValidNumber(entry) || !MathIsValidNumber(sl) || !MathIsValidNumber(tp)) return;

   color clrEntry = clrBlue;
   color clrTP    = clrGreen;
   color clrSL    = clrRed;
   int lineWidth = 2;

   if(time2 <= time1)
   {
      int ps = PeriodSeconds(_Period);
      if(ps <= 0) ps = 60;
      time2 = time1 + ps;
   }

   color clrFill_SL = C'80,30,30';
   color clrFill_TP = C'30,80,30';

   string fsl = pfx+"_FSL";
   string e   = pfx+"_E";
   string sln = pfx+"_SL";
   string tpn = pfx+"_TP";
   string ftp = pfx+"_FTP";

   bool firstTime = (ObjectFind(0, e) < 0);

   if(firstTime)
   {
      if(!ObjectCreate(0, fsl, OBJ_RECTANGLE, 0, time1, entry, time2, sl)) return;
      ObjectSetInteger(0, fsl, OBJPROP_COLOR, clrFill_SL);
      ObjectSetInteger(0, fsl, OBJPROP_BGCOLOR, clrFill_SL);
      ObjectSetInteger(0, fsl, OBJPROP_BACK, false);
      ObjectSetInteger(0, fsl, OBJPROP_FILL, true);
      ObjectSetInteger(0, fsl, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
      ObjectSetInteger(0, fsl, OBJPROP_SELECTABLE, false);

      if(!ObjectCreate(0, e, OBJ_TREND, 0, time1, entry, time2, entry)) return;
      ObjectSetInteger(0, e, OBJPROP_COLOR, clrEntry);
      ObjectSetInteger(0, e, OBJPROP_WIDTH, lineWidth);
      ObjectSetInteger(0, e, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, e, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
      ObjectSetInteger(0, e, OBJPROP_SELECTABLE, false);

      if(!ObjectCreate(0, sln, OBJ_TREND, 0, time1, sl, time2, sl)) return;
      ObjectSetInteger(0, sln, OBJPROP_COLOR, clrSL);
      ObjectSetInteger(0, sln, OBJPROP_WIDTH, lineWidth);
      ObjectSetInteger(0, sln, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, sln, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
      ObjectSetInteger(0, sln, OBJPROP_SELECTABLE, false);

      if(!ObjectCreate(0, tpn, OBJ_TREND, 0, time1, tp, time2, tp)) return;
      ObjectSetInteger(0, tpn, OBJPROP_COLOR, clrTP);
      ObjectSetInteger(0, tpn, OBJPROP_WIDTH, lineWidth);
      ObjectSetInteger(0, tpn, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, tpn, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
      ObjectSetInteger(0, tpn, OBJPROP_SELECTABLE, false);

      if(!ObjectCreate(0, ftp, OBJ_RECTANGLE, 0, time1, entry, time2, tp)) return;
      ObjectSetInteger(0, ftp, OBJPROP_COLOR, clrFill_TP);
      ObjectSetInteger(0, ftp, OBJPROP_BGCOLOR, clrFill_TP);
      ObjectSetInteger(0, ftp, OBJPROP_BACK, false);
      ObjectSetInteger(0, ftp, OBJPROP_FILL, true);
      ObjectSetInteger(0, ftp, OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS);
      ObjectSetInteger(0, ftp, OBJPROP_SELECTABLE, false);
   }
   else
   {
      if(ObjectFind(0, fsl) < 0 || ObjectFind(0, sln) < 0 || ObjectFind(0, tpn) < 0 || ObjectFind(0, ftp) < 0) return;

      ObjectSetInteger(0, fsl, OBJPROP_TIME, 0, time1); ObjectSetInteger(0, fsl, OBJPROP_TIME, 1, time2);
      ObjectSetDouble(0, fsl, OBJPROP_PRICE, 0, entry); ObjectSetDouble(0, fsl, OBJPROP_PRICE, 1, sl);

      ObjectSetInteger(0, e, OBJPROP_TIME, 0, time1); ObjectSetInteger(0, e, OBJPROP_TIME, 1, time2);
      ObjectSetDouble(0, e, OBJPROP_PRICE, 0, entry); ObjectSetDouble(0, e, OBJPROP_PRICE, 1, entry);

      ObjectSetInteger(0, sln, OBJPROP_TIME, 0, time1); ObjectSetInteger(0, sln, OBJPROP_TIME, 1, time2);
      ObjectSetDouble(0, sln, OBJPROP_PRICE, 0, sl); ObjectSetDouble(0, sln, OBJPROP_PRICE, 1, sl);

      ObjectSetInteger(0, tpn, OBJPROP_TIME, 0, time1); ObjectSetInteger(0, tpn, OBJPROP_TIME, 1, time2);
      ObjectSetDouble(0, tpn, OBJPROP_PRICE, 0, tp); ObjectSetDouble(0, tpn, OBJPROP_PRICE, 1, tp);

      ObjectSetInteger(0, ftp, OBJPROP_TIME, 0, time1); ObjectSetInteger(0, ftp, OBJPROP_TIME, 1, time2);
      ObjectSetDouble(0, ftp, OBJPROP_PRICE, 0, entry); ObjectSetDouble(0, ftp, OBJPROP_PRICE, 1, tp);
   }

   double risk = MathAbs(entry - sl);
   double ratio = (risk != 0) ? (MathAbs(tp - entry) / risk) : 1.0;
   datetime tA = (time1 < time2) ? time1 : time2;
   datetime tB = (time1 < time2) ? time2 : time1;

   UpdateTradeTexts(pfx, (side == "LONG"), tA, tB, entry, sl, tp, ratio);
}

void UpdateTradeTexts(string baseName, bool isLong, datetime tA, datetime tB, double entry, double sl, double tp, double ratio)
{
   string txtE  = baseName + "_TextEntry";
   string txtTP = baseName + "_TextTP";
   string txtSL = baseName + "_TextSL";
   color textColor = clrYellow;

   if(ObjectFind(0, txtE) < 0) { ObjectCreate(0, txtE, OBJ_TEXT, 0, 0, 0); ObjectSetString(0, txtE, OBJPROP_FONT, "Segoe UI"); ObjectSetInteger(0, txtE, OBJPROP_FONTSIZE, 8); ObjectSetInteger(0, txtE, OBJPROP_SELECTABLE, false); ObjectSetInteger(0, txtE, OBJPROP_HIDDEN, true); }
   if(ObjectFind(0, txtTP) < 0) { ObjectCreate(0, txtTP, OBJ_TEXT, 0, 0, 0); ObjectSetString(0, txtTP, OBJPROP_FONT, "Segoe UI"); ObjectSetInteger(0, txtTP, OBJPROP_FONTSIZE, 8); ObjectSetInteger(0, txtTP, OBJPROP_SELECTABLE, false); ObjectSetInteger(0, txtTP, OBJPROP_HIDDEN, true); }
   if(ObjectFind(0, txtSL) < 0) { ObjectCreate(0, txtSL, OBJ_TEXT, 0, 0, 0); ObjectSetString(0, txtSL, OBJPROP_FONT, "Segoe UI"); ObjectSetInteger(0, txtSL, OBJPROP_FONTSIZE, 8); ObjectSetInteger(0, txtSL, OBJPROP_SELECTABLE, false); ObjectSetInteger(0, txtSL, OBJPROP_HIDDEN, true); }

   ObjectSetInteger(0, txtE, OBJPROP_COLOR, textColor);
   ObjectSetInteger(0, txtTP, OBJPROP_COLOR, textColor);
   ObjectSetInteger(0, txtSL, OBJPROP_COLOR, textColor);

   datetime midT = tA + (tB - tA) / 2;
   int ptsTP = (int)MathRound(MathAbs(tp - entry) / _Point);
   int ptsSL = (int)MathRound(MathAbs(entry - sl) / _Point);

   string strE  = DoubleToString(entry, _Digits) + " / " + DoubleToString(ratio, 2) + "R";
   string strTP = DoubleToString(tp, _Digits) + " / " + IntegerToString(ptsTP);
   string strSL = DoubleToString(sl, _Digits) + " / -" + IntegerToString(ptsSL);

   ObjectSetString(0, txtE, OBJPROP_TEXT, strE);
   ObjectSetString(0, txtTP, OBJPROP_TEXT, strTP);
   ObjectSetString(0, txtSL, OBJPROP_TEXT, strSL);

   ObjectSetInteger(0, txtE, OBJPROP_TIME, midT); ObjectSetDouble(0, txtE, OBJPROP_PRICE, entry);
   ObjectSetInteger(0, txtTP, OBJPROP_TIME, midT); ObjectSetDouble(0, txtTP, OBJPROP_PRICE, tp);
   ObjectSetInteger(0, txtSL, OBJPROP_TIME, midT); ObjectSetDouble(0, txtSL, OBJPROP_PRICE, sl);

   if(isLong)
   {
      ObjectSetInteger(0, txtE, OBJPROP_ANCHOR, ANCHOR_LOWER);  
      ObjectSetInteger(0, txtTP, OBJPROP_ANCHOR, ANCHOR_UPPER); 
      ObjectSetInteger(0, txtSL, OBJPROP_ANCHOR, ANCHOR_LOWER); 
   }
   else
   {
      ObjectSetInteger(0, txtE, OBJPROP_ANCHOR, ANCHOR_UPPER);  
      ObjectSetInteger(0, txtTP, OBJPROP_ANCHOR, ANCHOR_LOWER); 
      ObjectSetInteger(0, txtSL, OBJPROP_ANCHOR, ANCHOR_UPPER); 
   }
}

void RegisterTradeGroup(string baseName)
{
   string master = baseName + "_FSL";
   string entryObj = baseName + "_E";
   string slObj = baseName + "_SL";
   string tpObj = baseName + "_TP";

   if(ObjectFind(0, master) < 0 || ObjectFind(0, entryObj) < 0 || ObjectFind(0, slObj) < 0 || ObjectFind(0, tpObj) < 0) return;

   int n = ArraySize(g_tradeStates);
   for(int i = 0; i < n; i++) if(g_tradeStates[i].baseName == baseName) return; 

   ArrayResize(g_tradeStates, n + 1);
   g_tradeStates[n].baseName = baseName;
   
   string tpBox  = baseName + "_FTP";
   g_tradeStates[n].t0 = (datetime)ObjectGetInteger(0, master, OBJPROP_TIME, 0);
   g_tradeStates[n].t1 = (datetime)ObjectGetInteger(0, master, OBJPROP_TIME, 1);
   g_tradeStates[n].entry = ObjectGetDouble(0, master, OBJPROP_PRICE, 0);
   g_tradeStates[n].sl = ObjectGetDouble(0, master, OBJPROP_PRICE, 1);
   g_tradeStates[n].selected = (bool)ObjectGetInteger(0, master, OBJPROP_SELECTED);
   
   if(ObjectFind(0, tpBox) >= 0) g_tradeStates[n].tp = ObjectGetDouble(0, tpBox, OBJPROP_PRICE, 1);
   else
   {
        double risk = MathAbs(g_tradeStates[n].entry - g_tradeStates[n].sl);
        bool isLong = (StringFind(baseName, "LONG") >= 0);
        g_tradeStates[n].tp = isLong ? (g_tradeStates[n].entry + risk) : (g_tradeStates[n].entry - risk);
   }
}

void UnregisterTradeGroup(string baseName)
{
   int total = ArraySize(g_tradeStates);
   for(int i = 0; i < total; i++)
   {
      if(g_tradeStates[i].baseName == baseName)
      {
         for(int j = i; j < total - 1; j++) g_tradeStates[j] = g_tradeStates[j + 1];
         ArrayResize(g_tradeStates, total - 1);
         return;
      }
   }
}

void SyncTradeFromMaster(string baseName, bool isLong)
{
   if(g_chartBusy || isUpdatingGroup || baseName == "") return;

   string master = baseName + "_FSL";
   string tpBox  = baseName + "_FTP";
   if(ObjectFind(0, master) < 0) return;

   int idx = -1;
   for(int i = 0; i < ArraySize(g_tradeStates); i++)
   {
      if(g_tradeStates[i].baseName == baseName) { idx = i; break; }
   }

   bool fsl_sel = (bool)ObjectGetInteger(0, master, OBJPROP_SELECTED);
   bool ftp_sel = (ObjectFind(0, tpBox) >= 0) ? (bool)ObjectGetInteger(0, tpBox, OBJPROP_SELECTED) : false;
   bool mem_sel = false;

   if (idx >= 0) {
      mem_sel = g_tradeStates[idx].selected;
      if (fsl_sel != mem_sel) { mem_sel = fsl_sel; if(ObjectFind(0, tpBox) >= 0) ObjectSetInteger(0, tpBox, OBJPROP_SELECTED, mem_sel); } 
      else if (ftp_sel != mem_sel) { mem_sel = ftp_sel; ObjectSetInteger(0, master, OBJPROP_SELECTED, mem_sel); }
   } else mem_sel = fsl_sel; 

   datetime fsl_t0 = (datetime)ObjectGetInteger(0, master, OBJPROP_TIME, 0);
   datetime fsl_t1 = (datetime)ObjectGetInteger(0, master, OBJPROP_TIME, 1);
   double fsl_entry = ObjectGetDouble(0, master, OBJPROP_PRICE, 0);
   double fsl_sl    = ObjectGetDouble(0, master, OBJPROP_PRICE, 1);

   bool tpBoxExists = (ObjectFind(0, tpBox) >= 0);
   datetime ftp_t0 = tpBoxExists ? (datetime)ObjectGetInteger(0, tpBox, OBJPROP_TIME, 0) : fsl_t0;
   datetime ftp_t1 = tpBoxExists ? (datetime)ObjectGetInteger(0, tpBox, OBJPROP_TIME, 1) : fsl_t1;
   double ftp_entry = tpBoxExists ? ObjectGetDouble(0, tpBox, OBJPROP_PRICE, 0) : fsl_entry;
   double ftp_tp   = tpBoxExists ? ObjectGetDouble(0, tpBox, OBJPROP_PRICE, 1) : 0;

   if(idx >= 0)
   {
      if(g_tradeStates[idx].entry == fsl_entry && g_tradeStates[idx].sl == fsl_sl && 
         g_tradeStates[idx].tp == ftp_tp && g_tradeStates[idx].t0 == fsl_t0 && 
         g_tradeStates[idx].t1 == fsl_t1 && g_tradeStates[idx].selected == mem_sel) return;
   }

   datetime new_t0, new_t1;
   double new_entry, new_sl, new_tp;

   if(idx >= 0)
   {
      new_t0 = g_tradeStates[idx].t0; new_t1 = g_tradeStates[idx].t1;
      new_entry = g_tradeStates[idx].entry; new_sl = g_tradeStates[idx].sl; new_tp = g_tradeStates[idx].tp;

      bool fsl_changed = (fsl_entry != new_entry || fsl_sl != new_sl || fsl_t0 != new_t0 || fsl_t1 != new_t1);
      bool ftp_changed = (ftp_entry != new_entry || ftp_tp != new_tp || ftp_t0 != new_t0 || ftp_t1 != new_t1);

      if (ftp_changed && !fsl_changed)
      {
         new_t0 = ftp_t0; new_t1 = ftp_t1;
         if (ftp_entry != new_entry) 
         { double entryDelta = ftp_entry - new_entry; new_entry = ftp_entry; new_sl += entryDelta; new_tp = ftp_tp; }
         else if (ftp_tp != new_tp) { new_tp = ftp_tp; }
      }
      else if (fsl_changed)
      {
         new_t0 = fsl_t0; new_t1 = fsl_t1;
         if (fsl_entry != new_entry)
         { double entryDelta = fsl_entry - new_entry; new_entry = fsl_entry; new_sl = fsl_sl; new_tp += entryDelta; }
         else if (fsl_sl != new_sl) { new_sl = fsl_sl; }
      }

      g_tradeStates[idx].t0 = new_t0; g_tradeStates[idx].t1 = new_t1;
      g_tradeStates[idx].entry = new_entry; g_tradeStates[idx].sl = new_sl;
      g_tradeStates[idx].tp = new_tp; g_tradeStates[idx].selected = mem_sel;
   }
   else
   {
      new_t0 = fsl_t0; new_t1 = fsl_t1; new_entry = fsl_entry; new_sl = fsl_sl;
      if(tpBoxExists) new_tp = ftp_tp;
      else { double risk = MathAbs(new_entry - new_sl); new_tp = isLong ? (new_entry + risk) : (new_entry - risk); }
   }

   datetime tA = (new_t0 < new_t1) ? new_t0 : new_t1;
   datetime tB = (new_t0 < new_t1) ? new_t1 : new_t0;
   if(tA == tB) tB = tA + PeriodSeconds(_Period);

   isUpdatingGroup = true;

   ObjectSetInteger(0, master, OBJPROP_TIME, 0, tA); ObjectSetInteger(0, master, OBJPROP_TIME, 1, tB);
   ObjectSetDouble(0, master, OBJPROP_PRICE, 0, new_entry); ObjectSetDouble(0, master, OBJPROP_PRICE, 1, new_sl);

   ObjectSetInteger(0, baseName+"_E", OBJPROP_TIME, 0, tA); ObjectSetInteger(0, baseName+"_E", OBJPROP_TIME, 1, tB);
   ObjectSetDouble(0, baseName+"_E", OBJPROP_PRICE, 0, new_entry); ObjectSetDouble(0, baseName+"_E", OBJPROP_PRICE, 1, new_entry);
   ObjectSetInteger(0, baseName+"_E", OBJPROP_SELECTED, mem_sel);

   ObjectSetInteger(0, baseName+"_SL", OBJPROP_TIME, 0, tA); ObjectSetInteger(0, baseName+"_SL", OBJPROP_TIME, 1, tB);
   ObjectSetDouble(0, baseName+"_SL", OBJPROP_PRICE, 0, new_sl); ObjectSetDouble(0, baseName+"_SL", OBJPROP_PRICE, 1, new_sl);
   ObjectSetInteger(0, baseName+"_SL", OBJPROP_SELECTED, mem_sel);

   ObjectSetInteger(0, baseName+"_TP", OBJPROP_TIME, 0, tA); ObjectSetInteger(0, baseName+"_TP", OBJPROP_TIME, 1, tB);
   ObjectSetDouble(0, baseName+"_TP", OBJPROP_PRICE, 0, new_tp); ObjectSetDouble(0, baseName+"_TP", OBJPROP_PRICE, 1, new_tp);
   ObjectSetInteger(0, baseName+"_TP", OBJPROP_SELECTED, mem_sel);

   if(tpBoxExists)
   {
      ObjectSetInteger(0, tpBox, OBJPROP_TIME, 0, tA); ObjectSetInteger(0, tpBox, OBJPROP_TIME, 1, tB);
      ObjectSetDouble(0, tpBox, OBJPROP_PRICE, 0, new_entry); ObjectSetDouble(0, tpBox, OBJPROP_PRICE, 1, new_tp);
   }
   
   double currentRisk = MathAbs(new_entry - new_sl);
   double currentRatio = (currentRisk != 0) ? (MathAbs(new_tp - new_entry) / currentRisk) : 1.0;
   UpdateTradeTexts(baseName, isLong, tA, tB, new_entry, new_sl, new_tp, currentRatio);

   isUpdatingGroup = false;
}

void FinalizeTradeGroup(string pfx)
{
   ObjectSetInteger(0, pfx+"_FSL", OBJPROP_SELECTABLE, true); ObjectSetInteger(0, pfx+"_FSL", OBJPROP_SELECTED, true); ObjectSetInteger(0, pfx+"_FSL", OBJPROP_HIDDEN, false);
   ObjectSetInteger(0, pfx+"_FTP", OBJPROP_SELECTABLE, true); ObjectSetInteger(0, pfx+"_FTP", OBJPROP_SELECTED, true); ObjectSetInteger(0, pfx+"_FTP", OBJPROP_HIDDEN, false);
   RegisterTradeGroup(pfx); 
}

string GetTradeBaseName(string objName)
{
   if(StringFind(objName, drawPrefix) != 0) return "";
   if(StringFind(objName, "LONG") < 0 && StringFind(objName, "SHORT") < 0) return "";

   string suffixes[5] = {"_FSL", "_FTP", "_SL", "_TP", "_E"};
   int nameLen = StringLen(objName);

   for(int i = 0; i < 5; i++)
   {
      int L = StringLen(suffixes[i]);
      if(nameLen > L && StringSubstr(objName, nameLen - L, L) == suffixes[i])
         return StringSubstr(objName, 0, nameLen - L);
   }
   return "";
}

void DeleteTradeGroup(string baseName)
{
   ObjectDelete(0, baseName + "_E"); ObjectDelete(0, baseName + "_SL"); ObjectDelete(0, baseName + "_TP");
   ObjectDelete(0, baseName + "_FSL"); ObjectDelete(0, baseName + "_FTP");
   ObjectDelete(0, baseName + "_TextEntry"); ObjectDelete(0, baseName + "_TextTP"); ObjectDelete(0, baseName + "_TextSL");
}

void ScanExistingTrades()
{
   ArrayResize(g_tradeStates, 0);
   int total = ObjectsTotal(0, 0, -1);
   for(int i = 0; i < total; i++)
   {
      string name = ObjectName(0, i, 0, -1);
      if(name == "") continue;
      if(StringFind(name, drawPrefix) != 0) continue;
      if(StringFind(name, "_FSL") <= 0) continue;
      string baseName = StringSubstr(name, 0, StringLen(name) - 4);
      if(ObjectFind(0, name) < 0) continue;
      RegisterTradeGroup(baseName);
   }
}

//====================================================================
// CHART EVENT MASTER (Replay UI + Drawing UI)
//====================================================================
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(!g_isCustomMode) return;

   //== 차트명가 추가: 단축키 (2026-09-29) ==========================
   //  원본에는 키 입력 처리가 없어 버튼을 마우스로 눌러야 했다.
   //  촬영 중에는 손이 차트 위에 있어야 하므로 키로 넘긴다.
   //    Z / X  한 봉 뒤·앞     A / S  열 봉 뒤·앞     스페이스  재생·정지
   //  (화살표는 MT5 가 차트 스크롤에 쓰므로 피했다)
   //== 차트명가 추가 (2026-09-30) ==================================
   //  MT5 안에서 도는 스크립트(CMG_ReplayStep)가 보내는 신호로도 감는다.
   //  lparam = 옮길 봉 수(음수면 뒤로). 키를 흉내 내지 않고 확인·자동화하기 위한 통로다.
   if(id == CHARTEVENT_CUSTOM + 0)
   {
      int n = (int)lparam;
      if(n != 0) SkipBars(n);
      return;
   }

   if(id == CHARTEVENT_KEYDOWN)
   {
      int key = (int)lparam;
      if(key == 'X')      { SkipBars(1);   return; }
      if(key == 'Z')      { SkipBars(-1);  return; }
      if(key == 'S')      { SkipBars(10);  return; }
      if(key == 'A')      { SkipBars(-10); return; }
      if(key == 32)  // 스페이스
      {
         if(g_currentDisplay >= g_totalBars) return;
         g_isPlaying = !g_isPlaying;
         ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, g_isPlaying ? "PAUSE" : "PLAY");
         ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, g_isPlaying ? clrFireBrick : clrForestGreen);
         if(g_isPlaying) g_lastPlayMs = GetTickCount64();
         ChartRedraw();
         return;
      }
   }

   if(id == CHARTEVENT_CHART_CHANGE)
   {
      g_chartBusy = true;
      g_lastSyncMs = GetTickCount64();
      ScanExistingTrades();
      return;
   }

   if(id == CHARTEVENT_MOUSE_MOVE)
   {
      int flags = (int)StringToInteger(sparam);
      bool leftPressed = ((flags & 1) == 1);
      int x = (int)lparam; int y = (int)dparam;

      bool overPanel = (x >= repPanelX1 && x <= repPanelX2 && y >= repPanelY1 && y <= repPanelY2);

      if(leftPressed && !overPanel) g_isMouseDragging = true;
      else if(!leftPressed) g_isMouseDragging = false;

      if(drawState == STATE_WAIT_P2)
      {
         datetime dt; double price; int subwin;
         if(ChartXYToTimePrice(0, x, y, subwin, dt, price))
         {
            if(activeObjName != "")
            {
               if(activeTool == "LONG")
               {
                  double entry = global_p1;
                  double sl = price;
                  if(sl >= entry) sl = entry - (Point() * 10);
                  double risk = entry - sl;
                  double tp = entry + risk;
                  DrawTrade(activeObjName, "LONG", t1, dt, entry, sl, tp);
               }
               else if(activeTool == "SHORT")
               {
                  double entry = global_p1;
                  double sl = price;
                  if(sl <= entry) sl = entry + (Point() * 10);
                  double risk = sl - entry;
                  double tp = entry - risk;
                  DrawTrade(activeObjName, "SHORT", t1, dt, entry, sl, tp);
               }
               ChartRedraw();
            }
         }
      }
      return;
   }

   if(id == CHARTEVENT_OBJECT_DRAG && sparam == "rep_startline")
   {
      long lineTime = ObjectGetInteger(0, "rep_startline", OBJPROP_TIME, 0);
      
      if(g_totalBars > 0 && lineTime < (long)g_allRates[0].time)
      {
         MessageBox("Data not available for this date! Exceeds oldest data limit.", "Warning", MB_OK|MB_ICONWARNING);
         MoveStartLine(g_allRates[0].time);
         ChartRedraw(0);
         return;
      }

      int idx = TFBarEndIndex(lineTime);             // 차트명가: 끌어다 놓아도 봉 끝에서 끊는다
      g_isPlaying = false;
      ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PLAY");
      ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrForestGreen);

      g_currentDisplay = ClampIndex(idx) + 1; 
      g_forceRecenter = true;
      RenderCurrentView(true); 

      datetime actualTime = g_allRates[g_currentDisplay - 1].time;
      MoveStartLine(actualTime); 
      ChartRedraw(0);
      return;
   }

   if(id == CHARTEVENT_CLICK && drawState != STATE_IDLE)
   {
      int x = (int)lparam; int y = (int)dparam;

      if( (x >= (panelStartX - 5) && x <= (panelStartX + panelTotalWidth + 5) && y >= (panelStartY - 5) && y <= (panelStartY + panelTotalHeight + 5)) || 
          (x >= repPanelX1 && x <= repPanelX2 && y >= repPanelY1 && y <= repPanelY2) )
      {
         return;
      }

      datetime dt; double price; int subwin;
      if(ChartXYToTimePrice(0, x, y, subwin, dt, price))
      {
         if(drawState == STATE_WAIT_P1)
         {
            t1 = dt; global_p1 = price;
            activeObjName = drawPrefix + activeTool + "_" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "_" + IntegerToString(MathRand());

            if(activeTool == "LONG")
            {
               double entry = global_p1;
               double sl = global_p1 - (Point() * 100);
               double tp = global_p1 + (Point() * 100);
               DrawTrade(activeObjName, "LONG", t1, t1 + PeriodSeconds(_Period)*5, entry, sl, tp);
            }
            else if(activeTool == "SHORT")
            {
               double entry = global_p1;
               double sl = global_p1 + (Point() * 100);
               double tp = global_p1 - (Point() * 100);
               DrawTrade(activeObjName, "SHORT", t1, t1 + PeriodSeconds(_Period)*5, entry, sl, tp);
            }

            drawState = STATE_WAIT_P2;
            ChartRedraw();
         }
         else if(drawState == STATE_WAIT_P2)
         {
            if(activeTool == "LONG")
            {
               double entry = global_p1;
               double sl = price;
               if(sl >= entry) sl = entry - (Point() * 10);
               double risk = entry - sl;
               double tp = entry + risk;
               DrawTrade(activeObjName, "LONG", t1, dt, entry, sl, tp);
               FinalizeTradeGroup(activeObjName);
            }
            else if(activeTool == "SHORT")
            {
               double entry = global_p1;
               double sl = price;
               if(sl <= entry) sl = entry + (Point() * 10);
               double risk = sl - entry;
               double tp = entry - risk;
               DrawTrade(activeObjName, "SHORT", t1, dt, entry, sl, tp);
               FinalizeTradeGroup(activeObjName);
            }

            drawState = STATE_IDLE;
            activeTool = ""; activeObjName = ""; t1 = 0; global_p1 = 0;

            for(int i = 0; i < ArraySize(tools); i++)
            {
               ObjectSetInteger(0, panelPrefix + "Btn_" + tools[i], OBJPROP_BGCOLOR, InpBtnColor);
               ObjectSetInteger(0, panelPrefix + "Btn_" + tools[i], OBJPROP_STATE, 0);
            }
            ChartRedraw();
         }
      }
      return;
   }

   if(id == CHARTEVENT_OBJECT_CLICK)
   {
      for(int i = 0; i < ArraySize(tools); i++)
      {
         string name = panelPrefix + "Btn_" + tools[i];
         if(sparam == name)
         {
            if(activeObjName != "" && drawState == STATE_WAIT_P2)
            {
               DeleteTradeGroup(activeObjName);
               activeObjName = "";
            }

            for(int j = 0; j < ArraySize(tools); j++)
            {
               ObjectSetInteger(0, panelPrefix + "Btn_" + tools[j], OBJPROP_BGCOLOR, InpBtnColor);
               ObjectSetInteger(0, panelPrefix + "Btn_" + tools[j], OBJPROP_STATE, 0);
            }

            activeTool = tools[i];
            ObjectSetInteger(0, name, OBJPROP_BGCOLOR, InpActiveColor);
            drawState = STATE_WAIT_P1;
            ChartRedraw();
            return;
         }
      }

      if(sparam == "rep_btn_play")
      {
         if(g_currentDisplay >= g_totalBars) { ObjectSetInteger(0, sparam, OBJPROP_STATE, false); return; }
         
         g_isPlaying = !g_isPlaying;
         if(g_isPlaying)
         {
            ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PAUSE");
            ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrFireBrick);
            g_lastPlayMs = GetTickCount64();
         }
         else
         {
            ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PLAY");
            ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrForestGreen);
         }
         ObjectSetInteger(0, "rep_btn_play", OBJPROP_STATE, false);
      }
      else if(sparam == "rep_btn_select") 
      {
         if(g_isVLineVisible) 
         {
            HideStartLine();
            g_isVLineVisible = false;
            ObjectSetInteger(0, "rep_btn_select", OBJPROP_BGCOLOR, clrGoldenrod);
         } 
         else 
         {
            g_isPlaying = false;
            ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PLAY");
            ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrForestGreen);

            datetime t = g_allRates[g_currentDisplay - 1].time;
            MoveStartLine(t); ShowStartLine();
            g_isVLineVisible = true;
            ObjectSetInteger(0, "rep_btn_select", OBJPROP_BGCOLOR, clrDarkOrange);
         }
         ObjectSetInteger(0, "rep_btn_select", OBJPROP_STATE, false);
      }
      else if(sparam == "rep_btn_loaddata")
      {
         g_isPlaying = false;
         ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PLAY");
         ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrForestGreen);

         LoadSelectedData();
         
         datetime earliestAvail = (g_totalBars > 0) ? g_allRates[0].time : 0;
         datetime guiStart = GetGuiStartDate();
         if(guiStart < earliestAvail)
         {
            MessageBox("Data not available for this date! Date auto-adjusted to the oldest data.", "Warning", MB_OK|MB_ICONWARNING);
            guiStart = earliestAvail;
            ObjectSetString(0, "rep_edit_startdate", OBJPROP_TEXT, TimeToString(guiStart, TIME_DATE|TIME_MINUTES));
         }

         long startLong = (long)guiStart;
         int idx = TFBarEndIndex(startLong);          // 차트명가: 봉 끝에서 시작
         int initialDisplay = idx + 1;
         int minDisp = GetMinDisplayBars();
         if(initialDisplay < minDisp && g_totalBars >= minDisp) initialDisplay = minDisp;
         if(initialDisplay > g_totalBars) initialDisplay = g_totalBars;
         g_currentDisplay = initialDisplay;

         g_forceRecenter = true; RenderCurrentView(true);
         if(g_currentDisplay > 0 && g_currentDisplay <= g_totalBars)
            MoveStartLine(g_allRates[g_currentDisplay - 1].time);

         ObjectSetInteger(0, "rep_btn_loaddata", OBJPROP_STATE, false);
      }
      else if(sparam == "rep_btn_next")   { SkipBars(1);   ObjectSetInteger(0, "rep_btn_next", OBJPROP_STATE, false); }
      else if(sparam == "rep_btn_prev")   { SkipBars(-1);  ObjectSetInteger(0, "rep_btn_prev", OBJPROP_STATE, false); }
      else if(sparam == "rep_btn_back10") { SkipBars(-10); ObjectSetInteger(0, "rep_btn_back10", OBJPROP_STATE, false); }
      else if(sparam == "rep_btn_skip10") { SkipBars(10);  ObjectSetInteger(0, "rep_btn_skip10", OBJPROP_STATE, false); }
      else if(sparam == "rep_btn_reset")
      {
         g_isPlaying = false;
         ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PLAY");
         ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrForestGreen);

         datetime earliestAvail = (g_totalBars > 0) ? g_allRates[0].time : 0;
         datetime guiStart = GetGuiStartDate();
         if(guiStart < earliestAvail)
         {
            MessageBox("Data not available for this date! Date auto-adjusted to the oldest data.", "Warning", MB_OK|MB_ICONWARNING);
            guiStart = earliestAvail;
            ObjectSetString(0, "rep_edit_startdate", OBJPROP_TEXT, TimeToString(guiStart, TIME_DATE|TIME_MINUTES));
         }

         long startLong = (long)guiStart;
         int idx = TFBarEndIndex(startLong);          // 차트명가: 봉 끝에서 시작
         int initialDisplay = idx + 1;
         int minDisp = GetMinDisplayBars();
         if(initialDisplay < minDisp && g_totalBars >= minDisp) initialDisplay = minDisp;
         if(initialDisplay > g_totalBars) initialDisplay = g_totalBars;
         g_currentDisplay = initialDisplay;

         g_forceRecenter = true; RenderCurrentView(true);
         MoveStartLine(g_allRates[g_currentDisplay - 1].time);
         ObjectSetInteger(0, "rep_btn_reset", OBJPROP_STATE, false);
      }
      else 
      {
         for(int i = 0; i < ArraySize(SPEED_BTNS); i++)
         {
            if(sparam == SPEED_BTNS[i])
            {
               SetSpeed(SPEED_BTNS[i], SPEED_VALS[i]);
               ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
               break;
            }
         }
      }
      ChartRedraw(0);
      return;
   }

   if(id == CHARTEVENT_OBJECT_CHANGE)
   {
      if(!isUpdatingGroup && !g_chartBusy)
      {
         if(StringFind(sparam, drawPrefix) == 0)
         {
            string baseName = GetTradeBaseName(sparam);
            if(baseName != "")
            {
               bool isLong = (StringFind(baseName, "LONG") >= 0);
               SyncTradeFromMaster(baseName, isLong);
               ChartRedraw();
            }
         }
      }
      return;
   }

   if(id == CHARTEVENT_OBJECT_DELETE)
   {
      if(!g_chartBusy && StringFind(sparam, drawPrefix) == 0)
      {
         string delBase = GetTradeBaseName(sparam);
         if(delBase != "")
         {
            DeleteTradeGroup(delBase);
            UnregisterTradeGroup(delBase);
            ChartRedraw();
         }
      }
      return;
   }
}

//====================================================================
// FUNGSI BANTUAN REPLAY ENGINE
//====================================================================
int CurrentIntervalMS()
{
   int ms = (int)MathRound(g_baseTimerMS / g_speedMult);
   if(ms < 5) ms = 5;
   return ms;
}

void ApplyGreenOnBlackTheme()
{
   ChartSetInteger(0, CHART_MODE, CHART_CANDLES);
   ChartSetInteger(0, CHART_COLOR_BACKGROUND, clrBlack);
   ChartSetInteger(0, CHART_COLOR_FOREGROUND, clrWhite);
   ChartSetInteger(0, CHART_COLOR_GRID, false);
   ChartSetInteger(0, CHART_COLOR_CHART_UP, clrGreen);
   ChartSetInteger(0, CHART_COLOR_CHART_DOWN, clrMaroon);
   ChartSetInteger(0, CHART_COLOR_CANDLE_BULL, clrTeal);
   ChartSetInteger(0, CHART_COLOR_CANDLE_BEAR, clrMaroon);
   ChartSetInteger(0, CHART_COLOR_CHART_LINE, clrLime);
   ChartSetInteger(0, CHART_COLOR_VOLUME, clrLimeGreen);
   ChartSetInteger(0, CHART_COLOR_BID, clrLightSlateGray);
   ChartSetInteger(0, CHART_COLOR_ASK, clrRed);
   ChartSetInteger(0, CHART_COLOR_LAST, C'0,192,0');
   ChartSetInteger(0, CHART_COLOR_VOLUME, false);
   ChartSetInteger(0, CHART_COLOR_STOP_LEVEL, clrRed);
   ChartSetInteger(0, CHART_SHOW_ASK_LINE, false);
   ChartSetInteger(0, CHART_AUTOSCROLL, true); 
   ChartRedraw(0);
}

bool EnsureSymbolHistoryRates(string symbol, ENUM_TIMEFRAMES tf, int wantBars, int timeoutMs, MqlRates &out[])
{
   SymbolSelect(symbol, true); ArraySetAsSeries(out, false);
   uint t0 = GetTickCount(); int copied = 0;
   while((int)(GetTickCount() - t0) < timeoutMs)
   {
      ResetLastError();
      copied = CopyRates(symbol, tf, 0, wantBars, out);
      bool synced = (bool)SeriesInfoInteger(symbol, tf, SERIES_SYNCHRONIZED);
      if(copied > 0 && (synced || copied >= wantBars)) return true;
      Sleep(250);
   }
   return (copied > 0);
}

datetime GetGuiStartDate()
{
   string dateStr = ObjectGetString(0, "rep_edit_startdate", OBJPROP_TEXT);
   if(dateStr != "") { datetime parsed = StringToTime(dateStr); if(parsed > 0) return parsed; }
   return InpStartDate;
}

void LoadSelectedData()
{
   MqlRates rawM1[];
   bool ok = EnsureSymbolHistoryRates(g_sourceSymbol, PERIOD_M1, 1000000, InpDownloadTimeoutSec * 1000, rawM1);
   if(ok)
   {
      int total = ArraySize(rawM1);
      if(total > 0)
      {
         ArrayResize(g_allRates, total);
         ArrayCopy(g_allRates, rawM1, 0, 0, total);
         g_totalBars = total;
      }
   }
}

void LoadSelectedDataInternal(string targetCustom)
{
   MqlRates rates[];
   bool ok = EnsureSymbolHistoryRates(g_sourceSymbol, PERIOD_M1, 1000000, InpDownloadTimeoutSec * 1000, rates);
   int copied = ArraySize(rates);
   if(copied > 0)
   {
      CustomRatesDelete(targetCustom, D'1970.01.01 00:00', D'2099.01.01 00:00');
      CustomRatesUpdate(targetCustom, rates, copied);
      Print("SUCCESS! Custom Symbol [", targetCustom, "] ready.");
   }
   else Print("Failed to copy M1 data from main symbol.");
}

int GetMinDisplayBars()
{
   if(g_totalBars <= 0) return InpMinVisibleBars;
   long minNeeded = InpMinVisibleBars;
   if(minNeeded > g_totalBars) minNeeded = g_totalBars;
   if(minNeeded < 20) minNeeded = 20;
   return (int)minNeeded;
}

int FindBarIndexAtOrAfterLong(const long targetTime)
{
   int left = 0; int right = g_totalBars - 1; int result = g_totalBars; 
   while(left <= right) 
   {
      int mid = left + (right - left) / 2;
      long t = (long)g_allRates[mid].time;
      if(t >= targetTime) { result = mid; right = mid - 1; }
      else { left = mid + 1; }
   }
   return result; 
}

//== 차트명가 추가 (2026-09-30) ==================================
//  화면 끝을 '다 만들어진 봉' 에 맞춘다.
//  원본은 TF 봉이 시작하는 **첫 M1 봉**에서 끊었다 → 마지막 봉이 1분짜리 미완성 봉이라
//  종가가 아니라 엉뚱한 중간값에서 끊긴 것처럼 보였다 (이정찬 09-29).
//  주어진 시각이 속한 TF 봉의 **마지막 M1 봉** 자리를 돌려준다.
int TFBarEndIndex(const long anyTime)
{
   int tfSec = PeriodSeconds(_Period);
   if(tfSec <= 0) tfSec = 60;
   long barOpen = anyTime - (anyTime % tfSec);
   int  endIdx  = FindBarIndexAtOrAfterLong(barOpen + (long)tfSec) - 1;  // 다음 TF 봉 첫 M1 의 한 칸 앞
   if(endIdx < 0) endIdx = 0;
   if(endIdx >= g_totalBars) endIdx = g_totalBars - 1;
   return endIdx;
}

int FindNearestBarIndex(const long targetTime)
{
   int left = 0; int right = g_totalBars - 1; int best = 0;
   long minDiff = LONG_MAX;
   while(left <= right)
   {
      int mid = left + (right - left) / 2;
      long t = (long)g_allRates[mid].time;
      long diff = t - targetTime; if(diff < 0) diff = -diff;
      if(diff < minDiff) { minDiff = diff; best = mid; }
      if(t < targetTime) left = mid + 1; else right = mid - 1;
   }
   return best;
}

int ClampIndex(int idx) 
{
   int minDisplay = GetMinDisplayBars();
   int minIdx = minDisplay - 1;
   if(idx < minIdx) return minIdx;
   if(idx >= g_totalBars) return g_totalBars - 1;
   return idx;
}

void UpdateCloseLine(double closePrice)
{
   if(ObjectFind(0, "rep_closeline") < 0)
   {
      ObjectCreate(0, "rep_closeline", OBJ_HLINE, 0, 0, closePrice);
      ObjectSetInteger(0, "rep_closeline", OBJPROP_COLOR, clrGold);
      ObjectSetInteger(0, "rep_closeline", OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(0, "rep_closeline", OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, "rep_closeline", OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, "rep_closeline", OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, "rep_closeline", OBJPROP_BACK, true); // Tambahan z-index
      ObjectSetInteger(0, "rep_closeline", OBJPROP_ZORDER, 0); // Tambahan z-index
   }
   else ObjectMove(0, "rep_closeline", 0, 0, closePrice);
}

//== 차트명가 추가 (2026-09-30) ==================================
//  밖에서 확인할 수 있게 상태를 파일로 적는다 — MQL5\Files\cmg_replay_<차트ID>.txt
//  (키를 흉내 내 확인하다 남의 창에 글자가 찍힌 사고가 있었다. 확인은 데이터로 한다.)
//    1줄  마지막으로 보이는 봉의 시각
//    2줄  END=<끝봉시각> CLOSE=<종가> FV=<왼쪽끝봉> WIDTH=<화면칸수> BLANK=<오른쪽빈칸> POS=<몇/몇>
void WriteReplayStatus()
{
   long fv    = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
   long width = ChartGetInteger(0, CHART_WIDTH_IN_BARS);
   datetime endT = (g_currentDisplay > 0) ? g_allRates[g_currentDisplay - 1].time : 0;
   double   endC = (g_currentDisplay > 0) ? g_allRates[g_currentDisplay - 1].close : 0.0;

   int fh = FileOpen("cmg_replay_" + IntegerToString(ChartID()) + ".txt",
                     FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) return;
   FileWrite(fh, TimeToString(endT, TIME_DATE | TIME_SECONDS));
   FileWrite(fh, StringFormat("END=%s CLOSE=%s FV=%d WIDTH=%d BLANK=%d WANT=%d POS=%d/%d",
                              TimeToString(endT, TIME_DATE | TIME_SECONDS),
                              DoubleToString(endC, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS)),
                              (int)fv, (int)width, (int)(width - (fv + 1)), g_blankBars,
                              g_currentDisplay, g_totalBars));
   FileClose(fh);
}

void RenderCurrentView(bool resetView = false)
{
   if(resetView) g_lastRenderedCount = 0;
   int minDisplay = GetMinDisplayBars();
   if(g_currentDisplay < minDisplay) g_currentDisplay = minDisplay;
   if(g_currentDisplay > g_totalBars) g_totalBars = g_totalBars;

   int delta = g_currentDisplay - g_lastRenderedCount;

   if(g_lastRenderedCount <= 0 || resetView)
   {
      CustomRatesDelete(g_customSymbol, D'1970.01.01 00:00', D'2099.01.01 00:00');
      MqlRates newRates[]; ArrayResize(newRates, g_currentDisplay);
      ArrayCopy(newRates, g_allRates, 0, 0, g_currentDisplay);
      CustomRatesUpdate(g_customSymbol, newRates);
   }
   else if(delta > 0)
   {
      MqlRates newRates[]; ArrayResize(newRates, delta);
      ArrayCopy(newRates, g_allRates, 0, g_currentDisplay - delta, delta);
      CustomRatesUpdate(g_customSymbol, newRates);
   }
   else
   {
      MqlRates singleRate[1]; singleRate[0] = g_allRates[g_currentDisplay - 1];
      CustomRatesUpdate(g_customSymbol, singleRate);
   }

   UpdateCloseLine(g_allRates[g_currentDisplay - 1].close);
   g_lastRenderedCount = g_currentDisplay;

   UpdateProgress();
   UpdateStatusLabel();

   //== 차트명가 고침 (2026-09-30, 두 번째) =========================
   //  09-29 판(화면을 그대로 두는 방식)은 안 먹혔다 — 되감을 때 데이터를 통째로 다시 쓰므로
   //  MT5 가 스스로 화면을 끝에 도로 맞췄고, 오른쪽 빈 칸이 늘 50% 에 붙어 있었다 (실측 09-30).
   //  그래서 빈 칸 수를 우리가 세어 두고, 그릴 때마다 **오른쪽 여백을 직접 지정**한다.
   //  되감으면 빈 칸이 늘고, 앞으로 가면 줄어든다.
   //  한계: MT5 는 마지막 봉을 화면 한가운데(여백 50%)보다 왼쪽에 두지 못한다.
   //        10~50% 안에서만 움직이고, 한계에 닿으면 그때부터 화면이 따라간다.
   if(g_anchorView)
   {
      long width = ChartGetInteger(0, CHART_WIDTH_IN_BARS);
      if(width < 10) width = 10;
      int minBlank = (int)(width * 10 / 100);
      int maxBlank = (int)(width * 50 / 100);

      if(g_forceRecenter)                       // 처음 붙였을 때·날짜로 점프했을 때
      {
         g_blankBars = (int)(width * MathMin(50, MathMax(10, InpShiftPercent)) / 100);
         g_forceRecenter = false;
      }
      if(g_blankBars < minBlank) g_blankBars = minBlank;
      if(g_blankBars > maxBlank) g_blankBars = maxBlank;

      ChartSetInteger(0, CHART_SHIFT, true);
      ChartSetDouble(0, CHART_SHIFT_SIZE, 100.0 * (double)g_blankBars / (double)width);
      ChartNavigate(0, CHART_END, 0);
   }
   else
      ChartNavigate(0, CHART_END, 0);

   WriteReplayStatus();

   long currentBarTimeLong = (long)g_allRates[g_currentDisplay - 1].time;
   GlobalVariableSet("RepLastTime_" + g_customSymbol, (double)currentBarTimeLong);
   GlobalVariableSet("RepIsPlaying_" + g_customSymbol, g_isPlaying ? 1.0 : 0.0);
   GlobalVariableSet("RepStartDate_" + g_customSymbol, (double)GetGuiStartDate());
}

void InitStartLine()
{
   ObjectDelete(0, "rep_startline");
   ObjectCreate(0, "rep_startline", OBJ_VLINE, 0, 0, 0);
   ObjectSetInteger(0, "rep_startline", OBJPROP_COLOR, clrGoldenrod);
   ObjectSetInteger(0, "rep_startline", OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, "rep_startline", OBJPROP_WIDTH, 2);
   ObjectSetInteger(0, "rep_startline", OBJPROP_BACK, false);
   ObjectSetInteger(0, "rep_startline", OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, "rep_startline", OBJPROP_SELECTED, true);
   ObjectSetInteger(0, "rep_startline", OBJPROP_HIDDEN, true);
   ObjectSetString(0, "rep_startline", OBJPROP_TOOLTIP, "Drag this line to select replay starting point");
   HideStartLine();
}

void ShowStartLine() { if(ObjectFind(0, "rep_startline") >= 0) ObjectSetInteger(0, "rep_startline", OBJPROP_TIMEFRAMES, OBJ_ALL_PERIODS); }
void HideStartLine() { if(ObjectFind(0, "rep_startline") >= 0) ObjectSetInteger(0, "rep_startline", OBJPROP_TIMEFRAMES, OBJ_NO_PERIODS); }
void MoveStartLine(datetime t) { if(ObjectFind(0, "rep_startline") >= 0) ObjectMove(0, "rep_startline", 0, t, 0); }

void UpdateProgress()
{
   int pct = (g_totalBars > 0) ? (g_currentDisplay * 100) / g_totalBars : 0;
   int w   = (int)MathRound(PROGRESS_WIDTH * pct / 100.0);
   if(w < 1) w = 1;
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_XSIZE, w);
   ChartRedraw(0);
}

void UpdateStatusLabel(string text = "") 
{
   if(text == "") 
   {
      if(g_currentDisplay > 0 && g_currentDisplay <= g_totalBars) 
      {
         datetime currentBarTime = g_allRates[g_currentDisplay - 1].time;
         string timeStr = TimeToString(currentBarTime, TIME_DATE|TIME_MINUTES);
         int pct = (g_totalBars > 0) ? (g_currentDisplay * 100) / g_totalBars : 0;
         text = StringFormat("Time: %s | Bar %d/%d (%d%%)", timeStr, g_currentDisplay, g_totalBars, pct);
      } 
      else text = "Status: Initializing...";
   }
   ObjectSetString(0, "rep_lbl_status", OBJPROP_TEXT, text);

   if(g_totalBars > 0)
   {
      string minLimitStr = "Min Start: " + TimeToString(g_allRates[0].time, TIME_DATE|TIME_MINUTES);
      ObjectSetString(0, "rep_lbl_limit", OBJPROP_TEXT, minLimitStr);
   }
   else ObjectSetString(0, "rep_lbl_limit", OBJPROP_TEXT, "Min Start: -");
   ChartRedraw(0);
}

void SkipBars(int n) 
{
   bool wasPlaying = g_isPlaying;
   g_isPlaying = false;

   int tfSec = PeriodSeconds(_Period);
   if(tfSec <= 0) tfSec = 60;
   if(g_currentDisplay <= 0 || g_currentDisplay > g_totalBars) return;

   long currentM1Time = (long)g_allRates[g_currentDisplay - 1].time;
   long currentBarOpenTF = currentM1Time - (currentM1Time % tfSec);
   long targetTime = currentBarOpenTF + (long)n * tfSec;

   int idx = TFBarEndIndex(targetTime);            // 차트명가: 다 만들어진 봉의 끝에서 끊는다
   int cur = g_currentDisplay - 1;
   //  주말·장 마감처럼 빈 구간이면 제자리일 수 있다 → 한 칸이라도 움직이게 한다.
   if(n > 0 && idx <= cur)
   {
      int j = FindBarIndexAtOrAfterLong(currentM1Time + 1);
      if(j < g_totalBars) idx = TFBarEndIndex((long)g_allRates[j].time);
   }
   else if(n < 0 && idx >= cur && cur > 0)
      idx = TFBarEndIndex((long)g_allRates[cur - 1].time);

   g_blankBars -= n;              // 차트명가: 뒤로 가면 오른쪽이 그만큼 비고, 앞으로 가면 메워진다
   g_currentDisplay = ClampIndex(idx) + 1;
   RenderCurrentView(true);

   if(wasPlaying && g_currentDisplay < g_totalBars)
   {
      g_isPlaying = true;
      g_lastPlayMs = GetTickCount64(); 
      ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PAUSE");
      ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrFireBrick);
   }
   else
   {
      ObjectSetString(0, "rep_btn_play", OBJPROP_TEXT, "PLAY");
      ObjectSetInteger(0, "rep_btn_play", OBJPROP_BGCOLOR, clrForestGreen);
   }
}

void SetSpeed(string activeBtn, double mult)
{
   g_speedMult = mult;
   for(int i = 0; i < ArraySize(SPEED_BTNS); i++)
   {
      color c = (SPEED_BTNS[i] == activeBtn) ? clrDodgerBlue : clrDimGray;
      ObjectSetInteger(0, SPEED_BTNS[i], OBJPROP_BGCOLOR, c);
      ObjectSetInteger(0, SPEED_BTNS[i], OBJPROP_STATE, false);
   }
   
   g_lastPlayMs = GetTickCount64();
   UpdateStatusLabel("Speed: " + DoubleToString(mult,1) + "x");
}

void CreateUI(datetime defaultStart)
{
   ObjectsDeleteAll(0, "rep_");

   ObjectCreate(0, "rep_bg", OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "rep_bg", OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, "rep_bg", OBJPROP_XDISTANCE, repPanelX1);
   ObjectSetInteger(0, "rep_bg", OBJPROP_YDISTANCE, repPanelY1);
   ObjectSetInteger(0, "rep_bg", OBJPROP_XSIZE, repPanelX2 - repPanelX1);
   ObjectSetInteger(0, "rep_bg", OBJPROP_YSIZE, repPanelY2 - repPanelY1);
   ObjectSetInteger(0, "rep_bg", OBJPROP_BGCOLOR, C'20,24,30');
   ObjectSetInteger(0, "rep_bg", OBJPROP_BORDER_COLOR, clrSilver);
   ObjectSetInteger(0, "rep_bg", OBJPROP_BACK, false);
   ObjectSetInteger(0, "rep_bg", OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, "rep_bg", OBJPROP_SELECTED, false);
   ObjectSetInteger(0, "rep_bg", OBJPROP_ZORDER, 10); // Tambahan z-index

   CreateLabel("rep_title", 20, 26, "MARKET REPLAY — " + g_customSymbol, clrWhite, 10);
   CreateLabel("rep_lbl_start", 20, 53, "Start:", clrSilver, 9);
   
   ObjectCreate(0, "rep_edit_startdate", OBJ_EDIT, 0, 0, 0);
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_XDISTANCE, 55);
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_YDISTANCE, 50);
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_XSIZE, 105);
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_YSIZE, 22);
   ObjectSetString(0, "rep_edit_startdate", OBJPROP_TEXT, TimeToString(defaultStart, TIME_DATE|TIME_MINUTES));
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_BGCOLOR, clrBlack);
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, "rep_edit_startdate", OBJPROP_ZORDER, 20); // Tambahan z-index

   CreateButton("rep_btn_select",  165, 50, 62, 22, "SELECT", clrGoldenrod, clrWhite);
   CreateButton("rep_btn_loaddata",231, 50, 75, 22, "LOAD DATA", clrTeal, clrWhite);
   CreateButton("rep_btn_reset",   309, 50, 61, 22, "RESET", clrSlateGray, clrWhite);

   CreateButton("rep_btn_back10", 20,  84, 58, 32, "-10", clrBrown, clrWhite);
   CreateButton("rep_btn_prev",   90,  84, 52, 32, "<<", clrDimGray, clrWhite);
   CreateButton("rep_btn_play",   154, 84, 82, 32, "PLAY", clrForestGreen, clrWhite);
   CreateButton("rep_btn_next",   248, 84, 52, 32, ">>", clrMidnightBlue, clrWhite);
   CreateButton("rep_btn_skip10", 312, 84, 58, 32, "+10", clrDarkOrange, clrWhite);

   CreateButton("rep_btn_sp05", 20,  126, 53, 26, "0.5x", clrDimGray, clrWhite);
   CreateButton("rep_btn_sp1",  79,  126, 53, 26, "1x",   clrDodgerBlue, clrWhite);
   CreateButton("rep_btn_sp2",  138, 126, 53, 26, "2x",   clrDimGray, clrWhite);
   CreateButton("rep_btn_sp5",  197, 126, 53, 26, "5x",   clrDimGray, clrWhite);
   CreateButton("rep_btn_sp10", 256, 126, 53, 26, "10x",  clrDimGray, clrWhite);
   CreateButton("rep_btn_sp20", 315, 126, 53, 26, "20x",  clrDimGray, clrWhite);

   ObjectCreate(0, "rep_progress_bg", OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_XDISTANCE, 20);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_YDISTANCE, 162);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_XSIZE, PROGRESS_WIDTH);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_YSIZE, 14);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_BGCOLOR, clrBlack);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_BORDER_COLOR, clrSilver);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_SELECTED, false);
   ObjectSetInteger(0, "rep_progress_bg", OBJPROP_ZORDER, 20); // Tambahan z-index

   ObjectCreate(0, "rep_progress_fill", OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_XDISTANCE, 20);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_YDISTANCE, 162);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_XSIZE, 1);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_YSIZE, 14);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_BGCOLOR, clrDodgerBlue);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_BORDER_COLOR, clrNONE);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_SELECTED, false);
   ObjectSetInteger(0, "rep_progress_fill", OBJPROP_ZORDER, 30); // Tambahan z-index

   CreateLabel("rep_lbl_status", 20, 182, "Status: Ready", clrYellow, 9);
   CreateLabel("rep_lbl_limit",  20, 204, "Min Start: -", clrDarkOrange, 8);

   ChartRedraw(0);
}

void CreateButton(string name, int x, int y, int w, int h, string text, color bg, color fg)
{
   ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, name, OBJPROP_COLOR, fg);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 20); // Tambahan z-index
}

void CreateLabel(string name, int x, int y, string text, color clr, int fontsize)
{
   ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontsize);
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 20); // Tambahan z-index
}
//+------------------------------------------------------------------+