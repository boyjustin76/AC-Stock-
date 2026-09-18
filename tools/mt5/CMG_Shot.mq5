//+------------------------------------------------------------------+
//| CMG_Shot.mq5 - 차트를 MT5 가 직접 그려서 PNG 로 저장한다            |
//| 창 캡처와 달리 요청한 크기로 다시 그리므로 글자·선이 안 뭉갠다.     |
//| 저장 위치: MQL5\Files\<ShotFile>                                    |
//| 찍고 나면 스스로 차트에서 빠진다 (사람 차트에 남지 않게).           |
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_plots 0

input string ShotFile = "cmg_shot.png";   // 파일 이름 (MQL5\Files 안)
input int    ShotW    = 1920;             // 가로 픽셀
input int    ShotH    = 1080;             // 세로 픽셀
input bool   SelfRemove = true;           // 찍은 뒤 스스로 빠지기

bool  g_done = false;
string g_name = "CMG_Shot";

int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME, g_name);
   EventSetMillisecondTimer(300);         // 차트가 다 그려진 뒤에 찍는다
   return(INIT_SUCCEEDED);
  }

void OnTimer()
  {
   if(!g_done)
     {
      ChartRedraw(0);
      bool ok = ChartScreenShot(0, ShotFile, ShotW, ShotH, ALIGN_RIGHT);
      PrintFormat("CMG_Shot: %s %s %dx%d", ok ? "OK" : "FAIL", ShotFile, ShotW, ShotH);
      g_done = true;
      return;                             // 다음 타이머에서 스스로 뺀다
     }
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
