/*
    M4-a. §3-9 정리 — 회차 시퀀스와 **그것이 쓰는 중첩 시퀀스**만 남기고 나머지를 지운다.

    컷 배치(대본 타임코드)와 무관한 조각이라 격자 결정 전에 먼저 한다.
    포토샵에서 195MB → 11.5MB 가 된 그 단계에 해당한다. 미사용 참조는 검증도 어지럽힌다.

    1차 시도에서 배운 것 둘 (둘 다 조용히 틀린다):
      * `sequence.close()` 는 아무것도 안 지운다 — 타임라인 탭만 닫는다. 9개에 걸어
        10 -> 10 그대로였고 오류도 없었다. 지우는 것은 `app.project.deleteSequence(seq)`.
      * "남길 것 하나 빼고 다 지운다" 로 하면 **남긴 시퀀스가 부서진다.** 롱폼 뼈대는
        중첩 시퀀스 3개를 타임라인에서 쓰고 있어서, 그걸 지우니 클립이 44 -> 41 로 줄었다.
        의존 관계를 먼저 계산해야 한다 (재귀).
      * `saveAs` 는 대상 파일이 프리미어에 열려 있으면 **예외 없이 false 를 돌려준다.**
        반환값을 반드시 본다.
*/
(function () {
    var SRC  = "C:/pprolab/m4_src.prproj";
    var OUT  = "C:/pprolab/m4_out.prproj";
    var KEEP = "롱폼 고정 양식 복사";

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m4_cleanup.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }

    // 다른 프로젝트가 열려 있으면 저장 대상이 잠긴다. 먼저 정리한다.
    probe("열린 프로젝트 수", function () { return app.projects.numProjects; });
    probe("열린 프로젝트", function () {
        var a = [];
        for (var i = 0; i < app.projects.numProjects; i++) a.push(app.projects[i].name);
        return a.join(" | ");
    });

    /*  이미 열려 있으면 재사용 — 하던 이 방식이 물렸다. 디스크의 파일을 새로 복사해
        덮어써도 **이미 열린 프로젝트는 안 바뀐다.** 직전 실행의 손상된 메모리 상태를
        그대로 다시 보게 된다. 그리고 열린 프로젝트는 그 파일을 잠가서 saveAs 가 false 를
        돌려준다. 그래서 전부 닫고 새로 연다.  */
    var closed = 0;
    for (var guard = 0; guard < 50 && app.projects.numProjects > 0; guard++) {
        var pj = app.projects[app.projects.numProjects - 1];
        try { pj.closeDocument(0, 0); closed++; }   // 저장 안 함, 물어보지도 않음
        catch (e) { say("closeDocument_ERR", e.toString()); break; }
    }
    say("닫은 프로젝트 수", closed);
    say("닫은 뒤 열린 수", app.projects.numProjects);

    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m4_src") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("열기 대기", w + "s");
    say("project.path", app.project.path);
    say("before.numSequences", app.project.sequences.numSequences);
    say("before.rootItems", app.project.rootItem.children.numItems);

    function findSeq(n) {
        var s = app.project.sequences;
        for (var q = 0; q < s.numSequences; q++) if (s[q].name === n) return s[q];
        return null;
    }

    // ---- 의존 관계: 시퀀스의 projectItem nodeId 로 지도를 만든다 -----------
    var byNode = {};      // projectItem.nodeId -> 시퀀스 이름
    for (var i2 = 0; i2 < app.project.sequences.numSequences; i2++) {
        var sq = app.project.sequences[i2];
        try { byNode[sq.projectItem.nodeId] = sq.name; } catch (e) {}
    }
    say("시퀀스 nodeId 지도", (function () {
        var a = []; for (var k in byNode) a.push(k + "=" + byNode[k]); return a.join(" | ");
    })());

    // KEEP 에서 출발해 타임라인이 참조하는 시퀀스를 재귀로 모은다
    var keepSet = {}, queue = [KEEP];
    while (queue.length) {
        var name = queue.pop();
        if (keepSet[name]) continue;
        keepSet[name] = true;
        var seq = findSeq(name);
        if (!seq) continue;
        var colls = [seq.videoTracks, seq.audioTracks];
        for (var ci = 0; ci < colls.length; ci++) {
            var coll = colls[ci];
            for (var t = 0; t < coll.numTracks; t++) {
                var tr = coll[t];
                for (var c = 0; c < tr.clips.numItems; c++) {
                    var pi = null;
                    try { pi = tr.clips[c].projectItem; } catch (e) {}
                    if (!pi) continue;
                    var nested = byNode[pi.nodeId];
                    if (nested && !keepSet[nested]) queue.push(nested);
                }
            }
        }
    }
    var keepList = [];
    for (var kk in keepSet) keepList.push(kk);
    say("남길 시퀀스", keepList.length + "개 :: " + keepList.join(" | "));

    function snapshot(seq, tag) {
        if (!seq) { say(tag, "(없음)"); return; }
        var clips = 0, named = [];
        for (var t2 = 0; t2 < seq.videoTracks.numTracks; t2++) {
            var tr2 = seq.videoTracks[t2];
            clips += tr2.clips.numItems;
            for (var c2 = 0; c2 < tr2.clips.numItems; c2++) {
                var p = null;
                try { p = tr2.clips[c2].projectItem; } catch (e) {}
                if (p) named.push(tr2.clips[c2].name);
            }
        }
        say(tag + ".videoClips", clips);
        say(tag + ".end", seq.end);
        say(tag + ".소스있는 클립", named.join(" | "));
    }
    snapshot(findSeq(KEEP), "before." + KEEP);

    // ---- 남길 것 빼고 지운다 -----------------------------------------------
    var doomed = [];
    for (var s2 = 0; s2 < app.project.sequences.numSequences; s2++) {
        var nm = app.project.sequences[s2].name;
        if (!keepSet[nm]) doomed.push(nm);
    }
    say("지울 시퀀스", doomed.length + "개 :: " + doomed.join(" | "));

    var killed = 0, failed = [];
    for (var d = 0; d < doomed.length; d++) {
        var target = null, sc = app.project.sequences;
        for (var e2 = 0; e2 < sc.numSequences; e2++) if (sc[e2].name === doomed[d]) { target = sc[e2]; break; }
        if (!target) { failed.push(doomed[d] + "(못 찾음)"); continue; }
        var b4 = app.project.sequences.numSequences;
        try { app.project.deleteSequence(target); }
        catch (err) { failed.push(doomed[d] + "(" + err.toString() + ")"); continue; }
        if (app.project.sequences.numSequences === b4 - 1) killed++;
        else failed.push(doomed[d] + "(안 줄었다)");
    }
    say("지운 수", killed);
    say("실패", failed.length ? failed.join(" | ") : "(없음)");
    say("after.numSequences", app.project.sequences.numSequences);

    snapshot(findSeq(KEEP), "after." + KEEP);
    probe("after.rootItems", function () { return app.project.rootItem.children.numItems; });

    // ---- 저장. 반환값을 반드시 본다 ----------------------------------------
    var outFile = new File(OUT);
    say("대상 파일 이미 있나", String(outFile.exists));
    var ok = false;
    probe("saveAs", function () { ok = app.project.saveAs(OUT); return ok; });
    if (!ok) {
        // 대상이 열려 있어 잠긴 경우가 있다. 다른 이름으로 한 번 더.
        var ALT = "C:/pprolab/m4_out2.prproj";
        say("saveAs 실패", "대상이 잠긴 것으로 보인다. " + ALT + " 로 재시도");
        probe("saveAs(ALT)", function () { ok = app.project.saveAs(ALT); return ok; });
        if (ok) OUT = ALT;
    }
    say("최종 저장 경로", OUT);
    say("out_size", new File(OUT).exists ? new File(OUT).length : "(없음)");
    say("project.path_after", app.project.path);
    return done("m4_cleanup " + (ok ? "ok" : "FAILED") + " — 시퀀스 -> " +
                app.project.sequences.numSequences);
})();
