/*
    M5-b. 차명12 인트로 3컷을 '제대로' 조립한다.

    M4-c 는 빈 트랙(V6)에 스틸을 얹은 게 전부였다. 두 가지가 틀렸다 —
      · V6 은 스택 위쪽이라 차트가 프리셋 그래픽·로고를 덮는다.
      · 모션이 하나도 없다. 컷이 정지화면으로 툭툭 바뀐다.

    이번엔 둘 다 고친다.

    1) 트랙을 원하는 깊이에 새로 끼운다.
       공개 DOM 에는 트랙 추가가 없지만 qe 층에 addTracks 가 있다 (m5_probe 실측).
       인덱스 2 에 넣으면 흰 배경·스틸(V0/V1) 위, 그래픽·중첩시퀀스(기존 V2 이상) 아래다.
       기존 V2~V10 은 V3~V11 로 밀린다.

    2) 모션은 프리셋의 어휘를 쓰되 대본에 맞춰 내가 짠다.
       프리셋 실측(M3): 비율 1->100 을 4프레임에, 위치 y 1.1148->0.5 를 7프레임에,
       보간은 첫 키 0(선형) 마지막 키 5(이즈). 짧고 빠른 '팝' 이 이 채널의 어휘다.
       다만 그건 배지·타이틀 같은 '얹는 그래픽' 의 어휘고, 차트는 화면의 바닥이라
       같은 팝을 걸면 어색하다. 그래서 어휘(이즈로 착지)만 가져오고 폭은 줄였다.

         컷1 "골든크로스에 사고 데드크로스에 팔아라"  비율 100 -> 103.5   다가간다
              + 불투명도 0 -> 100 (6프레임)            처음 등장이라 여기만 페이드
         컷2 "공식을 대입해보지만 수익이 안 난다"      비율 103.5 -> 100   물러나며 전체를 보여준다
         컷3 "크로스 신호만 보고 진입했다가"           비율 100 -> 104 -> 108  확 파고든다

       다가감 -> 물러남 -> 파고듦. 대본의 호흡 그대로다.

    격자(실측, M4-a): 컷 경계는 30.0, 모션 키프레임은 29.97. 여기서도 그대로 지킨다.
    키프레임 시각은 타임라인 시각이 아니라 '소스 시각' 이다 — clip.inPoint 기준으로 잡는다.
*/
(function () {
    var SRC = "C:/pprolab/m5_relink.prproj";
    var OUT = "C:/pprolab/m5_intro.prproj";
    var CLONE = "롱폼 고정 양식 복사";

    var TICKS = 254016000000;          // 1초
    var F2997 = 8475667200;            // 1프레임 @29.97  — 모션 키프레임
    var NEW_TRACK = 2;                 // 흰 배경 위 · 그래픽 아래

    /*  경계는 자막 초를 30.0 프레임으로 반올림한 값 (M4-c 와 동일)  */
    var CUTS = [
        { id: "cut1", png: "C:/cmgwork/cmg12/cut1.png",
          start:  863654400000, end: 1879718400000,   // 3.390 ~ 7.400s
          scale: [ { f: 0, v: 100, i: 0 }, { f: "end", v: 103.5, i: 5 } ],
          fade: 6 },
        { id: "cut2", png: "C:/cmgwork/cmg12/cut2.png",
          start: 1879718400000, end: 3496953600000,   // 7.400 ~ 13.770s
          scale: [ { f: 0, v: 103.5, i: 0 }, { f: "end", v: 100, i: 5 } ],
          fade: 0 },
        { id: "cut3", png: "C:/cmgwork/cmg12/cut3.png",
          start: 3496953600000, end: 3945715200000,   // 13.770 ~ 15.520s
          scale: [ { f: 0, v: 100, i: 0 }, { f: 4, v: 104, i: 5 }, { f: "end", v: 108, i: 5 } ],
          fade: 0 }
    ];

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m5_intro.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }
    function T(ticks) { var t = new Time(); t.ticks = String(Math.round(ticks)); return t; }

    for (var c0 = 0; c0 < CUTS.length; c0++)
        if (!new File(CUTS[c0].png).exists) return done("FAILED: 차트가 없다 " + CUTS[c0].png);

    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; }
        catch (e) { say("closeDocument_ERR", e.toString()); break; }
    }
    say("닫은 프로젝트", closed);

    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m5_relink") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);

    var seq = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name === CLONE) seq = app.project.sequences[i];
    if (!seq) return done("FAILED: 복제 시퀀스 없음");
    app.project.activeSequence = seq;

    function census(tag) {
        var lines = [];
        for (var t = 0; t < seq.videoTracks.numTracks; t++) {
            var tr = seq.videoTracks[t], names = [];
            for (var c = 0; c < tr.clips.numItems; c++) {
                var cl = tr.clips[c];
                if (Number(cl.start.ticks) > 17 * TICKS) continue;   // 인트로 구간만
                names.push(cl.name + "@" + (Number(cl.start.ticks) / TICKS).toFixed(2));
            }
            lines.push("V" + t + "(" + tr.clips.numItems + ") " + names.join(" , "));
        }
        say(tag, seq.videoTracks.numTracks + "트랙\n        " + lines.join("\n        "));
    }
    census("트랙 census 전");

    /* ── 1. 트랙 삽입 ─────────────────────────────────────── */
    var before = seq.videoTracks.numTracks;
    app.enableQE();                                   // 반환값은 성패가 아니다
    if (typeof qe === "undefined" || !qe) return done("FAILED: qe 없음");
    var qs = qe.project.getActiveSequence();
    say("qe 시퀀스", qs.name);

    var added = false;
    /*  인자 개수를 모르면 넓은 쪽부터 시도한다. 성공 판정은 반환값이 아니라 트랙 수 증가로 한다  */
    var forms = [
        function () { return qs.addTracks(1, NEW_TRACK, 0, 0, 0, 0, 0, 0); },
        function () { return qs.addTracks(1, NEW_TRACK, 0, 0, 0); },
        function () { return qs.addTracks(1, NEW_TRACK); }
    ];
    for (var fi = 0; fi < forms.length && !added; fi++) {
        var r = "?";
        try { r = String(forms[fi]()); } catch (e) { r = "ERR " + e.toString(); }
        var now = seq.videoTracks.numTracks;
        say("addTracks 형식 " + (fi + 1), "ret=" + r + "  트랙 " + before + " -> " + now);
        if (now === before + 1) added = true;
        else if (now !== before) return done("FAILED: 트랙 수가 예상 밖 " + before + " -> " + now);
    }
    if (!added) return done("FAILED: addTracks 가 트랙을 안 늘렸다");

    var track = seq.videoTracks[NEW_TRACK];
    probe("새 V" + NEW_TRACK + " 클립 수", function () { return track.clips.numItems; });
    if (track.clips.numItems !== 0)
        return done("FAILED: V" + NEW_TRACK + " 가 비어 있지 않다 — 엉뚱한 자리에 들어갔다");
    probe("V" + NEW_TRACK + " 잠금 해제", function () { track.setLocked(0); return "ok"; });

    /* ── 2. import ────────────────────────────────────────── */
    var paths = [];
    for (var p0 = 0; p0 < CUTS.length; p0++) paths.push(CUTS[p0].png);
    probe("importFiles", function () { return app.project.importFiles(paths, 1, app.project.rootItem, 0); });

    function findItem(pngPath) {
        var want = pngPath.toLowerCase(), root = app.project.rootItem;
        for (var i2 = 0; i2 < root.children.numItems; i2++) {
            var ch = root.children[i2], mp = "";
            try { mp = ch.getMediaPath(); } catch (e) { continue; }
            if (mp && mp.split(String.fromCharCode(92)).join("/").toLowerCase() === want) return ch;
        }
        return null;
    }

    /* ── 3. 배치 + 모션 ───────────────────────────────────── */
    function findComp(clip, names) {
        for (var ci = 0; ci < clip.components.numItems; ci++) {
            var cp = clip.components[ci];
            for (var n = 0; n < names.length; n++)
                if (String(cp.displayName) === names[n]) return cp;
        }
        return null;
    }
    function findProp(comp, names) {
        for (var pi = 0; pi < comp.properties.numItems; pi++) {
            var pr = comp.properties[pi];
            for (var n = 0; n < names.length; n++)
                if (String(pr.displayName) === names[n]) return pr;
        }
        return null;
    }

    for (var k = 0; k < CUTS.length; k++) {
        var C = CUTS[k];
        var item = findItem(C.png);
        if (!item) { say(C.id + "_FAIL", "import 항목을 못 찾겠다"); continue; }

        probe(C.id + ".overwriteClip", function () { track.overwriteClip(item, C.start / TICKS); return "ok"; });

        var placed = null;
        for (var q = 0; q < track.clips.numItems; q++)
            if (String(track.clips[q].start.ticks) === String(C.start)) { placed = track.clips[q]; break; }
        if (!placed) { say(C.id + "_FAIL", "놓인 클립을 못 찾겠다"); continue; }

        probe(C.id + ".end 대입", function () { placed.end = T(C.end); return "ok"; });
        say(C.id + ".배치", placed.name + "  " + (Number(placed.start.ticks) / TICKS).toFixed(3) + "s ~ " +
            (Number(placed.end.ticks) / TICKS).toFixed(3) + "s");

        var inTick = Number(placed.inPoint.ticks);
        var durTick = Number(C.end) - Number(C.start);
        say(C.id + ".inPoint", inTick + "  (소스 시각 기준점)");

        var comps = [];
        for (var ci2 = 0; ci2 < placed.components.numItems; ci2++) comps.push(placed.components[ci2].displayName);
        say(C.id + ".컴포넌트", comps.join(" · "));

        var motion = findComp(placed, ["모션", "Motion"]);
        if (!motion) { say(C.id + "_FAIL", "모션 컴포넌트 없음"); continue; }
        var props = [];
        for (var pi2 = 0; pi2 < motion.properties.numItems; pi2++) props.push(motion.properties[pi2].displayName);
        say(C.id + ".모션 속성", props.join(" · "));

        /*  속성 이름은 '비율' 이 아니라 '비율 조정' 이다 (실측).
            같은 모션 안에 '폭 비율 조정'·'균일 비율' 도 있어서 부분일치로 잡으면 엉뚱한 걸 잡는다  */
        var scale = findProp(motion, ["비율 조정", "Scale"]);
        if (!scale) { say(C.id + "_FAIL", "비율 속성 없음"); continue; }
        probe(C.id + ".scale.setTimeVarying", function () { scale.setTimeVarying(true); return "ok"; });

        for (var s = 0; s < C.scale.length; s++) {
            var K = C.scale[s];
            /*  마지막 키는 클립 끝 틱이 아니라 끝-1프레임에 둔다.
                끝 틱은 클립에 포함되지 않는 경계라, 거기 찍으면 실제 렌더되는 마지막
                프레임이 목표값에 못 미친 채로 끝난다.  */
            var off = (K.f === "end") ? (durTick - F2997) : K.f * F2997;   // 모션은 29.97 격자
            var tk = T(inTick + off);
            try { scale.addKey(tk); } catch (e) { say(C.id + ".비율#" + s + ".addKey_ERR", e.toString()); }
            try { scale.setValueAtKey(tk, K.v, true); } catch (e) { say(C.id + ".비율#" + s + ".setValue_ERR", e.toString()); }
            try { scale.setInterpolationTypeAtKey(tk, K.i, true); } catch (e) { say(C.id + ".비율#" + s + ".setInterp_ERR", e.toString()); }
            say(C.id + ".비율 키 " + s, "off=" + (off / F2997).toFixed(4) + "f@29.97  값=" + K.v +
                "  보간=" + K.i + "  틱=" + tk.ticks);
        }

        if (C.fade > 0) {
            var opComp = findComp(placed, ["불투명도", "Opacity"]);
            var op = opComp ? findProp(opComp, ["불투명도", "Opacity"]) : null;
            if (!op) say(C.id + ".불투명도", "속성을 못 찾겠다 — 페이드 생략");
            else {
                probe(C.id + ".op.setTimeVarying", function () { op.setTimeVarying(true); return "ok"; });
                var t0 = T(inTick), t1 = T(inTick + C.fade * F2997);
                try { op.addKey(t0); op.setValueAtKey(t0, 0, true); op.setInterpolationTypeAtKey(t0, 0, true); }
                catch (e) { say(C.id + ".op0_ERR", e.toString()); }
                try { op.addKey(t1); op.setValueAtKey(t1, 100, true); op.setInterpolationTypeAtKey(t1, 5, true); }
                catch (e) { say(C.id + ".op1_ERR", e.toString()); }
                say(C.id + ".불투명도", "0 -> 100  " + C.fade + "프레임@29.97");
            }
        }
    }

    census("트랙 census 후");

    /*  §M4-a 함정 20 의 변종: 직전 실행의 산출물이 방금 닫혔어도 프리미어가 파일을
        잠고 있어 saveAs 가 예외 없이 false 를 준다. 미리 지우고 저장한다.  */
    var prev = new File(OUT);
    if (prev.exists) say("기존 출력 삭제", prev.remove());

    var ok = false;
    probe("saveAs", function () { ok = app.project.saveAs(OUT); return ok; });
    if (!ok) { $.sleep(1500); probe("saveAs 재시도", function () { ok = app.project.saveAs(OUT); return ok; }); }
    say("out_size", new File(OUT).exists ? new File(OUT).length : "(없음)");
    return done("m5_intro " + (ok ? "ok" : "FAILED"));
})();
