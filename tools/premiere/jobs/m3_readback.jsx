/*
    M3 되읽기. 저장본 사본을 새로 열어 키프레임이 살아 돌아오는지 본다 (§3-5).
    포토샵 때 psd-tools 가 쓴 파일을 포토샵이 거부한 전례가 있다 — 파일이 파싱된다고
    앱이 받아들인다는 뜻은 아니다.
*/
(function () {
    var P = "C:/pprolab/m3_readback.prproj";
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }

    app.openDocument(P, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m3_readback") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);
    say("numSequences", app.project.sequences.numSequences);

    function findSeq(n) {
        var s = app.project.sequences;
        for (var i = 0; i < s.numSequences; i++) if (s[i].name === n) return s[i];
        return null;
    }
    function findClip(seq, name) {
        for (var t = 0; t < seq.videoTracks.numTracks; t++) {
            var tr = seq.videoTracks[t];
            for (var c = 0; c < tr.clips.numItems; c++) if (tr.clips[c].name === name) return tr.clips[c];
        }
        return null;
    }
    function dump(clip, comp, prop, tag) {
        if (!clip) { say(tag, "(클립 없음)"); return; }
        for (var ci = 0; ci < clip.components.numItems; ci++) {
            var cm = clip.components[ci];
            if (cm.displayName !== comp) continue;
            for (var pj = 0; pj < cm.properties.numItems; pj++) {
                var pr = cm.properties[pj];
                if (pr.displayName !== prop) continue;
                if (!pr.isTimeVarying()) { say(tag, "정적 value=" + pr.getValue()); return; }
                var ks = pr.getKeys(), a = [];
                for (var q = 0; q < ks.length; q++) a.push(ks[q].ticks + "=" + pr.getValueAtKey(ks[q]));
                say(tag, ks.length + "키 :: " + a.join(" | "));
                return;
            }
        }
        say(tag, "(파라미터 없음)");
    }

    var clone = findSeq("롱폼 고정 양식 복사"), base = findSeq("롱폼 고정 양식");
    dump(findClip(clone, "chartA.png"), "모션", "위치", "복제 chartA 모션/위치");
    dump(findClip(clone, "chartA.png"), "모션", "비율 조정", "복제 chartA 모션/비율 조정");
    dump(findClip(clone, "차트명가_유튜브 댓글 유도.png"), "모션", "비율 조정", "복제 댓글유도 모션/비율 조정");
    dump(findClip(base, "차트명가_유튜브 댓글 유도.png"), "모션", "비율 조정", "원본 댓글유도 모션/비율 조정");
    dump(findClip(base, "차10_1-5.png"), "모션", "위치", "원본 차10_1-5 모션/위치");

    var f = new File("C:/pprolab/m3_readback.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    return "m3_readback ok";
})();
