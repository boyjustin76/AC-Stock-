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
 *   5. 나머지 회차 그룹을 통째로 들어내고 .psd / .png / .jpg 로 저장한다
 *
 * 설정은 같은 폴더의 config.json 에서 읽는다. run.ps1 이 이 파일을 실행한다.
 *
 * 주의 — 타이틀 크기는 절대 자동으로 맞추지 마라.
 *   이 채널 규칙은 "글자 높이 고정, 폭 자유" 다 (thumbnail_rule 4·5).
 *   윗줄 141px / 아랫줄 194px 이 #2~#6 에서 완전히 일치한다.
 *   폭에 맞춰 크기를 역산하면 회차마다 글자 크기가 들쭉날쭉해진다.
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

for (var v = 0; v < CFG.variants.length; v++) {
    var V = CFG.variants[v];
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
    L("아랫줄 " + V.main + "  " + boxOf(mainL));
    L("윗줄  " + V.sub  + "  " + boxOf(subL));
    // 관측 최대폭을 넘으면 알려만 준다 (자동으로 줄이지 않는다 — 크기가 고정 규격이다)
    if (mainL.bounds[2].as("px") > 1600) L("  !! 아랫줄이 관측 최대폭(1583)을 넘습니다");
    if (subL.bounds[2].as("px")  > 1330) L("  !! 윗줄이 관측 최대폭(1306)을 넘습니다");

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
"OK " + CFG.variants.length + "안";
