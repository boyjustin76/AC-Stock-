/*
    M2 되읽기. 저장본의 **사본을 새로 열어** 교체가 파일에 박혔는지 확인한다 (§3-5).
    같은 세션의 메모리 상태가 아니라 디스크에서 다시 읽은 값이어야 한다.
*/
(function () {
    var P     = "C:/pprolab/m2_readback.prproj";
    var CLONE = "롱폼 고정 양식 복사";
    var BASE  = "롱폼 고정 양식";
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }

    app.openDocument(P, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m2_readback") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);
    say("numSequences", app.project.sequences.numSequences);

    function findSeq(n) {
        var s = app.project.sequences;
        for (var i = 0; i < s.numSequences; i++) if (s[i].name === n) return s[i];
        return null;
    }
    function dumpV1(seq, tag) {
        if (!seq) { say(tag, "(시퀀스 없음)"); return; }
        var tr = seq.videoTracks[1];
        for (var c = 0; c < tr.clips.numItems; c++) {
            var cl = tr.clips[c], p = "(projectItem 없음)";
            try { p = cl.projectItem.getMediaPath(); } catch (e) {}
            say(tag + ".V1[" + c + "]", cl.name + " | start=" + cl.start.ticks + " | " + p);
        }
        // 모션·자르기가 살아 있는지
        try {
            var t2 = tr.clips[2];
            for (var ci = 0; ci < t2.components.numItems; ci++) {
                var cm = t2.components[ci], ps = [];
                for (var pj = 0; pj < cm.properties.numItems; pj++) {
                    var pr = cm.properties[pj], v = "?";
                    try { v = pr.getValue(); } catch (e) {}
                    ps.push(pr.displayName + "=" + v);
                }
                say(tag + ".V1[2].component[" + ci + "]", cm.displayName + " :: " + ps.join(" · "));
            }
        } catch (e) { say(tag + ".components_ERR", e.toString()); }
    }
    dumpV1(findSeq(CLONE), "복제");
    dumpV1(findSeq(BASE), "원본");

    var f = new File("C:/pprolab/m2_readback.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    return "m2_readback ok";
})();
