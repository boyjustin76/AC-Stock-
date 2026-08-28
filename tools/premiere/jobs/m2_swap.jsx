/*
    M2. 복제한 시퀀스 안의 클립 하나를 렌더러가 뽑은 차트 png 로 교체한다.

    함정: 복제 시퀀스는 마스터 클립(projectItem)을 원본과 공유한다 — M2 프로브에서
    복제본의 nodeId 15개가 원본과 전부 같았다. 그래서 공유 항목에 changeMediaPath()
    를 걸면 원본 시퀀스까지 같이 바뀐다. 격리되는 길부터 순서대로 시도하고,
    어느 길로 됐는지 기록한다.

      1) 차트를 새 projectItem 으로 import 한 뒤 clip.projectItem 에 직접 물린다
         (되면 완전 격리. 클립의 이펙트·키프레임은 클립에 붙어 있으니 그대로 남는다)
      2) 안 되면 공유 항목에 changeMediaPath() — 원본도 같이 바뀐다는 사실을 기록한다

    교체 대상은 인덱스가 아니라 성질로 찾는다 (§3-10): 미디어 경로가
    TARGET_SUFFIX 로 끝나는 클립.
*/
(function () {
    var SRC           = "C:/pprolab/m2_src.prproj";
    var OUT           = "C:/pprolab/m2_out.prproj";
    var CLONE         = "롱폼 고정 양식 복사";
    var BASE          = "롱폼 고정 양식";
    var TARGET_SUFFIX = "차10_1-5.png";
    var CHART         = "C:/cmgwork/chartA.png";

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(msg) {
        var f = new File("C:/pprolab/m2_swap.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return msg;
    }

    if (!new File(CHART).exists) return done("m2_swap FAILED: 차트가 없다 " + CHART);

    // ---- 열기 ----------------------------------------------------------
    var opened = false;
    try { opened = (app.project && app.project.path && app.project.path.indexOf("m2_src") >= 0); } catch (e) {}
    if (!opened) {
        app.openDocument(SRC, 1, 1, 1, 1);
        var w = 0;
        while (w < 180 && !(app.project && app.project.path.indexOf("m2_src") >= 0
                            && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    }
    say("project.path", app.project.path);

    function findSeq(name) {
        var s = app.project.sequences;
        for (var i = 0; i < s.numSequences; i++) if (s[i].name === name) return s[i];
        return null;
    }
    var clone = findSeq(CLONE), base = findSeq(BASE);
    if (!clone) return done("m2_swap FAILED: 복제 시퀀스 없음 " + CLONE);

    // ---- 잠금부터 푼다 (§3-8) -------------------------------------------
    var unlocked = [];
    function unlock(coll, tag) {
        for (var t = 0; t < coll.numTracks; t++) {
            try { if (coll[t].isLocked()) { unlocked.push(tag + t); coll[t].setLocked(0); } } catch (e) {}
        }
    }
    unlock(clone.videoTracks, "V");
    unlock(clone.audioTracks, "A");
    say("unlocked", unlocked.length ? unlocked.join(",") : "(잠긴 트랙 없음)");

    // ---- 대상 찾기 (성질로) ---------------------------------------------
    function findClip(seq) {
        for (var t = 0; t < seq.videoTracks.numTracks; t++) {
            var tr = seq.videoTracks[t];
            for (var c = 0; c < tr.clips.numItems; c++) {
                var cl = tr.clips[c], pi = null;
                try { pi = cl.projectItem; } catch (e) {}
                if (!pi) continue;
                var mp = "";
                try { mp = pi.getMediaPath(); } catch (e) { continue; }
                if (mp && mp.length >= TARGET_SUFFIX.length &&
                    mp.substr(mp.length - TARGET_SUFFIX.length) === TARGET_SUFFIX) {
                    return { clip: cl, item: pi, track: t, idx: c, path: mp };
                }
            }
        }
        return null;
    }
    var hit = findClip(clone);
    if (!hit) return done("m2_swap FAILED: 대상 클립 없음 (" + TARGET_SUFFIX + ")");
    say("대상", "V" + hit.track + "[" + hit.idx + "] " + hit.clip.name);
    say("대상.nodeId", hit.item.nodeId);
    say("대상.경로_before", hit.path);

    // 원본 쪽에도 같은 항목이 쓰이는지
    var baseHit = base ? findClip(base) : null;
    say("원본에도_같은_항목", baseHit ? (baseHit.item.nodeId === hit.item.nodeId ? "예 (공유)" : "아니오") : "(원본 시퀀스 없음)");

    // ---- BEFORE 상태 ----------------------------------------------------
    function dumpClip(cl, tag) {
        say(tag + ".name", cl.name);
        say(tag + ".start", cl.start.ticks);
        say(tag + ".end", cl.end.ticks);
        say(tag + ".duration", cl.duration.ticks);
        say(tag + ".inPoint", cl.inPoint.ticks);
        say(tag + ".outPoint", cl.outPoint.ticks);
        try {
            for (var ci = 0; ci < cl.components.numItems; ci++) {
                var cm = cl.components[ci], ps = [];
                for (var pj = 0; pj < cm.properties.numItems; pj++) {
                    var pr = cm.properties[pj], v = "?", kf = "?";
                    try { v = pr.getValue(); } catch (e) {}
                    try { kf = pr.isTimeVarying() ? "KF" : "-"; } catch (e) {}
                    ps.push(pr.displayName + "=" + v + "(" + kf + ")");
                }
                say(tag + ".component[" + ci + "]", cm.displayName + " :: " + ps.join(" · "));
            }
        } catch (e) { say(tag + ".components_ERR", e.toString()); }
    }
    dumpClip(hit.clip, "BEFORE");

    // ---- 시도 1: 새 projectItem 을 import 해서 클립에 직접 물린다 --------
    var before = app.project.rootItem.children.numItems;
    probe("importFiles", function () {
        return app.project.importFiles([CHART], 1, app.project.rootItem, 0);
    });
    var after = app.project.rootItem.children.numItems;
    say("rootItem_children", before + " -> " + after);

    var newItem = null;
    for (var i = after - 1; i >= 0; i--) {
        var ch = app.project.rootItem.children[i];
        var p = "";
        try { p = ch.getMediaPath(); } catch (e) {}
        if (p && p.replace(/\\/g, "/").toLowerCase() === CHART.toLowerCase()) { newItem = ch; break; }
    }
    say("새 항목", newItem ? (newItem.name + " node=" + newItem.nodeId) : "(못 찾음)");

    var route = "";
    if (newItem) {
        probe("시도1_clip.projectItem_대입", function () {
            hit.clip.projectItem = newItem;
            var got = hit.clip.projectItem;
            return got ? got.nodeId : "(null)";
        });
        var nowPath = "";
        try { nowPath = hit.clip.projectItem.getMediaPath(); } catch (e) {}
        say("시도1_결과경로", nowPath);
        if (nowPath.replace(/\\/g, "/").toLowerCase() === CHART.toLowerCase()) route = "clip.projectItem 대입";
    }

    // ---- 시도 2: 공유 항목에 changeMediaPath ------------------------------
    if (!route) {
        say("시도1", "실패 — clip.projectItem 은 읽기 전용이다");
        probe("canChangeMediaPath", function () { return hit.item.canChangeMediaPath(CHART); });
        probe("changeMediaPath", function () { return hit.item.changeMediaPath(CHART); });
        var p2 = "";
        try { p2 = hit.item.getMediaPath(); } catch (e) {}
        say("시도2_결과경로", p2);
        if (p2.replace(/\\/g, "/").toLowerCase() === CHART.toLowerCase()) route = "changeMediaPath (공유 — 원본도 바뀐다)";
    }
    say("성공 경로", route || "(둘 다 실패)");
    if (!route) return done("m2_swap FAILED: 교체 경로를 못 찾았다");

    // ---- AFTER 상태 ------------------------------------------------------
    var again = findClip(clone);   // 경로가 바뀌었으니 이제 못 찾는 게 정상
    say("대상_재검색(옛 경로)", again ? "아직 있다 — 교체 안 됨" : "없다 (교체됨)");
    // 트랙·인덱스로 다시 잡는다
    var after_clip = clone.videoTracks[hit.track].clips[hit.idx];
    dumpClip(after_clip, "AFTER");
    probe("AFTER.mediaPath", function () { return after_clip.projectItem.getMediaPath(); });
    probe("원본쪽_경로", function () {
        var b = base ? base.videoTracks[hit.track].clips[hit.idx] : null;
        return b && b.projectItem ? b.projectItem.getMediaPath() : "(없음)";
    });

    // ---- 저장 ------------------------------------------------------------
    probe("saveAs", function () { return app.project.saveAs(OUT); });
    say("project.path_after", app.project.path);
    return done("m2_swap ok — 경로: " + route);
})();
