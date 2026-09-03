/*  A5 — .mogrt 내보내기.

    경로 인자를 **반드시** 넣는다. 생략하면 대화상자가 뜰 수 있고, 모달은 잡을 죽인다
    (매뉴얼 §3-6). 이름은 A4 에서 이미 박아 뒀다.
*/
var HERE = String(File($.fileName).parent.fsName).split(String.fromCharCode(92)).join("/");
$.evalFile(new File(HERE + "/_lib.jsx"));
logTo("a5");

function __main() {

var AEP  = LAB + "/pilot.aep";
var NAME = "차11-4_컷2_손익비";
/*  ⚠ 실측: 두 번째 인자는 **파일이 아니라 폴더**다.
    파일 경로처럼 "…/차11-4_손익비.mogrt" 를 주니 AE 가 **그 이름의 폴더를 만들고**
    그 안에 "<motionGraphicsTemplateName>.mogrt" 를 썼다. 이름은 내가 아니라 템플릿 이름이 정한다.  */
var OUTDIR = LAB + "/mogrt";
var OUT    = OUTDIR + "/차11-4 손익비.mogrt";   /* = comp.motionGraphicsTemplateName + ".mogrt" */

say("잡", "A5 mogrt 내보내기");

closeQuietly();
probe("app.open", function () { app.open(new File(AEP)); return "열림"; });

var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === NAME) comp = it;
}
if (!comp) { flush(); return fail("컴포지션이 없다"); }
say("템플릿 이름", comp.motionGraphicsTemplateName);

probe("출력 폴더 준비", function () {
    var d = new Folder(OUTDIR);
    if (!d.exists) d.create();
    var f = new File(OUT);
    if (f.exists) f.remove();
    return d.fsName;
});

/*  ⚠ 실측: 이 호출은 **Adobe Fonts 동기화 경고 모달**을 띄운다.
      "다음 2개의 글꼴이 Adobe와 동기화되지 않았습니다 — Gmarket Sans Bold / S-Core Dream 5 Medium.
       모션 그래픽 템플릿이 Adobe에 없는 글꼴이 필요한 것으로 표시됩니다."
    브랜드 폰트가 Adobe Fonts 가 아니라 로컬 설치라서 그렇다. 회사 PC 엔 다 깔려 있으니 내용은 문제가 아니다.
    문제는 **모달이라 잡이 멈춘다**는 것. beginSuppressDialogs 로 넘어가는지 여기서 잰다.        */
probe("beginSuppressDialogs", function () { app.beginSuppressDialogs(); return "켬"; });
probe("exportAsMotionGraphicsTemplate", function () {
    return String(comp.exportAsMotionGraphicsTemplate(true, OUTDIR));
});
probe("endSuppressDialogs", function () { app.endSuppressDialogs(false); return "끔"; });

/* saveFrameToPng 과 같은 함정 — 직후에는 파일 정보가 아직 갱신 전이다 */
$.sleep(400);
probe("파일 확인", function () {
    var f = new File(OUT);
    return f.exists ? f.length + " bytes" : "파일이 없다";
});

flush();
return done("내보냈다. 구조 판정(zip 안 definition.json)은 밖에서 한다");
}
__main();
