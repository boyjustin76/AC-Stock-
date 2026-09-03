/**
 * 롱폼 썸네일을 템플릿 .psd 에서 직접 만든다 — 포토샵이 있는 PC 전용.
 *
 * 컨테이너(리눅스)에는 포토샵이 없어 psd-tools 로 .psd 를 "쓴다". 그 방식은 포토샵이
 * 파일을 거부하는 문제를 계속 냈다(WORKLOG 의 issue 참고). 포토샵이 있으면 그럴 이유가
 * 없다 — 포토샵더러 직접 편집하게 하면 텍스트·레이어 효과·그룹이 전부 네이티브로 남는다.
 *
 * 하는 일
 *   1. 템플릿에서 회차 그룹 하나를 통째로 복제한다 (기본 베이스 = 인물 없는 #6)
 *   2. 회차 전용 그림(스마트오브젝트·스틸컷·버튼)을 걷어내고 흑백 조정 레이어를 끈다
 *   3. 렌더러가 뽑은 차트 .png 를 종이 배경 위에 얹는다
 *   4. 타이틀 두 줄의 글자만 바꾼다 — 크기·좌표는 건드리지 않는다
 *      config 에 emphasis 가 있으면 그 조각만 빨강으로 빼고 키운다 (#8 방식)
 *   5. 나머지 회차 그룹을 통째로 들어내고 .psd / .png / .jpg 로 저장한다
 *
 * 설정은 같은 폴더의 config.json 에서 읽는다. run.ps1 이 이 파일을 실행한다.
 *
 * 타이틀 크기 — 기본은 고정, 격자박스를 넘을 때만 줄인다 (thumbnail_rule 28).
 *   이 채널 규칙은 "글자 높이 고정, 폭 자유" 다 (thumbnail_rule 4·5).
 *   윗줄 141px / 아랫줄 194px 이 #2~#6 에서 완전히 일치한다 — 그래서 기본은 안 건드린다.
 *   다만 문구가 길어지면 폭이 상자를 넘어 차트를 덮는다 (차12 아랫줄이 1488px 였다).
 *   그때만 config 의 titleBox 폭에 맞춰 두 줄을 같은 배율로 줄인다.
 *   절대 키우지는 않는다 — 짧은 문구는 예전 회차와 같은 크기 그대로 남는다.
 *   폭 하나로 회차마다 크기를 역산하던 옛 컨테이너 방식과는 다르다. 저건 항상 상자를
 *   꽉 채워서 짧은 문구가 거대해졌다. 여기는 상자를 "넘을 때만" 줄이는 상한선이다.
 */
// @target photoshop

app.displayDialogs = DialogModes.NO;
var _ru = app.preferences.rulerUnits, _tu = app.preferences.typeUnits;
app.preferences.rulerUnits = Units.PIXELS;
app.preferences.typeUnits = TypeUnits.PIXELS;

var HERE = new File($.fileName).parent;
var log = [];
function L(s) { log.push(String(s)); }

function readConfig() {
    var f = new File(HERE.fsName + "/config.json");
    if (!f.exists) throw new Error("config.json 이 없습니다: " + f.fsName);
    f.encoding = "UTF-8";          // 한글이 들어 있다. 이걸 빼면 깨진다.
    f.open("r");
    var txt = f.read();
    f.close();
    return eval("(" + txt + ")");  // ExtendScript 에는 JSON 이 없는 판이 있다
}
var CFG = readConfig();

/** 템플릿을 연다. 이미 열려 있으면 그것을 쓴다 (180MB 라 여는 데 시간이 걸린다) */
function openTemplate() {
    var want = new File(CFG.template);
    if (!want.exists) throw new Error("템플릿이 없습니다: " + want.fsName);
    var base = decodeURI(want.name);
    for (var i = 0; i < app.documents.length; i++) {
        if (app.documents[i].name === base) return app.documents[i];
    }
    return app.open(want);
}

/** 템플릿 레이어에는 lspf(잠금)가 걸려 있다. 풀지 않으면 삭제가 오류 8800 으로 막힌다. */
function unlock(container) {
    for (var i = 0; i < container.layers.length; i++) {
        var y = container.layers[i];
        try { y.allLocked = false; } catch (e) {}
        if (y.typename === "ArtLayer") {
            try { y.pixelsLocked = false; } catch (e) {}
            try { y.positionLocked = false; } catch (e) {}
            try { y.transparentPixelsLocked = false; } catch (e) {}
        }
        if (y.typename === "LayerSet") unlock(y);
    }
}

function boxOf(l) {
    var b = l.bounds;
    return "(" + Math.round(b[0].as("px")) + "," + Math.round(b[1].as("px")) + ","
         + Math.round(b[2].as("px")) + "," + Math.round(b[3].as("px")) + ")"
         + " w=" + Math.round(b[2].as("px") - b[0].as("px"))
         + " h=" + Math.round(b[3].as("px") - b[1].as("px"));
}

/* ── 격자박스 (thumbnail_rule 28) ────────────────────────────────────
   타이틀은 좌상단 상자 안에 들어가야 한다. 상자 좌표는 config.titleBox.
   여기 세 함수는 "재고 · 줄이고 · 도로 그 자리에 놓는" 일만 한다.        */

function bnds(l) {
    var b = l.bounds;
    return [b[0].as("px"), b[1].as("px"), b[2].as("px"), b[3].as("px")];
}

/** 레이어의 왼쪽 위가 (x,y) 에 오도록 옮긴다 */
function place(l, x, y) {
    var b = bnds(l);
    l.translate(new UnitValue(x - b[0], "px"), new UnitValue(y - b[1], "px"));
}

/** 한 줄 전체를 k 배로. 베이스라인이 고정이라 글자는 아래를 딛고 줄어든다 */
function scaleLine(l, text, k) {
    paintRuns(l, [{ from: 0, to: String(text).length + 1, scale: k }]);
}

/* ─────────────────────────────────────────────────────────────────────
   문자 단위 강조 — 한 줄 안에서 일부 글자만 색·크기를 바꾼다.

   왜 ActionManager 인가
     DOM 의 textItem.color / .size 는 줄 전체에만 걸린다. 문자별 서식은
     textKey 디스크립터의 textStyleRange 목록에만 있고 거기는 DOM 이 못 닿는다.
     읽기만 하는 쪽은 dump_text_runs.jsx 를 보라.

   열 회차에서 뽑은 규칙 (thumbnail_rule 22·23)
     빨강은 윗줄 맨 앞 단어에만 붙고, 붙을 때는 글자도 같이 커진다.
       #8  "가짜신호" #FF0000 1.174배   #10 "변동성" #FF0000 1.174배
       #7  "가짜 반등" #FF5353 1.087배
     색 없이 크기만 키우는 강조가 더 흔하다 — 숫자·지표 이름에 붙는다.
       #1 "100배" 1.323배   #10 "수익" 1.274배   #9 "단일지표" 1.174배
     조사를 줄여서 명사를 띄우기도 한다 — #4 "부터/까지" 0.826배.

   베이스라인(y=198)이 고정이라 키운 글자는 위로만 자란다. 그래서 규칙 4 의
   "윗줄 141px" 는 안 깨진다 — 기준 구간이 141 이고 강조 구간만 위로 솟는다.

   주의 — 포토샵은 글자 끝에 종결 문자를 하나 더 센다. 마지막 to 는 길이+1 이다.
   ───────────────────────────────────────────────────────────────────── */
function sID(k) { return stringIDToTypeID(k); }

/** 활성 텍스트 레이어의 textKey 디스크립터를 가져온다 */
function getTextKey(layer) {
    doc.activeLayer = layer;
    var r = new ActionReference();
    r.putProperty(sID("property"), sID("textKey"));
    r.putEnumerated(sID("layer"), sID("ordinal"), sID("targetEnum"));
    return executeActionGet(r).getObjectValue(sID("textKey"));
}

/** "#FF0000" -> RGBColor 디스크립터. 초록 채널 키가 grain 이다. green 이 아니다. */
function rgbDesc(hex) {
    var h = String(hex).replace("#", "");
    var c = new ActionDescriptor();
    c.putDouble(sID("red"),   parseInt(h.substring(0, 2), 16));
    c.putDouble(sID("grain"), parseInt(h.substring(2, 4), 16));
    c.putDouble(sID("blue"),  parseInt(h.substring(4, 6), 16));
    return c;
}

/**
 * runs = [{from,to,color?,scale?}] 로 한 줄을 다시 칠한다.
 * 기준 서식(폰트·자간·크기)은 지금 줄의 첫 구간에서 그대로 물려받고
 * color / size 만 덮어쓴다 — 폰트를 다시 지정하면 자간이 날아간다.
 */
function paintRuns(layer, runs) {
    var tk    = getTextKey(layer);
    var lst   = tk.getList(sID("textStyleRange"));
    var proto = lst.getObjectValue(0);
    var pst   = proto.getObjectValue(sID("textStyle"));
    var baseSize = pst.getUnitDoubleValue(sID("size"));
    var sizeUnit = pst.getUnitDoubleType(sID("size"));

    /* 크기를 키울 때 size 만 쓰면 조용히 무시된다.
       이 채널 타이틀은 레이어에 큰 변형(transform xx≈9.63)이 걸려 있어서
       textStyle 이 size(11.95) 와 impliedFontSize(=size×배율, 115.07) 를 같이 들고 있다.
       둘이 어긋나면 포토샵은 impliedFontSize 를 믿고 size 를 되돌려 버린다.
       그래서 둘 다 같은 배율로 써야 한다. leading 은 줄간격이라 건드리지 않는다. */
    var hasImplied = pst.hasKey(sID("impliedFontSize"));
    var baseImplied = hasImplied ? pst.getUnitDoubleValue(sID("impliedFontSize")) : 0;
    var impliedUnit = hasImplied ? pst.getUnitDoubleType(sID("impliedFontSize")) : 0;

    var out = new ActionList();
    for (var i = 0; i < runs.length; i++) {
        var R = runs[i];
        // getObjectValue 는 사본을 준다 — 구간마다 새로 받아야 서로 안 섞인다
        var st = proto.getObjectValue(sID("textStyle"));
        if (R.color) st.putObject(sID("color"), sID("RGBColor"), rgbDesc(R.color));
        if (R.scale && R.scale !== 1) {
            st.putUnitDouble(sID("size"), sizeUnit, baseSize * R.scale);
            if (hasImplied) st.putUnitDouble(sID("impliedFontSize"), impliedUnit, baseImplied * R.scale);
        }
        var rd = new ActionDescriptor();
        rd.putInteger(sID("from"), R.from);
        rd.putInteger(sID("to"), R.to);
        rd.putObject(sID("textStyle"), sID("textStyle"), st);
        out.putObject(sID("textStyleRange"), rd);
    }
    tk.putList(sID("textStyleRange"), out);

    var ref = new ActionReference();
    ref.putEnumerated(sID("textLayer"), sID("ordinal"), sID("targetEnum"));
    var d = new ActionDescriptor();
    d.putReference(sID("null"), ref);
    d.putObject(sID("to"), sID("textLayer"), tk);
    executeAction(sID("set"), d, DialogModes.NO);
    return baseSize;
}

/**
 * config 의 emphasis 항목([{text,color,scale}])을 한 줄에 적용한다.
 * text 는 그 줄 안의 조각으로 찾는다 — 인덱스를 손으로 세면 띄어쓰기에서 틀린다.
 * 강조가 없으면 아무것도 하지 않는다 (기존 동작 그대로).
 */
function applyEmphasis(layer, lineText, specs, label) {
    if (!specs || !specs.length) return;

    var marks = [];
    for (var i = 0; i < specs.length; i++) {
        var E = specs[i];
        // nth 로 같은 글자의 몇 번째를 집을지 고른다 (조사처럼 반복되는 글자용). 기본 1번째.
        var at = -1, nth = E.nth || 1;
        for (var n = 0; n < nth; n++) {
            at = String(lineText).indexOf(E.text, at + 1);
            if (at < 0) break;
        }
        if (at < 0) {
            L("  !! " + label + " 에 \"" + E.text + "\" 의 " + nth + "번째가 없습니다 — 건너뜁니다");
            continue;
        }
        marks.push({ from: at, to: at + E.text.length, color: E.color || null, scale: E.scale || 1 });
    }
    if (!marks.length) return;
    marks.sort(function (a, b) { return a.from - b.from; });

    for (var i = 1; i < marks.length; i++)
        if (marks[i].from < marks[i - 1].to) throw new Error(label + " 의 강조 구간이 겹칩니다");

    // 강조 구간 사이사이를 기준 서식 구간으로 메운다. 마지막은 길이+1 까지.
    var runs = [], cur = 0, end = String(lineText).length + 1;
    for (var i = 0; i < marks.length; i++) {
        if (marks[i].from > cur) runs.push({ from: cur, to: marks[i].from });
        runs.push(marks[i]);
        cur = marks[i].to;
    }
    if (cur < end) runs.push({ from: cur, to: end });

    var baseSize = paintRuns(layer, runs);
    var bits = [];
    for (var i = 0; i < marks.length; i++)
        bits.push("\"" + lineText.substring(marks[i].from, marks[i].to) + "\""
                + (marks[i].color ? " " + marks[i].color : "")
                + (marks[i].scale !== 1 ? " x" + marks[i].scale : ""));
    L("  강조 " + label + " — " + bits.join(" · ") + "  (기준 " + Math.round(baseSize * 100) / 100 + "px)");
}

/** 종이 배경 레이어는 (4, -84) 에 놓여 있다 — 회차가 달라도 같다 */
function isPaper(y) {
    try {
        var b = y.bounds;
        return Math.abs(b[0].as("px") - 4) < 12 && Math.abs(b[1].as("px") + 84) < 12;
    } catch (e) { return false; }
}

var doc = openTemplate();
var outDir = new Folder(CFG.outDir);
if (!outDir.exists) outDir.create();

/** config 의 build 목록에 있는 안만 뽑는다. 목록이 없으면 전부 뽑는다. */
function wanted(id) {
    if (!CFG.build || !CFG.build.length) return true;
    for (var i = 0; i < CFG.build.length; i++) if (CFG.build[i] === id) return true;
    return false;
}

var built = 0;
for (var v = 0; v < CFG.variants.length; v++) {
    var V = CFG.variants[v];
    if (!wanted(V.id)) continue;
    built++;
    L("");
    L("================ " + V.id + " ================");

    app.activeDocument = doc;
    doc.activeHistoryState = doc.historyStates[0];   // 앞 회차의 편집을 되돌린다

    var root = doc.layers[0];                        // 아트보드 그룹
    var base = null;
    for (var i = 0; i < root.layers.length; i++) {
        var g = root.layers[i];
        if (g.typename === "LayerSet" && g.name.indexOf(CFG.base + " ") === 0) base = g;
    }
    if (!base) throw new Error("베이스 회차를 못 찾았습니다: " + CFG.base);
    L("base = " + base.name);

    var dup = base.duplicate();
    dup.name = CFG.group;
    dup.visible = true;
    try { dup.allLocked = false; } catch (e) {}
    unlock(dup);

    // 타이틀 그룹은 "텍스트 레이어 두 개짜리 그룹" 으로 찾는다 (이름에 의존하지 않는다)
    var titleGrp = null, verGrps = [];
    for (var i = 0; i < dup.layers.length; i++) {
        var g2 = dup.layers[i];
        if (g2.typename !== "LayerSet") continue;
        var allText = g2.layers.length === 2;
        for (var j = 0; j < g2.layers.length && allText; j++) {
            if (String(g2.layers[j].kind) !== "LayerKind.TEXT") allText = false;
        }
        if (allText && titleGrp === null) titleGrp = g2; else verGrps.push(g2);
    }
    if (!titleGrp) throw new Error("타이틀 그룹을 못 찾았습니다");

    // 회차 안에 v1·v2 처럼 버전 그룹이 여러 개다. 보이는 것만 남긴다.
    var keep = null;
    for (var i = 0; i < verGrps.length; i++) if (verGrps[i].visible && keep === null) keep = verGrps[i];
    if (keep === null) keep = verGrps[0];
    for (var i = verGrps.length - 1; i >= 0; i--) if (verGrps[i] !== keep) verGrps[i].remove();
    keep.name = "v1";

    // 회차 전용 그림을 걷어낸다. 종이 배경·그림자·단색칠은 남긴다.
    var paper = null;
    for (var i = keep.layers.length - 1; i >= 0; i--) {
        var y = keep.layers[i];
        if (y.typename === "LayerSet") continue;                 // 그림자 그룹
        var kind = String(y.kind).replace("LayerKind.", "");
        // 흑백 조정 레이어(불투명도 83.9%)가 켜져 있으면 우리 차트 색이 전부 죽는다
        if (kind === "BLACKANDWHITE") { y.visible = false; L("흑백 조정 끔"); continue; }
        if (kind === "SOLIDFILL") continue;
        if (paper === null && isPaper(y)) { paper = y; continue; }
        L("제거: " + y.name + " <" + kind + ">");
        y.remove();
    }
    if (!paper) throw new Error("종이 배경 레이어를 못 찾았습니다");

    // 렌더러가 뽑은 차트를 종이 배경 바로 위에 얹는다
    var chartFile = new File(CFG.chartDir + "/" + V.chart);
    if (!chartFile.exists) throw new Error("차트 png 가 없습니다: " + chartFile.fsName);
    var cd = app.open(chartFile);
    var placed = cd.artLayers[0].duplicate(paper, ElementPlacement.PLACEBEFORE);
    cd.close(SaveOptions.DONOTSAVECHANGES);
    app.activeDocument = doc;
    placed.name = "차트";
    var pb = placed.bounds;
    placed.translate(new UnitValue(0 - pb[0].as("px"), "px"), new UnitValue(0 - pb[1].as("px"), "px"));
    L("차트 = " + V.chart);

    // 타이틀 — 노랑(#FFFF00)이 아랫줄, 나머지가 윗줄이다
    var subL = null, mainL = null;
    for (var i = 0; i < titleGrp.layers.length; i++) {
        var t = titleGrp.layers[i].textItem;
        if (String(t.color.rgb.hexValue).toUpperCase() === "FFFF00") mainL = titleGrp.layers[i];
        else subL = titleGrp.layers[i];
    }
    mainL.textItem.contents = V.main; mainL.name = V.main;
    subL.textItem.contents  = V.sub;  subL.name  = V.sub;

    /* ── 격자박스에 넣는다 (thumbnail_rule 28) ──────────────────────
       강조를 걸기 전, 맨 글자 상태에서 잰다. 그래야 A 와 A2 의 배율이 같다.
       두 줄 중 넓은 쪽 하나가 배율을 정하고, 두 줄에 똑같이 걸린다 —
       줄마다 따로 줄이면 윗줄·아랫줄의 크기 비가 회차마다 달라진다.      */
    var BOX = CFG.titleBox || null;
    var k = 1;
    if (BOX) {
        var b0s = bnds(subL), b0m = bnds(mainL);
        var wide = Math.max(b0s[2] - b0s[0], b0m[2] - b0m[0]);
        if (wide > BOX.w) {
            k = Math.round((BOX.w / wide) * 1000) / 1000;
            scaleLine(subL,  V.sub,  k);
            scaleLine(mainL, V.main, k);
            /* 줄어든 글자를 원래 자리에 도로 놓는다. 상자 왼쪽 위를 붙박이로 잡고
               두 줄 사이 간격도 같은 배율로 좁힌다 — 블록째 왼쪽 위로 축소하는 셈.
               이렇게 안 하면 베이스라인이 고정이라 글자가 아래에 남아 흘러내린다. */
            var top0 = Math.min(b0s[1], b0m[1]), left0 = Math.min(b0s[0], b0m[0]);
            place(subL,  left0 + (b0s[0] - left0) * k, top0 + (b0s[1] - top0) * k);
            place(mainL, left0 + (b0m[0] - left0) * k, top0 + (b0m[1] - top0) * k);
            L("  격자박스 — 넓은 줄 " + Math.round(wide) + "px 가 상자 폭 " + BOX.w
              + " 를 넘어 두 줄 다 x" + k + " (" + Math.round((1 - k) * 100) + "% 축소)");
        } else {
            L("  격자박스 — 넓은 줄 " + Math.round(wide) + "px, 상자 안이라 크기 그대로");
        }
    }

    // 문자 단위 강조는 글자를 다 넣은 뒤에 건다 — contents 를 쓰면 서식이 초기화된다
    // 배율은 지금 크기(=격자박스에 맞춘 크기) 기준이다. 그래서 k 를 곱하지 않는다.
    var EMP = V.emphasis || [];
    var empSub = [], empMain = [];
    for (var e = 0; e < EMP.length; e++) ((EMP[e].line === "main") ? empMain : empSub).push(EMP[e]);
    applyEmphasis(subL,  V.sub,  empSub,  "윗줄");
    applyEmphasis(mainL, V.main, empMain, "아랫줄");

    L("아랫줄 " + V.main + "  " + boxOf(mainL));
    L("윗줄  " + V.sub  + "  " + boxOf(subL));
    // 상자를 넘으면 알려 준다. 8px 는 획(6px)+그림자가 글자 밖으로 번지는 몫이다.
    if (BOX) {
        var R = BOX.x + BOX.w, B = BOX.y + BOX.h;
        if (bnds(mainL)[2] > R + 8) L("  !! 아랫줄이 상자 오른쪽(" + R + ")을 넘습니다");
        if (bnds(subL)[2]  > R + 8) L("  !! 윗줄이 상자 오른쪽(" + R + ")을 넘습니다");
        if (bnds(mainL)[3] > B + 8) L("  !! 타이틀이 상자 아래(" + B + ")를 넘습니다");
        // 위쪽은 상자로 안 잰다 — 강조한 글자는 베이스라인이 고정이라 원래 위로 솟는다
        // (규칙 4). 진짜 한계는 틀 안쪽 26px 다 (규칙 27).
        if (bnds(subL)[1] < 34) L("  !! 윗줄이 틀 안전선(26)에 닿습니다 — 강조 배율을 낮추세요");
    }

    // 다른 회차 그룹은 통째로 들어낸다 (템플릿 180MB → 회차 하나 11MB)
    for (var i = root.layers.length - 1; i >= 0; i--) {
        var g3 = root.layers[i];
        if (g3.typename === "LayerSet" && g3.name.charAt(0) === "#" && g3 !== dup) {
            try { g3.allLocked = false; } catch (e) {}
            unlock(g3);
            g3.remove();
        }
    }

    var so = new PhotoshopSaveOptions(); so.layers = true; so.embedColorProfile = true;
    doc.saveAs(new File(CFG.outDir + "/" + V.id + ".psd"), so, true);   // true = 사본으로 저장

    var flat = doc.duplicate();
    flat.flatten();
    var po = new PNGSaveOptions(); po.compression = 6; po.interlaced = false;
    flat.saveAs(new File(CFG.outDir + "/" + V.id + ".png"), po, true);
    var jo = new JPEGSaveOptions(); jo.quality = 9;
    flat.saveAs(new File(CFG.outDir + "/" + V.id + ".jpg"), jo, true);
    flat.close(SaveOptions.DONOTSAVECHANGES);
    app.activeDocument = doc;
    L("저장 " + V.id);
}

doc.activeHistoryState = doc.historyStates[0];       // 템플릿은 손대지 않은 상태로 되돌린다
app.preferences.rulerUnits = _ru;
app.preferences.typeUnits = _tu;

var lf = new File(CFG.outDir + "/build_log.txt");
lf.encoding = "UTF-8"; lf.open("w"); lf.write(log.join(String.fromCharCode(10))); lf.close();
"OK " + built + "안";
