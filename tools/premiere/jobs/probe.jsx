/*
    프리미어 안에서 돈다 (BridgeTalk 로 배달됨). 아무것도 열지 않고 바꾸지 않는다.
    스크립팅 계층이 어디까지 열려 있는지만 재서 C:/pprolab/probe_premiere.txt 에 적는다.
*/
(function () {
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }
    function probe(k, fn) { try { say(k, String(fn())); } catch (e) { say(k + "_ERR", e.toString()); } }

    probe("app.version",       function () { return app.version; });
    probe("app.build",         function () { return app.build; });
    probe("app.getAppPrefPath",function () { return app.getAppPrefPath(); });
    probe("app.path",          function () { return app.path; });

    // 열려 있는 프로젝트 (없을 수도 있다)
    probe("project.name",      function () { return app.project.name; });
    probe("project.path",      function () { return app.project.path; });
    probe("numSequences",      function () { return app.project.sequences.numSequences; });
    probe("numProjectItems",   function () { return app.project.rootItem.children.numItems; });
    probe("activeSequence",    function () { return app.project.activeSequence ? app.project.activeSequence.name : "(없음)"; });

    // 공개 DOM 표면 — app 과 project 의 멤버를 전부 나열한다 (§3-6 대표값 하나 믿지 마라)
    probe("app_members", function () {
        var a = []; for (var k in app) a.push(k); a.sort(); return a.join(",");
    });
    probe("project_members", function () {
        var a = []; for (var k in app.project) a.push(k); a.sort(); return a.join(",");
    });

    // 한 층 아래 — qe (§3-3)
    probe("typeof_enableQE", function () { return typeof app.enableQE; });
    probe("enableQE()",      function () { return app.enableQE(); });
    probe("typeof_qe",       function () { return typeof qe; });
    probe("qe_members",      function () { var a = []; for (var k in qe) a.push(k); a.sort(); return a.join(","); });
    probe("qe.project_members", function () { var a = []; for (var k in qe.project) a.push(k); a.sort(); return a.join(","); });
    probe("qe.version",      function () { return qe.version; });

    // 쓰기 계열이 있는지만 확인한다 (호출하지 않는다)
    var wanted = ["openDocument", "newProject", "quit", "setSDKEventMessage", "encoder", "sourceMonitor", "anywhere", "properties"];
    for (var i = 0; i < wanted.length; i++) {
        (function (w) { probe("app." + w, function () { return typeof app[w]; }); })(wanted[i]);
    }

    var text = out.join("\n");
    var f = new File("C:/pprolab/probe_premiere.txt");
    f.encoding = "UTF-8";
    f.open("w");
    f.write(text);
    f.close();

    return "probe ok, " + out.length + " lines";
})();
