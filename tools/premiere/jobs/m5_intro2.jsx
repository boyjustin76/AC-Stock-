/*
    M5-d. 차명12 인트로 4컷 — 영상 클립으로 조립한다.

    M5-b 는 정지 이미지 3장이었다. 그러면 렌더러가 만든 레이어 애니메이션(원이 그려지고
    태그가 튀어나오고 밴드가 자라는 것)이 전부 죽는다. 이 저장소의 산출물은 원래
    '차트만 있는 영상 클립' 이다(README). 그래서 mp4 로 바꿨다.

    역할 분담을 이렇게 잡았다 —
      · 렌더러 : 차트 안에서 벌어지는 일 (봉 드러남, 원, 태그, 밴드, 데이터 확대)
      · 프리미어 : 카메라 워크 (밀고 당기기) 와 페이드
    회사 프리셋의 모션이 프리미어 쪽에 들어 있어서, 편집자가 나중에 손볼 수 있어야 한다.

    컷을 넷으로 나눈 이유는 프레임을 뽑아 보고 알았다 (jobs/m5_frames.jsx 실측).
    프리셋의 5.93~12.20 은 인트로 애니메이션 + 타이틀 카드가 화면의 주인공이라,
    거기에 라벨 붙은 차트를 깔면 매수/매도 태그가 두 벌로 겹친다.
    그 구간(컷2)은 라벨 없는 배경으로 깔고, 프리셋이 비는 12.20 부터 다시 이야기한다.

        컷1  3.400~ 7.400  공식을 짚는다        비율 100 -> 103.5   다가간다
             + 불투명도 0 -> 100 (6프레임)       처음 등장이라 여기만 페이드
        컷2  7.400~12.200  조용한 배경          비율 103.5 -> 106.5 아주 완만
        컷3 12.200~13.767  손실이 드러난다      비율 106.5 -> 101   물러나며 전체를 본다
        컷4 13.767~15.533  크로스 신호 하나     비율 100 -> 103     (데이터 확대는 렌더러가)

    격자(실측): 컷 경계는 30.0, 모션 키프레임은 29.97.
    키프레임 시각은 타임라인 시각이 아니라 소스 시각 — clip.inPoint 기준.
*/
(function () {
    var SRC = "C:/pprolab/m5_relink.prproj";
    var OUT = "C:/pprolab/m5_intro2.prproj";
    /*  out/ 은 gitignore 라 프로젝트가 참조하면 다른 PC 에서 오프라인이 된다.
        납품 폴더(저장소에 커밋되는 자리)를 가리킨다.  */
    var REND = "C:/Users/user/Desktop/이정찬/Claude/AC-Stock-/deliver/cutscene/차12_RSI+이평선 스캘핑/";
    var CLONE = "롱폼 고정 양식 복사";

    var TICKS = 254016000000;          // 1초
    var F2997 = 8475667200;            // 1프레임 @29.97
    var NEW_TRACK = 2;                 // 흰 배경 위 · 그래픽 아래

    var CUTS = [
        { id: "cut1", mp4: REND + "컷1_교과서공식.mp4",
          start:  863654400000, end: 1879718400000,   //  3.400 ~  7.400s
          scale: [ { f: 0, v: 100, i: 0 }, { f: "end", v: 103.5, i: 5 } ],
          fade: 6 },
        { id: "cut2", mp4: REND + "컷2_조용한배경.mp4",
          start: 1879718400000, end: 3098995200000,   //  7.400 ~ 12.200s
          scale: [ { f: 0, v: 103.5, i: 0 }, { f: "end", v: 106.5, i: 5 } ],
          fade: 0 },
        { id: "cut3", mp4: REND + "컷3_공식대로_손실.mp4",
          start: 3098995200000, end: 3496953600000,   // 12.200 ~ 13.767s
          scale: [ { f: 0, v: 106.5, i: 0 }, { f: "end", v: 101, i: 5 } ],
          fade: 0 },
        { id: "cut4", mp4: REND + "컷4_크로스신호하나.mp4",
          start: 3496953600000, end: 3945715200000,   // 13.767 ~ 15.533s
          scale: [ { f: 0, v: 100, i: 0 }, { f: "end", v: 103, i: 5 } ],
          fade: 0 }
    ];

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }
    function done(m) {
        var f = new File("C:/pprolab/m5_intro2.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }
    function T(ticks) { var t = new Time(); t.ticks = String(Math.round(ticks)); return t; }

    for (var c0 = 0; c0 < CUTS.length; c0++)
        if (!new File(CUTS[c0].mp4).exists) return done("FAILED: 렌더 결과가 없다 " + CUTS[c0].mp4);

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
                if (Number(cl.start.ticks) > 17 * TICKS) continue;
                names.push(cl.name + "@" + (Number(cl.start.ticks) / TICKS).toFixed(2));
            }
            lines.push("V" + t + "(" + tr.clips.numItems + ") " + names.join(" , "));
        }
        say(tag, seq.videoTracks.numTracks + "트랙\n        " + lines.join("\n        "));
    }
    census("트랙 census 전");

    /* ── 트랙 삽입 ────────────────────────────────────────── */
    var before = seq.videoTracks.numTracks;
    app.enableQE();
    if (typeof qe === "undefined" || !qe) return done("FAILED: qe 없음");
    var qs = qe.project.getActiveSequence();
    probe("addTracks", function () { return qs.addTracks(1, NEW_TRACK, 0, 0, 0, 0, 0, 0); });
    if (seq.videoTracks.numTracks !== before + 1)
        return done("FAILED: 트랙 " + before + " -> " + seq.videoTracks.numTracks);

    var track = seq.videoTracks[NEW_TRACK];
    if (track.clips.numItems !== 0)
        return done("FAILED: V" + NEW_TRACK + " 가 비어 있지 않다 — 엉뚱한 자리에 들어갔다");
    probe("V" + NEW_TRACK + " 잠금 해제", function () { track.setLocked(0); return "ok"; });

    /* ── import ───────────────────────────────────────────── */
    var paths = [];
    for (var p0 = 0; p0 < CUTS.length; p0++) paths.push(CUTS[p0].mp4);
    probe("importFiles", function () { return app.project.importFiles(paths, 1, app.project.rootItem, 0); });

    function findItem(mp4Path) {
        var want = mp4Path.toLowerCase(), root = app.project.rootItem;
        for (var i2 = 0; i2 < root.children.numItems; i2++) {
            var ch = root.children[i2], mp = "";
            try { mp = ch.getMediaPath(); } catch (e) { continue; }
            if (mp && mp.split(String.fromCharCode(92)).join("/").toLowerCase() === want) return ch;
        }
        return null;
    }
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

    /* ── 배치 + 모션 ──────────────────────────────────────── */
    for (var k = 0; k < CUTS.length; k++) {
        var C = CUTS[k];
        var item = findItem(C.mp4);
        if (!item) { say(C.id + "_FAIL", "import 항목을 못 찾겠다"); continue; }

        probe(C.id + ".overwriteClip", function () { track.overwriteClip(item, C.start / TICKS); return "ok"; });

        var placed = null;
        for (var q = 0; q < track.clips.numItems; q++)
            if (String(track.clips[q].start.ticks) === String(C.start)) { placed = track.clips[q]; break; }
        if (!placed) { say(C.id + "_FAIL", "놓인 클립을 못 찾겠다"); continue; }

        var natural = Number(placed.end.ticks) - Number(placed.start.ticks);
        probe(C.id + ".end 대입", function () { placed.end = T(C.end); return "ok"; });
        var durTick = Number(C.end) - Number(C.start);
        say(C.id + ".배치", placed.name + "  " + (Number(placed.start.ticks) / TICKS).toFixed(3) + "s ~ " +
            (Number(placed.end.ticks) / TICKS).toFixed(3) + "s" +
            "   렌더 길이 " + (natural / TICKS).toFixed(4) + "s / 컷 길이 " + (durTick / TICKS).toFixed(4) + "s" +
            "   남는 프레임 " + ((natural - durTick) / F2997).toFixed(2));

        var inTick = Number(placed.inPoint.ticks);
        say(C.id + ".inPoint", inTick);

        var motion = findComp(placed, ["모션", "Motion"]);
        if (!motion) { say(C.id + "_FAIL", "모션 컴포넌트 없음"); continue; }
        /*  속성 이름은 '비율' 이 아니라 '비율 조정' 이다 (실측).
            같은 모션 안에 '폭 비율 조정'·'균일 비율' 도 있어서 부분일치로 잡으면 엉뚱한 걸 잡는다  */
        var scale = findProp(motion, ["비율 조정", "Scale"]);
        if (!scale) { say(C.id + "_FAIL", "비율 조정 속성 없음"); continue; }
        probe(C.id + ".scale.setTimeVarying", function () { scale.setTimeVarying(true); return "ok"; });

        for (var s = 0; s < C.scale.length; s++) {
            var K = C.scale[s];
            /*  마지막 키는 클립 끝 틱이 아니라 끝-1프레임에 둔다.
                끝 틱은 클립에 포함되지 않는 경계라, 거기 찍으면 실제 렌더되는 마지막
                프레임이 목표값에 못 미친 채로 끝난다.  */
            var off = (K.f === "end") ? (durTick - F2997) : K.f * F2997;
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

    var prev = new File(OUT);
    if (prev.exists) say("기존 출력 삭제", prev.remove());
    var ok = false;
    probe("saveAs", function () { ok = app.project.saveAs(OUT); return ok; });
    if (!ok) { $.sleep(1500); probe("saveAs 재시도", function () { ok = app.project.saveAs(OUT); return ok; }); }
    say("out_size", new File(OUT).exists ? new File(OUT).length : "(없음)");
    return done("m5_intro2 " + (ok ? "ok" : "FAILED"));
})();
