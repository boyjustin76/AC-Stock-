/*  일부러 모달을 띄워 놓고 멈추는 잡 — 실행기의 실패 경로를 재는 데만 쓴다.

    `alert()` 는 일러스트레이터가 직접 그리는 창이고, 뜨는 순간 **COM 이 거기서 멈춘다**.
    실행기가 시간 제한에 걸려 ① 모달을 찍고 ② 문구를 분류하고 ③ 앱을 죽이는 세 걸음이
    실제로 도는지 이걸로 본다. D 가 1단계에서 "안 본 것" 으로 남긴 자리다
    (log/inbox/2026-09-21_D_공용실행기_남은둘_실측.md — 실제 모달이 떠 있을 때 _fail.png 가 그걸 담는가).

    문구는 표(tools/_com/modal_known.json)에 **일부러 없는 말**로 둔다 — 표에 걸리면
    분류기의 Jev 갈래를 못 재기 때문이다.

    이름 앞의 밑줄은 일부러다 — 판정 줄 래칫(tests/test_verdict_lines.py)이 건너뛴다.
    이 잡은 **끝나면 안 되는 잡**이라 판정 줄을 쓸 자리가 없다.

    쓰는 법:  .\tools\illustrator\run.ps1 _trap_alert -TimeoutSec 45
    결과:     일러스트레이터가 죽는다. 열어 둔 문서가 없을 때만 돌린다.
*/
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;   // 알림을 켜야 창이 뜬다

alert("자동화 시험용 창입니다. 실행기가 이 창을 찍고 저를 죽입니다.");

"여기까지 왔으면 누가 창을 닫은 것이다";
