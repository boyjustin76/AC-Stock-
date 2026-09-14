/*  C8 — 열린 프로젝트를 **저장하지 않고** 닫는다.
    c7(문구 늘림 시험)이 문구를 바꾼 채 남겨 둔 프로젝트를, 누가 AE 에서 실수로 저장하지 않게 정리할 때 쓴다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c8");

function __main() {
say("잡", "C8 저장 없이 닫기");
probe("닫기 전", function () { return (app.project.file ? app.project.file.fsName : "(새 프로젝트)") + " · dirty=" + app.project.dirty; });
closeQuietly();
probe("닫은 뒤", function () { return (app.project.file ? app.project.file.fsName : "(빈 새 프로젝트)") + " · 항목 " + app.project.numItems; });
flush();
return done("저장 없이 닫음");
}
__main();
