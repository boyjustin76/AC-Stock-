/*  C5x — trad_rr.aep 의 템플릿을 mogrt 로 내보낸다. **하나 내보낼 때마다 디스크의 aep 를 새로 연다.**

    ⚠ 실측(2026-09-14 13:05, 컴퓨터 비정상 종료 뒤 새 AE):
      exportAsMotionGraphicsTemplate 가 메모리의 프로젝트를 **그 템플릿 컴포지션만 남도록 줄여 놓고 되돌리지 않았다**
      (내보내기 2번 뒤 항목 7개 · 컴포지션 1개 · dirty=true — c5c_state_probe).
      종료 전에는 같은 코드로 13개가 다 나갔으므로 늘 그렇다고 믿을 수 없다 → 매번 새로 연다.
      그리고 **이 잡은 절대 저장하지 않는다.** 줄어든 프로젝트를 저장하면 aep 가 망가진다.
    같은 세션에서 saveFrameToPng 캡처 뒤 내보내기가 썸네일(thumb.mp4 0바이트)에서 멈춘 적이 있다(12:49) —
    그래서 검사·캡처 잡(c6)과 섞지 않고 따로 돈다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c5x");
var PACK = LAB + "/pack/trad_rr";
var AEP = PACK + "/trad_rr.aep";
/*  ⚠ 실측(2026-09-14 13:17, c5t_export_trial): **프로젝트 폴더 안**(pack/trad_rr/mogrt)으로 내보내면 '손절 박스' 가
    푸티지 누락 2 로 적히고 프로젝트가 7항목으로 줄어 남았다. **폴더 밖**으로 같은 컴포지션을 내보내니 누락 0 · 항목 그대로.
    그래서 밖(trad_rr_mogrt_out)으로 내보내고, 누락 검사를 통과한 파일만 밖에서 pack/trad_rr/mogrt 로 옮긴다.
    또 하나: 내보내기는 **수정된(dirty) 프로젝트를 디스크에 저장한다** — 이 잡에서 프로젝트를 바꾸는 코드를 넣지 말 것.  */
var MOG = LAB + "/trad_rr_mogrt_out";
/*  비워 두면 전부. 이름을 넣으면 그것만 다시 내보내고 **그 파일만** 지운다
    (2026-09-14: '손익비 · 손절 박스' 가 내보낸 뒤 프로젝트가 7항목으로 줄면서 누락 자산 2 로 나왔다).  */
var ONLY = [];

function templates() {
    var t = [];
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it instanceof CompItem && it.motionGraphicsTemplateName) t.push(it.name);
    }
    return t;
}
function openFresh() {
    app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
    app.open(new File(AEP));
}
function compNamed(nm) {
    for (var z = 1; z <= app.project.numItems; z++) {
        var it = app.project.item(z);
        if (it instanceof CompItem && it.name === nm) return it;
    }
    return null;
}

function __main() {
say("잡", "C5x mogrt 내보내기 (하나마다 새로 열기 · 저장 안 함)");
closeQuietly();
var names = [];
probe("aep 확인", function () {
    app.open(new File(AEP));
    names = templates();
    if (names.length < 13) throw new Error("템플릿 컴포지션이 " + names.length + "개뿐 — aep 가 온전하지 않다. 내보내지 않는다");
    return app.project.numItems + "항목 · 템플릿 " + names.length + "개";
});
if (names.length < 13) { flush(); return fail("aep 가 온전하지 않다"); }
if (ONLY.length) {
    var pick = [];
    for (var s = 0; s < names.length; s++) for (var t = 0; t < ONLY.length; t++) if (names[s] === ONLY[t]) pick.push(names[s]);
    if (pick.length !== ONLY.length) { flush(); return fail("ONLY 에 aep 에 없는 이름이 있다: " + ONLY.join(", ")); }
    names = pick;
    say("대상", names.join(", "));
}

probe("mogrt 폴더 비우기", function () {
    var dd = new Folder(MOG);
    if (!dd.exists) { dd.create(); return dd.fsName + " (새로 만듦)"; }
    if (ONLY.length) {
        var gone = [];
        for (var o = 0; o < ONLY.length; o++) { var fo = new File(MOG + "/" + ONLY[o] + ".mogrt"); if (fo.exists && fo.remove()) gone.push(ONLY[o]); }
        return "지정한 것만 지움: " + gone.join(", ");
    }
    var old = dd.getFiles("*.mogrt"); for (var q = 0; q < old.length; q++) old[q].remove();
    return dd.fsName + " 전부 비움";
});

var ok = 0, bad = [];
app.beginSuppressDialogs();
for (var m = 0; m < names.length; m++) {
    (function (nm, idx) {
        var r = probe("  " + nm, function () {
            if (idx > 0) openFresh();
            var c = compNamed(nm);
            if (!c) throw new Error("다시 연 aep 에 없다");
            var res = c.exportAsMotionGraphicsTemplate(true, MOG);
            return String(res) + " · 내보낸 뒤 항목 " + app.project.numItems;
        });
        if (String(r).indexOf("true") === 0) ok++; else bad.push(nm);
    })(names[m], m);
}
app.endSuppressDialogs(false);
/* 줄어든 상태로 남기지 않는다 — 저장 없이 닫고 온전한 aep 를 다시 열어 둔다 */
probe("정리: 저장 없이 닫고 다시 열기", function () { openFresh(); return app.project.numItems + "항목"; });
flush();
if (bad.length) return fail("못 내보낸 것 " + bad.length + "개: " + bad.join(", "));
return done("mogrt " + ok + "개 내보냄");
}
__main();
