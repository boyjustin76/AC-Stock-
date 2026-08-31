/*  A3 준비 — 폰트 이름과 셰이프/텍스트 API 를 실측한다.

    폰트는 짐작하면 안 된다. 렌더러 테마는 CSS 이름('Gmarket Sans')을 쓰지만
    AE 의 TextDocument.font 는 **PostScript 이름**을 받는다. 프리미어에서 속성 이름을
    `비율` 로 짐작했다가 틀린 것과 같은 자리다. 여기서 목록을 뽑아 두고 A3 이 그걸 쓴다.
*/
$.evalFile(new File(String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/") + "/_lib.jsx"));
logTo("a3_probe");

say("잡", "A3 준비 — 폰트 · API 실측");
say("AE", app.version);

/* ---- 폰트 ---- */
probe("app.fonts 있나", function () { return typeof app.fonts; });
var hits = [];
probe("폰트 열거", function () {
    if (!app.fonts || !app.fonts.allFonts) return "app.fonts.allFonts 없음";
    var all = app.fonts.allFonts;
    var n = 0;
    for (var i = 0; i < all.length; i++) {
        var f = all[i];
        var fam = String(f.familyName || "");
        var ps  = String(f.postScriptName || "");
        if (/gmarket/i.test(fam) || /gmarket/i.test(ps) ||
            /score|dream/i.test(fam) || /pretendard/i.test(fam)) {
            hits.push(ps + "\t(" + fam + " / " + f.styleName + ")");
        }
        n++;
    }
    return "전체 " + n + "개 중 후보 " + hits.length + "개";
});
for (var k = 0; k < hits.length; k++) say("  폰트 " + (k + 1), hits[k]);

/* ---- 만들기 API ---- */
closeQuietly();
probe("newProject", function () { app.newProject(); return "ok"; });
var comp = null;
probe("addComp", function () {
    comp = app.project.items.addComp("probe", 1080, 1080, 1, 176 / 30, 30);
    return comp.name;
});

probe("addText", function () {
    var t = comp.layers.addText("익절");
    var d = t.property("ADBE Text Properties").property("ADBE Text Document").value;
    d.fontSize = 40;
    if (hits.length) d.font = hits[0].split("\t")[0];
    t.property("ADBE Text Properties").property("ADBE Text Document").setValue(d);
    var r = t.sourceRectAtTime(0, false);
    return "익절 40px 잉크 " + Math.round(r.width * 100) / 100 + "x" + Math.round(r.height * 100) / 100 +
           " (left " + Math.round(r.left * 100) / 100 + ", top " + Math.round(r.top * 100) / 100 + ") · font=" + d.font;
});

probe("addShape", function () {
    var s = comp.layers.addShape();
    var g = s.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    var c = g.property("ADBE Vectors Group");
    var pathProp = c.addProperty("ADBE Vector Shape - Group");
    var sh = new Shape();
    sh.vertices = [[0, 0], [100, 0], [100, 50], [0, 50]];
    sh.closed = true;
    pathProp.property("ADBE Vector Shape").setValue(sh);
    var fill = c.addProperty("ADBE Vector Graphic - Fill");
    fill.property("ADBE Vector Fill Color").setValue([0.08, 1, 0.21, 1]);
    return "셰이프 + 패스 + 칠 됐다";
});

probe("importFile(base.png)", function () {
    var f = new File(LAB + "/base.png");
    if (!f.exists) return "base.png 이 없다 — " + LAB + "/base.png";
    var io = new ImportOptions(f);
    var it = app.project.importFile(io);
    var L = comp.layers.add(it);
    return it.name + " · " + it.width + "x" + it.height + " · 레이어 " + L.name;
});

probe("mogrt API 셋", function () {
    var t = [];
    t.push("motionGraphicsTemplateName=" + (typeof comp.motionGraphicsTemplateName));
    t.push("exportAsMotionGraphicsTemplate=" + (typeof comp.exportAsMotionGraphicsTemplate));
    var op = comp.layer(1).property("ADBE Transform Group").property("ADBE Opacity");
    t.push("canAddToMotionGraphicsTemplate=" + (typeof op.canAddToMotionGraphicsTemplate));
    return t.join(" · ");
});

probe("컴포지션 상태", function () { return dumpComp(comp); });

/* 뒷정리 — 프로브 프로젝트는 저장하지 않는다 */
closeQuietly();

flush();
done("실측 끝");
