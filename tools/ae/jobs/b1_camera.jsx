/*  B1 — 차트 카메라 널 구조 찌르기.
;
    6종을 포팅하고 7종을 새로 쓰기 전에, **주석이 움직이는 차트를 따라가는 방식**부터
    확인한다. 이게 틀리면 나머지가 전부 헛일이다.

    구조:
      · 널 레이어 "차트 카메라" 에 슬라이더 4개(X0·BW·Y0·K)를 프레임마다 키프레임으로 박는다.
      · 주석은 표현식으로 자기 위치를 계산한다 —  x = X0 + 봉*BW,  y = Y0 - 가격*K
      · 주석마다 "손보정" 포인트 컨트롤을 둬서, 사람이 밀어도 추적이 안 깨지게 한다.

    프레임마다 키프레임이 있으므로 보간 방식은 상관없다(프레임 시각의 값이 곧 키 값이다).
    그래서 수백 개 키프레임의 이징을 따로 세팅하지 않는다 — 느리기만 하고 효과가 없다.

    판정은 렌더링이 아니라 숫자로 한다: 표현식이 계산한 Position 을 valueAtTime 으로
    되읽어, 밖에서 렌더러가 낸 값과 맞춰 본다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("b1");

var DATA = LAB + "/ae/sl-11-4.jsx";
var CUT  = "cut2-early-exit";
var AEP  = LAB + "/b1_camera.aep";

/*  좌표는 **최상위에서** 읽는다. $.evalFile 은 부른 자리의 스코프에 심으므로,
    함수 안에서 부르면 var SCENE 이 그 함수와 함께 사라진다 — 실제로 물렸다.  */
$.evalFile(new File(DATA));

function __main() {

say("잡", "B1 차트 카메라 널");
probe("좌표", function () {
    if (typeof SCENE === "undefined") throw new Error("좌표 파일을 못 읽었다: " + DATA);
    return SCENE.slug + " · 컷 " + SCENE.cuts.length + " · " + SCENE.w + "x" + SCENE.h + " @" + SCENE.fps;
});

var cut = null;
for (var i = 0; i < SCENE.cuts.length; i++) if (SCENE.cuts[i].id === CUT) cut = SCENE.cuts[i];
if (!cut) { flush(); return fail("컷이 없다: " + CUT); }
say("컷", cut.id + " · " + cut.frames + "f · 레이어 " + cut.layers.length + " · 카메라 " + (cut.still ? "멈춤" : "움직임"));

closeQuietly();
app.newProject();
var comp = probeVal("컴포지션", function () {
    var c = app.project.items.addComp("B1_" + CUT, SCENE.w, SCENE.h, 1, cut.frames / SCENE.fps, SCENE.fps);
    return c;
}, function (c) { return c.name + " · " + c.duration.toFixed(3) + "s"; });

/* ── 카메라 널 ─────────────────────────────────────────── */
var cam = comp.layers.addNull(comp.duration);
cam.name = "차트 카메라";
cam.enabled = false;               /* 보이지 않게 — 값만 나르는 레이어다 */
cam.shy = true;

var SLIDERS = ["X0", "BW", "Y0", "K"];
var times = [];
for (var f = 0; f < cut.frames; f++) times.push(f / SCENE.fps);

for (var s = 0; s < SLIDERS.length; s++) {
    (function (key) {
        probe("슬라이더 " + key, function () {
            var fx = cam.property("ADBE Effect Parade").addProperty("ADBE Slider Control");
            fx.name = key;
            var sl = fx.property(1);
            sl.setValuesAtTimes(times, cut.cam[key]);
            return sl.numKeys + "키 · 첫 " + sl.valueAtTime(0, false) + " · 끝 " + sl.valueAtTime(times[times.length - 1], false);
        });
    })(SLIDERS[s]);
}

/* ── 시험용 주석: 익절 화살표가 붙는 자리 (봉 53, 가격 24055) ── */
var BAR = 53, PRICE = 24055;

function camExpr(bar, price) {
    return 'var c = thisComp.layer("차트 카메라");\n'
         + 'var o = effect("손보정")(1);\n'
         + '[c.effect("X0")(1) + ' + bar + ' * c.effect("BW")(1) + o[0],\n'
         + ' c.effect("Y0")(1) - ' + price + ' * c.effect("K")(1) + o[1]]';
}

var mark = comp.layers.addShape();
mark.name = "시험 표식";
probe("표식 만들기", function () {
    var g = mark.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    g.name = "동그라미";
    var cts = g.property("ADBE Vectors Group");
    var el = cts.addProperty("ADBE Vector Shape - Ellipse");
    el.property("ADBE Vector Ellipse Size").setValue([40, 40]);
    var st = cts.addProperty("ADBE Vector Graphic - Stroke");
    st.property("ADBE Vector Stroke Color").setValue([1, 0, 0.33, 1]);
    st.property("ADBE Vector Stroke Width").setValue(6);
    /* 앵커를 0 으로 두면 레이어 좌표 = 컴포 좌표가 된다 (파일럿에서 정한 규칙) */
    mark.property("ADBE Transform Group").property("ADBE Anchor Point").setValue([0, 0]);
    var off = mark.property("ADBE Effect Parade").addProperty("ADBE Point Control");
    off.name = "손보정";
    /*  포인트 컨트롤의 기본값은 **컴포 중앙**이다([540,540]). 0 으로 내리지 않으면
        추적 좌표에 그만큼 얹혀 전부 어긋난다 — 실제로 물렸다.  */
    off.property(1).setValue([0, 0]);
    var pos = mark.property("ADBE Transform Group").property("ADBE Position");
    pos.expression = camExpr(BAR, PRICE);
    if (pos.expressionError && String(pos.expressionError).length) throw new Error("표현식 오류: " + pos.expressionError);
    return "봉 " + BAR + " / 가격 " + PRICE;
});

/* ── 판정: 표현식이 계산한 위치를 되읽는다 ───────────────── */
var pos = mark.property("ADBE Transform Group").property("ADBE Position");
var CHECK = [0, 30, 60, 90, 120, 150, 175];
var rows = [];
for (var k = 0; k < CHECK.length; k++) {
    var fn = CHECK[k];
    if (fn >= cut.frames) continue;
    var v = pos.valueAtTime(fn / SCENE.fps, false);
    rows.push(fn + ":" + Math.round(v[0] * 100) / 100 + "," + Math.round(v[1] * 100) / 100);
}
say("위치", rows.join("  "));

probe("저장", function () {
    app.project.save(new File(AEP));
    return "호출됨";
});

flush();
return done("카메라 널 + 표현식 구조 세움");
}
__main();
