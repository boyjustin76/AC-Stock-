/*
    열린 프리미어 프로젝트를 전부 저장하고 프리미어를 끈다 (사용자 요청 2026-09-14).

    안전장치
      · 한 번도 저장된 적 없는 프로젝트(경로 없음)가 있으면 **끄지 않는다** — 저장 위치를 물어보는 대화상자가 떠야 해서.
      · 저장이 하나라도 실패하면 끄지 않는다.
      · app.quit() 뒤에는 BridgeTalk 응답이 안 돌아올 수 있다. 그래서 결과는 먼저 파일에 쓴다: C:/pprolab/save_quit.txt
*/
(function () {
    var LOG = "C:/pprolab/save_quit.txt";
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function flush() {
        try { var f = new File(LOG); f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n") + "\n"); f.close(); } catch (e) {}
    }

    var n = 0;
    try { n = app.projects.numProjects; } catch (e) { say("ERR", e.toString()); }
    say("열린 프로젝트", n);
    var bad = [];
    for (var i = 0; i < n; i++) {
        var p = app.projects[i];
        var path = "";
        try { path = String(p.path); } catch (e) {}
        say("  [" + i + "]", p.name + " | " + path);
        if (!path || path.length < 5 || !(new File(path)).exists) { bad.push(p.name + " (저장 위치 없음)"); continue; }
        try {
            var before = (new File(path)).modified;
            var r = p.save();
            $.sleep(1500);
            var after = (new File(path)).modified;
            say("  저장", p.name + " → save()=" + r + " · 수정시각 " + before + " → " + after);
        } catch (e2) {
            bad.push(p.name + " (" + e2.toString() + ")");
        }
    }
    if (bad.length) {
        say("판정", "끄지 않았다 — " + bad.join(", "));
        flush();
        return "NOT_QUIT\n" + out.join("\n");
    }
    say("판정", "전부 저장 · app.quit() 호출");
    flush();
    app.quit();
    return "QUIT\n" + out.join("\n");
})();
