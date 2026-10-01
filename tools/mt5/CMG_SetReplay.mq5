//+------------------------------------------------------------------+
//| CMG_SetReplay.mq5 - 리플레이 시작 시각을 밖에서 정해 준다          |
//|                                                                    |
//| Market Replay Tool(무료·소스공개, MQL5 코드베이스 76669)은 상태를   |
//| 전역 변수 셋으로 주고받는다:                                        |
//|   RepStartDate_<심볼> · RepLastTime_<심볼> · RepIsPlaying_<심볼>    |
//| EA 는 **붙는 순간** 이 값을 읽는다. 그래서 값을 넣고 EA 를 다시     |
//| 붙이면 원하는 시각에서 시작한다.                                    |
//|                                                                    |
//| 왜 필요한가: MCP 로 EA 인자를 줄 때 **공백이 금지**라 날짜+시각     |
//| ("2026.09.21 14:30")을 못 넘긴다(09-29 실측). 이 스크립트는 공백 대신|
//| T 를 쓴다 — 촬영 큐시트의 시각을 그대로 넣어 줄 수 있다.            |
//+------------------------------------------------------------------+
#property script_show_inputs

input string InpSymbol = "";                    // 리플레이 심볼 (빈칸이면 지금 차트)
input string InpTime   = "2026.09.21T14:30";    // 시작 시각 — 공백 대신 T
input bool   InpPlay   = false;                 // 붙자마자 재생할까

void OnStart()
  {
   string sym = (StringLen(InpSymbol) > 0) ? InpSymbol : _Symbol;
   string t = InpTime;
   StringReplace(t, "T", " ");
   datetime when = StringToTime(t);
   if(when <= 0)
     {
      Print("CMG_SetReplay: 시각을 못 읽었다 — ", InpTime);
      return;
     }
   GlobalVariableSet("RepStartDate_" + sym, (double)when);
   GlobalVariableSet("RepLastTime_" + sym, (double)when);      // 여기서부터 보여 준다
   GlobalVariableSet("RepIsPlaying_" + sym, InpPlay ? 1.0 : 0.0);
   PrintFormat("CMG_SetReplay: %s → %s (재생=%s)", sym, TimeToString(when, TIME_DATE | TIME_MINUTES),
               InpPlay ? "예" : "아니오");
  }
