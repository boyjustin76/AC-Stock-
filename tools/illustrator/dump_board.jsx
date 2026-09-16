/**
 * 아트보드 하나를 항목 단위로 떠서 적는다 — 두 파일을 비교하려고 만든 것.
 *
 * 사용자가 손으로 고친 판과 내가 지은 판의 같은 아트보드를 각각 떠서 diff 하면
 * 무엇이 바뀌었는지 눈이 아니라 값으로 알 수 있다.
 *
 * config.json 의 dumpTargets 에 {file, board, out} 을 배열로 준다.
 * 읽기만 한다. 저장하지 않고 닫는다.
 */
// @target illustrator

var HERE = new File($.fileName).parent;
$.evalFile(new File(HERE.fsName + "/_lib.jsx"));
var CFG = readConfig(HERE);
var PATHS = readPaths(HERE);
var OUT = PATHS.outDir;

function r1(n) { return Math.round(n * 10) / 10; }

function hex(c) {
    try {
        if (c.typename === "RGBColor")
            return "#" + ("0" + Math.round(c.red).toString(16)).slice(-2)
                       + ("0" + Math.round(c.green).toString(16)).slice(-2)
                       + ("0" + Math.round(c.blue).toString(16)).slice(-2);
        if (c.typename === "GrayColor") return "gray" + Math.round(c.gray);
        if (c.typename === "NoColor")   return "없음";
        return c.typename;
    } catch (e) { return "?"; }
}

var targets = CFG.dumpTargets || [];
var done = 0;

for (var t = 0; t < targets.length; t++) {
    var T = targets[t];
    var f = new File(OUT + "/" + T.file);
    if (!f.exists) { continue; }

    var doc = app.open(f);
    var out = [];
    function O(s) { out.push(String(s)); }

    O("파일: " + decodeURI(doc.name));
    O("아트보드: " + T.board);

    /* 대상 아트보드 상자 */
    var A = null;
    for (var i = 0; i < doc.artboards.length; i++) {
        if (doc.artboards[i].name === T.board) {
            var r = doc.artboards[i].artboardRect;
            A = { l: r[0], t: r[1], r: r[2], b: r[3] };
            break;
        }
    }
    if (!A) { O("!! 그 이름의 아트보드가 없다"); }

    var rows = [];
    function inBoard(bb) {
        if (!A) return true;
        var cx = (bb[0] + bb[2]) / 2, cy = (bb[1] + bb[3]) / 2;
        return cx >= A.l - 1 && cx <= A.r + 1 && cy <= A.t + 1 && cy >= A.b - 1;
    }

    function walk(c, depth, path) {
        for (var i = 0; i < c.pageItems.length; i++) {
            var it = c.pageItems[i];
            var bb;
            try { bb = it.geometricBounds; } catch (e) { continue; }
            if (it.typename === "GroupItem") {
                if (depth < 5) walk(it, depth + 1, path + "/그룹");
                continue;
            }
            if (!inBoard(bb)) continue;

            /* 아트보드 안 좌표로 환산 — 아트보드가 어디 놓였든 같은 값이 나오게 */
            var x = A ? bb[0] - A.l : bb[0];
            var y = A ? A.t - bb[1] : -bb[1];
            var w = bb[2] - bb[0], h = bb[1] - bb[3];

            var kind = it.typename, extra = "";
            if (kind === "TextFrame") {
                var s = String(it.contents).replace(/[\r\n]+/g, "/");
                var fn = "?", fs = "?";
                try { fn = it.textRange.characterAttributes.textFont.name; } catch (e) {}
                try { fs = r1(it.textRange.characterAttributes.size); } catch (e) {}
                var fc = "?";
                try { fc = hex(it.textRange.characterAttributes.fillColor); } catch (e) {}
                extra = '"' + s + '"  ' + fn + " " + fs + "pt " + fc;
            } else if (kind === "PathItem") {
                extra = (it.filled ? "채움 " + hex(it.fillColor) : "채움없음")
                      + " · " + (it.stroked ? "선 " + hex(it.strokeColor) + " " + r1(it.strokeWidth) + "pt" : "선없음");
            } else if (kind === "RasterItem" || kind === "PlacedItem") {
                var nm = "";
                try { nm = decodeURI(it.file.name); } catch (e) { nm = "(임베드)"; }
                extra = nm;
            }
            var op = "";
            try { if (it.opacity < 99.5) op = " 불투명" + r1(it.opacity) + "%"; } catch (e) {}
            rows.push({ y: y, x: x, s: "(" + Math.round(x) + "," + Math.round(y) + ") "
                      + Math.round(w) + "x" + Math.round(h) + "  " + kind + op + "  " + extra
                      + "   [" + path + "]" });
        }
    }
    for (var L = 0; L < doc.layers.length; L++) walk(doc.layers[L], 0, doc.layers[L].name);

    rows.sort(function (p, q) { return (p.y - q.y) || (p.x - q.x); });
    O("항목 " + rows.length + "개  (위에서 아래 순)");
    for (var k = 0; k < rows.length; k++) O("  " + rows[k].s);

    doc.close(SaveOptions.DONOTSAVECHANGES);

    var lf = new File(OUT + "/" + T.out);
    lf.encoding = "UTF-8"; lf.open("w"); lf.write(out.join(String.fromCharCode(10))); lf.close();
    done++;
}

"OK " + done + "개";
