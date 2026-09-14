/*  C8q — 열린 프로젝트를 **저장하지 않고** 닫은 뒤 AE 를 스스로 끈다.
    프리미어 다이내믹 링크가 띄우고 남긴 AE 에 BridgeTalk 잡이 들어가 응답이 끊긴 적이 있다(2026-09-14 15:00, NO_RESPONSE 600s).
    강제 종료 대신 이 잡으로 정상 종료시키고, 다음 잡은 BridgeTalk 이 새로 띄운 AE 에서 돌린다.
    종료는 1.5초 뒤로 예약한다 — 그래야 이 잡의 결과가 먼저 돌아간다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c8q");

function __main() {
say("잡", "C8q 저장 없이 닫고 AE 종료");
probe("닫기 전", function () { return (app.project.file ? app.project.file.fsName : "(저장 안 된 프로젝트)") + " · dirty=" + app.project.dirty + " · 항목 " + app.project.numItems; });
closeQuietly();
probe("종료 예약", function () { app.scheduleTask("app.quit();", 1500, false); return "1.5초 뒤 app.quit()"; });
flush();
return done("저장 없이 닫음 · 종료 예약");
}
__main();
