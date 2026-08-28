/*
    M2 검사. 아무것도 바꾸지 않는다.

    오프라인/온라인 대비는 파일이 아니라 런타임 상태라 프리미어에게 물어야 한다
    (verify.py 로는 못 잰다). 교체한 항목만 온라인이면 교체가 실제로 먹혔다는 증거다.
    프리셋 미디어는 D:\ 를 가리키는데 이 PC 는 G:\ 라 전부 오프라인이고,
    교체해 넣은 차트만 C:\cmgwork 라 살아 있어야 한다.
*/
(function () {
    var CHART = "chartA.png";
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }

    say("project.path", app.project.path);

    var total = 0, off = 0, on = [], offSample = [];
    function walk(item) {
        for (var i = 0; i < item.children.numItems; i++) {
            var c = item.children[i];
            if (c.type === 2) { walk(c); continue; }   // BIN
            total++;
            var isOff = null;
            try { isOff = c.isOffline(); } catch (e) { isOff = "ERR"; }
            if (isOff === true) { off++; if (offSample.length < 3) offSample.push(c.name); }
            else if (isOff === false) { on.push(c.name); }
        }
    }
    walk(app.project.rootItem);
    say("오프라인 / 전체", off + " / " + total);
    say("온라인 항목", on.join(" | "));
    say("오프라인 예시", offSample.join(" | "));

    // 교체한 항목을 콕 집어서
    var found = null;
    function find(item) {
        for (var i = 0; i < item.children.numItems; i++) {
            var c = item.children[i];
            if (c.type === 2) { find(c); continue; }
            if (c.name === CHART) found = c;
        }
    }
    find(app.project.rootItem);
    if (found) {
        say(CHART + ".isOffline", String(found.isOffline()));
        say(CHART + ".mediaPath", found.getMediaPath());
        try {
            var fi = found.getFootageInterpretation();
            say(CHART + ".해석", "frameRate=" + fi.frameRate + " pixelAspect=" + fi.pixelAspectRatio);
        } catch (e) { say(CHART + ".해석_ERR", e.toString()); }
    } else {
        say(CHART, "(프로젝트에 없다)");
    }

    var f = new File("C:/pprolab/m2_check.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n"));
    f.close();
    return "m2_check ok";
})();
