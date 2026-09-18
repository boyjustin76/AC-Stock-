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
input bool   SelfRemove  = true;            // 찍은 뒤 스스로 빠지기

int    g_step = 0;
string g_name = "CMG_Shot";

int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME, g_name);
   EventSetMillisecondTimer(400);
   return(INIT_SUCCEEDED);
  }

void OnTimer()
  {
//--- 1단계: 배율·자동스크롤을 정하고, 필요한 날짜 이력을 불러 놓는다
   if(g_step == 0)
     {
      if(ShotScale >= 0)
         ChartSetInteger(0, CHART_SCALE, ShotScale);
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
         PrintFormat("CMG_Shot: %s → shift %d (전체 %d봉)", ShotEndTime, shift, bars);
         if(shift > 0)
            ChartNavigate(0, CHART_END, -shift);
        }
      ChartRedraw(0);
      g_step = 2;
      return;
     }
//--- 3단계: 찍는다
   if(g_step == 2)
     {
      bool ok = ChartScreenShot(0, ShotFile, ShotW, ShotH, ALIGN_RIGHT);
      PrintFormat("CMG_Shot: %s %s %dx%d", ok ? "OK" : "FAIL", ShotFile, ShotW, ShotH);
      g_step = 3;
      return;
     }
//--- 4단계: 스스로 빠진다
   EventKillTimer();
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
