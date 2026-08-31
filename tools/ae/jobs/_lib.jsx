/*  AE 잡 공용 헬퍼.  각 잡이 맨 앞에서 이렇게 부른다:

        $.evalFile(new File(String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/") + "/_lib.jsx"));

    설계 두 가지는 프리미어 M6 에서 피 보고 배운 것이다:
      · **매 줄마다 로그를 flush 한다.** 멈춰도 어디서 멈췄는지는 남는다.
      · **측정값을 반환값에도 싣는다.** AE 는 환경설정이 꺼져 있으면 파일 쓰기가
        조용히 죽으므로, 파일에만 쓰면 실패 시 아무 정보가 없다.
*/
var LAB = "C:/aelab";
var LOGDIR = LAB + "/log";
var out = [];
var LOGPATH = null;

function _write(p, t) {
    try {
        var d = new Folder(LOGDIR);
        if (!d.exists) d.create();
        var f = new File(p);
        f.encoding = "UTF-8";
        if (!f.open("w")) return false;
        f.write(t);
        f.close();
        /*  A1 실측: 파일쓰기 권한이 없으면 open 은 **통과하고** 0바이트 파일이 생긴 뒤
            write 에서 거부된다. 그러므로 "파일이 있다" 는 증거가 아니다 — 길이를 본다.  */
        return (new File(p)).length > 0;
    } catch (e) { return false; }
}

/** 잡 이름을 주면 그 이름으로 로그를 쓴다 */
function logTo(name) { LOGPATH = LOGDIR + "/" + name + ".txt"; }

function flush() { if (LOGPATH) _write(LOGPATH, out.join("\n") + "\n"); }

function say(k, v) { out.push(k + "\t" + v); flush(); }

/** 위험한 호출은 이걸로 감싼다 — 부르기 **전에** 한 줄 남긴다 */
function probe(k, fn) {
    out.push(k + "\t…호출 직전"); flush();
    var r;
    try { r = String(fn()); } catch (e) { r = "ERR " + e.toString() + (e.line ? " @line " + e.line : ""); }
    out[out.length - 1] = k + "\t" + r; flush();
    return r;
}

function fail(msg) { say("판정", "실패 — " + msg); return "FAIL\n" + out.join("\n"); }
function done(msg) { say("판정", msg || "통과"); return "OK\n" + out.join("\n"); }

/** 열린 프로젝트를 조용히 닫는다. 안 닫으면 newProject/open 이 "저장할까요" 모달을 띄운다. */
function closeQuietly() {
    return probe("기존 프로젝트 닫기", function () {
        if (!app.project) return "프로젝트 없음";
        app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        return "닫음";
    });
}

/** 초 → 프레임(반올림) 과 그 역 */
function fr(sec, fps) { return Math.round(sec * fps); }

/** 컴포지션 한 개를 dump 한다 — 검증용 */
function dumpComp(c) {
    var t = [];
    t.push("이름=" + c.name);
    t.push("크기=" + c.width + "x" + c.height);
    t.push("fps=" + c.frameRate);
    t.push("길이초=" + c.duration);
    t.push("프레임=" + Math.round(c.duration * c.frameRate));
    t.push("픽셀종횡비=" + c.pixelAspect);
    t.push("레이어=" + c.numLayers);
    return t.join(" · ");
}
