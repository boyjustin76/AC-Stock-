/*  일부러 모달을 띄워 놓고 멈추는 잡 — 실행기의 bridge 갈래 실패 경로를 재는 데만 쓴다.

    tools/illustrator/_trap_alert.jsx 의 AE 판(B 가 2단계에서 넘긴 셋 중 1·2번, 2026-09-22).
    잡은 BridgeTalk 으로 AE 안에서 돈다. 그러면 창은 **AE 에 뜨나, 길로 쓰는 포토샵에 뜨나** —
    Read-Modal 이 어느 프로세스를 봐야 하는지를 이걸로 잰다.

    문구는 표(tools/_com/modal_known.json)에 일부러 없는 말로 둔다.
    이름 앞의 밑줄은 일부러다 — 끝나면 안 되는 잡이라 판정 줄 래칫이 건너뛴다.

    쓰는 법:  .\tools\ae\run.ps1 _trap_alert -TimeoutSec 120
    결과:     AE 와 포토샵이 죽는다. 열어 둔 작업이 없을 때만 돌린다.
*/
alert("자동화 시험용 창입니다(AE). 실행기가 이 창을 찍고 저를 죽입니다.");

"여기까지 왔으면 누가 창을 닫은 것이다";
