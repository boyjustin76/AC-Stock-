//+------------------------------------------------------------------+
//|  CMG_NavProbe.mq5 — ChartNavigate 가 화면을 어디에 두는지 잰다     |
//+------------------------------------------------------------------+
//  리플레이의 '화면 고정' 을 만들려면 ChartNavigate(CHART_END, -K) 뒤에
//  왼쪽 끝 봉(CHART_FIRST_VISIBLE_BAR)이 얼마가 되는지 정확히 알아야 한다.
//  문서만 보고 짐작하다 두 번 틀렸다(09-30). 그래서 직접 잰다.
//  결과: MQL5\Files\cmg_nav_probe.txt
//+------------------------------------------------------------------+
#property strict

input int K = 100;   // ChartNavigate(0, CHART_END, -K)

void OnStart()
{
   long before = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
   ChartNavigate(0, CHART_END, -K);
   ChartRedraw(0);
   Sleep(700);
   long fv = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
   long w  = ChartGetInteger(0, CHART_WIDTH_IN_BARS);

   int fh = FileOpen("cmg_nav_probe.txt", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) return;
   FileWrite(fh, StringFormat("K=%d BEFORE=%d FV=%d W=%d", K, (int)before, (int)fv, (int)w));
   FileClose(fh);
   PrintFormat("NavProbe K=%d before=%d fv=%d w=%d", K, (int)before, (int)fv, (int)w);
}
