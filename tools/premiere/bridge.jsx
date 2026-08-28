/*
    포토샵 안에서 돈다. 잡 .jsx 를 읽어 BridgeTalk 으로 프리미어에 보내고,
    응답을 <labDir>/_result.txt 에 남긴다.

    프리미어에는 Photoshop.Application 같은 COM 자동화 ProgID 가 없다(실측).
    대신 포토샵이 BridgeTalk 대상으로 premierepro-26.0 을 본다(실측) — 그걸 전송로로 쓴다.
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
// ExtendScript 에 JSON 이 없는 판이 있다 — eval 로 읽는다 (포토샵 build_thumb.jsx 와 같은 방식)
var cfg = eval("(" + readFile(here + "/config.json") + ")");
var lab = cfg.labDir;

var jobPath = readFile(lab + "/_job.txt").replace(/^\s+|\s+$/g, "");

/*  잡 소스를 본문에 실어 보내면 안 된다 — BridgeTalk 전송 중에 역슬래시 이스케이프가
    한 번 더 이스케이프된다 (실측: "\t" 가 프리미어에서 글자 \t 로 실행됐다).
    본문은 "이 파일을 실행해라" 한 줄만 보내고, 소스는 프리미어가 디스크에서 직접 읽는다.
    덤으로 본문이 짧아져 메시지 크기 제한에서도 자유롭다.  */
var body =
    'var __r; try { __r = $.evalFile(new File("' + jobPath + '")); }' +
    ' catch (e) { __r = "JOBERR " + e.toString() + " @line " + e.line; } __r;';

var state = { done: false, ok: false, text: "" };

var bt = new BridgeTalk();
bt.target    = cfg.target;
bt.body      = body;
bt.onResult  = function (msg) { state.done = true; state.ok = true;  state.text = String(msg.body); };
bt.onError   = function (msg) { state.done = true; state.ok = false; state.text = "ERROR " + String(msg.body); };
bt.onTimeout = function ()    { state.done = true; state.ok = false; state.text = "TIMEOUT"; };

writeFile(lab + "/_result.txt", "PENDING\t" + jobPath);
bt.send(cfg.timeoutSec);

var waited = 0;
while (!state.done && waited < cfg.timeoutSec) {
    BridgeTalk.pump();
    $.sleep(250);
    waited += 0.25;
}
if (!state.done) {
    /*  §5 — NO_RESPONSE 면 프리미어 탓하기 전에 포토샵의 열린 문서부터 적는다.
        썸네일 빌드가 같은 포토샵 인스턴스를 지나가면 순서 대기가 생긴다.  */
    var busy = [];
    try {
        for (var d = 0; d < app.documents.length; d++) busy.push(app.documents[d].name);
    } catch (e) { busy.push("(문서 목록 실패: " + e.toString() + ")"); }
    state.text = "NO_RESPONSE\t" + waited + "s 기다렸다\n포토샵 열린 문서: " +
                 (busy.length ? busy.join(" | ") : "(없음)");
}

writeFile(lab + "/_result.txt", (state.ok ? "OK" : "FAIL") + "\n" + state.text);
(state.ok ? "OK " : "FAIL ") + state.text;
