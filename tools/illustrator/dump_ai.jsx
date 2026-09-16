/**
 * 원본 .ai 의 구조를 읽어 적는다 — 아트보드 · 레이어 · 항목 종류 · 글꼴 · 색.
 * 읽기만 한다. 저장하지 않고, 원본은 끝나면 닫는다.
 *
 * 왜 필요한가: '차트명가 NEW 라이브화면구성.ai' 는 트레이딩팩토리 2026v 의
 * 구성·양식을 따라가야 한다. 눈으로 본 그림만으로는 자리(좌표)를 알 수 없다.
 */
// @target illustrator

var HERE = new File($.fileName).parent;

function readConfig() {
    var f = new File(HERE.fsName + "/config.json");
    if (!f.exists) throw new Error("config.json 이 없습니다: " + f.fsName);
    f.encoding = "UTF-8";
    f.open("r");
    var t = f.read();
    f.close();
    return eval("(" + t + ")");
}
var CFG = readConfig();

var out = [];
function O(s) { out.push(String(s)); }
function r2(n) { return Math.round(n * 10) / 10; }

/* 경로는 run.ps1 이 _paths.json 으로 넘겨 준다 (환경변수는 못 쓴다 — _lib.jsx 참고) */
$.evalFile(new File(HERE.fsName + "/_lib.jsx"));
var PATHS = readPaths(HERE);
var LAB = PATHS.liveframeDir, OUT = PATHS.outDir;

var src = new File(LAB + "/" + CFG.refAi);
if (!src.exists) throw new Error("원본 .ai 가 없습니다: " + src.fsName);

O("원본: " + src.fsName);
O("크기: " + Math.round(src.length / 1e6 * 10) / 10 + "MB");
O("");

var doc = app.open(src);
O("문서: " + doc.name);
O("색 모드: " + doc.documentColorSpace);
O("단위 폭x높이: " + r2(doc.width) + " x " + r2(doc.height) + " pt");
O("");

/* ── 아트보드 ─────────────────────────────────────── */
O("■ 아트보드 " + doc.artboards.length + "개");
for (var a = 0; a < doc.artboards.length; a++) {
    var ab = doc.artboards[a];
    var r = ab.artboardRect;   // [left, top, right, bottom]
    O("  [" + a + "] " + ab.name
      + "  " + r2(r[2] - r[0]) + " x " + r2(r[1] - r[3])
      + "  (left " + r2(r[0]) + ", top " + r2(r[1]) + ")");
}
O("");

/* ── 레이어 ───────────────────────────────────────── */
function kindOf(it) {
    var t = it.typename;
    if (t === "PathItem")        return "패스";
    if (t === "CompoundPathItem")return "복합패스";
    if (t === "TextFrame")       return "글자";
    if (t === "PlacedItem")      return "링크이미지";
    if (t === "RasterItem")      return "래스터";
    if (t === "SymbolItem")      return "심볼";
    if (t === "GroupItem")       return "그룹";
    if (t === "MeshItem")        return "메시";
    if (t === "PluginItem")      return "플러그인";
    return t;
}

function boxOf(it) {
    try {
        var b = it.geometricBounds;   // [left, top, right, bottom]
        return "(" + Math.round(b[0]) + "," + Math.round(b[1]) + ")  "
             + Math.round(b[2] - b[0]) + "x" + Math.round(b[1] - b[3]);
    } catch (e) { return "-"; }
}

var fonts = {}, texts = [];

function walk(container, depth, path) {
    var pad = "";
    for (var p = 0; p < depth; p++) pad += "  ";

    var items = container.pageItems;
    var counts = {}, n = 0;
    for (var i = 0; i < items.length; i++) {
        var k = kindOf(items[i]);
        counts[k] = (counts[k] || 0) + 1;
        n++;
    }
    var bits = [];
    for (var k2 in counts) bits.push(k2 + " " + counts[k2]);
    O(pad + "└ 항목 " + n + (bits.length ? "  [" + bits.join(" · ") + "]" : ""));

    /* 글자는 내용까지 적는다 — 어떤 문구가 어디 있는지가 구성의 핵심이다 */
    for (var t = 0; t < container.textFrames.length; t++) {
        var tf = container.textFrames[t];
        var c = String(tf.contents).replace(/[\r\n]+/g, " / ");
        if (c.length > 60) c = c.substring(0, 60) + "…";
        var fn = "?", fs = "?";
        try { fn = tf.textRange.characterAttributes.textFont.name; } catch (e) {}
        try { fs = r2(tf.textRange.characterAttributes.size); } catch (e) {}
        fonts[fn] = (fonts[fn] || 0) + 1;
        texts.push(pad + "    \"" + c + "\"  " + fn + " " + fs + "pt  " + boxOf(tf));
    }

    /* 그룹은 한 겹만 더 들어간다 — 다 펼치면 수천 줄이 된다 */
    if (depth < 2) {
        for (var g = 0; g < container.groupItems.length && g < 40; g++) {
            var grp = container.groupItems[g];
            O(pad + "  · 그룹 " + (grp.name || "(이름없음)") + "  " + boxOf(grp));
            walk(grp, depth + 1, path);
        }
    }
}

O("■ 레이어 " + doc.layers.length + "개  (위가 앞)");
for (var L = 0; L < doc.layers.length; L++) {
    var ly = doc.layers[L];
    O("");
    O("[" + L + "] " + ly.name
      + (ly.visible ? "" : "  (숨김)")
      + (ly.locked ? "  (잠김)" : "")
      + "  불투명 " + r2(ly.opacity) + "%");
    walk(ly, 1, ly.name);
    for (var s = 0; s < ly.layers.length; s++) {
        var sub = ly.layers[s];
        O("  ▸ 하위 레이어: " + sub.name + (sub.visible ? "" : " (숨김)"));
        walk(sub, 2, ly.name + "/" + sub.name);
    }
}

O("");
O("■ 글자 전부");
for (var x = 0; x < texts.length; x++) O(texts[x]);

O("");
O("■ 쓰인 글꼴");
for (var f2 in fonts) O("  " + f2 + "  (" + fonts[f2] + "곳)");

O("");
O("■ 스와치 " + doc.swatches.length + "개");
for (var sw = 0; sw < doc.swatches.length && sw < 60; sw++) {
    var S = doc.swatches[sw], desc = S.name;
    try {
        var col = S.color;
        if (col.typename === "RGBColor")
            desc += "  RGB(" + Math.round(col.red) + "," + Math.round(col.green) + "," + Math.round(col.blue) + ")";
        else if (col.typename === "CMYKColor")
            desc += "  CMYK(" + Math.round(col.cyan) + "," + Math.round(col.magenta) + "," + Math.round(col.yellow) + "," + Math.round(col.black) + ")";
        else desc += "  " + col.typename;
    } catch (e) {}
    O("  " + desc);
}

var nLayers = doc.layers.length;
doc.close(SaveOptions.DONOTSAVECHANGES);   // 원본은 절대 건드리지 않는다

var lf = new File(OUT + "/ai_tree.txt");
lf.encoding = "UTF-8";
lf.open("w");
lf.write(out.join(String.fromCharCode(10)));
lf.close();

"OK 레이어 " + nLayers + " · 글자 " + texts.length;
