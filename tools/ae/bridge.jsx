/*
    포토샵 안에서 돈다. 잡 .jsx 를 읽어 BridgeTalk 으로 애프터이펙트에 보내고,
    응답을 <labDir>/_result.txt 에 남긴다.

    tools/premiere/bridge.jsx 를 그대로 베끼고 타깃만 바꾼 것이다. 다른 점 하나:
    config.target 이 비어 있으면 BridgeTalk.getSpecifier(targetApp) 로 **실측해서** 쓴다.
    프리미어 때는 이미 실측한 값(premierepro-26.0)이 있었지만 AE 는 첫 접촉이라
    짐작으로 박지 않는다(매뉴얼 §3-2). 실측값은 _target.txt 에 남긴다.
*/
function readFile(p) {
    var f = new File(p);
    if (!f.exists) throw new Error("파일 없음: " + p);
    f.encoding = "UTF-8";
    f.open("r");
    var t = f.read();
    f.close();
    return t.replace(/^\uFEFF/, "");   // BOM 이 섞이면 경로가 안 맞는다
}
function writeFile(p, t) {
    var f = new File(p);
    f.encoding = "UTF-8";
    f.open("w");
    f.write(t);
    f.close();
}

var here = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
// ExtendScript 에 JSON 이 없는 판이 있다 — eval 로 읽는다
var cfg = eval("(" + readFile(here + "/config.json") + ")");
var lab = cfg.labDir;

/*  타깃 실측. getSpecifier 는 설치돼 있으면 "aftereffects-26.0" 같은 문자열을,
    없으면 null 을 준다. 여기서 null 이면 AE 미설치/미인식이지 잡의 잘못이 아니다.  */
var target = cfg.target;
var allTargets = [];
try { allTargets = BridgeTalk.getTargets(null) || []; } catch (e) { allTargets = ["(열거 실패: " + e.toString() + ")"]; }
if (!target) {
    try { target = BridgeTalk.getSpecifier(cfg.targetApp); } catch (e2) { target = null; }
}
writeFile(lab + "/_target.txt",
    "getSpecifier(" + cfg.targetApp + ")\t" + String(target) + "\n" +
    "getTargets(null)\t" + allTargets.join(" | "));
if (!target) {
    writeFile(lab + "/_result.txt",
        "FAIL\nNO_TARGET\t" + cfg.targetApp + " 을 BridgeTalk 이 못 찾는다.\n열거된 타깃: " + allTargets.join(" | "));
    "FAIL NO_TARGET  열거된 타깃: " + allTargets.join(" | ");
} else {

var jobPath = readFile(lab + "/_job.txt").replace(/^\s+|\s+$/g, "");

/*  잡 소스를 본문에 실어 보내면 안 된다 — 전송 중에 역슬래시가 한 번 더 이스케이프된다
    (프리미어 실측: "\t" 가 글자 t 로 실행됐다). 본문은 "이 파일 실행해라" 한 줄만.  */
var body =
    'var __r; try { __r = $.evalFile(new File("' + jobPath + '")); }' +
    ' catch (e) { __r = "JOBERR " + e.toString() + " @line " + e.line; } __r;';

var state = { done: false, ok: false, text: "" };

var bt = new BridgeTalk();
bt.target    = target;
bt.body      = body;
bt.onResult  = function (msg) { state.done = true; state.ok = true;  state.text = String(msg.body); };
bt.onError   = function (msg) { state.done = true; state.ok = false; state.text = "ERROR " + String(msg.body); };
bt.onTimeout = function ()    { state.done = true; state.ok = false; state.text = "TIMEOUT"; };

writeFile(lab + "/_result.txt", "PENDING\t" + target + "\t" + jobPath);
bt.send(cfg.timeoutSec);

var waited = 0;
while (!state.done && waited < cfg.timeoutSec) {
    BridgeTalk.pump();
    $.sleep(250);
    waited += 0.25;
}
if (!state.done) {
    /*  NO_RESPONSE 면 AE 탓하기 전에 포토샵의 열린 문서부터 적는다 —
        같은 포토샵 인스턴스를 썸네일 빌드가 지나가면 순서 대기가 생긴다.  */
    var busy = [];
    try {
        for (var d = 0; d < app.documents.length; d++) busy.push(app.documents[d].name);
    } catch (e3) { busy.push("(문서 목록 실패: " + e3.toString() + ")"); }
    state.text = "NO_RESPONSE\t" + waited + "s 기다렸다\n타깃: " + target +
                 "\n포토샵 열린 문서: " + (busy.length ? busy.join(" | ") : "(없음)");
}

writeFile(lab + "/_result.txt", (state.ok ? "OK" : "FAIL") + "\n" + state.text);
(state.ok ? "OK " : "FAIL ") + state.text;

}
