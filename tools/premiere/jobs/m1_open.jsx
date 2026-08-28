/*
    M1-a. 프리셋 사본을 열고 무엇이 들어왔는지 잰다. 아직 아무것도 바꾸지 않는다.

    미디어 연결 대화상자를 억제하고 연다 — 프리셋 미디어 49개가 D:\ 를 가리키는데
    이 PC 는 G:\ 라 전부 오프라인이다. M1 은 구조만 보므로 오프라인이어도 된다.
    (되살리는 것은 M2 직전에 사람이 GUI 에서 한 번 한다.)
*/
(function () {
    var SRC = "C:/pprolab/src.prproj";
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function members(o) { var a = []; for (var k in o) a.push(k); a.sort(); return a.join(","); }

    probe("openDocument_arity", function () { return app.openDocument.length; });
    probe("project_before", function () { return app.project ? app.project.name : "(null)"; });

    // 인자가 남아도 ExtendScript 는 조용히 무시한다. 억제 플래그 자리를 전부 채운다.
    probe("openDocument_call", function () {
        return app.openDocument(SRC, 1, 1, 1, 1);
    });

    // 열기는 비동기다. 시퀀스가 들어올 때까지 기다린다.
    var waited = 0, seqs = 0;
    while (waited < 180) {
        try { seqs = app.project.sequences.numSequences; } catch (e) { seqs = 0; }
        if (seqs > 0) break;
        $.sleep(500);
        waited += 0.5;
    }
    say("waited_sec", waited);

    probe("project.name", function () { return app.project.name; });
    probe("project.path", function () { return app.project.path; });
    probe("numSequences", function () { return app.project.sequences.numSequences; });
    probe("numRootItems", function () { return app.project.rootItem.children.numItems; });

    // 시퀀스 목록 — 이름·id·길이. 복제 출발점을 성질로 고르기 위해서다 (§3-10)
    probe("sequences", function () {
        var s = app.project.sequences, a = [];
        for (var i = 0; i < s.numSequences; i++) {
            var q = s[i];
            var end = "?";
            try { end = q.end; } catch (e) {}
            a.push(i + "|" + q.name + "|id=" + q.sequenceID + "|end=" + end);
        }
        return a.join("\n\t\t");
    });

    // 시퀀스 객체의 멤버 — clone/duplicate 가 있는지 (§3-3 공개 API 부터 확인)
    probe("sequence_members", function () { return members(app.project.sequences[0]); });
    probe("sequences_members", function () { return members(app.project.sequences); });
    probe("rootItem_members", function () { return members(app.project.rootItem); });
    probe("projectManager_members", function () { return members(app.projectManager); });

    // 쓰기 계열 이름을 직접 찍어 본다 (열거에 안 잡히는 것이 있다 — probe 에서 실측)
    var wanted = ["clone", "duplicate", "createSubsequence", "exportAsProject", "close",
                  "save", "saveAs", "importSequences", "getSettings", "setSettings", "videoTracks", "audioTracks"];
    for (var w = 0; w < wanted.length; w++) {
        (function (n) {
            probe("seq." + n, function () { return typeof app.project.sequences[0][n]; });
        })(wanted[w]);
    }
    var pw = ["save", "saveAs", "closeDocument", "importFiles", "createNewSequence", "openSequence"];
    for (var v = 0; v < pw.length; v++) {
        (function (n) { probe("project." + n, function () { return typeof app.project[n]; }); })(pw[v]);
    }

    // 오프라인 실태 (§3-8 잠금·오프라인부터 파악)
    probe("offline_count", function () {
        var n = 0, total = 0;
        function walk(item) {
            for (var i = 0; i < item.children.numItems; i++) {
                var c = item.children[i];
                if (c.type === 2 /* BIN */) { walk(c); continue; }
                total++;
                try { if (c.isOffline && c.isOffline()) n++; } catch (e) {}
            }
        }
        walk(app.project.rootItem);
        return n + " / " + total;
    });

    var f = new File("C:/pprolab/m1_open.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    return "m1_open ok, " + out.length + " lines, seqs=" + seqs;
})();
