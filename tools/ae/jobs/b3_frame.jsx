/*  B3 — 지은 컴포지션에서 프레임을 뽑는다. 판정용이다.

    렌더큐는 쓰지 않는다 — 한국어 판 출력 템플릿에 PNG 가 없어 .mp4 가 나오고,
    두 번째부터는 덮어쓰기 대화상자(모달)가 떠서 잡을 죽인다(파일럿에서 두 번 물렸다).
    comp.saveFrameToPng 로 뽑는다.

    저장 직후 File.length 는 낡은 값을 준다. 그래서 잠깐 재우고, 최종 판정은 밖에서 한다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("b3");

var SPEC = (function () {
    var f = new File(LAB + "/ae/_build.txt");
    f.open("r"); var t = f.read(); f.close();
    var p = String(t).replace(/^\s+|\s+$/g, "").split(/\s+/);
    return { slug: p[0], cut: p[1], frames: p[2] || "30,90,120,155" };
})();

function __main() {

var AEP = LAB + "/ae/" + SPEC.slug + ".aep";
var DIR = LAB + "/ae/frames/" + SPEC.cut;
var NAME = SPEC.slug + " " + SPEC.cut;

say("잡", "B3 프레임 뽑기 — " + NAME);

closeQuietly();
probe("열기", function () {
    var f = new File(AEP);
    if (!f.exists) throw new Error("없다: " + AEP);
    app.open(f);
    return app.project.numItems + "항목";
});

var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션이 없다: " + NAME); }
say("컴포지션", dumpComp(comp));

var d = new Folder(DIR);
if (!d.exists) d.create();

var list = SPEC.frames.split(",");
var okN = 0;
for (var k = 0; k < list.length; k++) {
    (function (fn) {
        probe("f" + fn, function () {
            var t = Number(fn) / comp.frameRate;
            var out = new File(DIR + "/f" + fn + ".png");
            comp.saveFrameToPng(t, out);
            $.sleep(600);          /* 200ms 는 첫 프레임에서 모자랐다 (파일럿 실측) */
            okN++;
            return "t=" + (Math.round(t * 1000) / 1000) + "s";
        });
    })(String(Number(list[k])));
}
say("뽑음", okN + "/" + list.length + " → " + DIR);

flush();
return done(okN + "장");
}
__main();
