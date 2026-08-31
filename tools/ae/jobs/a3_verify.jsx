/*  A3 판정 — 저장한 .aep 를 **새로 열어** dump 하고, 렌더큐로 프레임을 뽑는다.

    "저장 성공" 은 증거가 아니다(매뉴얼 §3-5). 증거는 둘이다:
      ① 재열기 dump 에 레이어가 전부 있는가
      ② 뽑은 프레임이 렌더러의 같은 시점과 같은 그림인가

    ②의 시점 선택이 중요하다. 바닥이 **reveal 63 고정 스틸**이므로 렌더러와 배경이
    일치하는 구간은 컷② 안에서 reveal 이 63 에 도달한 뒤 스우프 전까지 —
    즉 **4.6 ~ 5.15초** 뿐이다. 그래서 주 대조 시점은 **5.00초(150프레임)** 다.
    (그 앞은 캔들이 계속 자라는데 우리는 리빌 모션을 파일럿에서 포기했다 — 매뉴얼 승인.)
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("a3_verify");

/*  AE 는 최상위 return 을 문법 오류로 잡는다 — 본문을 함수로 감싼다.  */
function __main() {

var AEP   = LAB + "/pilot.aep";
var NAME  = "차11-4_컷2_손익비";
var OUT   = LAB + "/frames";
var SHOTS = [5.00, 4.70, 2.00, 0.60];   /* 첫 번째가 주 대조 시점 */

say("잡", "A3 재열기 검증 + 프레임");

closeQuietly();
probe("app.open", function () {
    var f = new File(AEP);
    if (!f.exists) throw new Error("파일이 없다: " + AEP);
    app.open(f);
    return String(app.project.file.fsName) + " · items " + app.project.numItems;
});

var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션 '" + NAME + "' 이 없다"); }
say("컴포지션", dumpComp(comp));

/* ── 레이어 dump ── */
var names = [], kf = 0, masks = 0;
for (var j = 1; j <= comp.numLayers; j++) {
    var L = comp.layer(j);
    var op = L.property("ADBE Transform Group").property("ADBE Opacity");
    var nk = op.numKeys;
    kf += nk;
    var mp = L.property("ADBE Mask Parade");
    var nm = mp ? mp.numProperties : 0;
    masks += nm;
    names.push(j + ":" + L.name + (nk ? " (불투명도 키 " + nk + ")" : "") + (nm ? " (마스크 " + nm + ")" : ""));
}
for (var n = 0; n < names.length; n++) say("  레이어 " + names[n].split(":")[0], names[n].substr(names[n].indexOf(":") + 1));
say("합계", comp.numLayers + " 레이어 · 불투명도 키 " + kf + " · 마스크 " + masks);

/* ── 렌더큐 ── */
probe("출력 모듈 템플릿", function () {
    var rq = app.project.renderQueue;
    var probe1 = rq.items.add(comp);
    var t = probe1.outputModule(1).templates.join(" | ");
    probe1.remove();
    return t;
});

var pngTpl = null;
probe("PNG 템플릿 고르기", function () {
    var rq = app.project.renderQueue;
    var p1 = rq.items.add(comp);
    var ts = p1.outputModule(1).templates;
    for (var k = 0; k < ts.length; k++) {
        if (/png/i.test(ts[k])) { pngTpl = ts[k]; break; }
    }
    p1.remove();
    return pngTpl ? pngTpl : "PNG 템플릿이 없다 — 아래에서 파일 확장자로만 시도한다";
});

probe("프레임 렌더", function () {
    var d = new Folder(OUT);
    if (!d.exists) d.create();
    var rq = app.project.renderQueue;
    /* 남아 있는 항목을 비운다 */
    while (rq.numItems > 0) rq.item(1).remove();

    for (var s = 0; s < SHOTS.length; s++) {
        var t = SHOTS[s];
        var item = rq.items.add(comp);
        item.timeSpanStart = t;
        item.timeSpanDuration = 1 / comp.frameRate;
        var om = item.outputModule(1);
        if (pngTpl) om.applyTemplate(pngTpl);
        var tag = String(Math.round(t * 100) / 100).replace(".", "_");
        om.file = new File(OUT + "/a3_" + tag + "s_[#####].png");
    }
    rq.render();
    return rq.numItems + "개 항목 렌더 끝";
});

probe("만들어진 파일", function () {
    var d = new Folder(OUT);
    var fs = d.getFiles("*.png");
    var t = [];
    for (var k = 0; k < fs.length; k++) t.push(fs[k].name + " (" + fs[k].length + ")");
    return t.length ? t.join(" | ") : "없다";
});

flush();
return done("재열기 + 프레임까지 끝. 그림 대조는 밖에서 한다");
}
__main();
