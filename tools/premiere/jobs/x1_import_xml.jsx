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

    function readLines(p) {
        var f = new File(p), a = [];
        if (!f.exists) return a;
        f.encoding = "UTF-8";
        f.open("r");
        while (!f.eof) {
            var s = f.readln();
            if (s) { s = String(s).replace(/^\s+|\s+$/g, ""); if (s) a.push(s); }
        }
        f.close();
        return a;
    }

    var lines = readLines(LAB + "/x1_input.txt");
    var xml = lines.length > 0 ? lines[0] : "";
    var srt = lines.length > 1 ? lines[1] : "";   // 둘째 줄이 있으면 자막도 넣는다
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
    //  마커가 시퀀스에 들어왔는지 (E 요청 2026-10-01)
    probe("seq0_markers", function () {
        var s = app.project.sequences[0], m = s.markers, a = [];
        var n = m.numMarkers;
        var cur = m.getFirstMarker();
        while (cur && a.length < 20) {
            a.push(cur.name + "@" + Math.round(cur.start.seconds * 100) / 100 + "초");
            cur = m.getNextMarker(cur);
        }
        return n + "개 — " + a.join(" / ");
    });
    //  꺼둔 클립(enabled=FALSE)이 살아 들어왔는지
    probe("disabled_clips", function () {
        var s = app.project.sequences[0], off = 0, on = 0;
        for (var i = 0; i < s.videoTracks.numTracks; i++) {
            var t = s.videoTracks[i];
            for (var j = 0; j < t.clips.numItems; j++) {
                if (t.clips[j].isSelected === undefined) { }
                try { (t.clips[j].disabled ? off++ : on++); } catch (e) { on++; }
            }
        }
        return "켠 것 " + on + " · 끈 것 " + off;
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

    //== 자막(.srt) — 둘째 줄이 있으면 같은 프로젝트에 넣고 캡션으로 들어왔는지 본다 =====
    if (srt) {
        say("srt", srt);
        say("srt_exists", String(new File(srt).exists));
        var itemsBefore = app.project.rootItem.children.numItems;
        probe("importSRT", function () {
            return app.project.importFiles([srt], true, app.project.rootItem, false);
        });
        $.sleep(2000);
        probe("rootItems_srt", function () {
            return itemsBefore + " → " + app.project.rootItem.children.numItems;
        });
        probe("srt_item", function () {
            var r = app.project.rootItem, a = [];
            for (var i = 0; i < r.children.numItems; i++) {
                var it = r.children[i];
                if (String(it.name).toLowerCase().indexOf(".srt") >= 0 ||
                    String(it.name).indexOf("캠_컷") >= 0) {
                    var t = "?";
                    try { t = it.type; } catch (e) {}
                    a.push(it.name + "(type=" + t + ")");
                }
            }
            return a.join(" / ");
        });
        //  시퀀스에 캡션 트랙이 생기는 길이 있는지 — 버전마다 이름이 다르다. 있는 것만 적는다.
        probe("caption_api", function () {
            var s = app.project.sequences[0], a = [];
            var names = ["captionTracks", "createCaptionTrack", "getCaptionTrackCount",
                         "addCaptionTrack", "captions"];
            for (var i = 0; i < names.length; i++) {
                a.push(names[i] + "=" + (typeof s[names[i]]));
            }
            return a.join(" ");
        });
        probe("seq_members", function () {
            var s = app.project.sequences[0], a = [];
            for (var k in s) a.push(k);
            a.sort();
            return a.join(",");
        });
        probe("caption_count", function () {
            var s = app.project.sequences[0];
            if (s.captionTracks) return "captionTracks.numTracks=" + s.captionTracks.numTracks;
            if (typeof s.getCaptionTrackCount === "function") return "getCaptionTrackCount=" + s.getCaptionTrackCount();
            return "(캡션 트랙 API 없음)";
        });

        //  실제로 캡션 트랙을 만들어 붙여 본다 (createCaptionTrack 이 있다 — 2026-10-01 실측)
        probe("createCaptionTrack", function () {
            var s = app.project.sequences[0], r = app.project.rootItem, item = null;
            for (var i = 0; i < r.children.numItems; i++) {
                if (String(r.children[i].name).toLowerCase().indexOf(".srt") >= 0) item = r.children[i];
            }
            if (!item) return "자막 항목을 못 찾음";
            say("createCaptionTrack_arity", String(s.createCaptionTrack.length));
            return String(s.createCaptionTrack(item, 0));
        });
        $.sleep(2000);
        probe("after_caption", function () {
            var s = app.project.sequences[0];
            return "V" + s.videoTracks.numTracks + "/A" + s.audioTracks.numTracks +
                   " · 시퀀스 멤버에 caption 있나: " + (typeof s.captionTracks);
        });
    }

    //  사람이 눈으로 볼 수 있게 시퀀스를 타임라인에 열고 저장해 둔다
    probe("openSequence", function () {
        return String(app.project.openSequence(app.project.sequences[0].sequenceID));
    });
    probe("save", function () { app.project.save(); return "saved"; });

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
