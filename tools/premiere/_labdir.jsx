/**
 * 프리미어 실험실 폴더를 스스로 찾는다 — 경로를 박지 않는다.
 * tools/ae/labdir.* · tools/photoshop/_labdir.jsx 와 같은 규칙이고, 여기는 프리미어 판이다.
 *
 * 쓰는 법 (jobs/*.jsx 맨 앞에서):
 *     $.evalFile(new File(String(new File($.fileName).parent.parent.fsName)
 *         .split(String.fromCharCode(92)).join("/") + "/_labdir.jsx"));
 *     var LAB = labDirPath();          // 예: .../06_실험실/pprolab
 *     var CMG = cmgDirPath();          // 썸네일 실험실 (차트 PNG 등)
 *
 * 찾는 순서
 *   1) 환경변수 PPROLAB_DIR (썸네일 쪽은 CMGWORK_DIR)
 *   2) config.json 의 labDir (비어 있으면 건너뛴다)
 *   3) 자기 위치에서 위로 8단계 올라가며 '06_실험실/pprolab' → 'pprolab' 을 찾는다
 *   4) 옛 자리 C:/pprolab (되돌렸을 때를 위해)
 *
 * 2026-09-16: 작업물을 한 폴더로 모으면서 C:/pprolab · C:/cmgwork 를 없앴다.
 * 실체는 <통합 폴더>/06_실험실/ 아래에 있다.
 */

function _fwd(s) { return String(s).split(String.fromCharCode(92)).join("/"); }

function _findDir(here, names, envName, legacy, cfgLabDir) {
    var f;
    try {
        var env = $.getenv(envName);
        if (env) { f = new Folder(env); if (f.exists) return f; }
    } catch (e) {}

    if (cfgLabDir) {
        f = new Folder(cfgLabDir);
        if (!f.exists) f = new Folder(here.fsName + "/" + cfgLabDir);
        if (f.exists) return f;
    }

    var d = here;
    for (var i = 0; i < 8 && d; i++) {
        for (var n = 0; n < names.length; n++) {
            f = new Folder(d.fsName + "/" + names[n]);
            if (f.exists) return f;
        }
        d = d.parent;
    }

    f = new Folder(legacy);
    if (f.exists) return f;

    d = here;
    for (var j = 0; j < 4 && d && d.parent; j++) d = d.parent;
    return new Folder(d.fsName + "/" + names[0]);
}

/** 이 스크립트가 있는 폴더 (tools/premiere) */
function _here() { return new File($.fileName).parent; }

/** 프리미어 실험실 경로 (슬래시 문자열) */
function labDirPath(cfgLabDir) {
    return _fwd(_findDir(_here(), ["06_실험실/pprolab", "pprolab"],
                         "PPROLAB_DIR", "C:/pprolab", cfgLabDir).fsName);
}

/** 썸네일 실험실 경로 — 차트 PNG 등 (슬래시 문자열) */
function cmgDirPath() {
    return _fwd(_findDir(_here(), ["06_실험실/cmgwork", "cmgwork"],
                         "CMGWORK_DIR", "C:/cmgwork", null).fsName);
}
