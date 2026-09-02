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
/*  넣은 알파 키 수와 실측 오차를 모아 둔다 — 드라이버가 컷마다 보고한다 */
var ALPHA = { keys: 0, err: 0 };
function _alpha(layer, fn) {
    var r = setAlpha(layer, fn, CTX.dur, CTX.fps);
    ALPHA.keys += r.keys;
    if (r.err > ALPHA.err) ALPHA.err = r.err;
    return r;
}
/** 등장·퇴장을 렌더러 cue() 그대로 */
function fadeL(layer, l) {
    return _alpha(layer, function (t) { return cueJS(t, l); });
}
/** cue 에 곱해지는 연출 알파까지 함께 (라벨 팝처럼 alpha 를 한 번 더 곱하는 것들) */
function fadeMul(layer, l, extra) {
    return _alpha(layer, function (t) { return cueJS(t, l) * clampJS(extra(t)); });
}

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
        /* 렌더러: cue × clamp(span(in+labelDelay, +0.4, outCubic)) */
        fadeMul(T, L, function (t) { return spanJS(t, IN + lDelay, IN + lDelay + 0.4, E.outCubic); });
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
    /* 렌더러: cue × clamp(span(in+labelDelay, +0.35, outBack)) — 살짝 튀어나온다 */
    var labelA = function (t) { return spanJS(t, IN + lDelay, IN + lDelay + 0.35, E.outBack); };
    fadeMul(B, L, labelA);

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
    fadeMul(T2, L, labelA);

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
    /*  렌더러는 pop 이 0.5 를 넘은 뒤에야 글씨를 그리고, clamp((pop-0.5)*3) 을 곱한다.  */
    fadeMul(T, L, function (t) {
        var pop = POP <= 0 ? 1 : spanJS(t, IN, IN + POP, E.outBack);
        return pop > 0.5 ? (pop - 0.5) * 3 : 0;
    });
    return [S, T];
};

/* ══════════════════════════════════════════════════════════
   cmgNote — 차트 위 짧은 주석.  두 편에서 12번, 가장 많이 쓴다.
   흰 글씨 + 검정 외곽선(굵기 size*0.16), 등장할 때 18px 아래에서 올라온다.
   폰트가 태그와 다르다 — 주석은 타이틀 계열(Gmarket Sans Bold)이다.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgNote = function (L) {
    var IN = tIn(L);
    var size = num(L.size, 56);
    var T = textLayer(LN("문구 " + String(L.text).replace(/\s+/g, " ")), L.text, F_NOTE, size,
                      num(L.color, "#FFFFFF"), num(L.stroke, "#000000"), num(L.strokeWidth, size * 0.16));
    var x = L.bar != null ? "px(" + L.bar + ") + " + num(L.dx, 0) : String(num(L.x, 0));
    var y = (L.price != null ? "py(" + L.price + ")" : String(num(L.y, 0))) + " + " + num(L.dy, 0);
    /* 올라오며 등장 — translate(0, (1-rise)*18) 를 그대로 옮긴다 */
    var rise = "(1 - _sp(time," + IN + "," + (IN + 0.45) + ",_outCubic)) * 18";
    trackTextCenter(T, x, "(" + y + ") + " + rise);
    /* trackTextCenter 는 camHead 만 넣는다 — 이징이 필요하니 앞에 덧댄다 */
    var pos = tr(T).property("ADBE Position");
    pos.expression = easeHead() + pos.expression;
    fadeL(T, L);
    return [T];
};

/* ══════════════════════════════════════════════════════════
   flash — 컷 전환용 화면 전체 플래시. 화면 고정이라 카메라와 무관하다.
   알파 = sin(p*π) * strength,  p = (t - at)/dur 선형.
   ══════════════════════════════════════════════════════════ */
TYPES.flash = function (L) {
    var at = num(L.at, 0), dur = num(L.dur, 0.3);
    var c = color2(L.color, "#FFFFFF");
    var S = COMP.layers.addSolid(hex(c.hex), LN("플래시"), COMP.width, COMP.height, 1, CTX.dur);
    var str = num(L.strength, 0.85);
    /* 플래시는 사인 곡선이라 이징 하나로 안 맞는다 — setAlpha 가 재 보고 키를 더 넣는다 */
    _alpha(S, function (t) {
        var p = spanJS(t, at, at + dur, E.linear);
        return (p <= 0 || p >= 1) ? 0 : Math.sin(p * Math.PI) * str;
    });
    return [S];
};

/* ══════════════════════════════════════════════════════════
   cmgBadge — 화면 고정 배지(손익비 등). 둥근 판 + 외곽선 글씨.
   등장은 판 중심을 축으로 한 팝(outBack, 0.35s).
   판 중심과 글자 잉크 중심이 같은 점이라, 판은 크기만 키우고 글자는 Scale 로 키우면 된다.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgBadge = function (L) {
    var IN = tIn(L);
    var size = num(L.size, 46);
    var col = color2(L.color, TH.accent);
    var padX = size * 0.5, bh = size * 1.5;
    var pop = "_sp(time," + IN + "," + (IN + 0.35) + ",_outBack)";

    var T = textLayer(LN("배지 " + L.text), L.text, F_TAG, size,
                      TH.labelText, TH.labelStroke, size * 0.15);
    var bwCalc = 'var _r = thisComp.layer("' + T.name + '").sourceRectAtTime(time, false);\n'
               + 'var bw = _r.width + ' + (padX * 2) + ';\n';
    var align = num(L.align, "left");
    var bx = align === "right" ? "(" + L.x + " - bw)" : align === "center" ? "(" + L.x + " - bw/2)" : String(L.x);

    var B = localIsComp(newShape(LN("배지판 " + L.text)));
    var gB = addGroup(B, "판");
    var rc = gB.addProperty("ADBE Vector Shape - Rect");
    rc.property("ADBE Vector Rect Roundness").setValue(num(L.radius, 10));
    /* 판 중심이 곧 팝의 축이라 크기만 키우면 된다 */
    rc.property("ADBE Vector Rect Size").expression = head() + bwCalc + "[bw * " + pop + ", " + bh + " * " + pop + "]";
    rc.property("ADBE Vector Rect Position").expression = head() + bwCalc + "[" + bx + " + bw/2, " + L.y + "]";
    addFill(gB, col.hex, null, "강조");
    if (L.border !== false) addStroke(gB, "#000000", 4, false, null, "배지 테두리");
    B.moveAfter(T);

    /* 글자는 판 한가운데 — 캔버스가 bx+padX 에 왼쪽정렬로 그리므로 잉크 중심이 판 중심이다 */
    var offT = fx(T).addProperty("ADBE Point Control");
    offT.name = "손보정";
    offT.property(1).setValue([0, 0]);
    tr(T).property("ADBE Anchor Point").expression =
        'var r = thisLayer.sourceRectAtTime(time, false);\n[r.left + r.width/2, r.top + r.height/2]';
    tr(T).property("ADBE Position").expression = head() + bwCalc
        + 'var o = effect("손보정")(1);\n[' + bx + ' + bw/2 + o[0], ' + (L.y + 2) + ' + o[1]]';
    tr(T).property("ADBE Scale").expression = easeHead() + "var p = " + pop + ";\n[p*100, p*100]";

    fadeL(B, L);
    fadeL(T, L);
    return [B, T];
};

/* ══════════════════════════════════════════════════════════
   cmgUnderline — 손그림 밑줄. 흔들리는 폴리라인을 왼→오로 긋는다.
   렌더러는 그어지는 만큼만 다시 계산해 흔들림이 늘어나지만, AE 는 전체 경로를
   만들어 두고 트림으로 드러낸다. 0.35초짜리 연출이라 차이는 그 구간에만 있다.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgUnderline = function (L) {
    var IN = tIn(L), DRAW = num(L.drawDur, 0.5);
    var W = num(L.width, 300);
    var S = newShape(LN("밑줄"));
    var g = addGroup(S, "손그림");
    var x0 = (L.align === "center") ? -W / 2 : 0;
    var steps = Math.max(2, Math.round(W / 8));
    var verts = [];
    for (var i = 0; i <= steps; i++) {
        var p = i / steps;
        verts.push([x0 + W * p, Math.sin(p * 7.3 + 1.1) * 3.2 + Math.sin(p * 2.1) * 2.4]);
    }
    addPath(g, shapeFrom(verts, false));
    addStroke(g, color2(L.color, "#C0272D").hex, num(L.thickness, 12), true, null, "밑줄");
    var trim = S.property("ADBE Root Vectors Group").addProperty("ADBE Vector Filter - Trim");
    trim.property("ADBE Vector Trim End").expression =
        easeHead() + "_sp(time," + IN + "," + (IN + DRAW) + ",_outCubic) * 100";

    var x = L.bar != null ? "px(" + L.bar + ") + " + num(L.dx, 0) : String(num(L.x, 0));
    var y = (L.price != null ? "py(" + L.price + ")" : String(num(L.y, 0))) + " + " + num(L.dy, 0);
    trackPoint(S, x, y);
    fadeL(S, L);
    return [S];
};

/* ══════════════════════════════════════════════════════════
   cmgMissed — "이만큼 더 먹을 수 있었다" 빗금. 아래에서 위로 자란다.
   10% 바탕 + 42px 간격 45° 사선(28%). 자라는 사각형으로 잘린다.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgMissed = function (L) {
    var p = CTX.plot;
    var IN = tIn(L), GROW = num(L.growDur, 0.8);
    var col = color2(L.color, TH.accent);
    var x0 = xOf(L.fromBar, p.x), x1 = xOf(L.toBar, p.right);
    var yF = "py(" + L.from + ")", yT = "py(" + L.to + ")";
    var grow = "_sp(time," + IN + "," + (IN + GROW) + ",_outExpo)";
    var hE = "(Math.abs(" + yT + " - " + yF + ") * " + grow + ")";
    var yb = "Math.max(" + yF + ", " + yT + ")";
    var wE = "((" + x1 + ") - (" + x0 + "))";

    var S = localIsComp(newShape(LN("빗금")));
    /* 사선이 위, 바탕이 아래 — 먼저 추가한 것이 위다 */
    var g2 = addGroup(S, "사선");
    var pth = g2.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape");
    pth.expression = head()
        + "var h = " + hE + ", yb = " + yb + ", a = " + x0 + ";\n"
        + "createPath([[a - h, yb],[a, yb - h]], [], [], false)";
    addStroke(g2, col.hex, 6, false, 28, "빗금선");
    var rep = g2.addProperty("ADBE Vector Filter - Repeater");
    rep.property("ADBE Vector Repeater Copies").expression = head()
        + "var h = " + hE + ";\nMath.max(1, Math.ceil((" + wE + " + h*2)/42) + 1)";
    rep.property("ADBE Vector Repeater Transform").property("ADBE Vector Repeater Position").setValue([42, 0]);

    var g1 = addGroup(S, "바탕");
    addRect(g1, wE + ", " + hE, "((" + x0 + ") + (" + x1 + "))/2, " + yb + " - " + hE + "/2");
    addFill(g1, col.hex, 10, "빗금 바탕");

    /*  렌더러는 자라는 사각형으로 clip 한 뒤 다시 plot 으로 clip 한다.
        마스크 패스도 표현식을 받으므로 자라는 사각형을 그대로 옮긴다.  */
    var m = S.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    m.name = "자라는 영역";
    m.property("ADBE Mask Shape").expression = head()
        + "var h = " + hE + ", yb = " + yb + ";\n"
        + "var a = Math.max(" + x0 + ", " + p.x + "), b = Math.min(" + x1 + ", " + p.right + ");\n"
        + "var t = Math.max(yb - h, " + p.y + ");\n"
        + "createPath([[a,t],[b,t],[b,yb],[a,yb]], [], [], true)";
    fadeL(S, L);
    return [S];
};

/* ══════════════════════════════════════════════════════════
   zone — 두 가격 사이 옅은 띠 + 점선 테두리. 왼→오로 펼쳐진다.
   ══════════════════════════════════════════════════════════ */
TYPES.zone = function (L) {
    var p = CTX.plot;
    var IN = tIn(L), GROW = num(L.growDur, 0.7);
    var col = color2(L.color, TH.ma);
    var grow = "_sp(time," + IN + "," + (IN + GROW) + ",_outExpo)";
    var w = "(" + p.w + " * " + grow + ")";
    var yA = "py(" + L.from + ")", yB = "py(" + L.to + ")";
    var top = "Math.min(" + yA + ", " + yB + ")", hgt = "Math.abs(" + yB + " - " + yA + ")";

    var S = localIsComp(newShape(LN("존")));
    var g = addGroup(S, "존");
    addRect(g, w + ", " + hgt, p.x + " + " + w + "/2, " + top + " + " + hgt + "/2");
    var st = addStroke(g, col.hex, 2, false, 60, "존 테두리");
    var dash = st.property("ADBE Vector Stroke Dashes");
    dash.addProperty("ADBE Vector Stroke Dash 1").setValue(10);
    dash.addProperty("ADBE Vector Stroke Gap 1").setValue(8);
    addFill(g, col.hex, Math.round(num(L.opacity, 0.13) * 100), "존 채움");
    fadeL(S, L);
    return [S];
};

/* ══════════════════════════════════════════════════════════
   cmgCross — 손그림 큰 ✕. 화면(플롯) 고정이라 카메라와 무관하다.
   획 두 개가 순서대로 그어진다: s1 = min(1, draw*2), s2 = max(0, draw*2-1).
   ══════════════════════════════════════════════════════════ */
TYPES.cmgCross = function (L) {
    var p = CTX.plot;
    var inset = num(L.inset, 90);
    var x0 = num(L.x0, p.x + inset), y0 = num(L.y0, p.y + inset);
    var x1 = num(L.x1, p.right - inset), y1 = num(L.y1, p.bottom - inset);
    var IN = tIn(L), DRAW = num(L.drawDur, 0.55);
    var col = color2(L.color, "#E01313");
    var S = localIsComp(newShape(LN("엑스")));

    function oneStroke(nm, ax, ay, bx, by, prog) {
        var g = addGroup(S, nm);
        var verts = [];
        for (var i = 0; i <= 24; i++) {
            var t = i / 24;
            /* 손그림 흔들림 — 시작 x 가 식에 들어가 두 획이 서로 다르게 떨린다 */
            var wob = Math.sin(t * 9.2 + ax * 0.01) * 6 + Math.sin(t * 17.7) * 3;
            verts.push([ax + (bx - ax) * t + wob * 0.4, ay + (by - ay) * t + wob]);
        }
        addPath(g, shapeFrom(verts, false));
        addStroke(g, col.hex, num(L.width, 34), true, null, nm);
        var tm = g.addProperty("ADBE Vector Filter - Trim");
        tm.property("ADBE Vector Trim End").expression = easeHead()
            + "var d = _sp(time," + IN + "," + (IN + DRAW) + ",_outCubic);\n" + prog + " * 100";
        return g;
    }
    /* 둘째 획을 먼저 넣어야 첫째 획이 위에 온다 (렌더러가 그린 순서와 같아진다) */
    oneStroke("둘째 획", x1, y0, x0, y1, "Math.max(0, d*2 - 1)");
    oneStroke("첫째 획", x0, y0, x1, y1, "Math.min(1, d*2)");
    fadeL(S, L);
    return [S];
};

/* ══════════════════════════════════════════════════════════
   cmgTrace — 이평선 한 구간을 굵게 덧칠한다("누워 있음" 강조).
   점은 내보내기가 풀어 준다(flatten 적용 완료). 봉·가격이라 카메라를 따라간다.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgTrace = function (L) {
    var IN = tIn(L), DRAW = num(L.drawDur, 0.6);
    var col = color2(L.color, TH.ma);
    var pts = L.pts || [];
    var S = localIsComp(newShape(LN("궤적")));
    var g = addGroup(S, "궤적");
    var arr = [];
    for (var i = 0; i < pts.length; i++) {
        /* 손그림 흔들림은 점 번호로 정해진다 — 미리 계산해 넣는다 */
        arr.push("[" + pts[i][0] + "," + pts[i][1] + "," + (Math.round(Math.sin(i * 1.7) * 1.5 * 100) / 100) + "]");
    }
    var pth = g.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape");
    pth.expression = head()
        + "var P = [" + arr.join(",") + "];\n"
        + "var v = [];\n"
        + "for (var i = 0; i < P.length; i++) v.push([px(P[i][0]), py(P[i][1]) + P[i][2]]);\n"
        + "createPath(v, [], [], false)";
    addStroke(g, col.hex, num(L.width, 16), true, null, "궤적");
    var tm = S.property("ADBE Root Vectors Group").addProperty("ADBE Vector Filter - Trim");
    tm.property("ADBE Vector Trim End").expression =
        easeHead() + "_sp(time," + IN + "," + (IN + DRAW) + ",_outCubic) * 100";
    var op = num(L.opacity, 0.92);
    fadeMul(S, L, function () { return op; });
    return [S];
};

/* ══════════════════════════════════════════════════════════
   cmgProfit — 진입가와 현재가 사이 평가손익 영역 + 점선 진입선.
   현재가는 프레임마다 바뀌므로 카메라 널의 LAST 슬라이더에서 읽는다.
   수익이면 초록, 손실이면 빨강 — 색도 프레임마다 갈린다.
   ══════════════════════════════════════════════════════════ */
TYPES.cmgProfit = function (L) {
    var p = CTX.plot;
    var x0 = xOf(L.fromBar, p.x), x1 = xOf(L.toBar, p.right);
    var yE = "py(" + L.entry + ")";
    var yN = 'py(thisComp.layer("' + CAM_NAME + '").effect("LAST")(1))';
    var S = localIsComp(newShape(LN("평가손익")));

    /* 점선 진입선이 위 */
    var g2 = addGroup(S, "진입선");
    var pth = g2.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape");
    pth.expression = head() + "var y = " + yE + ";\ncreatePath([[" + x0 + ", y],[" + x1 + ", y]], [], [], false)";
    var ec = color2(L.entryColor, "rgba(0,0,0,0.75)");
    var st = addStroke(g2, ec.hex, num(L.entryWidth, 5), false, ec.opacity, "진입선");
    var dash = st.property("ADBE Vector Stroke Dashes");
    dash.addProperty("ADBE Vector Stroke Dash 1").setValue(18);
    dash.addProperty("ADBE Vector Stroke Gap 1").setValue(12);

    var g1 = addGroup(S, "영역");
    addRect(g1, "((" + x1 + ") - (" + x0 + ")), Math.abs(" + yN + " - " + yE + ")",
                "((" + x0 + ") + (" + x1 + "))/2, (" + yE + " + " + yN + ")/2");
    var f = addFill(g1, TH.tpFill, Math.round(num(L.opacity, 0.6) * 100), "평가손익 색");
    /* 수익이면 초록, 손실이면 빨강 — 프레임마다 갈린다 */
    f.property("ADBE Vector Fill Color").expression =
        'var now = thisComp.layer("' + CAM_NAME + '").effect("LAST")(1);\n'
        + "var up = now >= " + L.entry + ";\n"
        + "up ? [" + hex(TH.tpFill).join(",") + ",1] : [" + hex(TH.slFill).join(",") + ",1]";
    fadeL(S, L);
    return [S];
};

/* ══════════════════════════════════════════════════════════
   titleCard — CTA 카드. 어두운 스크림 + 큰 타이틀 + 강조 밑줄.
   화면 고정이라 카메라와 무관하다. 등장 이징이 다르다(outQuart).

   스크림은 세로 그라데이션(알파 0.86 → 0.72 → 0.9)인데, AE 스크립트로는
   그라데이션 칠의 색 정지점을 못 박는다(공식 API 가 없다). 그래서 가로 띠
   54장으로 나눠 각 띠의 칠 불투명도를 직접 준다 — 계단 폭이 0.6/255 라 안 보인다.
   ══════════════════════════════════════════════════════════ */
TYPES.titleCard = function (L) {
    var W = COMP.width, H = COMP.height;
    var IN = tIn(L);
    var made = [];
    var strength = num(L.scrimStrength, 1);

    /** 캔버스 그라데이션과 같은 알파: 0 → 0.86, 0.55 → 0.72, 1 → 0.9 */
    function scrimAlpha(u) {
        var a = u <= 0.55 ? 0.86 + (0.72 - 0.86) * (u / 0.55)
                          : 0.72 + (0.9 - 0.72) * ((u - 0.55) / 0.45);
        return a * strength;
    }
    if (L.scrim !== false) {
        var S = localIsComp(newShape(LN("스크림")));
        var BANDS = 108, bh = H / BANDS;   /* 1080/108 = 10px — 계단이 0.6/255 라 안 보인다 */
        for (var b = 0; b < BANDS; b++) {
            var g = addGroup(S, "띠" + (b + 1));
            /*  겹치면 안 된다 — 반투명끼리 포개져 이음새가 두 배로 진해지고 가로줄이 생긴다.
                1080/54 = 20 으로 딱 떨어져서 딱 붙여도 틈이 안 난다.  */
            addPath(g, shapeFrom(rectVerts(0, b * bh, W, bh)));
            addFill(g, "#04070C", Math.round(scrimAlpha((b + 0.5) / BANDS) * 1000) / 10, "스크림 띠");
        }
        /* 등장 이징이 outCubic 이 아니라 outQuart 다 */
        _alpha(S, function (t) { return titleCue(t, L); });
        made.push(S);
    }

    /*  타이틀 — 캔버스는 textBaseline 'alphabetic' 이라 y 가 베이스라인이다.
        AE 의 점 텍스트도 Position 이 베이스라인이므로 그대로 맞는다.        */
    var cx = num(L.x, W / 2), baseY = num(L.y, H * 0.46);
    var lines = (L.title instanceof Array) ? L.title : [L.title];
    var lh = num(L.lineHeight, 124);
    for (var i = 0; i < lines.length; i++) {
        (function (line, k) {
            var T = textLayer(LN("타이틀 " + line), line, F_NOTE, num(L.size, 108),
                              num(L.color, TH.text), TH.labelStroke, 0);
            var t0 = IN + 0.12 + k * 0.14, t1 = t0 + 0.7;
            /* riseText: 46px 아래에서 올라오며 blur 10 → 0, 알파는 p*1.2 를 clamp */
            tr(T).property("ADBE Anchor Point").setValue([0, 0]);
            tr(T).property("ADBE Position").expression = easeHead()
                + "var p = _sp(time," + t0 + "," + t1 + ",_outQuart);\n"
                + "[" + cx + ", " + (baseY + k * lh) + " + (1-p)*46]";
            var bl = fx(T).addProperty("ADBE Box Blur2");
            bl.property("ADBE Box Blur2-0001").expression = easeHead()
                + "var p = _sp(time," + t0 + "," + t1 + ",_outQuart);\n(1-p)*10";
            _alpha(T, function (t) {
                return titleCue(t, L) * clampJS(spanJS(t, t0, t1, E.outQuart) * 1.2);
            });
            made.push(T);
        })(lines[i], i);
    }

    if (L.rule !== false) {
        var y = baseY + (lines.length - 1) * lh;
        var rw = num(L.ruleWidth, 200);
        var R = localIsComp(newShape(LN("강조 밑줄")));
        var gr = addGroup(R, "밑줄");
        var rc = gr.addProperty("ADBE Vector Shape - Rect");
        var r0 = IN + 0.25, r1 = IN + 0.95;
        rc.property("ADBE Vector Rect Size").expression = easeHead()
            + "var p = _sp(time," + r0 + "," + r1 + ",_outExpo);\n[" + rw + "*p, 5]";
        rc.property("ADBE Vector Rect Position").setValue([cx, y + num(L.ruleGap, 120) + 2.5]);
        addFill(gr, num(L.kickerColor, TH.accent), null, "강조 밑줄");
        _alpha(R, function (t) { return titleCue(t, L); });
        made.push(R);
    }
    return made;
};
/** titleCard 만 등장 이징이 outQuart 다 (layers.js 의 cue 세 번째 인자) */
function titleCue(t, L) {
    var i = L["in"], o = L["out"];
    var enter = (i && i.length) ? spanJS(t, i[0], i[0] + i[1], E.outQuart) : 1;
    var exit  = (o && o.length) ? 1 - spanJS(t, o[0], o[0] + o[1], E.inOutQuad) : 1;
    return Math.min(enter, exit);
}
