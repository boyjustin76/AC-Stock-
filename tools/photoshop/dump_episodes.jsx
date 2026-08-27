/**
 * 완성된 회차를 한 장씩 뽑고 레이어 구성을 받아 적는다 — 방식을 뽑아낼 때 쓴다.
 *
 * 새 회차 썸네일을 만들 때 회차 하나만 보고 따라 하면 그 회차를 베낀 것이 된다.
 * 열 회차를 전부 켜 보고 무엇이 같고 무엇이 다른지 갈라야 "규칙" 이 나온다.
 * thumbnail_rule 4·5·19·20·21 이 전부 이 스크립트 결과에서 나왔다.
 *
 * 하는 일
 *   - 회차 그룹(# 으로 시작)을 하나씩만 켜서 outDir/ref/ep00.jpg ... 로 저장 (960x540)
 *   - 각 회차의 레이어 트리를 좌표·텍스트 내용·폰트·자간·색까지 outDir/ref_tree.txt 로
 *
 * 여기서 읽어 낸 것
 *   타이틀은 폭이 아니라 글자 높이가 고정이다 — 윗줄 141px / 아랫줄 194px
 *   좌표도 고정 — 윗줄 x=88 baseline y=198, 아랫줄 x=74 baseline y=395
 *   #1 쿠라마기만 가운데 정렬인 예외다
 */
// @target photoshop

app.displayDialogs = DialogModes.NO;
var _ru = app.preferences.rulerUnits, _tu = app.preferences.typeUnits;
app.preferences.rulerUnits = Units.PIXELS;
app.preferences.typeUnits = TypeUnits.PIXELS;

var HERE = new File($.fileName).parent;
var out = [];
function O(s) { out.push(String(s)); }
function pad(n) { var s = ""; for (var i = 0; i < n; i++) s += "  "; return s; }

function readConfig() {
    var f = new File(HERE.fsName + "/config.json");
    f.encoding = "UTF-8"; f.open("r");
    var t = f.read(); f.close();
    return eval("(" + t + ")");
}
var CFG = readConfig();

var doc = null;
var want = decodeURI(new File(CFG.template).name);
for (var i = 0; i < app.documents.length; i++) if (app.documents[i].name === want) doc = app.documents[i];
if (doc === null) doc = app.open(new File(CFG.template));
app.activeDocument = doc;
doc.activeHistoryState = doc.historyStates[0];

var refDir = new Folder(CFG.outDir + "/ref");
if (!refDir.exists) refDir.create();

var root = doc.layers[0];
var eps = [];
for (var i = 0; i < root.layers.length; i++) {
    var g = root.layers[i];
    if (g.typename === "LayerSet" && g.name.charAt(0) === "#") eps.push(g);
}
O("회차 " + eps.length + "개");

function describe(container, depth) {
    for (var i = 0; i < container.layers.length; i++) {
        var y = container.layers[i];
        var vis = y.visible ? "*" : ".";
        var bs = "";
        try {
            var b = y.bounds;
            bs = "(" + Math.round(b[0].as("px")) + "," + Math.round(b[1].as("px")) + ","
               + Math.round(b[2].as("px")) + "," + Math.round(b[3].as("px")) + ")";
        } catch (e) { bs = "(-)"; }
        if (y.typename === "LayerSet") {
            O(pad(depth) + vis + " [G] " + y.name + " " + bs);
            if (depth < 4) describe(y, depth + 1);
            continue;
        }
        var kind = "?"; try { kind = String(y.kind).replace("LayerKind.", ""); } catch (e) {}
        var ex = "";
        if (kind === "TEXT") {
            try {
                var t = y.textItem;
                ex = " || \"" + String(t.contents).replace(/[\r\n]/g, " / ") + "\""
                   + " | px=" + Math.round(parseFloat(t.size))
                   + " | " + t.font
                   + " | " + String(t.justification).replace("Justification.", "")
                   + " | anchor=" + Math.round(t.position[0].as("px")) + "," + Math.round(t.position[1].as("px"));
                try { ex += " | #" + t.color.rgb.hexValue; } catch (e2) {}
                try { ex += " | track=" + t.tracking; } catch (e3) {}
            } catch (e) { ex = " || 텍스트 읽기 실패 " + e; }
        }
        O(pad(depth) + vis + " " + y.name + " <" + kind + "> " + bs + ex);
    }
}

for (var e = 0; e < eps.length; e++) {
    for (var k = 0; k < eps.length; k++) eps[k].visible = (k === e);   // 하나만 켠다
    O("");
    O("=================================================================");
    O("회차 " + e + "  " + eps[e].name);
    O("=================================================================");
    describe(eps[e], 1);

    var d2 = doc.duplicate();
    d2.flatten();
    d2.resizeImage(UnitValue(960, "px"), UnitValue(540, "px"), 72, ResampleMethod.BICUBICSHARPER);
    var jo = new JPEGSaveOptions(); jo.quality = 8;
    var nn = e < 10 ? "0" + e : "" + e;
    d2.saveAs(new File(CFG.outDir + "/ref/ep" + nn + ".jpg"), jo, true);
    d2.close(SaveOptions.DONOTSAVECHANGES);
    app.activeDocument = doc;
}

doc.activeHistoryState = doc.historyStates[0];       // 템플릿은 건드리지 않은 상태로
app.preferences.rulerUnits = _ru;
app.preferences.typeUnits = _tu;

var f = new File(CFG.outDir + "/ref_tree.txt");
f.encoding = "UTF-8"; f.open("w"); f.write(out.join(String.fromCharCode(10))); f.close();
"OK 회차 " + eps.length + "개 · " + out.length + "줄";
