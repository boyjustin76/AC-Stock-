/*  A3 프레임 뽑기 — 렌더큐 대신 `comp.saveFrameToPng` 를 쓴다.

    렌더큐로 하면 출력 모듈 템플릿에 매인다. 한국어 판 템플릿 목록엔 **PNG 가 없고**,
    파일 이름을 .png 로 줘도 형식이 안 바뀐다 — 실측: 기본 H.264 로 .mp4 가 나왔다.
    saveFrameToPng 는 템플릿과 무관하게 한 프레임을 PNG 로 바로 쓴다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("a3_frame");

function __main() {

var AEP  = LAB + "/pilot.aep";
var NAME = "차11-4_컷2_손익비";
var OUT  = LAB + "/frames";
/*  바닥이 reveal 63 고정 스틸이라 렌더러와 배경이 일치하는 구간은 4.6~5.15초뿐이다.
    5.00초(150프레임)가 주 대조 시점. 나머지는 주석 등장 순서를 눈으로 보기 위한 것.  */
var SHOTS = [5.00, 4.70, 3.40, 2.00, 1.00, 0.60];

say("잡", "A3 프레임 (saveFrameToPng)");

closeQuietly();
probe("app.open", function () { app.open(new File(AEP)); return "열림 · items " + app.project.numItems; });

var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션이 없다"); }

probe("saveFrameToPng 있나", function () { return typeof comp.saveFrameToPng; });

var d = new Folder(OUT);
if (!d.exists) d.create();

var made = [];
for (var s = 0; s < SHOTS.length; s++) {
    (function (t) {
        probe(t.toFixed(2) + "s", function () {
            var tag = t.toFixed(2).replace(".", "_");
            var f = new File(OUT + "/a3_" + tag + "s.png");
            if (f.exists) f.remove();
            comp.saveFrameToPng(t, f);
            /*  ⚠ 쓰기가 곧바로 반영되지 않는다. 직후에 File.exists/length 를 보면 거짓 실패가 난다
                (실측: "0장" 이라고 보고했는데 디스크엔 6장이 다 있었다). 조금 기다렸다 다시 만들어 잰다.  */
            $.sleep(600);   /* 200 은 첫 장에 모자랐다 — 크기를 절반으로 잘못 읽었다 */
            var g = new File(OUT + "/a3_" + tag + "s.png");
            if (!g.exists || g.length === 0) throw new Error("파일이 안 생겼거나 0바이트다");
            made.push(g.name);
            return g.length + " bytes";
        });
    })(SHOTS[s]);
}
say("만든 것", made.join(" | "));

flush();
return done(made.length + "장");
}
__main();
