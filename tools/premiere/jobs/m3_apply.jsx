/*
    M3. 키프레임 — 읽고 → 하나 수정하고 → 새로 만든다.

    실측 근거 (m3_probe · m3_interp · kfdump):
      * 키프레임 시각은 **소스 시간**이다 (클립의 inPoint 기준). 타임라인 시간이 아니다.
      * 회사 모션은 **29.97 격자**(8,475,667,200 틱/프레임)에 정수배로 놓여 있다 —
        이 시퀀스의 timebase 가 8,467,200,000(30.0) 인데도 그렇다.
      * setInterpolationTypeAtKey 의 상수는 파일 코드와 0~7 그대로 1:1.
        "선형 → 이즈" = 0 → 5 (프리셋의 motion_preset #1 세 군데에서 확인).
      * getInterpolationTypeAtKey 는 없다 — 검증은 kfdump.py 로 파일을 읽어서 한다.
      * Time 객체에 .ticks 문자열을 넣는 경로는 오차가 없다 (8키 전부 의도한 틱에 안착).
*/
(function () {
    var SRC   = "C:/pprolab/m3_src.prproj";
    var OUT   = "C:/pprolab/m3_out.prproj";
    var CLONE = "롱폼 고정 양식 복사";
    var BASE  = "롱폼 고정 양식";
    var F2997 = 8475667200;

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m3_apply.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }
    function timeAt(ticksNum) { var t = new Time(); t.ticks = String(ticksNum); return t; }

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
    var clone = findSeq(CLONE), base = findSeq(BASE);
    if (!clone) return done("FAILED: 복제 시퀀스 없음");

    function findClip(seq, name) {
        for (var t = 0; t < seq.videoTracks.numTracks; t++) {
            var tr = seq.videoTracks[t];
            for (var c = 0; c < tr.clips.numItems; c++) if (tr.clips[c].name === name) return tr.clips[c];
        }
        return null;
    }
    function findProp(clip, comp, prop) {
        if (!clip) return null;
        for (var ci = 0; ci < clip.components.numItems; ci++) {
            var cm = clip.components[ci];
            if (cm.displayName !== comp) continue;
            for (var pj = 0; pj < cm.properties.numItems; pj++)
                if (cm.properties[pj].displayName === prop) return cm.properties[pj];
        }
        return null;
    }
    function keyDump(prop) {
        if (!prop) return "(없음)";
        try {
            if (!prop.isTimeVarying()) return "정적 value=" + prop.getValue();
            var ks = prop.getKeys(), a = [];
            for (var q = 0; q < ks.length; q++) a.push(ks[q].ticks + "=" + prop.getValueAtKey(ks[q]));
            return ks.length + "키 :: " + a.join(" | ");
        } catch (e) { return "ERR " + e.toString(); }
    }

    // ================= M3-b. 기존 키프레임 하나 수정 =======================
    var MODCLIP = "차트명가_유튜브 댓글 유도.png";
    var modClone = findClip(clone, MODCLIP), modBase = base ? findClip(base, MODCLIP) : null;
    var pClone = findProp(modClone, "모션", "비율 조정");
    var pBase  = findProp(modBase, "모션", "비율 조정");
    say("[수정] 대상", MODCLIP + " 모션/비율 조정");
    say("[수정] 복제 before", keyDump(pClone));
    say("[수정] 원본 before", keyDump(pBase));

    if (pClone && pClone.isTimeVarying()) {
        var ks = pClone.getKeys();
        var last = ks[ks.length - 1];
        say("[수정] 마지막 키 틱", last.ticks);
        probe("[수정] setValueAtKey(80)", function () { pClone.setValueAtKey(last, 80, 1); return "ok"; });
        say("[수정] 복제 after", keyDump(pClone));
        say("[수정] 원본 after", keyDump(pBase));
    } else {
        say("[수정] 건너뜀", "대상에 키프레임이 없다");
    }

    // ================= M3-c. 새 키프레임 생성 =============================
    var chart = findClip(clone, "chartA.png");
    if (!chart) return done("FAILED: chartA.png 클립 없음");
    var inTicks = Number(chart.inPoint.ticks);
    say("[생성] chartA.inPoint", chart.inPoint.ticks);
    say("[생성] chartA.start", chart.start.ticks);
    say("[생성] chartA.duration", chart.duration.ticks);

    // --- motion_preset #2 아래에서 올라오기 : 위치 0.5,1.1148 -> 0.5,0.5 / 7프레임 / 선형->이즈
    var pos = findProp(chart, "모션", "위치");
    if (!pos) return done("FAILED: 모션/위치 없음");
    say("[생성] 위치 before", keyDump(pos));
    probe("[생성] 위치 setTimeVarying", function () { return pos.setTimeVarying(true); });

    var t0 = timeAt(inTicks), t1 = timeAt(inTicks + 7 * F2997);
    say("[생성] 위치 t0", t0.ticks);
    say("[생성] 위치 t1", t1.ticks + "  (= t0 + 7프레임@29.97 = " + (7 * F2997) + "틱)");

    probe("[생성] 위치 addKey(t0)", function () { pos.addKey(t0); return "ok"; });
    probe("[생성] 위치 addKey(t1)", function () { pos.addKey(t1); return "ok"; });
    // 2D 값은 배열로 준다. 안 되면 문자열도 시도한다.
    probe("[생성] 위치 setValueAtKey(t0,[0.5,1.1148])", function () {
        pos.setValueAtKey(t0, [0.5, 1.1148], 1); return "ok";
    });
    probe("[생성] 위치 setValueAtKey(t1,[0.5,0.5])", function () {
        pos.setValueAtKey(t1, [0.5, 0.5], 1); return "ok";
    });
    probe("[생성] 위치 interp t0=0(선형)", function () { pos.setInterpolationTypeAtKey(t0, 0, 1); return "ok"; });
    probe("[생성] 위치 interp t1=5(이즈)", function () { pos.setInterpolationTypeAtKey(t1, 5, 1); return "ok"; });
    say("[생성] 위치 after", keyDump(pos));

    // --- motion_preset #1 수치 재현 : 1 -> 100 / 4프레임 / 선형->이즈
    //     원래는 '변형/높이 비율 조정' 이지만 이 클립엔 변형 이펙트가 없다.
    //     수치·프레임·이징만 스칼라 파라미터(모션/비율 조정)에 재현한다.
    var scale = findProp(chart, "모션", "비율 조정");
    if (scale) {
        say("[생성] 비율 조정 before", keyDump(scale));
        probe("[생성] 비율 setTimeVarying", function () { return scale.setTimeVarying(true); });
        var s0 = timeAt(inTicks), s1 = timeAt(inTicks + 4 * F2997);
        probe("[생성] 비율 addKey(s0)", function () { scale.addKey(s0); return "ok"; });
        probe("[생성] 비율 addKey(s1)", function () { scale.addKey(s1); return "ok"; });
        probe("[생성] 비율 setValueAtKey(s0,1)", function () { scale.setValueAtKey(s0, 1, 1); return "ok"; });
        probe("[생성] 비율 setValueAtKey(s1,100)", function () { scale.setValueAtKey(s1, 100, 1); return "ok"; });
        probe("[생성] 비율 interp s0=0", function () { scale.setInterpolationTypeAtKey(s0, 0, 1); return "ok"; });
        probe("[생성] 비율 interp s1=5", function () { scale.setInterpolationTypeAtKey(s1, 5, 1); return "ok"; });
        say("[생성] 비율 조정 after", keyDump(scale));
    }

    // 원본 쪽 chartA 자리(차10_1-5.png)가 그대로인지
    probe("[격리] 원본 V1[2]", function () {
        var b = base.videoTracks[1].clips[2];
        return b.name + " | " + b.projectItem.getMediaPath();
    });
    probe("[격리] 원본 V1[2] 모션/위치", function () { return keyDump(findProp(base.videoTracks[1].clips[2], "모션", "위치")); });

    probe("saveAs", function () { return app.project.saveAs(OUT); });
    return done("m3_apply ok");
})();
