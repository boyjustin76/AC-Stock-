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
    한지밝 = rgb("#FAF6EE"), 흰   = rgb("#FFFFFF"),
    /* 브랜드 팔레트 (컬러팔레트.png) — 역할이 정해져 있다. '잘 보이는 색' 으로 고르지 않는다. */
    메인타이틀 = rgb(P["메인타이틀"]), 서브타이틀 = rgb(P["서브타이틀"]),
    배경먹 = rgb(P["배경먹"]), 대비강조 = rgb(P["대비강조"]), 부가설명 = rgb(P["부가설명"]);

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
                포지션:"종류/거래량 · 수익", 메모:"스티커 메모", 댓글:"댓글창" },
    고정댓글: "고정댓글 확인",

    /* 07 — 트팩 Artboard 13 */
    화면조정: "화면 조정 중",

    /* 08 — 트팩 Artboard 12 copy 2. 서머타임 판이다 (2026-09-17 이정찬) */
    방송시간SM: "방송시간 : 월~금 22:00~24:00",

    /* 09 — 트팩 원본의 아트보드 밖 레이아웃(왼쪽 정보칸). 글자는 원본 텍스트 그대로.
       '볼리저밴드' 오타도 원본 그대로 둔다 — 문구는 팀장 지시가 오면 한꺼번에 고친다. */
    정보칸: {
        입장제목: "트레이딩룸 입장방법",
        입장줄:   [["0.1프로 트레이딩룸 입장은 ", "고정댓글"],
                   ["메타트레이더 계좌개설 문의는 ", "고정댓글"]],
        칸: [
            { 제목: "진입 기준", 줄: ["- TF 추세지표 방향에 따라 매매", "- 볼린저밴드 중심선/상·하단선 진입", "- 주요 지지·저항선 진입"] },
            { 제목: "목표가",    줄: ["매수 : ① 캔들 1개 → ② 볼리저밴드 상단", "매도 : ① 캔들 1개 → ② 볼리저밴드 하단"] },
            { 제목: "손절가",    줄: ["- 주요 지지·저항선 또는 전고점·전저점 이탈 시", "- 시드 대비 5% 손실 도달 시"] },
            { 제목: "매매 원칙", 줄: ["- 1회 진입 시 1계약, 물타기·불타기 없음", "- 시드 대비 10% 손실 시 매매 중단"] }
        ]
    },

    /* 10 — 트팩 원본의 아트보드 밖 레이아웃(VIP 안내). 원본이 통짜 그림이라 글자는 그림에서 읽어 옮겼다. */
    VIP: {
        제목: "[VIP 멤버쉽 제공 서비스 무료체험 진행중]",
        왼줄: ["1. VIP전용 원데이 나스닥 분석.예측 LIVE 방송",
               "2. VIP전용 해외선물 실전트레이딩 강의 커리큘럼"],
        오른줄: ["3. VIP전용 자체개발 (보조지표) 3종 전략 제공",
                 "4. VIP전용 자체개발 보조지표 강의 커리큘럼",
                 "5. VIP전용 트레이딩팩토리 소통 채널 입장"],
        시작: "25, 01, 10 start",
        금액: "20,000$",
        구독: "구 독 & 좋 아 요",
        경고: "※본 방송은 실전 트레이딩 교육방송이며, 투자를 권유하지 않습니다※",
        하단: ["VIP 전용 트레이딩팩토리 소통 커뮤니티 채널 입장 → ", "고정댓글 확인!"]
    }
};

/* ── 글꼴 — 궁서. 이름이 판마다 달라 후보를 차례로 본다 ──────────── */
var 궁서 = pickFont(["Gungsuh", "GungsuhChe", "궁서", "BatangChe", "Batang"], L);
var 궁서B = pickFont(["Gungsuh", "궁서", "Batang"], null);
L("글꼴: " + 궁서.name);

/* ── 문서 ────────────────────────────────────────────────────── */
var BOARDS = ["01_고정_배경_레이어", "02_오프닝_프레임", "03_메인_방송프레임",
              "04_레이어_가이드", "05_최종출력샘플_오프닝", "06_최종출력샘플_메인",
              "07_화면_조정_중", "08_메인_하단광고(SM)", "09_메인_정보칸", "10_메인_VIP안내"];
/* 07~10 은 트팩 원본에 있는데 우리 것이 없던 판이다 (2026-09-17 이정찬).
     07 ← Artboard 13 (화면 조정 중)          08 ← Artboard 12 copy 2 (광고가 아래, 서머타임)
     09 ← 아트보드 밖 레이아웃 (왼쪽 정보칸)   10 ← 아트보드 밖 레이아웃 (VIP 안내 — 원본은 통짜 그림)
   캡쳐(차트·포지션·댓글·시계·작은 차트·거래내역)는 넣지 않는다 — 그 자리는 비워 둔다. */
/* 04~06 은 트팩 Reference_01~03 에 대응한다. 04 는 OBS 배치 설명도, 05·06 은 실제로
   소스가 다 얹혔을 때의 그림이다. 05·06 에 들어가는 캡쳐는 트팩 것을 그대로 쓴다 —
   차트명가도 같은 프로그램(MT5·텔레그램·유튜브 댓글)을 쓰기 때문이다 (2026-09-16 이정찬).
   우리가 새로 만드는 것은 틀과 그 위의 우리 그래픽(편액·목차·낙관)뿐이다. */
var GAP = 120, COLS = 3;

var doc = app.documents.add(DocumentColorSpace.RGB, 1920, 1080);
while (doc.artboards.length > 1) doc.artboards.remove(doc.artboards.length - 1);
doc.artboards[0].artboardRect = [0, 0, 1920, -1080];
doc.artboards[0].name = BOARDS[0];
/* 가로로만 늘어놓으면 일러스트레이터 캔버스 한계(원점에서 ±8172pt)를 넘는다 —
   6개째에서 'AOoC' 오류가 났다 (2026-09-16 실측). 2행 3열 격자로 놓는다. */
for (var b = 1; b < BOARDS.length; b++) {
    var cL = (b % COLS) * (1920 + GAP), cT = -Math.floor(b / COLS) * (1080 + GAP);
    doc.artboards.add([cL, cT, cL + 1920, cT - 1080]).name = BOARDS[b];
}
/* 기본 레이어를 치우고 이름 있는 레이어로만 간다 — 원본은 레이어 1개에 155항목이 뭉쳐 있었다 */
var base = doc.layers[0];

function layer(name) { var y = doc.layers.add(); y.name = name; return y; }
/* layers.add() 는 맨 위에 넣는다. 그래서 바닥에 깔릴 것부터 만든다 —
   바탕(한지) → 틀(병풍·현판) → 글자 → 가이드 순. */
var LY = {};
var order = ["바탕", "캡쳐", "틀", "글자", "가이드"];
for (var i = 0; i < order.length; i++) LY[order[i]] = layer(order[i]);

/* 아트보드 b 의 화면좌표 (x,y) → 문서좌표. 격자 배치라 행·열을 같이 본다. */
function OX(b, x) { return (b % COLS) * (1920 + GAP) + x; }
function OY(b, y) { return -(Math.floor(b / COLS) * (1080 + GAP) + y); }

/* ── 그리기 헬퍼 ─────────────────────────────────────────────── */
function box(ly, b, x, y, w, h, fill, strokeCol, strokeW) {
    var r = ly.pathItems.rectangle(OY(b, y), OX(b, x), w, h);
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
        var dx = wantL - gb[0], dy = (OY(b, y) + h / 2) - gb[1];
        if (DEBUG_TEXT) L("    [" + pass + "] \"" + s + "\" w=" + Math.round(w)
            + " gbL=" + Math.round(gb[0]) + " wantL=" + Math.round(wantL)
            + " dx=" + Math.round(dx) + " align=<" + align + ">");
        if (pass && Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) break;
        t.translate(dx, dy);
    }
    return t;
}

/** 글자 일부만 색을 바꾼다 — parts = [[글자, 색], ...]. 자리는 text() 가 전체 문자열로 잡는다. */
function textRuns(ly, b, x, y, parts, size, align, maxW) {
    var s = "";
    for (var i = 0; i < parts.length; i++) s += parts[i][0];
    var t = text(ly, b, x, y, s, size, parts[0][1], align, maxW);
    var at = 0;
    for (var p = 0; p < parts.length; p++) {
        var n = parts[p][0].length;
        if (p > 0) for (var c = at; c < at + n; c++)
            t.textRange.characters[c].characterAttributes.fillColor = parts[p][1];
        at += n;
    }
    return t;
}

/** 역삼각형 ▼ — 궁서에 없을 수 있어 도형으로 그린다 (roll_ad.py tri 와 같은 비율) */
function tri(ly, b, cx, cy, s, color) {
    var p = ly.pathItems.add();
    p.setEntirePath([[OX(b, cx - s), OY(b, cy - s * 0.62)], [OX(b, cx + s), OY(b, cy - s * 0.62)],
                     [OX(b, cx), OY(b, cy + s * 0.78)]]);
    p.closed = true; p.stroked = false; p.filled = true; p.fillColor = color;
    p.name = "▼";
    return p;
}

/**
 * 현판(CTA) — 면 + 안쪽 금테 + 궁서 + 양옆 ▼. 롤링 광고의 '고정댓글 확인' 판과 같은 구성이다.
 * 한지 위에서는 옻칠 면 + 한지밝 글자, 옻칠 위에서는 뒤집는다 (롤링 광고 옻칠판과 같은 규칙).
 */
function ctaPlaque(lyB, lyT, b, x, y, w, h, s, face, ink) {
    var inset = Math.max(3, Math.round(h * 0.08)), edge = Math.max(1.5, h * 0.03);
    box(lyB, b, x, y, w, h, face, null, 0).name = "현판 면";
    box(lyB, b, x + inset, y + inset, w - inset * 2, h - inset * 2, null, 금테, edge).name = "현판 금테";
    var size = h * 0.55, triS = size * 0.2, gap = triS * 2.4;
    var inner = w - (inset + edge) * 2 - (gap + triS) * 2 - h * 0.3;
    var t = text(lyT, b, x + w / 2, y + h / 2, s, size, ink, "center", inner);
    var g = t.geometricBounds, tw = g[2] - g[0];
    tri(lyT, b, x + w / 2 - tw / 2 - gap, y + h / 2, triS, ink);
    tri(lyT, b, x + w / 2 + tw / 2 + gap, y + h / 2, triS, ink);
    return t;
}

/** 한지를 사각형 하나만큼만 깐다 — 뚫린 판(오버레이)에서 띠·칸만 불투명하게 할 때 */
function hanjiIn(b, x, y, w, h, name) {
    var bg = new File(OUT + "/" + CFG.bgPng);
    if (!bg.exists) throw new Error("한지 바탕이 없습니다: " + bg.fsName);
    var g = LY["바탕"].groupItems.add();
    g.name = name || "한지";
    var p = g.placedItems.add();
    p.file = bg;
    p.left = OX(b, 0);
    p.top  = OY(b, 0);
    p.embed();
    var r = g.pathItems.rectangle(OY(b, y), OX(b, x), w, h);   // 맨 위에 둬야 클리핑이 된다
    r.clipping = true; r.filled = false; r.stroked = false;
    g.clipped = true;
    return g;
}

/** 옻칠 판 + 안쪽 금테 — 롤링 광고 옻칠판과 같은 재질의 띠 */
function lacquer(ly, b, x, y, w, h) {
    box(ly, b, x, y, w, h, 옻칠, null, 0).name = "옻칠 판";
    box(ly, b, x + 6, y + 6, w - 12, h - 12, null, 금테, 2).name = "금테";
}

/** 그림 파일을 폭에 맞춰 놓는다 (높이는 비율). 돌려준 항목의 height 로 세로 자리를 잡는다. */
function placeW(ly, b, fileName, x, y, w, opacity) {
    var f = new File(OUT + "/" + fileName);
    if (!f.exists) { L("  !! 그림이 없습니다: " + f.fsName); return null; }
    var p = ly.placedItems.add();
    p.file = f;
    var k = w / p.width;
    p.resize(k * 100, k * 100);
    p.left = OX(b, x);
    p.top  = OY(b, y);
    p.embed();
    var r = ly.pageItems[0];                  // embed 뒤에는 rasterItem 으로 바뀐다
    if (opacity !== undefined) r.opacity = opacity;
    return r;
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
    p.top  = OY(b, 0);
    p.embed();
    L("  한지 바탕: " + bg.name);
}

/* ── 캡쳐 가져오기 ───────────────────────────────────────────
   차트·포지션표·수익요약·댓글창·시계·롤링광고·카드는 우리가 그릴 그림이 아니다.
   차트명가도 같은 프로그램(MT5·유튜브 댓글)을 쓰니 트팩 것을 그대로 쓴다 (2026-09-16 이정찬).

   **원본 .ai 에서 항목째 복사한다.** 참고용 PNG(8000px JPG 압축본)를 1920 으로 줄여서
   자르면 압축+축소로 두 번 열화된다. 원본 .ai 안에는 같은 그림이 원해상도 래스터로 들어 있다.

   자리 기준은 dump_caps.jsx 로 실측한 값이다 (아트보드 안 좌표, 1920x1080 기준).
     보드 08 = 최종 출력 샘플(메인) · 보드 04 = 오프닝
   텔레그램은 원본 .ai 에도 빈 자리(시안 테두리)로만 있다 — 트팩도 캡쳐를 안 넣어 뒀다. */
var CAPS = {
    롤링광고: { ab: 8, x:    0, y:   2, w: 1920, h: 121 },
    시계:     { ab: 8, x: 1566, y: 122, w:  308, h:  90 },
    차트화면: { ab: 8, x:    1, y: 181, w: 1520, h: 901 },
    포지션표: { ab: 8, x: 1526, y: 263, w:  386, h: 282 },
    수익요약: { ab: 8, x: 1525, y: 540, w:  390, h: 125 },
    댓글창:   { ab: 8, x: 1534, y: 665, w:  379, h: 417 },
    카드4장:  { ab: 4, x:  661, y: 761, w:  770, h: 289 },
    신청버튼: { ab: 4, x: 1137, y: 714, w:  213, h:  40 }
};

var refDoc = null, refABS = null;
function openRef() {
    if (refDoc) return refDoc;
    var f = new File(LAB + "/" + CFG.refAi);
    if (!f.exists) { L("  !! 원본 .ai 가 없습니다: " + f.fsName); return null; }
    /* 원본 안에 끊긴 링크(09012023_15.jpg)가 있어 "연결된 파일을 찾을 수 없습니다" 모달이 뜬다.
       뜨면 스크립트가 거기서 멈춘다 (2026-09-17 사용자가 화면에서 발견 — 빌드가 오래 걸리던 원인).
       원본은 저장하지 않으니 링크를 고치지 않고, 여는 동안만 알림을 끈다. 캡쳐는 임베드 항목이라 영향 없다. */
    var ui = app.userInteractionLevel;
    app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
    try { refDoc = app.open(f); }
    finally { app.userInteractionLevel = ui; }
    refABS = [];
    for (var i = 0; i < refDoc.artboards.length; i++) {
        var r = refDoc.artboards[i].artboardRect;
        refABS.push({ l: r[0], t: r[1], r: r[2], b: r[3] });
    }
    L("  원본 열기: " + refDoc.name);
    return refDoc;
}
function closeRef() {
    if (!refDoc) return;
    refDoc.close(SaveOptions.DONOTSAVECHANGES);   // 원본은 절대 건드리지 않는다
    refDoc = null;
    app.activeDocument = doc;
}

/** 원본에서 spec 에 맞는 항목을 찾는다 (가운데 좌표·크기로 식별) */
function findCap(spec) {
    var A = refABS[spec.ab], tol = 6;
    var found = null;
    function walk(c, depth) {
        for (var i = 0; i < c.pageItems.length && !found; i++) {
            var it = c.pageItems[i];
            if (it.typename === "GroupItem") { if (depth < 4) walk(it, depth + 1); continue; }
            if (it.typename !== "RasterItem" && it.typename !== "PlacedItem") continue;
            var bb;
            try { bb = it.geometricBounds; } catch (e) { continue; }
            var lx = bb[0] - A.l, ly = A.t - bb[1];
            var w = bb[2] - bb[0], h = bb[1] - bb[3];
            if (Math.abs(lx - spec.x) <= tol && Math.abs(ly - spec.y) <= tol
             && Math.abs(w - spec.w) <= tol && Math.abs(h - spec.h) <= tol) found = it;
        }
    }
    for (var L2 = 0; L2 < refDoc.layers.length && !found; L2++) walk(refDoc.layers[L2], 0);
    return found;
}

/** 자른 자리 밖으로 넘치는 것을 가린다 — 클리핑 그룹 */
function clipTo(item, b, x, y, w, h) {
    var g = LY["캡쳐"].groupItems.add();
    item.move(g, ElementPlacement.PLACEATEND);
    var r = g.pathItems.rectangle(OY(b, y), OX(b, x), w, h);
    r.clipping = true; r.filled = false; r.stroked = false;
    g.clipped = true;
    return g;
}

/**
 * 캡쳐 하나를 내 칸에 놓는다.
 *   mode "cover" — 칸을 꽉 채우고 넘치는 건 자른다 (차트처럼 비율이 다른 것)
 *   mode "fit"   — 비율 그대로 칸 안에 들어가게 (표·댓글처럼 잘리면 안 되는 것)
 */
function cap(b, name, x, y, w, h, mode) {
    if (!openRef()) return null;
    var spec = CAPS[name];
    var it = findCap(spec);
    if (!it) { L("  !! 원본에서 못 찾음: " + name); return null; }

    app.activeDocument = refDoc;
    var dup = it.duplicate(LY["캡쳐"], ElementPlacement.PLACEATEND);   // 문서 사이 복사
    app.activeDocument = doc;

    var sw = dup.width, sh = dup.height;
    var k = (mode === "cover") ? Math.max(w / sw, h / sh) : Math.min(w / sw, h / sh);
    dup.resize(k * 100, k * 100);
    dup.left = OX(b, x + (w - sw * k) / 2);
    dup.top  = OY(b, y + (h - sh * k) / 2);
    if (mode === "cover") clipTo(dup, b, x, y, w, h);
    return dup;
}

/** 캡쳐를 칸에 **꽉 채운다** — 비율을 지키지 않고 늘린다.
    화면 캡쳐는 OBS 에서도 칸을 채우는 것이라, 비율을 지키면 좌우에 한지 띠가 남아 어색하다.
    2026-09-16 사용자가 06 에서 직접 그렇게 고쳤다 (fit 으로 남던 여백을 없앰). */
function capFill(b, name, x, y, w, h) {
    if (!openRef()) return null;
    var it = findCap(CAPS[name]);
    if (!it) { L("  !! 원본에서 못 찾음: " + name); return null; }
    app.activeDocument = refDoc;
    var dup = it.duplicate(LY["캡쳐"], ElementPlacement.PLACEATEND);
    app.activeDocument = doc;
    /* 크기는 **resize() 로** 바꾼다. `.width = w; .height = h` 로 주면 일러스트레이터가 멈춘다 —
       문서 사이로 복사해 온 래스터에 치수를 직접 박으면 원본 문서를 다시 보러 가는 듯하다.
       2026-09-16 두 번 다 9분 넘게 응답 없음(CPU 20초에 +1s = 사실상 0)으로 굳었다.
       처음엔 '사용자가 쓰던 인스턴스와 엉켰다' 고 봤는데, 내가 띄운 깨끗한 인스턴스에서도
       똑같이 굳어서 원인이 이쪽임이 드러났다. resize() 는 앞서 cap() 에서 잘 돌던 길이다. */
    var sx = w / dup.width * 100, sy = h / dup.height * 100;
    dup.resize(sx, sy);
    dup.left = OX(b, x);
    dup.top  = OY(b, y);
    return dup;
}

/** 오른쪽 패널 네 칸 + 롤링 광고 — 두 샘플이 똑같이 쓴다.
    칸 좌표는 사용자 직접 수정판(06) 실측값이다. 내 1차판은 폭을 395 로 잡아
    패널 오른쪽 끝(1903)을 15px 넘고 있었다 — 사용자가 379 로 맞춰 놓은 것을 따른다. */
function capPanel(b) {
    var T = 2, PX = Z.패널.x + T, PW = 379;       // 1523 ~ 1902
    var B0 = 1063;                                 // 바깥 병풍 안쪽 아래

    /* 롤링 광고 — D 가 만든 전통판 배너를 쓴다 (2026-09-16).
       트팩 원본에서 복사하던 것을 대체한다. 문구는 트팩 것 그대로라 바뀐 건 톤뿐이고,
       한지 바탕이라 광고가 돌든 안 돌든 같은 종이 위에서 이어진다.
       글자가 양끝까지 차 있어 자르면 안 되므로 틀 안쪽에 통째로 넣는다. */
    var ad = new File(OUT + "/" + CFG.rollAdJpg);
    if (ad.exists) {
        var ap = LY["캡쳐"].placedItems.add();
        ap.file = ad;
        var ak = 1886 / ap.width;
        ap.resize(ak * 100, ak * 100);
        ap.left = OX(b, 17);
        ap.top  = OY(b, 17 + (Z.광고.h - 20 - ap.height) / 2);
        ap.embed();
        L("  롤링 광고: " + decodeURI(ad.name) + " (전통판)");
    } else {
        L("  !! 롤링 광고 배너가 없어 트팩 것을 씁니다: " + ad.fsName);
        cap(b, "롤링광고", 17, 17, 1886, Z.광고.h - 20, "fit");
    }

    /* 시계만 비율을 지킨다 — 사용자 판에서도 안 바뀌었다 (253x74 그대로) */
    cap(b, "시계", Z.시계.x + T, Z.시계.y + T, Z.시계.w - T * 2, Z.시계.h - T * 2, "fit");

    capFill(b, "포지션표", PX, Z.포지션.y + 1, PW, Z.메모.y - (Z.포지션.y + 1));
    capFill(b, "수익요약", PX, Z.메모.y + 2,   PW, Z.댓글.y + 1 - (Z.메모.y + 2));
    capFill(b, "댓글창",   PX, Z.댓글.y + 2,   PW, B0 - (Z.댓글.y + 2));
}

/** 오프닝에 얹는 우리 그래픽 — 편액·목차. 자리는 트팩 오프닝 실측 행에 맞췄다.
    (트팩: 종목 y271~350 · 1줄 y402~487 · 2줄 y529~614 · 버튼 y714~756 · 카드 y765~1050) */
function openingArt(b) {
    var 글 = LY["글자"], cx = 1046;          // 트팩 오른쪽 블록 가운데 (682~1409)
    var probe = 글.textFrames.add();
    probe.contents = COPY.종목;
    probe.textRange.characterAttributes.textFont = 궁서;
    probe.textRange.characterAttributes.size = 46;
    app.redraw();
    var pw = probe.geometricBounds[2] - probe.geometricBounds[0] + 64;
    probe.remove();
    hyeonpan(LY["틀"], 글, b, cx - pw / 2, 271, pw, 79, COPY.종목, 46);
    text(글, b, cx, 444, COPY.오프닝1, 66, 먹, "center");
    text(글, b, cx, 571, COPY.오프닝2, 66, 먹, "center");
    /* 카드 4장은 트팩 그래픽을 그대로 쓴다 (문구도 트팩 것 그대로 — 2026-09-16 이정찬).
       '고정댓글 확인' 빨간 알약만 우리 현판으로 바꾼다 (2026-09-17 이정찬). 자리는 트팩 알약 그대로. */
    ctaPlaque(LY["틀"], 글, b, 1137, 714, 213, 40, COPY.고정댓글, 옻칠, 한지밝);
    cap(b, "카드4장",   661, 761, 770, 289, "fit");
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
        bp.top  = OY(b, Z.현판띠.y);
        bp.embed();
    }
    var 띠중 = Z.현판띠.y + Z.현판띠.h / 2;

    /* ── 정보 띠 안 (2026-09-16 사용자 직접 수정판을 그대로 따른다) ──────
       06 아트보드를 사용자가 손으로 고친 것을 값으로 떠서(dump_board.jsx) 옮겼다.

       바뀐 것
         · 편액(옻칠 판 + 금테)을 **없앴다** — 로고를 한지 띠 위에 직접 올린다.
           로고 자체가 워드마크+심볼이라 판까지 두르면 무거웠다.
         · 로고를 키웠다 (144x36 → 215x54)
         · 정보 글자를 27pt 먹 → **31pt 부가설명 #334155** 로 (컬러팔레트.png).
           방송시간·입장문의는 '부가 설명 자막' 이다. 한때 #0D9488 을 썼는데 그건
           매수/매도처럼 반대되는 개념에만 쓰는 색이라 잘못이었다.
         · 구분선을 글자 길이에 맞게 옮겼다 (253/1051 → 395/975)
       좌표는 사용자 판 실측값이다. 바꾸려면 여기만 고치면 여섯 아트보드에 다 걸린다. */
    var LOGO = { x: 90, y: 152, w: 215 };          // 높이는 비율로 따라온다
    /* 2026-09-17 사용자 직접 수정판 2차: 31 → 36pt, 왼쪽으로 35 · 위로 4 (상자 위 161, 높이 36.5).
       구분선·로고는 그대로다 (판 전체를 떠서 비교 — 바뀐 건 이 두 글자뿐). */
    var 정보 = [
        { x: 434, seam: 395, text: COPY.방송시간 },
        { x: 999, seam: 975, text: COPY.입장문의 }
    ];
    var 정보크기 = 36;
    /* 글자 상자 세로 가운데 = 161 + 36.5/2 = 179.25 ≈ 띠 가운데(179) */
    var 정보중 = 띠중;

    var logo = new File(OUT + "/" + CFG.logoPng);
    if (logo.exists) {
        var lp = 글.placedItems.add();
        lp.file = logo;
        var lk = LOGO.w / lp.width;
        lp.resize(lk * 100, lk * 100);
        lp.left = OX(b, LOGO.x);
        lp.top  = OY(b, LOGO.y);
        lp.embed();
    } else {
        L("  !! 로고가 없습니다 — make_bg.py 를 먼저 돌리세요: " + logo.fsName);
        text(글, b, LOGO.x, 띠중, COPY.채널, 34, 먹, "left");
    }

    /* 정보 둘 — 앞에 쪽빛 세로 가는 선을 세워 가른다 */
    for (var q = 0; q < 정보.length; q++) {
        seam(틀, b, 정보[q].seam, Z.현판띠.y + 16, T, Z.현판띠.h - 32);
        text(글, b, 정보[q].x, 정보중, 정보[q].text, 정보크기, 부가설명, "left");
    }

    /* 4) 포지션 헤더 — 트팩은 회색 그라디언트. 여기서는 쪽빛 바 + 흰 궁서 */
    box(틀, b, Z.헤더.x + T, Z.헤더.y + T, R0 - Z.헤더.x - T, Z.헤더.h - T, 쪽, null, 0);   // 높이 24 (사용자 판)
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

/* ── [1] 오프닝 프레임 — 틀 + 우리 그래픽. 바탕은 안 깐다 ──────────
   OBS 에서 맨 아래 배경 레이어 위에 얹는 오버레이다. 텔레그램 자리는 캡쳐가 들어오므로
   비워 둔다 (트팩 오프닝 프레임도 그 자리만 뚫려 있다). */
L("");
L("■ " + BOARDS[1]);
drawFrame(1);
openingArt(1);

/* ── [2] 메인 방송 프레임 — 틀만. 가운데는 뚫려 있어야 한다 ───────── */
L("");
L("■ " + BOARDS[2]);
drawFrame(2);

/* ── [3] 레이어 가이드 — OBS 에 뭘 어디 올리는지 (트팩 Reference_01) ── */
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

/* ── [4] 최종 출력 샘플 — 오프닝 (트팩 Reference_02) ───────────── */
L("");
L("■ " + BOARDS[4]);
hanji(LY["바탕"], 4);
capPanel(4);
/* 텔레그램은 원본 .ai 에도 빈 자리로만 있다 — 트팩도 캡쳐를 안 넣어 뒀다.
   자리만 쪽빛 가는 테두리로 표시한다 (방송 때 디스플레이 캡쳐가 들어온다). */
box(LY["틀"], 4, 110, 245, 464, 786, null, 쪽, 2);
drawFrame(4);
openingArt(4);

/* ── [5] 최종 출력 샘플 — 메인 (트팩 Reference_03) ─────────────── */
L("");
L("■ " + BOARDS[5]);
hanji(LY["바탕"], 5);
capPanel(5);
cap(5, "차트화면", 17, Z.차트.y + 2, 1502, 843, "cover");
drawFrame(5);

closeRef();

/* ════ 07~10 — 트팩에 있고 우리에게 없던 판 (2026-09-17) ════════════════
   틀 문법은 01~06 과 같다: 바깥 병풍 한 바퀴(쪽 12+2) + 칸 사이 쪽빛 2px 이음선.
   캡쳐 자리는 뚫어 둔다 — 06 처럼 캡쳐를 채워 넣지 않는다. */

/** 바깥 병풍 + 이음선 목록. segs = [[x, y, w, h], ...] */
function frameSeams(b, segs) {
    var 틀 = LY["틀"];
    byeongpung(틀, b, 0, 0, 1920, 1080, 12);
    for (var i = 0; i < segs.length; i++) seam(틀, b, segs[i][0], segs[i][1], segs[i][2], segs[i][3]);
}

/** 포지션 헤더 바 — 쪽빛 + 흰 궁서 (01~06 과 같은 모양) */
function posHeader(b, x, y, w, h, size) {
    box(LY["틀"], b, x, y, w, h, 쪽, null, 0).name = "포지션 헤더";
    var colX = [x + w * 0.18, x + w * 0.5, x + w * 0.82];
    for (var i = 0; i < COPY.헤더.length; i++)
        text(LY["글자"], b, colX[i], y + h / 2, COPY.헤더[i], size, 흰, "center");
}

/* ── [6] 07 화면 조정 중 — 트팩 Artboard 13 ──────────────────────
   방송 화면을 잠깐 덮는 판이라 전부 불투명이다. 트팩은 회색 면에 자기 로고 심볼을 크게 깔고
   흰 글자를 얹었다. 우리는 한지 위에 로고 심볼을 옅게, 먹 궁서를 크게. 틀·정보 띠는 01 과 같다. */
L("");
L("■ " + BOARDS[6]);
(function () {
    var b = 6, 글 = LY["글자"];
    hanji(LY["바탕"], b);
    drawFrame(b);
    /* 차트 자리 가운데 (뚫린 자리 x17~1521 · y220~1063) */
    var cx = (17 + 1521) / 2, cy = (220 + 1063) / 2;
    var m = placeW(LY["틀"], b, CFG.logoMarkPng, cx - 330, cy - 330, 660, 12);
    if (m) { m.top = OY(b, cy - m.height / 2); m.name = "로고 심볼 (옅게)"; }
    var t = text(글, b, cx, cy, COPY.화면조정, 150, 먹, "center");
    t.textRange.characterAttributes.strokeColor = 먹;       // 궁서가 얇아 크게 써도 가볍다 — 롤링 광고와 같은 처리
    t.textRange.characterAttributes.strokeWeight = 2;
    /* 댓글 자리에도 트팩처럼 심볼을 아주 옅게 */
    var m2 = placeW(LY["틀"], b, CFG.logoMarkPng, Z.댓글.x + 100, Z.댓글.y + 100, 200, 8);
    if (m2) { m2.top = OY(b, Z.댓글.y + (Z.댓글.h - m2.height) / 2); m2.name = "로고 심볼 (옅게)"; }
})();

/* ── [7] 08 메인 하단광고 (SM) — 트팩 Artboard 12 copy 2 ─────────────
   트팩 실측: 위 띠 y0~121(로고·방송시간·입장문의) + 오른쪽 위 시계 x1521~1920 · 차트 y121~967 ·
   오른쪽 패널 헤더 126~177 / 포지션 177~374 / 수익 374~503 / 댓글 503~967 · 롤링 광고 y967~1080 전폭.
   OBS 오버레이라 캡쳐·광고·시계 자리는 뚫어 두고, 위 띠만 한지로 막는다. */
L("");
L("■ " + BOARDS[7]);
(function () {
    var b = 7, 글 = LY["글자"], PX = 1521, TOP = 121, AD = 967, R0 = 1903, L0 = 17;
    hanjiIn(b, L0, L0, PX - L0, TOP - L0, "한지 — 위 띠");
    frameSeams(b, [
        [L0, TOP, R0 - L0, 2],          // 위 띠 아래 (전폭)
        [L0, AD,  R0 - L0, 2],          // 광고 위 (전폭)
        [PX, L0,  2, AD - L0],          // 차트 | 패널
        [PX, 177, R0 - PX, 2],          // 헤더 아래
        [PX, 374, R0 - PX, 2],          // 포지션 아래
        [PX, 503, R0 - PX, 2]           // 수익 아래
    ]);
    posHeader(b, PX + 2, TOP + 2, R0 - PX - 2, 177 - TOP - 2, 22);
    var 띠중 = (L0 + TOP) / 2;
    var lg = placeW(글, b, CFG.logoPng, 60, 띠중 - 27, 215);
    if (lg) lg.top = OY(b, 띠중 - lg.height / 2);
    seam(LY["틀"], b, 380, 띠중 - 23, 2, 46);
    text(글, b, 419, 띠중, COPY.방송시간SM, 36, 부가설명, "left");
    seam(LY["틀"], b, 960, 띠중 - 23, 2, 46);
    text(글, b, 999, 띠중, COPY.입장문의, 36, 부가설명, "left");
})();

/* ── [8] 09 메인 정보칸 — 트팩 원본의 아트보드 밖 레이아웃 ──────────────
   트팩 실측: 위 띠 y0~121(가운데 로고) · 왼쪽 정보칸 x0~360 · 차트 x360~1522 y121~971 ·
   거래내역 y971~1080 · 오른쪽 패널 포지션 121~241 / 수익 241~548 / 시계 548~615 / 댓글 615~1080.
   정보칸 안: 입장방법(y127 h138) · 방송시간(273 h64) · 작은 차트(346 h300, 캡쳐) ·
   진입 기준(655) · 목표가(778) · 손절가(875) · 매매 원칙(974). 트팩은 칸 끝이 1074 인데
   우리는 바깥 병풍 안쪽이 1063 이라 네 칸을 650~1063 에 맞춰 조금 줄였다.
   색: 트팩 회·파·빨·회 → 쪽 · 대비강조 · 인주 · 쪽. 목표가와 손절가는 **반대되는 개념**이라
   팔레트의 대비강조(#0D9488)와 인주를 짝으로 쓴다. 본문은 먹. */
L("");
L("■ " + BOARDS[8]);
(function () {
    var b = 8, 글 = LY["글자"], 틀 = LY["틀"], L0 = 17, R0 = 1903, B0 = 1063;
    var TOP = 121, CX = 360, PX = 1522, CHB = 971, MINI = { y: 346, h: 300 };
    hanjiIn(b, L0, L0, R0 - L0, TOP - L0, "한지 — 위 띠");
    hanjiIn(b, L0, TOP + 2, CX - L0, MINI.y - TOP - 2, "한지 — 정보칸 위");
    hanjiIn(b, L0, MINI.y + MINI.h, CX - L0, B0 - MINI.y - MINI.h, "한지 — 정보칸 아래");
    frameSeams(b, [
        [L0, TOP, R0 - L0, 2],          // 위 띠 아래
        [CX, TOP, 2, B0 - TOP],         // 정보칸 | 차트
        [PX, TOP, 2, B0 - TOP],         // 차트 | 패널
        [CX, CHB, PX - CX, 2],          // 차트 | 거래내역
        [PX, 241, R0 - PX, 2],
        [PX, 548, R0 - PX, 2],
        [PX, 615, R0 - PX, 2],
        [L0, MINI.y, CX - L0, 2],       // 작은 차트 위·아래
        [L0, MINI.y + MINI.h, CX - L0, 2]
    ]);
    /* 위 띠 — 로고 가운데 */
    var lg = placeW(글, b, CFG.logoPng, 960 - 150, 30, 300);
    if (lg) lg.top = OY(b, (L0 + TOP) / 2 - lg.height / 2);

    var X = 25, W = CX - X - 8, cx = X + W / 2, 본문 = 17;
    /* 입장방법 — 옻칠 현판 제목 + 두 줄 */
    box(틀, b, X, 131, W, 128, null, 쪽, 2);
    hyeonpan(틀, 글, b, X, 131, W, 42, COPY.정보칸.입장제목, 24);
    for (var i = 0; i < 2; i++)
        textRuns(글, b, cx, 196 + i * 36, [[COPY.정보칸.입장줄[i][0], 먹], [COPY.정보칸.입장줄[i][1], 메인타이틀]], 본문 + 2, "center", W - 12);
    /* 방송시간 */
    box(틀, b, X, 271, W, 64, null, 쪽, 2);
    text(글, b, cx, 303, COPY.방송시간, 24, 부가설명, "center", W - 16);

    /* 네 칸 — 650~1063 (413) 을 트팩 높이 비율(126:99:101:100)로 나눈다 */
    var 색 = [쪽, 대비강조, 인주, 쪽], 높이 = [126, 99, 101, 100], 합 = 426, 시작 = 652, 끝 = B0 - 6;
    var y = 시작;
    for (var c = 0; c < 4; c++) {
        var h = Math.round((끝 - 시작) * 높이[c] / 합);
        var 칸 = COPY.정보칸.칸[c];
        box(틀, b, X, y, W, h - 4, null, 색[c], 2);
        box(틀, b, X, y, W, 32, 색[c], null, 0).name = 칸.제목 + " 머리";
        text(글, b, cx, y + 16, 칸.제목, 22, 흰, "center");
        var 줄간 = (h - 4 - 32) / 칸.줄.length;
        for (var j = 0; j < 칸.줄.length; j++)
            text(글, b, X + 8, y + 32 + 줄간 * (j + 0.5), 칸.줄[j], 본문, 먹, "left", W - 14);
        y += h;
    }
})();

/* ── [9] 10 메인 VIP 안내 — 트팩 원본의 아트보드 밖 레이아웃(통짜 그림) ──────
   그림(2656x1449)을 1920 폭으로 줄여 잰 자리 × 세로 1080/1047:
   위 띠 y0~175 (왼쪽 안내 x0~1528 · 오른쪽 시작일 1528~1920) · 차트 두 개 + 거래내역 y175~975 ·
   경고 문구 975~1005 · 아래 띠 1005~1080 (x0~1528) · 오른쪽 패널 포지션 175~583 / 시계 583~648 / 댓글 648~1080.
   트팩은 검정 판 + 민트 테두리. 우리는 롤링 광고 옻칠판과 같은 옻칠 판 + 금테, 강조는 메인 타이틀색. */
L("");
L("■ " + BOARDS[9]);
(function () {
    var b = 9, 글 = LY["글자"], 틀 = LY["틀"], L0 = 17, R0 = 1903, B0 = 1063;
    var TOP = 175, PX = 1528, WARN = 975, BOT = 1005;
    frameSeams(b, [
        [L0, TOP, R0 - L0, 2],
        [PX, L0, 2, B0 - L0],
        [L0, WARN, PX - L0, 2],
        [PX, 583, R0 - PX, 2],
        [PX, 648, R0 - PX, 2]
    ]);
    /* 위 왼쪽 — 안내 */
    lacquer(틀, b, L0 + 4, L0 + 4, PX - L0 - 8, TOP - L0 - 8);
    text(글, b, 45, 50, COPY.VIP.제목, 36, 메인타이틀, "left", 730);
    for (var i = 0; i < 2; i++) text(글, b, 45, 96 + i * 42, COPY.VIP.왼줄[i], 28, 한지밝, "left", 730);
    for (var j = 0; j < 3; j++) text(글, b, 800, 54 + j * 42, COPY.VIP.오른줄[j], 28, 한지밝, "left", 700);
    /* 위 오른쪽 — 시작일 */
    lacquer(틀, b, PX + 6, L0 + 4, R0 - PX - 10, TOP - L0 - 8);
    var rx = (PX + R0) / 2;
    text(글, b, rx, 45, COPY.VIP.시작, 26, 한지밝, "center", 340);
    var 금액 = text(글, b, rx, 98, COPY.VIP.금액, 64, 금테, "center", 340);
    금액.textRange.characterAttributes.strokeColor = 금테;
    금액.textRange.characterAttributes.strokeWeight = 1.5;
    text(글, b, rx, 146, COPY.VIP.구독, 28, 한지밝, "center", 340);
    /* 경고 문구 — 한지 띠 위 인주 */
    hanjiIn(b, L0, WARN + 2, PX - L0, BOT - WARN - 2, "한지 — 경고 띠");
    text(글, b, L0 + 14, (WARN + BOT) / 2 + 1, COPY.VIP.경고, 20, 인주, "left", PX - L0 - 28);
    /* 아래 띠 */
    lacquer(틀, b, L0 + 4, BOT + 2, PX - L0 - 8, B0 - BOT - 4);
    textRuns(글, b, 45, (BOT + B0) / 2, [[COPY.VIP.하단[0], 한지밝], [COPY.VIP.하단[1], 메인타이틀]], 36, "left", PX - 90);
})();

/* ── 저장 ───────────────────────────────────────────────────── */
try { base.remove(); } catch (e) {}

var outFile = new File(OUT + "/" + CFG.outAi);
var so = new IllustratorSaveOptions();
/* CS6(ILLUSTRATOR17)로 내리면 글자가 '이전 버전 텍스트'가 되어 열 때마다 "업데이트하면 문자 위치가
   바뀔 수 있다" 창이 뜬다 (2026-09-17 실측). 팀장이 열어 고칠 파일이라 현재 형식으로 둔다. */
so.compatibility = Compatibility.ILLUSTRATOR24;
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

/* 다 만들었으면 닫는다 — 안 닫으면 돌릴 때마다 문서가 쌓인다.
   내용은 위 saveAs 로 이미 디스크에 있다. (2026-09-16: 11개까지 쌓여 있는 걸 사용자가 발견) */
var nBoards = doc.artboards.length;          // 닫기 전에 세어 둔다 — 닫은 doc 은 못 읽는다
doc.close(SaveOptions.DONOTSAVECHANGES);
L("문서 닫음 — 결과는 디스크에 있다");

var lf = new File(OUT + "/build_log.txt");
lf.encoding = "UTF-8"; lf.open("w"); lf.write(log.join(String.fromCharCode(10))); lf.close();

"OK 아트보드 " + nBoards;
