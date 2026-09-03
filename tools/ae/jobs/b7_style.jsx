/*  B7 — 태그 광선을 무엇으로 그릴지 실측한다.
;
    ⚠ app.newProject() 앞에 반드시 closeQuietly() — 안 그러면 "저장하시겠습니까?" 모달이
       세션을 막는다(두 번 물렸다).

    ── 레이어 스타일은 접었다 ──────────────────────────────────
    "ADBE Layer Styles" 그룹은 셰이프 레이어에 처음부터 있고 하위 11개가 스타일 그룹이다
    (matchName `outerGlow/enabled` 인데 스위치가 아니라 그룹이다). 그런데 **켤 수가 없다**:
      · `.enabled = true`        → canSetEnabled 가 false
      · 하위 값 setValue          → "속성 또는 부모 속성이 숨겨져 있으므로"
      · findMenuCommandId("외부 광선") → 0
      · 9000~9012 훑기            → 전부 안 켜짐
    findMenuCommandId("그림자 효과") 가 잡히긴 하는데 그건 레이어 스타일이 아니라
    **효과 메뉴의 그림자 효과**다. 이름이 같아 헷갈린다.

    ── 그래서 효과로 간다 ──────────────────────────────────────
    렌더러의 광선은 offsetY 0 · blur 0.114·h · 검정 18% 를 3번 겹친 것이다. 방향이 없으니
    **거리 0 인 드롭 섀도 효과**가 곧 같은 그림이다. 효과는 이미 쓰는 API 라 안전하다.
    여기서는 속성 이름·색인·범위만 확인한다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("b7");

function __main() {

say("잡", "B7 그림자 효과 속성 실측");

var S = null;

closeQuietly();
probe("빈 컴포지션 + 셰이프", function () {
    app.newProject();
    var comp = app.project.items.addComp("탐침", 200, 200, 1, 2, 30);
    S = comp.layers.addShape();
    S.name = "탐침 셰이프";
    return "지음";
});

probe("ADBE Drop Shadow 붙이기", function () {
    var e = S.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
    var t = ["붙임 · 속성 " + e.numProperties + "개"];
    for (var k = 1; k <= e.numProperties; k++) {
        var q = e.property(k);
        var v = ""; try { v = " = " + q.value; } catch (err) { v = " (못 읽음)"; }
        var rng = "";
        try { rng = " [" + q.minValue + "~" + q.maxValue + "]"; } catch (err2) {}
        t.push("        " + k + " [" + q.matchName + "] " + q.name + v + rng);
    }
    return String.fromCharCode(10) + t.join(String.fromCharCode(10));
});

probe("값 넣고 되읽기 (거리 0 = 사방 광선)", function () {
    var e = S.property("ADBE Effect Parade").property(1);
    e.property(1).setValue([0, 0, 0]);   /* 그림자 색상 */
    e.property(2).setValue(115);         /* 불투명도 0~255 */
    e.property(3).setValue(0);           /* 방향 */
    e.property(4).setValue(0);           /* 거리 */
    e.property(5).setValue(10);          /* 부드러움 */
    var t = [];
    for (var k = 1; k <= e.numProperties; k++) {
        var q = e.property(k);
        var v = ""; try { v = " = " + q.value; } catch (err) { v = " (못 읽음)"; }
        t.push("        " + k + " " + q.name + v);
    }
    return String.fromCharCode(10) + t.join(String.fromCharCode(10));
});

flush();
return done("탐침 끝");
}
__main();
