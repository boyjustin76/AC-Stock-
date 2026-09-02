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

function __main() {

var AEP = LAB + "/pack/" + SPEC.slug + "/" + SPEC.slug + ".aep";
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
    say(k + " " + L.name, root ? "셰이프" : L.matchName);
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
