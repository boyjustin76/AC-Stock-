/**
 * 롤링 광고 옻칠판 11장을 팀장이 고칠 수 있는 .ai 한 파일로 짓는다.
 *
 * 새로 그리지 않는다. rollad_layout.py 가 D 의 roll_ad.py 를 돌리며 적어 둔
 * _rollad/layout.json 을 그대로 옮긴다 — 글자는 궁서 텍스트, 판·금테·▼ 는 벡터,
 * 로고 무늬는 png 임베드 + 불투명도. 1pt = 1px 이라 아트보드가 곧 8000x504 / 8000x750 이다.
 *
 *     python tools/illustrator/rollad_layout.py --out tools/illustrator/_rollad
 *     .\tools\illustrator\run.ps1 build_rollad
 *
 * PIL 과 일러스트레이터의 좌표 차이 (D 확인, 2026-09-17)
 *   · rectangle 은 끝 좌표 포함 → 폭 = x1 - x0 + 1
 *   · outline 은 상자 안쪽으로 자란다 → 선 가운데 정렬이면 w/2 만큼 들여 그린다
 *   · 굵기 bold=1 은 사방 1px 팽창 → 같은 색 선 2pt (바깥 1pt), 모서리 각지게
 */
// @target illustrator

var HERE = new File($.fileName).parent;
$.evalFile(new File(HERE.fsName + "/_lib.jsx"));
var PATHS = readPaths(HERE);
var OUT = PATHS.outDir;
var SRC = HERE.fsName + "/_rollad";

var log = [];
function L(s) { log.push(String(s)); }

function readJson(path) {
    var f = new File(path);
    if (!f.exists) throw new Error("없습니다 — 먼저 rollad_layout.py 를 돌리세요: " + f.fsName);
    f.encoding = "UTF-8"; f.open("r"); var t = f.read(); f.close();
    return eval("(" + t + ")");
}
var LAY = readJson(SRC + "/layout.json");

var 궁서 = pickFont(["GungSuh", "Gungsuh", "궁서"], L);
L("글꼴: " + 궁서.name);

/* ── 문서 · 아트보드 ──────────────────────────────────────────
   8000 폭 판을 세로로 쌓는다. 캔버스 한계(원점 ±8172pt) 안에 들도록 x 는 -4000 에서 시작하고,
   높이 합(약 6400)도 원점 위아래로 나눠 놓는다. */
var GAP = 120, X0 = -4000;
var total = 0;
for (var i = 0; i < LAY.boards.length; i++) total += LAY.boards[i].h + GAP;
var Y0 = Math.round(total / 2);

var doc = app.documents.add(DocumentColorSpace.RGB, 8000, 504);
var base = doc.layers[0];
var TOPS = [];
var y = Y0;
for (var b = 0; b < LAY.boards.length; b++) {
    var B = LAY.boards[b];
    var rect = [X0, y, X0 + B.w, y - B.h];
    if (b === 0) { doc.artboards[0].artboardRect = rect; doc.artboards[0].name = B.name; }
    else doc.artboards.add(rect).name = B.name;
    TOPS.push(y);
    y -= B.h + GAP;
}

/* 판 좌표 → 문서 좌표 */
var CUR = 0;
function DX(x) { return X0 + x; }
function DY(yy) { return TOPS[CUR] - yy; }

function colorOf(hex) { return rgb(hex); }

/* ── 이름 붙이기 — 팀장이 레이어 패널에서 알아보게 ───────────── */
function rectName(it, B) {
    if (it.stroke && it.width >= 9) return "키 박스 테두리";
    if (it.stroke) return "현판 금테";
    if (it.y0 <= 0 && it.y1 < 30) return "금테 위";
    if (it.y1 >= B.h - 1 && it.y0 > B.h - 30) return "금테 아래";
    if (it.y1 - it.y0 < 12) return "밑줄";
    return "현판 면";
}

/* ── 항목 하나씩 ─────────────────────────────────────────────── */
function addRect(g, it, B) {
    /* PIL 은 소수 좌표를 내려서 칠한다 — 밑줄(y 151.64~158.64)이 151~158 행에 찍혔다.
       소수 그대로 넣으면 위아래 행이 반씩 칠해져 1px 어긋난다 (2026-09-17 비교에서 잡음). */
    var x0 = Math.floor(it.x0), y0 = Math.floor(it.y0);
    var x1 = Math.min(Math.floor(it.x1), B.w - 1), y1 = Math.min(Math.floor(it.y1), B.h - 1);
    var w = x1 - x0 + 1, h = y1 - y0 + 1;
    var r;
    if (it.stroke) {
        var sw = it.width, half = sw / 2;
        r = g.pathItems.rectangle(DY(y0 + half), DX(x0 + half), w - sw, h - sw);
        r.filled = false;
        r.stroked = true; r.strokeColor = colorOf(it.stroke); r.strokeWidth = sw;
        r.strokeJoin = StrokeJoin.MITERENDJOIN;
    } else {
        r = g.pathItems.rectangle(DY(y0), DX(x0), w, h);
        r.stroked = false;
        r.filled = true; r.fillColor = colorOf(it.fill);
        if (it.alpha !== undefined) r.opacity = it.alpha / 255 * 100;
    }
    r.name = rectName(it, B);
    return r;
}

function addPoly(g, it) {
    var p = g.pathItems.add();
    var pts = [];
    for (var k = 0; k < it.pts.length; k++) pts.push([DX(it.pts[k][0]), DY(it.pts[k][1])]);
    p.setEntirePath(pts);
    p.closed = true;
    p.stroked = false;
    p.filled = true; p.fillColor = colorOf(it.fill);
    p.name = "▼";
    return p;
}

function addImage(g, it) {
    var f = new File(SRC + "/" + it.src);
    if (!f.exists) throw new Error("그림 자료가 없습니다: " + f.fsName);
    var p = g.placedItems.add();
    p.file = f;
    p.left = DX(it.x);
    p.top = DY(it.y);
    p.embed();
    /* embed 뒤에는 placedItem 이 rasterItem 으로 바뀌어 p 가 끊긴다 — 방금 넣은 맨 위 항목을 다시 잡는다 */
    var r = g.pageItems[0];
    if (Math.abs(r.width - it.w) > 0.5 || Math.abs(r.height - it.h) > 0.5)
        L("  !! 그림 크기 어긋남 " + it.src + " " + r.width + "x" + r.height + " (기대 " + it.w + "x" + it.h + ")");
    r.opacity = it.opacity;
    if (it.role === "mark") r.name = "로고 무늬 (불투명 " + it.opacity + "%)";
    else r.name = "차트명가 로고";
    return r;
}

/** 궁서 글자. 잉크 상자의 가운데를 PIL 이 찍은 잉크 상자 가운데에 맞춘다. */
function addText(g, it, stats) {
    var t = g.textFrames.add();
    t.contents = it.text;
    var ca = t.textRange.characterAttributes;
    ca.textFont = 궁서;
    ca.size = it.size;
    ca.fillColor = colorOf(it.color);
    if (it.bold) {
        ca.strokeColor = colorOf(it.color);
        ca.strokeWeight = 2 * it.bold;
        ca.strokeJoin = StrokeJoin.MITERENDJOIN;   // MaxFilter 정사각 커널 — 모서리가 각지다
    }
    t.name = it.text;
    t.left = DX(it.ink[0]);
    t.top = DY(it.ink[1]);

    var wantCX = DX((it.ink[0] + it.ink[2]) / 2), wantCY = DY((it.ink[1] + it.ink[3]) / 2);
    for (var pass = 0; pass < 2; pass++) {
        app.redraw();
        var d = t.duplicate();
        var o = d.createOutline();          // 글자 → 윤곽. 이 상자가 잉크 상자다
        var gb = o.geometricBounds;         // [left, top, right, bottom]
        o.remove();
        var cx = (gb[0] + gb[2]) / 2, cy = (gb[1] + gb[3]) / 2;
        var dx = wantCX - cx, dy = wantCY - cy;
        if (pass === 0) {
            var aiW = gb[2] - gb[0], pilW = it.ink[2] - it.ink[0];
            stats.push(it.text + "  폭 AI " + Math.round(aiW) + " / PIL " + pilW
                       + " (" + (Math.round(aiW / pilW * 1000) / 10) + "%)");
        }
        if (Math.abs(dx) < 0.25 && Math.abs(dy) < 0.25) break;
        t.translate(dx, dy);
    }
    return t;
}

/* ── 판마다 레이어 하나 · 클리핑 그룹 하나 ─────────────────────────
   layers.add() 는 맨 위에 쌓는다 — 레이어 패널에서 위부터 판 순서로 보이게 거꾸로 만든다. */
var LY = [];
for (var b2 = LAY.boards.length - 1; b2 >= 0; b2--) {
    var ly = doc.layers.add();
    ly.name = LAY.boards[b2].name;
    LY[b2] = ly;
}

for (CUR = 0; CUR < LAY.boards.length; CUR++) {
    var B = LAY.boards[CUR];
    var g = LY[CUR].groupItems.add();
    g.name = B.name;
    var stats = [];
    var n = { text: 0, rect: 0, poly: 0, image: 0 };

    if (B.bg) {
        var bg = g.pathItems.rectangle(DY(0), DX(0), B.w, B.h);
        bg.stroked = false; bg.filled = true; bg.fillColor = colorOf(B.bg);
        bg.name = "옻칠 바탕";
    }
    /* 그린 순서대로 쌓는다 — groupItems 에 add 하면 맨 위로 가므로 순서가 곧 z 순서다 */
    for (var k = 0; k < B.items.length; k++) {
        var it = B.items[k];
        if (it.kind === "rect") addRect(g, it, B);
        else if (it.kind === "poly") addPoly(g, it);
        else if (it.kind === "image") addImage(g, it);
        else if (it.kind === "text") addText(g, it, stats);
        n[it.kind]++;
    }
    /* 모서리 무늬가 판 밖으로 걸친다 — 판 크기로 잘라 둔다 (내보내기는 어차피 아트보드로 잘린다) */
    var clip = g.pathItems.rectangle(DY(0), DX(0), B.w, B.h);
    clip.name = "판 자르기";
    g.clipped = true;

    L(B.name + "  " + B.w + "x" + B.h + "  글자 " + n.text + " · 도형 " + (n.rect + n.poly) + " · 그림 " + n.image);
    for (var s = 0; s < stats.length; s++) L("    " + stats[s]);
}

try { base.remove(); } catch (e) {}

/* ── 저장 ───────────────────────────────────────────────────── */
/* 2026-09-17 이정찬: 한지판을 지우고 옻칠판을 롤링광고/ 바로 아래로 올렸다. 이름도 롤링광고.ai.
   ※ 이정찬이 이 파일을 손으로 고친 '롤링광고_사용자수정.ai' 가 지금의 원본이다 (jpg 도 거기서 뽑았다).
     이 스크립트로 다시 지으면 roll_ad.py 기준판이 나온다 — 사용자수정본을 덮지 않도록 이름이 다르다. */
var outDir = new Folder(OUT + "/롤링광고");
if (!outDir.exists) outDir.create();
var outFile = new File(outDir.fsName + "/롤링광고.ai");
var so = new IllustratorSaveOptions();
/* CS6(ILLUSTRATOR17)로 내리면 글자가 '이전 버전 텍스트'가 되어, 열 때마다 "업데이트하면 문자 위치가
   바뀔 수 있다" 창이 뜬다 (2026-09-17 다시 열어 보다 걸림). 팀장이 고칠 파일이라 현재 형식으로 둔다. */
so.compatibility = Compatibility.ILLUSTRATOR24;
so.pdfCompatible = true;
so.embedICCProfile = true;
doc.saveAs(outFile, so);
L("");
L("저장: " + outFile.fsName);

/* 비교용 png — 100%. 옻칠 판은 불투명, 고정댓글만 투명 (matte 끔: EXTENDSCRIPT-TRAPS ⑮) */
var cmp = new Folder(SRC + "/ai_png");
if (!cmp.exists) cmp.create();
var nB = doc.artboards.length;
for (var e = 0; e < nB; e++) {
    doc.artboards.setActiveArtboardIndex(e);
    var eo = new ExportOptionsPNG24();
    eo.artBoardClipping = true;
    eo.transparency = true;
    eo.matte = false;
    eo.antiAliasing = true;
    eo.horizontalScale = 100; eo.verticalScale = 100;
    doc.exportFile(new File(cmp.fsName + "/" + LAY.boards[e].name + ".png"), ExportType.PNG24, eo);
}
L("비교용 png " + nB + "장: " + cmp.fsName);

doc.close(SaveOptions.DONOTSAVECHANGES);

var lf = new File(OUT + "/build_log.txt");
lf.encoding = "UTF-8"; lf.open("w"); lf.write(log.join(String.fromCharCode(10))); lf.close();

"OK 아트보드 " + nB;
