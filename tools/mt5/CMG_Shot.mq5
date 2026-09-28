//+------------------------------------------------------------------+
//| CMG_Shot.mq5 - MT5 가 차트를 직접 그려 PNG 로 저장한다              |
//|                                                                    |
//| 창 캡처와 다른 점: 요청한 크기로 **다시 그린다**. 늘린 게 아니라    |
//| 그 해상도로 새로 그리는 것이라 글자·선이 안 뭉갠다.                 |
//| 저장 위치: MQL5\Files\<ShotFile>                                    |
//|                                                                    |
//| 주의: 캔버스를 키우면 봉이 커지는 게 아니라 **봉이 더 많이** 들어온다. |
//|       화면 구도를 그대로 두고 싶으면 필요한 크기를 그대로 달라고 하고,|
//|       봉 수는 ShotScale(0~5) 로 맞춘다.                             |
//|                                                                    |
//| 찍고 나면 스스로 차트에서 빠진다 (사람 차트에 남지 않게).           |
//+------------------------------------------------------------------+
#property indicator_chart_window
//  이평선은 **우리가 직접 그린다** (09-28 검수: 기본 지표를 붙이면 넷이 다 같은 빨강이라 구분이 안 됐고,
//  붙이기가 조용히 실패하는 일도 있었다). 색은 회차 그림에서 흔한 순서 — 주황·파랑·초록·보라.
#property indicator_buffers 4
#property indicator_plots   4
#property indicator_type1   DRAW_LINE
#property indicator_type2   DRAW_LINE
#property indicator_type3   DRAW_LINE
#property indicator_type4   DRAW_LINE
#property indicator_color1  clrDarkOrange
#property indicator_color2  clrDodgerBlue
#property indicator_color3  clrSeaGreen
#property indicator_color4  clrMediumOrchid
#property indicator_width1  2
#property indicator_width2  2
#property indicator_width3  2
#property indicator_width4  2

input string ShotFile    = "cmg_shot.png";  // 파일 이름 (MQL5\Files 안)
input int    ShotW       = 1920;            // 가로 픽셀
input int    ShotH       = 1080;            // 세로 픽셀
input string ShotEndTime = "";              // 오른쪽 끝에 둘 시각 "YYYY.MM.DD HH:MM" (빈칸이면 최신)
input int    ShotScale   = -1;              // 배율 0~5 (-1 이면 그대로)
input string ShotInds    = "";               // 켤 지표 "EMA20+EMA200+ADX" (빈칸이면 그대로). MCP 로 줄 때는 '+' — 쉼표는 잘린다
input bool   ShotRestore = false;            // true 면 찍지 않고 보던 자리(최신)로 되돌리기만 한다
input bool   SelfRemove  = true;            // 찍은 뒤 스스로 빠지기
input bool   Hold        = false;           // true 면 빠지지 않고 1.2초마다 자리를 다시 잡으며, 화면 오른쪽 끝 봉 시각을
                                            // MQL5\Files\cmg_nav_<차트ID>.txt 에 적는다 — 밖의 캡처가 확인하고 찍는다.
                                            // (09-22: 옮긴 뒤 찍기 전에 장중 US100 차트가 최신으로 되돌아가 엉뚱한 날을 찍었다)
input bool   KeepInds    = false;           // true 면 얹은 지표를 떼지 않는다 — 밖에서 창을 찍고 차트째 닫을 때
                                            // (떼는 단계가 ~4.8초에 와서, 밖의 캡처가 떼는 도중을 찍었다 — 09-22)

double g_ma1[], g_ma2[], g_ma3[], g_ma4[];      // 우리가 그리는 이평선 넷
int    g_maH[4] = {INVALID_HANDLE, INVALID_HANDLE, INVALID_HANDLE, INVALID_HANDLE};
string g_maName[4];
int    g_nma = 0;

int    g_step = 0;
string g_name = "CMG_Shot";
int    g_added[8];       // 우리가 얹은 지표 핸들
string g_addedName[8];
int    g_nadd = 0;
long   g_autoscroll0 = -1;   // 원래 자동스크롤 값 — 끝나면 돌려놓는다

//--- 대본이 말한 지표를 그 자리에서 얹는다 (템플릿을 안 만들어도 되게)
void AddInds()
  {
   // 구분자는 '+' 다. MCP chart_add_indicator 는 인자 문자열을 쉼표로 나누기 때문에
   // "ShotInds=EMA200,EMA20,ADX" 는 EMA200 하나만 남는다 (09-22 실측 — 로그에 EMA200 만 얹혔다).
   string s = ShotInds;
   StringReplace(s, ",", "+");
   string parts[];
   int n = StringSplit(s, '+', parts);
   for(int i = 0; i < n; i++)
     {
      string k = parts[i];
      StringTrimLeft(k); StringTrimRight(k);
      int h = INVALID_HANDLE; int sub = 0; string nm = k;
      // 이평선은 OnInit 에서 우리 버퍼로 그린다 — 여기서는 건너뛴다
      if(StringFind(k, "EMA") == 0 || (StringFind(k, "MA") == 0 && StringFind(k, "MACD") != 0))
         continue;
      if(k == "BB")
        {
         h = iBands(_Symbol, _Period, 20, 0, 2.0, PRICE_CLOSE);
         nm = "Bands(20,2.00)";
        }
      else if(k == "ADX")
        {
         h = iADX(_Symbol, _Period, 14);
         sub = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
         nm = "ADX(14)";
        }
      else if(k == "RSI")
        {
         h = iRSI(_Symbol, _Period, 14, PRICE_CLOSE);
         sub = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
         nm = "RSI(14)";
        }
      else if(k == "STOCH")
        {
         h = iStochastic(_Symbol, _Period, 5, 3, 3, MODE_SMA, STO_LOWHIGH);
         sub = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
         nm = "Stoch(5,3,3)";
        }
      else if(k == "MACD")
        {
         h = iMACD(_Symbol, _Period, 12, 26, 9, PRICE_CLOSE);
         sub = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
         nm = "MACD(12,26,9)";
        }
      if(h != INVALID_HANDLE && ChartIndicatorAdd(0, sub, h) && g_nadd < 8)
        {
         g_added[g_nadd] = h; g_addedName[g_nadd] = nm; g_nadd++;
         PrintFormat("CMG_Shot: 지표 %s 를 %d번 창에 얹음", k, sub);
        }
     }
  }

void DropInds()
  {
   for(int i = g_nadd - 1; i >= 0; i--)
     {
      int total = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
      for(int sub = total - 1; sub >= 0; sub--)
         if(ChartIndicatorDelete(0, sub, g_addedName[i])) break;
      IndicatorRelease(g_added[i]);
     }
   g_nadd = 0;
  }

//--- 이평선을 우리 버퍼에 건다 (색이 달라야 대본의 '20일선·60일선' 을 가릴 수 있다)
void SetupMAs()
  {
   SetIndexBuffer(0, g_ma1, INDICATOR_DATA);
   SetIndexBuffer(1, g_ma2, INDICATOR_DATA);
   SetIndexBuffer(2, g_ma3, INDICATOR_DATA);
   SetIndexBuffer(3, g_ma4, INDICATOR_DATA);
   for(int p = 0; p < 4; p++)
     {
      PlotIndexSetInteger(p, PLOT_DRAW_TYPE, DRAW_NONE);   // 쓰지 않는 자리는 안 그린다
      PlotIndexSetDouble(p, PLOT_EMPTY_VALUE, EMPTY_VALUE);
     }
   string s = ShotInds;
   StringReplace(s, ",", "+");
   string parts[];
   int n = StringSplit(s, '+', parts);
   for(int i = 0; i < n && g_nma < 4; i++)
     {
      string k = parts[i];
      StringTrimLeft(k); StringTrimRight(k);
      int per = 0; ENUM_MA_METHOD meth = MODE_SMA;
      if(StringFind(k, "EMA") == 0)
        { per = (int)StringToInteger(StringSubstr(k, 3)); meth = MODE_EMA; }
      else
         if(StringFind(k, "MA") == 0 && StringFind(k, "MACD") != 0)
            per = (int)StringToInteger(StringSubstr(k, 2));
      if(per <= 0) continue;
      int h = iMA(_Symbol, _Period, per, 0, meth, PRICE_CLOSE);
      if(h == INVALID_HANDLE) continue;
      g_maH[g_nma] = h;
      g_maName[g_nma] = (meth == MODE_EMA ? "EMA" : "MA") + IntegerToString(per);
      PlotIndexSetInteger(g_nma, PLOT_DRAW_TYPE, DRAW_LINE);
      PlotIndexSetString(g_nma, PLOT_LABEL, g_maName[g_nma]);
      g_nma++;
     }
   PrintFormat("CMG_Shot: 이평선 %d 개를 직접 그린다", g_nma);
  }

int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME, g_name);
   SetupMAs();
   EventSetMillisecondTimer(1200);
   return(INIT_SUCCEEDED);
  }

void OnTimer()
  {
//--- 1단계: 배율·자동스크롤을 정하고, 필요한 날짜 이력을 불러 놓는다
   if(g_step == 0 && ShotRestore)
     {
      ChartNavigate(0, CHART_END, 0);
      ChartSetInteger(0, CHART_AUTOSCROLL, true);
      ChartRedraw(0);
      Print("CMG_Shot: 보던 자리로 되돌림");
      g_step = 9;
      return;
     }
   if(g_step == 0)
     {
      if(ShotScale >= 0)
         ChartSetInteger(0, CHART_SCALE, ShotScale);
      if(StringLen(ShotInds) > 0)
         AddInds();
      if(StringLen(ShotEndTime) > 0)
        {
         // 자동 스크롤이 켜져 있으면 옮겨 놔도 곧바로 끝으로 되돌아간다
         ChartSetInteger(0, CHART_AUTOSCROLL, false);
         ChartSetInteger(0, CHART_SHIFT, false);
         // 새로 연 차트는 최근 이력만 갖고 있다. 원하는 날짜를 한 번 읽어 내려받게 한다.
         MqlRates rr[];
         CopyRates(_Symbol, _Period, StringToTime(ShotEndTime), 2, rr);
        }
      g_step = 1;
      return;
     }
//--- 2단계: 보는 자리를 옮긴다
   if(g_step == 1)
     {
      if(StringLen(ShotEndTime) > 0)
        {
         datetime t = StringToTime(ShotEndTime);
         int shift = iBarShift(_Symbol, _Period, t, false);
         int bars  = Bars(_Symbol, _Period);
         long fv0 = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
         long au  = ChartGetInteger(0, CHART_AUTOSCROLL);
         bool nav = ChartNavigate(0, CHART_END, -shift);
         ChartRedraw(0);
         long fv1 = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
         PrintFormat("CMG_Shot: %s shift=%d 전체=%d 자동스크롤=%d 첫보임 %d→%d nav=%d err=%d",
                     ShotEndTime, shift, bars, (int)au, (int)fv0, (int)fv1, (int)nav, GetLastError());
        }
      ChartRedraw(0);
      g_step = 2;
      return;
     }
//--- 2-b단계: 이력이 다 붙은 뒤 한 번 더 옮긴다 (한 번만 하면 끝으로 되돌아간다)
   if(g_step == 2 && StringLen(ShotEndTime) > 0)
     {
      int shift2 = iBarShift(_Symbol, _Period, StringToTime(ShotEndTime), false);
      if(shift2 > 0)
         ChartNavigate(0, CHART_END, -shift2);
      ChartRedraw(0);
      g_step = 3;
      return;
     }
//--- 3단계: 옮긴 자리를 다시 못박고 **같은 순간에** 찍는다
//    (배율·템플릿을 건드리면 자리가 풀려 끝으로 돌아가기 때문이다)
   if(g_step == 2 || g_step == 3)
     {
      if(StringLen(ShotEndTime) > 0)
        {
         if(g_autoscroll0 < 0)
            g_autoscroll0 = ChartGetInteger(0, CHART_AUTOSCROLL);
         ChartSetInteger(0, CHART_AUTOSCROLL, false);
         int sh = iBarShift(_Symbol, _Period, StringToTime(ShotEndTime), false);
         if(sh > 0)
            ChartNavigate(0, CHART_END, -sh);
         ChartRedraw(0);
        }
      // ShotFile 이 비면 찍지 않는다 — 자리만 옮겨 두고 밖에서 창을 캡처할 때 쓴다.
      // (ChartScreenShot 은 스크롤 자리를 무시하고 늘 최신 구간을 그린다. 실측 09-18)
      bool ok = (StringLen(ShotFile) > 0)
                ? ChartScreenShot(0, ShotFile, ShotW, ShotH, ALIGN_RIGHT) : true;
      long fv = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
      long vb = ChartGetInteger(0, CHART_VISIBLE_BARS);
      PrintFormat("CMG_Shot: %s %s %dx%d 첫보임=%d 보이는봉=%d",
                  ok ? "OK" : "FAIL", ShotFile, ShotW, ShotH, (int)fv, (int)vb);
      g_step = 9;
      return;
     }
//--- 붙잡기: 자리를 계속 못박고, 지금 보이는 오른쪽 끝 봉의 시각을 적는다 (차트를 닫으면 같이 사라진다)
   if(Hold && StringLen(ShotEndTime) > 0)
     {
      ChartSetInteger(0, CHART_AUTOSCROLL, false);
      int sh = iBarShift(_Symbol, _Period, StringToTime(ShotEndTime), false);
      if(sh > 0)
         ChartNavigate(0, CHART_END, -sh);
      ChartRedraw(0);
      long fv = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
      long vb = ChartGetInteger(0, CHART_VISIBLE_BARS);
      int right = (int)MathMax(0, fv - vb + 1);
      int fh = FileOpen("cmg_nav_" + IntegerToString(ChartID()) + ".txt", FILE_WRITE | FILE_TXT | FILE_ANSI);
      if(fh != INVALID_HANDLE)
        {
         FileWriteString(fh, TimeToString(iTime(_Symbol, _Period, right), TIME_DATE | TIME_MINUTES) + "\n");
         // 둘째 줄: 우리가 **직접 그린 이평선** 과 얹은 지표 — 밖에서 확인한다
         // (이평선은 이제 차트의 지표 목록에 안 나온다. 우리 버퍼로 그리기 때문이다)
         string drew = "";
         for(int q = 0; q < g_nma; q++) drew += (q ? "," : "") + g_maName[q];
         string added = "";
         for(int q = 0; q < g_nadd; q++) added += (q ? "," : "") + g_addedName[q];
         FileWriteString(fh, "MA:" + drew + "|ADD:" + added);
         FileClose(fh);
        }
      return;
     }
//--- 4단계: 스스로 빠진다
   EventKillTimer();
   if(!KeepInds)
      DropInds();
   // 사람 차트를 빌려 썼으면 보던 자리로 돌려놓는다 (찍지 않는 모드는 밖에서 캡처해야 하니 그대로 둔다)
   if(g_autoscroll0 >= 0 && StringLen(ShotFile) > 0)
     {
      ChartNavigate(0, CHART_END, 0);
      ChartSetInteger(0, CHART_AUTOSCROLL, g_autoscroll0);
      ChartRedraw(0);
     }
   if(SelfRemove)
      ChartIndicatorDelete(0, 0, g_name);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

int OnCalculate(const int rates_total,
                const int prev_calculated,
                const int begin,
                const double &price[])
  {
   for(int i = 0; i < g_nma; i++)
     {
      if(g_maH[i] == INVALID_HANDLE) continue;
      double buf[];
      int got = CopyBuffer(g_maH[i], 0, 0, rates_total, buf);
      if(got <= 0) continue;                              // 아직 계산 중이면 다음 틱에 다시 온다
      int off = rates_total - got;
      for(int j = 0; j < rates_total; j++)
        {
         double v = (j >= off) ? buf[j - off] : EMPTY_VALUE;
         if(i == 0) g_ma1[j] = v;
         else if(i == 1) g_ma2[j] = v;
         else if(i == 2) g_ma3[j] = v;
         else g_ma4[j] = v;
        }
     }
   return(rates_total);
  }
//+------------------------------------------------------------------+
