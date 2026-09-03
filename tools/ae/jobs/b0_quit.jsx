/*  B0 — AE 를 완전히 닫는다.
;
    프로젝트만 닫아도 AE 는 푸티지 폴더를 붙들고 있어 파일을 옮기거나 지울 수 없다.
    포터블 시험처럼 **원래 경로를 치워야** 할 때 쓴다.
    다음 잡을 돌리면 BridgeTalk 이 AE 를 다시 띄운다.

    ⚠ 이 잡은 결과를 돌려주지 못한다 — 돌려주기 전에 앱이 죽는다.
       run.ps1 이 타임아웃/빈 결과를 내는 게 정상이다.

    ⚠ **app.quit() 을 스크립트 안에서 바로 부르지 마라.** BridgeTalk 메시지를 처리하는
       도중에 앱이 죽으면 AE 가 정상 종료 기록을 못 남긴다. 다음에 켤 때
       "충돌 복구 옵션" 모달이 떠서 세션을 통째로 막는다 — 사람이 「계속」을 눌러 줄
       때까지 어떤 잡도 못 돈다(실측: 두 번 물렸다).
       scheduleTask 로 스크립트가 끝난 뒤에 끄면 평범한 종료로 처리된다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("b0");

say("잡", "B0 AE 종료");
try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e) {}
say("판정", "닫고 종료한다 (스크립트가 끝난 뒤)");
flush();
/* 800ms 뒤에 끈다 — BridgeTalk 이 답을 돌려주고 스크립트 문맥이 풀린 다음이다 */
app.scheduleTask("app.quit();", 800, false);
