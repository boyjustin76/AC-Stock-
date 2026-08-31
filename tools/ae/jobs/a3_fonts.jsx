/*  폰트 열거가 후보 0개를 줬다. 속성 이름을 짐작한 탓일 수 있으니 **실제로 뭘 주는지** 본다.
    (프리미어에서 `비율` → `비율 조정` 으로 물린 것과 같은 자리다.)  */
$.evalFile(new File(String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/") + "/_lib.jsx"));
logTo("a3_fonts");

say("잡", "폰트 실측");

probe("allFonts 길이", function () { return app.fonts.allFonts.length; });

/* 첫 항목의 **속성 이름 자체**를 뽑는다 */
probe("FontObject 의 키", function () {
    var f = app.fonts.allFonts[0];
    var ks = [];
    for (var k in f) ks.push(k);
    return ks.length ? ks.join(", ") : "(for..in 이 아무것도 안 준다 — 네이티브 객체)";
});
probe("첫 항목 값", function () {
    var f = app.fonts.allFonts[0];
    var t = [];
    var names = ["postScriptName", "familyName", "styleName", "fullName", "family", "style", "name", "location"];
    for (var i = 0; i < names.length; i++) {
        var v;
        try { v = String(f[names[i]]); } catch (e) { v = "(못 읽음)"; }
        t.push(names[i] + "=" + v);
    }
    return t.join(" · ");
});

/* 전체를 postScriptName 으로 훑어 한글/브랜드 폰트를 찾는다 */
var all = app.fonts.allFonts;
var found = [], sample = [];
for (var i = 0; i < all.length; i++) {
    var ps = "";
    try { ps = String(all[i].postScriptName); } catch (e) { ps = "?"; }
    if (i < 12) sample.push(ps);
    if (/gmarket|scdream|s-core|score|pretendard|nanum/i.test(ps)) found.push(ps);
}
say("앞 12개", sample.join(" | "));
say("브랜드 후보", found.length ? found.join(" | ") : "없다");

/* 이름으로 직접 찾아 본다 — 열거가 안 돼도 지정은 될 수 있다 */
probe("getFontsByFamilyNameAndStyleName", function () {
    if (!app.fonts.getFontsByFamilyNameAndStyleName) return "그런 함수 없음";
    var r = app.fonts.getFontsByFamilyNameAndStyleName(FontsObject.FontType.ANY_TYPE, "Gmarket Sans", "Bold");
    return r && r.length ? r.length + "개 · " + r[0].postScriptName : "0개";
});
probe("getFontsByPostScriptName", function () {
    if (!app.fonts.getFontsByPostScriptName) return "그런 함수 없음";
    var names = ["GmarketSansBold", "GmarketSansTTFBold", "GmarketSansMedium", "SCDream5", "S-CoreDream-5Medium"];
    var t = [];
    for (var i = 0; i < names.length; i++) {
        var r = app.fonts.getFontsByPostScriptName(names[i]);
        t.push(names[i] + "=" + (r && r.length ? "있다" : "없다"));
    }
    return t.join(" · ");
});

/* 마지막 확인 — 텍스트 레이어에 직접 박아 보고 되돌아오는 이름을 본다 */
closeQuietly();
probe("newProject+addComp", function () {
    app.newProject();
    app.project.items.addComp("f", 400, 200, 1, 1, 30);
    return "ok";
});
var tries = ["GmarketSansBold", "GmarketSansTTFBold", "Gmarket Sans", "SCDream5", "맑은 고딕"];
for (var j = 0; j < tries.length; j++) {
    (function (name) {
        probe("font=" + name, function () {
            var comp = app.project.item(1);
            var t = comp.layers.addText("익절");
            var tp = t.property("ADBE Text Properties").property("ADBE Text Document");
            var d = tp.value;
            d.fontSize = 40; d.font = name;
            tp.setValue(d);
            var back = tp.value.font;
            var r = t.sourceRectAtTime(0, false);
            t.remove();
            return "→ " + back + (String(back) === name ? "  (박혔다)" : "  (다른 걸로 대체됐다)") +
                   " · 잉크폭 " + Math.round(r.width * 100) / 100;
        });
    })(tries[j]);
}
closeQuietly();

flush();
done("폰트 실측 끝");
