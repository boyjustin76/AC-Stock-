/*  C4 — trad_motion.aep 을 다시 열어 판정하고 프레임을 찍는다.
      ① 푸티지 누락  ② 표현식 오류(시각을 여러 번 옮겨 가며)  ③ mogrt 파일 수
      ④ 컴포지션마다 f40(등장 끝난 뒤) 한 장 → 합성 스틸과 픽셀 대조용
      ⑤ 대표 셋(낙관 매수 · 붓 원 · 족자 자막 (본편))은 f0~f26 전부 → 움직임 미리보기 GIF 용
    출력: C:/aelab/trad_motion_check/  (final_<n>.png · anim_<n>_<ff>.png · _map.txt)
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c4");
var PACK = LAB + "/pack/trad_motion";
var AEP = PACK + "/trad_motion.aep";
var OUT = LAB + "/trad_motion_check";
var ANIM = { "낙관 매수": 1, "붓 원": 1, "족자 자막 (본편)": 1 };

function __main() {
say("잡", "C4 모션 꾸러미 재열기 검사 + 프레임 캡처");
closeQuietly();
probe("열기", function () { app.open(new File(AEP)); return app.project.numItems + "항목"; });

var miss = [], foot = 0;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (!(it instanceof FootageItem)) continue;
    foot++;
    if (it.footageMissing) miss.push(it.name);
}
say("푸티지", foot + "개 · " + (miss.length ? "**없음 " + miss.length + "개: " + miss.join(", ") + "**" : "전부 연결됨"));

var comps = [];
for (var j = 1; j <= app.project.numItems; j++) { var c = app.project.item(j); if (c instanceof CompItem) comps.push(c); }

var bad = [], checked = 0;
function scan(pg, where) {
    for (var a = 1; a <= pg.numProperties; a++) {
        var p = pg.property(a);
        if (p.numProperties != null && p.numProperties > 0) { scan(p, where); continue; }
        if (p.canSetExpression && p.expressionEnabled) {
            checked++;
            if (p.expressionError && String(p.expressionError).length) bad.push(where + " > " + p.name + ": " + String(p.expressionError).substr(0, 80));
        }
    }
}
var times = [0, 0.1, 0.5, 2];
for (var m = 0; m < comps.length; m++) {
    for (var ti = 0; ti < times.length; ti++) {
        comps[m].time = times[ti];
        for (var n = 1; n <= comps[m].numLayers; n++) {
            var L = comps[m].layer(n);
            try { scan(L, comps[m].name + " / " + L.name + " @" + times[ti] + "s"); } catch (e) {}
        }
    }
}
say("표현식", checked + "회 검사 · " + (bad.length ? "**오류 " + bad.length + "개**" : "오류 없음"));
for (var b = 0; b < Math.min(bad.length, 10); b++) out.push("    " + bad[b]);

probe("mogrt", function () {
    var fs = new Folder(PACK + "/mogrt").getFiles("*.mogrt"), t = [];
    for (var q = 0; q < fs.length; q++) t.push(decodeURI(fs[q].name) + " " + Math.round(fs[q].length / 1024) + "KB");
    return fs.length + "개 · " + t.join(" | ");
});

var od = new Folder(OUT);
if (od.exists) { var old = od.getFiles("*.png"); for (var r = 0; r < old.length; r++) old[r].remove(); } else od.create();
var map = [];
for (var k = 0; k < comps.length; k++) {
    (function (comp, idx) {
        map.push(idx + "\t" + comp.name);
        probe("  캡처 " + comp.name, function () {
            comp.saveFrameToPng(40 / comp.frameRate, new File(OUT + "/final_" + idx + ".png"));
            var nAnim = 0;
            if (ANIM[comp.name]) {
                for (var fr = 0; fr <= 26; fr++) {
                    var ff = (fr < 10 ? "0" : "") + fr;
                    comp.saveFrameToPng(fr / comp.frameRate, new File(OUT + "/anim_" + idx + "_" + ff + ".png"));
                    nAnim++;
                }
            }
            return comp.numLayers + "레이어" + (nAnim ? " · 움직임 " + nAnim + "장" : "");
        });
    })(comps[k], k);
}
_write(OUT + "/_map.txt", map.join("\n") + "\n");
flush();
if (miss.length || bad.length) return fail("누락 또는 표현식 오류");
return done("컴포지션 " + comps.length + "개 검사");
}
__main();
