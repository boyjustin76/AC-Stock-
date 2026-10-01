/*  EXTENDSCRIPT-TRAPS ⑨-4 를 다시 재는 잡 — **지금은 재현되지 않는다.**

    ⑨-4 에 `pdfCompatible = false` 로 저장하면

        Acrobat PDF 파일 포맷에 문제가 있습니다. The size of the passed callbacks struct is wrong.

    창이 뜨고 COM 이 멈춘다고 적어 두었다(2026-09-21 오전, 라이브화면 빌드 중에 겪은 것).
    그런데 2026-09-21 오후에 **새로 만든 200x200 빈 문서**로 같은 옵션을 주니 창 없이 3.1초에
    저장되었다(일러스트레이터 30.8.1). 즉 그 모달은 '옵션을 끄면 반드시' 가 아니라
    **문서 내용이나 앞선 상태에 달려 있다**. ⑨-4 를 '늘 뜬다' 로 읽으면 안 된다.

    그래서 실행기 실패 경로 시험에는 이 잡 대신 `_trap_alert.jsx` 를 쓴다(alert 은 늘 뜬다).
    이 파일은 ⑨-4 의 조건을 다시 좁힐 때 쓰라고 남긴다 — 큰 원본을 연 뒤에 돌려 보는 식으로.

    이름 앞의 밑줄은 일부러다 — 판정 줄 래칫(tests/test_verdict_lines.py)이 건너뛴다.

    쓰는 법:  .\tools\illustrator\run.ps1 _trap_pdf_modal -TimeoutSec 60
    결과:     지금은 통과(경고)로 끝나고 임시 폴더에 .ai 한 장이 남는다. 문서는 닫고 나온다.
*/
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;   // 알림을 켜야 창이 뜬다

var doc = app.documents.add(DocumentColorSpace.RGB, 200, 200);
var f = new File(Folder.temp + "/_trap_pdf_modal.ai");

var so = new IllustratorSaveOptions();
so.compatibility = Compatibility.ILLUSTRATOR24;
so.pdfCompatible = false;      // ← 여기서 창이 뜨고 멈춘다
doc.saveAs(f, so);

doc.close(SaveOptions.DONOTSAVECHANGES);   /* 쌓이지 않게 닫는다 — 함정이 걸리면 여기까지 못 온다 */

"여기까지 왔으면 함정이 안 걸린 것이다";
