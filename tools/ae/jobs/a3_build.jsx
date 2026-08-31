/*  A3 — 바닥 스틸 + 주석 레이어 재현.  하이브리드 파일럿의 본체다.

    바닥은 렌더된 스틸(C:/aelab/base.png = lab/ae/cut2-base-r63-무주석.png),
    그 위 주석 열 개를 AE 네이티브(셰이프·텍스트)로 다시 그린다.

    좌표는 _anchors.jsx — `node tools/ae/anchors.mjs` 가 렌더러의 makeScale 로 낸 실측값이다.
    스틸을 자로 재지 않았다. 바닥 스틸을 재렌더해 저장소본과 md5 가 같은 것으로 전제를 증명했다.

    설계 규칙 넷:
      · 셰이프/텍스트 레이어의 위치를 [0,0] 으로 두어 **레이어 좌표 = 컴포지션 좌표** 로 만든다.
        그래야 렌더러의 픽셀 좌표를 변환 없이 그대로 쓴다.
      · 등장/퇴장은 불투명도 키프레임, **자라나기(grow)는 마스크**로 한다.
        패스 자체를 키프레임하는 것보다 어긋날 여지가 적고, 클리핑도 공짜로 따라온다.
      · 글자폭은 **AE 가 재게** 한다(`sourceRectAtTime`). 캔버스 measureText 값을 옮겨 적지 않는다.
      · 폰트는 `getFontsByPostScriptName` 으로 **존재를 먼저 확인**한다.
        `d.font` 는 없는 이름도 받아서 그대로 되돌려주므로(A3 폰트 실측) 되돌아온 값은 증거가 아니다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
$.evalFile(new File(HERE + "/_anchors.jsx"));
logTo("a3");

/*  AE 는 최상위 return 을 문법 오류로 잡는다(프리미어 ExtendScript 와 다르다).
    그래서 본문을 함수로 감싼다 — 중간에서 빠져나가는 판정 가드를 쓰려면 이 형태여야 한다.  */
function __main() {

    var A     = ANCHORS;
    var W     = A.comp.w, H = A.comp.h, FPS = A.comp.fps, FRAMES = A.comp.frames;
    var DUR   = FRAMES / FPS;
    var NAME  = "차11-4_컷2_손익비";
    var AEP   = LAB + "/pilot.aep";
    var BASE  = LAB + "/base.png";

    /* 폰트 — scenes/../theme.js 실측 매핑.
       태그·라벨·뱃지 = fontTag 'S-Core Dream' 500  → SCDream5.otf     → S-CoreDream-5Medium
       차트 위 주석    = font    'Gmarket Sans' 700 → GmarketSansBold.otf → GmarketSansBold      */
    var F_TAG  = "S-CoreDream-5Medium";
    var F_NOTE = "GmarketSansBold";

    /* 색 — 씬(COLOR/LV)과 테마 실측값. 씬이 테마를 덮어쓴 것은 씬 쪽을 쓴다. */
    var C = {
        tp:     "#14FF36",  tpFill: "#BAFDC0",
        sl:     "#9F0000",  slFill: "#FEBABA",
        entry:  "#000000",  entryOpacity: 72,
        accent: "#E90054",
        buy:    "#E80001",           /* theme.buy — 국내식 매수 빨강 */
        tpBtn:  "#0DA82A",
        under:  "#C0272D",
        white:  "#FFFFFF"
    };

    say("잡", "A3 바닥 스틸 + 주석 레이어");
    say("AE", app.version);
    say("좌표", "bar42 x=" + A.x.bar42 + " · 진입 y=" + A.y.entry + " · 익절 y=" + A.y.target + " · 손절 y=" + A.y.stop);

    /* ══════════════════ 도구 ══════════════════ */

    function hex(h) {
        return [parseInt(h.substr(1, 2), 16) / 255, parseInt(h.substr(3, 2), 16) / 255, parseInt(h.substr(5, 2), 16) / 255];
    }
    function tr(L)   { return L.property("ADBE Transform Group"); }
    function pos0(L) { tr(L).property("ADBE Anchor Point").setValue([0, 0]); tr(L).property("ADBE Position").setValue([0, 0]); }

    function shapeFrom(verts, closed, inT, outT) {
        var s = new Shape();
        s.vertices = verts;
        s.closed = closed !== false;
        var z = [];
        for (var i = 0; i < verts.length; i++) z.push([0, 0]);
        s.inTangents  = inT  || z;
        s.outTangents = outT || z;
        return s;
    }
    function rectVerts(x, y, w, h) { return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]; }

    /** 셰이프 레이어 하나. 좌표는 컴포지션 좌표 그대로 쓴다. */
    function newShape(name) {
        var L = comp.layers.addShape();
        L.name = name;
        pos0(L);
        return L;
    }
    function addGroup(L) {
        return L.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group").property("ADBE Vectors Group");
    }
    function addPath(g, shape) {
        var p = g.addProperty("ADBE Vector Shape - Group");
        p.property("ADBE Vector Shape").setValue(shape);
        return p;
    }
    function addFill(g, color, opacity) {
        var f = g.addProperty("ADBE Vector Graphic - Fill");
        f.property("ADBE Vector Fill Color").setValue(hex(color));
        if (opacity != null) f.property("ADBE Vector Fill Opacity").setValue(opacity);
        return f;
    }
    function addStroke(g, color, width, roundCap) {
        var s = g.addProperty("ADBE Vector Graphic - Stroke");
        s.property("ADBE Vector Stroke Color").setValue(hex(color));
        s.property("ADBE Vector Stroke Width").setValue(width);
        if (roundCap) {
            s.property("ADBE Vector Stroke Line Cap").setValue(2);   /* 2 = 둥근 끝 */
            s.property("ADBE Vector Stroke Line Join").setValue(2);
        }
        return s;
    }

    /** 사각형 셰이프 레이어 한 장 (칠만) */
    function rectLayer(name, x, y, w, h, color, opacity) {
        var L = newShape(name);
        var g = addGroup(L);
        addPath(g, shapeFrom(rectVerts(x, y, w, h)));
        addFill(g, color, opacity);
        return L;
    }

    /** 등장/퇴장 불투명도. inSpec = [t, dur] 또는 null(처음부터 켜짐), outSpec = [t, dur] */
    function fade(L, inSpec, outSpec) {
        var op = tr(L).property("ADBE Opacity");
        if (inSpec) {
            op.setValueAtTime(inSpec[0], 0);
            op.setValueAtTime(inSpec[0] + inSpec[1], 100);
        } else {
            op.setValueAtTime(0, 100);
        }
        if (outSpec) {
            op.setValueAtTime(outSpec[0], 100);
            op.setValueAtTime(Math.min(outSpec[0] + outSpec[1], DUR - 1 / FPS), 0);
        }
        /* 이즈 — 렌더러는 컷 등장에 outCubic 계열을 쓴다. AE 는 이지이즈로 근사한다. */
        for (var i = 1; i <= op.numKeys; i++) {
            try {
                op.setTemporalEaseAtKey(i, [new KeyframeEase(0, 40)], [new KeyframeEase(0, 40)]);
            } catch (e) { /* 선형이어도 파일럿 합격 */ }
        }
        return op;
    }

    /** 자라나기 마스크. from/to 는 사각형 [x,y,w,h]. t0 에 from, t1 에 to. */
    function growMask(L, from, to, t0, t1) {
        var m = L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
        var sp = m.property("ADBE Mask Shape");
        sp.setValueAtTime(t0, shapeFrom(rectVerts(from[0], from[1], from[2], from[3])));
        sp.setValueAtTime(t1, shapeFrom(rectVerts(to[0], to[1], to[2], to[3])));
        for (var i = 1; i <= sp.numKeys; i++) {
            try { sp.setTemporalEaseAtKey(i, [new KeyframeEase(0, 75)], [new KeyframeEase(0, 75)]); } catch (e) {}
        }
        return m;
    }

    /** 텍스트 레이어. 잉크 박스의 중심을 (cx, cy) 에 맞춘다. */
    function textLayer(name, str, font, size, fillColor, strokeColor, strokeW) {
        var L = comp.layers.addText(str);
        L.name = name;
        var tp = L.property("ADBE Text Properties").property("ADBE Text Document");
        var d = tp.value;
        d.fontSize = size;
        d.font = font;
        d.applyFill = true;
        d.fillColor = hex(fillColor);
        if (strokeW > 0) {
            d.applyStroke = true;
            d.strokeColor = hex(strokeColor);
            d.strokeWidth = strokeW;
            d.strokeOverFill = false;          /* 캔버스 strokeText 는 획을 칠 뒤에 둔다 */
        } else {
            d.applyStroke = false;
        }
        d.justification = ParagraphJustification.CENTER_JUSTIFY;
        tp.setValue(d);
        return L;
    }
    function inkOf(L)  { return L.sourceRectAtTime(0, false); }
    function centerAt(L, cx, cy) {
        var r = inkOf(L);
        tr(L).property("ADBE Position").setValue([cx - (r.left + r.width / 2), cy - (r.top + r.height / 2)]);
        return r;
    }

    /* ══════════════════ 짓기 ══════════════════ */

    closeQuietly();
    probe("newProject", function () { app.newProject(); return "ok"; });

    probe("폰트 확인", function () {
        var t = [];
        var ns = [F_TAG, F_NOTE];
        for (var i = 0; i < ns.length; i++) {
            var r = app.fonts.getFontsByPostScriptName(ns[i]);
            t.push(ns[i] + "=" + (r && r.length ? "있다" : "**없다**"));
            if (!r || !r.length) throw new Error("폰트가 없다: " + ns[i]);
        }
        return t.join(" · ");
    });

    var comp = null;
    if (/없다/.test(out[out.length - 1])) { flush(); return fail("폰트가 없다 — 위 줄 참조"); }
    probe("addComp", function () {
        comp = app.project.items.addComp(NAME, W, H, 1, DUR, FPS);
        return comp.name;
    });
    if (!comp) { flush(); return fail("컴포지션 실패"); }

    /* ── 0. 바닥 스틸 ───────────────────────────────── */
    probe("바닥 스틸", function () {
        var f = new File(BASE);
        if (!f.exists) throw new Error("base.png 이 없다: " + BASE);
        var it = app.project.importFile(new ImportOptions(f));
        it.name = "바닥_무주석_r63";
        var L = comp.layers.add(it);
        L.name = "0_바닥스틸";
        return it.width + "x" + it.height;
    });

    /* ── 1. 매수 태그 (컷①에서 이어받아 처음부터 떠 있다) ── */
    /*  브랜드 버튼 실측 비율: 글씨높이/버튼높이 0.761 · (버튼폭−글씨폭)/높이 0.659
        · 촉 0.49·h · 모서리 0.08·h.  촉 끝은 캔들 왼쪽 gap(16) 만큼 떨어진다.        */
    function arrowTag(name, tipX, cy, label, size, bg) {
        /* 글씨를 먼저 만들어 잉크 크기를 재고, 그 값으로 버튼을 그린다 */
        var T = textLayer(name + "_글씨", label, F_TAG, size, C.white, C.white, 0);
        var r = inkOf(T);
        var inkW = r.width, inkH = r.height;
        var h = inkH / 0.761;
        var w = inkW + 0.659 * h;
        var head = 0.49 * h, rad = 0.08 * h;
        var x0 = tipX - w, x1 = tipX - head, top = cy - h / 2, bot = cy + h / 2;
        var k = 2 / 3;

        var S = newShape(name);
        var g = addGroup(S);
        var verts = [[tipX, cy], [x1, top], [x0 + rad, top], [x0, top + rad], [x0, bot - rad], [x0 + rad, bot], [x1, bot]];
        var zin = [], zout = [];
        for (var i = 0; i < 7; i++) { zin.push([0, 0]); zout.push([0, 0]); }
        /* 2차 베지어 → 3차: 제어점 Q 에 대해 접선 = 2/3·(Q − P) */
        zout[2] = [k * (x0 - (x0 + rad)), 0];
        zin[3]  = [0, k * (top - (top + rad))];
        zout[4] = [0, k * (bot - (bot - rad))];
        zin[5]  = [k * (x0 - (x0 + rad)), 0];
        addPath(g, shapeFrom(verts, true, zin, zout));
        addFill(g, bg);

        /* 글씨는 몸통 한가운데에서 촉 쪽으로 0.04·h 밀려 있다 (브랜드 실측) */
        var bodyCx = tipX - (head + (w - head) / 2);
        centerAt(T, bodyCx + h * 0.04, cy + 2);

        /* 셰이프가 글씨보다 아래로 가야 한다 — 나중에 만든 글씨가 위에 있으니 셰이프를 글씨 밑으로 */
        S.moveAfter(T);
        return { shape: S, text: T, w: w, h: h };
    }

    var buy = null;
    probe("1 매수 태그", function () {
        buy = arrowTag("1_매수태그", A.x.bar42 - 16, A.y.entry, "매수", 32, C.buy);
        fade(buy.shape, null, [5.0, 0.4]);
        fade(buy.text,  null, [5.0, 0.4]);
        return "촉 x=" + (A.x.bar42 - 16) + " · 버튼 " + Math.round(buy.w) + "x" + Math.round(buy.h);
    });

    /* ── 2·3. 익절 / 손절 색박스 ──────────────────────── */
    /*  채움(불투명도 55) + 그 위 굵기 14 선 + 선 시작점 왼쪽에 붙는 각진 라벨 박스.  */
    function levelBox(no, name, yLine, yFill, lineColor, fillColor, label) {
        var x0 = A.x.bar42, wFull = A.x.right - x0;
        var th = 14;
        var top = Math.min(yLine, yFill), hh = Math.abs(yFill - yLine);

        var L = newShape(no + "_" + name);
        /*  ⚠ AE 셰이프 레이어는 **먼저 추가한 그룹이 위에** 그려진다 — 캔버스와 반대다.
        캔버스는 채움을 먼저 칠하고 그 위에 선을 얹으므로, AE 에서는 **선을 먼저 추가**해야 한다.
        반대로 두면 55% 반투명 채움이 굵은 선의 윗절반을 덮어 색이 흐려진다 — 프레임 대조로 잡았다.  */
        var g2 = addGroup(L);
        addPath(g2, shapeFrom(rectVerts(x0, yLine - th / 2, wFull, th)));
        addFill(g2, lineColor);
        var g1 = addGroup(L);
        addPath(g1, shapeFrom(rectVerts(x0, top, wFull, hh)));
        addFill(g1, fillColor, 55);

        /* 라벨 — 글자폭은 AE 가 잰다 */
        var T = textLayer(no + "_" + name + "_라벨", label, F_TAG, 40, C.white, C.white, 0);
        var r = inkOf(T);
        var bw = r.width + 24 * 2, bh = 40 * 1.35;
        var bx = Math.max(x0 - bw, 6);
        var B = rectLayer(no + "_" + name + "_라벨판", bx, yLine - bh / 2, bw, bh, lineColor);
        centerAt(T, bx + bw / 2, yLine + 2);
        B.moveAfter(T);
        L.moveAfter(B);
        return { box: L, plate: B, text: T, x0: x0, wFull: wFull, top: top, hh: hh, th: th, bw: bw, bh: bh, bx: bx };
    }

    probe("2 익절 색박스", function () {
        var o = levelBox("2", "익절박스", A.y.target, A.y.entry, C.tp, C.tpFill, "익절");
        /* 왼→오 자라나기: 마스크 폭 0 → 전체 (선 굵기까지 덮게 위아래로 넉넉히) */
        var mtop = o.top - o.th, mh = o.hh + o.th * 2;
        growMask(o.box, [o.x0, mtop, 0.01, mh], [o.x0, mtop, o.wFull, mh], 0.3, 0.7);
        fade(o.box,   [0.3, 0.2], [5.15, 0.35]);
        fade(o.plate, [0.42, 0.35], [5.15, 0.35]);   /* labelDelay 0.12 */
        fade(o.text,  [0.42, 0.35], [5.15, 0.35]);
        return "y " + A.y.target + "~" + A.y.entry + " · 라벨판 " + Math.round(o.bw) + "x" + Math.round(o.bh) + " @x" + Math.round(o.bx);
    });

    probe("3 손절 색박스", function () {
        var o = levelBox("3", "손절박스", A.y.stop, A.y.entry, C.sl, C.slFill, "손절");
        var mtop = o.top - o.th, mh = o.hh + o.th * 2;
        growMask(o.box, [o.x0, mtop, 0.01, mh], [o.x0, mtop, o.wFull, mh], 0.7, 1.1);
        fade(o.box,   [0.7, 0.2], [5.15, 0.35]);
        fade(o.plate, [0.82, 0.35], [5.15, 0.35]);
        fade(o.text,  [0.82, 0.35], [5.15, 0.35]);
        return "y " + A.y.stop + "~" + A.y.entry + " · 라벨판 " + Math.round(o.bw) + "x" + Math.round(o.bh);
    });

    /* ── 4. 진입 라인 ─────────────────────────────────── */
    probe("4 진입 라인", function () {
        var x0 = A.x.bar42, wFull = A.x.right - x0, th = 4;
        /* 72% 는 레이어 불투명도가 아니라 **칠** 불투명도로 준다 — 등장 페이드가 레이어 쪽을 쓰므로 */
        var L = rectLayer("4_진입라인", x0, A.y.entry - th / 2, wFull, th, C.entry, C.entryOpacity);
        growMask(L, [x0, A.y.entry - 20, 0.01, 40], [x0, A.y.entry - 20, wFull, 40], 0.3, 0.7);
        fade(L, [0.3, 0.2], [5.15, 0.35]);
        return "y=" + A.y.entry + " · 굵기 " + th + " · 칠 불투명도 " + C.entryOpacity;
    });

    /* ── 5. 손익비 뱃지 ───────────────────────────────── */
    probe("5 손익비 뱃지", function () {
        var size = 46, x = 64, y = 1004;
        var T = textLayer("5_손익비_글씨", "손익비  1 : 2", F_TAG, size, C.white, "#000000", size * 0.15);
        var r = inkOf(T);
        var padX = size * 0.5, bw = r.width + padX * 2, bh = size * 1.5, rad = 10;
        /* 모서리 둥근 사각형 — 네 귀퉁이에 3차 접선을 준다 */
        var k = 0.5523 * rad;
        var x0 = x, y0 = y - bh / 2, x1 = x + bw, y1 = y + bh / 2;
        var verts = [
            [x0 + rad, y0], [x1 - rad, y0], [x1, y0 + rad], [x1, y1 - rad],
            [x1 - rad, y1], [x0 + rad, y1], [x0, y1 - rad], [x0, y0 + rad]
        ];
        var zin = [], zout = [];
        for (var i = 0; i < 8; i++) { zin.push([0, 0]); zout.push([0, 0]); }
        zout[1] = [k, 0];  zin[2] = [0, -k];
        zout[3] = [0, k];  zin[4] = [k, 0];
        zout[5] = [-k, 0]; zin[6] = [0, k];
        zout[7] = [0, -k]; zin[0] = [-k, 0];
        var B = newShape("5_손익비_판");
        var g = addGroup(B);
        addPath(g, shapeFrom(verts, true, zin, zout));
        addFill(g, C.accent);                       /* border:false — 검정 테두리 없음 */
        centerAt(T, x0 + padX + r.width / 2, y + 2);
        B.moveAfter(T);
        fade(T, [1.3, 0.3], [5.15, 0.35]);
        fade(B, [1.3, 0.3], [5.15, 0.35]);
        return Math.round(bw) + "x" + Math.round(bh) + " @ " + x0 + "," + Math.round(y0);
    });

    /* ── 6. 익절 버튼 ─────────────────────────────────── */
    probe("6 익절 버튼", function () {
        var o = arrowTag("6_익절버튼", A.x.bar53 - 16, A.y.target, "익절", 32, C.tpBtn);
        fade(o.shape, [3.3, 0.35], [5.15, 0.35]);
        fade(o.text,  [3.3, 0.35], [5.15, 0.35]);
        return "촉 x=" + (A.x.bar53 - 16) + " · y=" + A.y.target;
    });

    /* ── 7. 놓친 구간 빗금 ────────────────────────────── */
    /*  색 10% 채움 + 42px 간격·굵기 6·색 28% 의 45° 사선. 아래에서 위로 자란다.  */
    probe("7 놓친 구간 빗금", function () {
        var x0 = A.x.bar53, x1 = A.x.right;
        var yTop = A.y.missedHigh, yBase = A.y.target;
        var hh = yBase - yTop, ww = x1 - x0;

        var L = newShape("7_놓친구간_빗금");
        /* 사선 하나를 만들고 리피터로 42px 씩 복제한다 */
        var g2 = addGroup(L);
        var startX = x0 - hh;
        addPath(g2, shapeFrom([[startX, yBase], [startX + hh, yBase - hh]], false));
        addStroke(g2, C.accent, 6, false).property("ADBE Vector Stroke Opacity").setValue(28);
        var rep = g2.addProperty("ADBE Vector Filter - Repeater");
        var copies = Math.ceil((ww + hh * 2) / 42) + 1;
        rep.property("ADBE Vector Repeater Copies").setValue(copies);
        rep.property("ADBE Vector Repeater Transform").property("ADBE Vector Repeater Position").setValue([42, 0]);

        /* 사선이 위, 10% 채움이 아래 — 먼저 추가한 것이 위다 (levelBox 주석 참조) */
        var g1 = addGroup(L);
        addPath(g1, shapeFrom(rectVerts(x0, yTop, ww, hh)));
        addFill(g1, C.accent, 10);

        growMask(L, [x0, yBase - 0.01, ww, 0.01], [x0, yTop, ww, hh], 3.55, 4.45);   /* growDur 0.9 */
        fade(L, [3.55, 0.3], [5.15, 0.35]);
        return "y " + yTop + "~" + yBase + " · 사선 " + copies + "개 · 화살표는 씬에서 꺼져 있다";
    });

    /* ── 8. '놓친 구간' 글자 ──────────────────────────── */
    probe("8 놓친구간 글자", function () {
        var size = 58;
        var T = textLayer("8_놓친구간_글자", "놓친 구간", F_NOTE, size, C.white, "#000000", size * 0.16);
        centerAt(T, A.x.bar57, A.y.note);
        fade(T, [4.05, 0.3], [5.15, 0.35]);
        /* 등장할 때 18px 아래에서 올라온다 */
        var p = tr(T).property("ADBE Position");
        var v = p.value;
        p.setValueAtTime(4.05, [v[0], v[1] + 18]);
        p.setValueAtTime(4.50, v);
        for (var i = 1; i <= p.numKeys; i++) {
            try { p.setTemporalEaseAtKey(i, [new KeyframeEase(0, 70), new KeyframeEase(0, 70)],
                                            [new KeyframeEase(0, 70), new KeyframeEase(0, 70)]); } catch (e) {}
        }
        return "중심 " + A.x.bar57 + "," + A.y.note + " · " + size + "px · 외곽선 " + (size * 0.16);
    });

    /* ── 9. 손그림 밑줄 ───────────────────────────────── */
    probe("9 손그림 밑줄", function () {
        var cx = A.x.bar57, cy = A.y.note + 46, wid = 300;
        var x = cx - wid / 2;
        var steps = Math.max(2, Math.round(wid / 8));
        var verts = [];
        for (var i = 0; i <= steps; i++) {
            var p = i / steps;
            /* 렌더러와 같은 흔들림 식 */
            verts.push([x + wid * p, cy + Math.sin(p * 7.3 + 1.1) * 3.2 + Math.sin(p * 2.1) * 2.4]);
        }
        var L = newShape("9_손그림밑줄");
        var g = addGroup(L);
        addPath(g, shapeFrom(verts, false));
        addStroke(g, C.under, 12, true);
        /* 그어지는 연출 — 트림 패스 끝을 0 → 100 */
        var trim = g.addProperty("ADBE Vector Filter - Trim");
        var end = trim.property("ADBE Vector Trim End");
        end.setValueAtTime(4.3, 0);
        end.setValueAtTime(4.65, 100);
        for (var j = 1; j <= end.numKeys; j++) {
            try { end.setTemporalEaseAtKey(j, [new KeyframeEase(0, 70)], [new KeyframeEase(0, 70)]); } catch (e) {}
        }
        fade(L, [4.3, 0.2], [5.15, 0.35]);
        return "중심 " + cx + "," + cy + " · 폭 " + wid + " · 점 " + verts.length + "개";
    });

    /* ── 저장 ─────────────────────────────────────────── */
    say("레이어 수", comp.numLayers);
    probe("기존 pilot.aep 삭제", function () {
        var f = new File(AEP);
        if (!f.exists) return "없었다";
        return f.remove() ? "지웠다" : "못 지웠다";
    });
    probe("project.save", function () { app.project.save(new File(AEP)); return "호출됨"; });
    probe("파일 확인", function () {
        var f = new File(AEP);
        return f.exists ? f.length + " bytes" : "파일이 없다";
    });

    flush();
    return done("지었다. 판정은 a3_verify(재열기) + a3_frame(렌더큐 png) 이 한다");
}
__main();
