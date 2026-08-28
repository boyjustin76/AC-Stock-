/*
    M5 프로브 — 두 가지를 확인한다.

    1) 릴링크 API : projectItem.changeMediaPath 가 실제로 있는지, 오프라인 항목에 먹는지.
       프리셋 미디어 경로가 D:\01_공유 드라이브(파고들AC)\트레이딩팩토리\... 로 박혀 있는데
       이 PC 는 같은 드라이브를 G:\내 드라이브\트레이딩팩토리\... 로 마운트한다.
       (편집자 PC 는 '공유 드라이브' 로, 이 PC 는 '내 드라이브' 로 붙어 있다.)

    2) 트랙 삽입 : 차트는 스택에서 흰 배경(V0/V1) 위, 그래픽·로고(V2 이상) 아래에 와야 한다.
       공개 DOM 에 트랙 추가가 없다. qe 층의 addTracks 가 있는지 본다.
*/
(function () {
    var SRC = "C:/pprolab/m4_purged.prproj";
    var CLONE = "롱폼 고정 양식 복사";

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m5_probe.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }

    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; }
        catch (e) { say("closeDocument_ERR", e.toString()); break; }
    }
    say("닫은 프로젝트", closed);

    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m4_purged") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);

    /* ── 1. 릴링크 ─────────────────────────────────────────── */
    var root = app.project.rootItem;
    function walk(item, fn) {
        for (var i = 0; i < item.children.numItems; i++) {
            var ch = item.children[i];
            fn(ch);
            try { if (ch.type === ProjectItemType.BIN) walk(ch, fn); } catch (e) {}
        }
    }
    var offline = [], sample = null;
    walk(root, function (ch) {
        var mp = "";
        try { mp = ch.getMediaPath(); } catch (e) { return; }
        if (mp && mp.charAt(0).toUpperCase() === "D") { offline.push(ch); if (!sample) sample = ch; }
    });
    say("D: 로 시작하는 항목", offline.length);

    if (sample) {
        say("sample.name", sample.name);
        say("sample.mediaPath", sample.getMediaPath());
        say("sample.isOffline", (function () { try { return sample.isOffline(); } catch (e) { return "ERR " + e; } })());
        var api = ["changeMediaPath", "relinkMedia", "setOffline", "attachProxy", "canChangeMediaPath",
                   "refreshMedia", "getMediaPath", "isOffline", "isSequence"];
        for (var a = 0; a < api.length; a++) say("  typeof " + api[a], typeof sample[api[a]]);
    }

    /* ── 2. 트랙 삽입 ──────────────────────────────────────── */
    var seq = null;
    for (var i2 = 0; i2 < app.project.sequences.numSequences; i2++)
        if (app.project.sequences[i2].name === CLONE) seq = app.project.sequences[i2];
    if (!seq) return done("FAILED: 복제 시퀀스 없음");
    app.project.activeSequence = seq;
    say("videoTracks", seq.videoTracks.numTracks);
    say("audioTracks", seq.audioTracks.numTracks);

    probe("typeof qe (enableQE 전)", function () { return typeof qe; });
    probe("app.enableQE()", function () { return app.enableQE(); });
    probe("typeof qe (후)", function () { return typeof qe; });

    if (typeof qe !== "undefined" && qe) {
        probe("qe.project", function () { return typeof qe.project; });
        probe("qe 활성 시퀀스", function () { return qe.project.getActiveSequence().name; });
        var qs = null;
        try { qs = qe.project.getActiveSequence(); } catch (e) { say("qe_seq_ERR", e.toString()); }
        if (qs) {
            var qapi = ["addTracks", "removeTracks", "numVideoTracks", "getVideoTrackAt", "makeCurrent", "razor"];
            for (var b = 0; b < qapi.length; b++) say("  typeof qs." + qapi[b], typeof qs[qapi[b]]);
            probe("qs.numVideoTracks", function () { return qs.numVideoTracks; });
        }
    }

    return done("m5_probe ok");
})();
