/*  A1 — 통신 스모크.  AE 안에서 돈다.

    매뉴얼 A1 은 "버전 문자열을 C:/aelab/log/a1.txt 에 써라" 지만, 그 파일 쓰기 자체가
    환경설정(스크립트 파일쓰기 허용)에 걸려 조용히 죽는 게 1순위 용의자다(§6).
    그래서 **측정값을 반환값에도 같이 실어 보낸다** — 파일이 안 생겨도 _result.txt 로는 온다.
    파일이 생기는지 여부 자체가 환경설정 판정이 된다.
*/
var LOG = "C:/aelab/log/a1.txt";
var out = [];
function say(k, v) { out.push(k + "\t" + v); }
function probe(k, fn) {
    var r; try { r = String(fn()); } catch (e) { r = "ERR " + e.toString(); }
    say(k, r); return r;
}

probe("app.version",   function () { return app.version; });
probe("app.buildName", function () { return app.buildName; });
probe("app.language",  function () { return app.language; });
probe("app.isoLanguage", function () { return app.isoLanguage; });
probe("system.osName", function () { return $.os; });
probe("ExtendScript",  function () { return $.version; });
probe("project 있나",   function () { return app.project ? "있다 (items " + app.project.numItems + ")" : "null"; });
probe("컴포지션 생성 API", function () { return typeof app.project.items.addComp; });
probe("mogrt API",      function () { return typeof CompItem !== "undefined" ? "CompItem 있다" : "CompItem 없다"; });

/*  스크립트 파일쓰기·네트워크 허용 여부. 켜져 있으면 1.
    이걸 못 읽어도(판이 다르면) 아래 실제 파일쓰기 시도가 진짜 판정이다.  */
probe("파일쓰기 허용 pref", function () {
    return app.preferences.getPrefAsLong(
        "Main Pref Section v2", "Pref_SCRIPTING_FILE_NETWORK_SECURITY",
        PREFType.PREF_Type_MACHINE_INDEPENDENT);
});

/*  모달을 띄우는 설정이 켜져 있으면 세션이 죽는다 — 미리 끈다.  */
probe("app.exitAfterLaunchAndEval", function () { return app.exitAfterLaunchAndEval; });
probe("beginSuppressDialogs", function () {
    app.beginSuppressDialogs(); return "호출됨";
});
probe("endSuppressDialogs", function () {
    app.endSuppressDialogs(false); return "호출됨";
});

var wrote = "안 함";
try {
    var d = new Folder("C:/aelab/log");
    if (!d.exists) d.create();
    var f = new File(LOG);
    f.encoding = "UTF-8";
    if (!f.open("w")) throw new Error("open 실패 — 환경설정 파일쓰기 허용이 꺼져 있을 가능성이 가장 크다");
    f.write("A1 통신 스모크\n" + out.join("\n") + "\n");
    f.close();
    wrote = (new File(LOG)).exists ? "성공 (" + (new File(LOG)).length + " bytes)" : "open 은 됐는데 파일이 없다";
} catch (e) {
    wrote = "ERR " + e.toString();
}
say("파일쓰기 결과", wrote);

"A1\n" + out.join("\n");
