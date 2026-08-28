/*
    M2-a. 교체 대상과 API 표면을 잰다. 아무것도 바꾸지 않는다.

    가장 큰 함정부터 확인한다: 복제 시퀀스는 마스터 클립(projectItem)을 원본과 공유한다
    (prproj_fact 23). 그러면 projectItem.changeMediaPath() 는 원본 시퀀스까지 같이 바꾼다.
    복제본의 클립과 원본의 클립이 같은 nodeId 를 쓰는지 여기서 확인한다.
*/
(function () {
    var SRC   = "C:/pprolab/m2_src.prproj";
    var CLONE = "롱폼 고정 양식 복사";
    var BASE  = "롱폼 고정 양식";

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function members(o) { if (!o) return "(null)"; var a = []; for (var k in o) a.push(k); a.sort(); return a.join(","); }

    var opened = false;
    try { opened = (app.project && app.project.path && app.project.path.indexOf("m2_src") >= 0); } catch (e) {}
    if (!opened) {
        app.openDocument(SRC, 1, 1, 1, 1);
        var w = 0;
        while (w < 180 && !(app.project && app.project.path.indexOf("m2_src") >= 0
                            && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    }
    say("project.path", app.project.path);
    say("numSequences", app.project.sequences.numSequences);

    function findSeq(name) {
        var s = app.project.sequences;
        for (var i = 0; i < s.numSequences; i++) if (s[i].name === name) return s[i];
        return null;
    }
    var clone = findSeq(CLONE), base = findSeq(BASE);
    if (!clone) { say("FATAL", "복제 시퀀스를 못 찾았다: " + CLONE); }

    // 두 시퀀스의 클립을 전부 훑어 nodeId 를 모은다
    function dump(seq, tag) {
        var ids = {};
        if (!seq) return ids;
        for (var t = 0; t < seq.videoTracks.numTracks; t++) {
            var tr = seq.videoTracks[t];
            for (var c = 0; c < tr.clips.numItems; c++) {
                var cl = tr.clips[c];
                var pi = null, nodeId = "?", mp = "?";
                try { pi = cl.projectItem; } catch (e) {}
                if (pi) {
                    try { nodeId = pi.nodeId; } catch (e) {}
                    try { mp = pi.getMediaPath(); } catch (e) { mp = "(경로없음)"; }
                }
                ids[nodeId] = (ids[nodeId] || 0) + 1;
                say(tag + ".V" + t + "[" + c + "]",
                    cl.name + " | start=" + cl.start.ticks + " | end=" + cl.end.ticks +
                    " | node=" + nodeId + " | " + mp);
            }
        }
        return ids;
    }
    say("--- 복제 시퀀스 클립 ---", "");
    var cloneIds = dump(clone, "clone");
    say("--- 원본 시퀀스 클립 ---", "");
    var baseIds = dump(base, "base");

    var shared = [];
    for (var k in cloneIds) if (baseIds[k]) shared.push(k);
    say("공유 nodeId 수", shared.length + " / 복제 고유 " + (function () { var n = 0; for (var q in cloneIds) n++; return n; })());
    say("공유 nodeId", shared.join(","));

    // API 표면
    // projectItem 이 실제로 붙어 있는 클립을 고른다 — 조정 레이어·트랜지션은 null 이다
    var anyClip = null;
    try {
        for (var t2 = 0; t2 < clone.videoTracks.numTracks && !anyClip; t2++) {
            var trk = clone.videoTracks[t2];
            for (var c2 = 0; c2 < trk.clips.numItems && !anyClip; c2++) {
                try { if (trk.clips[c2].projectItem) anyClip = trk.clips[c2]; } catch (e) {}
            }
        }
    } catch (e) {}
    say("probe_clip", anyClip ? anyClip.name : "(projectItem 붙은 클립을 못 찾았다)");
    if (anyClip) {
        probe("trackItem_members", function () { return members(anyClip); });
        var tiWanted = ["projectItem", "components", "getMatchName", "getSpeed", "setScale", "name",
                        "mediaType", "disabled", "duration", "inPoint", "outPoint", "start", "end", "remove"];
        for (var i2 = 0; i2 < tiWanted.length; i2++)
            (function (n) { probe("trackItem." + n, function () { return typeof anyClip[n]; }); })(tiWanted[i2]);

        var pi2 = anyClip.projectItem;
        probe("projectItem_members", function () { return members(pi2); });
        var piWanted = ["changeMediaPath", "canChangeMediaPath", "getMediaPath", "refreshMedia",
                        "attachProxy", "canProxy", "createSubClip", "setOverrideFrameRate",
                        "setScaleToFrameSize", "getFootageInterpretation", "setFootageInterpretation",
                        "videoComponents", "getColorLabel", "name", "nodeId", "type"];
        for (var i3 = 0; i3 < piWanted.length; i3++)
            (function (n) { probe("projectItem." + n, function () { return typeof pi2[n]; }); })(piWanted[i3]);

        // 모션 파라미터 (§3-4 스케일 기준값)
        probe("components", function () {
            var a = [];
            for (var ci = 0; ci < anyClip.components.numItems; ci++) {
                var cm = anyClip.components[ci], ps = [];
                for (var pj = 0; pj < cm.properties.numItems; pj++) {
                    var pr = cm.properties[pj], v = "?";
                    try { v = pr.getValue(); } catch (e) {}
                    var kf = "?";
                    try { kf = pr.isTimeVarying() ? "KF" : "-"; } catch (e) {}
                    ps.push(pr.displayName + "=" + v + "(" + kf + ")");
                }
                a.push("[" + cm.displayName + "] " + ps.join(" · "));
            }
            return a.join("\n\t\t");
        });
    }

    // 트랙·프로젝트 쓰기 API
    var trWanted = ["overwriteClip", "insertClip", "clips", "numItems", "isLocked", "setLocked", "id"];
    for (var i4 = 0; i4 < trWanted.length; i4++)
        (function (n) { probe("videoTrack." + n, function () { return typeof clone.videoTracks[0][n]; }); })(trWanted[i4]);
    var prWanted = ["importFiles", "createNewBin", "rootItem", "getInsertionBin"];
    for (var i5 = 0; i5 < prWanted.length; i5++)
        (function (n) { probe("project." + n, function () { return typeof app.project[n]; }); })(prWanted[i5]);
    probe("rootItem_members", function () { return members(app.project.rootItem); });
    probe("projectItem_proto", function () { return members(app.project.rootItem.children[0]); });

    var f = new File("C:/pprolab/m2_probe.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    return "m2_probe ok, " + out.length + " lines";
})();
