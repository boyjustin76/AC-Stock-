/*  C5b — 전체 컴포지션에서 소스의 '필수 속성'이 왜 canAdd=false 인지 구조를 잰다 (1회용 실측).
    레이어 하나의 ADBE Layer Overrides 아래를 두 단계까지 펼쳐 종류·matchName·canAdd 를 적는다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c5b");
var AEP = LAB + "/pack/trad_rr/trad_rr.aep";

function __main() {
say("잡", "C5b 필수 속성 구조 실측");
closeQuietly();
probe("열기", function () { app.open(new File(AEP)); return "열림"; });
var main = null;
for (var i = 1; i <= app.project.numItems; i++) { var c = app.project.item(i); if (c instanceof CompItem && c.name === "차11-4 손익비 (전통)") main = c; }
if (!main) { flush(); return fail("전체 컴포지션 없음"); }
say("템플릿 이름", main.motionGraphicsTemplateName);
say("EGP 컨트롤 수", main.motionGraphicsTemplateControllerCount);
var L = main.layer("익절 낙관");
say("레이어", L.name + " · source=" + (L.source ? L.source.name : "-"));
var eo = L.property("ADBE Layer Overrides");
say("Overrides", "type=" + eo.propertyType + " match=" + eo.matchName + " n=" + eo.numProperties);
function kind(p) {
    var t = p.propertyType === PropertyType.PROPERTY ? "PROPERTY" : (p.propertyType === PropertyType.INDEXED_GROUP ? "INDEXED_GROUP" : "NAMED_GROUP");
    return t;
}
for (var k = 1; k <= eo.numProperties; k++) {
    var p = eo.property(k);
    var line = k + " " + p.name + " · " + kind(p) + " · match=" + p.matchName;
    try { line += " · canAdd=" + p.canAddToMotionGraphicsTemplate(main); } catch (e) { line += " · canAdd ERR " + e; }
    try { if (p.propertyType === PropertyType.PROPERTY) line += " · pvt=" + p.propertyValueType + " · val=" + String(p.value).substr(0, 30); } catch (e2) {}
    out.push("    " + line);
    if (p.numProperties) {
        for (var q = 1; q <= p.numProperties; q++) {
            var s = p.property(q), l2 = "      " + q + " " + s.name + " · " + kind(s) + " · match=" + s.matchName;
            try { l2 += " · canAdd=" + s.canAddToMotionGraphicsTemplate(main); } catch (e3) { l2 += " · canAdd ERR " + e3; }
            out.push(l2);
        }
    }
}
/* 비교 — 전체 컴포지션 자신의 속성은 열리는가 (레이어 불투명도) */
probe("대조: 레이어 불투명도 canAdd", function () { return String(L.property("ADBE Transform Group").property("ADBE Opacity").canAddToMotionGraphicsTemplate(main)); });
/* 소스 컴포지션 쪽 — 거기서는 여전히 열려 있나 */
var src = L.source;
probe("대조: 소스 템플릿 컨트롤 수", function () { return src.motionGraphicsTemplateControllerCount + " · 이름 " + src.motionGraphicsTemplateName; });
flush();
return done("실측 끝");
}
__main();
