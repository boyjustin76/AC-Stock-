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

var AEP = LAB + "/pack/" + SPEC.slug + "/" + SPEC.slug + ".aep";

say("잡", "B3 프레임 뽑기 — " + SPEC.slug + " / " + SPEC.cut);

closeQuietly();
probe("열기", function () {
    var f = new File(AEP);
    if (!f.exists) throw new Error("없다: " + AEP);
    app.open(f);
    return app.project.numItems + "항목";
});

/*  컷 하나면 그 컴포지션만, all 이면 전부 — 프로젝트를 한 번만 열면 되니 훨씬 싸다.  */
var comps = [];
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (!(it instanceof CompItem)) continue;
    if (SPEC.cut === "all" || it.name === SPEC.slug + " " + SPEC.cut) comps.push(it);
}
if (!comps.length) { flush(); return fail("컴포지션이 없다: " + SPEC.slug + " " + SPEC.cut); }

var total = 0;
for (var c = 0; c < comps.length; c++) {
    var comp = comps[c];
    var cutId = comp.name.replace(SPEC.slug + " ", "");
    var DIR = LAB + "/ae/frames/" + cutId;
    var d = new Folder(DIR);
    if (!d.exists) d.create();

    /*  컷마다 길이가 달라 고정 프레임 번호는 못 쓴다. 길이의 25·50·75·95% 를 뽑는다.
        컷 하나만 지정했을 때는 _build.txt 세 번째 칸으로 직접 줄 수 있다.  */
    var list;
    if (SPEC.cut !== "all" && SPEC.frames) {
        list = SPEC.frames.split(",");
    } else {
        var n = Math.round(comp.duration * comp.frameRate);
        list = [Math.round(n * 0.25), Math.round(n * 0.5), Math.round(n * 0.75), Math.round(n * 0.95)];
    }
    var okN = 0, got = [];
    for (var k = 0; k < list.length; k++) {
        var fn = Number(list[k]);
        try {
            comp.saveFrameToPng(fn / comp.frameRate, new File(DIR + "/f" + fn + ".png"));
            $.sleep(400);          /* 200ms 는 첫 프레임에서 모자랐다 (파일럿 실측) */
            okN++; got.push(fn);
        } catch (e) { got.push("f" + fn + " ERR " + e.toString()); }
    }
    total += okN;
    say("  " + cutId, okN + "/" + list.length + " · " + got.join(","));
}
say("뽑음", total + "장 → " + LAB + "/ae/frames/");

flush();
return done(total + "장");
}
__main();
