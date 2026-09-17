/**
 * tools/illustrator 의 jsx 가 함께 쓰는 것들.
 *
 * ExtendScript 에는 import 가 없지만 $.evalFile 은 있다. 같은 10줄을 파일마다
 * 베끼지 않는다 — tools/photoshop/_labdir.jsx 와 같은 방식이다.
 *
 *     $.evalFile(new File(new File($.fileName).parent.fsName + "/_lib.jsx"));
 */

/** config.json 을 읽는다. 경로 해석은 run.ps1(labdir.ps1)이 해서 환경변수로 넘긴다. */
function readConfig(here) {
    var f = new File(here.fsName + "/config.json");
    if (!f.exists) throw new Error("config.json 이 없습니다: " + f.fsName);
    f.encoding = "UTF-8";          // 한글이 들어 있다. 이걸 빼면 깨진다.
    f.open("r");
    var t = f.read();
    f.close();
    t = t.replace(/^\uFEFF/, "");   // BOM 이 붙어 와도 eval 이 안 깨지게 (총괄 개선안 B-1)
    return eval("(" + t + ")");    // ExtendScript 에는 JSON 이 없는 판이 있다
}

/**
 * run.ps1 이 남긴 _paths.json 을 읽는다 — liveframeDir · outDir · repoDir.
 * 환경변수를 안 쓰는 이유: $.getenv 는 일러스트레이터가 켜진 시점의 환경만 본다.
 * 앱이 이미 떠 있으면 뒤에 set 한 변수가 안 간다 (2026-09-16 실측).
 */
function readPaths(here) {
    var f = new File(here.fsName + "/_paths.json");
    if (!f.exists) throw new Error("_paths.json 이 없습니다 — run.ps1 로 실행하세요: " + f.fsName);
    f.encoding = "UTF-8";
    f.open("r");
    var t = f.read();
    f.close();
    t = t.replace(/^\uFEFF/, "");   // BOM 이 붙어 와도 eval 이 안 깨지게 (총괄 개선안 B-1)
    return eval("(" + t + ")");
}

/** "#RRGGBB" -> RGBColor */
function rgb(hex) {
    var h = String(hex).replace("#", "");
    var c = new RGBColor();
    c.red   = parseInt(h.substring(0, 2), 16);
    c.green = parseInt(h.substring(2, 4), 16);
    c.blue  = parseInt(h.substring(4, 6), 16);
    return c;
}

/**
 * 후보 이름을 차례로 찾아 처음 있는 글꼴을 준다.
 * 글꼴 이름은 윈도우 판·일러스트레이터 판마다 달라서(궁서 = Gungsuh / GungsuhChe / 궁서)
 * 하나를 박으면 다른 PC 에서 조용히 다른 글꼴로 바뀐다.
 * onLog 를 주면 실제로 있는 후보를 전부 적어 준다.
 */
function pickFont(names, onLog) {
    var found = [];
    for (var i = 0; i < app.textFonts.length; i++) {
        var n = app.textFonts[i].name;
        for (var j = 0; j < names.length; j++) {
            if (n === names[j] || n.indexOf(names[j]) === 0) { found.push(n); break; }
        }
    }
    if (onLog) onLog("글꼴 후보 중 설치된 것: " + (found.length ? found.join(" · ") : "(없음)"));

    for (var k = 0; k < names.length; k++) {
        try { return app.textFonts.getByName(names[k]); } catch (e) {}
        for (var m = 0; m < found.length; m++) {
            if (found[m].indexOf(names[k]) === 0) {
                try { return app.textFonts.getByName(found[m]); } catch (e2) {}
            }
        }
    }
    throw new Error("글꼴을 못 찾았습니다: " + names.join(" / ")
                  + "\n설치된 비슷한 것: " + found.join(" · "));
}
