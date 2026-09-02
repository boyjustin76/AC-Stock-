/*  B2 — 컷 하나를 AE 컴포지션으로 짓는다. 풀버전의 본체다.

    파일럿(a3_build)과 다른 점:
      · 컷 하나에 박아 넣은 코드가 아니라 **데이터가 몬다.** 좌표·타이밍은 전부
        tools/ae/scene-export.mjs 가 낸 SCENE 에서 온다. 씬 파일이 바뀌면 다시 내보내면 된다.
      · 바닥이 스틸 PNG 가 아니라 **차트만 담은 알파 무비**다(--split --floor).
        11컷 중 10컷이 카메라가 움직여서 스틸로는 안 된다.
      · 주석은 "차트 카메라" 널을 표현식으로 읽어 차트를 따라간다.

    무엇을 지을지는 C:/aelab/ae/_build.txt 가 정한다 — "<슬러그> <컷id 또는 all>".
    run.ps1 은 잡 이름만 넘기므로, 인자는 이 파일로 준다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
$.evalFile(new File(HERE + "/_ae.jsx"));
$.evalFile(new File(HERE + "/_types.jsx"));
logTo("b2");

/*  좌표는 **최상위에서** 읽는다. $.evalFile 은 부른 자리의 스코프에 심으므로
    함수 안에서 부르면 var SCENE 이 그 함수와 함께 사라진다 (B1 에서 물렸다).  */
var SPEC = (function () {
    var f = new File(LAB + "/ae/_build.txt");
    if (!f.exists) return { slug: "sl-11-4", cut: "all" };
    f.open("r"); var t = f.read(); f.close();
    var p = String(t).replace(/^\s+|\s+$/g, "").split(/\s+/);
    return { slug: p[0], cut: p[1] || "all" };
})();
$.evalFile(new File(LAB + "/ae/" + SPEC.slug + ".jsx"));

function __main() {

/*  **포터블 구조로 짓는다.**  <팩>/<슬러그>.aep 와 <팩>/footage/<컷>.mov 를 나란히 두면,
    AE 는 절대경로가 안 맞을 때 프로젝트 파일 기준 상대경로로 다시 찾는다.
    그래서 이 폴더째 어디로 옮겨도 "파일 없음" 이 안 뜬다 — 압축해서 그대로 넘기면 된다.  */
var PACK  = LAB + "/pack/" + (SCENE.packName || SPEC.slug);
var FLOOR = PACK + "/footage";
var AEP   = PACK + "/" + SPEC.slug + ".aep";   /* 파일 이름은 씬 파일과 맞춘다 — 추적용 */

say("잡", "B2 컴포지션 짓기 — " + SPEC.slug + " / " + SPEC.cut);
probe("좌표", function () {
    if (typeof SCENE === "undefined") throw new Error("좌표를 못 읽었다: " + SPEC.slug);
    return SCENE.title + " · 컷 " + SCENE.cuts.length;
});
probe("폰트", function () {
    var ns = [F_TAG, F_NOTE], t = [];
    for (var i = 0; i < ns.length; i++) {
        var r = app.fonts.getFontsByPostScriptName(ns[i]);
        t.push(ns[i] + "=" + (r && r.length ? "있다" : "**없다**"));
        if (!r || !r.length) throw new Error("폰트가 없다: " + ns[i]);
    }
    return t.join(" · ");
});

closeQuietly();
app.newProject();

/*  색 합성 공간을 캔버스와 맞춘다.
    렌더러는 브라우저 캔버스라 **sRGB 값 그대로** 섞는다. AE 가 선형 감마로 섞거나
    작업 색공간이 걸려 있으면 반투명 합성이 미묘하게 어긋난다 — 스크림·영역 채움·
    빗금처럼 알파를 쓰는 것 전부에 걸린다.  */
probe("색 설정", function () {
    var before = "선형=" + app.project.linearBlending + " 공간='" + app.project.workingSpace + "' 비트=" + app.project.bitsPerChannel;
    app.project.linearBlending = false;
    app.project.workingSpace = "";          /* 색 관리 끔 = sRGB 값 그대로 */
    return before + "  →  선형=" + app.project.linearBlending + " 공간='" + app.project.workingSpace + "'";
});

/** 컷 하나 */
function buildCut(cut) {
    COMP = app.project.items.addComp(SCENE.slug + " " + cut.id, SCENE.w, SCENE.h, 1,
                                     cut.frames / SCENE.fps, SCENE.fps);
    CTX.plot = cut.plot;
    ALPHA.keys = 0; ALPHA.err = 0;
    CTX.dur  = cut.frames / SCENE.fps;
    CTX.fps  = SCENE.fps;

    /* ── 바닥: 차트만 담은 알파 무비 ── */
    var fp = new File(FLOOR + "/" + cut.id + ".mov");
    if (!fp.exists) throw new Error("바닥이 없다: " + fp.fsName);
    var item = app.project.importFile(new ImportOptions(fp));
    item.name = "바닥 " + cut.id;
    var floor = COMP.layers.add(item);
    floor.name = "차트 바닥";

    /* ── 카메라 널 ── */
    /*  카메라 널은 **기계 부품**이다. 사람이 만질 물건이 아니라서
        shy + 잠금으로 두고 컴포지션에서 shy 를 숨긴다 — 타임라인에서 아예 사라진다.
        (숨기지 않았더니 키 수천 개가 깔려서 "무서워서 못 건드리겠다" 는 말을 들었다.)  */
    var cam = COMP.layers.addNull(COMP.duration);
    cam.name = CAM_NAME;
    cam.enabled = false;
    cam.shy = true;
    COMP.hideShyLayers = true;

    /*  LAST 는 '지금 가격' — reveal 이 움직이면 같이 바뀐다. cmgProfit 이 쓴다.
        빠뜨렸더니 표현식이 없는 이펙트를 가리켜 사각형이 통째로 죽었다.  */
    var keys = ["X0", "BW", "Y0", "K", "LAST"];
    var camKeys = 0;
    for (var s = 0; s < keys.length; s++) {
        var e = fx(cam).addProperty("ADBE Slider Control");
        e.name = keys[s];
        /*  내보내기가 미리 솎아 둔 점만 박는다(화면 오차 0.1px 안). 보간은 **선형** —
            노드에서 오차를 잴 때 쓴 것과 같은 보간이라야 잰 값이 실제 값이 된다.  */
        var kf = cut.cam[keys[s]];
        var times = [];
        for (var f = 0; f < kf.f.length; f++) times.push(kf.f[f] / SCENE.fps);
        var pr = e.property(1);
        pr.setValuesAtTimes(times, kf.v);
        for (var k = 1; k <= pr.numKeys; k++) {
            pr.setInterpolationTypeAtKey(k, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR);
        }
        camKeys += pr.numKeys;
    }
    cam.locked = true;

    /*  내보내기가 이미 **그리는 순서**로 정렬해 준다(팀장 규칙 ⑭ — 버튼이 맨 위).
        AE 의 addShape 은 맨 위에 얹으므로, 그 순서대로 넣으면 화면 순서와 같아진다.  */
    var okN = 0, skipped = [];
    for (var i = 0; i < cut.layers.length; i++) {
        var L = cut.layers[i];
        var fn = TYPES[L.type];
        if (!fn) { skipped.push(L.type); continue; }
        var no = i;
        (function (layer, idx) {
            probe("  " + (idx + 1) + " " + layer.type, function () {
                IDX = idx;                 /* 이름을 만들 때 번호가 붙는다 — 뒤에 바꾸면 표현식이 끊긴다 */
                var made = fn(layer);
                okN++;
                return made.length + "개 · " + made[made.length - 1].name;
            });
        })(L, no);
    }
    return { comp: COMP, ok: okN, skipped: skipped, camKeys: camKeys,
             alphaKeys: ALPHA.keys, alphaErr: ALPHA.err };
}

var total = 0, allSkipped = {};
for (var c = 0; c < SCENE.cuts.length; c++) {
    var cut = SCENE.cuts[c];
    if (SPEC.cut !== "all" && cut.id !== SPEC.cut) continue;
    say("컷", cut.id + " · " + cut.frames + "f · 레이어 " + cut.layers.length);
    var r = probeVal("  컴포지션", function () { return buildCut(cut); },
                     function (v) {
                         return v ? v.comp.name + " · " + v.comp.numLayers + "레이어"
                                  + " · 카메라키 " + v.camKeys + "(숨김)"
                                  + " · 알파키 " + v.alphaKeys + " 오차 " + v.alphaErr + "%" : "실패";
                     });
    if (r) {
        total += r.ok;
        for (var s2 = 0; s2 < r.skipped.length; s2++) allSkipped[r.skipped[s2]] = (allSkipped[r.skipped[s2]] || 0) + 1;
    }
}

var sk = [];
for (var k2 in allSkipped) if (allSkipped.hasOwnProperty(k2)) sk.push(k2 + "×" + allSkipped[k2]);
say("변환", total + "개 성공" + (sk.length ? " · 아직 없는 종류: " + sk.join(" ") : ""));

probe("저장", function () { app.project.save(new File(AEP)); return AEP; });

flush();
return done(total + "개 레이어 변환");
}
__main();
