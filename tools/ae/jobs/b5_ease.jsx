/*  B5 — 키 2개 + 이징으로 렌더러 곡선을 얼마나 맞출 수 있는지 **실측**한다.
;
    왜 필요한가 —
      지금은 알파를 프레임마다 구워 넣는다. 정확하지만 키가 너무 많아 사람이 손대기 무섭다.
      키 2개로 줄이려면 AE 의 시간 이징(KeyframeEase)이 렌더러 곡선을 대신해야 하는데,
      Easy Ease 는 좌우 대칭이고 렌더러 이징은 한쪽으로 치우쳐 있다. 그냥 씌우면
      페이드 중간에서 크게 벌어진다(실제로 60% vs 92% 로 물렸다).

    그래서 짐작하지 않고 잰다:
      · 시작·끝 **속도**는 곡선의 미분값에서 온다 (outCubic'(0)=3, outExpo'(0)=6.93 …).
      · **영향력(influence)** 은 후보를 쓸어 보며 오차가 가장 작은 것을 고른다.
      · 고른 뒤 AE 가 보간한 값을 프레임마다 되읽어 원곡선과 대조한다.

    결과는 로그로만 낸다. 프로젝트는 남기지 않는다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
$.evalFile(new File(HERE + "/_ae.jsx"));
logTo("b5");

function __main() {

var FPS = 30, DUR = 2;

say("잡", "B5 이징 맞추기 실측");
closeQuietly();
app.newProject();
var comp = app.project.items.addComp("B5", 100, 100, 1, DUR, FPS);
var nul = comp.layers.addNull(DUR);
var sl = nul.property("ADBE Effect Parade").addProperty("ADBE Slider Control").property(1);

/*  후보 곡선: 이름, 함수, 시작 미분, 끝 미분.
    렌더러 anim.js 의 Ease 를 그대로 옮긴 것이다.  */
var CURVES = [
    { name: "outCubic",  f: E.outCubic,  d0: 3,    d1: 0 },
    { name: "outQuart",  f: E.outQuart,  d0: 4,    d1: 0 },
    { name: "outExpo",   f: E.outExpo,   d0: 6.93, d1: 0 },
    { name: "outBack",   f: E.outBack,   d0: 4.2,  d1: 0 },
    { name: "inOutQuad", f: E.inOutQuad, d0: 0,    d1: 0 }
];
/* 영향력 후보 — 0.1 은 AE 최솟값이다 */
var INF = [0.1, 8, 16, 25, 33, 42, 50, 60, 70, 80, 90];

/** 구간 [0, d] 에서 0→100 을 두 키로 박고, 이징을 준 뒤 프레임마다 되읽어 최대 오차를 낸다 */
function measure(curve, d, i1, i2) {
    while (sl.numKeys > 0) sl.removeKey(1);
    sl.setValueAtTime(0, 0);
    sl.setValueAtTime(d, 100);
    /* 속도는 '값/초' 단위다. 0→100 을 d 초에 가므로 평균 속도는 100/d 다. */
    var avg = 100 / d;
    try {
        sl.setTemporalEaseAtKey(1, [new KeyframeEase(curve.d0 * avg, i1)], [new KeyframeEase(curve.d0 * avg, i1)]);
        sl.setTemporalEaseAtKey(2, [new KeyframeEase(curve.d1 * avg, i2)], [new KeyframeEase(curve.d1 * avg, i2)]);
    } catch (e) { return { err: 999, msg: String(e) }; }
    var worst = 0, n = Math.round(d * FPS);
    for (var f = 0; f <= n; f++) {
        var t = f / FPS;
        var want = curve.f(t / d) * 100;
        var got = sl.valueAtTime(t, false);
        var e2 = Math.abs(got - want);
        if (e2 > worst) worst = e2;
    }
    return { err: worst };
}

/* 실제로 쓰이는 길이들 — 씬의 등장·퇴장 길이가 대개 이 범위다 */
var DURS = [0.2, 0.35, 0.45];

for (var c = 0; c < CURVES.length; c++) {
    (function (curve) {
        probe(curve.name, function () {
            var rows = [];
            for (var k = 0; k < DURS.length; k++) {
                var d = DURS[k];
                var best = null;
                for (var a = 0; a < INF.length; a++) {
                    for (var b = 0; b < INF.length; b++) {
                        var r = measure(curve, d, INF[a], INF[b]);
                        if (!best || r.err < best.err) best = { err: r.err, i1: INF[a], i2: INF[b] };
                    }
                }
                /* 견줄 대상 — 기본 이지이즈(양쪽 33%, 속도 0) */
                while (sl.numKeys > 0) sl.removeKey(1);
                sl.setValueAtTime(0, 0);
                sl.setValueAtTime(d, 100);
                sl.setTemporalEaseAtKey(1, [new KeyframeEase(0, 33)], [new KeyframeEase(0, 33)]);
                sl.setTemporalEaseAtKey(2, [new KeyframeEase(0, 33)], [new KeyframeEase(0, 33)]);
                var ez = 0, n = Math.round(d * FPS);
                for (var f = 0; f <= n; f++) {
                    var t = f / FPS;
                    var e3 = Math.abs(sl.valueAtTime(t, false) - curve.f(t / d) * 100);
                    if (e3 > ez) ez = e3;
                }
                rows.push(d + "s: 최적 영향력 " + best.i1 + "/" + best.i2
                        + " 오차 " + (Math.round(best.err * 100) / 100) + "%"
                        + " (이지이즈면 " + (Math.round(ez * 10) / 10) + "%)");
            }
            return rows.join("  ·  ");
        });
    })(CURVES[c]);
}

flush();
return done("이징 실측 끝");
}
__main();
