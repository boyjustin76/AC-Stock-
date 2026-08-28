/*
    M6 프로브 2 — 시퀀스 생성 인자 형식을 좁힌다.

    실측(m6_probe):
      · app.project.createNewSequence(name, id) 는 **'새 시퀀스' 모달을 띄운다.**
        BridgeTalk 가 영영 안 돌아온다. 절대 쓰면 안 된다.
      · qe.project.newSequence(name, "C:/.../x.sqpreset") 는 false 를 주고 아무것도 안 만든다.

    exportFramePNG 도 슬래시 경로에서 실패했다(역슬래시여야 했다). 같은 함정인지 본다.

    ⚠ 이 잡은 **매 줄마다 파일을 다시 쓴다.** 모달이 떠서 멈추면 어디서 멈췄는지
      로그에 남아 있어야 한다. 안 그러면 타임아웃만 보고 원인을 못 찾는다.
*/
(function () {
    var BS = String.fromCharCode(92);
    var SLASH = "C:/pprolab/cmg_1080p_30fps.sqpreset";
    var BACK = SLASH.split("/").join(BS);
    var LOG = "C:/pprolab/m6_probe2.txt";

    var out = [];
    function flush() {
        var f = new File(LOG);
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    }
    function say(k, v) { out.push(k + "\t" + v); flush(); }
    function probe(k, fn) {
        say(k, "…호출 직전");                       // 여기서 멈추면 이 줄이 마지막이다
        var r; try { r = String(fn()); } catch (e) { r = "ERR " + e.toString(); }
        out[out.length - 1] = k + "\t" + r; flush();
    }

    say("프리셋(ASCII)", new File(SLASH).exists + "  " + BACK);

    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); } catch (e) { break; }
    }
    var NEWPROJ = "C:/pprolab/m6_scratch.prproj";
    var old = new File(NEWPROJ); if (old.exists) old.remove();
    probe("newProject", function () { return app.newProject(NEWPROJ); });
    say("시퀀스 수(처음)", app.project.sequences.numSequences);

    app.enableQE();

    function count() { return app.project.sequences.numSequences; }
    function attempt(tag, fn) {
        var n0 = count();
        probe(tag, fn);
        var n1 = count();
        say("  → " + tag, "시퀀스 " + n0 + " -> " + n1 + (n1 > n0 ? "  ★만들어졌다" : ""));
        if (n1 > n0) {
            var sq = app.project.sequences[n1 - 1];
            say("  → 설정", "name=" + sq.name + "  timebase=" + sq.timebase +
                "  " + sq.frameSizeHorizontal + "x" + sq.frameSizeVertical +
                "  V" + sq.videoTracks.numTracks + " A" + sq.audioTracks.numTracks);
        }
        return n1 > n0;
    }

    /*  createNewSequence 는 모달을 띄우므로 시도조차 하지 않는다  */

    var okA = attempt("qe.newSequence(역슬래시)", function () { return qe.project.newSequence("A_qe_back", BACK); });
    if (!okA) attempt("qe.newSequence(File 객체)", function () { return qe.project.newSequence("B_qe_file", new File(SLASH)); });

    var okC = attempt("project.newSequence(역슬래시)", function () { return app.project.newSequence("C_dom_back", BACK); });
    if (!okC) attempt("project.newSequence(슬래시)", function () { return app.project.newSequence("D_dom_slash", SLASH); });

    /*  프리셋 없이 이름만 — 기본 설정으로라도 만들어지는가  */
    attempt("project.newSequence(이름만)", function () { return app.project.newSequence("E_dom_noargs"); });

    /*  클립에서 유도 — 클립이 하나 있어야 한다  */
    var mp4 = "C:/Users/user/Desktop/이정찬/Claude/AC-Stock-/deliver/cutscene/차12_RSI+이평선 스캘핑/컷1_교과서공식.mp4";
    if (new File(mp4).exists) {
        probe("importFiles", function () { return app.project.importFiles([mp4], 1, app.project.rootItem, 0); });
        var it = null;
        for (var i = 0; i < app.project.rootItem.children.numItems; i++) {
            var ch = app.project.rootItem.children[i];
            try { if (ch.getMediaPath()) { it = ch; break; } } catch (e) {}
        }
        if (it) attempt("createNewSequenceFromClips", function () {
            return app.project.createNewSequenceFromClips("F_fromClip", [it]);
        });
    }

    var names = [];
    for (var j = 0; j < count(); j++) {
        var s2 = app.project.sequences[j];
        names.push(s2.name + " tb=" + s2.timebase + " " + s2.frameSizeHorizontal + "x" + s2.frameSizeVertical +
                   " V" + s2.videoTracks.numTracks);
    }
    say("결과 목록", names.length + "개\n        " + names.join("\n        "));
    return "m6_probe2 ok";
})();
