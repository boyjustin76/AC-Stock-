/*
    M4-c. 대본 타임코드에 맞춰 컷 3개를 배치한다 (차명12 인트로 테스트).

    경계는 자막의 초를 30.0 격자로 환산한 값이다 — 컷 경계는 시퀀스 timebase(30.0)에
    떨어져야 한다(실측). 프레임 번호로 옮기면 20분에서 1.2초 어긋난다.

        컷1  3.390~7.400s   f102~f222   틱   863,654,400,000 ~ 1,879,718,400,000
        컷2  7.400~13.770s  f222~f413   틱 1,879,718,400,000 ~ 3,496,953,600,000
        컷3 13.770~15.520s  f413~f466   틱 3,496,953,600,000 ~ 3,945,715,200,000

    배치는 overwriteClip 을 쓴다. 이건 **새 클립을 만들기 때문에 프리셋의 이펙트·
    키프레임을 물려받지 못한다** — M2 의 clip.projectItem 대입(기존 클립의 소스만 교체)과
    성질이 다르다. 그 차이를 여기서 숫자로 남기는 것도 이 잡의 목적이다.
*/
(function () {
    var SRC = "C:/pprolab/m4_place_src.prproj";
    var OUT = "C:/pprolab/m4_place.prproj";
    var CLONE = "롱폼 고정 양식 복사";
    /*  V1 은 프리셋에서 차트 스틸이 놓이던 트랙이지만, 이 구간에 프리셋 클립이 이미 있다.
        거기에 overwriteClip 하면 그 클립과 키프레임이 지워진다 (실측: V1 에 놓았더니
        '흰 배경' 클립이 통째로 사라지고 StartKeyframe 이 2,372 → 2,345 로 줄었다).
        V6 은 0~16초가 비어 있어(m4_tracks 로 확인) 아무것도 안 부수고 놓을 수 있다.
        실제 회차 조립에서는 차트가 스택 아래에 와야 하므로, 트랙을 새로 끼우거나
        기존 클립의 소스만 교체(M2 방식)하는 쪽으로 가야 한다.  */
    var TRACK = 6;
    var TICKS = 254016000000;

    var CUTS = [
        { id: 'cut1', png: 'C:/cmgwork/cmg12/cut1.png', start: 863654400000, end: 1879718400000 },
        { id: 'cut2', png: 'C:/cmgwork/cmg12/cut2.png', start: 1879718400000, end: 3496953600000 },
        { id: 'cut3', png: 'C:/cmgwork/cmg12/cut3.png', start: 3496953600000, end: 3945715200000 }
    ];

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m4_place.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }
    function T(ticks) { var t = new Time(); t.ticks = String(ticks); return t; }

    for (var c0 = 0; c0 < CUTS.length; c0++) {
        if (!new File(CUTS[c0].png).exists) return done("FAILED: 차트가 없다 " + CUTS[c0].png);
    }

    // 열린 프로젝트를 전부 닫고 새로 연다 (안 그러면 옛 메모리 상태를 본다)
    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; }
        catch (e) { say("closeDocument_ERR", e.toString()); break; }
    }
    say("닫은 프로젝트", closed);

    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m4_place_src") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);

    var seq = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name === CLONE) seq = app.project.sequences[i];
    if (!seq) return done("FAILED: 복제 시퀀스 없음");
    say("seq.timebase", seq.timebase);
    say("seq.end", seq.end);

    var track = seq.videoTracks[TRACK];
    probe("V" + TRACK + " 잠금 해제", function () { track.setLocked(0); return "ok"; });

    // 배치 전 V1 상태 — 무엇을 덮어쓰는지 남긴다
    var before = [];
    for (var b = 0; b < track.clips.numItems; b++) {
        var cl = track.clips[b];
        before.push(cl.name + "@" + cl.start.ticks + "~" + cl.end.ticks);
    }
    say("V" + TRACK + " before", before.length + "개 :: " + before.join(" | "));

    // 차트 import
    var paths = [];
    for (var p0 = 0; p0 < CUTS.length; p0++) paths.push(CUTS[p0].png);
    var rootBefore = app.project.rootItem.children.numItems;
    probe("importFiles", function () { return app.project.importFiles(paths, 1, app.project.rootItem, 0); });
    say("rootItems", rootBefore + " -> " + app.project.rootItem.children.numItems);

    function findItem(pngPath) {
        var want = pngPath.toLowerCase();
        var root = app.project.rootItem;
        for (var i2 = 0; i2 < root.children.numItems; i2++) {
            var ch = root.children[i2], mp = "";
            try { mp = ch.getMediaPath(); } catch (e) { continue; }
            if (mp && mp.split(String.fromCharCode(92)).join("/").toLowerCase() === want) return ch;
        }
        return null;
    }

    // 배치
    for (var k = 0; k < CUTS.length; k++) {
        var C = CUTS[k];
        var item = findItem(C.png);
        if (!item) { say(C.id + "_FAIL", "import 한 항목을 못 찾겠다"); continue; }
        say(C.id + ".item", item.name + " node=" + item.nodeId);

        var startSec = C.start / TICKS;
        probe(C.id + ".overwriteClip", function () { track.overwriteClip(item, startSec); return "ok"; });

        // 방금 놓인 클립을 시작 틱으로 찾는다 (인덱스로 잡지 않는다)
        var placed = null;
        for (var q = 0; q < track.clips.numItems; q++) {
            if (String(track.clips[q].start.ticks) === String(C.start)) { placed = track.clips[q]; break; }
        }
        if (!placed) {
            // 정확히 안 맞으면 가장 가까운 것을 찾아 얼마나 틀어졌는지 적는다
            var best = null, bd = null;
            for (var q2 = 0; q2 < track.clips.numItems; q2++) {
                var d = Math.abs(Number(track.clips[q2].start.ticks) - C.start);
                if (bd === null || d < bd) { bd = d; best = track.clips[q2]; }
            }
            say(C.id + ".정확히_안맞음", "가장 가까운 클립 " + (best ? best.name + "@" + best.start.ticks : "(없음)") +
                "  차이=" + bd + "틱 (" + (bd / TICKS).toFixed(4) + "s)");
            placed = best;
        }
        if (!placed) { say(C.id + "_FAIL", "놓인 클립을 못 찾겠다"); continue; }

        say(C.id + ".놓인 시작", placed.start.ticks + "  (의도 " + C.start + ")");
        say(C.id + ".놓인 끝(자르기 전)", placed.end.ticks + "  (의도 " + C.end + ")");

        // 길이를 컷 경계에 맞춘다
        probe(C.id + ".end 대입", function () { placed.end = T(C.end); return "ok"; });
        say(C.id + ".최종", placed.name + "  " + placed.start.ticks + " ~ " + placed.end.ticks +
            "  길이=" + (Number(placed.end.ticks) - Number(placed.start.ticks)) +
            " (" + ((Number(placed.end.ticks) - Number(placed.start.ticks)) / TICKS).toFixed(4) + "s)");

        // 이펙트를 물려받았는지 — overwriteClip 은 새 클립이라 기본값일 것이다
        var comps = [];
        try {
            for (var ci = 0; ci < placed.components.numItems; ci++) comps.push(placed.components[ci].displayName);
        } catch (e) { comps.push("ERR " + e.toString()); }
        say(C.id + ".컴포넌트", comps.join(" · "));
    }

    // 배치 후 V1
    var after = [];
    for (var a2 = 0; a2 < track.clips.numItems; a2++) {
        var cl2 = track.clips[a2];
        after.push(cl2.name + "@" + cl2.start.ticks + "~" + cl2.end.ticks);
    }
    say("V" + TRACK + " after", after.length + "개 :: " + after.join(" | "));

    var ok = false;
    probe("saveAs", function () { ok = app.project.saveAs(OUT); return ok; });
    say("out_size", new File(OUT).exists ? new File(OUT).length : "(없음)");
    return done("m4_place " + (ok ? "ok" : "FAILED"));
})();
