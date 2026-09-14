/*  C6 — trad_rr.aep 을 다시 열어 판정하고 프레임을 찍는다.
      ① 푸티지 누락  ② 표현식 오류(시각을 여러 번 옮겨 가며)  ③ mogrt 파일 수
      ④ 전체 f150(전부 등장 · 퇴장 전) 한 장 → 합성기 기준(_ref.png)과 픽셀 대조
      ⑤ 소스 컴포지션마다 f30(등장 끝) 한 장 → 떼어 써도 같은 자리·같은 모양인지
      ⑥ 전체 f0~f174 두 프레임마다 → 움직임 미리보기 GIF
    출력: C:/aelab/trad_rr_check/  (main_150.png · src_<id>.png · anim_<fff>.png · _map.txt)
    ⚠ saveFrameToPng 는 비동기다 — 이 잡 뒤에 프로젝트를 닫는 잡을 바로 붙이지 않는다 (C4 실측).
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c6");
var PACK = LAB + "/pack/trad_rr";
var AEP = PACK + "/trad_rr.aep";
var OUT = LAB + "/trad_rr_check";
var PFX = "손익비 · ";
$.evalFile(new File(PACK + "/footage/rr.jsx"));   /* RR */

function __main() {
say("잡", "C6 손익비 (전통) 재열기 검사 + 프레임 캡처");
closeQuietly();
probe("열기", function () { app.open(new File(AEP)); return app.project.numItems + "항목"; });

var miss = [], foot = 0;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (!(it instanceof FootageItem) || !it.file) continue;
    foot++;
    if (it.footageMissing) miss.push(it.name);
}
say("푸티지", foot + "개 · " + (miss.length ? "**없음 " + miss.length + "개: " + miss.join(", ") + "**" : "전부 연결됨"));

var comps = {};
for (var j = 1; j <= app.project.numItems; j++) { var c = app.project.item(j); if (c instanceof CompItem) comps[c.name] = c; }

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
var times = [0, 0.1, 0.5, 2, 5];
for (var nm in comps) {
    for (var ti = 0; ti < times.length; ti++) {
        comps[nm].time = times[ti];
        for (var n = 1; n <= comps[nm].numLayers; n++) {
            var L = comps[nm].layer(n);
            try { scan(L, nm + " / " + L.name + " @" + times[ti] + "s"); } catch (e) {}
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
var main = comps[RR.name];
if (!main) { flush(); return fail("전체 컴포지션이 없다"); }
probe("캡처 전체 f150 + 움직임", function () {
    main.saveFrameToPng(150 / main.frameRate, new File(OUT + "/main_150.png"));
    var k = 0;
    for (var fr = 0; fr < RR.frames; fr += 2) {
        var ff = ("00" + fr).slice(-3);
        main.saveFrameToPng(fr / main.frameRate, new File(OUT + "/anim_" + ff + ".png"));
        k++;
    }
    return "움직임 " + k + "장";
});
for (var s = 0; s < RR.items.length; s++) {
    (function (it) {
        probe("  캡처 " + it.title, function () {
            var cc = comps[it.name];
            if (!cc) throw new Error("소스 컴포지션 없음");
            cc.saveFrameToPng(30 / cc.frameRate, new File(OUT + "/src_" + it.id + ".png"));
            map.push(it.id + "\t" + it.title);
            return cc.numLayers + "레이어";
        });
    })(RR.items[s]);
}
_write(OUT + "/_map.txt", map.join("\n") + "\n");
flush();
if (miss.length || bad.length) return fail("누락 또는 표현식 오류");
return done("검사 끝 · 캡처 요청 " + (Math.ceil(RR.frames / 2) + 1 + RR.items.length) + "장");
}
__main();
