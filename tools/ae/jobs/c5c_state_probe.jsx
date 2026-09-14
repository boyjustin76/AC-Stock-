/*  C5c — 지금 열린 프로젝트 상태를 **읽기만** 한다 (1회용 실측, 아무것도 바꾸지 않는다).
    c5 가 mogrt 2개를 내보낸 뒤 '컴포지션을 다시 못 찾았다' 로 멈춘 원인을 가린다:
    내보내기가 app.project 를 다른(임시) 프로젝트로 바꿔 놓았는가, 이름이 바뀌었는가, 항목이 사라졌는가.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("c5c");

function __main() {
say("잡", "C5c 열린 프로젝트 상태 (읽기 전용)");
probe("프로젝트 파일", function () { return app.project.file ? app.project.file.fsName : "(저장 안 된 새 프로젝트)"; });
probe("항목 수", function () { return String(app.project.numItems); });
probe("수정됨(dirty)", function () { return String(app.project.dirty); });
var comps = [], folders = [], foot = 0;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem) comps.push(i + ":" + it.name + " [tpl=" + it.motionGraphicsTemplateName + "]");
    else if (it instanceof FolderItem) folders.push(it.name);
    else foot++;
}
say("폴더", folders.join(" | "));
say("푸티지", foot + "개");
say("컴포지션", comps.length + "개");
for (var k = 0; k < comps.length; k++) out.push("    " + comps[k]);
/* 이름 비교 — 스크립트 문자열과 항목 이름이 바이트 단위로 같은가 (정규화 차이 의심 시) */
probe("이름 대조 '손익비 · 진입선'", function () {
    var want = "손익비 · 진입선", hit = "없음";
    for (var j = 1; j <= app.project.numItems; j++) {
        var c = app.project.item(j);
        if (!(c instanceof CompItem)) continue;
        if (c.name === want) return "정확히 일치 @" + j;
        if (c.name.indexOf("진입선") >= 0) {
            var codes = [];
            for (var q = 0; q < c.name.length; q++) codes.push(c.name.charCodeAt(q).toString(16));
            hit = "비슷한 이름 @" + j + " codes=" + codes.join(",");
        }
    }
    return hit;
});
flush();
return done("읽기만 함");
}
__main();
