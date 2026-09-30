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

void OnStart()
{
   ChartSetInteger(ChartID(), CHART_BRING_TO_TOP, true);   // 차트를 앞으로 (시장 탭 등에 가려져 있을 때)
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
