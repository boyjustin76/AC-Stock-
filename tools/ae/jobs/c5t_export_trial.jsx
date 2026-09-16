/*  C5t — '손익비 · 손절 박스' 만 mogrt 에 푸티지 누락(2)이 적히고 내보낸 뒤 프로젝트가 7항목으로 줄어 남는 원인 가리기.
    **저장하지 않는다.** 시험마다 aep 를 새로 열고, 결과는 <작업실>/trad_rr_exporttest/<시험>/ 에만 쓴다.
      t1 원본 그대로          — 재현되는가
      t2 PNG 두 장을 새로 가져와 레이어 소스 교체 — 푸티지 항목 문제인가
      t3 컴포지션 복제본       — 컴포지션 자체 문제인가
      t4 익절 박스 (대조)      — 같은 방식에서 멀쩡한가
    판정(누락 여부)은 밖에서 zip 안 definition.json 으로 한다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c5t");
var PACK = LAB + "/pack/trad_rr";
var AEP = PACK + "/trad_rr.aep";
var OUTD = LAB + "/trad_rr_exporttest";

function openFresh() {
    if (app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
    app.open(new File(AEP));
}
function compNamed(nm) {
    for (var z = 1; z <= app.project.numItems; z++) {
        var it = app.project.item(z);
        if (it instanceof CompItem && it.name === nm) return it;
    }
    return null;
}
function folderFor(t) {
    var d = new Folder(OUTD + "/" + t);
    if (d.exists) { var old = d.getFiles("*.mogrt"); for (var q = 0; q < old.length; q++) old[q].remove(); } else d.create();
    return d.fsName;
}
function footInfo(c) {
    var t = [];
    for (var i = 1; i <= c.numLayers; i++) {
        var L = c.layer(i);
        if (L.source && L.source instanceof FootageItem) {
            var s = L.source;
            t.push(L.name + "→" + s.name + "#" + s.id + (s.file ? "(" + decodeURI(s.file.name) + (s.footageMissing ? ",없음" : "") + ")" : "(단색)"));
        }
    }
    return t.join(" ; ");
}
function exportTo(c, t) {
    var dir = folderFor(t);
    var before = app.project.numItems;
    var res = c.exportAsMotionGraphicsTemplate(true, dir);
    return "반환 " + res + " · 항목 " + before + "→" + app.project.numItems;
}

function __main() {
say("잡", "C5t 손절 박스 내보내기 원인 시험 (저장 안 함)");
closeQuietly();
app.beginSuppressDialogs();

probe("t1 원본 그대로", function () {
    openFresh();
    var c = compNamed("손익비 · 손절 박스");
    if (!c) throw new Error("없음");
    say("  t1 레이어", footInfo(c));
    return exportTo(c, "t1");
});

probe("t2 PNG 새로 가져와 소스 교체", function () {
    openFresh();
    var c = compNamed("손익비 · 손절 박스");
    var map = { "담채": "sl_box_zone.png", "선": "sl_box_line.png" };
    var done_ = [];
    for (var i = 1; i <= c.numLayers; i++) {
        var L = c.layer(i);
        if (!map[L.name]) continue;
        var it = app.project.importFile(new ImportOptions(new File(PACK + "/footage/" + map[L.name])));
        it.name = "t2_" + map[L.name];
        try { it.mainSource.alphaMode = AlphaMode.STRAIGHT; } catch (e) {}
        L.replaceSource(it, false);
        done_.push(L.name + "→" + it.name + "#" + it.id);
    }
    say("  t2 교체", done_.join(" ; "));
    return exportTo(c, "t2");
});

probe("t3 컴포지션 복제", function () {
    openFresh();
    var c = compNamed("손익비 · 손절 박스");
    var d = c.duplicate();
    d.name = "손익비 · 손절 박스 t3";
    d.motionGraphicsTemplateName = "손익비 · 손절 박스 t3";
    say("  t3 컨트롤 수", d.motionGraphicsTemplateControllerCount);
    return exportTo(d, "t3");
});

probe("t4 익절 박스 (대조)", function () {
    openFresh();
    var c = compNamed("손익비 · 익절 박스");
    say("  t4 레이어", footInfo(c));
    return exportTo(c, "t4");
});

app.endSuppressDialogs(false);
probe("정리: 저장 없이 닫고 다시 열기", function () { openFresh(); return app.project.numItems + "항목"; });
flush();
return done("시험 끝 (저장 안 함)");
}
__main();
