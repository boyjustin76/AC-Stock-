/*
    M4-b. §3-9 의 나머지 절반 — 미사용 애셋을 지운다.

    m4_cleanup 으로 시퀀스는 정리됐지만 고유 미디어 경로는 50 그대로였다.
    projectItem 에는 삭제 함수가 없다 (`delete`·`remove` 둘 다 undefined, 실측).
    있는 것은 `createBin` · `moveBin` · `deleteBin` 셋이다 —
    **미사용 항목을 빈 하나로 몰아넣고 그 빈을 지운다.**

    안전장치: 지우기 전에 무엇을 지울지 전부 적는다. 남은 시퀀스가 쓰는 것과
    시퀀스 자신의 projectItem 은 절대 건드리지 않는다.
*/
(function () {
    var SRC = "C:/pprolab/m4_purge_src.prproj";
    var OUT = "C:/pprolab/m4_purged.prproj";
    var TRASH = "_지울것";

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m4_purge.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }

    // 열린 프로젝트를 전부 닫는다 — 안 그러면 디스크를 갈아도 옛 메모리 상태를 본다
    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; }
        catch (e) { say("closeDocument_ERR", e.toString()); break; }
    }
    say("닫은 프로젝트", closed);

    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m4_purge_src") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);
    say("before.numSequences", app.project.sequences.numSequences);

    // ---- 쓰이는 nodeId 를 모은다 -------------------------------------------
    var used = {};
    for (var s = 0; s < app.project.sequences.numSequences; s++) {
        var seq = app.project.sequences[s];
        try { used[seq.projectItem.nodeId] = "시퀀스 자신: " + seq.name; } catch (e) {}
        var colls = [seq.videoTracks, seq.audioTracks];
        for (var ci = 0; ci < colls.length; ci++) {
            for (var t = 0; t < colls[ci].numTracks; t++) {
                var tr = colls[ci][t];
                for (var c = 0; c < tr.clips.numItems; c++) {
                    var pi = null;
                    try { pi = tr.clips[c].projectItem; } catch (e) {}
                    if (pi) used[pi.nodeId] = seq.name + " / " + tr.clips[c].name;
                }
            }
        }
    }
    var usedN = 0; for (var u in used) usedN++;
    say("쓰이는 projectItem", usedN + "개");

    // ---- 전체 항목을 훑어 미사용을 고른다 -----------------------------------
    var all = [], types = {};
    function walk(item, path) {
        for (var i = 0; i < item.children.numItems; i++) {
            var ch = item.children[i];
            var ty = -1;
            try { ty = ch.type; } catch (e) {}
            types[ty] = (types[ty] || 0) + 1;
            if (ty === 2) { walk(ch, path + ch.name + "/"); continue; }   // BIN
            all.push({ item: ch, name: ch.name, node: ch.nodeId, path: path });
        }
    }
    walk(app.project.rootItem, "");
    say("type 분포", (function () { var a = []; for (var k in types) a.push(k + ":" + types[k]); return a.join(" "); })());
    say("전체 비-빈 항목", all.length);

    var doomed = [], kept = [];
    for (var a2 = 0; a2 < all.length; a2++) {
        if (used[all[a2].node]) kept.push(all[a2].name);
        else doomed.push(all[a2]);
    }
    say("남길 항목", kept.length + "개 :: " + kept.join(" | "));
    say("지울 항목", doomed.length + "개 :: " + (function () {
        var a = []; for (var i = 0; i < doomed.length; i++) a.push(doomed[i].path + doomed[i].name);
        return a.join(" | ");
    })());

    if (!doomed.length) return done("m4_purge — 지울 것이 없다");

    // ---- 빈으로 몰아넣고 빈째로 지운다 --------------------------------------
    var trash = null;
    probe("createBin", function () { trash = app.project.rootItem.createBin(TRASH); return trash ? trash.name : "(null)"; });
    if (!trash) return done("m4_purge FAILED: 빈을 못 만들었다");

    var moved = 0, moveFail = [];
    for (var d = 0; d < doomed.length; d++) {
        try { doomed[d].item.moveBin(trash); moved++; }
        catch (e) { moveFail.push(doomed[d].name + "(" + e.toString() + ")"); }
    }
    say("빈으로 옮긴 수", moved);
    say("옮기기 실패", moveFail.length ? moveFail.join(" | ") : "(없음)");
    say("빈 안 항목 수", trash.children.numItems);

    var beforeRoot = app.project.rootItem.children.numItems;
    probe("deleteBin", function () { trash.deleteBin(); return "ok"; });
    say("rootItems", beforeRoot + " -> " + app.project.rootItem.children.numItems);
    say("after.numSequences", app.project.sequences.numSequences);

    // 남은 시퀀스가 멀쩡한지
    for (var s3 = 0; s3 < app.project.sequences.numSequences; s3++) {
        var sq = app.project.sequences[s3], n = 0;
        for (var t3 = 0; t3 < sq.videoTracks.numTracks; t3++) n += sq.videoTracks[t3].clips.numItems;
        say("after.시퀀스 " + sq.name, n + " 비디오 클립 · end=" + sq.end);
    }

    var ok = false;
    probe("saveAs", function () { ok = app.project.saveAs(OUT); return ok; });
    say("out_size", new File(OUT).exists ? new File(OUT).length : "(없음)");
    return done("m4_purge " + (ok ? "ok" : "FAILED") + " — 항목 " + all.length + " -> " + (all.length - moved));
})();
