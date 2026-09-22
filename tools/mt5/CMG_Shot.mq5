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
#property indicator_plots 0

input string ShotFile    = "cmg_shot.png";  // 파일 이름 (MQL5\Files 안)
input int    ShotW       = 1920;            // 가로 픽셀
input int    ShotH       = 1080;            // 세로 픽셀
input string ShotEndTime = "";              // 오른쪽 끝에 둘 시각 "YYYY.MM.DD HH:MM" (빈칸이면 최신)
input int    ShotScale   = -1;              // 배율 0~5 (-1 이면 그대로)
input string ShotInds    = "";               // 켤 지표 "EMA20+EMA200+ADX" (빈칸이면 그대로). MCP 로 줄 때는 '+' — 쉼표는 잘린다
input bool   ShotRestore = false;            // true 면 찍지 않고 보던 자리(최신)로 되돌리기만 한다
input bool   SelfRemove  = true;            // 찍은 뒤 스스로 빠지기
input bool   KeepInds    = false;           // true 면 얹은 지표를 떼지 않는다 — 밖에서 창을 찍고 차트째 닫을 때
                                            // (떼는 단계가 ~4.8초에 와서, 밖의 캡처가 떼는 도중을 찍었다 — 09-22)

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
      if(StringFind(k, "EMA") == 0)
        {
         int per = (int)StringToInteger(StringSubstr(k, 3));
         if(per <= 0) continue;
         h = iMA(_Symbol, _Period, per, 0, MODE_EMA, PRICE_CLOSE);
         nm = "MA(" + IntegerToString(per) + ")";
        }
      else if(StringFind(k, "MA") == 0 && StringFind(k, "MACD") != 0)
        {
         // 단순 이평 — 차11 '20일 이동평균선' (09-22 다른 회차 검증에서 필요해졌다)
         int per = (int)StringToInteger(StringSubstr(k, 2));
         if(per <= 0) continue;
         h = iMA(_Symbol, _Period, per, 0, MODE_SMA, PRICE_CLOSE);
         nm = "MA(" + IntegerToString(per) + ")";
        }
      else if(k == "BB")
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

int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME, g_name);
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
   return(rates_total);
  }
//+------------------------------------------------------------------+
