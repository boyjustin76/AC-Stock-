/**
 * OBS 에 올릴 8000x4500 png 를 뽑는다.
 *
 * 왜 8000 인가 — 트팩 원본이 그렇다. 원본 .ai 는 1920x1080 pt 이고, OBS 용 png 는 그걸
 * 417% 로 내보낸 것이다 (8000/1920 = 4.16667). 방송 캔버스는 1080p 라 OBS 가 다시 줄인다.
 * 크게 뽑아 두면 OBS 안에서 소스를 확대·이동해도 안 뭉갠다.
 *
 * 뽑는 것은 **OBS 가 실제로 쓰는 세 장**이다 (레이어 순서.txt 기준).
 *   01_고정_배경_레이어   #7 맨 아래 (전부 불투명)
 *   02_오프닝_프레임       오프닝 폴더 #1
 *   03_메인_방송프레임     라이브 폴더 #1
 * 04~06(가이드·최종출력샘플)은 사람이 보는 설명도라 100% 로 따로 둔다.
 *
 * build_live.jsx 가 만든 .ai 를 열어서 내보내기만 한다 — 다시 짓지 않는다.
 */
// @target illustrator

var HERE = new File($.fileName).parent;
$.evalFile(new File(HERE.fsName + "/_lib.jsx"));
var CFG = readConfig(HERE);
var PATHS = readPaths(HERE);
var OUT = PATHS.outDir;

var log = [];
function L(s) { log.push(String(s)); }

var SCALE = CFG.obsScale || 416.667;     // 1920 -> 8000
var WANT = CFG.obsBoards || ["01_고정_배경_레이어", "02_오프닝_프레임", "03_메인_방송프레임"];

var src = new File(OUT + "/" + CFG.outAi);
if (!src.exists) throw new Error(".ai 가 없습니다. 먼저 build_live 를 돌리세요: " + src.fsName);

var doc = app.open(src);
L("연 파일: " + decodeURI(doc.name));
L("배율: " + SCALE + "%  (1920 x 1080 -> " + Math.round(1920 * SCALE / 100) + " x " + Math.round(1080 * SCALE / 100) + ")");
L("");

var outDir = new Folder(OUT + "/OBS");
if (!outDir.exists) outDir.create();

function wanted(name) {
    for (var i = 0; i < WANT.length; i++) if (WANT[i] === name) return true;
    return false;
}

var n = 0;
for (var a = 0; a < doc.artboards.length; a++) {
    var nm = doc.artboards[a].name;
    if (!wanted(nm)) continue;
    doc.artboards.setActiveArtboardIndex(a);

    var eo = new ExportOptionsPNG24();
    eo.artBoardClipping = true;
    eo.transparency = true;                 // 틀은 가운데가 뚫려 있어야 한다
    eo.antiAliasing = true;
    eo.horizontalScale = SCALE;
    eo.verticalScale = SCALE;

    var f = new File(outDir.fsName + "/" + nm + ".png");
    doc.exportFile(f, ExportType.PNG24, eo);
    n++;
    L("  " + nm + ".png");
}

doc.close(SaveOptions.DONOTSAVECHANGES);    // 내보내기만 했다. 문서는 그대로 둔다

L("");
L("자리: " + outDir.fsName);
var lf = new File(OUT + "/build_log.txt");
lf.encoding = "UTF-8"; lf.open("w"); lf.write(log.join(String.fromCharCode(10))); lf.close();

"OK " + n + "장";
