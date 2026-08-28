/*
    M3-b 예비실험. setInterpolationTypeAtKey 의 상수와 파일에 박히는 보간 코드를 매핑한다.

    getInterpolationTypeAtKey 는 undefined 다 — 보간은 쓸 수는 있는데 API 로 읽을 수가 없다.
    그래서 0~7 을 각각 다른 키에 걸고 저장한 뒤, <Keyframes> 평문을 읽어 대조한다 (§3-5).
    덤으로 addKey 가 Time 객체를 받는지 초(number)를 받는지도 여기서 가른다.

    버리는 파일이다. 산출물은 m3_apply.jsx 가 만든다.
*/
(function () {
    var SRC   = "C:/pprolab/m3_interp_src.prproj";
    var OUT   = "C:/pprolab/m3_interp.prproj";
    var CLONE = "롱폼 고정 양식 복사";
    var CLIP  = "chartA.png";
    var COMP  = "모션";
    var PROP  = "비율 조정";
    var FRAME_2997 = 8475667200;   // 틱/프레임 @29.97 — 프리셋 키프레임이 이 격자에 있다

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m3_interp.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }

    var opened = false;
    try { opened = (app.project && app.project.path && app.project.path.indexOf("m3_interp_src") >= 0); } catch (e) {}
    if (!opened) {
        app.openDocument(SRC, 1, 1, 1, 1);
        var w = 0;
        while (w < 180 && !(app.project && app.project.path.indexOf("m3_interp_src") >= 0
                            && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    }
    say("project.path", app.project.path);

    var seq = null, s = app.project.sequences;
    for (var i = 0; i < s.numSequences; i++) if (s[i].name === CLONE) seq = s[i];
    if (!seq) return done("FAILED: 복제 시퀀스 없음");

    var clip = null;
    for (var t = 0; t < seq.videoTracks.numTracks && !clip; t++) {
        var tr = seq.videoTracks[t];
        for (var c = 0; c < tr.clips.numItems && !clip; c++) if (tr.clips[c].name === CLIP) clip = tr.clips[c];
    }
    if (!clip) return done("FAILED: " + CLIP + " 클립 없음");

    var prop = null;
    for (var ci = 0; ci < clip.components.numItems; ci++) {
        var cm = clip.components[ci];
        if (cm.displayName !== COMP) continue;
        for (var pj = 0; pj < cm.properties.numItems; pj++)
            if (cm.properties[pj].displayName === PROP) prop = cm.properties[pj];
    }
    if (!prop) return done("FAILED: " + COMP + "/" + PROP + " 없음");

    var base = clip.inPoint.ticks;   // 키프레임 시각은 소스 시간이다 (프로브에서 확인)
    say("clip.inPoint.ticks", base);
    say("clip.start.ticks", clip.start.ticks);
    probe("areKeyframesSupported", function () { return prop.areKeyframesSupported(); });
    probe("setTimeVarying(true)", function () { return prop.setTimeVarying(true); });
    probe("isTimeVarying", function () { return prop.isTimeVarying(); });

    function tickAt(n) {
        // 문자열 산술 없이 Number 로 더한다. 9.1e14 + 8.4e9 는 double 로 정확히 표현된다
        // (2^53 = 9.0e15 보다 작다) — 그래도 결과를 되읽어 확인한다.
        var v = Number(base) + n * FRAME_2997;
        var tm = new Time();
        tm.ticks = String(v);
        return tm;
    }

    // 0~7 을 각각 다른 키에 건다
    for (var k = 0; k <= 7; k++) {
        (function (n) {
            var tm = tickAt(n);
            probe("k" + n + ".addKey(Time)", function () { prop.addKey(tm); return "ok"; });
            probe("k" + n + ".setValueAtKey", function () { prop.setValueAtKey(tm, 10 + n * 10, 1); return "ok"; });
            probe("k" + n + ".setInterp(" + n + ")", function () { prop.setInterpolationTypeAtKey(tm, n, 1); return "ok"; });
            say("k" + n + ".의도한_틱", tm.ticks);
        })(k);
    }

    // 되읽기 — API 가 실제로 어디에 키를 놨는지
    probe("getKeys_후", function () {
        var ks = prop.getKeys(), a = [];
        for (var q = 0; q < ks.length; q++) {
            var v = "?";
            try { v = prop.getValueAtKey(ks[q]); } catch (e) {}
            a.push(ks[q].ticks + "=" + v);
        }
        return ks.length + "키 :: " + a.join(" | ");
    });

    probe("saveAs", function () { return app.project.saveAs(OUT); });
    return done("m3_interp ok");
})();
