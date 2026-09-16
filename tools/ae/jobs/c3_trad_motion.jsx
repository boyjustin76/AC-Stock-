/*  C3 — 신규안 v2 전통: 애니메이션이 계획돼 있던 소스를 소스마다 컴포지션 + .mogrt 로.

    입력:  <작업실>/pack/trad_motion/footage/motion.jsx   (tools/ae/trad_motion_pack.py)
    출력:  <작업실>/pack/trad_motion/trad_motion.aep      컴포지션 = 소스 하나
           <작업실>/pack/trad_motion/mogrt/<템플릿 이름>.mogrt

    컴포지션은 전부 1920×1080 · 30fps · 5초. 요소는 **틀 스틸과 같은 자리**에 있다 —
    프리미어에 떨구면 틀과 맞는다. '조절' 널의 위치·크기를 Essential Graphics 로 연다.

    모션 셋 (계획: 신규안_v2_전통/결과.md '남은 것')
      stamp   낙관 '쾅'   f0 150% 투명 → f4 94% 착지(선형으로 꽂는다) → f7 102% → f10 100%, 회전 8°→0, 착지 순간 2px 흔들림
      drawon  붓 원       붓길(열린 패스, 합성기와 같은 떨림·시작각·넘침) 트림 0→100 을 알파 매트로 f0→f16
      scroll  족자 펼침   두 축이 가운데서 f0→f3 나타나 f3→f21 양옆으로 벌어지고, 그 사이 종이·글자가 드러난다.
                          글자는 AE 텍스트(궁서) — 문구·크기를 바꾸면 종이 폭(글자폭+120, 최소 700)·높이(크기+30)가 따라온다.
    인트로 길이만큼 보호 구간 마커를 건다 — 프리미어에서 클립을 늘여도 등장 속도가 안 변한다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c3");

var PACK = LAB + "/pack/trad_motion";
var FOOT = PACK + "/footage";
var AEP  = PACK + "/trad_motion.aep";
var MOG  = PACK + "/mogrt";
var FONT = "Gungsuh";
$.evalFile(new File(FOOT + "/motion.jsx"));   /* MOTION */

var FPS = MOTION.fps, DUR = MOTION.dur;
function f(n) { return n / FPS; }
function rgb(r, g, b) { return [r / 255, g / 255, b / 255]; }
var C_INK = rgb(0x1C, 0x1A, 0x17), C_JJOK = rgb(0x2C, 0x33, 0x58), C_WOOD = rgb(0x5A, 0x40, 0x29);
function tr(L) { return L.property("ADBE Transform Group"); }
function fxOf(L) { return L.property("ADBE Effect Parade"); }

/** 차원 수를 몰라도 이징을 건다 (크기 3 · 슬라이더 1 …) */
function setEase(prop, k, infIn, infOut) {
    var dims = [3, 2, 1];
    for (var i = 0; i < dims.length; i++) {
        try {
            var a = [], b = [];
            for (var j = 0; j < dims[i]; j++) { a.push(new KeyframeEase(0, infIn)); b.push(new KeyframeEase(0, infOut)); }
            prop.setTemporalEaseAtKey(k, a, b);
            return true;
        } catch (e) {}
    }
    return false;
}
function lin(prop, k) { prop.setInterpolationTypeAtKey(k, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR); }

var FOLDER_C = null, FOLDER_F = null;
function importPng(rel, name) {
    var fl = new File(FOOT + "/" + rel);
    if (!fl.exists) throw new Error("PNG 없음: " + rel);
    var it = app.project.importFile(new ImportOptions(fl));
    it.name = name;
    it.parentFolder = FOLDER_F;
    try { it.mainSource.alphaMode = AlphaMode.STRAIGHT; } catch (e) {}
    return it;
}
function newComp(title) {
    var c = app.project.items.addComp(title, 1920, 1080, 1, DUR, FPS);
    c.parentFolder = FOLDER_C;
    return c;
}
/** 조절 널 — 앵커 0 이라 자식의 [0,0] 이 곧 널 자리다 */
function controller(comp, name, x, y) {
    var n = comp.layers.addNull(comp.duration);
    n.name = name;
    tr(n).property("ADBE Anchor Point").setValue([0, 0]);
    tr(n).property("ADBE Position").setValue([x, y]);
    return n;
}
function protect(comp, frames, label) {
    var mv = new MarkerValue(label);
    mv.duration = f(frames);
    try { mv.protectedRegion = true; } catch (e) {}
    comp.markerProperty.setValueAtTime(0, mv);
}
var EXPOSED = [];
function expose(comp, prop, name) {
    var r;
    if (!prop.canAddToMotionGraphicsTemplate(comp)) r = "canAdd=false";
    else {
        try { r = prop.addToMotionGraphicsTemplateAs(comp, name) ? "ok" : "실패"; }
        catch (e) { r = prop.addToMotionGraphicsTemplate(comp) ? "ok(이름 기본)" : "실패"; }
    }
    EXPOSED.push(comp.name + " · " + name + "=" + r);
    return r;
}
function matte(layer, matteLayer) {
    if (typeof layer.setTrackMatte === "function") {
        layer.setTrackMatte(matteLayer, TrackMatteType.ALPHA);
        return "setTrackMatte";
    }
    matteLayer.moveBefore(layer);
    layer.trackMatteType = TrackMatteType.ALPHA;
    return "legacy";
}

/* ── 낙관 '쾅' ─────────────────────────────────────── */
function buildStamp(it) {
    var comp = newComp(it.title);
    var item = importPng(it.file, it.title + ".png");
    var L = comp.layers.add(item);
    L.name = it.title;
    var cx = it.x + it.w / 2, cy = it.y0 + it.h / 2;
    var n = controller(comp, "조절", cx, cy);
    L.parent = n;
    tr(L).property("ADBE Position").setValue([0, 0]);

    var op = tr(L).property("ADBE Opacity");
    op.setValueAtTime(f(0), 0); op.setValueAtTime(f(2), 100);
    lin(op, 1); lin(op, 2);

    var sc = tr(L).property("ADBE Scale");
    sc.setValueAtTime(f(0), [150, 150]); sc.setValueAtTime(f(4), [94, 94]);
    sc.setValueAtTime(f(7), [102, 102]); sc.setValueAtTime(f(10), [100, 100]);
    lin(sc, 1);
    sc.setInterpolationTypeAtKey(2, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.BEZIER);
    sc.setInterpolationTypeAtKey(3, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
    sc.setInterpolationTypeAtKey(4, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
    setEase(sc, 3, 50, 50); setEase(sc, 4, 70, 33);

    var ro = tr(L).property("ADBE Rotate Z");
    ro.setValueAtTime(f(0), 8); ro.setValueAtTime(f(4), 0);
    lin(ro, 1); lin(ro, 2);

    var po = tr(L).property("ADBE Position");
    var shake = [[0, 0], [2, -1], [-1, 1], [0, 0]];
    for (var i = 0; i < shake.length; i++) po.setValueAtTime(f(4 + i), shake[i]);
    for (var k = 1; k <= po.numKeys; k++) lin(po, k);

    protect(comp, 10, "도장");
    comp.motionGraphicsTemplateName = it.title;
    expose(comp, tr(n).property("ADBE Position"), "위치");
    expose(comp, tr(n).property("ADBE Scale"), "크기");
    return comp;
}

/* ── 붓 원 드로우온 ────────────────────────────────── */
function buildDrawOn(it) {
    var comp = newComp(it.title);
    var item = importPng(it.file, it.title + ".png");
    var L = comp.layers.add(item);
    L.name = it.title;

    /* 붓길 — trad.brush_ellipse 와 같은 식 (시작각 · 떨림 · 한 바퀴 뒤 넘침) */
    var M = comp.layers.addShape();
    M.name = it.title + " 붓길 매트";
    var g = M.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    g.name = "붓길";
    var pth = g.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Group");
    var pts = [];
    for (var i = 0; i <= it.n + it.over; i++) {
        var t = (it.start + 360 * i / it.n) * Math.PI / 180;
        var jit = 1 + 0.025 * Math.sin(3 * t + 0.7) + 0.02 * Math.cos(5 * t);
        pts.push([it.rx * jit * Math.cos(t), it.ry * jit * Math.sin(t)]);
    }
    var sh = new Shape();
    sh.vertices = pts; sh.closed = false;
    pth.property("ADBE Vector Shape").setValue(sh);
    var st = g.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Stroke");
    st.property("ADBE Vector Stroke Color").setValue([1, 1, 1]);
    st.property("ADBE Vector Stroke Width").setValue(2 * it.wmax + 14);
    var trim = M.property("ADBE Root Vectors Group").addProperty("ADBE Vector Filter - Trim");
    var end = trim.property("ADBE Vector Trim End");
    end.setValueAtTime(f(0), 0); end.setValueAtTime(f(16), 100);
    setEase(end, 1, 33, 40); setEase(end, 2, 75, 33);

    var n = controller(comp, "조절", it.cx, it.cy);
    L.parent = n; M.parent = n;
    tr(L).property("ADBE Position").setValue([it.x + it.w / 2 - it.cx, it.y0 + it.h / 2 - it.cy]);
    tr(M).property("ADBE Position").setValue([0, 0]);
    var how = matte(L, M);
    M.enabled = false;

    protect(comp, 16, "붓");
    comp.motionGraphicsTemplateName = it.title;
    expose(comp, tr(n).property("ADBE Position"), "위치");
    expose(comp, tr(n).property("ADBE Scale"), "크기");
    return comp;
}

/* ── 족자 펼침 ─────────────────────────────────────── */
var HEAD = [
    'var c = thisComp.layer("족자 조절");',
    'var p = c.effect("펼침")(1) / 100;',
    'var t = thisComp.layer("자막");',
    'var fs = t.text.sourceText.style.fontSize;',
    'var r = t.sourceRectAtTime(time, false);',
    'var W = Math.max(r.width + 120, 700);',
    'var h = fs + 30;',
    'var half = W / 2 * p;',
    'var o = c.transform.position;'
].join("\n") + "\n";

function rectGroup(layer, name, sizeExpr, pos, color) {
    var g = layer.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    g.name = name;
    var rc = g.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Rect");
    rc.property("ADBE Vector Rect Size").expression = HEAD + sizeExpr;
    rc.property("ADBE Vector Rect Position").setValue(pos);
    var fl = g.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Fill");
    fl.property("ADBE Vector Fill Color").setValue(color);
    return g;
}
function exprOk(prop, where) {
    var e = prop.expressionError;
    if (e && String(e).length) throw new Error("표현식 오류 " + where + ": " + e);
}

function buildScroll(it) {
    var comp = newComp(it.title);
    var paperItem = importPng("jokja_paper.png", "족자 종이.png");

    /* 아래 → 위 순서로 넣는다 (layers.add 는 맨 위에 얹는다) */
    var mt = comp.layers.addShape();                 /* 펼침 매트 — 종이·글자가 같이 쓴다 */
    mt.name = "펼침 매트";
    rectGroup(mt, "매트", "[W * p, h]", [0, 0], [1, 1, 1]);

    var sd = comp.layers.addShape();
    sd.name = "그림자";
    rectGroup(sd, "그림자", "[W * p, h]", [0, 0], [0, 0, 0]);
    tr(sd).property("ADBE Opacity").setValue(22);
    var gb = fxOf(sd).addProperty("ADBE Gaussian Blur 2");
    gb.property(1).setValue(12);

    var pp = comp.layers.add(paperItem);
    pp.name = "종이";

    var T = comp.layers.addText(it.text);
    T.name = "자막";
    var tp = T.property("ADBE Text Properties").property("ADBE Text Document");
    var d = tp.value;
    d.resetCharStyle();
    d.fontSize = it.size;
    d.font = FONT;
    d.applyFill = true; d.fillColor = C_INK;
    d.applyStroke = true; d.strokeColor = C_INK; d.strokeWidth = 2; d.strokeOverFill = false;   /* 합성기 굵기 1px 팽창과 같다 */
    d.justification = ParagraphJustification.CENTER_JUSTIFY;
    tp.setValue(d);

    var la = comp.layers.addShape(); la.name = "왼 축";
    rectGroup(la, "축", "[12, h + 10]", [-2, 0], C_WOOD);
    rectGroup(la, "끝단", "[26, h]", [13, 0], C_JJOK);
    var ra = comp.layers.addShape(); ra.name = "오른 축";
    rectGroup(ra, "축", "[12, h + 10]", [2, 0], C_WOOD);
    rectGroup(ra, "끝단", "[26, h]", [-13, 0], C_JJOK);

    var n = controller(comp, "족자 조절", 960, it.y);
    var sl = fxOf(n).addProperty("ADBE Slider Control");
    sl.name = "펼침";
    var pv = sl.property(1);
    pv.setValueAtTime(f(3), 0); pv.setValueAtTime(f(21), 100);
    setEase(pv, 1, 33, 15); setEase(pv, 2, 80, 33);

    /* 자리 */
    tr(mt).property("ADBE Position").expression = HEAD + "[o[0], o[1]]";
    tr(sd).property("ADBE Position").expression = HEAD + "[o[0], o[1] + 5]";
    tr(pp).property("ADBE Position").expression = 'thisComp.layer("족자 조절").transform.position';
    tr(pp).property("ADBE Scale").expression = HEAD + "[100, h / " + 160 + " * 100]";
    tr(T).property("ADBE Anchor Point").setValue([0, 0]);
    tr(T).property("ADBE Position").expression =
        'var o = thisComp.layer("족자 조절").transform.position;\nvar r = sourceRectAtTime(time, false);\n[o[0], o[1] + 1 - (r.top + r.height / 2)]';
    tr(la).property("ADBE Position").expression = HEAD + "[o[0] - half, o[1]]";
    tr(ra).property("ADBE Position").expression = HEAD + "[o[0] + half, o[1]]";
    var axes = [la, ra];
    for (var i = 0; i < axes.length; i++) {
        var op = tr(axes[i]).property("ADBE Opacity");
        op.setValueAtTime(f(0), 0); op.setValueAtTime(f(3), 100);
        lin(op, 1); lin(op, 2);
    }

    matte(pp, mt);
    matte(T, mt);
    mt.enabled = false;

    /* 표현식이 조용히 죽는지 되읽는다 */
    comp.time = f(30);
    exprOk(tr(la).property("ADBE Position"), "왼 축 위치");
    exprOk(tr(T).property("ADBE Position"), "자막 위치");
    exprOk(tr(pp).property("ADBE Scale"), "종이 크기");

    protect(comp, 21, "족자");
    comp.motionGraphicsTemplateName = it.title;
    expose(comp, tp, "자막");
    expose(comp, tr(n).property("ADBE Position"), "위치");
    return comp;
}

function __main() {
say("잡", "C3 전통 모션 컴포지션 + mogrt");
say("AE", app.version);
probe("목록", function () { return MOTION.items.length + "개"; });
probe("폰트", function () {
    var r = app.fonts.getFontsByPostScriptName(FONT);
    if (!r || !r.length) throw new Error("폰트가 없다: " + FONT);
    return FONT + " 있다 (" + r[0].familyName + " " + r[0].styleName + ")";
});

closeQuietly();
app.newProject();
probe("색 설정", function () {
    app.project.linearBlending = false;
    app.project.workingSpace = "";
    return "선형=" + app.project.linearBlending;
});
FOLDER_C = app.project.items.addFolder("모션 컴포지션");
FOLDER_F = app.project.items.addFolder("모션 footage");

var built = [], bad = [];
for (var i = 0; i < MOTION.items.length; i++) {
    (function (it) {
        var r = probe("  " + it.kind + " · " + it.title, function () {
            var c;
            if (it.kind === "stamp") c = buildStamp(it);
            else if (it.kind === "drawon") c = buildDrawOn(it);
            else if (it.kind === "scroll") c = buildScroll(it);
            else throw new Error("모르는 모션: " + it.kind);
            built.push(c);
            return c.numLayers + "레이어";
        });
        if (r.indexOf("ERR") === 0) bad.push(it.title);
    })(MOTION.items[i]);
}
for (var e = 0; e < EXPOSED.length; e++) out.push("    노출 " + EXPOSED[e]);
flush();

probe("aep 저장", function () {
    var fl = new File(AEP);
    if (fl.exists) fl.remove();
    app.project.save(fl);
    return AEP;
});

probe("mogrt 폴더", function () {
    var dd = new Folder(MOG);
    if (dd.exists) { var old = dd.getFiles("*.mogrt"); for (var q = 0; q < old.length; q++) old[q].remove(); }
    else dd.create();
    return dd.fsName;
});
/*  ⚠ 실측(2026-09-14): exportAsMotionGraphicsTemplate 한 번 뒤에 **들고 있던 CompItem 이 전부 무효**가 된다
    ("개체가 잘못되었습니다"). 내보내기가 프로젝트를 한 번 다시 싸는 듯하다. 그래서 이름만 들고 매번 새로 찾는다.  */
var names = [];
for (var m0 = 0; m0 < built.length; m0++) names.push(built[m0].name);
function compNamed(nm) {
    for (var z = 1; z <= app.project.numItems; z++) {
        var itz = app.project.item(z);
        if (itz instanceof CompItem && itz.name === nm) return itz;
    }
    return null;
}
app.beginSuppressDialogs();
var exported = 0;
for (var m = 0; m < names.length; m++) {
    (function (nm) {
        var r = probe("  mogrt " + nm, function () {
            var c = compNamed(nm);
            if (!c) throw new Error("컴포지션을 다시 못 찾았다");
            return String(c.exportAsMotionGraphicsTemplate(true, MOG));
        });
        if (r === "true") exported++;
    })(names[m]);
}
app.endSuppressDialogs(false);

flush();
if (bad.length) return fail("못 지은 것 " + bad.length + "개: " + bad.join(", "));
return done("컴포지션 " + built.length + "개 · mogrt " + exported + "개 호출 성공");
}
__main();
