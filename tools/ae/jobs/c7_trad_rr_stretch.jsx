/*  C7 — 문구를 바꾸면 판이 따라 커지는지 (옛 A6 합격선) 소스 컴포지션에서 확인한다.
    익절 낙관 '익절' → '1차 익절' · 손익비 현판 → '손익비  1 : 3.5' · 놓친 구간 문구 → '놓친 수익 구간'
    각각 f30 을 C:/aelab/trad_rr_check/stretch_<id>.png 로 찍는다. **저장하지 않는다.**
    ⚠ saveFrameToPng 는 비동기 — 찍은 뒤 문구를 되돌리지 않는다(되돌리면 대기 중인 캡처가 바뀐 값으로 찍힐 수 있다).
      다음 잡의 closeQuietly 가 저장 없이 닫는다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c7");
var AEP = LAB + "/pack/trad_rr/trad_rr.aep";
var OUT = LAB + "/trad_rr_check";
var TESTS = [
    { id: "tp_set", comp: "손익비 · 익절선&박스", text: "1차 익절" },
    { id: "rr", comp: "손익비 · 손익비 현판", text: "손익비  1 : 3.5" },
    { id: "note", comp: "손익비 · 놓친 구간 문구", text: "놓친 수익 구간" }
];

function __main() {
say("잡", "C7 문구 늘림 시험");
closeQuietly();
probe("열기", function () { app.open(new File(AEP)); return "열림"; });
for (var i = 0; i < TESTS.length; i++) {
    (function (t) {
        probe("  " + t.comp + " ← " + t.text, function () {
            var c = null;
            for (var k = 1; k <= app.project.numItems; k++) { var it = app.project.item(k); if (it instanceof CompItem && it.name === t.comp) c = it; }
            if (!c) throw new Error("컴포지션 없음");
            var L = c.layer("문구");
            var tp = L.property("ADBE Text Properties").property("ADBE Text Document");
            var before = L.sourceRectAtTime(1, false).width;
            var d = tp.value; d.text = t.text; tp.setValue(d);
            var after = L.sourceRectAtTime(1, false).width;
            c.saveFrameToPng(30 / c.frameRate, new File(OUT + "/stretch_" + t.id + ".png"));
            return "잉크폭 " + Math.round(before) + " → " + Math.round(after);
        });
    })(TESTS[i]);
}
flush();
return done("찍음 (저장 안 함)");
}
__main();
