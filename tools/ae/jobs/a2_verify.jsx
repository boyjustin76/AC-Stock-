/*  A2 검증 — 만든 .aep 를 **새로 열어** dump 한다.
    "저장 성공 반환값" 은 증거가 아니다(매뉴얼 §3-5). 재열기 dump 만 증거다.
*/
$.evalFile(new File(String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/") + "/_lib.jsx"));
logTo("a2_verify");

/*  AE 는 최상위 return 을 문법 오류로 잡는다(프리미어 ExtendScript 와 다르다).
    그래서 본문을 함수로 감싼다 — 중간에서 빠져나가는 판정 가드를 쓰려면 이 형태여야 한다.  */
function __main() {

    var AEP    = LAB + "/pilot.aep";
    var NAME   = "차11-4_컷2_손익비";
    var W = 1080, H = 1080, FPS = 30, FRAMES = 176;

    say("잡", "A2 재열기 검증");

    closeQuietly();

    probe("app.open", function () {
        var f = new File(AEP);
        if (!f.exists) throw new Error("파일이 없다: " + AEP);
        app.open(f);
        return app.project.file ? String(app.project.file.fsName) : "열렸는데 file 이 null";
    });

    say("items 수", app.project.numItems);

    var comp = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        say("item " + i, it.typeName + " · " + it.name);
        if (it instanceof CompItem && it.name === NAME) comp = it;
    }
    if (!comp) { flush(); return fail("컴포지션 '" + NAME + "' 이 없다"); }

    say("dump", dumpComp(comp));

    /* 판정 — 하나라도 어긋나면 실패 */
    var bad = [];
    if (comp.width !== W)      bad.push("폭 " + comp.width);
    if (comp.height !== H)     bad.push("높이 " + comp.height);
    if (comp.frameRate !== FPS) bad.push("fps " + comp.frameRate);
    var f176 = Math.round(comp.duration * comp.frameRate);
    if (f176 !== FRAMES)       bad.push("프레임 " + f176);
    if (comp.pixelAspect !== 1) bad.push("픽셀종횡비 " + comp.pixelAspect);

    flush();
    if (bad.length) return fail(bad.join(" / "));
    return done("1080x1080 · 30fps · 176프레임 정확");
}
__main();
