/*
    M5-c. 합성 결과를 프레임으로 뽑는다.

    파일을 뜯어 키프레임과 트랙을 확인하는 것만으로는 '차트가 프리셋 그래픽에 가려지는지'
    를 알 수 없다. 스택 순서는 맞아도 위 트랙에 전면 배경(종이 배경 등)이 깔려 있으면
    차트가 안 보인다. 그건 합성해 봐야 안다.

    qe 층의 exportFramePNG 가 있는지 먼저 보고, 있으면 컷마다 여러 시점을 뽑는다.
    없으면 대안 API 이름을 전부 찍어서 남긴다.
*/
(function () {
    var SRC = "C:/pprolab/m5_intro2.prproj";
    var DIR = "C:/pprolab/frames";
    var CLONE = "롱폼 고정 양식 복사";
    var TICKS = 254016000000;

    /*  컷 경계 직후·중간·직전을 고루 본다. 모션이 걸린 구간이라 값이 변한다  */
    var SHOTS = [3.45, 4.60, 5.80, 6.60, 7.30, 8.50, 10.50, 12.10, 12.40, 13.20, 13.70, 14.20, 15.00, 15.45];

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m5_frames.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }

    var d = new Folder(DIR); if (!d.exists) d.create();

    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; }
        catch (e) { say("closeDocument_ERR", e.toString()); break; }
    }
    say("닫은 프로젝트", closed);

    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m5_intro2") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);

    var seq = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name === CLONE) seq = app.project.sequences[i];
    if (!seq) return done("FAILED: 복제 시퀀스 없음");
    app.project.activeSequence = seq;

    app.enableQE();
    if (typeof qe === "undefined" || !qe) return done("FAILED: qe 없음");
    var qs = qe.project.getActiveSequence();

    /*  어떤 이름으로 뽑을 수 있는지 먼저 남긴다 — 다음에 헤매지 않게  */
    var names = ["exportFramePNG", "exportFrameJPEG", "exportFrameTIFF", "exportFrameDPX",
                 "exportFrameTarga", "getExportFileExtension", "exportDirect"];
    for (var n = 0; n < names.length; n++) say("typeof qs." + names[n], typeof qs[names[n]]);
    say("typeof seq.exportAsMediaDirect", typeof seq.exportAsMediaDirect);

    if (typeof qs.exportFramePNG !== "function")
        return done("FAILED: exportFramePNG 가 없다 — 위 목록 보고 다른 길 찾아라");

    /*  시각은 타임코드 문자열로 준다. 시퀀스 timebase 는 30.0 (실측)  */
    function tc(sec) {
        var f = Math.round(sec * 30);
        var ss = Math.floor(f / 30), ff = f % 30;
        var mm = Math.floor(ss / 60); ss = ss % 60;
        var hh = Math.floor(mm / 60); mm = mm % 60;
        function p(x) { return (x < 10 ? "0" : "") + x; }
        return p(hh) + ":" + p(mm) + ":" + p(ss) + ":" + p(ff);
    }

    try { qs.makeCurrent(); } catch (e) { say("makeCurrent_ERR", e.toString()); }

    var okCnt = 0;
    for (var s = 0; s < SHOTS.length; s++) {
        var sec = SHOTS[s];
        /*  실측(m5_frames2): 경로에 슬래시를 쓰면 'Unknown error exception' 이 난다.
            역슬래시여야 하고, 확장자는 함수가 알아서 붙이므로 주면 안 된다 (t.png -> t.png.png).  */
        var name = (sec < 10 ? "0" : "") + sec.toFixed(2).replace(".", "_") + "s";
        var path = DIR.split("/").join(String.fromCharCode(92)) + String.fromCharCode(92) + name;
        var t = tc(sec);
        var r = "?";
        try { r = String(qs.exportFramePNG(t, path)); } catch (e) { r = "ERR " + e.toString(); }
        var f2 = new File(path + ".png");
        var made = f2.exists;
        if (made) okCnt++;
        say(sec.toFixed(2) + "s", "tc=" + t + "  ret=" + r + "  " + (made ? f2.length + "바이트" : "파일없음"));
    }
    say("뽑은 프레임", okCnt + " / " + SHOTS.length);
    return done("m5_frames " + (okCnt > 0 ? "ok" : "FAILED"));
})();
