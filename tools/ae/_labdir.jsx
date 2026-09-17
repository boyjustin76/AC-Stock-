/*  AE 작업실 폴더를 스스로 찾는다 — 경로를 박지 않는다.
    tools/ae/labdir.py · labdir.mjs · labdir.ps1 과 같은 규칙의 ExtendScript 판이다.
    포토샵(bridge.jsx)과 AE(jobs/_lib.jsx) 양쪽에서 부른다.

    쓰는 법 (부르는 파일 맨 앞):
        $.evalFile(new File(<tools/ae 폴더> + "/_labdir.jsx"));
        var LAB = aeLabDir((new File($.fileName)).parent, cfg.labDir);

    찾는 순서
      1) 환경변수 AELAB_DIR
      2) config.json 의 labDir (넘겨 줄 때만. 상대경로면 start 기준)
      3) start 에서 위로 8단계 올라가며 '02_AE작업실_aelab'
      못 찾으면 **어디서 찾았는지 말하고 멈춘다.**

    2026-09-17: 이 로직이 bridge.jsx · jobs/_lib.jsx · jobs/a1_smoke.jsx 에 복붙돼 있었고(총괄 개선안 D-2),
    셋 다 못 찾으면 'C:/aelab' 을 돌려줬다. 그 폴더는 09-16 에 없앴으므로 엉뚱한 자리에서
    "파일 없음" 으로 늦게 터졌다 — 이제 여기서 바로 멈춘다.
    a1_smoke.jsx 는 공용 파일 없이 도는 부트스트랩 시험이라 일부러 따로 둔다.
*/
function aeLabDir(start, cfgLabDir) {
    var FOLDER = "02_AE작업실_aelab";
    function fwd(p) { return String(p).split(String.fromCharCode(92)).join("/"); }

    try {
        var env = $.getenv("AELAB_DIR");
        if (env && (new Folder(env)).exists) return fwd(env);
    } catch (e) {}

    if (cfgLabDir) {
        var f = new Folder(cfgLabDir);
        if (!f.exists) f = new Folder(start.fsName + "/" + cfgLabDir);
        if (f.exists) return fwd(f.fsName);
    }

    var d = start;
    for (var i = 0; i < 8 && d; i++) {
        var c = new Folder(d.fsName + "/" + FOLDER);
        if (c.exists) return fwd(c.fsName);
        d = d.parent;
    }
    throw new Error("AE 작업실 폴더 '" + FOLDER + "' 를 못 찾았다 — 환경변수 AELAB_DIR 을 주거나 "
                    + "config.json 의 labDir 에 적는다 (찾기 시작: " + fwd(start.fsName) + ")");
}
