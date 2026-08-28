/*
    M5-c2. exportFramePNG 가 'Unknown error exception' 을 던진다. 원인을 좁힌다.
    한 시점(6초)에 대해 조합을 바꿔 가며 시도하고, 무엇이 먹는지 남긴다.
*/
(function () {
    var SRC = "C:/pprolab/m5_intro.prproj";
    var DIR = "C:/pprolab/frames";
    var BS = String.fromCharCode(92);
    var CLONE = "롱폼 고정 양식 복사";

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function done(m) {
        var f = new File("C:/pprolab/m5_frames2.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }

    var d = new Folder(DIR); if (!d.exists) d.create();
    say("폴더", DIR + " exists=" + new Folder(DIR).exists);

    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); } catch (e) { break; }
    }
    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m5_intro") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);

    var seq = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name === CLONE) seq = app.project.sequences[i];
    if (!seq) return done("FAILED: 복제 시퀀스 없음");
    app.project.activeSequence = seq;

    app.enableQE();
    var qs = qe.project.getActiveSequence();
    say("qs.name", qs.name);
    try { say("qs.makeCurrent()", String(qs.makeCurrent())); } catch (e) { say("makeCurrent_ERR", e.toString()); }
    try { say("qs.getSettings().videoFrameRate", String(qs.getSettings().videoFrameRate)); } catch (e) {}
    try { say("qs.CTI", String(qs.CTI.timecode)); } catch (e) { say("CTI_ERR", e.toString()); }

    var slash = DIR + "/t_slash.png";
    var back  = DIR.split("/").join(BS) + BS + "t_back.png";

    var TC = "00:00:06:00";
    var cases = [
        ["슬래시 경로",        function () { return qs.exportFramePNG(TC, slash); }],
        ["역슬래시 경로",      function () { return qs.exportFramePNG(TC, back); }],
        ["프레임 번호",        function () { return qs.exportFramePNG(180, back); }],
        ["인자 순서 뒤집기",   function () { return qs.exportFramePNG(back, TC); }],
        ["JPEG",              function () { return qs.exportFrameJPEG(TC, DIR.split("/").join(BS) + BS + "t.jpg"); }],
        ["TIFF",              function () { return qs.exportFrameTIFF(TC, DIR.split("/").join(BS) + BS + "t.tif"); }],
        ["Targa",             function () { return qs.exportFrameTarga(TC, DIR.split("/").join(BS) + BS + "t.tga"); }],
        ["CTI 이동 후 PNG",    function () { qs.setCTI(TC); return qs.exportFramePNG(TC, back); }]
    ];

    for (var c = 0; c < cases.length; c++) {
        var r = "?";
        try { r = String(cases[c][1]()); } catch (e) { r = "ERR " + e.toString(); }
        var made = [];
        var ff = new Folder(DIR).getFiles();
        for (var q = 0; q < ff.length; q++) made.push(ff[q].name);
        say(cases[c][0], "ret=" + r + "  폴더=" + made.join(","));
    }

    return done("m5_frames2 ok");
})();
