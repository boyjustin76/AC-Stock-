/*  A4 — Essential Graphics 노출.

    두 가지를 한다.
      ① **색을 하나로 묶는다.** 익절 색은 굵은 선과 라벨판 두 군데에 있다. 그대로 두면
         EGP 에 컨트롤이 두 개 뜨고, 팀장이 하나만 바꾸면 색이 어긋난다.
         라벨판 칠을 선 칠에 표현식으로 물려 **컨트롤 하나가 둘을 몬다.**
      ② 노출. 문구 4 + 색 3. 가격 슬라이더는 2차다(매뉴얼 A4 — 파일럿에서 시도하지 마라).

    `canAddToMotionGraphicsTemplate` 이 false 를 주는 속성이 무엇인지 기록하는 것이
    이 마일스톤의 실측 가치다(매뉴얼 A4 판정).
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("a4");

function __main() {

var AEP  = LAB + "/pilot.aep";
var NAME = "차11-4_컷2_손익비";
var MGT  = "차11-4 손익비";

say("잡", "A4 Essential Graphics 노출");

closeQuietly();
probe("app.open", function () { app.open(new File(AEP)); return "열림"; });

var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션이 없다"); }

function layerNamed(n) {
    for (var k = 1; k <= comp.numLayers; k++) if (comp.layer(k).name === n) return comp.layer(k);
    return null;
}
/** 이름 붙인 그룹 안의 이름 붙인 칠에서 색 속성을 꺼낸다 */
function fillColorOf(layerName, groupName, fillName) {
    var L = layerNamed(layerName);
    if (!L) throw new Error("레이어 없음: " + layerName);
    var root = L.property("ADBE Root Vectors Group");
    for (var a = 1; a <= root.numProperties; a++) {
        var g = root.property(a);
        if (g.name !== groupName) continue;
        var cts = g.property("ADBE Vectors Group");
        for (var b = 1; b <= cts.numProperties; b++) {
            var f = cts.property(b);
            if (f.name === fillName) return f.property("ADBE Vector Fill Color");
        }
    }
    throw new Error("칠 없음: " + layerName + " > " + groupName + " > " + fillName);
}
function strokeColorOf(layerName, groupName) {
    var L = layerNamed(layerName);
    var root = L.property("ADBE Root Vectors Group");
    for (var a = 1; a <= root.numProperties; a++) {
        var g = root.property(a);
        if (g.name !== groupName) continue;
        var cts = g.property("ADBE Vectors Group");
        for (var b = 1; b <= cts.numProperties; b++) {
            if (cts.property(b).matchName === "ADBE Vector Graphic - Stroke") {
                return cts.property(b).property("ADBE Vector Stroke Color");
            }
        }
    }
    throw new Error("획 없음: " + layerName + " > " + groupName);
}
function srcText(layerName) {
    var L = layerNamed(layerName);
    if (!L) throw new Error("레이어 없음: " + layerName);
    return L.property("ADBE Text Properties").property("ADBE Text Document");
}

/* ── ① 색 묶기 ─────────────────────────────────── */
function link(targetProp, srcLayer, srcGroup, srcFill, label) {
    probe("색 묶기 " + label, function () {
        targetProp.expression =
            'thisComp.layer("' + srcLayer + '").content("' + srcGroup + '").content("' + srcFill + '").color';
        /* 표현식 오류는 조용하다 — 반드시 되읽어서 확인한다 */
        if (targetProp.expressionError && String(targetProp.expressionError).length) {
            return "**표현식 오류** " + targetProp.expressionError;
        }
        var v = targetProp.value;
        return "ok · 값 " + [Math.round(v[0] * 255), Math.round(v[1] * 255), Math.round(v[2] * 255)].join(",");
    });
}
link(fillColorOf("2_익절박스_라벨판", "판", "판칠"), "2_익절박스", "선", "선칠", "익절 라벨판 ← 익절 선");
link(fillColorOf("3_손절박스_라벨판", "판", "판칠"), "3_손절박스", "선", "선칠", "손절 라벨판 ← 손절 선");
link(strokeColorOf("7_놓친구간_빗금", "그룹 1"),      "5_손익비_판", "판", "판칠", "빗금 사선 ← 강조");

/* ── ② 노출 ────────────────────────────────────── */
probe("템플릿 이름", function () { comp.motionGraphicsTemplateName = MGT; return comp.motionGraphicsTemplateName; });

var 목록 = [
    { 이름: "익절 라벨 문구",  p: function () { return srcText("2_익절박스_라벨"); } },
    { 이름: "손절 라벨 문구",  p: function () { return srcText("3_손절박스_라벨"); } },
    { 이름: "손익비 문구",     p: function () { return srcText("5_손익비_글씨"); } },
    { 이름: "놓친 구간 문구",  p: function () { return srcText("8_놓친구간_글자"); } },
    { 이름: "익절 색",         p: function () { return fillColorOf("2_익절박스", "선", "선칠"); } },
    { 이름: "손절 색",         p: function () { return fillColorOf("3_손절박스", "선", "선칠"); } },
    { 이름: "강조 색",         p: function () { return fillColorOf("5_손익비_판", "판", "판칠"); } }
];

var 성공 = 0, 실패 = [];
for (var n = 0; n < 목록.length; n++) {
    (function (item) {
        probe("노출 " + item.이름, function () {
            var pr = item.p();
            var can = pr.canAddToMotionGraphicsTemplate(comp);
            if (!can) { 실패.push(item.이름 + " (canAdd=false)"); return "canAdd=false — 노출 못 함"; }
            var ok = pr.addToMotionGraphicsTemplate(comp);
            if (ok) 성공++; else 실패.push(item.이름 + " (add 실패)");
            return "canAdd=true · add=" + ok;
        });
    })(목록[n]);
}

/* 참고 — 노출이 **안 되는** 속성도 재 둔다. 경계를 아는 게 실측 가치다(매뉴얼 A4). */
probe("참고: 노출 불가 후보", function () {
    var t = [];
    var tries = [
        ["레이어 위치", function () { return layerNamed("8_놓친구간_글자").property("ADBE Transform Group").property("ADBE Position"); }],
        ["레이어 불투명도", function () { return layerNamed("8_놓친구간_글자").property("ADBE Transform Group").property("ADBE Opacity"); }],
        ["마스크 패스", function () { return layerNamed("2_익절박스").property("ADBE Mask Parade").property(1).property("ADBE Mask Shape"); }],
        ["칠 불투명도", function () { var L = layerNamed("2_익절박스"); var root = L.property("ADBE Root Vectors Group");
              for (var a = 1; a <= root.numProperties; a++) if (root.property(a).name === "채움")
                  return root.property(a).property("ADBE Vectors Group").property("채움칠").property("ADBE Vector Fill Opacity");
              return null; }],
        ["푸티지 교체(바닥스틸 소스)", function () { return layerNamed("0_바닥스틸"); }]
    ];
    for (var k = 0; k < tries.length; k++) {
        var r;
        try {
            var pr = tries[k][1]();
            r = (pr && pr.canAddToMotionGraphicsTemplate) ? String(pr.canAddToMotionGraphicsTemplate(comp)) : "속성 아님";
        } catch (e) { r = "ERR " + e.toString(); }
        t.push(tries[k][0] + "=" + r);
    }
    return t.join(" · ");
});

say("노출 결과", 성공 + "/" + 목록.length + (실패.length ? " · 실패: " + 실패.join(", ") : ""));

probe("project.save", function () { app.project.save(new File(AEP)); return "호출됨"; });

flush();
if (실패.length) return fail(실패.join(", "));
return done(성공 + "개 노출");
}
__main();
