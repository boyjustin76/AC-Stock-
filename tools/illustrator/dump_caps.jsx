/**
 * 원본 .ai 안의 '캡쳐' 후보를 찾아 적는다 — 래스터·링크이미지가 어느 아트보드의 어느 자리에 있나.
 *
 * 왜: 최종 출력 샘플을 만들 때 캡쳐(차트·포지션표·댓글창 등)는 우리가 그릴 게 아니라
 * 트팩 것을 그대로 쓴다. 참고용 PNG(8000px JPG 압축본)를 줄여서 자르면 두 번 열화된다.
 * 원본 .ai 안의 원본 항목을 그대로 복사해 와야 한다.
 *
 * 읽기만 한다. 원본은 저장하지 않고 닫는다.
 */
// @target illustrator

var HERE = new File($.fileName).parent;
$.evalFile(new File(HERE.fsName + "/_lib.jsx"));
var CFG = readConfig(HERE);
var PATHS = readPaths(HERE);

var out = [];
function O(s) { out.push(String(s)); }
function r0(n) { return Math.round(n); }

var src = new File(PATHS.liveframeDir + "/" + CFG.refAi);
if (!src.exists) throw new Error("원본 .ai 가 없습니다: " + src.fsName);
var doc = app.open(src);

/* 아트보드 상자 */
var ABS = [];
for (var a = 0; a < doc.artboards.length; a++) {
    var r = doc.artboards[a].artboardRect;      // [l, t, r, b]
    ABS.push({ i: a, name: doc.artboards[a].name, l: r[0], t: r[1], r: r[2], b: r[3] });
}
O("■ 아트보드");
for (var a2 = 0; a2 < ABS.length; a2++)
    O("  [" + a2 + "] " + ABS[a2].name + "  (" + r0(ABS[a2].l) + "," + r0(ABS[a2].t) + ")");
O("");

/** 항목 가운데가 어느 아트보드 안인가 */
function boardOf(b) {
    var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
    for (var i = 0; i < ABS.length; i++) {
        var A = ABS[i];
        if (cx >= A.l && cx <= A.r && cy <= A.t && cy >= A.b) return i;
    }
    return -1;
}

/* 래스터·링크이미지를 전부 훑는다 (그룹 안까지) */
var rows = [];
function walk(c, depth, path) {
    for (var i = 0; i < c.pageItems.length; i++) {
        var it = c.pageItems[i];
        var tn = it.typename;
        if (tn === "GroupItem") { if (depth < 4) walk(it, depth + 1, path + "/그룹"); continue; }
        if (tn !== "RasterItem" && tn !== "PlacedItem") continue;
        var bb;
        try { bb = it.geometricBounds; } catch (e) { continue; }
        var w = bb[2] - bb[0], h = bb[1] - bb[3];
        if (w < 40 || h < 20) continue;                 // 아이콘·장식은 건너뛴다
        var ab = boardOf(bb);
        var lx = ab >= 0 ? bb[0] - ABS[ab].l : bb[0];
        var ly = ab >= 0 ? ABS[ab].t - bb[1] : bb[1];
        rows.push({ ab: ab, x: lx, y: ly, w: w, h: h, tn: tn, path: path, name: it.name || "" });
    }
}
for (var L = 0; L < doc.layers.length; L++) walk(doc.layers[L], 0, doc.layers[L].name);

rows.sort(function (p, q) { return (p.ab - q.ab) || (p.y - q.y) || (p.x - q.x); });

O("■ 래스터·링크이미지 " + rows.length + "개  (아트보드 안 좌표 · 1920x1080 기준)");
O("   보드  종류          자리(x,y)        크기         이름");
for (var k = 0; k < rows.length; k++) {
    var R = rows[k];
    O("   " + (R.ab < 0 ? " -" : ("0" + R.ab).slice(-2))
      + "   " + (R.tn === "RasterItem" ? "래스터    " : "링크이미지")
      + "  (" + ("    " + r0(R.x)).slice(-5) + "," + ("    " + r0(R.y)).slice(-5) + ")"
      + "  " + ("    " + r0(R.w)).slice(-5) + "x" + ("    " + r0(R.h)).slice(-5)
      + "  " + R.name);
}

/* 아트보드마다 작은 png 를 뽑는다 — 어느 보드가 무엇인지 눈으로 확인하려고 */
for (var e = 0; e < doc.artboards.length; e++) {
    doc.artboards.setActiveArtboardIndex(e);
    var eo = new ExportOptionsPNG24();
    eo.artBoardClipping = true;
    eo.horizontalScale = 25; eo.verticalScale = 25;
    doc.exportFile(new File(PATHS.outDir + "/_원본보드_" + ("0" + e).slice(-2) + ".png"), ExportType.PNG24, eo);
}

doc.close(SaveOptions.DONOTSAVECHANGES);

var lf = new File(PATHS.outDir + "/ai_tree.txt");
lf.encoding = "UTF-8"; lf.open("w"); lf.write(out.join(String.fromCharCode(10))); lf.close();
"OK 후보 " + rows.length;
