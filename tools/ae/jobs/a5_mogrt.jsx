/*  A5 — .mogrt 내보내기.

    경로 인자를 **반드시** 넣는다. 생략하면 대화상자가 뜰 수 있고, 모달은 잡을 죽인다
    (매뉴얼 §3-6). 이름은 A4 에서 이미 박아 뒀다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("a5");

function __main() {

var AEP  = LAB + "/pilot.aep";
var NAME = "차11-4_컷2_손익비";
var OUT  = LAB + "/차11-4_손익비.mogrt";

say("잡", "A5 mogrt 내보내기");

closeQuietly();
probe("app.open", function () { app.open(new File(AEP)); return "열림"; });

var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션이 없다"); }
say("템플릿 이름", comp.motionGraphicsTemplateName);

probe("기존 mogrt 삭제", function () {
    var f = new File(OUT);
    if (!f.exists) return "없었다";
    return f.remove() ? "지웠다" : "못 지웠다";
});

probe("exportAsMotionGraphicsTemplate", function () {
    return String(comp.exportAsMotionGraphicsTemplate(true, OUT));
});

/* saveFrameToPng 과 같은 함정 — 직후에는 파일 정보가 아직 갱신 전이다 */
$.sleep(400);
probe("파일 확인", function () {
    var f = new File(OUT);
    return f.exists ? f.length + " bytes" : "파일이 없다";
});

flush();
return done("내보냈다. 구조 판정(zip 안 definition.json)은 밖에서 한다");
}
__main();
