/*
    X1. FCP7 XML 을 프리미어가 받는지 **실제로** 넣어 본다.

    왜: 우리가 만든 시퀀스 XML 을 프리미어가 "프로젝트가 손상되어 열 수 없습니다" 로 거부한다는
    보고가 있었다(E 세션, 마01 캠). 명령줄로는 .xml 을 못 연다(프로젝트 열기만 받는다) —
    그래서 스크립트로 **가져오기(importFiles)** 를 시킨다. 사람이 메뉴를 누르는 것과 같은 길이다.

    넣을 파일은 환경변수가 아니라 <실험실>/x1_input.txt 첫 줄에서 읽는다 (경로에 한글이 있어도 안전).
    결과는 run.ps1 이 보는 _result.txt 와 같은 꼴로 적는다.
*/
$.evalFile(new File(String(new File($.fileName).parent.parent.fsName).split(String.fromCharCode(92)).join("/") + "/_labdir.jsx"));
var LAB = labDirPath();
(function () {
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }

    function readFirstLine(p) {
        var f = new File(p);
        if (!f.exists) return "";
        f.encoding = "UTF-8";
        f.open("r");
        var s = f.readln();
        f.close();
        return s ? String(s).replace(/^\s+|\s+$/g, "") : "";
    }

    var xml = readFirstLine(LAB + "/x1_input.txt");
    say("xml", xml);
    say("xml_exists", String(new File(xml).exists));

    // 1) 빈 프로젝트를 새로 만든다 (회사 프로젝트는 건드리지 않는다)
    var proj = LAB + "/x1_test.prproj";
    try { var old = new File(proj); if (old.exists) old.remove(); } catch (e) {}
    probe("newProject", function () { return app.newProject(proj); });

    var waited = 0;
    while (waited < 30 && !app.project) { $.sleep(500); waited += 0.5; }
    probe("project.name", function () { return app.project.name; });

    var before = 0;
    try { before = app.project.sequences.numSequences; } catch (e) {}
    say("seq_before", before);

    // 2) 가져오기
    probe("importFiles", function () {
        return app.project.importFiles([xml], true, app.project.rootItem, false);
    });

    // 가져오기는 비동기일 수 있다 — 시퀀스가 생길 때까지 기다린다
    waited = 0;
    var seqs = before;
    while (waited < 60) {
        try { seqs = app.project.sequences.numSequences; } catch (e) {}
        if (seqs > before) break;
        $.sleep(500);
        waited += 0.5;
    }
    say("waited_sec", waited);
    say("seq_after", seqs);

    probe("numRootItems", function () { return app.project.rootItem.children.numItems; });
    probe("seq_names", function () {
        var a = [];
        for (var i = 0; i < app.project.sequences.numSequences; i++) a.push(app.project.sequences[i].name);
        return a.join(" | ");
    });
    probe("seq0_clips", function () {
        var s = app.project.sequences[0];
        var v = 0, au = 0;
        for (var i = 0; i < s.videoTracks.numTracks; i++) v += s.videoTracks[i].clips.numItems;
        for (var j = 0; j < s.audioTracks.numTracks; j++) au += s.audioTracks[j].clips.numItems;
        return "video=" + v + " audio=" + au + " 트랙 V" + s.videoTracks.numTracks + "/A" + s.audioTracks.numTracks;
    });
    probe("seq0_end", function () {
        return app.project.sequences[0].end;
    });
    //  미디어가 실제로 붙었는지 (오프라인이면 '미디어 연결' 창이 뜬다)
    probe("media", function () {
        var r = app.project.rootItem, a = [];
        for (var i = 0; i < r.children.numItems; i++) {
            var it = r.children[i];
            if (it.type !== 1 /* CLIP */) continue;
            var off = "?";
            try { off = String(it.isOffline()); } catch (e) {}
            var mp = "";
            try { mp = it.getMediaPath(); } catch (e) {}
            a.push(it.name + " 오프라인=" + off + " 경로=" + mp);
        }
        return a.join(" / ");
    });

    var ok = (seqs > before);
    var verdict = (ok ? "OK 가져오기 성공" : "FAIL 시퀀스가 안 생겼다") + " · 시퀀스 " + seqs + "개";
    say("판정", verdict);

    //  _result.txt 는 실행기가 쓴다 — 우리 보고는 따로 남긴다.
    var f = new File(LAB + "/x1_report.txt");
    f.encoding = "UTF-8";
    f.open("w");
    f.write(out.join("\n") + "\n");
    f.close();
    return "판정: " + verdict;
})();
