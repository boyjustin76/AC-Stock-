/**
 * 타이틀 글자를 "문자 단위" 로 읽는다 — 한 줄 안에서 색이 갈리는 곳을 찾아낸다.
 *
 * 왜 따로 필요한가
 *   DOM 의 textItem.color 는 그 줄의 첫 글자 색 하나만 돌려준다.
 *   그래서 dump_episodes.jsx 는 #8 의 윗줄을 통째로 #FF0000 이라고 적어 놨는데,
 *   실제로는 "가짜신호" 만 빨강이고 "는 이제 그만" 은 흰색이다. 덤프가 틀린 것이다.
 *   문자별 서식은 textKey 디스크립터 안 textStyleRange 목록에만 들어 있고,
 *   거기는 ActionManager 로만 닿는다.
 *
 * 읽는 구조
 *   textKey (object)
 *     └ textKey          : 글자 내용 (string)
 *     └ textStyleRange   : LIST — 서식이 같은 구간마다 하나씩
 *          └ from / to    : 문자 인덱스 (to 는 미포함)
 *          └ textStyle    : color{red,grain,blue} · fontPostScriptName · size · tracking
 *   색을 안 적은 구간은 앞 구간 색을 물려받으므로 비어 있을 수 있다 — 그때는 "(상속)".
 *   초록 채널의 키 이름이 "grain" 이다. green 이 아니다. (dump_layer_fx.jsx 와 같은 함정)
 *
 * 결과는 outDir/text_runs.txt.
 */
// @target photoshop

app.displayDialogs = DialogModes.NO;
var _ru = app.preferences.rulerUnits, _tu = app.preferences.typeUnits;
app.preferences.rulerUnits = Units.PIXELS;
app.preferences.typeUnits = TypeUnits.PIXELS;

var HERE = new File($.fileName).parent;
var out = [];
function O(s) { out.push(String(s)); }
function hex2(n) { var s = Math.round(n).toString(16).toUpperCase(); return s.length < 2 ? "0" + s : s; }

function readConfig() {
    var f = new File(HERE.fsName + "/config.json");
    f.encoding = "UTF-8"; f.open("r");
    var t = f.read(); f.close();
    return eval("(" + t + ")");
}
var CFG = readConfig();

/* 기본은 템플릿을 읽는다. config 에 runsTarget 이 있으면 그 .psd 를 읽는다 —
   build_thumb 이 뽑은 결과에 강조가 실제로 박혔는지 확인할 때 쓴다. */
var doc = null, closeAfter = false;
if (CFG.runsTarget) {
    doc = app.open(new File(CFG.runsTarget));
    closeAfter = true;
    O("대상: " + CFG.runsTarget);
} else {
    var want = decodeURI(new File(CFG.template).name);
    for (var i = 0; i < app.documents.length; i++) if (app.documents[i].name === want) doc = app.documents[i];
    if (doc === null) doc = app.open(new File(CFG.template));
    app.activeDocument = doc;
    doc.activeHistoryState = doc.historyStates[0];
    O("대상: 템플릿 " + want);
}

/** textStyle 디스크립터에서 색을 #RRGGBB 로 */
function styleColor(ts) {
    if (!ts.hasKey(stringIDToTypeID("color"))) return null;
    var c = ts.getObjectValue(stringIDToTypeID("color"));
    return "#" + hex2(c.getDouble(stringIDToTypeID("red")))
               + hex2(c.getDouble(stringIDToTypeID("grain")))
               + hex2(c.getDouble(stringIDToTypeID("blue")));
}

/** 텍스트 레이어 하나를 구간별로 뜯는다. 구간이 2개 이상이면 그 줄은 섞인 줄이다. */
function runsOf(layer) {
    doc.activeLayer = layer;
    var r = new ActionReference();
    r.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("textKey"));
    r.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
    var d = executeActionGet(r);
    if (!d.hasKey(stringIDToTypeID("textKey"))) return null;
    var tk = d.getObjectValue(stringIDToTypeID("textKey"));
    var body = tk.hasKey(stringIDToTypeID("textKey")) ? tk.getString(stringIDToTypeID("textKey")) : "";
    if (!tk.hasKey(stringIDToTypeID("textStyleRange"))) return { text: body, runs: [] };

    var lst = tk.getList(stringIDToTypeID("textStyleRange"));
    var runs = [];
    for (var i = 0; i < lst.count; i++) {
        var o = lst.getObjectValue(i);
        var from = o.getInteger(stringIDToTypeID("from"));
        var to   = o.getInteger(stringIDToTypeID("to"));
        var ts   = o.getObjectValue(stringIDToTypeID("textStyle"));
        var rec = { from: from, to: to, text: body.substring(from, to), color: styleColor(ts) };
        if (ts.hasKey(stringIDToTypeID("fontPostScriptName")))
            rec.font = ts.getString(stringIDToTypeID("fontPostScriptName"));
        if (ts.hasKey(stringIDToTypeID("size")))
            rec.size = Math.round(ts.getUnitDoubleValue(stringIDToTypeID("size")) * 100) / 100;
        if (ts.hasKey(stringIDToTypeID("tracking")))
            rec.track = Math.round(ts.getDouble(stringIDToTypeID("tracking")));
        runs.push(rec);
    }
    return { text: body, runs: runs };
}

var mixed = [];   // 색이 갈리는 줄만 따로 모아 맨 뒤에 요약한다

function scan(container, path, epName) {
    for (var i = 0; i < container.layers.length; i++) {
        var y = container.layers[i];
        if (y.typename === "LayerSet") { scan(y, path + "/" + y.name, epName); continue; }
        var kind = "?"; try { kind = String(y.kind).replace("LayerKind.", ""); } catch (e) {}
        if (kind !== "TEXT") continue;

        var info = null;
        try { info = runsOf(y); } catch (e) { O("  " + path + "/" + y.name + "  읽기 실패 " + e); continue; }
        if (info === null) continue;

        var flat = String(info.text).replace(/[\r\n]/g, " / ");
        var colors = [];
        for (var k = 0; k < info.runs.length; k++)
            if (info.runs[k].color !== null) colors.push(info.runs[k].color);
        var uniq = [];
        for (var k = 0; k < colors.length; k++) {
            var dup = false;
            for (var m = 0; m < uniq.length; m++) if (uniq[m] === colors[k]) dup = true;
            if (!dup) uniq.push(colors[k]);
        }
        var tag = uniq.length > 1 ? "  <<< 섞인 줄" : "";
        O("  " + (y.visible ? "*" : ".") + " " + path + "/" + y.name
          + "  \"" + flat + "\"  구간 " + info.runs.length + "개" + tag);
        for (var k = 0; k < info.runs.length; k++) {
            var r2 = info.runs[k];
            O("       [" + r2.from + "," + r2.to + ") \"" + String(r2.text).replace(/[\r\n]/g, " / ") + "\""
              + "  " + (r2.color === null ? "(상속)" : r2.color)
              + (r2.font ? "  " + r2.font : "")
              + (r2.size ? "  " + r2.size + "px" : "")
              + (r2.track === undefined ? "" : "  track=" + r2.track));
        }
        if (uniq.length > 1) mixed.push(epName + "  " + y.name + "  \"" + flat + "\"  " + uniq.join(" + "));
    }
}

var root = doc.layers[0];
var n = 0;
for (var i = 0; i < root.layers.length; i++) {
    var g = root.layers[i];
    if (g.typename !== "LayerSet" || g.name.charAt(0) !== "#") continue;
    O("");
    O("========== " + g.name + " ==========");
    scan(g, "", g.name);
    n++;
}

if (n === 0) { O(""); O("========== 문서 전체 =========="); scan(doc, "", "문서"); }

O("");
O("========== 색이 갈리는 줄 " + mixed.length + "개 ==========");
for (var i = 0; i < mixed.length; i++) O("  " + mixed[i]);

if (closeAfter) doc.close(SaveOptions.DONOTSAVECHANGES);
app.preferences.rulerUnits = _ru;
app.preferences.typeUnits = _tu;
var f = new File(CFG.outDir + "/text_runs.txt");
f.encoding = "UTF-8"; f.open("w"); f.write(out.join(String.fromCharCode(10))); f.close();
"OK 회차 " + n + "개 · 섞인 줄 " + mixed.length + "개";
