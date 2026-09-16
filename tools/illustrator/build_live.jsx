/**
 * '차트명가 NEW 라이브화면구성.ai' 를 짓는다.
 *
 * 구성·양식 = 트레이딩팩토리 2026v 원본 (260114_라이브화면구성(2026v).ai)
 *   원본은 1920x1080 pt 문서다. OBS 에 올리는 8000x4500 png 는 417% 로 내보낸 것이다.
 *   구역 좌표는 Reference_01_레이어_가이드 와 03_메인(일)_방송프레임 의 알파를 실측했다.
 *
 * 톤앤매너 = 차트명가 NEW 전통(병풍·낙관)  — 01_납품_차트명가NEW/신규안_v2_전통/무드보드.md
 *   한지 #F3EEE3 (2026-09-15 팀장 '더 하얗게') · 쪽 #2C3358 · 인주 적 #D42A26 ·
 *   옻칠 #221E1B · 금테 #B08D3C · 글꼴 궁서.
 *
 * 문구는 트레이딩팩토리 것을 그대로 쓴다 (2026-09-16 이정찬: "갖다 쓸 게 바꿀 것보다 많다").
 * 바꿀 문구는 나중에 팀장 지시가 오면 한꺼번에 고친다 — 그래서 문구를 COPY 한 곳에 모아 뒀다.
 */
// @target illustrator

var HERE = new File($.fileName).parent;
var log = [];
var DEBUG_TEXT = false;  // true 로 두면 글자 자리잡기 과정을 로그에 적는다
function L(s) { log.push(String(s)); }

$.evalFile(new File(HERE.fsName + "/_lib.jsx"));
var CFG = readConfig(HERE);

var PATHS = readPaths(HERE);
var LAB = PATHS.liveframeDir, OUT = PATHS.outDir, REPO = PATHS.repoDir;

/* ── 팔레트 (config 에서 읽는다 — 색을 두 곳에 적지 않는다) ───────── */
var P = CFG.palette;
var 한지 = rgb(P["한지"]), 먹 = rgb(P["먹"]), 인주 = rgb(P["인주적"]),
    쪽   = rgb(P["쪽남"]), 금테 = rgb(P["금테"]), 옻칠 = rgb("#221E1B"),
    한지밝 = rgb("#FAF6EE"), 흰   = rgb("#FFFFFF");

/* ── 구역 (1920x1080 화면 좌표, y 는 위에서 아래) ─────────────────
   트팩 원본 실측값이다. OBS 소스가 이 자리에 맞춰 놓이므로 함부로 바꾸지 않는다. */
var Z = {
    광고:   { x:0,    y:0,    w:1920, h:138 },   // 롤링 광고 (별도 미디어 소스)
    현판띠: { x:0,    y:140,  w:1527, h:78  },   // 트팩은 검정 띠 + 민트 글자
    차트:   { x:0,    y:218,  w:1527, h:862 },   // 테두리 포함 바깥 상자
    패널:   { x:1521, y:140,  w:399,  h:940 },
    시계:   { x:1521, y:140,  w:399,  h:78  },
    헤더:   { x:1521, y:221,  w:399,  h:26  },
    포지션: { x:1521, y:247,  w:399,  h:300 },
    메모:   { x:1521, y:553,  w:399,  h:116 },
    댓글:   { x:1521, y:676,  w:399,  h:404 }
};

/* ── 문구 — 트레이딩팩토리 원본 그대로 ───────────────────────────
   팀장 지시가 오면 여기만 고치면 된다 (thumbnail_rule 28 과 같은 생각: 한 곳에 모은다). */
var COPY = {
    채널:     "차트명가",
    방송시간: "방송시간 : 월~금 23:00~01:00",
    입장문의: "입장문의 : 아래 고정댓글 확인",
    종목:     "나스닥 해외선물",
    오프닝1:  "1. 오늘의 시장 분석",
    오프닝2:  "2. 오늘의 매매 전략",
    헤더:     ["포지션", "계약수", "수익"],
    가이드:   { 광고:"롤링 광고", 시계:"시계", 차트:"차트 화면",
                포지션:"종류/거래량 · 수익", 메모:"스티커 메모", 댓글:"댓글창" }
};

/* ── 글꼴 — 궁서. 이름이 판마다 달라 후보를 차례로 본다 ──────────── */
var 궁서 = pickFont(["Gungsuh", "GungsuhChe", "궁서", "BatangChe", "Batang"], L);
var 궁서B = pickFont(["Gungsuh", "궁서", "Batang"], null);
L("글꼴: " + 궁서.name);

/* ── 문서 ────────────────────────────────────────────────────── */
var BOARDS = ["01_고정_배경_레이어", "02_오프닝_프레임", "03_메인_방송프레임", "04_레이어_가이드"];
var GAP = 120;

var doc = app.documents.add(DocumentColorSpace.RGB, 1920, 1080);
while (doc.artboards.length > 1) doc.artboards.remove(doc.artboards.length - 1);
doc.artboards[0].artboardRect = [0, 0, 1920, -1080];
doc.artboards[0].name = BOARDS[0];
for (var b = 1; b < BOARDS.length; b++) {
    var L0 = b * (1920 + GAP);
    doc.artboards.add([L0, 0, L0 + 1920, -1080]).name = BOARDS[b];
}
/* 기본 레이어를 치우고 이름 있는 레이어로만 간다 — 원본은 레이어 1개에 155항목이 뭉쳐 있었다 */
var base = doc.layers[0];

function layer(name) { var y = doc.layers.add(); y.name = name; return y; }
/* layers.add() 는 맨 위에 넣는다. 그래서 바닥에 깔릴 것부터 만든다 —
   바탕(한지) → 틀(병풍·현판) → 글자 → 가이드 순. */
var LY = {};
var order = ["바탕", "틀", "글자", "가이드"];
for (var i = 0; i < order.length; i++) LY[order[i]] = layer(order[i]);

/* 아트보드 b 의 화면좌표 (x,y) → 문서좌표 */
function OX(b, x) { return b * (1920 + GAP) + x; }
function OY(y)    { return -y; }

/* ── 그리기 헬퍼 ─────────────────────────────────────────────── */
function box(ly, b, x, y, w, h, fill, strokeCol, strokeW) {
    var r = ly.pathItems.rectangle(OY(y), OX(b, x), w, h);
    if (fill) { r.filled = true; r.fillColor = fill; } else r.filled = false;
    if (strokeCol) { r.stroked = true; r.strokeColor = strokeCol; r.strokeWidth = strokeW || 1; }
    else r.stroked = false;
    return r;
}

/** 병풍 한 폭: 쪽빛 비단 띠 + 안쪽 가는 쪽선 (trad.py byeongpung_frame 과 같은 비율) */
function byeongpung(ly, b, x, y, w, h, band) {
    band = band || 12;
    /* 띠는 획으로 그린다 — 안쪽이 비어 있어야 아래 소스가 비친다 */
    var o = box(ly, b, x + band / 2, y + band / 2, w - band, h - band, null, 쪽, band);
    var g = band + 5;
    box(ly, b, x + g, y + g, w - g * 2, h - g * 2, null, 쪽, 2);
    return { x: x + g, y: y + g, w: w - g * 2, h: h - g * 2 };   // 뚫린 자리
}

/** 현판: 옻칠 판 + 금테 + 흰 궁서 (trad.py hyeonpan 과 같은 구성).
    w 를 0 으로 주면 글자 폭에 맞춰 판을 키운다 — D 의 hyeonpan 도 `tw(f,title)+64` 로 그렇게 한다.
    고정 폭으로 두면 긴 종목명이 판 밖으로 잘린다 (1차 빌드에서 '나스닥 해외선물' 이 그랬다). */
function hyeonpan(lyBox, lyText, b, x, y, w, h, title, size) {
    var t = null;
    if (title) {
        t = text(lyText, b, 0, y + h / 2, title, size, 한지밝, "left");   // 재려고 먼저 만든다
        var tb = t.geometricBounds;
        if (!w) w = (tb[2] - tb[0]) + 64;
    }
    box(lyBox, b, x, y, w, h, 옻칠, null, 0);
    box(lyBox, b, x + 5, y + 5, w - 10, h - 10, null, 금테, 2);
    if (t) {
        var g = t.geometricBounds, tw = g[2] - g[0];
        t.translate((OX(b, x + w / 2) - tw / 2) - g[0], 0);              // 판 가운데로
    }
    return { x: x, y: y, w: w, h: h };
}

/**
 * 글자. (x, y) 는 기준점이고 **y 는 글자 상자의 세로 가운데**다 — 베이스라인이 아니다.
 * 칸 안에 넣는 일이 대부분이라 가운데가 다루기 쉽다.
 *
 * 만든 뒤에 실제 상자(geometricBounds)를 재서 옮긴다. textFrame 의 top/left 는
 * 글자가 실제로 차지하는 자리와 달라서(어센더·행간 몫) 그대로 앉히면 칸 밖으로 나간다 —
 * 1차 빌드에서 '차트명가' 가 띠 밖으로 잘렸던 게 이것이다.
 *
 * maxW 를 주면 그 폭에 들어갈 때까지 크기를 줄인다 (칸이 좁은 가이드 라벨용).
 */
function text(ly, b, x, y, s, size, color, align, maxW) {
    var t = ly.textFrames.add();
    t.contents = s;
    var ca = t.textRange.characterAttributes;
    ca.textFont = 궁서;
    ca.size = size;
    ca.fillColor = color;

    /* 글자를 바꾼 직후의 geometricBounds 는 아직 이전 값이다 — 다시 그리게 해야 맞는 상자가 나온다.
       1차 빌드에서 크기조절 루프가 돈 라벨만 가운데가 맞고 나머지가 왼쪽으로 밀렸던 게 이것이다
       (루프가 우연히 갱신을 강제했다). 2026-09-16 실측. */
    app.redraw();

    if (maxW) {
        for (var guard = 0; guard < 24; guard++) {
            var gb0 = t.geometricBounds;
            if (gb0[2] - gb0[0] <= maxW || ca.size <= 8) break;
            ca.size = ca.size * 0.92;
            app.redraw();
        }
    }

    /* 놓고 → 다시 재서 → 남은 차이만큼 또 옮긴다. 두 번째 바퀴가 0 이면 제대로 앉은 것이다.
       (자리가 틀렸던 진짜 원인은 아래 삼항 오파싱이었지만, 이 두 바퀴는 남겨 둔다 —
        글꼴이 바뀌어 상자가 달라져도 스스로 맞춘다.) */
    for (var pass = 0; pass < 2; pass++) {
        app.redraw();
        var gb = t.geometricBounds;          // [left, top, right, bottom]
        var w = gb[2] - gb[0], h = gb[1] - gb[3];
        /* 삼항 연산자를 겹쳐 쓰지 마라. ExtendScript 가 `a ? x : b ? y : z` 를 잘못 읽어
           align 이 "center" 인데도 "right" 가지를 탔다 (2026-09-16 실측 — align 을 찍어 확인).
           if/else 로 풀면 그대로 맞는다. */
        var wantL = OX(b, x);
        if (align == "center") wantL = OX(b, x) - w / 2;
        else if (align == "right") wantL = OX(b, x) - w;
        var dx = wantL - gb[0], dy = (OY(y) + h / 2) - gb[1];
        if (DEBUG_TEXT) L("    [" + pass + "] \"" + s + "\" w=" + Math.round(w)
            + " gbL=" + Math.round(gb[0]) + " wantL=" + Math.round(wantL)
            + " dx=" + Math.round(dx) + " align=<" + align + ">");
        if (pass && Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) break;
        t.translate(dx, dy);
    }
    return t;
}

/** 한지 바탕 — make_bg.py 가 구운 png 를 1:1 로 깐다.
    한지는 '바탕색 + 닥종이 사진의 밝기 편차'(trad.py hanji)라 블렌드모드로는 값이 안 나온다.
    그래서 D 의 함수를 그대로 불러 구워 두고 여기서는 놓기만 한다. */
function hanji(ly, b) {
    var bg = new File(OUT + "/" + CFG.bgPng);
    if (!bg.exists) throw new Error("한지 바탕이 없습니다 — 먼저 구우세요: python tools/illustrator/make_bg.py --out <결과폴더>  |  " + bg.fsName);
    var p = ly.placedItems.add();
    p.file = bg;
    p.left = OX(b, 0);
    p.top  = OY(0);
    p.embed();
    L("  한지 바탕: " + bg.name);
}

/* ── 공통 틀 ─────────────────────────────────────────────────
   D 검수(2026-09-16) 반영. 실물 병풍은 **두꺼운 비단 테두리가 바깥을 한 바퀴** 두르고,
   폭과 폭 사이는 접히는 좁은 이음선뿐이다. 폭마다 두꺼운 테두리를 두르지 않는다.
   1차 시안은 칸마다 12px 띠를 둘러 띠끼리 맞닿았고, 그래서 병풍이 아니라 '표' 로 읽혔다.
       바깥 한 바퀴  쪽빛 12px + 안쪽 가는 선 2px
       칸과 칸 사이  쪽빛 2px 한 줄
   덤으로 뚫린 자리가 트팩 크기를 되찾는다.                                        */

/** 이음선 — 칸과 칸을 가르는 쪽빛 가는 줄 */
function seam(ly, b, x, y, w, h) { return box(ly, b, x, y, w, h, 쪽, null, 0); }

function drawFrame(b, opts) {
    var 틀 = LY["틀"], 글 = LY["글자"];
    var T = 2;                                   // 이음선 두께

    /* 1) 바깥 병풍 한 바퀴 — 화면 전체를 두른다 */
    var hole = byeongpung(틀, b, 0, 0, 1920, 1080, 12);     // 뚫린 자리 17~1903 / 17~1063
    var L0 = hole.x, R0 = hole.x + hole.w, T0 = hole.y, B0 = hole.y + hole.h;

    /* 2) 칸과 칸 사이 이음선 */
    var PX = Z.패널.x;                            // 차트 | 패널 경계
    seam(틀, b, L0, Z.광고.h,   R0 - L0, T);      // 광고 아래 (전폭)
    seam(틀, b, L0, Z.차트.y,   PX - L0, T);      // 정보 띠 아래
    seam(틀, b, PX, Z.광고.h,   T,  B0 - Z.광고.h);  // 차트 | 패널 (세로)
    seam(틀, b, PX, Z.헤더.y,   R0 - PX, T);      // 시계 아래
    seam(틀, b, PX, Z.포지션.y, R0 - PX, T);      // 헤더 아래
    seam(틀, b, PX, Z.메모.y,   R0 - PX, T);      // 포지션 아래
    seam(틀, b, PX, Z.댓글.y,   R0 - PX, T);      // 메모 아래

    /* 3) 정보 띠 — 한지 띠 위에 편액(채널 이름) + 먹 궁서 둘.
       편액(扁額)은 가로로 긴 판이 맞다(扁 = 납작하다). 다만 판은 **글자에 맞춰 깎는다** —
       1527x78(19.6:1)로 늘리면 편액이 아니라 그냥 검정 바로 읽힌다(D 검수).
       채널 이름만 판에 걸고, 방송시간·입장문의는 한지 위 먹 글씨로 둔다. */
    var 띠 = new File(OUT + "/" + CFG.bandPng);
    if (띠.exists) {
        var bp = 틀.placedItems.add();
        bp.file = 띠;
        bp.left = OX(b, L0);
        bp.top  = OY(Z.현판띠.y);
        bp.embed();
    }
    var 띠중 = Z.현판띠.y + Z.현판띠.h / 2;
    var plaque = hyeonpan(틀, 글, b, L0 + 18, Z.현판띠.y + 9, 0, Z.현판띠.h - 18, COPY.채널, 34);

    /* 두인 — 편액 옆에 도장. 실제 관행이고, 차트 위에 얹지 않아 캔들을 안 가린다.
       (D 추천은 '패널 맨 아래 빈 칸' 이었지만 패널 칸이 전부 라이브 소스라 자리가 없다.) */
    var seal = new File(OUT + "/" + CFG.sealPng);
    var seamX = plaque.x + plaque.w + 16;
    if (seal.exists) {
        var sp = 글.placedItems.add();
        sp.file = seal;
        sp.left = OX(b, seamX);
        sp.top  = OY(띠중 - sp.height / 2);
        sp.embed();
        seamX += sp.width + 18;
    }

    /* 정보 둘 — 사이를 쪽빛 세로 가는 선으로 가른다 */
    seam(틀, b, seamX, Z.현판띠.y + 16, T, Z.현판띠.h - 32);
    text(글, b, seamX + 26, 띠중, COPY.방송시간, 27, 먹, "left");
    var midX = PX - 470;
    seam(틀, b, midX, Z.현판띠.y + 16, T, Z.현판띠.h - 32);
    text(글, b, midX + 26, 띠중, COPY.입장문의, 27, 먹, "left");

    /* 4) 포지션 헤더 — 트팩은 회색 그라디언트. 여기서는 쪽빛 바 + 흰 궁서 */
    box(틀, b, Z.헤더.x + T, Z.헤더.y + T, R0 - Z.헤더.x - T, Z.헤더.h - T * 2, 쪽, null, 0);
    var colX = [Z.헤더.x + 70, Z.헤더.x + 200, Z.헤더.x + 330];
    for (var h = 0; h < COPY.헤더.length; h++)
        text(글, b, colX[h], Z.헤더.y + Z.헤더.h / 2, COPY.헤더[h], 17, 흰, "center");

    if (opts && opts.hole) {
        L("  바깥 뚫린 자리: x " + L0 + "~" + R0 + " · y " + T0 + "~" + B0);
        L("  차트 자리: x " + L0 + "~" + PX + " · y " + (Z.차트.y + T) + "~" + B0);
    }
}

/* ── [0] 고정 배경 레이어 — 맨 아래. 전부 불투명 ────────────────── */
L("");
L("■ " + BOARDS[0]);
hanji(LY["바탕"], 0);
/* 광고 자리는 따로 칠하지 않는다 — 바탕 한지 그대로 둔다.
   1차 시안은 인주 적(#D42A26)을 전폭으로 깔았는데, 인주는 낙관·매수·익절에 '점 찍는' 색이라
   1920x138 면으로 쓰면 팔레트 규칙(면 3개·화이트 톤)과 부딪힌다. 광고 소스가 끊기면
   붉은 띠가 통째로 방송에 뜨는 문제도 있다 (D 검수 2026-09-16). */
drawFrame(0, { hole: true });

/* ── [1] 오프닝 프레임 ──────────────────────────────────────── */
L("");
L("■ " + BOARDS[1]);
hanji(LY["바탕"], 1);
drawFrame(1);
(function () {
    var 글 = LY["글자"], b = 1;
    /* 종목 현판 + 오프닝 두 줄 — 차트 구멍 가운데에 건다.
       현판 폭은 글자에 맞춰 늘어나므로 가운데 정렬하려면 먼저 재고 x 를 잡는다. */
    var cx = 17 + (1510 - 17) / 2;
    var probe = 글.textFrames.add();
    probe.contents = COPY.종목;
    probe.textRange.characterAttributes.textFont = 궁서;
    probe.textRange.characterAttributes.size = 52;
    app.redraw();
    var pw = probe.geometricBounds[2] - probe.geometricBounds[0] + 64;
    probe.remove();
    hyeonpan(LY["틀"], 글, b, cx - pw / 2, 300, pw, 96, COPY.종목, 52);
    text(글, b, cx, 540, COPY.오프닝1, 76, 먹, "center");
    text(글, b, cx, 660, COPY.오프닝2, 76, 먹, "center");
})();

/* ── [2] 메인 방송 프레임 — 틀만. 가운데는 뚫려 있어야 한다 ───────── */
L("");
L("■ " + BOARDS[2]);
drawFrame(2);

/* ── [3] 레이어 가이드 — OBS 에 뭘 어디 올리는지 ────────────────── */
L("");
L("■ " + BOARDS[3]);
(function () {
    var 가 = LY["가이드"], b = 3;
    hanji(LY["바탕"], b);
    drawFrame(b);
    function 라벨(zone, s) {
        var z = Z[zone];
        var pad = Math.min(20, z.h * 0.18);
        box(가, b, z.x + pad, z.y + pad, z.w - pad * 2, z.h - pad * 2, null, 인주, 2);
        /* 칸보다 넓으면 줄인다 — 오른쪽 패널은 399px 라 긴 라벨이 넘친다 */
        text(가, b, z.x + z.w / 2, z.y + z.h / 2, s, Math.min(34, z.h * 0.42), 인주, "center", z.w - pad * 4);
    }

    라벨("광고",   COPY.가이드.광고);
    라벨("시계",   COPY.가이드.시계);
    라벨("차트",   COPY.가이드.차트);
    라벨("포지션", COPY.가이드.포지션);
    라벨("메모",   COPY.가이드.메모);
    라벨("댓글",   COPY.가이드.댓글);
})();

/* ── 저장 ───────────────────────────────────────────────────── */
try { base.remove(); } catch (e) {}

var outFile = new File(OUT + "/" + CFG.outAi);
var so = new IllustratorSaveOptions();
so.compatibility = Compatibility.ILLUSTRATOR17;
so.pdfCompatible = true;
so.embedICCProfile = true;
doc.saveAs(outFile, so);
L("");
L("저장: " + outFile.fsName);

/* 확인용 png — 아트보드마다 1장 (100%). OBS 용 8000x4500 은 417% 로 따로 뽑는다 */
for (var e = 0; e < doc.artboards.length; e++) {
    doc.artboards.setActiveArtboardIndex(e);
    var eo = new ExportOptionsPNG24();
    eo.artBoardClipping = true;
    eo.transparency = true;
    eo.horizontalScale = 100; eo.verticalScale = 100;
    doc.exportFile(new File(OUT + "/미리보기_" + BOARDS[e] + ".png"), ExportType.PNG24, eo);
}
L("미리보기 png " + doc.artboards.length + "장");

var lf = new File(OUT + "/build_log.txt");
lf.encoding = "UTF-8"; lf.open("w"); lf.write(log.join(String.fromCharCode(10))); lf.close();

"OK 아트보드 " + doc.artboards.length;
