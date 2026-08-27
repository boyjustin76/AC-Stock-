/**
 * 레이어 효과(lfx2)를 값으로 읽어 낸다 — ActionManager 로 직접 뜯는다.
 *
 * DOM(ArtLayer) 에는 레이어 효과를 읽는 길이 없다. layerEffects 속성을
 * executeActionGet 으로 가져와야 값이 나온다.
 *
 * 이걸로 #6·#7 의 "매수 버튼(좌우)" 를 읽어서 나온 것:
 *   outerGlow  ON  검정 rgb(0,0,0) · 표준 · 불투명도 18% · 스프레드 72 · 크기 10 · 노이즈 22
 *   dropShadow / innerShadow / gradientFill / frameFX(획)  — 전부 off
 * 즉 이 채널 버튼에 걸린 효과는 외부 광선 하나뿐이다.
 *
 * config.json 의 targets 에 적은 이름이 들어간 레이어만 훑는다.
 * 결과는 outDir/layer_fx.txt.
 */
// @target photoshop

app.displayDialogs = DialogModes.NO;
var _ru = app.preferences.rulerUnits, _tu = app.preferences.typeUnits;
app.preferences.rulerUnits = Units.PIXELS;
app.preferences.typeUnits = TypeUnits.PIXELS;

var HERE = new File($.fileName).parent;
var out = [];
function O(s) { out.push(String(s)); }

function readConfig() {
    var f = new File(HERE.fsName + "/config.json");
    f.encoding = "UTF-8"; f.open("r");
    var t = f.read(); f.close();
    return eval("(" + t + ")");
}
var CFG = readConfig();
var TARGETS = CFG.fxTargets || ["매수", "매도", "익절", "손절"];
var GROUPS  = CFG.fxGroups  || ["#6", "#7"];

var doc = null;
var want = decodeURI(new File(CFG.template).name);
for (var i = 0; i < app.documents.length; i++) if (app.documents[i].name === want) doc = app.documents[i];
if (doc === null) doc = app.open(new File(CFG.template));
app.activeDocument = doc;
doc.activeHistoryState = doc.historyStates[0];

/** 효과 하나(디스크립터)를 사람이 읽을 문자열로 */
function dumpFxObj(o) {
    var bits = [];
    function U(k, lbl) {
        if (o.hasKey(stringIDToTypeID(k)))
            bits.push(lbl + "=" + Math.round(o.getUnitDoubleValue(stringIDToTypeID(k)) * 10) / 10);
    }
    if (o.hasKey(stringIDToTypeID("enabled")))
        bits.push(o.getBoolean(stringIDToTypeID("enabled")) ? "ON" : "off");
    if (o.hasKey(stringIDToTypeID("present")))
        bits.push("present=" + o.getBoolean(stringIDToTypeID("present")));
    if (o.hasKey(stringIDToTypeID("mode")))
        bits.push("blend=" + typeIDToStringID(o.getEnumerationValue(stringIDToTypeID("mode"))));
    if (o.hasKey(stringIDToTypeID("style")))
        bits.push("pos=" + typeIDToStringID(o.getEnumerationValue(stringIDToTypeID("style"))));
    U("opacity", "op"); U("size", "size"); U("distance", "dist"); U("chokeMatte", "spread");
    U("localLightingAngle", "angle"); U("blur", "blur"); U("noise", "noise");
    if (o.hasKey(stringIDToTypeID("useGlobalAngle")))
        bits.push("global=" + o.getBoolean(stringIDToTypeID("useGlobalAngle")));
    if (o.hasKey(stringIDToTypeID("color"))) {
        var c = o.getObjectValue(stringIDToTypeID("color"));
        // 초록 채널의 키가 "grain" 이다. green 이 아니다.
        try {
            bits.push("color=rgb(" + Math.round(c.getDouble(stringIDToTypeID("red"))) + ","
                + Math.round(c.getDouble(stringIDToTypeID("grain"))) + ","
                + Math.round(c.getDouble(stringIDToTypeID("blue"))) + ")");
        } catch (e) { bits.push("color=?"); }
    }
    return bits.join(" ");
}

function fxOf(layer) {
    try {
        doc.activeLayer = layer;
        var r = new ActionReference();
        r.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("layerEffects"));
        r.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var d = executeActionGet(r);
        if (!d.hasKey(stringIDToTypeID("layerEffects"))) return " 없음";
        var fx = d.getObjectValue(stringIDToTypeID("layerEffects"));
        var lines = [];
        for (var k = 0; k < fx.count; k++) {
            var key = fx.getKey(k), sid = typeIDToStringID(key), t = fx.getType(key);
            if (t == DescValueType.LISTTYPE) {
                var lst = fx.getList(key);
                for (var m = 0; m < lst.count; m++)
                    lines.push("      - " + sid + "[" + m + "] " + dumpFxObj(lst.getObjectValue(m)));
            } else if (t == DescValueType.OBJECTTYPE) {
                lines.push("      - " + sid + " " + dumpFxObj(fx.getObjectValue(key)));
            } else if (t == DescValueType.BOOLEANTYPE) {
                lines.push("      - " + sid + " = " + fx.getBoolean(key));
            } else if (t == DescValueType.UNITDOUBLE) {
                lines.push("      - " + sid + " = " + fx.getUnitDoubleValue(key));
            }
        }
        return String.fromCharCode(10) + lines.join(String.fromCharCode(10));
    } catch (e) { return " 읽기 실패 " + e; }
}

function scan(c, path) {
    for (var i = 0; i < c.layers.length; i++) {
        var y = c.layers[i];
        if (y.typename === "LayerSet") { scan(y, path + "/" + y.name); continue; }
        var hit = false;
        for (var k = 0; k < TARGETS.length; k++) if (y.name.indexOf(TARGETS[k]) >= 0) hit = true;
        if (!hit) continue;
        var kind = "?"; try { kind = String(y.kind).replace("LayerKind.", ""); } catch (e) {}
        var b = y.bounds;
        O("  " + path + "/" + y.name + "  <" + kind + "> "
          + Math.round(b[2].as("px") - b[0].as("px")) + "x" + Math.round(b[3].as("px") - b[1].as("px"))
          + "  op=" + Math.round(y.opacity) + " " + (y.visible ? "보임" : "숨김"));
        if (kind === "TEXT") {
            var t = y.textItem;
            O("      글씨 \"" + t.contents + "\"  " + t.font + "  " + Math.round(parseFloat(t.size)) + "px"
              + "  #" + t.color.rgb.hexValue);
        }
        O("      fx:" + fxOf(y));
    }
}

var root = doc.layers[0];
for (var i = 0; i < root.layers.length; i++) {
    var g = root.layers[i];
    if (g.typename !== "LayerSet") continue;
    for (var k = 0; k < GROUPS.length; k++) {
        if (g.name.indexOf(GROUPS[k] + " ") === 0 || g.name === GROUPS[k]) {
            O("========== " + g.name + " ==========");
            scan(g, "");
        }
    }
}

app.preferences.rulerUnits = _ru;
app.preferences.typeUnits = _tu;
var f = new File(CFG.outDir + "/layer_fx.txt");
f.encoding = "UTF-8"; f.open("w"); f.write(out.join(String.fromCharCode(10))); f.close();
"OK " + out.length + "줄";
