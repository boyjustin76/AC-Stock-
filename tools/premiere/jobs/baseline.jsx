/*
    대조군. 프리셋 사본을 열고 **아무것도 하지 않고** 다른 이름으로 저장한다.

    매뉴얼 §3-5 보강이 말하는 기준선은 "열고 아무것도 안 하고 저장한 파일" 이다.
    m1_after_open_only.prproj 는 saveAs 없이 열기만 한 in-place 재작성본이라
    저장 정규화가 빠져 있다 — 복제 손실과 저장 정규화를 구분하려면 이 파일이 필요하다.
*/
(function () {
    var SRC = "C:/pprolab/baseline_src.prproj";
    var OUT = "C:/pprolab/baseline.prproj";
    var out = [];
    function say(k, v) { out.push(k + "\t" + v); }

    say("src_size_before", new File(SRC).length);
    app.openDocument(SRC, 1, 1, 1, 1);
    var w = 0;
    while (w < 180) {
        try { if (app.project.path.indexOf("baseline_src") >= 0 && app.project.sequences.numSequences > 0) break; } catch (e) {}
        $.sleep(500); w += 0.5;
    }
    say("waited_sec", w);
    say("project.path", app.project.path);
    say("numSequences", app.project.sequences.numSequences);
    say("src_size_after_open", new File(SRC).length);

    // 아무것도 바꾸지 않는다. 저장만 한다.
    say("saveAs", String(app.project.saveAs(OUT)));
    say("out_size", new File(OUT).length);

    var f = new File("C:/pprolab/baseline.txt");
    f.encoding = "UTF-8"; f.open("w"); f.write(out.join("\n")); f.close();
    return "baseline ok";
})();
