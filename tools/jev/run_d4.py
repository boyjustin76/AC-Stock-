"""D-4 (D 가 고른 것) — 잡 로그 **한 줄**이 성공인가 실패인가.

왜 이 자리인가: 공용 실행기(`tools/_com/run.ps1`)는 지금 "bridge 가 답했고 시간 초과가 아니면 통과" 로
넘긴다. 이건 판단을 규칙으로 흉내 낸 것이다. 잡 로그를 읽고 판정할 수 있으면 그 자리를 채울 수 있다.

D-1(잡 단위)은 표본이 성공 쪽으로 쏠려 못 썼다. 줄 단위는 양쪽이 다 있다 — 탐침 잡은
표기법·인자 형태를 하나씩 바꿔 보며 되는 것과 안 되는 것을 **같은 파일 안에** 적어 둔다.

정답: D 가 직접 표시했다. 로그 원문은 `02_AE작업실_aelab/log/a3_frame2.txt`,
`06_실험실/pprolab/m5_frames2.txt`·`m6_probe2.txt`.

**어려운 자리를 일부러 넣었다** — `ret=true` 인데 파일이 안 늘어난 줄, `true` 인데 시퀀스 수가
그대로인 줄. 낱말만 보는 규칙은 여기서 틀린다.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jev  # noqa: E402

# (로그 줄(문맥 포함), 정답)  성공=할 일이 됐다 / 실패=안 됐다
CASES = [
    ('① 슬래시 + .png\t반환=[object Object] · 새 파일=없음', '실패'),
    ('② 슬래시 + 확장자없음\t반환=[object Object] · 새 파일=없음', '실패'),
    ('③ 역슬래시 + .png\t반환=[object Object] · 새 파일=없음', '실패'),
    ('④ fsName 로 다시 만든 File\t반환=[object Object] · 새 파일=없음', '실패'),
    ('⑤ 문자열 그대로\tthrow: Error: After Effects 오류: 2 매개 변수로 인해 "saveFrameToPng"을(를) '
     '호출할 수 없습니다. C:/aelab/frames/v5.png이(가) 파일 또는 폴더 개체가 아닙니다.', '실패'),
    ('⑥ 이미 열어 둔 File\t반환=[object Object] · 새 파일=v6.png', '성공'),
    ('슬래시 경로\tret=ERR Error: Unknown error exception  폴더=', '실패'),
    ('역슬래시 경로\tret=true  폴더=t_back.png.png', '성공'),
    ('프레임 번호\tret=ERR Error: Illegal Parameter type  폴더=t_back.png.png', '실패'),
    ('인자 순서 뒤집기\tret=false  폴더=t_back.png.png', '실패'),
    ('JPEG\tret=true  폴더=t.jpg.jpg,t_back.png.png', '성공'),
    ('TIFF\tret=true  폴더=t.jpg.jpg,t.tif.tif,t_back.png.png', '성공'),
    ('Targa\tret=true  폴더=t.jpg.jpg,t.tga.tga,t.tga.tga.xmp,t.tif.tif,t_back.png.png', '성공'),
    # 반환은 true 인데 폴더 목록이 앞 줄과 똑같다 — 새 png 가 안 생겼다
    ('앞 줄 폴더=t.jpg.jpg,t.tga.tga,t.tga.tga.xmp,t.tif.tif,t_back.png.png\n'
     'CTI 이동 후 PNG\tret=true  폴더=t.jpg.jpg,t.tga.tga,t.tga.tga.xmp,t.tif.tif,t_back.png.png', '실패'),
    ('qe.newSequence(역슬래시)\ttrue\n  → qe.newSequence(역슬래시)\t시퀀스 0 -> 0', '실패'),
    ('qe.newSequence(File 객체)\tERR Error: Illegal Parameter type\n'
     '  → qe.newSequence(File 객체)\t시퀀스 0 -> 0', '실패'),
    ('project.newSequence(역슬래시)\t[object Sequence]\n'
     '  → project.newSequence(역슬래시)\t시퀀스 0 -> 1  ★만들어졌다', '성공'),
    ('project.newSequence(이름만)\tERR Error: Not Enough Parameters\n'
     '  → project.newSequence(이름만)\t시퀀스 1 -> 1', '실패'),
    ('importFiles\ttrue', '성공'),
    ('createNewSequenceFromClips\t[object Sequence]\n'
     '  → createNewSequenceFromClips\t시퀀스 1 -> 2  ★만들어졌다', '성공'),
]

OPTIONS = {
    '성공': '하려던 것이 실제로 됐다',
    '실패': '하려던 것이 안 됐다',
}
# 지금 코드가 하는 일 — 낱말만 본다
RE_BAD = re.compile(r'ERR|throw|없음|false|Error')


def baseline(line):
    return '실패' if RE_BAD.search(line) else '성공'


def main():
    rows = []
    for line, want in CASES:
        ans = jev.ask(line, {'v': jev.choice(
            '이 로그 줄은 하려던 것이 됐음을 보여 주는가', OPTIONS)})
        got, conf = jev.pick(ans, 'v')
        b = baseline(line)
        rows.append({'줄': line.replace('\n', ' / ')[:70], '정답': want,
                     'jev': got, 'conf': conf, '규칙': b})
        m = 'O' if got == want else 'X'
        mb = 'O' if b == want else 'X'
        print(f"{m} jev {got}({conf:.2f})  {mb} 규칙 {b}  | {rows[-1]['줄'][:56]}")

    n = len(rows)
    j = sum(1 for r in rows if r['jev'] == r['정답'])
    b = sum(1 for r in rows if r['규칙'] == r['정답'])
    print(f"\njev {j}/{n} · 지금 규칙(낱말 보기) {b}/{n}")
    co = [r['conf'] for r in rows if r['jev'] == r['정답']]
    cn = [r['conf'] for r in rows if r['jev'] != r['정답']]
    print(f"confidence 맞은 것 {sum(co) / len(co):.2f}" if co else '',
          f"· 틀린 것 {sum(cn) / len(cn):.2f}" if cn else '· 틀린 것 없음')
    hard = [r for r in rows if r['규칙'] != r['정답']]
    if hard:
        print('\n낱말 규칙이 틀린 자리에서 jev 는:')
        for r in hard:
            print(f"   {'맞음' if r['jev'] == r['정답'] else '틀림'} ({r['conf']:.2f}) {r['줄'][:60]}")
    json.dump(rows, io.open(os.path.join(HERE, 'd4_result.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
