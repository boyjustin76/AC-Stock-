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
/**
 * 휘도(0~1). 렌더러 layers.js 의 luma() 를 그대로 옮긴 것이다 — 계수까지 같아야 한다.
 * 어두운 글자에 검정 테두리를 두르면 획이 뭉개지므로, 렌더러는 luma < 0.16 이면
 * 테두리를 흰색으로 바꾼다. 이 규칙을 안 옮겼더니 #9F0000(휘도 0.133) "손절" 두 개에
 * AE 에서만 검은 후광이 생겼다 — 픽셀 대조가 잡았다.
 */
function luma(h) {
    var s = String(h == null ? "" : h);
    if (!/^#[0-9a-fA-F]{6}$/.test(s)) return 1;
    var n = parseInt(s.substr(1), 16);
    return (((n >> 16) & 255) * 0.2126 + ((n >> 8) & 255) * 0.7152 + (n & 255) * 0.0722) / 255;
}

/**
 * 씬 데이터의 문자열 비교.
 *
 * 처음엔 `===` 가 실패하는 줄 알고 이걸 만들었다. **그건 오진이었다** —
 * 진짜 원인은 중첩 삼항이었고(아래 trackText 주석), 고치고 나니 `===` 도 잘 돈다.
 * 그래도 남겨 둔다: 씬은 사람이 손으로 쓰는 데이터라 숫자 1 이 문자열 "1" 로 오는 식의
 * 어긋남이 언제든 생긴다. 값만 보고 비교하는 게 여기선 맞다.
 */
function eq(v, s) { return String(v) == String(s); }

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

/**
 * 이월 요소 판정 — 렌더러 layers.js 의 isStill() 을 그대로 옮긴 것이다.
 *
 * 클립 경계에서 이어받은 요소는 씬에 `in: [0,0]`(또는 `[-1,0]`)로 선언된다. 그런 요소는
 * 등장 연출(팝·라이즈·그리기·라벨 지연)을 **재생하지 않고 완성 상태로 시작**한다 —
 * 같은 요소가 클립마다 다시 등장하면 컷 경계에서 깜빡임으로 보이기 때문이다(룰북 ⑧ 보충).
 *
 * ⚠ 이 규칙은 등장 **연출**에만 걸린다. 불투명도(cue)는 따로 간다.
 */
function isStill(L) {
    var i = L["in"];
    var a = (i && i.length) ? i[0] : 0;
    var b = (i && i.length > 1) ? i[1] : 0;
    return a <= 0 && b <= 0;
}
/** 표현식용 등장 진행도. 이월이면 상수 "1" 을 낸다 (렌더러 enter() 와 같다) */
function enterX(L, t0, t1, ease) {
    if (isStill(L)) return "1";
    return "_sp(time," + t0 + "," + t1 + "," + ease + ")";
}
/** 키를 구울 때 쓰는 등장 진행도 */
function enterJS(L, t, t0, t1, e) {
    return isStill(L) ? 1 : spanJS(t, t0, t1, e);
}
/** anim.js cue() 그대로 — 등장은 outCubic, 퇴장은 inOutQuad 다 */
function cueJS(t, L) {
    var i = L["in"], o = L["out"];
    var enter = (i && i.length) ? spanJS(t, i[0], i[0] + i[1], E.outCubic) : 1;
    var exit  = (o && o.length) ? 1 - spanJS(t, o[0], o[0] + o[1], E.inOutQuad) : 1;
    return Math.min(enter, exit);
}

/**
 * 불투명도를 **키 몇 개 + 이징**으로 넣는다. fn(t) 는 0~1 을 준다.
 *
 * 왜 표현식이 아니라 키프레임인가 —
 *   팀장이 손으로 끌어 싱크를 바꿀 수 있어야 한다. 표현식이면 식을 고쳐야 한다.
 * 왜 프레임마다 굽지 않는가 —
 *   처음엔 그렇게 했다. 정확하지만 램프마다 키가 열 개씩 생겨 손대기 무섭다.
 * 왜 그냥 이지이즈를 씌우지 않는가 —
 *   렌더러 이징(outCubic·outBack)은 한쪽으로 치우쳤는데 이지이즈는 대칭이다.
 *   씌웠더니 페이드 중간에서 60% vs 92% 로 벌어졌다.
 *
 * 그래서: 값이 변하는 구간의 양 끝에만 키를 두고, **이징 속도를 곡선의 미분값**으로
 * 준다. B5 실측으로 이 방법이 키 2개에 오차 0.4~1.2% 임을 확인했다(이지이즈는 44~66%).
 * 그래도 남는 오차는 **박은 뒤 되읽어 재고**, 허용치를 넘으면 제일 나쁜 지점에
 * 키를 하나 더 넣는다 — 짐작으로 두지 않는다.
 *
 * @returns {keys, err} 넣은 키 수와 실측 최대 오차(%)
 */
function setAlpha(L, fn, dur, fps, tol) {
    var op = tr(L).property("ADBE Opacity");
    var n = Math.round(dur * fps);
    var TOL = tol == null ? 1.5 : tol;          /* % — 255 단계로 4 미만이라 안 보인다 */
    var ex = [];
    for (var f = 0; f <= n; f++) ex.push(clampJS(fn(f / fps)) * 100);

    /* 값이 변하는 구간의 경계만 키로 잡는다 */
    var idx = [0];
    for (var i = 1; i <= n; i++) {
        var chg = Math.abs(ex[i] - ex[i - 1]) > 1e-9;
        var chgPrev = i > 1 && Math.abs(ex[i - 1] - ex[i - 2]) > 1e-9;
        if (chg !== chgPrev) idx.push(chg ? i - 1 : i - 1);
    }
    if (idx[idx.length - 1] !== n) idx.push(n);

    var h = 1 / (fps * 4);
    function put() {
        while (op.numKeys > 0) op.removeKey(1);
        var ts = [], vs = [];
        for (var k = 0; k < idx.length; k++) { ts.push(idx[k] / fps); vs.push(ex[idx[k]]); }
        if (ts.length === 1) { op.setValueAtTime(0, vs[0]); return; }
        op.setValuesAtTimes(ts, vs);
        /*  들어오는 쪽은 뒤쪽 기울기, 나가는 쪽은 앞쪽 기울기로 준다.
            꺾이는 지점(등장 끝 같은 곳)에서 양쪽 기울기가 다른 걸 그대로 살린다.  */
        for (var k2 = 1; k2 <= op.numKeys; k2++) {
            var t = idx[k2 - 1] / fps;
            var dIn  = (fn(t) - fn(Math.max(t - h, 0))) / h * 100;
            var dOut = (fn(Math.min(t + h, dur)) - fn(t)) / h * 100;
            try {
                op.setTemporalEaseAtKey(k2, [new KeyframeEase(dIn, 33)], [new KeyframeEase(dOut, 33)]);
            } catch (e) { /* 속도가 범위를 벗어나면 기본값으로 둔다 */ }
        }
    }
    function worstAt() {
        var w = -1, wi = -1;
        for (var f2 = 0; f2 <= n; f2++) {
            var d = Math.abs(op.valueAtTime(f2 / fps, false) - ex[f2]);
            if (d > w) { w = d; wi = f2; }
        }
        return { err: w, at: wi };
    }
    put();
    var r = worstAt();
    for (var pass = 0; pass < 6 && r.err > TOL; pass++) {
        /* 제일 나쁜 지점에 키를 하나 넣고 다시 잰다 */
        var ins = r.at, put2 = false;
        for (var q = 0; q < idx.length; q++) if (idx[q] === ins) put2 = true;
        if (put2) break;
        idx.push(ins);
        idx.sort(function (a, b) { return a - b; });
        put();
        r = worstAt();
    }
    return { keys: op.numKeys, err: Math.round(r.err * 100) / 100 };
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
 * 글자를 좌표에 붙인다. 세로는 잉크 박스 가운데(캔버스 textBaseline 'middle'),
 * 가로는 **AE 자체 정렬(justification)** 에 맡긴다 — 점 텍스트의 원점이 곧 정렬점이라
 * 캔버스 textAlign 이 가리키는 점과 같은 자리다.
 *
 * 앵커를 잉크 위의 그 점에 두고 Position 을 좌표에 둔다. Position 만 보정해도 같은
 * 그림이 나오지만, 그러면 크기·회전이 [0,0] 을 축으로 돌아서 팝 연출을 못 건다.
 *
 * ⚠ align 을 빠뜨렸다가 컷③ 문구 둘이 글자 폭의 절반만큼 왼쪽으로 밀려 화면 밖으로
 *    잘렸다. 씬에서 align:'left' 를 쓰는 건 흔치 않아 눈에 안 띄었다.
 */
/**
 * 이 레이어가 찍는 글자의 **실측 치수**. scene-export 가 크로미움 안에서 재 붙인다.
 * (총괄 승인 2026-09-03, 길 A) 못 잰 층에는 없다 — 그럴 땐 예전 방식으로 돈다.
 */
function tmOf(L, str) {
    var a = L.tm;
    if (!a || !a.length) return null;
    var s = String(str);
    for (var i = 0; i < a.length; i++) if (String(a[i].text) === s) return a[i];
    return null;
}
/**
 * 캔버스 y 를 AE 점 텍스트의 Position y 로 옮기는 보정.
 *
 * 캔버스는 textBaseline 'middle' 로 찍고 AE 점 텍스트의 원점은 알파벳 베이스라인이다.
 * 그 사이 거리를 폰트에서 재 온 값이 dy 다 — 글자 내용과 무관한 폰트 값이라 층마다
 * 하나면 된다(39건 실측에서 잉크 기준과 폰트 기준이 전부 일치했다).
 *
 * 예전에는 잉크 상자 중심을 y 에 맞추고 `+2` 를 손으로 더했다. 잉크는 글자마다
 * 비대칭이고 획(stroke) 번짐까지 품어 5px 가까이 어긋났다.
 * 못 잰 층은 null 을 돌려주고, 부르는 쪽이 예전 방식으로 돈다.
 */
function baseDY(L, str) {
    var t = tmOf(L, str);
    if (!t) return null;
    if (t.dy == null) return null;
    return t.dy;
}
/**
 * 세로 자리 한 줄. yExpr 은 **캔버스가 넘기는 y 그대로**다 (캔버스가 +2 를 더하는
 * 자리면 그 +2 까지 담아서 준다 — 그건 캔버스 것이지 보정이 아니다).
 * dy 를 잰 층은 베이스라인을 바로 놓고, 못 잰 층은 예전처럼 잉크 중심을 맞춘다.
 */
function yOf(dy, yExpr) {
    if (dy == null) return "(" + yExpr + ") - (_r.top + _r.height/2) + o[1]";
    return "(" + yExpr + ") + " + dy + " + o[1]";
}
/**
 * 판 폭 보정. 캔버스는 판을 **전진폭**(measureText().width)으로 짓는데 AE 는
 * sourceRectAtTime 으로 재니 **잉크폭**이 나온다 — 획 번짐과 사이드베어링만큼 넓다.
 * 그 차이를 상수로 더해 두면 판이 캔버스와 같아지고, 나중에 글자를 고쳐도 판은
 * 여전히 식으로 따라 커진다(A6 합격선을 지킨다).
 * 실측: '손익비  1 : 2' 에서 잉크 263.8 vs 전진 256.86 → 판이 6.9 넓고,
 * 가운데 정렬이라 글자가 그 절반인 3.5px 밀렸다. 오래 못 잡던 그 값이다.
 */
function advAdj(L, str, T) {
    var t = tmOf(L, str);
    if (!t) return 0;
    if (t.advance == null) return 0;
    return t.advance - inkOf(T).width;
}

function trackText(L, xExpr, yExpr, align, dy) {
    var off = fx(L).addProperty("ADBE Point Control");
    off.name = "손보정";
    off.property(1).setValue([0, 0]);
    /*  ⚠ **앵커에 자기 sourceRectAtTime 을 쓰면 안 된다.** 자기 자신을 참조하는 꼴이라
        AE 가 엉뚱한 값을 낸다 — 실측: 잉크 left 가 -144.2 인데 앵커가 +144.5 로 잡혀
        글자가 화면 밖으로 288px 밀렸다. 앵커는 0 으로 두고 **Position 에서 보정**한다
        (파일럿 때부터 쓰던 방식이고, 다른 레이어를 가리키는 건 문제없다).            */
    /*  ⚠ **중첩 삼항을 쓰지 마라.** ExtendScript 는 `a ? 0 : b ? 1 : 0.5` 를
        `(a ? 0 : b) ? 1 : 0.5` 로 묶는다. a 가 참이면 0 이 되고, 0 은 거짓이라
        결과가 0.5 로 튄다 — 왼쪽 정렬이 가운데 정렬로 둔갑해 문구가 화면 밖으로 밀렸다.
        값이 우연히 같은 경우가 많아 오래 안 보였다. if/else 로만 쓴다.            */
    /*  ⚠ **가로를 잉크 상자로 맞추면 안 된다.** 잉크 상자는 획(stroke)이 글자 밖으로
        번진 만큼과 왼쪽 사이드베어링을 함께 품는다. 캔버스의 textAlign 'left' 는
        **글자 원점**을 좌표에 두고 획은 그 왼쪽으로 삐져나가게 둔다. 그래서 잉크
        왼끝을 좌표에 맞추면 그만큼 오른쪽으로 밀린다 — 컷③ 문구가 실측 5px 밀렸다.
        AE 점 텍스트는 원점이 곧 정렬점이니, 정렬을 맞춰 두면 가로 보정이 필요 없다.  */
    var just = ParagraphJustification.CENTER_JUSTIFY;
    if (eq(align, "left")) just = ParagraphJustification.LEFT_JUSTIFY;
    else if (eq(align, "right")) just = ParagraphJustification.RIGHT_JUSTIFY;
    var tp = L.property("ADBE Text Properties").property("ADBE Text Document");
    var doc = tp.value;
    doc.justification = just;
    tp.setValue(doc);

    tr(L).property("ADBE Anchor Point").setValue([0, 0]);
    /*  세로: 실측 dy 가 있으면 그걸 더해 베이스라인을 바로 놓는다. 없으면 예전처럼
        잉크 상자 중심을 맞춘다 — 정확하진 않아도 아무것도 없는 것보다 낫다.  */
    var yPos;
    if (dy == null) {
        yPos = 'var r = thisLayer.sourceRectAtTime(time, false);\n'
             + '[(' + xExpr + ') + o[0], (' + yExpr + ') - (r.top + r.height/2) + o[1]]';
    } else {
        yPos = '[(' + xExpr + ') + o[0], (' + yExpr + ') + ' + dy + ' + o[1]]';
    }
    tr(L).property("ADBE Position").expression =
        camHead() + 'var o = effect("손보정")(1);\n' + yPos;
    return L;
}
