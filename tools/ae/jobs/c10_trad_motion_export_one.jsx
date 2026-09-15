/*  C10 — trad_motion.aep 에서 템플릿 **하나만** 같은 이름으로 다시 내보낸다. **저장하지 않는다.**
    2026-09-15: 매도 낙관을 파랑(#1F60E0)으로 바꿔 footage/sources/s21_seal_sell.png 를 교체했다 →
    '낙관 매도.mogrt' 안에는 옛 쪽빛 PNG 가 들어 있어 이름 그대로 다시 내보낸다.
    출력은 팩 밖(C:/aelab/trad_motion_mogrt_out) — 검사(zip 안 누락 자산 · 들어간 PNG 해시 · capsuleID)를 통과한 뒤에만 팩·납품으로 옮긴다.
    ⚠ 내보내기는 수정된(dirty) 프로젝트를 디스크에 저장한다 — 이 잡은 프로젝트를 바꾸지 않는다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c10");
var AEP = LAB + "/pack/trad_motion/trad_motion.aep";
var OUTD = LAB + "/trad_motion_mogrt_out";
var NAME = "낙관 매도";

function compNamed(nm) {
    for (var z = 1; z <= app.project.numItems; z++) {
        var it = app.project.item(z);
        if (it instanceof CompItem && it.name === nm) return it;
    }
    return null;
}

function __main() {
say("잡", "C10 템플릿 하나 다시 내보내기 — " + NAME + " (저장 안 함)");
closeQuietly();
probe("열기", function () { app.open(new File(AEP)); return app.project.numItems + "항목 · dirty=" + app.project.dirty; });
var c = compNamed(NAME);
if (!c) { flush(); return fail("컴포지션 없음: " + NAME); }
probe("템플릿 이름", function () {
    if (c.motionGraphicsTemplateName !== NAME) throw new Error("템플릿 이름이 다르다: " + c.motionGraphicsTemplateName);
    return c.motionGraphicsTemplateName + " · 컨트롤 " + c.motionGraphicsTemplateControllerCount;
});
probe("푸티지", function () {
    var t = [];
    for (var i = 1; i <= c.numLayers; i++) {
        var L = c.layer(i);
        if (L.source && L.source instanceof FootageItem && L.source.file) {
            var s = L.source;
            if (s.footageMissing) throw new Error("푸티지 누락: " + s.name);
            t.push(s.name + " " + s.width + "x" + s.height + " ← " + s.file.fsName);
        }
    }
    return t.join(" ; ");
});
probe("출력 폴더", function () {
    var d = new Folder(OUTD);
    if (!d.exists) d.create();
    var f = new File(OUTD + "/" + NAME + ".mogrt");
    if (f.exists) f.remove();
    return d.fsName;
});
app.beginSuppressDialogs();
probe("내보내기", function () {
    var res = c.exportAsMotionGraphicsTemplate(true, OUTD);
    return String(res) + " · 내보낸 뒤 항목 " + app.project.numItems + " · dirty=" + app.project.dirty;
});
app.endSuppressDialogs(false);
$.sleep(400);
probe("파일", function () { var f = new File(OUTD + "/" + NAME + ".mogrt"); return f.exists ? f.length + " bytes" : "없음"; });
closeQuietly();
flush();
return done("내보냄 (저장 안 함)");
}
__main();
