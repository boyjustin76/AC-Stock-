"""D-3 — 오류 한 줄을 보고 우리 constraint_note 63개 중 어느 것인지 Jev 가 고르게 한다 (radar 3순위 자리).

정답은 D 가 안다 — `log/inbox/2026-09-17_D_오류·비효율.md` 의 항목이 곧 constraint 38~46 이 됐다.
**확실한 것만 넣는다.** 애매한 것(A2·A3·A7·C5 처럼 constraint 로 안 올라간 것)은 빼서 정답을 지어내지 않는다.

주의: B1~B10 과 constraint 38~46 은 **같은 사건을 적은 글**이라 낱말이 겹친다.
그래서 이 시험은 '뜻으로 고르기' 보다 쉬운 쪽이다. 결과를 읽을 때 감안한다.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jev  # noqa: E402

# (오류 문장, 정답 constraint id) — D 가 직접 짝지은 것
CASES = [
    ('Bash 도구의 heredoc 이 역슬래시·따옴표를 망가뜨린다. 여러 번 겪었다.', 38),
    ('Windows 콘솔이 cp949 라 파이썬 출력과 파일 읽기가 한글에서 죽는다.', 39),
    ('Bash 에서 Windows 파이썬에 /c/Users/... 경로를 넘기면 한글이 깨져 파일을 못 찾는다.', 40),
    ('Node ESM 에서 Windows 절대경로로 import 하면 안 받는다.', 41),
    ('Claude Code 자동 모드 분류기가 설정 파일 쓰기를 막았다.', 42),
    ('세션이 붙잡고 있는 폴더는 옮길 수 없었다.', 43),
    ('파이썬 subprocess 로 python3 을 불렀더니 WindowsApps 가짜가 잡혀 거짓으로 통과했다.', 44),
    ('Gemini 비전 MCP 가 쿼터와 모델 폐기 때문에 막혔다.', 45),
    ('AE 잡이 끝났는지 반환값으로 판단했더니 틀렸다. 로그 파일을 봐야 했다.', 46),
    ('앱이 파일을 잡고 있어서 mogrt zip 만들기가 실패했다.', 46),
    ('비공개인 줄 알았던 저장소가 실은 공개였다.', 20),
    ('폴더를 옮겼더니 프리미어 프로젝트가 무는 미디어 경로가 전부 끊겼다.', 24),
]


def main():
    cons = json.load(io.open(os.path.join(HERE, 'constraints_63.json'), encoding='utf-8'))
    options = {str(c['id']): c['topic'] for c in cons}
    options['없음'] = '해당하는 것이 목록에 없다'

    rows = []
    for text, want in CASES:
        ans = jev.ask(text, {'c': jev.choice('이 일은 아래 기록 중 어느 것인가', options)})
        got, conf = jev.pick(ans, 'c')
        ok = (str(got) == str(want))
        rows.append({'문장': text, '정답': want, 'jev': got, 'conf': conf, '맞음': ok})
        mark = 'O' if ok else 'X'
        title = options.get(str(got), '?')[:34]
        print(f"{mark} 정답 {want:>3} · jev {str(got):>3} ({conf:.2f})  {title}")
        if not ok:
            print(f"    문장: {text[:60]}")

    n = len(rows)
    ok = sum(1 for r in rows if r['맞음'])
    co = [r['conf'] for r in rows if r['맞음']]
    cn = [r['conf'] for r in rows if not r['맞음']]
    print(f"\n{ok}/{n} 일치")
    print(f"confidence 맞은 것 평균 {sum(co) / len(co):.2f}" if co else "맞은 것 없음",
          f"· 틀린 것 평균 {sum(cn) / len(cn):.2f}" if cn else "· 틀린 것 없음")
    json.dump(rows, io.open(os.path.join(HERE, 'd3_result.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
