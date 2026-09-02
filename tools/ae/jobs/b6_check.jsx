/*  B6 — 꾸러미가 **정말 포터블인지** 연다. 압축을 다른 경로에 푼 뒤 이걸 돌린다.
;
    보는 것 셋:
      ① 푸티지가 없다고 뜨는 게 하나라도 있는가 (footageMissing)
      ② 컴포지션 수·레이어 수가 기대와 맞는가
      ③ 표현식이 깨진 게 있는가 (이름으로 서로를 가리키므로 조용히 끊길 수 있다)

    "AE 에서 잘 열린다" 는 눈으로 보는 게 아니라 이 셋으로 확인한다.
    열 파일 경로는 C:/aelab/ae/_check.txt 에 적어 둔다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("b6");

var AEP = (function () {
    var f = new File(LAB + "/ae/_check.txt");
    if (!f.exists) return "";
    /* 경로에 한글이 들어간다 — 기본 인코딩(CP949)으로 읽으면 깨진다 */
    f.encoding = "UTF-8";
    f.open("r"); var t = f.read(); f.close();
    return String(t).replace(/^\s+|\s+$/g, "");
})();

function __main() {

say("잡", "B6 꾸러미 열기 검사");
say("파일", AEP);

closeQuietly();
probe("열기", function () {
    var f = new File(AEP);
    if (!f.exists) throw new Error("없다: " + AEP);
    app.open(f);
    return app.project.numItems + "항목";
});

/* ① 푸티지 */
var miss = [], foot = 0;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (!(it instanceof FootageItem)) continue;
    foot++;
    if (it.footageMissing) miss.push(it.name);
}
say("푸티지", foot + "개 · " + (miss.length ? "**없음 " + miss.length + "개: " + miss.join(", ") + "**" : "전부 연결됨"));

/* ② 컴포지션 */
var comps = [];
for (var j = 1; j <= app.project.numItems; j++) {
    var c = app.project.item(j);
    if (c instanceof CompItem) comps.push(c);
}
for (var k = 0; k < comps.length; k++) {
    say("  " + comps[k].name, comps[k].numLayers + "레이어 · "
        + Math.round(comps[k].duration * comps[k].frameRate) + "f · "
        + comps[k].width + "x" + comps[k].height);
}

/* ③ 표현식 — 이름으로 서로를 가리키니 조용히 끊길 수 있다 */
var bad = [], checked = 0;
function scan(pg, where) {
    for (var a = 1; a <= pg.numProperties; a++) {
        var p = pg.property(a);
        if (p.numProperties != null && p.numProperties > 0) { scan(p, where); continue; }
        if (p.canSetExpression && p.expressionEnabled) {
            checked++;
            if (p.expressionError && String(p.expressionError).length) {
                bad.push(where + " > " + p.name + ": " + String(p.expressionError).substr(0, 60));
            }
        }
    }
}
for (var m = 0; m < comps.length; m++) {
    for (var n = 1; n <= comps[m].numLayers; n++) {
        var L = comps[m].layer(n);
        try { scan(L, comps[m].name + " / " + L.name); } catch (e) {}
    }
}
say("표현식", checked + "개 검사 · " + (bad.length ? "**오류 " + bad.length + "개**" : "오류 없음"));
for (var b = 0; b < Math.min(bad.length, 8); b++) out.push("    " + bad[b]);

flush();
if (miss.length || bad.length) return fail("푸티지 없음 " + miss.length + " · 표현식 오류 " + bad.length);
return done(comps.length + "컴포지션 · 푸티지 " + foot + "개 전부 연결 · 표현식 " + checked + "개 정상");
}
__main();
