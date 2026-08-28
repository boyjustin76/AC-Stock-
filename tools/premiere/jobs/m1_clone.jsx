/*
    M1-b. 시퀀스 하나를 복제하고 다른 이름으로 저장한다.

    출발점은 트랙 번호나 인덱스가 아니라 이름으로 찾는다 (§3-10).
    저장은 saveAs — 원본 사본(src.prproj)은 디스크에서 건드리지 않는다.
    검증은 이 스크립트가 하지 않는다. 저장된 파일을 gunzip 해서 따로 읽는다 (§3-5).
*/
(function () {
    var SRC  = "C:/pprolab/src.prproj";
    var BASE = "롱폼 고정 양식";
    var OUT  = "C:/pprolab/m1_out.prproj";

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function fail(msg) {
        say("FAILED", msg);
        var f = new File("C:/pprolab/m1_clone.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return "m1_clone FAILED: " + msg;
    }

    // 이미 열려 있으면 그대로 쓴다. 아니면 연다.
    var opened = false;
    try { opened = (app.project && app.project.path && app.project.path.indexOf("src.prproj") >= 0); } catch (e) {}
    if (!opened) {
        app.openDocument(SRC, 1, 1, 1, 1);
        var w = 0;
        while (w < 180 && !(app.project && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    }
    say("project.path", app.project.path);
    say("before_numSequences", app.project.sequences.numSequences);

    // 이름으로 찾는다
    var seqs = app.project.sequences, base = null;
    for (var i = 0; i < seqs.numSequences; i++) {
        if (seqs[i].name === BASE) { base = seqs[i]; break; }
    }
    if (!base) return fail("베이스 시퀀스를 못 찾았다: " + BASE);
    say("base.name", base.name);
    say("base.sequenceID", base.sequenceID);
    say("base.end_ticks", base.end);
    say("base.timebase", base.timebase);
    say("base.frameSize", base.frameSizeHorizontal + "x" + base.frameSizeVertical);
    say("base.numVideoTracks", base.videoTracks.numTracks);
    say("base.numAudioTracks", base.audioTracks.numTracks);

    // 잠긴 트랙을 먼저 푼다 (§3-8). 원래 상태를 적어 두고 푼다.
    var locked = [];
    function unlock(coll, tag) {
        for (var t = 0; t < coll.numTracks; t++) {
            var tr = coll[t];
            try {
                if (tr.isLocked && tr.isLocked()) { locked.push(tag + t); tr.setLocked(0); }
            } catch (e) { say("unlock_ERR_" + tag + t, e.toString()); }
        }
    }
    unlock(base.videoTracks, "V");
    unlock(base.audioTracks, "A");
    say("unlocked", locked.length ? locked.join(",") : "(잠긴 트랙 없음)");

    // 복제
    var before = seqs.numSequences;
    try { base.clone(); } catch (e) { return fail("clone() 실패: " + e.toString()); }
    var after = app.project.sequences.numSequences;
    say("after_numSequences", after);
    if (after !== before + 1) return fail("시퀀스가 하나 늘지 않았다: " + before + " -> " + after);

    // 늘어난 것이 무엇인지 이름으로 확인
    var names = [];
    for (var j = 0; j < after; j++) names.push(app.project.sequences[j].name);
    say("all_sequence_names", names.join(" | "));

    // 저장
    var res;
    try { res = app.project.saveAs(OUT); } catch (e2) { return fail("saveAs 실패: " + e2.toString()); }
    say("saveAs_return", String(res));
    say("project.path_after", app.project.path);

    var f2 = new File("C:/pprolab/m1_clone.txt");
    f2.encoding = "UTF-8"; f2.open("w"); f2.write(out.join("\n")); f2.close();
    return "m1_clone ok, " + before + " -> " + after + " sequences, saved " + OUT;
})();
