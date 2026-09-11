/*  C1 — 신규안 v2 "병풍 위의 차트" 레이어 PNG 를 AE 컴포지션으로 모은다.

    입력:  C:/aelab/pack/trad_ae/footage/manifest.jsx   (tools/style/trad.py --split 이 쓴 목록)
           C:/aelab/pack/trad_ae/footage/<comp>/<NN_slug>.png
    출력:  C:/aelab/pack/trad_ae/trad.aep   — footage/ 와 나란히 (포터블, pack.mjs 와 같은 구조)

    층 하나 = PNG 하나. 목록의 (x,y,w,h) 가 알파 상자라 AE 위치는 그 중심이다.
    차트 바닥은 흰 바탕 PNG 라 블렌딩 모드 Multiply — 합성기(trad.py)가 한지에 곱하기로 얹은 것과 같다.
    PNG 알파는 스트레이트(PIL) — AE 가 프리멀티로 짐작하면 가장자리가 어두워지니 명시한다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c1");

var PACK = LAB + "/pack/trad_ae";
var FOOT = PACK + "/footage";
var AEP  = PACK + "/trad.aep";
var SUB  = { "\uc804\ud1b5_\ucd1d\uc9d1\ud569": "sources", "\uc804\ud1b5_\ud2c0": "frame", "\uc804\ud1b5_\ub85c\uace0": "logo", "\uc804\ud1b5_\uc544\uc6c3\ud2b8\ub85c": "outro" };

$.evalFile(new File(FOOT + "/manifest.jsx"));   /* MANIFEST */

function __main() {

say("잡", "C1 전통 레이어 컴포지션");
say("AE", app.version);
probe("목록", function () {
    if (typeof MANIFEST === "undefined") throw new Error("manifest.jsx 를 못 읽었다");
    return MANIFEST.comps.length + "컴포지션";
});

closeQuietly();
app.newProject();
probe("색 설정", function () {
    app.project.linearBlending = false;
    app.project.workingSpace = "";
    return "선형=" + app.project.linearBlending + " 공간='" + app.project.workingSpace + "'";
});

var totalLayers = 0, missing = [];
for (var c = 0; c < MANIFEST.comps.length; c++) {
    var M = MANIFEST.comps[c];
    var sub = SUB[M.comp] || ("c" + c);
    (function (M, sub) {
        probe("컴포지션 " + M.comp, function () {
            var comp = app.project.items.addComp(M.comp, M.w, M.h, 1, M.dur, M.fps);
            var folder = app.project.items.addFolder(M.comp + " footage");
            /* 목록은 아래→위 순서. layers.add 는 맨 위에 얹으므로 그대로 돌리면 화면 순서가 된다 */
            for (var i = 0; i < M.layers.length; i++) {
                var L = M.layers[i];
                var f = new File(FOOT + "/" + sub + "/" + L.file);
                if (!f.exists) { missing.push(sub + "/" + L.file); continue; }
                var item = app.project.importFile(new ImportOptions(f));
                item.name = L.name;
                item.parentFolder = folder;
                try { item.mainSource.alphaMode = AlphaMode.STRAIGHT; } catch (e) {}
                var lay = comp.layers.add(item);
                lay.name = L.name;
                lay.property("Position").setValue([L.x + L.w / 2, L.y + L.h / 2]);
                if (L.blend === "multiply") lay.blendingMode = BlendingMode.MULTIPLY;
                totalLayers++;
            }
            return comp.numLayers + "레이어";
        });
    })(M, sub);
}
say("층", totalLayers + "개" + (missing.length ? " · **빠진 파일 " + missing.length + "개: " + missing.join(", ") + "**" : ""));

probe("기존 aep 삭제", function () {
    var f = new File(AEP);
    if (!f.exists) return "없었다";
    return f.remove() ? "지웠다" : "못 지웠다";
});
probe("저장", function () { app.project.save(new File(AEP)); return AEP; });
probe("파일 확인", function () { var f = new File(AEP); return f.exists ? f.length + " bytes" : "파일이 없다"; });

flush();
if (missing.length) return fail("빠진 PNG 가 있다");
return done("컴포지션 " + MANIFEST.comps.length + "개 · 층 " + totalLayers + "개 저장");
}
__main();
