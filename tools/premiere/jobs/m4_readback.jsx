/* M4 되읽기. 저장본 사본을 새로 열어 컷 배치가 파일에 박혔는지 본다 (§3-5). */
(function () {
    var P = "C:/pprolab/m4_readback.prproj";
    var TICKS = 254016000000;
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }

    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; } catch (e) { break; }
    }
    say("닫은 프로젝트", closed);
    app.openDocument(P, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m4_readback") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);
    say("numSequences", app.project.sequences.numSequences);

    var seq = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name === "롱폼 고정 양식 복사") seq = app.project.sequences[i];
    if (!seq) { say("FATAL", "복제 시퀀스 없음"); }

    var tr = seq.videoTracks[6];
    for (var c = 0; c < tr.clips.numItems; c++) {
        var cl = tr.clips[c], mp = "(없음)";
        try { mp = cl.projectItem.getMediaPath(); } catch (e) {}
        say("V6[" + c + "]", cl.name +
            "  " + cl.start.ticks + " ~ " + cl.end.ticks +
            "  (" + (Number(cl.start.ticks) / TICKS).toFixed(3) + "s ~ " +
            (Number(cl.end.ticks) / TICKS).toFixed(3) + "s)  " + mp);
    }
    // M3 에서 만든 키프레임이 아직 살아 있는지
    var chart = null;
    for (var t2 = 0; t2 < seq.videoTracks.numTracks && !chart; t2++) {
        var k = seq.videoTracks[t2];
        for (var c2 = 0; c2 < k.clips.numItems && !chart; c2++) if (k.clips[c2].name === "chartA.png") chart = k.clips[c2];
    }
    if (chart) {
        for (var ci = 0; ci < chart.components.numItems; ci++) {
            var cm = chart.components[ci];
            if (cm.displayName !== "모션") continue;
            for (var pj = 0; pj < cm.properties.numItems; pj++) {
                var pr = cm.properties[pj];
                if (pr.displayName !== "위치" && pr.displayName !== "비율 조정") continue;
                if (!pr.isTimeVarying()) { say("M3 " + pr.displayName, "정적 " + pr.getValue()); continue; }
                var ks = pr.getKeys(), a = [];
                for (var q = 0; q < ks.length; q++) a.push(ks[q].ticks + "=" + pr.getValueAtKey(ks[q]));
                say("M3 " + pr.displayName, ks.length + "키 :: " + a.join(" | "));
            }
        }
    } else say("chartA.png", "(못 찾음)");

    var f = new File("C:/pprolab/m4_readback.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    return "m4_readback ok";
})();
