/*  레이어 종류별 AE 변환기.  src/render/layers.js 의 각 함수를 셰이프·텍스트로 옮긴 것이다.

    옮길 때 지킨 것:
      · **연출을 표현식으로 옮긴다.** 렌더러는 grow·pop·draw 를 span(t, a, b, ease) 로 낸다.
        같은 식을 AE 표현식에 넣으면 키프레임 근사가 아니라 원식 그대로가 된다.
        (파일럿은 마스크 키프레임으로 근사했다 — 컷 하나였으니 통했을 뿐이다.)
      · **차트 좌표는 카메라에서 온다.** px(봉)·py(가격) — _ae.jsx camHead() 참고.
      · 렌더러가 plot 으로 클리핑하는 것은 마스크로 옮긴다.

    각 함수는 만든 레이어를 **그릴 순서대로**(뒤→앞) 돌려준다. 드라이버가 쌓는다.
*/

/* 테마 실측값 — src/render/theme.js CHARTMYEONGGA */
var TH = {
    up: "#0B8C7F", down: "#E80001", ma: "#F38808", accent: "#E90054",
    buy: "#E80001", sell: "#0200F3", tp: "#14FF36", tpFill: "#C5FFC4",
    sl: "#9F0000", slFill: "#F9BAC1",
    labelText: "#FFFFFF", labelStroke: "#000000", text: "#111111"
};

var CTX = { plot: null, dur: 0, fps: 30 };   /* 드라이버가 컷마다 채운다 */
var IDX = 0;                                 /* 드라이버가 레이어마다 채운다 */

/*  레이어 이름은 **만들 때 확정한다.**
    나중에 번호를 붙여 이름을 바꾸면, 이름으로 서로를 가리키는 표현식이 통째로 끊긴다
    — 라벨판이 글자 폭을 못 읽어 안 그려졌다. 프레임 대조로 잡았다.  */
function LN(s) { return (IDX + 1) + " " + s; }

/* 표현식 머리(camHead·easeHead·head)는 _ae.jsx 에 있다 */

function num(v, d) { return v == null ? d : v; }
function tIn(L)  { return (L["in"] && L["in"].length) ? L["in"][0] : 0; }
function inSpec(L)  { return (L["in"] && L["in"].length) ? L["in"] : null; }
function outSpec(L) { return (L["out"] && L["out"].length) ? L["out"] : null; }
/** 봉 또는 고정 x 를 표현식 조각으로 */
function xOf(bar, fallbackX) { return bar != null ? "px(" + bar + ")" : String(fallbackX); }

/** 렌더러가 chart.clipPlot 으로 자르는 것 — 마스크로 옮긴다 (plot 은 고정이라 정적이면 된다) */
function clipToPlot(L) {
    var p = CTX.plot;
    var m = L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    m.name = "차트 영역";
    m.property("ADBE Mask Shape").setValue(shapeFrom(rectVerts(p.x, p.y, p.w, p.h)));
    return m;
}
function fadeL(L, l) { return fade(L, inSpec(l), outSpec(l), CTX.dur, CTX.fps); }

var TYPES = {};

/* ══════════════════════════════════════════════════════════
   cmgLevel — 수평선 + (선택) 색 영역 + (선택) 라벨.  두 편에서 14번 쓴다.
   렌더러: 채움(불투명도 55) → 그 위 굵기 th 선 → 선 시작점 왼쪽에 각진 라벨판.
   왼→오 자라나기 w = (plot.right - x0) * outExpo.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgLevel = function (L) {
    var p = CTX.plot;
    var made = [];
    var IN = tIn(L), GROW = num(L.growDur, 0.45);
    var th = num(L.thickness, 13);
    var col = color2(L.color, TH.tp);
    var label = L.label;
    var nm = label ? label : ("수평선 " + L.price);

    var x0 = xOf(L.fromBar, num(L.fromX, p.x));
    var grow = "_sp(time," + IN + "," + (IN + GROW) + ",_outExpo)";
    var w = "((" + p.right + " - " + x0 + ") * " + grow + ")";
    var y1 = "py(" + L.price + ")";

    var box = localIsComp(newShape(LN(nm + " 선")));
    /*  ⚠ 먼저 추가한 그룹이 **위**다 — 캔버스와 반대다.
        캔버스는 채움을 먼저 칠하고 그 위에 선을 얹으므로 AE 에서는 선을 먼저 넣는다.
        반대로 두면 55% 채움이 굵은 선의 윗절반을 덮는다 (파일럿에서 프레임 대조로 잡았다). */
    var gLine = addGroup(box, "선");
    addRect(gLine, w + ", " + th, x0 + " + " + w + "/2, " + y1);
    addFill(gLine, col.hex, col.opacity, label ? label : "선");

    if (L.fillTo != null) {
        var y2 = "py(" + L.fillTo + ")";
        var fc = color2(L.fill, TH.tpFill);
        var gFill = addGroup(box, "채움");
        addRect(gFill, w + ", Math.abs(" + y2 + " - " + y1 + ")",
                       x0 + " + " + w + "/2, (" + y1 + " + " + y2 + ")/2");
        addFill(gFill, fc.hex, Math.round(num(L.fillOpacity, 0.55) * 100), (label ? label : "선") + " 영역");
    }
    clipToPlot(box);
    fadeL(box, L);
    made.push(box);

    if (!label) return made;

    var lDelay = num(L.labelDelay, 0.12);
    var lSize  = num(L.labelSize, 62);

    if (L.labelStyle === "inzone" && L.fillTo != null) {
        /* 최종본 스타일 — 영역 한가운데 흰 글씨 + 얇은 검정 외곽선. 판을 쓰지 않는다. */
        var y2b = "py(" + L.fillTo + ")";
        var T = textLayer(LN(nm + " 라벨"), label, F_TAG, lSize,
                          num(L.labelColor, TH.labelText), TH.labelStroke, lSize * 0.075);
        trackTextCenter(T, x0 + " + " + w + " * " + num(L.labelFrac, 0.55),
                           "(" + y1 + " + " + y2b + ")/2");
        fade(T, [IN + lDelay, 0.4], outSpec(L), CTX.dur, CTX.fps);
        made.push(T);
        return made;
    }

    /*  판 크기를 글자에 물려 둔다 — 팀장이 문구를 바꾸면 판이 따라 커진다(A6 합격선).
        bx 는 렌더러와 같은 규칙: labelSide 'right' 면 앵커에서 오른쪽, 아니면 왼쪽.
        labelClamp 가 꺼져 있지 않으면 plot 안으로 물린다.                              */
    var T2 = textLayer(LN(nm + " 라벨"), label, F_TAG, lSize, num(L.labelColor, TH.labelText), TH.labelStroke, 0);
    var anchor = L.labelX != null ? String(L.labelX) : x0;
    var padX = num(L.labelPadX, 24);
    var bh = num(L.labelHeight, lSize * 1.35);

    var bwCalc = 'var _t = thisComp.layer("' + T2.name + '");\n'
               + 'var _r = _t.sourceRectAtTime(time, false);\n'
               + 'var bw = _r.width + ' + (padX * 2) + ';\n';
    var bxCalc = 'var bx = ' + (L.labelSide === "right" ? anchor : "(" + anchor + " - bw)") + ';\n'
               + (L.labelClamp === false ? ''
                  : 'bx = Math.min(Math.max(bx, ' + (p.x + 6) + '), ' + p.right + ' - bw - 6);\n');

    var B = localIsComp(newShape(LN(nm + " 라벨판")));
    var gB = addGroup(B, "판");
    var rc = gB.addProperty("ADBE Vector Shape - Rect");
    rc.property("ADBE Vector Rect Size").expression = head() + bwCalc + "[bw, " + bh + "]";
    rc.property("ADBE Vector Rect Position").expression = head() + bwCalc + bxCalc + "[bx + bw/2, " + y1 + "]";
    addFill(gB, col.hex, null, (label ? label : "선") + " 판");
    /*  글자를 먼저 만들었으니 판이 **위**에 온다 — 글자를 덮는다. 판을 글자 밑으로 내린다.
        (화살표 태그와 같은 함정이다. AE 는 나중에 만든 레이어가 위다.)  */
    B.moveAfter(T2);
    fade(B, [IN + lDelay, 0.35], outSpec(L), CTX.dur, CTX.fps);

    /* 글자는 판과 같은 식을 써서 함께 움직인다 */
    var off = fx(T2).addProperty("ADBE Point Control");
    off.name = "손보정";
    off.property(1).setValue([0, 0]);
    tr(T2).property("ADBE Anchor Point").setValue([0, 0]);
    tr(T2).property("ADBE Position").expression = head()
        + 'var o = effect("손보정")(1);\n'
        + 'var _r = thisLayer.sourceRectAtTime(time, false);\n'
        + 'var bw = _r.width + ' + (padX * 2) + ';\n'
        + bxCalc
        + '[bx + bw/2 - (_r.left + _r.width/2) + o[0], (' + y1 + ') + 2 - (_r.top + _r.height/2) + o[1]]';
    fade(T2, [IN + lDelay, 0.35], outSpec(L), CTX.dur, CTX.fps);

    made.push(B);
    made.push(T2);
    return made;
};

/* ══════════════════════════════════════════════════════════
   cmgCircle — 손그림 타원.  두 편에서 9번. 반지름이 픽셀 고정이라 **점에 붙는다.**
   렌더러: 반지름에 미세한 흔들림을 준 폴리라인을 turns 만큼 그린다 (drawDur 동안 자란다).
   AE 에서는 전체 경로를 만들어 두고 트림 패스로 같은 비율만큼 드러낸다.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgCircle = function (L) {
    var IN = tIn(L), DRAW = num(L.drawDur, 0.7);
    var rx = num(L.rx, 150), ry = num(L.ry, 110);
    var turns = num(L.turns, 1.12);
    var start = num(L.startAngle, -Math.PI * 0.62);
    var col = color2(L.color, TH.accent);

    var S = newShape(LN("동그라미 " + (L.bar != null ? "봉" + L.bar : "")));
    var g = addGroup(S, "손그림");
    var steps = Math.max(2, Math.round(turns * 90));
    var verts = [];
    for (var i = 0; i <= steps; i++) {
        var a = start + (i / 90) * Math.PI * 2;
        /* 렌더러와 같은 흔들림 식 — 손으로 그린 느낌이 이 두 항에서 나온다 */
        var wob = 1 + Math.sin(a * 3.1 + 0.7) * 0.028 + Math.sin(a * 5.3) * 0.018;
        verts.push([Math.cos(a) * rx * wob, Math.sin(a) * ry * wob]);
    }
    addPath(g, shapeFrom(verts, false));
    addStroke(g, col.hex, num(L.width, 11), true, null, "동그라미");

    /* 그려지는 비율을 표현식으로 — 렌더러의 span(t, in, in+drawDur, outCubic) 그대로 */
    var trim = S.property("ADBE Root Vectors Group").addProperty("ADBE Vector Filter - Trim");
    trim.property("ADBE Vector Trim End").expression =
        easeHead() + "_sp(time," + IN + "," + (IN + DRAW) + ",_outCubic) * 100";

    trackPoint(S, "px(" + L.bar + ") + " + num(L.dx, 0),
                  "py(" + L.price + ") + " + num(L.dy, 0));
    fadeL(S, L);
    return [S];
};

/* ══════════════════════════════════════════════════════════
   cmgArrow — 매수/매도 화살표 태그.  두 편에서 11번.
   브랜드 버튼(brand/ui/매수 버튼(좌우).png) 실측 비율:
     글씨높이/버튼높이 0.761 · (버튼폭-글씨폭)/높이 0.659 · 촉 0.49·h · 모서리 0.08·h
   글씨는 몸통 한가운데에서 촉 쪽으로 0.04·h 밀려 있다.
   등장(pop)은 **폭만** 커진다 — 촉 길이는 그대로다. 그래서 경로를 표현식으로 만든다.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgArrow = function (L) {
    var IN = tIn(L), POP = num(L.popDur, 0.4);
    var size = num(L.size, 36);
    var buy = num(L.dir, "buy") === "buy";
    var col = color2(L.color, buy ? TH.buy : TH.sell);
    var label = L.label != null ? L.label : (buy ? "매수" : "매도");
    var dirRight = L.point !== "left";
    var d = dirRight ? 1 : -1;
    var gap = num(L.gap, 14);

    /* 글씨를 먼저 만들어 **AE 가 잰 잉크 크기**로 버튼을 그린다 (폰트를 바꿔도 비율 유지) */
    var T = textLayer(LN("태그 " + label + " 글씨"), label, F_TAG, size,
                      TH.labelText, TH.labelStroke, num(L.textStroke, 0));
    var r = inkOf(T);
    var inkW = r.width, inkH = r.height;
    var h = num(L.height, inkH / num(L.inkRatio, 0.761));
    var W = inkW + num(L.padRatio, 0.659) * h;
    var head_ = num(L.headRatio, 0.49) * h;
    var rad = num(L.radius, h * 0.08);

    var S = newShape(LN("태그 " + label));
    var g = addGroup(S, "버튼");
    var pathProp = g.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape");
    /*  촉을 원점에 두고 로컬 좌표로 그린다. pop 은 폭 w 만 키운다 —
        2차 베지어를 3차로 옮길 때 접선 = 2/3·(제어점 − 꼭짓점).                      */
    pathProp.expression = easeHead()
        + "var pop = " + (POP <= 0 ? "1" : "_sp(time," + IN + "," + (IN + POP) + ",_outBack)") + ";\n"
        + "var w = " + W + " * pop, h = " + h + ", hd = " + head_ + ", r = " + rad + ", d = " + d + ";\n"
        + "var x0 = -d*w, x1 = -d*hd, top = -h/2, bot = h/2, k = 2/3;\n"
        + "var pts = [[0,0],[x1,top],[x0+d*r,top],[x0,top+r],[x0,bot-r],[x0+d*r,bot],[x1,bot]];\n"
        + "var ai = [[0,0],[0,0],[0,0],[0,k*(-r)],[0,0],[0,0],[0,0]];\n"
        + "var ao = [[0,0],[0,0],[-d*k*r,0],[0,0],[0,k*r],[0,0],[0,0]];\n"
        + "ai[5] = [-d*k*r,0];\n"
        + "createPath(pts, ai, ao, true)";
    addFill(g, col.hex, col.opacity, "태그 " + label);

    var tipX = "px(" + L.bar + ") - " + (d * gap);
    var cy = L.price != null ? "py(" + L.price + ")" : "py(" + num(L.priceResolved, 0) + ")";
    trackPoint(S, tipX, cy);

    /* 글씨는 몸통 한가운데에서 촉 쪽으로 0.04·h. pop 중에는 몸통도 좁으므로 같은 식을 쓴다. */
    var bodyOff = easeHead()
        + "var pop = " + (POP <= 0 ? "1" : "_sp(time," + IN + "," + (IN + POP) + ",_outBack)") + ";\n"
        + "var w = " + W + " * pop;\n"
        + "var bcx = -" + d + "*(" + head_ + " + (w - " + head_ + ")/2) + " + d + "*" + (h * 0.04) + ";\n";
    var offT = fx(T).addProperty("ADBE Point Control");
    offT.name = "손보정";
    offT.property(1).setValue([0, 0]);
    tr(T).property("ADBE Anchor Point").setValue([0, 0]);
    tr(T).property("ADBE Position").expression = camHead() + bodyOff
        + 'var o = effect("손보정")(1);\n'
        + 'var _r = thisLayer.sourceRectAtTime(time, false);\n'
        + '[(' + tipX + ') + bcx - (_r.left + _r.width/2) + o[0], (' + cy + ') + 2 - (_r.top + _r.height/2) + o[1]]';

    /*  글씨를 먼저 만들었으므로 나중에 만든 셰이프가 **위**에 온다 — 글씨를 덮는다.
        셰이프를 글씨 밑으로 내린다 (파일럿에서도 같은 데 물렸다).  */
    S.moveAfter(T);
    fadeL(S, L);
    fadeL(T, L);
    return [S, T];
};
