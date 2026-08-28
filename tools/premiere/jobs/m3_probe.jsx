/*
    M3-a. 이미 걸려 있는 키프레임을 읽고 프로퍼티 API 표면을 잰다. 아무것도 바꾸지 않는다.

    목적 셋:
      1) 복제 시퀀스 안에서 키프레임이 걸린 파라미터를 전부 찾는다 (§3-6 — 목록으로 읽는다)
      2) 그 키프레임의 시각·값·보간을 공개 DOM 으로 읽을 수 있는지 확인
      3) 쓰기 API(addKey/setValueAtKey/setInterpolationTypeAtKey…)가 있는지 typeof 로 찍는다
         — 열거에 안 잡히는 함수가 있다는 걸 M1 에서 배웠다
*/
(function () {
    var SRC   = "C:/pprolab/m3_src.prproj";
    var CLONE = "롱폼 고정 양식 복사";
    var TICKS = 254016000000;

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }

    var opened = false;
    try { opened = (app.project && app.project.path && app.project.path.indexOf("m3_src") >= 0); } catch (e) {}
    if (!opened) {
        app.openDocument(SRC, 1, 1, 1, 1);
        var w = 0;
        while (w < 180 && !(app.project && app.project.path.indexOf("m3_src") >= 0
                            && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    }
    say("project.path", app.project.path);

    function findSeq(n) {
        var s = app.project.sequences;
        for (var i = 0; i < s.numSequences; i++) if (s[i].name === n) return s[i];
        return null;
    }
    var seq = findSeq(CLONE);
    if (!seq) { say("FATAL", "복제 시퀀스 없음"); }

    // ---- Time 객체 표면 --------------------------------------------------
    probe("typeof_Time", function () { return typeof Time; });
    probe("Time_members", function () {
        var t = new Time(), a = [];
        for (var k in t) a.push(k);
        a.sort();
        return a.join(",");
    });
    probe("Time_ticks_왕복", function () {
        var t = new Time();
        t.ticks = "59270400000";
        return "ticks=" + t.ticks + " seconds=" + t.seconds;
    });

    // ---- 키프레임이 걸린 파라미터를 전부 찾는다 ---------------------------
    var kfCount = 0, propAPIdumped = false;
    for (var tr = 0; tr < seq.videoTracks.numTracks; tr++) {
        var track = seq.videoTracks[tr];
        for (var ci = 0; ci < track.clips.numItems; ci++) {
            var clip = track.clips[ci];
            var comps = null;
            try { comps = clip.components; } catch (e) { continue; }
            if (!comps) continue;
            for (var cj = 0; cj < comps.numItems; cj++) {
                var comp = comps[cj];
                for (var pk = 0; pk < comp.properties.numItems; pk++) {
                    var prop = comp.properties[pk];
                    var varying = false;
                    try { varying = prop.isTimeVarying(); } catch (e) { continue; }
                    if (!varying) continue;
                    kfCount++;
                    var tag = "KF[V" + tr + "/" + ci + "] " + clip.name + " :: " +
                              comp.displayName + " / " + prop.displayName;
                    var keys = [];
                    try {
                        var ks = prop.getKeys();
                        for (var q = 0; q < ks.length; q++) {
                            var t0 = ks[q], v = "?";
                            try { v = prop.getValueAtKey(t0); } catch (e) {}
                            var it = "?";
                            try { it = prop.getInterpolationTypeAtKey(t0); } catch (e) {}
                            keys.push("t=" + t0.ticks + "(" + (Number(t0.ticks) / TICKS).toFixed(4) + "s)" +
                                      " v=" + v + " interp=" + it);
                        }
                    } catch (e) { keys.push("getKeys_ERR " + e.toString()); }
                    say(tag, keys.length + "키 :: " + keys.join(" | "));

                    // 프로퍼티 쓰기 API 는 한 번만 찍는다
                    if (!propAPIdumped) {
                        propAPIdumped = true;
                        var pm = [];
                        for (var m in prop) pm.push(m);
                        pm.sort();
                        say("property_members", pm.join(","));
                        var wanted = ["addKey", "removeKey", "removeKeyRange", "getKeys", "keyExistsAtTime",
                                      "getValue", "setValue", "getValueAtKey", "setValueAtKey",
                                      "isTimeVarying", "setTimeVarying", "areKeyframesSupported",
                                      "getInterpolationTypeAtKey", "setInterpolationTypeAtKey",
                                      "getColorValue", "setColorValue", "findNearestKey", "displayName"];
                        for (var wi = 0; wi < wanted.length; wi++) {
                            (function (n) { probe("property." + n, function () { return typeof prop[n]; }); })(wanted[wi]);
                        }
                    }
                }
            }
        }
    }
    say("키프레임 걸린 파라미터 수", kfCount);

    // ---- 교체한 chartA 클립의 모션 파라미터 (M3 대상) ---------------------
    var target = null;
    for (var t2 = 0; t2 < seq.videoTracks.numTracks && !target; t2++) {
        var trk = seq.videoTracks[t2];
        for (var c2 = 0; c2 < trk.clips.numItems && !target; c2++) {
            if (trk.clips[c2].name === "chartA.png") target = trk.clips[c2];
        }
    }
    if (!target) { say("chartA 클립", "(못 찾음)"); }
    else {
        say("chartA 클립", target.name + " start=" + target.start.ticks + " dur=" + target.duration.ticks);
        for (var c3 = 0; c3 < target.components.numItems; c3++) {
            var cm = target.components[c3];
            for (var p3 = 0; p3 < cm.properties.numItems; p3++) {
                var pr = cm.properties[p3], sup = "?";
                try { sup = pr.areKeyframesSupported(); } catch (e) { sup = "ERR"; }
                var v3 = "?";
                try { v3 = pr.getValue(); } catch (e) {}
                say("chartA." + cm.displayName + "/" + pr.displayName,
                    "value=" + v3 + " 키프레임가능=" + sup);
            }
        }
    }

    var f = new File("C:/pprolab/m3_probe.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n"));
    f.close();
    return "m3_probe ok, " + out.length + " lines, 키프레임 파라미터 " + kfCount;
})();
