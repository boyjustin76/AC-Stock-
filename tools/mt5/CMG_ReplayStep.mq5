//+------------------------------------------------------------------+
//|  CMG_ReplayStep.mq5 — 리플레이를 MT5 안에서 감는다                |
//+------------------------------------------------------------------+
//  Replay_Tool_CMG 가 붙은 차트에 이 스크립트를 얹으면, 붙어 있는 리플레이에
//  "몇 봉 옮겨라" 는 신호를 보낸다. 밖에서 키를 흉내 내지 않고 확인·자동화하기 위한 통로다.
//  (키 흉내는 금지 — 포커스를 뺏기면 남의 창에 글자가 찍힌다. 2026-09-29 사고)
//
//  쓰는 법: MCP chart_add_script 로 이 스크립트를 얹고 Steps 를 준다.
//           Steps 가 음수면 뒤로 감는다. Repeat 번 되풀이한다.
//+------------------------------------------------------------------+
// (입력 창은 띄우지 않는다 — MCP 로 값을 넘겨 자동으로 돈다)
#property strict

input int Steps    = -1;    // 한 번에 옮길 봉 수 (음수 = 뒤로)
input int Repeat   = 1;     // 몇 번 되풀이할지
input int DelayMs  = 250;   // 사이에 쉬는 시간 (리플레이가 다 그릴 때까지)
input int CueIndex = -1;    // 0 이상이면 봉 감기 대신 '그 번째 장면' 으로 간다 (큐시트 순서, 0부터)
input int ProbeK   = -1;    // 0 이상이면 ChartNavigate(CHART_END,-K) 를 걸고 결과를 파일에 적는다 (확인용)
input int Action   = 0;     // 2 = 지금 시각까지 다시 받기 · 3 = 조작판 숨김 · 4 = 조작판 보임

void OnStart()
{
   ChartSetInteger(ChartID(), CHART_BRING_TO_TOP, true);   // 차트를 앞으로 (시장 탭 등에 가려져 있을 때)

   if(ProbeK >= 0)
   {
      //  화면을 어디에 두는지 직접 재 본다 — 문서만 보고 짐작하다 두 번 틀렸다(09-30).
      long before = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
      ChartNavigate(0, CHART_END, -ProbeK);
      ChartRedraw(0);
      Sleep(700);
      long fv = ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
      long w  = ChartGetInteger(0, CHART_WIDTH_IN_BARS);
      int fh = FileOpen("cmg_nav_probe.txt", FILE_WRITE | FILE_TXT | FILE_ANSI);
      if(fh != INVALID_HANDLE)
      {
         FileWrite(fh, StringFormat("K=%d BEFORE=%d FV=%d W=%d", ProbeK, (int)before, (int)fv, (int)w));
         FileClose(fh);
      }
      return;
   }
   if(Action == 2) { EventChartCustom(ChartID(), 2, 0, 0.0, ""); Print("다시 받기 신호"); return; }
   if(Action == 3) { EventChartCustom(ChartID(), 3, 1, 0.0, ""); Print("조작판 숨김 신호"); return; }
   if(Action == 4) { EventChartCustom(ChartID(), 3, 0, 0.0, ""); Print("조작판 보임 신호"); return; }

   if(CueIndex >= 0)
   {
      EventChartCustom(ChartID(), 1, (long)CueIndex, 0.0, "");
      Print("CMG_ReplayStep: 장면 ", CueIndex, " 로 보냈다");
      return;
   }
   for(int i = 0; i < Repeat; i++)
   {
      EventChartCustom(ChartID(), 0, (long)Steps, 0.0, "");
      Sleep(DelayMs);
   }
   Print("CMG_ReplayStep: ", Steps, " 봉 x ", Repeat, " 회 보냈다");
}
