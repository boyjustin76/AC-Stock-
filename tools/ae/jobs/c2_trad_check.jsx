/*  C2 — trad.aep 을 다시 열어 판정한다 (b6 와 같은 셋) + 컴포지션마다 0프레임을 PNG 로 찍는다.
    찍은 PNG 는 tools/style/trad.py 합성본과 픽셀로 대조한다 — "AE 에서 잘 열린다" 를 눈이 아니라 수로.
    출력: <작업실>/trad_check/<comp>.png
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c2");
var AEP = LAB + "/pack/trad_ae/trad.aep";
var OUT = LAB + "/trad_check";

function __main() {
say("잡", "C2 trad.aep 재열기 검사 + 프레임 캡처");
closeQuietly();
probe("열기", function () {
    var f = new File(AEP);
    if (!f.exists) throw new Error("없다: " + AEP);
    app.open(f);
    return app.project.numItems + "항목";
});
var miss = [], foot = 0;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (!(it instanceof FootageItem)) continue;
    foot++;
    if (it.footageMissing) miss.push(it.name);
}
say("푸티지", foot + "개 · " + (miss.length ? "**없음 " + miss.length + "개: " + miss.join(", ") + "**" : "전부 연결됨"));
var od = new Folder(OUT); if (!od.exists) od.create();
var comps = [];
for (var j = 1; j <= app.project.numItems; j++) { var c = app.project.item(j); if (c instanceof CompItem) comps.push(c); }
for (var k = 0; k < comps.length; k++) {
    (function (comp, idx) {
        probe("  " + comp.name, function () {
            var f = new File(OUT + "/comp" + idx + ".png");
            if (f.exists) f.remove();
            comp.saveFrameToPng(0, f);
            return comp.numLayers + "레이어 · " + comp.width + "x" + comp.height + " · " + (f.exists ? "png " + f.length + "B" : "**png 안 생김**");
        });
    })(comps[k], k);
}
/* 이름 ↔ 파일 대응표 */
var map = [];
for (var m = 0; m < comps.length; m++) map.push("comp" + m + ".png\t" + comps[m].name);
_write(OUT + "/_map.txt", map.join("\n") + "\n");
flush();
if (miss.length) return fail("푸티지 누락");
return done("컴포지션 " + comps.length + "개 캡처");
}
__main();
