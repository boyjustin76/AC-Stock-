/*  C9 — 버튼-선 세트(익절선&박스 · 손절선&박스 · 진입선 · 지지선 · 저항선)를 **세트마다 따로 .aep** 로.
    사용자 요청(2026-09-14): "위 셋은 .aep 로도 만들어줘" + 지지선·저항선도 같은 세트로.

    빌더는 c5_trad_rr.jsx 것을 그대로 빌린다(__RR_LIB_ONLY). 세트마다 새 프로젝트 → 컴포지션 1개 → 저장.
    출력: <작업실>/pack/trad_rr/aep/<컴포지션 이름>.aep   — footage 는 ../footage (팩과 같은 상대 구조라 폴더째 옮겨도 열린다)
    끝에 하나씩 다시 열어 푸티지 누락·컴포지션·템플릿 컨트롤 수를 적는다. mogrt 는 만들지 않는다(그건 trad_rr_export.ps1).
*/
var HERE9 = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.global.__RR_LIB_ONLY = true;
$.evalFile(new File(HERE9 + "/c5_trad_rr.jsx"));
$.global.__RR_LIB_ONLY = false;
logTo("c9");
var AEP_DIR = PACK + "/aep";

function __main9() {
say("잡", "C9 버튼-선 세트 — 세트마다 aep");
var sets = [];
for (var i = 0; i < RR.items.length; i++) if (RR.items[i].kind === "set") sets.push(RR.items[i]);
say("세트", sets.length + "개");
probe("aep 폴더", function () {
    var d = new Folder(AEP_DIR);
    if (d.exists) { var old = d.getFiles("*.aep"); for (var q = 0; q < old.length; q++) old[q].remove(); return d.fsName + " (예전 aep " + old.length + "개 지움)"; }
    d.create();
    return d.fsName + " (새로 만듦)";
});

var saved = [], bad = [];
for (var s = 0; s < sets.length; s++) {
    (function (it) {
        var r = probe("  짓기 " + it.name, function () {
            closeQuietly();
            app.newProject();
            app.project.linearBlending = false; app.project.workingSpace = "";
            FOLDER_S = app.project.items.addFolder("소스 컴포지션");
            FOLDER_F = app.project.items.addFolder("footage");
            var o = buildItem(it);
            var fl = new File(AEP_DIR + "/" + it.name + ".aep");
            app.project.save(fl);
            saved.push(fl);
            return o.comp.numLayers + "레이어 · " + o.note + " → 저장";
        });
        if (String(r).indexOf("ERR") === 0) bad.push(it.name);
    })(sets[s]);
}
for (var e = 0; e < EXPOSED.length; e++) out.push("    노출 " + EXPOSED[e]);
flush();

for (var k = 0; k < saved.length; k++) {
    (function (fl) {
        var r = probe("  다시 열기 " + decodeURI(fl.name), function () {
            closeQuietly();
            app.open(fl);
            var comps = 0, foot = 0, miss = 0, ctl = 0;
            for (var j = 1; j <= app.project.numItems; j++) {
                var it = app.project.item(j);
                if (it instanceof CompItem) { comps++; ctl = it.motionGraphicsTemplateControllerCount; }
                else if (it instanceof FootageItem && it.file) { foot++; if (it.footageMissing) miss++; }
            }
            if (miss) throw new Error("푸티지 누락 " + miss + "/" + foot);
            return "컴포지션 " + comps + " · 푸티지 " + foot + " 연결 · 컨트롤 " + ctl + " · " + Math.round(fl.length / 1024) + "KB";
        });
        if (String(r).indexOf("ERR") === 0) bad.push(decodeURI(fl.name));
    })(saved[k]);
}
closeQuietly();
flush();
if (bad.length) return fail("문제: " + bad.join(", "));
return done("세트 aep " + saved.length + "개 저장·재열기 확인");
}
__main9();
