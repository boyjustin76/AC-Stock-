/*  AE 셰이프·텍스트를 짓는 공용 도구. a3_build(파일럿)에서 뜯어내 일반화했다.

    파일럿과 달라진 점 하나 — **좌표가 표현식으로 온다.**
    파일럿은 카메라가 멈춘 컷 하나라 픽셀을 박아 넣었지만, 실제 11컷 중 10컷이 움직인다.
    그래서 "차트 카메라" 널에서 X0·BW·Y0·K 를 꺼내 쓴다:  x = X0 + 봉*BW,  y = Y0 - 가격*K

    붙는 방식이 둘이다:
      점(point)    — 크기가 픽셀로 고정된 그림. Position 만 추적한다.
                     (동그라미·화살표 태그·문구·밑줄)
      영역(region) — 차트 좌표로 범위를 덮는 그림. 크기까지 표현식이라야 한다.
                     (수평선 박스·빗금·존)

    파일럿에서 배운 규칙은 그대로 지킨다:
      · 글자폭은 AE 가 재게 한다(sourceRectAtTime). 캔버스 measureText 를 옮겨 적지 않는다.
      · 폰트는 getFontsByPostScriptName 으로 존재를 먼저 확인한다 — d.font 는 없는 이름도 받는다.
      · 셰이프 그룹은 **먼저 추가한 것이 위**다. 캔버스와 반대다.
      · 등장·퇴장은 불투명도 키프레임, 자라나기는 마스크나 트림 패스.
*/

var COMP = null;                  /* 드라이버가 컷마다 갈아 끼운다 */
var CAM_NAME = "차트 카메라";
var NL = String.fromCharCode(10);   /* 표현식 줄바꿈 */

/* 폰트 — src/render/scene.html 의 @font-face 매핑 실측
   태그·라벨·뱃지 = fontTag 'S-Core Dream' 500  → S-CoreDream-5Medium
   차트 위 주석   = font    'Gmarket Sans' 700 → GmarketSansBold           */
var F_TAG  = "S-CoreDream-5Medium";
var F_NOTE = "GmarketSansBold";

function hex(h) {
    if (String(h).charAt(0) !== "#") return [0, 0, 0];
    return [parseInt(h.substr(1, 2), 16) / 255, parseInt(h.substr(3, 2), 16) / 255, parseInt(h.substr(5, 2), 16) / 255];
}
/** 씬은 rgba(0,0,0,0.72) 형태도 쓴다 → {hex, opacity} 로 갈라 준다 */
function color2(c, fallback) {
    var s = String(c == null ? fallback : c);
    var m = s.match(/rgba?\(([^)]+)\)/);
    if (m) {
        var p = m[1].split(",");
        var to = function (n) { var v = Math.round(parseFloat(n)); return ("0" + v.toString(16)).slice(-2); };
        return { hex: "#" + to(p[0]) + to(p[1]) + to(p[2]), opacity: p.length > 3 ? Math.round(parseFloat(p[3]) * 100) : null };
    }
    return { hex: s, opacity: null };
}

function tr(L) { return L.property("ADBE Transform Group"); }
function fx(L) { return L.property("ADBE Effect Parade"); }

/* ── 카메라 표현식 ───────────────────────────────────── */

/** 표현식 머리 — px(봉)·py(가격) 를 쓸 수 있게 한다 */
function camHead() {
    return 'var c = thisComp.layer("' + CAM_NAME + '");\n'
         + 'var X0 = c.effect("X0")(1), BW = c.effect("BW")(1);\n'
         + 'var Y0 = c.effect("Y0")(1), K = c.effect("K")(1);\n'
         + 'function px(b){ return X0 + b*BW; }\n'
         + 'function py(p){ return Y0 - p*K; }\n';
}

/** 렌더러의 span()·Ease 를 그대로 옮긴 표현식 머리 */
function easeHead() {
    return 'function _sp(t,a,b,e){ if(b<=a) return t>=b?1:0; var p=(t-a)/(b-a); p=p<0?0:(p>1?1:p); return e(p); }' + NL
         + 'function _linear(p){ return p; }' + NL
         + 'function _outCubic(p){ return 1-Math.pow(1-p,3); }' + NL
         + 'function _outQuart(p){ return 1-Math.pow(1-p,4); }' + NL
         + 'function _outExpo(p){ return p>=1?1:1-Math.pow(2,-10*p); }' + NL
         + 'function _outBack(p){ return 1+2.2*Math.pow(p-1,3)+1.2*Math.pow(p-1,2); }' + NL;
}
/** 거의 모든 표현식이 좌표와 이징을 함께 쓴다 */
function head() { return camHead() + easeHead(); }

/**
 * 점에 붙이기. 그림은 원점(0,0) 둘레에 그려 두고 Position 이 추적한다.
 * "손보정" 포인트 컨트롤을 함께 달아 둔다 — 사람이 밀어도 추적이 안 깨진다.
 */
function trackPoint(L, xExpr, yExpr) {
    var off = fx(L).addProperty("ADBE Point Control");
    off.name = "손보정";
    off.property(1).setValue([0, 0]);   /* 기본값이 컴포 중앙이라 반드시 내려야 한다 */
    tr(L).property("ADBE Anchor Point").setValue([0, 0]);
    tr(L).property("ADBE Position").expression =
        camHead() + 'var o = effect("손보정")(1);\n[(' + xExpr + ') + o[0], (' + yExpr + ') + o[1]]';
    return L;
}
/** 영역용 — 레이어 좌표 = 컴포 좌표로 두고, 그림 쪽을 표현식으로 움직인다 */
function localIsComp(L) {
    tr(L).property("ADBE Anchor Point").setValue([0, 0]);
    tr(L).property("ADBE Position").setValue([0, 0]);
    return L;
}

/* ── 셰이프 ─────────────────────────────────────────── */

function shapeFrom(verts, closed, inT, outT) {
    var s = new Shape();
    s.vertices = verts;
    s.closed = closed !== false;
    var z = [];
    for (var i = 0; i < verts.length; i++) z.push([0, 0]);
    s.inTangents = inT || z;
    s.outTangents = outT || z;
    return s;
}
function rectVerts(x, y, w, h) { return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]; }

function newShape(name) {
    var L = COMP.layers.addShape();
    L.name = name;
    return L;
}
/*  그룹·칠에 이름을 준다. 한국어 판 AE 기본 이름은 "그룹 1"·"칠 1" 이라 로케일에 물린다. */
function addGroup(L, nm) {
    var g = L.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    if (nm) g.name = nm;
    return g.property("ADBE Vectors Group");
}
function addPath(g, shape) {
    var p = g.addProperty("ADBE Vector Shape - Group");
    p.property("ADBE Vector Shape").setValue(shape);
    return p;
}
function addFill(g, colorHex, opacity, nm) {
    var f = g.addProperty("ADBE Vector Graphic - Fill");
    if (nm) f.name = nm;
    f.property("ADBE Vector Fill Color").setValue(hex(colorHex));
    if (opacity != null) f.property("ADBE Vector Fill Opacity").setValue(opacity);
    return f;
}
function addStroke(g, colorHex, width, roundCap, opacity, nm) {
    var s = g.addProperty("ADBE Vector Graphic - Stroke");
    if (nm) s.name = nm;
    s.property("ADBE Vector Stroke Color").setValue(hex(colorHex));
    s.property("ADBE Vector Stroke Width").setValue(width);
    if (opacity != null) s.property("ADBE Vector Stroke Opacity").setValue(opacity);
    if (roundCap) {
        s.property("ADBE Vector Stroke Line Cap").setValue(2);
        s.property("ADBE Vector Stroke Line Join").setValue(2);
    }
    return s;
}
/** 파라메트릭 사각형 — 크기·위치를 표현식으로 물릴 수 있다 (영역 그림용) */
function addRect(g, sizeExpr, posExpr, roundness) {
    var rc = g.addProperty("ADBE Vector Shape - Rect");
    if (roundness) rc.property("ADBE Vector Rect Roundness").setValue(roundness);
    /*  이징 함수까지 넣어야 한다 — 크기 식에 자라나기(_sp·_outExpo)가 들어간다.
        camHead 만 붙였다가 식이 통째로 죽어 수평선·라벨판이 안 보였다.  */
    rc.property("ADBE Vector Rect Size").expression = head() + "[" + sizeExpr + "]";
    rc.property("ADBE Vector Rect Position").expression = head() + "[" + posExpr + "]";
    return rc;
}

/* ── 시간 ───────────────────────────────────────────── */

/*  ── 이징: src/render/anim.js 를 JSX 로 옮긴 것 ──
    표현식용은 easeHead() 가 문자열로 낸다. 이쪽은 **키프레임을 구울 때** 쓴다.  */
var E = {
    linear:    function (p) { return p; },
    outCubic:  function (p) { return 1 - Math.pow(1 - p, 3); },
    outQuart:  function (p) { return 1 - Math.pow(1 - p, 4); },
    outExpo:   function (p) { return p >= 1 ? 1 : 1 - Math.pow(2, -10 * p); },
    outBack:   function (p) { return 1 + 2.2 * Math.pow(p - 1, 3) + 1.2 * Math.pow(p - 1, 2); },
    inOutQuad: function (p) { return p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2; }
};
function clampJS(v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }
function spanJS(t, a, b, e) {
    if (b <= a) return t >= b ? 1 : 0;
    return e(clampJS((t - a) / (b - a)));
}
/** anim.js cue() 그대로 — 등장은 outCubic, 퇴장은 inOutQuad 다 */
function cueJS(t, L) {
    var i = L["in"], o = L["out"];
    var enter = (i && i.length) ? spanJS(t, i[0], i[0] + i[1], E.outCubic) : 1;
    var exit  = (o && o.length) ? 1 - spanJS(t, o[0], o[0] + o[1], E.inOutQuad) : 1;
    return Math.min(enter, exit);
}

/**
 * 불투명도를 **프레임 단위로 구워** 넣는다. fn(t) 는 0~1 을 준다.
 *
 * 왜 표현식이 아니라 키프레임인가 —
 *   팀장이 손으로 끌어 싱크를 바꿀 수 있어야 한다. 표현식이면 식을 고쳐야 한다.
 * 왜 AE 이징이 아니라 굽는가 —
 *   렌더러의 등장은 outCubic 인데 AE 이지이즈로 근사했더니 페이드 중간에서
 *   60% vs 92% 로 벌어졌다(컷① 프레임 대조로 잡았다). 램프는 6~12프레임뿐이라
 *   프레임마다 찍어도 값이 싸고, 값이 안 변하는 구간은 키를 찍지 않는다.
 */
function bakeAlpha(L, fn, dur, fps) {
    var op = tr(L).property("ADBE Opacity");
    var n = Math.round(dur * fps);
    var times = [], vals = [], prev = null;
    for (var f = 0; f <= n; f++) {
        var t = f / fps;
        var v = Math.round(clampJS(fn(t)) * 10000) / 100;
        var nx = (f < n) ? Math.round(clampJS(fn((f + 1) / fps)) * 10000) / 100 : null;
        /* 값이 변하는 순간과 그 양쪽만 남긴다 — 평평한 구간은 키 두 개면 된다 */
        if (prev === null || v !== prev || (nx !== null && nx !== v)) { times.push(t); vals.push(v); }
        prev = v;
    }
    if (times.length === 1) { op.setValueAtTime(0, vals[0]); }
    else op.setValuesAtTimes(times, vals);
    /* 프레임마다 키가 있는 구간은 보간이 무의미하므로 이징을 건드리지 않는다 */
    return op;
}
/** 그려지는 연출 — 트림 패스 (손그림 동그라미·밑줄) */
function trimDraw(L, t0, t1) {
    var g = L.property("ADBE Root Vectors Group").addProperty("ADBE Vector Filter - Trim");
    var end = g.property("ADBE Vector Trim End");
    end.setValueAtTime(t0, 0);
    end.setValueAtTime(t1, 100);
    for (var i = 1; i <= end.numKeys; i++) {
        try { end.setTemporalEaseAtKey(i, [new KeyframeEase(0, 75)], [new KeyframeEase(0, 75)]); } catch (e) {}
    }
    return g;
}

/* ── 글자 ───────────────────────────────────────────── */

function textLayer(name, str, font, size, fillHex, strokeHex, strokeW) {
    var L = COMP.layers.addText(str);
    L.name = name;
    var tp = L.property("ADBE Text Properties").property("ADBE Text Document");
    var d = tp.value;
    d.fontSize = size;
    d.font = font;
    d.applyFill = true;
    d.fillColor = hex(fillHex);
    if (strokeW > 0) {
        d.applyStroke = true;
        d.strokeColor = hex(strokeHex);
        d.strokeWidth = strokeW;
        d.strokeOverFill = false;      /* 캔버스 strokeText 는 획을 칠 뒤에 둔다 */
    } else {
        d.applyStroke = false;
    }
    d.justification = ParagraphJustification.CENTER_JUSTIFY;
    tp.setValue(d);
    return L;
}
function inkOf(L) { return L.sourceRectAtTime(0, false); }

/**
 * 글자는 잉크 박스 **중심**을 좌표에 맞춘다 — 캔버스의 textAlign center + textBaseline middle 과 같다.
 *
 * 앵커를 잉크 중심에 두고 Position 을 좌표에 둔다. Position 만 보정하는 방법도 같은
 * 그림이 나오지만, 그렇게 하면 크기·회전이 [0,0] 을 축으로 돌아서 팝 연출을 못 건다.
 */
function trackTextCenter(L, xExpr, yExpr) {
    var off = fx(L).addProperty("ADBE Point Control");
    off.name = "손보정";
    off.property(1).setValue([0, 0]);
    tr(L).property("ADBE Anchor Point").expression =
        'var r = thisLayer.sourceRectAtTime(time, false);\n[r.left + r.width/2, r.top + r.height/2]';
    tr(L).property("ADBE Position").expression =
        camHead() + 'var o = effect("손보정")(1);\n[(' + xExpr + ') + o[0], (' + yExpr + ') + o[1]]';
    return L;
}
