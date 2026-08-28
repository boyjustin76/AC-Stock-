/*
    M5-a. 프리셋 미디어를 이 PC 의 실제 경로로 다시 연결한다.

    왜 D: 가 박혀 있었나 —
      프리셋을 만든 편집자 PC 는 회사 구글 드라이브를 D:\01_구글 드라이브(파가드AC)\ 로
      마운트했다. 이 PC 는 같은 드라이브를 G:\내 드라이브\ 로 붙인다.
      prproj 는 절대경로를 저장하므로, 드라이브 문자만 다른 게 아니라 최상위 폴더 이름까지
      다르다. 그래서 프리미어가 자동으로 못 찾고 전부 오프라인이 됐다.

        D:\01_구글 드라이브(파가드AC)\트레이딩팩토리\...
        G:\내 드라이브\트레이딩팩토리\...
                                    ^^^ 이 아래는 같다

    변환은 드라이브 문자만 바꾸는 게 아니라 '앞 두 마디를 G:\내 드라이브 로 갈아끼우는' 것이다.
    경로를 문자열로 조작하기 전에 파일이 실제로 있는지 File.exists 로 확인하고,
    없으면 건드리지 않는다 (엉뚱한 데로 연결하느니 오프라인이 낫다).
*/
(function () {
    var SRC = "C:/pprolab/m4_purged.prproj";
    var OUT = "C:/pprolab/m5_relink.prproj";
    var BS = String.fromCharCode(92);
    var NEW_ROOT = "G:" + BS + "내 드라이브" + BS;

    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function done(m) {
        var f = new File("C:/pprolab/m5_relink.txt");
        f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
        return m;
    }

    var closed = 0;
    for (var g = 0; g < 50 && app.projects.numProjects > 0; g++) {
        try { app.projects[app.projects.numProjects - 1].closeDocument(0, 0); closed++; }
        catch (e) { say("closeDocument_ERR", e.toString()); break; }
    }
    say("닫은 프로젝트", closed);

    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180 && !(app.project && app.project.path.indexOf("m4_purged") >= 0
                        && app.project.sequences.numSequences > 0)) { $.sleep(500); w += 0.5; }
    say("project.path", app.project.path);

    function walk(item, fn) {
        for (var i = 0; i < item.children.numItems; i++) {
            var ch = item.children[i];
            fn(ch);
            try { if (ch.type === ProjectItemType.BIN) walk(ch, fn); } catch (e) {}
        }
    }

    /*  D:\<드라이브 폴더>\트레이딩팩토리\... 에서 앞 두 마디를 떼고 G:\내 드라이브\ 를 붙인다  */
    function toLocal(p) {
        var parts = p.split(BS);
        if (parts.length < 3) return null;
        if (parts[0].toUpperCase() !== "D:") return null;
        return NEW_ROOT + parts.slice(2).join(BS);
    }

    var targets = [];
    walk(app.project.rootItem, function (ch) {
        var mp = "";
        try { mp = ch.getMediaPath(); } catch (e) { return; }
        if (!mp) return;
        var n = toLocal(mp);
        if (n) targets.push({ item: ch, from: mp, to: n });
    });
    say("대상 항목", targets.length);

    var okCnt = 0, missCnt = 0, failCnt = 0;
    for (var t = 0; t < targets.length; t++) {
        var T = targets[t];
        var tag = "[" + (t + 1) + "] " + T.item.name;

        if (!new File(T.to).exists) { say(tag, "MISS  실제 파일이 없다 :: " + T.to); missCnt++; continue; }

        var can = "?";
        try { can = String(T.item.canChangeMediaPath(T.to)); } catch (e) { can = "ERR " + e.toString(); }

        var res = "?";
        try { res = String(T.item.changeMediaPath(T.to, true)); }
        catch (e) {
            /* 인자 하나만 받는 빌드일 수 있다 */
            try { res = String(T.item.changeMediaPath(T.to)); }
            catch (e2) { res = "ERR " + e2.toString(); }
        }

        /*  §3-4 : 반환값을 믿지 않는다. 실제 경로를 다시 읽어서 확인한다  */
        var now = "";
        try { now = T.item.getMediaPath(); } catch (e) {}
        var offline = "?";
        try { offline = String(T.item.isOffline()); } catch (e) {}

        var moved = (now.toLowerCase() === T.to.toLowerCase());
        if (moved) okCnt++; else failCnt++;
        say(tag, (moved ? "OK  " : "FAIL") + "  can=" + can + " ret=" + res +
                 " offline=" + offline + BS + "n        -> " + now);
    }
    say("결과", "성공 " + okCnt + " · 파일없음 " + missCnt + " · 실패 " + failCnt);

    /*  남은 오프라인 전수 조사 — 통과 판정의 근거  */
    var stillOffline = [], online = [];
    walk(app.project.rootItem, function (ch) {
        var mp = "";
        try { mp = ch.getMediaPath(); } catch (e) { return; }
        if (!mp) return;
        var off = false;
        try { off = ch.isOffline(); } catch (e) {}
        (off ? stillOffline : online).push(ch.name);
    });
    say("온라인", online.length + " :: " + online.join(" | "));
    say("아직 오프라인", stillOffline.length + " :: " + stillOffline.join(" | "));

    var ok = false;
    try { ok = app.project.saveAs(OUT); } catch (e) { say("saveAs_ERR", e.toString()); }
    say("saveAs", ok);
    say("out_size", new File(OUT).exists ? new File(OUT).length : "(없음)");
    return done("m5_relink " + (ok ? "ok" : "FAILED"));
})();
