/*
    M6. 차명12 인트로 시퀀스를 **처음부터 만든다.**

    지금까지는 회사 프리셋 시퀀스를 복제해서 손봤다. 이번엔 빈 시퀀스를 새로 만들고
    컷을 층으로 쌓는다 — 포토샵 레이어 그룹과 같은 구조다.

        V4  텍스트      글자 라벨 · 밑줄          (알파)
        V3  매수매도    화살표 태그               (알파)
        V2  강조        강조원 · 손실 밴드 · 진입선 (알파)
        V1  이평선      5·20 이평선               (알파)
        V0  캔들        캔들 + 흰 배경            (불투명, 스택의 바닥)

    층이 어긋나지 않는 이유: 렌더러에서 차트를 안 그려도 좌표계(scale/viewport)는
    똑같이 계산된다(`showCandles`/`showMAs` 는 그리기만 끈다). 그래서 오버레이 층만
    렌더해도 캔들 층과 픽셀 단위로 겹친다. chart 설정(reveal·zoom)은 층마다 동일하다.

    ── 실측해서 알아낸 것 (m6_probe / m6_probe2) ──────────────────────────
    · app.project.createNewSequence(name, id) 는 **'새 시퀀스' 모달을 띄운다.**
      BridgeTalk 가 영영 안 돌아온다. 쓰면 안 된다.
    · qe.project.newSequence(name, path) 는 true 를 돌려주고 **아무것도 안 만든다.**
    · app.project.newSequence(name, 역슬래시경로) 가 정답. 슬래시면 실패한다.
    · 프리미어 기본 프리셋에 30.0 이 없다(29.97 뿐). 회사 timebase 는 30.0 이라
      29.97 프리셋을 복사해 VideoFrameRate 만 바꾼 것을 쓴다
      (tools/premiere/presets/차트명가_1080p_30fps.sqpreset).

    시각은 **대본 절대 시각 그대로** 둔다(0~3.4초는 빈 채로). 회차 시퀀스에 중첩하거나
    붙여넣을 때 그대로 떨어지게 하기 위해서다.

    ⚠ 매 줄마다 로그를 flush 한다. 모달이 뜨면 어디서 멈췄는지 남아야 한다.
*/
(function () {
    var BS = String.fromCharCode(92);
    var SRC = "C:/pprolab/m5_relink.prproj";      // 릴링크된 프리셋 프로젝트 — 옆에 나란히 만든다
    var OUT = "C:/pprolab/m6_build.prproj";
    var PRESET = ("C:/pprolab/cmg_1080p_30fps.sqpreset").split("/").join(BS);
    var ROOT = "C:/Users/user/Desktop/이정찬/Claude/AC-Stock-/out/cmg12/layers/";
    var SEQNAME = "차명12_인트로_레이어";
    var LOG = "C:/pprolab/m6_build.txt";

    var TICKS = 254016000000;
    var F2997 = 8475667200;

    /*  컷 — 대본 자막 초를 30.0 격자로 반올림한 값. 카메라 워크도 여기 붙는다.
        같은 컷의 모든 층에 **똑같은** 비율 키를 준다. 하나라도 다르면 층이 어긋난다.  */
    var CUTS = {
        "cut1-rule":        { start:  863654400000, end: 1879718400000,
                              scale: [ { f: 0, v: 100,   i: 0 }, { f: "end", v: 103.5, i: 5 } ], fade: 6 },
        "cut2-bed":         { start: 1879718400000, end: 3098995200000,
                              scale: [ { f: 0, v: 103.5, i: 0 }, { f: "end", v: 106.5, i: 5 } ], fade: 0 },
        "cut3-loss":        { start: 3098995200000, end: 3496953600000,
                              scale: [ { f: 0, v: 106.5, i: 0 }, { f: "end", v: 101,   i: 5 } ], fade: 0 },
        "cut4-signal-only": { start: 3496953600000, end: 3945715200000,
                              scale: [ { f: 0, v: 100,   i: 0 }, { f: "end", v: 103,   i: 5 } ], fade: 0 }
    };

    var ALL4 = ["cut1-rule", "cut2-bed", "cut3-loss", "cut4-signal-only"];
    var NOBED = ["cut1-rule", "cut3-loss", "cut4-signal-only"];   // 컷2 는 라벨이 없어 그릴 게 없다

    /*  아래에서 위로. track 은 프리미어 V 번호와 같다.  */
    var LAYERS = [
        { track: 0, dir: "1_candle", bin: "1_캔들",     ext: "mp4", cuts: ALL4 },
        { track: 1, dir: "2_ma",     bin: "2_이평선",   ext: "mov", cuts: ALL4 },
        { track: 2, dir: "3_mark",   bin: "3_강조",     ext: "mov", cuts: NOBED },
        { track: 3, dir: "4_tag",    bin: "4_매수매도", ext: "mov", cuts: NOBED },
        { track: 4, dir: "5_text",   bin: "5_텍스트",   ext: "mov", cuts: NOBED }
    ];

    var out = [];
    function flush() {
        var f = new File(LOG);
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    }
    function say(k, v) { out.push(k + "\t" + v); flush(); }
    function probe(k, fn) {
        say(k, "…호출 직전");
        var r; try { r = String(fn()); } catch (e) { r = "ERR " + e.toString(); }
        out[out.length - 1] = k + "\t" + r; flush();
        return r;
    }
    function fail(m) { say("FAILED", m); return "FAILED: " + m; }
    function T(t) { var x = new Time(); x.ticks = String(Math.round(t)); return x; }

    /* ── 0. 렌더 결과가 다 있는지 먼저 본다 ─────────────────────── */
    var missing = [], total = 0;
    for (var a = 0; a < LAYERS.length; a++) {
        for (var b = 0; b < LAYERS[a].cuts.length; b++) {
            var p = ROOT + LAYERS[a].dir + "/" + LAYERS[a].cuts[b] + "." + LAYERS[a].ext;
            total++;
            if (!new File(p).exists) missing.push(p);
        }
    }
    say("렌더 클립", (total - missing.length) + " / " + total);
    if (missing.length) return fail("렌더 결과 없음:\n        " + missing.join("\n        "));
    say("프리셋", new File(PRESET.split(BS).join("/")).exists + "  " + PRESET);

    /* ── 1. 프로젝트 열기 ───────────────────────────────────────── */
    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; }
        catch (e) { say("closeDocument_ERR", e.toString()); break; }
    }
    say("닫은 프로젝트", closed);

    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m5_relink") >= 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);
    say("기존 시퀀스", app.project.sequences.numSequences);

    /* ── 2. 시퀀스를 새로 만든다 ────────────────────────────────── */
    var n0 = app.project.sequences.numSequences;
    probe("newSequence", function () { return app.project.newSequence(SEQNAME, PRESET); });
    if (app.project.sequences.numSequences !== n0 + 1)
        return fail("시퀀스가 안 만들어졌다 " + n0 + " -> " + app.project.sequences.numSequences);

    var seq = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name === SEQNAME) seq = app.project.sequences[i];
    if (!seq) return fail("이름으로 못 찾겠다: " + SEQNAME);
    app.project.activeSequence = seq;
    say("새 시퀀스", "timebase=" + seq.timebase + "  " + seq.frameSizeHorizontal + "x" + seq.frameSizeVertical +
        "  V" + seq.videoTracks.numTracks + " A" + seq.audioTracks.numTracks);
    if (String(seq.timebase) !== "8467200000")
        return fail("timebase 가 30.0 이 아니다: " + seq.timebase);

    /* ── 3. 트랙을 층 수만큼 확보한다 ───────────────────────────── */
    app.enableQE();
    if (typeof qe === "undefined" || !qe) return fail("qe 없음");
    var qs = qe.project.getActiveSequence();
    var need = LAYERS.length - seq.videoTracks.numTracks;
    if (need > 0) {
        var v0 = seq.videoTracks.numTracks;
        probe("addTracks(+" + need + ")", function () { return qs.addTracks(need, v0, 0, 0, 0, 0, 0, 0); });
    }
    say("V 트랙", seq.videoTracks.numTracks);
    if (seq.videoTracks.numTracks < LAYERS.length) return fail("트랙이 모자란다");

    /*  트랙 이름 — 포토샵 레이어 이름에 해당한다. 되면 좋고 안 되면 그냥 넘어간다  */
    for (var t2 = 0; t2 < LAYERS.length; t2++) {
        var qt = null;
        try { qt = qs.getVideoTrackAt(t2); } catch (e) {}
        if (qt && typeof qt.setName === "function") {
            try { qt.setName(LAYERS[t2].bin); } catch (e) { say("setName_ERR V" + t2, e.toString()); }
        }
    }
    var tn = [];
    for (var t3 = 0; t3 < LAYERS.length; t3++) tn.push("V" + t3 + "=" + seq.videoTracks[t3].name);
    say("트랙 이름", tn.join("  "));

    /* ── 4. 층마다 빈을 만들고 import ───────────────────────────── */
    var rootBin = null;
    probe("createBin(차명12 인트로)", function () {
        rootBin = app.project.rootItem.createBin("차명12 인트로 레이어");
        return rootBin ? rootBin.name : "null";
    });
    if (!rootBin) return fail("빈을 못 만들겠다");

    function findIn(bin, wantPath) {
        var want = wantPath.toLowerCase();
        for (var i2 = 0; i2 < bin.children.numItems; i2++) {
            var ch = bin.children[i2], mp = "";
            try { mp = ch.getMediaPath(); } catch (e) { continue; }
            if (mp && mp.split(BS).join("/").toLowerCase() === want) return ch;
        }
        return null;
    }
    function findComp(clip, names) {
        for (var ci = 0; ci < clip.components.numItems; ci++) {
            var cp = clip.components[ci];
            for (var n = 0; n < names.length; n++) if (String(cp.displayName) === names[n]) return cp;
        }
        return null;
    }
    function findProp(comp, names) {
        for (var pi = 0; pi < comp.properties.numItems; pi++) {
            var pr = comp.properties[pi];
            for (var n = 0; n < names.length; n++) if (String(pr.displayName) === names[n]) return pr;
        }
        return null;
    }

    var placedCount = 0, kfCount = 0;

    for (var li = 0; li < LAYERS.length; li++) {
        var L = LAYERS[li];
        var bin = null;
        try { bin = rootBin.createBin(L.bin); } catch (e) { say("createBin_ERR " + L.bin, e.toString()); }
        if (!bin) return fail("빈 실패: " + L.bin);

        var paths = [];
        for (var c1 = 0; c1 < L.cuts.length; c1++) paths.push(ROOT + L.dir + "/" + L.cuts[c1] + "." + L.ext);
        probe("import " + L.bin, function () { return app.project.importFiles(paths, 1, bin, 0); });

        var track = seq.videoTracks[L.track];
        try { track.setLocked(0); } catch (e) {}

        for (var c2 = 0; c2 < L.cuts.length; c2++) {
            var cid = L.cuts[c2];
            var C = CUTS[cid];
            var want = ROOT + L.dir + "/" + cid + "." + L.ext;
            var item = findIn(bin, want);
            if (!item) { say(L.bin + "/" + cid, "FAIL — import 항목을 못 찾겠다"); continue; }

            var startSec = C.start / TICKS;
            (function (track, item, startSec) {
                try { track.overwriteClip(item, startSec); } catch (e) { say("overwrite_ERR", e.toString()); }
            })(track, item, startSec);

            var placed = null;
            for (var q = 0; q < track.clips.numItems; q++)
                if (String(track.clips[q].start.ticks) === String(C.start)) { placed = track.clips[q]; break; }
            if (!placed) { say(L.bin + "/" + cid, "FAIL — 놓인 클립을 못 찾겠다"); continue; }

            var natural = Number(placed.end.ticks) - Number(placed.start.ticks);
            try { placed.end = T(C.end); } catch (e) { say("end_ERR", e.toString()); }
            var durTick = Number(C.end) - Number(C.start);
            placedCount++;

            /*  카메라 워크 — 같은 컷의 모든 층에 똑같이  */
            var inTick = Number(placed.inPoint.ticks);
            var motion = findComp(placed, ["모션", "Motion"]);
            var scale = motion ? findProp(motion, ["비율 조정", "Scale"]) : null;
            if (scale) {
                try { scale.setTimeVarying(true); } catch (e) {}
                for (var s = 0; s < C.scale.length; s++) {
                    var K = C.scale[s];
                    /*  마지막 키는 클립 끝이 아니라 끝-1프레임. 끝 틱은 포함되지 않는 경계다  */
                    var off = (K.f === "end") ? (durTick - F2997) : K.f * F2997;
                    var tk = T(inTick + off);
                    try { scale.addKey(tk); scale.setValueAtKey(tk, K.v, true);
                          scale.setInterpolationTypeAtKey(tk, K.i, true); kfCount++; }
                    catch (e) { say("kf_ERR " + L.bin + "/" + cid + "#" + s, e.toString()); }
                }
            } else say(L.bin + "/" + cid, "비율 조정 속성 없음");

            if (C.fade > 0) {
                var opComp = findComp(placed, ["불투명도", "Opacity"]);
                var op = opComp ? findProp(opComp, ["불투명도", "Opacity"]) : null;
                if (op) {
                    try {
                        op.setTimeVarying(true);
                        var t0 = T(inTick), t1 = T(inTick + C.fade * F2997);
                        op.addKey(t0); op.setValueAtKey(t0, 0, true); op.setInterpolationTypeAtKey(t0, 0, true);
                        op.addKey(t1); op.setValueAtKey(t1, 100, true); op.setInterpolationTypeAtKey(t1, 5, true);
                        kfCount += 2;
                    } catch (e) { say("op_ERR " + L.bin + "/" + cid, e.toString()); }
                }
            }

            say("V" + L.track + " " + L.bin + " / " + cid,
                (Number(placed.start.ticks) / TICKS).toFixed(3) + "s ~ " +
                (Number(placed.end.ticks) / TICKS).toFixed(3) + "s" +
                "   렌더 " + (natural / TICKS).toFixed(4) + "s / 컷 " + (durTick / TICKS).toFixed(4) + "s" +
                "   남는 프레임 " + ((natural - durTick) / F2997).toFixed(2));
        }
    }

    /* ── 5. 결과 census ─────────────────────────────────────────── */
    var lines = [];
    for (var t4 = 0; t4 < seq.videoTracks.numTracks; t4++) {
        var tr = seq.videoTracks[t4], names = [];
        for (var c3 = 0; c3 < tr.clips.numItems; c3++) {
            var cl = tr.clips[c3];
            names.push(cl.name + "@" + (Number(cl.start.ticks) / TICKS).toFixed(2) +
                       "~" + (Number(cl.end.ticks) / TICKS).toFixed(2));
        }
        lines.push("V" + t4 + " [" + tr.name + "] " + tr.clips.numItems + "개 :: " + names.join(" , "));
    }
    say("층 census", "\n        " + lines.join("\n        "));
    say("놓은 클립", placedCount + " / " + total);
    say("찍은 키프레임", kfCount);
    say("시퀀스 길이", (Number(seq.end) / TICKS).toFixed(3) + "s");

    var prev = new File(OUT);
    if (prev.exists) say("기존 출력 삭제", prev.remove());
    var ok = false;
    probe("saveAs", function () { ok = app.project.saveAs(OUT); return ok; });
    if (!ok) { $.sleep(1500); probe("saveAs 재시도", function () { ok = app.project.saveAs(OUT); return ok; }); }
    say("out_size", new File(OUT).exists ? new File(OUT).length : "(없음)");
    return "m6_build " + (ok ? "ok" : "FAILED");
})();
