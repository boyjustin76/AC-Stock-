/**
 * 썸네일 작업실 폴더를 스스로 찾는다 — 경로를 박지 않는다.
 * tools/ae/labdir.py · labdir.ps1 과 같은 규칙이고, 여기는 ExtendScript 판이다.
 *
 * 쓰는 법 (jsx 안에서):
 *     $.evalFile(new File(new File($.fileName).parent.fsName + "/_labdir.jsx"));
 *     var CFG = loadConfig(HERE);      // 경로 키가 절대경로로 풀려서 온다
 *
 * ExtendScript 에는 import 가 없지만 $.evalFile 은 있다. 같은 10줄을 파일마다
 * 복사하는 것(= 이번에 지적받은 그 문제)보다 한 파일을 불러 쓰는 쪽이 낫다.
 *
 * 찾는 순서
 *   1) 환경변수 CMGWORK_DIR
 *   2) config.json 의 labDir (비어 있으면 건너뛴다)
 *   3) 자기 위치에서 위로 8단계 올라가며 '06_실험실/cmgwork' → 'cmgwork' 를 찾는다
 *   4) 옛 자리 C:/cmgwork (되돌렸을 때를 위해)
 * 다 실패하면 3번이 만들 자리를 돌려준다.
 */

var LAB_ENV    = "CMGWORK_DIR";
var LAB_NAMES  = ["06_실험실/cmgwork", "cmgwork"];
var LAB_LEGACY = "C:/cmgwork";

/** 작업실 폴더를 찾아 Folder 로 돌려준다. here 는 이 스크립트가 있는 Folder */
function findLabDir(here, cfgLabDir) {
    var f;

    // 1) 환경변수
    try {
        var env = $.getenv(LAB_ENV);
        if (env) { f = new Folder(env); if (f.exists) return f; }
    } catch (e) {}

    // 2) config 의 labDir — 상대경로면 이 폴더 기준
    if (cfgLabDir) {
        f = new Folder(cfgLabDir);
        if (!f.exists) f = new Folder(here.fsName + "/" + cfgLabDir);
        if (f.exists) return f;
    }

    // 3) 위로 올라가며 찾는다 — 꾸러미를 어디에 풀어도 따라온다
    var d = here;
    for (var i = 0; i < 8 && d; i++) {
        for (var n = 0; n < LAB_NAMES.length; n++) {
            f = new Folder(d.fsName + "/" + LAB_NAMES[n]);
            if (f.exists) return f;
        }
        d = d.parent;
    }

    // 4) 옛 자리
    f = new Folder(LAB_LEGACY);
    if (f.exists) return f;

    // 없으면 만들 자리를 알려 준다 (통합 폴더 안)
    d = here;
    for (var j = 0; j < 4 && d && d.parent; j++) d = d.parent;
    return new Folder(d.fsName + "/" + LAB_NAMES[0]);
}

/** 값이 상대경로면 작업실 기준으로 풀고, 절대경로면 그대로 둔다 */
function underLab(v, lab) {
    if (!v) return v;
    var s = String(v).replace(/\\/g, "/");
    if (/^[A-Za-z]:\//.test(s) || s.charAt(0) === "/") return s;   // 이미 절대경로
    if (s === "." || s === "./") return lab.fsName.replace(/\\/g, "/");
    return lab.fsName.replace(/\\/g, "/") + "/" + s.replace(/^\.\//, "");
}

/**
 * config.json 을 읽고 경로 키들을 절대경로로 풀어 돌려준다.
 * 푸는 키: template · chartDir · outDir · runsTarget. 나머지는 손대지 않는다.
 */
function loadConfig(here) {
    var f = new File(here.fsName + "/config.json");
    if (!f.exists) throw new Error("config.json 이 없습니다: " + f.fsName);
    f.encoding = "UTF-8";          // 한글이 들어 있다. 이걸 빼면 깨진다.
    f.open("r");
    var txt = f.read();
    f.close();
    var cfg = eval("(" + txt + ")");   // ExtendScript 에는 JSON 이 없는 판이 있다

    var lab = findLabDir(here, cfg.labDir);
    cfg.labDir     = lab.fsName.replace(/\\/g, "/");
    cfg.template   = underLab(cfg.template,   lab);
    cfg.chartDir   = underLab(cfg.chartDir,   lab);
    cfg.outDir     = underLab(cfg.outDir,     lab);
    cfg.runsTarget = underLab(cfg.runsTarget, lab);
    return cfg;
}
