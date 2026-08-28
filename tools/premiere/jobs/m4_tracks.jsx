/* 복제 시퀀스의 각 비디오 트랙이 0~16초 구간에서 비어 있는지 본다. 아무것도 바꾸지 않는다. */
(function () {
    var P = "C:/pprolab/m4_place_src.prproj";
    var TICKS = 254016000000, WIN_END = 16 * TICKS;
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }

    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; } catch (e) { break; }
    }
    app.openDocument(P, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m4_place_src") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }

    var seq = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name === "롱폼 고정 양식 복사") seq = app.project.sequences[i];

    for (var t = 0; t < seq.videoTracks.numTracks; t++) {
        var tr = seq.videoTracks[t], hits = [];
        for (var c = 0; c < tr.clips.numItems; c++) {
            var cl = tr.clips[c];
            if (Number(cl.start.ticks) < WIN_END) {
                hits.push(cl.name + "@" + (Number(cl.start.ticks) / TICKS).toFixed(2) + "~" +
                          (Number(cl.end.ticks) / TICKS).toFixed(2) + "s");
            }
        }
        say("V" + t, (hits.length ? hits.length + "개 :: " + hits.join(" | ") : "0~16초 비어 있음") +
            "   (트랙 전체 " + tr.clips.numItems + "개)");
    }
    var f = new File("C:/pprolab/m4_tracks.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    return "m4_tracks ok";
})();
