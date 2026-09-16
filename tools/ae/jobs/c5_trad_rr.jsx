/*  C5 — '차11-4 손익비' 모션(익절·손절 박스)을 신규안 v2 전통 문법으로 다시 짓는다.

    입력:  <작업실>/pack/trad_rr/footage/rr.jsx     (tools/style/trad_rr.py)
    출력:  <작업실>/pack/trad_rr/trad_rr.aep         (mogrt 는 c5x · 세트별 aep 는 c9)

    구성 — 사용자 요청(2026-09-14) "차트 배경은 빼도 돼. 소스별로 잘라서 쓸거야."
      · 소스 하나 = 컴포지션 하나 (1920×1080 투명 · 30fps · 6초). 요소는 v2 틀·차트와 같은 자리에 있고
        **자기 등장 모션이 0프레임에서 시작**한다. 표현식은 그 컴포지션 안의 레이어만 가리킨다 — 떼어 가도 안 깨진다.
      · 전체 = RR.stack 의 소스 컴포지션을 박자대로 늦춰 깐 것(176프레임). 끝에서 같이 사라진다.

    버튼-선 세트 (2026-09-14 2차 요청: 선은 화면 전체를 덮고, 버튼이 출발점, 버튼이 먼저)
      익절선&박스 · 손절선&박스 · 진입선 · 지지선 · 저항선(뒤 둘은 박스 없음, 전체에 안 들어감)
      f0~10  버튼(낙관) '쾅' — 화면 왼쪽 열(x=166)
      f4~20  선 앞끝이 화면 왼끝에서 출발해 **왼→오 한 방향**으로 오른끝까지 (선 PNG 는 0~1920 전체)
      f6~22  박스(담채)가 선을 2프레임 뒤따른다 (역시 0~1920 전체)

    전체 박자 (30fps 프레임)
      f0 매수 낙관 · f9 진입선 · f15 익절선&박스 · f21 손절선&박스 · f39 손익비 현판
      f99 익절 실행 낙관 · f107 놓친 구간(아래→위 27f) · f122 놓친 구간 문구 · f129 붓 밑줄 · f155~165 전부 퇴장

    글자 폭을 따라 판이 커지는 성질(옛 A6 합격선)은 남긴다 — 낙관 면은 가로로 늘고, 현판은 판 폭이 글자폭+64 로 따라온다.
    다른 잡이 빌더만 빌려 쓸 때(c9)는 $.global.__RR_LIB_ONLY = true 로 불러 __main 을 건너뛴다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c5");

var PACK = LAB + "/pack/trad_rr";
var FOOT = PACK + "/footage";
var AEP  = PACK + "/trad_rr.aep";
var FONT = "Gungsuh";
$.evalFile(new File(FOOT + "/rr.jsx"));   /* RR */

var FPS = RR.fps, SRC_DUR = 6, MAIN_DUR = RR.frames / RR.fps;
function f(n) { return n / FPS; }
function hex(h) { return [parseInt(h.substr(1, 2), 16) / 255, parseInt(h.substr(3, 2), 16) / 255, parseInt(h.substr(5, 2), 16) / 255]; }
function tr(L) { return L.property("ADBE Transform Group"); }
function fxOf(L) { return L.property("ADBE Effect Parade"); }
function num(v) { return (Math.round(v * 100) / 100).toString(); }

/** 차원 수를 몰라도 이징을 건다 (크기 3 · 슬라이더 1 · 공간 속성 1 …) */
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
function easeAll(prop, inf) { for (var k = 1; k <= prop.numKeys; k++) setEase(prop, k, inf, inf); }
function lin(prop, k) { prop.setInterpolationTypeAtKey(k, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR); }
function linAll(prop) { for (var k = 1; k <= prop.numKeys; k++) lin(prop, k); }

var FOLDER_S = null, FOLDER_F = null;
function importPng(rel, name) {
    var fl = new File(FOOT + "/" + rel);
    if (!fl.exists) throw new Error("PNG 없음: " + rel);
    var it = app.project.importFile(new ImportOptions(fl));
    it.name = name || rel;
    it.parentFolder = FOLDER_F;
    try { it.mainSource.alphaMode = AlphaMode.STRAIGHT; } catch (e) {}
    return it;
}
function newComp(title) {
    var c = app.project.items.addComp(title, RR.w, RR.h, 1, SRC_DUR, FPS);
    c.parentFolder = FOLDER_S;
    return c;
}
function compNamed(nm) {
    for (var z = 1; z <= app.project.numItems; z++) {
        var it = app.project.item(z);
        if (it instanceof CompItem && it.name === nm) return it;
    }
    return null;
}
function itemById(id) {
    for (var j = 0; j < RR.items.length; j++) if (RR.items[j].id === id) return RR.items[j];
    return null;
}
/** 조절 널 — 앵커 0 이라 자식의 [0,0] 이 곧 널 자리다 */
function controller(comp, name, x, y) {
    var n = comp.layers.addNull(comp.duration);
    n.name = name;
    tr(n).property("ADBE Anchor Point").setValue([0, 0]);
    tr(n).property("ADBE Position").setValue([x, y]);
    return n;
}
/** 자식으로 붙이고 부모 기준 자리를 바로 준다 (붙이는 순간 AE 가 월드 좌표를 보존하려고 값을 바꾸므로) */
function attach(L, parent, anchor, pos) {
    L.parent = parent;
    tr(L).property("ADBE Anchor Point").setValue(anchor);
    tr(L).property("ADBE Position").setValue(pos);
    tr(L).property("ADBE Rotate Z").setValue(0);
    tr(L).property("ADBE Scale").setValue([100, 100]);
}
function protect(comp, startF, frames, label) {
    var mv = new MarkerValue(label);
    mv.duration = f(frames);
    try { mv.protectedRegion = true; } catch (e) {}
    comp.markerProperty.setValueAtTime(f(startF), mv);
}
var EXPOSED = [];
function expose(comp, prop, name) {
    var r;
    try {
        if (!prop.canAddToMotionGraphicsTemplate(comp)) r = "canAdd=false";
        else {
            try { r = prop.addToMotionGraphicsTemplateAs(comp, name) ? "ok" : "실패"; }
            catch (e) { r = prop.addToMotionGraphicsTemplate(comp) ? "ok(이름 기본)" : "실패"; }
        }
    } catch (e2) { r = "ERR " + e2.toString(); }
    EXPOSED.push(comp.name + " · " + name + "=" + r);
    return r;
}
function matte(layer, matteLayer) {
    if (typeof layer.setTrackMatte === "function") { layer.setTrackMatte(matteLayer, TrackMatteType.ALPHA); return "setTrackMatte"; }
    matteLayer.moveBefore(layer);
    layer.trackMatteType = TrackMatteType.ALPHA;
    return "legacy";
}
function exprOk(prop, where) {
    var e = prop.expressionError;
    if (e && String(e).length) throw new Error("표현식 오류 " + where + ": " + e);
}
function textProp(L) { return L.property("ADBE Text Properties").property("ADBE Text Document"); }
function styleText(L, size, fill, stroke, sw) {
    var tp = textProp(L);
    var d = tp.value;
    d.resetCharStyle();
    d.fontSize = size;
    d.font = FONT;
    d.applyFill = true; d.fillColor = hex(fill);
    if (sw > 0) { d.applyStroke = true; d.strokeColor = hex(stroke); d.strokeWidth = sw; d.strokeOverFill = false; }
    else d.applyStroke = false;
    d.justification = ParagraphJustification.CENTER_JUSTIFY;
    tp.setValue(d);
}
/** 글자 잉크 상자 중심을 부모 기준 (dx, dy) 에 둔다 — 합성기의 anchor='mm' + 잉크 오프셋과 같은 자리 */
function inkCenterExpr(dx, dy, withValue) {
    return 'var r = sourceRectAtTime(time, false);\n' + (withValue ? 'value + ' : '') +
           '[' + num(dx) + ' - (r.left + r.width / 2), ' + num(dy) + ' - (r.top + r.height / 2)]';
}
function fillFx(L, color) {
    var e = fxOf(L).addProperty("ADBE Fill");
    e.name = "색";
    var c = fxOf(L).property("색").property("ADBE Fill-0002");
    c.setValue(hex(color));
    return c;
}
function fillColorOf(L) { return fxOf(L).property("색").property("ADBE Fill-0002"); }
function fadeIn(L, f0, f1, to) {
    var op = tr(L).property("ADBE Opacity");
    op.setValueAtTime(f(f0), 0); op.setValueAtTime(f(f1), to == null ? 100 : to);
    linAll(op);
}
function rectShape(x0, y0, x1, y1) {
    var s = new Shape();
    s.vertices = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
    s.closed = true;
    return s;
}
function rectGroup(layer, name, sizeExpr, posExpr) {
    var g = layer.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    g.name = name;
    var rc = layer.property("ADBE Root Vectors Group").property(name).property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Rect");
    rc.property("ADBE Vector Rect Size").expression = sizeExpr;
    if (typeof posExpr === "string") rc.property("ADBE Vector Rect Position").expression = posExpr;
    else rc.property("ADBE Vector Rect Position").setValue(posExpr);
    return layer.property("ADBE Root Vectors Group").property(name).property("ADBE Vectors Group");
}

/* ── 낙관 한 벌 (면 PNG + AE 궁서 글자) 을 parent 아래에 짓고 '쾅' 을 건다 (c3 와 같은 모션) ── */
function makeSeal(comp, parent, it) {
    var s = comp.layers.addNull(comp.duration);
    s.name = "찍힘";
    attach(s, parent, [0, 0], [0, 0]);

    var F = comp.layers.add(importPng(it.face.file));
    F.name = "낙관 면";
    attach(F, s, [it.cx - it.face.x, it.cy - it.face.y], [0, 0]);
    fillFx(F, it.color);

    var Tx = comp.layers.addText(it.text);
    Tx.name = "문구";
    styleText(Tx, it.size, it.fg, null, 0);
    attach(Tx, s, [0, 0], [0, 0]);
    tr(Tx).property("ADBE Position").expression = inkCenterExpr(it.tdx, it.tdy, false);
    var w0 = Tx.sourceRectAtTime(0, false).width;
    /* 문구가 길어지면 면을 가로로 늘린다. 기본 문구에서 정확히 100% */
    tr(F).property("ADBE Scale").expression =
        'var r = thisComp.layer("문구").sourceRectAtTime(time, false);\n' +
        'var k = Math.max(1, (r.width + ' + num(it.pad) + ') / (' + num(w0) + ' + ' + num(it.pad) + '));\n' +
        '[100 * k, 100]';

    var sc = tr(s).property("ADBE Scale");
    sc.setValueAtTime(f(0), [150, 150]); sc.setValueAtTime(f(4), [94, 94]);
    sc.setValueAtTime(f(7), [102, 102]); sc.setValueAtTime(f(10), [100, 100]);
    lin(sc, 1);
    sc.setInterpolationTypeAtKey(2, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.BEZIER);
    sc.setInterpolationTypeAtKey(3, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
    sc.setInterpolationTypeAtKey(4, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
    setEase(sc, 3, 50, 50); setEase(sc, 4, 70, 33);
    var ro = tr(s).property("ADBE Rotate Z");
    ro.setValueAtTime(f(0), 8); ro.setValueAtTime(f(4), 0); linAll(ro);
    var po = tr(s).property("ADBE Position");
    var shake = [[0, 0], [2, -1], [-1, 1], [0, 0]];
    for (var i = 0; i < shake.length; i++) po.setValueAtTime(f(4 + i), shake[i]);
    linAll(po);
    fadeIn(F, 0, 2); fadeIn(Tx, 0, 2);
    return { s: s, F: F, Tx: Tx, w0: w0 };
}

function buildSeal(it) {
    var comp = newComp(it.name);
    var n = controller(comp, "조절", it.cx, it.cy);
    var o = makeSeal(comp, n, it);
    /*  기울임은 자식을 다 붙인 뒤에. ⚠ 부호가 반대다 — PIL rotate(+) 는 반시계, AE 회전(+) 은 시계 방향
        (2026-09-14 대조에서 매수·익절 실행 낙관이 거울처럼 기울어 잡았다).  */
    tr(n).property("ADBE Rotate Z").setValue(-it.tilt);

    comp.time = f(20);
    exprOk(tr(o.F).property("ADBE Scale"), "면 크기");
    exprOk(tr(o.Tx).property("ADBE Position"), "문구 자리");
    protect(comp, 0, it.intro, "도장");
    comp.motionGraphicsTemplateName = comp.name;
    expose(comp, textProp(o.Tx), "문구");
    expose(comp, fillColorOf(o.F), "색");
    expose(comp, tr(n).property("ADBE Position"), "위치");
    expose(comp, tr(n).property("ADBE Scale"), "크기");
    return { comp: comp, note: "글자 잉크폭 " + num(o.w0) };
}

/* ── 버튼-선 세트 — 버튼이 먼저 찍히고, 선·박스가 왼쪽에서 오른쪽으로 한 방향으로 화면 끝까지 ── */
function buildSet(it) {
    var comp = newComp(it.name);
    var n = controller(comp, "조절", it.cx, it.cy);          /* 조절 널 = 버튼 자리 */
    var FE = 10, M = 30, zone = null, line = null;          /* 굵은 인주 선이라 앞끝 흐림은 짧게 (3차) */
    for (var i = 0; i < it.layers.length; i++) {
        var p = it.layers[i];
        var L = comp.layers.add(importPng(p.file));
        L.name = p.name === "zone" ? "박스" : "선";
        attach(L, n, [0, 0], [p.x - it.cx, p.y - it.cy]);
        fillFx(L, p.fill);
        if (p.name === "zone") zone = L; else line = L;
        /*  펼침 마스크: 왼끝은 화면 밖에 고정, 오른끝(앞끝)만 화면 왼끝 → 오른끝 밖으로.
            처음 키에서는 앞끝이 화면 밖(-FE)이라 아무것도 안 보인다. 버튼(x=166)이 출발점을 덮고 있다.  */
        var rv = it.reveal[p.name];
        L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom").name = "펼침";
        var mp = L.property("ADBE Mask Parade").property("펼침");
        mp.property("ADBE Mask Feather").setValue([FE, 0]);
        var sp = mp.property("ADBE Mask Shape");
        sp.setValueAtTime(f(rv[0]), rectShape(-M - FE - p.x, -M, -FE - p.x, p.h + M));
        sp.setValueAtTime(f(rv[1]), rectShape(-M - FE - p.x, -M, RR.w + FE + M - p.x, p.h + M));
        setEase(sp, 1, 33, 25); setEase(sp, 2, 80, 33);          /* 빠르게 뻗고 오른끝에서 가라앉는다 */
    }
    var o = makeSeal(comp, n, it);                             /* 버튼은 맨 위 */
    /*  3차(2026-09-14): 선은 버튼과 같은 재질·같은 색이다 — 색 컨트롤 하나가 버튼 → 선 → 박스를 몬다.  */
    fillColorOf(line).expression = 'thisComp.layer("낙관 면").effect("색")("ADBE Fill-0002")';
    if (zone) fillColorOf(zone).expression = 'thisComp.layer("선").effect("색")("ADBE Fill-0002")';

    comp.time = f(30);
    exprOk(fillColorOf(line), "선 색 묶음");
    if (zone) exprOk(fillColorOf(zone), "박스 색 묶음");
    exprOk(tr(o.F).property("ADBE Scale"), "면 크기");
    exprOk(tr(o.Tx).property("ADBE Position"), "문구 자리");
    protect(comp, 0, it.intro, "버튼→선");
    comp.motionGraphicsTemplateName = comp.name;
    expose(comp, textProp(o.Tx), "문구");
    expose(comp, fillColorOf(o.F), "색");
    /* 4차: 박스는 선명한 단색(기본 100%) — 흐리기는 편집자가 직접 (레이어 불투명도는 템플릿에 열린다, c5b 실측) */
    if (zone) expose(comp, tr(zone).property("ADBE Opacity"), "박스 불투명도");
    expose(comp, tr(n).property("ADBE Position"), "위치");
    expose(comp, tr(n).property("ADBE Scale"), "크기");
    return { comp: comp, note: "버튼 f0 · 선 f" + it.reveal.line[0] + "~" + it.reveal.line[1] + (zone ? " · 박스 f" + it.reveal.zone[0] + "~" + it.reveal.zone[1] : "") };
}

/* ── 빗금 — 마스크가 번지며 펼친다 (옛 growMask 와 같은 방향·이징 75) ── */
function buildWipe(it) {
    var comp = newComp(it.name);
    var bx0 = it.box[0], by0 = it.box[1], bx1 = it.box[2], by1 = it.box[3];
    var cx = (bx0 + bx1) / 2, cy = (by0 + by1) / 2;
    var n = controller(comp, "조절", cx, cy);
    var NAMES = { zone: "담채", line: "선", hatch: "빗금" };
    var FE = 12, M = 24, first = null;
    for (var i = 0; i < it.layers.length; i++) {
        var p = it.layers[i];
        var L = comp.layers.add(importPng(p.file));
        L.name = NAMES[p.name] || p.name;
        attach(L, n, [0, 0], [p.x - cx, p.y - cy]);
        if (p.fill) {
            fillFx(L, p.fill);
            if (!first) first = L;
            else fillColorOf(L).expression = 'thisComp.layer("' + first.name + '").effect("색")("ADBE Fill-0002")';
        }
        var m = L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
        m.name = "펼침";
        var sp = L.property("ADBE Mask Parade").property("펼침").property("ADBE Mask Shape");
        var fe = L.property("ADBE Mask Parade").property("펼침").property("ADBE Mask Feather");
        if (it.dir === "lr") {
            sp.setValueAtTime(f(0), rectShape(-M, -M, bx0 - FE - p.x, p.h + M));
            sp.setValueAtTime(f(it.intro), rectShape(-M, -M, bx1 + FE - p.x, p.h + M));
            fe.setValue([FE, 0]);
        } else {
            sp.setValueAtTime(f(0), rectShape(-M, by1 + FE - p.y, p.w + M, p.h + M));
            sp.setValueAtTime(f(it.intro), rectShape(-M, by0 - FE - p.y, p.w + M, p.h + M));
            fe.setValue([0, FE]);
        }
        easeAll(sp, 75);
    }
    if (first) { comp.time = f(20); if (it.layers.length > 1) exprOk(fillColorOf(comp.layer(1)), "선 색 묶음"); }
    protect(comp, 0, it.intro, "펼침");
    comp.motionGraphicsTemplateName = comp.name;
    if (first) expose(comp, fillColorOf(first), "색");
    expose(comp, tr(n).property("ADBE Position"), "위치");
    expose(comp, tr(n).property("ADBE Scale"), "크기");
    return { comp: comp, note: it.dir + " " + it.intro + "f" };
}

/* ── 손익비 현판 — 옻칠 판 + 금테 + 흰 궁서, 판 폭은 글자폭 + 64 (trad.hyeonpan) ── */
function buildPlate(it) {
    var comp = newComp(it.name);
    var n = controller(comp, "조절", it.cx, it.top);         /* 걸린 자리 = 판 위 가운데 */
    var hg = comp.layers.addNull(comp.duration);
    hg.name = "걸림";
    attach(hg, n, [0, 0], [0, 0]);

    var Tx = comp.layers.addText(it.text);
    Tx.name = "문구";
    styleText(Tx, it.size, it.fg, it.fg, 2);                  /* 합성기 bold=1(1px 팽창) */
    attach(Tx, hg, [0, 0], [0, 0]);
    tr(Tx).property("ADBE Position").expression = inkCenterExpr(it.tdx, it.ph / 2 + it.tdy, false);

    var WEXP = 'var r = thisComp.layer("문구").sourceRectAtTime(time, false);\nvar w = r.width + ' + num(it.pad) + ';\n';
    var S = comp.layers.addShape();
    S.name = "그림자";
    var gs = rectGroup(S, "그림자", WEXP + '[w, ' + it.ph + ']', [4, it.ph / 2 + 6]);
    gs.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue([0, 0, 0]);
    fxOf(S).addProperty("ADBE Gaussian Blur 2").property(1).setValue(18);   /* 12 는 PIL 반경 6 보다 날카로웠다 (대조 실측) */
    attach(S, hg, [0, 0], [0, 0]);

    var P = comp.layers.addShape();
    P.name = "현판";
    /* 셰이프 레이어는 먼저 추가한 그룹이 위에 그려진다 (AE-LAB A3) — 금테를 먼저 */
    var gg = rectGroup(P, "금테", WEXP + '[w - 12, ' + (it.ph - 12) + ']', [0, it.ph / 2]);
    var st = gg.addProperty("ADBE Vector Graphic - Stroke");
    st.property("ADBE Vector Stroke Color").setValue(hex(it.gold));
    st.property("ADBE Vector Stroke Width").setValue(2);
    var gl = rectGroup(P, "옻칠", WEXP + '[w, ' + it.ph + ']', [0, it.ph / 2]);
    var fl = gl.addProperty("ADBE Vector Graphic - Fill");
    fl.name = "판칠";
    fl.property("ADBE Vector Fill Color").setValue(hex(it.bg));
    attach(P, hg, [0, 0], [0, 0]);
    Tx.moveToBeginning();

    /* 위에서 16px 떨어져 걸리고, 걸린 점을 축으로 한 번 흔들린다 */
    var po = tr(hg).property("ADBE Position");
    po.setValueAtTime(f(0), [0, -16]); po.setValueAtTime(f(9), [0, 0]);
    setEase(po, 1, 33, 20); setEase(po, 2, 80, 33);
    var ro = tr(hg).property("ADBE Rotate Z");
    ro.setValueAtTime(f(0), -3); ro.setValueAtTime(f(6), 1.5); ro.setValueAtTime(f(12), 0);
    easeAll(ro, 50);
    fadeIn(Tx, 0, 5); fadeIn(P, 0, 5); fadeIn(S, 0, 5, 27.45);    /* 그림자 알파 70/255 */

    comp.time = f(20);
    exprOk(tr(Tx).property("ADBE Position"), "문구 자리");
    protect(comp, 0, it.intro, "현판");
    comp.motionGraphicsTemplateName = comp.name;
    expose(comp, textProp(Tx), "문구");
    expose(comp, P.property("ADBE Root Vectors Group").property("옻칠").property("ADBE Vectors Group").property("판칠").property("ADBE Vector Fill Color"), "판 색");
    expose(comp, tr(n).property("ADBE Position"), "위치");
    expose(comp, tr(n).property("ADBE Scale"), "크기");
    return { comp: comp, note: "" };
}

/* ── '놓친 구간' 먹글씨 — 한지색 후광, 18px 아래에서 올라온다 (옛 cmgNote) ── */
function buildNote(it) {
    var comp = newComp(it.name);
    var n = controller(comp, "조절", it.cx, it.cy);
    var Tx = comp.layers.addText(it.text);
    Tx.name = "문구";
    styleText(Tx, it.size, it.fill, it.halo, 6);              /* 합성기 halo = 3px 팽창 → 획 6 의 바깥 절반 */
    attach(Tx, n, [0, 0], [0, 0]);
    var po = tr(Tx).property("ADBE Position");
    po.setValueAtTime(f(0), [0, 18]); po.setValueAtTime(f(it.intro), [0, 0]);
    easeAll(po, 70);
    po.expression = inkCenterExpr(it.tdx, it.tdy, true);
    fadeIn(Tx, 0, 9);
    comp.time = f(20);
    exprOk(po, "문구 자리");
    protect(comp, 0, it.intro, "글자");
    comp.motionGraphicsTemplateName = comp.name;
    expose(comp, textProp(Tx), "문구");
    expose(comp, tr(n).property("ADBE Position"), "위치");
    expose(comp, tr(n).property("ADBE Scale"), "크기");
    return { comp: comp, note: "" };
}

/* ── 인주 붓 밑줄 — 붓길(열린 패스) 트림을 알파 매트로 (c3 붓 원과 같은 방식) ── */
function buildBrush(it) {
    var comp = newComp(it.name);
    var cx = (it.box[0] + it.box[2]) / 2, cy = (it.box[1] + it.box[3]) / 2;
    var n = controller(comp, "조절", cx, cy);
    var L = comp.layers.add(importPng(it.layer.file));
    L.name = "붓 밑줄";
    attach(L, n, [0, 0], [it.layer.x - cx, it.layer.y - cy]);
    fillFx(L, it.fill);

    var M = comp.layers.addShape();
    M.name = "붓길 매트";
    var g = M.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    g.name = "붓길";
    var cts = M.property("ADBE Root Vectors Group").property("붓길").property("ADBE Vectors Group");
    var pth = cts.addProperty("ADBE Vector Shape - Group");
    var pts = [];
    for (var i = 0; i < it.pts.length; i++) pts.push([it.pts[i][0] - cx, it.pts[i][1] - cy]);
    var sh = new Shape();
    sh.vertices = pts; sh.closed = false;
    pth.property("ADBE Vector Shape").setValue(sh);
    var st = cts.addProperty("ADBE Vector Graphic - Stroke");
    st.property("ADBE Vector Stroke Color").setValue([1, 1, 1]);
    st.property("ADBE Vector Stroke Width").setValue(it.stroke);
    st.property("ADBE Vector Stroke Line Cap").setValue(2);
    var trim = M.property("ADBE Root Vectors Group").addProperty("ADBE Vector Filter - Trim");
    var end = trim.property("ADBE Vector Trim End");
    end.setValueAtTime(f(0), 0); end.setValueAtTime(f(it.intro), 100);
    setEase(end, 1, 33, 45); setEase(end, 2, 70, 33);
    attach(M, n, [0, 0], [0, 0]);
    var how = matte(L, M);
    M.enabled = false;
    fadeIn(L, 0, 1);                                          /* 길이 0 인 둥근 끝이 점으로 남지 않게 */

    protect(comp, 0, it.intro, "붓");
    comp.motionGraphicsTemplateName = comp.name;
    expose(comp, fillColorOf(L), "색");
    expose(comp, tr(n).property("ADBE Position"), "위치");
    expose(comp, tr(n).property("ADBE Scale"), "크기");
    return { comp: comp, note: how };
}

function buildItem(it) {
    if (it.kind === "seal") return buildSeal(it);
    if (it.kind === "set") return buildSet(it);
    if (it.kind === "wipe") return buildWipe(it);
    if (it.kind === "plate") return buildPlate(it);
    if (it.kind === "note") return buildNote(it);
    if (it.kind === "brush") return buildBrush(it);
    throw new Error("모르는 종류: " + it.kind);
}

/* ── 전체 — RR.stack 의 소스 컴포지션을 박자대로 늦춰 깐다 ── */
function buildMain() {
    var comp = app.project.items.addComp(RR.name, RR.w, RR.h, 1, MAIN_DUR, FPS);
    comp.motionGraphicsTemplateName = RR.name;
    /*  ⚠ 실측(2026-09-14, c5b_ess_probe): 소스에서 연 컨트롤은 전체 쪽 레이어에 '필수 속성'(ADBE Layer Overrides)으로
        올라오지만 **스크립트로는 전체 템플릿에 다시 열 수 없다** — 크기·위치·색·문구 넷 다 canAdd=false,
        같은 레이어의 불투명도는 true. (UI 에서 끌어다 놓는 것은 되는 기능이다.)
        컨트롤이 0개면 mogrt 내보내기가 false 를 준다. 그래서 전체는 '전체 조절' 널의 위치·크기만 연다.
        문구·색은 소스 mogrt 와 aep 에서 바꾼다. 소스가 전체를 표현식으로 읽게 하면 떼어 쓸 때 깨지므로 하지 않는다.  */
    var all = comp.layers.addNull(comp.duration);
    all.name = "전체 조절";
    tr(all).property("ADBE Anchor Point").setValue([0, 0]);
    tr(all).property("ADBE Position").setValue([RR.w / 2, RR.h / 2]);
    var ess = [];
    for (var i = 0; i < RR.stack.length; i++) {
        var it = itemById(RR.stack[i]);
        var src = compNamed(it.name);
        if (!src) throw new Error("소스 컴포지션 없음: " + it.name);
        var L = comp.layers.add(src);
        L.name = it.title;
        L.startTime = f(it.beat);
        var op = tr(L).property("ADBE Opacity");
        op.setValueAtTime(f(RR.out[0]), 100); op.setValueAtTime(f(RR.out[1]), 0);
        easeAll(op, 40);
        L.parent = all;
        ess.push(it.title + "@f" + it.beat);
    }
    all.moveToBeginning();
    protect(comp, 0, 140, "등장");
    protect(comp, RR.out[0], RR.frames - RR.out[0], "퇴장");
    expose(comp, tr(all).property("ADBE Position"), "위치");
    expose(comp, tr(all).property("ADBE Scale"), "크기");
    return { comp: comp, note: ess.join(" · ") };
}

function __main() {
say("잡", "C5 차11-4 손익비 (전통) 컴포지션 짓기");
say("AE", app.version);
probe("목록", function () { return RR.items.length + "개 · 전체 " + RR.stack.length + "개 · " + RR.frames + "프레임"; });
probe("폰트", function () {
    var r = app.fonts.getFontsByPostScriptName(FONT);
    if (!r || !r.length) throw new Error("폰트가 없다: " + FONT);
    return FONT + " 있다";
});

closeQuietly();
app.newProject();
probe("색 설정", function () { app.project.linearBlending = false; app.project.workingSpace = ""; return "선형=" + app.project.linearBlending; });
FOLDER_S = app.project.items.addFolder("손익비 소스 컴포지션");
FOLDER_F = app.project.items.addFolder("손익비 footage");

var built = [], bad = [];
for (var i = 0; i < RR.items.length; i++) {
    (function (it) {
        var r = probe("  " + it.kind + " · " + it.name, function () {
            var o = buildItem(it);
            built.push(o.comp.name);
            return o.comp.numLayers + "레이어 " + o.note;
        });
        if (String(r).indexOf("ERR") === 0) bad.push(it.name);
    })(RR.items[i]);
}
if (!bad.length) {
    var mr = probe("전체 " + RR.name, function () { var o = buildMain(); built.push(o.comp.name); return o.comp.numLayers + "레이어 · " + o.note; });
    if (String(mr).indexOf("ERR") === 0) bad.push("전체");
}
for (var e = 0; e < EXPOSED.length; e++) out.push("    노출 " + EXPOSED[e]);
flush();
if (bad.length) { flush(); return fail("못 지은 것: " + bad.join(", ") + " (aep 저장 안 함)"); }

probe("aep 저장", function () {
    var fl = new File(AEP);
    if (fl.exists) fl.remove();
    app.project.save(fl);
    return AEP;
});

/*  mogrt 내보내기는 여기서 하지 않는다 → tools/ae/trad_rr_export.ps1 (c5x + zip 검사 + 누락분 재내보내기).
    ⚠ 실측(2026-09-14): 내보내기가 메모리 프로젝트를 줄여 놓거나, 반환값 true 인데 푸티지 누락을 적는다.  */
flush();
return done("컴포지션 " + built.length + "개 · aep 저장 (mogrt 는 trad_rr_export.ps1)");
}
if (!$.global.__RR_LIB_ONLY) __main();
