/*  A2 — 컴포지션 생성 + .aep 저장.  검증(재열기)은 a2_verify 가 따로 한다.

    매뉴얼 A2 판정: 1080×1080 / 30fps / 5.8667s(176f) 정확히.
    176/30 은 5.86666… 라 부동소수점이 남는다. **저장한 뒤 다시 열어 프레임 수로 판정한다** —
    duration 문자열 비교는 하지 않는다.
*/
$.evalFile(new File(String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/") + "/_lib.jsx"));
logTo("a2");

var NAME   = "차11-4_컷2_손익비";
var W = 1080, H = 1080, FPS = 30, FRAMES = 176;
var AEP    = LAB + "/pilot.aep";

say("잡", "A2 컴포지션 생성");
say("AE", app.version);

closeQuietly();

probe("app.newProject", function () { app.newProject(); return app.project ? "프로젝트 생김" : "null"; });

var comp = null;
probe("addComp", function () {
    comp = app.project.items.addComp(NAME, W, H, 1, FRAMES / FPS, FPS);
    return comp ? comp.name : "null";
});
if (!comp) { flush(); return fail("컴포지션이 안 만들어졌다"); }

say("생성 직후", dumpComp(comp));

/*  저장 전에 기존 파일을 지운다 — 프리미어 M5 에서 앱이 출력 파일을 붙들고 있어
    saveAs 가 false 를 준 전례가 있다. AE 는 다르겠지만 같은 값으로 막아 둔다.  */
probe("기존 pilot.aep 삭제", function () {
    var f = new File(AEP);
    if (!f.exists) return "없었다";
    return f.remove() ? "지웠다" : "못 지웠다(누가 붙들고 있다)";
});

probe("project.save", function () {
    app.project.save(new File(AEP));
    return "호출됨";
});

probe("파일 확인", function () {
    var f = new File(AEP);
    return f.exists ? f.length + " bytes" : "파일이 없다";
});
say("project.file", app.project.file ? String(app.project.file.fsName) : "null");

flush();
done("저장까지 했다. 판정은 a2_verify 가 재열기로 한다");
