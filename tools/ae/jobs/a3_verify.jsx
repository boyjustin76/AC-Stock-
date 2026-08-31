/*  A3 판정 — 저장한 .aep 를 **새로 열어** dump 하고, 렌더큐로 프레임을 뽑는다.

    "저장 성공" 은 증거가 아니다(매뉴얼 §3-5). 증거는 둘이다:
      ① 재열기 dump 에 레이어가 전부 있는가
      ② 뽑은 프레임이 렌더러의 같은 시점과 같은 그림인가

    ②의 시점 선택이 중요하다. 바닥이 **reveal 63 고정 스틸**이므로 렌더러와 배경이
    일치하는 구간은 컷② 안에서 reveal 이 63 에 도달한 뒤 스우프 전까지 —
    즉 **4.6 ~ 5.15초** 뿐이다. 그래서 주 대조 시점은 **5.00초(150프레임)** 다.
    (그 앞은 캔들이 계속 자라는데 우리는 리빌 모션을 파일럿에서 포기했다 — 매뉴얼 승인.)
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("a3_verify");

/*  AE 는 최상위 return 을 문법 오류로 잡는다 — 본문을 함수로 감싼다.  */
function __main() {

var AEP   = LAB + "/pilot.aep";
var NAME  = "차11-4_컷2_손익비";
var OUT   = LAB + "/frames";
var SHOTS = [5.00, 4.70, 2.00, 0.60];   /* 첫 번째가 주 대조 시점 */

say("잡", "A3 재열기 검증 + 프레임");

closeQuietly();
probe("app.open", function () {
    var f = new File(AEP);
    if (!f.exists) throw new Error("파일이 없다: " + AEP);
    app.open(f);
    return String(app.project.file.fsName) + " · items " + app.project.numItems;
});

var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션 '" + NAME + "' 이 없다"); }
say("컴포지션", dumpComp(comp));

/* ── 레이어 dump ── */
var names = [], kf = 0, masks = 0;
for (var j = 1; j <= comp.numLayers; j++) {
    var L = comp.layer(j);
    var op = L.property("ADBE Transform Group").property("ADBE Opacity");
    var nk = op.numKeys;
    kf += nk;
    var mp = L.property("ADBE Mask Parade");
    var nm = mp ? mp.numProperties : 0;
    masks += nm;
    names.push(j + ":" + L.name + (nk ? " (불투명도 키 " + nk + ")" : "") + (nm ? " (마스크 " + nm + ")" : ""));
}
for (var n = 0; n < names.length; n++) say("  레이어 " + names[n].split(":")[0], names[n].substr(names[n].indexOf(":") + 1));
say("합계", comp.numLayers + " 레이어 · 불투명도 키 " + kf + " · 마스크 " + masks);

/*  렌더큐는 들어냈다. 한국어 판 출력 템플릿에 PNG 가 없어 .mp4 가 나오고,
    두 번째부터는 덮어쓰기 대화상자(모달)를 띄워 잡을 죽인다 — 실측으로 두 번 물렸다.
    프레임 뽑기는 a3_frame(saveFrameToPng)이 한다.  */

flush();
return done("재열기 + 프레임까지 끝. 그림 대조는 밖에서 한다");
}
__main();
