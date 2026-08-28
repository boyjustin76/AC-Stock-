/*
    M6 프로브 — 시퀀스를 처음부터 만들 수 있는가.

    지금까지는 회사 프리셋 시퀀스를 복제해서 손봤다. 이번엔 **빈 시퀀스를 새로 만들고
    트랙을 층으로 쌓는다.** 필요한 것 셋을 확인한다.

      1. 시퀀스 생성 API 이름과 인자 (DOM / qe 둘 다)
      2. .sqpreset 을 먹는지 — 회사 timebase 는 30.0 인데 프리미어 기본 프리셋에는 30.0 이 없다.
         29.97 프리셋을 복사해 VideoFrameRate 만 8467200000 으로 바꾼 파일을 만들어 두었다.
      3. 만들어진 시퀀스의 timebase / 프레임 크기가 정말 그 값인지 (반환값 말고 실측)
*/
(function () {
    var PRESET_KO = "C:/Users/user/Desktop/이정찬/Claude/AC-Stock-/tools/premiere/presets/차트명가_1080p_30fps.sqpreset";
    var PRESET_ASCII = "C:/pprolab/cmg_1080p_30fps.sqpreset";

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m6_probe.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }

    say("프리셋(한글경로) 존재", new File(PRESET_KO).exists);
    /*  ExtendScript 가 한글 경로를 못 읽을 가능성에 대비해 ASCII 사본을 만들어 둔다  */
    try {
        var srcF = new File(PRESET_KO), dstF = new File(PRESET_ASCII);
        if (srcF.exists) say("ASCII 사본 복사", srcF.copy(PRESET_ASCII));
        say("프리셋(ASCII) 존재", new File(PRESET_ASCII).exists);
    } catch (e) { say("복사_ERR", e.toString()); }

    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); } catch (e) { break; }
    }

    /*  깨끗한 새 프로젝트에서 시험한다 — 프리셋 프로젝트를 건드리지 않는다  */
    var NEWPROJ = "C:/pprolab/m6_scratch.prproj";
    var old = new File(NEWPROJ); if (old.exists) old.remove();
    probe("newProject", function () { return app.newProject(NEWPROJ); });
    say("project.path", app.project ? app.project.path : "(없음)");
    say("시퀀스 수(처음)", app.project.sequences.numSequences);

    var api = ["createNewSequence", "newSequence", "createNewSequenceFromClips", "importSequences"];
    for (var a = 0; a < api.length; a++) say("typeof project." + api[a], typeof app.project[api[a]]);

    app.enableQE();
    if (typeof qe !== "undefined" && qe && qe.project) {
        var qapi = ["newSequence", "newBin", "getActiveSequence", "deleteSequence"];
        for (var b = 0; b < qapi.length; b++) say("typeof qe.project." + qapi[b], typeof qe.project[qapi[b]]);
    }

    function report(tag, seq) {
        if (!seq) { say(tag, "(시퀀스 없음)"); return; }
        var s = [];
        s.push("name=" + seq.name);
        try { s.push("timebase=" + seq.timebase); } catch (e) {}
        try { s.push("frameSize=" + seq.frameSizeHorizontal + "x" + seq.frameSizeVertical); } catch (e) {}
        try { s.push("V=" + seq.videoTracks.numTracks + " A=" + seq.audioTracks.numTracks); } catch (e) {}
        try { s.push("audioFrameRate=" + seq.audioFrameRate); } catch (e) {}
        say(tag, s.join("  "));
    }

    /*  ① DOM createNewSequence — 설정을 못 준다. 기본값이 무엇인지 본다  */
    probe("createNewSequence 호출", function () { return app.project.createNewSequence("A_기본", "a1b2c3d4-0001-0000-0000-000000000001"); });
    report("① A_기본", app.project.activeSequence);

    /*  ② qe.project.newSequence(name, presetPath)  */
    var before = app.project.sequences.numSequences;
    probe("qe.newSequence(ASCII 프리셋)", function () { return qe.project.newSequence("B_qe_30fps", PRESET_ASCII); });
    say("시퀀스 수", before + " -> " + app.project.sequences.numSequences);
    report("② B_qe_30fps", app.project.activeSequence);

    /*  ③ 한글 경로로도 되는지  */
    var before2 = app.project.sequences.numSequences;
    probe("qe.newSequence(한글 프리셋)", function () { return qe.project.newSequence("C_qe_한글경로", PRESET_KO); });
    say("시퀀스 수", before2 + " -> " + app.project.sequences.numSequences);
    report("③ C_qe_한글경로", app.project.activeSequence);

    /*  ④ 트랙을 층으로 쌓을 수 있는지 — 새로 만든 시퀀스에 5층  */
    var target = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name.indexOf("B_qe_30fps") === 0) target = app.project.sequences[i];
    if (target) {
        app.project.activeSequence = target;
        var qs = qe.project.getActiveSequence();
        var v0 = target.videoTracks.numTracks;
        probe("addTracks(+4)", function () { return qs.addTracks(4, v0, 0, 0, 0, 0, 0, 0); });
        say("V 트랙", v0 + " -> " + target.videoTracks.numTracks);
    }

    /*  전체 시퀀스 목록  */
    var names = [];
    for (var j = 0; j < app.project.sequences.numSequences; j++) {
        var sq = app.project.sequences[j];
        names.push(sq.name + "(tb=" + sq.timebase + ", " + sq.frameSizeHorizontal + "x" + sq.frameSizeVertical +
                   ", V" + sq.videoTracks.numTracks + ")");
    }
    say("만들어진 시퀀스", names.join("\n        "));

    return done("m6_probe ok");
})();
