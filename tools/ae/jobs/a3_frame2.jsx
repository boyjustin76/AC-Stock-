/*  saveFrameToPng 가 조용히 아무것도 안 만든다. 표기법을 바꿔 가며 잰다.
    프리미어 exportFramePNG 가 "슬래시 금지 + 확장자는 함수가 붙인다" 였던 전례가 있다.  */
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("a3_frame2");

function __main() {

var BS   = String.fromCharCode(92);
var AEP  = LAB + "/pilot.aep";
var NAME = "차11-4_컷2_손익비";
var DIR  = LAB + "/frames";
var T    = 5.0;

closeQuietly();
probe("app.open", function () { app.open(new File(AEP)); return "열림"; });
var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션 없음"); }

var d = new Folder(DIR);
if (!d.exists) d.create();

function snapshot() {
    var fs = d.getFiles();
    var t = [];
    for (var k = 0; k < fs.length; k++) t.push(fs[k].name);
    return t.join(",");
}
function tryIt(label, mk) {
    probe(label, function () {
        var before = snapshot();
        var r;
        try { r = String(comp.saveFrameToPng(T, mk())); } catch (e) { return "throw: " + e.toString(); }
        var after = snapshot();
        var news = [];
        var b = "," + before + ",";
        var arr = after.split(",");
        for (var k = 0; k < arr.length; k++) if (arr[k] && b.indexOf("," + arr[k] + ",") < 0) news.push(arr[k]);
        return "반환=" + r + " · 새 파일=" + (news.length ? news.join(" ") : "없음");
    });
}

tryIt("① 슬래시 + .png",      function () { return new File(DIR + "/v1.png"); });
tryIt("② 슬래시 + 확장자없음", function () { return new File(DIR + "/v2"); });
tryIt("③ 역슬래시 + .png",    function () { return new File(DIR.split("/").join(BS) + BS + "v3.png"); });
tryIt("④ fsName 로 다시 만든 File", function () {
    var f = new File(DIR + "/v4.png");
    return new File(f.fsName);
});
tryIt("⑤ 문자열 그대로",      function () { return DIR + "/v5.png"; });
tryIt("⑥ 이미 열어 둔 File",  function () {
    var f = new File(DIR + "/v6.png");
    f.open("w"); f.close();
    return f;
});

/* 렌더큐 경로도 하나 남겨 둔다 — 위가 다 실패하면 이쪽이 대안이다 */
probe("참고: 렌더큐 기본 템플릿", function () {
    var rq = app.project.renderQueue;
    while (rq.numItems > 0) rq.item(1).remove();
    var item = rq.items.add(comp);
    var om = item.outputModule(1);
    var s = "기본템플릿=" + om.name + " · 파일=" + (om.file ? om.file.name : "null");
    item.remove();
    return s;
});

flush();
return done("표기법 실측 끝");
}
__main();
