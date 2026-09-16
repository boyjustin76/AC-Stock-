/*  C11 — 작업실을 옮긴 뒤 .aep 들이 푸티지를 스스로 찾는지 확인한다. **저장하지 않는다.**

    2026-09-16: 작업물을 한 폴더로 모으면서 작업실이 C:/aelab 에서
    <통합 폴더>/02_AE작업실_aelab 으로 옮겨졌고 옛 경로는 없앴다.
    .aep 안에는 옛 절대경로가 박혀 있지만 footage/ 가 .aep 옆에 함께 따라왔으므로
    AE 가 상대경로로 다시 찾아줄 것으로 본다 — 그 가정을 여기서 실측한다.

    통과 기준: 팩 5개 전부 footageMissing = 0.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c11");

var PACKS = [
    "pack/ch11-4_ae/sl-11-4.aep",
    "pack/ch11-5_ae/sl-11-5.aep",
    "pack/trad_ae/trad.aep",
    "pack/trad_motion/trad_motion.aep",
    "pack/trad_rr/trad_rr.aep"
];

function checkOne(rel) {
    var path = LAB + "/" + rel;
    var f = new File(path);
    if (!f.exists) return "파일 없음: " + path;

    closeQuietly();
    app.open(f);

    var total = 0, missing = 0, names = [];
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it instanceof FootageItem && it.file) {
            total++;
            if (it.footageMissing) {
                missing++;
                if (names.length < 4) names.push(it.name);
            }
        }
    }
    var dirty = app.project.dirty;
    closeQuietly();
    if (missing > 0) MISSING_TOTAL += missing;
    return (missing ? "못찾음 " : "정상 ") + "· 푸티지 " + total + "개 · 못 찾음 " + missing +
           (missing ? " (" + names.join(", ") + ")" : "") + " · dirty=" + dirty;
}

say("잡", "C11 작업실 이전 뒤 푸티지 재연결 확인 (저장 안 함)");
say("작업실", LAB);

var MISSING_TOTAL = 0;
app.beginSuppressDialogs();
for (var k = 0; k < PACKS.length; k++) {
    probe(PACKS[k], (function (rel) {
        return function () { return checkOne(rel); };
    })(PACKS[k]));
}
app.endSuppressDialogs(false);

closeQuietly();
flush();
if (MISSING_TOTAL > 0) { fail("못 찾은 푸티지 " + MISSING_TOTAL + "개"); }
else { done("팩 5개 모두 푸티지 정상 — 작업실을 옮겨도 열린다"); }
