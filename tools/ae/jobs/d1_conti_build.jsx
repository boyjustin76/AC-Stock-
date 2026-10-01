/*  D1 — 차트 장면 콘티를 AE 프로젝트로 세팅한다 (next_step 45 ②, 2026-09-22).

    입력: <AE작업실>/conti_in.json  — tools/mt5/conti_sheet.py 가 쓴다 (batch_capture 결과에서).
    출력: conti_in.json 의 aep 자리 (기본 <AE작업실>/conti/<회차>_차트장면.aep)

      · 비트마다 컴포지션 하나  <회차>_<비트>  1920x1080 · 59.94fps · 길이는 json 의 sec
          - 차트 그림(MT5 캡처) 한 장 — 가로를 컴포지션 폭에 맞춘다
          - 가이드 레이어 둘: 대본 문장 · 고른 이유  (가이드라 렌더에 안 나온다 — 편집자가 보는 메모)
      · 전체 컴포지션  <회차>_전체  — 비트 컴포지션을 차례로 이어 붙인다
      · 폴더: 01_비트 · 02_그림

    길이는 추정값이다(대본 글자 수 ÷ 초당 글자수). 타임코드가 오면 json 의 sec 만 바꾸면 된다.
    자막·타이틀·로고는 넣지 않는다 (프리미어 프리셋에 있다 — CLAUDE.md).

    판정 줄: 로그 d1_conti_build.txt 에 `판정 <…>` 을 done()/fail() 이 쓴다 (실행기가 이 줄로 성공을 정한다).

    쓰는 법:  python tools/mt5/conti_sheet.py <콘티폴더> --title 차10
              .\tools\ae\run.ps1 d1_conti_build
*/
$.evalFile(new File(String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/") + "/_lib.jsx"));
logTo("d1_conti_build");

function readJson(p) {
    var f = new File(p);
    if (!f.exists) throw new Error("없다: " + p);
    f.encoding = "UTF-8"; f.open("r"); var t = f.read(); f.close();
    return eval("(" + t.replace(/^﻿/, "") + ")");     // ExtendScript 에 JSON 이 없는 판이 있다
}

function __main() {
    var cfg = null;
    probe("conti_in.json", function () { cfg = readJson(LAB + "/conti_in.json"); return cfg.title + " · 비트 " + cfg.beats.length; });
    if (!cfg) { flush(); return fail("conti_in.json 을 못 읽었다 — conti_sheet.py 를 먼저 돌려라"); }

    var W = cfg.w, H = cfg.h, FPS = cfg.fps;
    say("AE", app.version);
    say("길이 근거", cfg["길이_근거"]);
    closeQuietly();
    app.newProject();

    var P = app.project;
    var fBeat = P.items.addFolder("01_비트");
    var fImg  = P.items.addFolder("02_그림");

    var comps = [], missing = [], total = 0;
    for (var i = 0; i < cfg.beats.length; i++) {
        var b = cfg.beats[i];
        var c = P.items.addComp(cfg.title + "_" + b.id, W, H, 1, b.sec, FPS);
        c.parentFolder = fBeat;

        var f = new File(b.png);
        if (b.png && f.exists) {
            var it = P.importFile(new ImportOptions(f));
            it.parentFolder = fImg;
            var L = c.layers.add(it);
            L.name = "차트 " + b.id;
            var s = 100 * W / it.width;                     // 가로를 맞춘다 (MT5 판 1920x915 → 그대로)
            L.property("Scale").setValue([s, s]);
            L.property("Position").setValue([W / 2, H / 2]);
        } else {
            missing.push(b.id);
        }

        var t1 = c.layers.addText(b.text.substr(0, 120));
        t1.name = "메모: 대본"; t1.guideLayer = true;
        t1.property("Position").setValue([60, 80]);
        var t2 = c.layers.addText(b.why.substr(0, 120));
        t2.name = "메모: 왜 이 장면"; t2.guideLayer = true;
        t2.property("Position").setValue([60, H - 60]);
        // 글자 크기·정렬 — 메모라 가볍게만
        var docs = [t1, t2];
        for (var k = 0; k < docs.length; k++) {
            var sp = docs[k].property("Source Text"), d = sp.value;
            d.fontSize = 28; d.justification = ParagraphJustification.LEFT_JUSTIFY;
            d.applyFill = true; d.fillColor = [0.9, 0.1, 0.1];
            sp.setValue(d);
        }
        comps.push(c);
        total += b.sec;
    }

    var master = P.items.addComp(cfg.title + "_전체", W, H, 1, total, FPS);
    var at = 0;
    for (var j = 0; j < comps.length; j++) {
        var ML = master.layers.add(comps[j]);
        ML.startTime = at;
        at += comps[j].duration;
    }
    // layers.add 는 맨 위에 쌓는다 — 순서는 시간으로 정해져 있으니 쌓임은 상관없다
    try { master.openInViewer(); } catch (e) { }          // 열자마자 전체가 보이게 (09-22: 빈 뷰어였다)
    say("비트 컴포지션", comps.length);
    say("전체 길이", total.toFixed(1) + "s · 레이어 " + master.numLayers);
    if (missing.length) say("그림 없는 비트", missing.join(","));

    probe("저장", function () {
        var out = new File(cfg.aep);
        if (!out.parent.exists) out.parent.create();
        if (out.exists) out.remove();
        P.save(out);
        return out.exists ? out.length + " bytes" : "파일이 없다";
    });
    var saved = new File(cfg.aep).exists;
    flush();
    if (!saved) return fail("aep 가 안 써졌다: " + cfg.aep);
    if (missing.length) return fail("그림이 없는 비트가 있다: " + missing.join(","));
    return done("비트 " + comps.length + " · 전체 " + total.toFixed(1) + "s · " + cfg.aep);
}
__main();
