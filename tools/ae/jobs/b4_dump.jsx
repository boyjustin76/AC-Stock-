/*  B4 — 지어진 컴포지션의 셰이프 속을 덤프한다.
;
    "왜 이 색이 아닌가" 를 짐작으로 좁히지 않기 위한 도구다.
    _build.txt 의 <슬러그> <컷> 을 읽어 그 컴포지션의 레이어·그룹·칠·획을 훑는다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("b4");

var SPEC = (function () {
    var f = new File(LAB + "/ae/_build.txt");
    f.open("r"); var t = f.read(); f.close();
    var p = String(t).replace(/^\s+|\s+$/g, "").split(/\s+/);
    return { slug: p[0], cut: p[1] };
})();
/* 꾸러미 이름(ch11-4_ae)이 좌표 파일에 들어 있다 — 최상위에서 읽어야 살아남는다 */
$.evalFile(new File(LAB + "/ae/" + SPEC.slug + ".jsx"));

function __main() {

var AEP = LAB + "/pack/" + (typeof SCENE !== "undefined" && SCENE.packName ? SCENE.packName : SPEC.slug)
        + "/" + SPEC.slug + ".aep";
var NAME = SPEC.slug + " " + SPEC.cut;
say("잡", "B4 덤프 — " + NAME);

closeQuietly();
probe("열기", function () { app.open(new File(AEP)); return app.project.numItems + "항목"; });

var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션이 없다: " + NAME); }

function c255(v) {
    if (!v || v.length == null) return String(v);
    var o = [];
    for (var i = 0; i < Math.min(3, v.length); i++) o.push(Math.round(v[i] * 255));
    return o.join(",");
}
/** 무효값이면 던지는 속성을 안전하게 읽는다 */
function at(prop, t) {
    try { return String(prop.valueAtTime(t, false)); }
    catch (e) { return "ERR(" + String(e).split(String.fromCharCode(10)).join(" ").substr(0, 44) + ")"; }
}
function walk(grp, indent) {
    var t = [];
    for (var i = 1; i <= grp.numProperties; i++) {
        var p = grp.property(i);
        var line = indent + i + " " + p.name + " [" + p.matchName + "]";
        if (p.matchName === "ADBE Vector Graphic - Fill") {
            line += "  색=" + c255(p.property("ADBE Vector Fill Color").value)
                  + " 불투명도=" + p.property("ADBE Vector Fill Opacity").value;
        } else if (p.matchName === "ADBE Vector Graphic - Stroke") {
            line += "  색=" + c255(p.property("ADBE Vector Stroke Color").value)
                  + " 굵기=" + p.property("ADBE Vector Stroke Width").value
                  + " 불투명도=" + p.property("ADBE Vector Stroke Opacity").value;
        } else if (p.matchName === "ADBE Vector Shape - Rect") {
            /*  표현식이 무효값을 내면 .value 를 읽는 것만으로 던진다
                ("0으로 나누었는지 확인하십시오"). 시점을 바꿔 가며 안전하게 읽는다.  */
            var sz = p.property("ADBE Vector Rect Size");
            line += "  크기" + (sz.expressionEnabled ? "(식)" : "") + "=" + at(sz, 0) + " / 끝 " + at(sz, comp.duration - 0.1);
        }
        t.push(line);
        if (p.matchName === "ADBE Vector Group") t = t.concat(walk(p.property("ADBE Vectors Group"), indent + "    "));
    }
    return t;
}

for (var k = 1; k <= comp.numLayers; k++) {
    var L = comp.layer(k);
    var root = null;
    try { root = L.property("ADBE Root Vectors Group"); } catch (e) {}
    /*  글자 레이어는 잉크 박스·앵커·위치를 함께 낸다 — 정렬이 맞는지 보려면 이 셋이 필요하다.
        컴포지션 좌표에서 잉크 왼끝 = 위치 - 앵커 + r.left 다.  */
    var extra = "";
    if (L.matchName === "ADBE Text Layer") {
        try {
            var t = comp.duration * 0.6;
            var r = L.sourceRectAtTime(t, false);
            var an = L.property("ADBE Transform Group").property("ADBE Anchor Point").valueAtTime(t, false);
            var po = L.property("ADBE Transform Group").property("ADBE Position").valueAtTime(t, false);
            var rd = function (n) { return Math.round(n * 10) / 10; };
            extra = "  잉크(left " + rd(r.left) + " w " + rd(r.width) + ")"
                  + " 앵커 " + rd(an[0]) + " 위치 " + rd(po[0])
                  + " → 화면 왼끝 " + rd(po[0] - an[0] + r.left);
            /* 실제로 구워진 식을 봐야 한다 — 소스가 맞아도 지어진 게 다를 수 있다 */
            var ex = String(L.property("ADBE Transform Group").property("ADBE Position").expression);
            var m = ex.split(String.fromCharCode(10));
            var tag = "";
            for (var q = 0; q < m.length; q++) if (m[q].indexOf("정렬") >= 0) tag = m[q];
            extra += "\n        " + (tag || "(정렬 주석 없음)") + "\n        식: " + m[m.length - 1];
        } catch (e) { extra = "  ERR " + e.toString().substr(0, 40); }
    }
    say(k + " " + L.name, (root ? "셰이프" : L.matchName) + extra);
    if (root) {
        var rows = walk(root, "      ");
        for (var r = 0; r < rows.length; r++) out.push(rows[r]);
        flush();
    }
}

flush();
return done(comp.numLayers + "레이어 덤프");
}
__main();
