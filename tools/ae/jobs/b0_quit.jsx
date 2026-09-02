/*  B0 — AE 를 완전히 닫는다.
;
    프로젝트만 닫아도 AE 는 푸티지 폴더를 붙들고 있어 파일을 옮기거나 지울 수 없다.
    포터블 시험처럼 **원래 경로를 치워야** 할 때 쓴다.
    다음 잡을 돌리면 BridgeTalk 이 AE 를 다시 띄운다.

    ⚠ 이 잡은 결과를 돌려주지 못한다 — 돌려주기 전에 앱이 죽는다.
       run.ps1 이 타임아웃/빈 결과를 내는 게 정상이다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("b0");

say("잡", "B0 AE 종료");
try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e) {}
say("판정", "닫고 종료한다");
flush();
app.quit();
