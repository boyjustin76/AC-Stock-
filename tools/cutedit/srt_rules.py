# -*- coding: utf-8 -*-
"""숏폼 자막(.srt) 규칙 — 나누기 + 검사. 표준 라이브러리만 쓴다.

규칙 (2026-09-01 이정찬 피드백 — 룰북과 함께 진본):
  1. 큐 하나는 **띄어쓰기 포함 14자가 최대**다. 더 짧게 끊는 건 언제나 허용.
  2. 가능하면 절/구 단위로 자연스럽게 끊는다 — 쉼표 뒤, 연결어미(-고/-면/-서/…) 뒤가
     좋은 자리다.
  3. **관형형과 의존명사를 가르지 마라.** '~하는 것까지'를 '~하는 | 것까지'로 끊는
     종류의 분리 금지 — 의존명사(것·수·때·만큼·뿐·데·지…)로 큐를 시작하지 않는다.
  4. 텍스트는 대본 표기를 따른다 (STT 오인식 배제 — build_cuts.py 와 같은 원칙).

사용:
  나누기   from srt_rules import split_cue;  split_cue('문장 하나')  → ['조각', ...]
  검사     python3 tools/cutedit/srt_rules.py check 파일.srt [파일2.srt ...]

split_cue 는 어절 경계 DP다: 큐 수를 최소로 하되, 같은 큐 수면 쉼표/연결어미 뒤에서
끊는 답을 고르고, 의존명사 앞 분리는 사실상 금지(큰 벌점)한다. 한 어절이 14자를
넘으면 그 어절만 초과를 허용하고 검사에서 경고한다.
"""
import re
import sys

MAX_LEN = 14  # 띄어쓰기 포함

# 큐 첫 어절이 이걸로 시작하면 어색한 분리 (의존명사·보조용언류)
BAD_START = (
    '것', '수', '때', '만큼', '뿐', '데', '지', '채', '줄', '쪽', '터', '바',
    '듯', '척', '법이', '싶', '있는지',
)
# 의존명사는 아니지만 앞 어절에 붙어 한 덩어리로 읽히는 것들.
# 금지까지는 아니고 벌점만 준다 — 규칙 ②(절/구 단위로 자연스럽게)를 돕는다.
# 실제로 '욕심 | 없이 짧게 수익' 처럼 갈라지는 자리가 나왔다.
WEAK_START = ('없이', '없는', '없을', '있는', '있을', '같은', '같이', '대로', '만한')
# 이 어미로 끝나는 어절 뒤는 끊기 좋은 자리 (절 경계)
GOOD_END = re.compile(r'(고|며|면|서|만|데|요|다|죠|까)[,.!?]?$')


def _bad_break(next_word):
    w = next_word.lstrip('"\'')
    return any(w.startswith(b) for b in BAD_START)


def split_cue(sentence, max_len=MAX_LEN):
    """문장 하나 → 자막 큐 조각 리스트. 규칙 1~3을 함께 최적화한다."""
    words = [w for w in sentence.split() if w]
    if not words:
        return []
    n = len(words)

    def seg_len(i, j):  # words[i:j] 를 한 큐로 했을 때 길이 (공백 포함)
        return sum(len(w) for w in words[i:j]) + (j - i - 1)

    def break_score(i):  # words[i-1] | words[i] 사이에서 끊는 비용 (낮을수록 좋다)
        s = 0
        if _bad_break(words[i]):
            s += 500  # 의존명사 분리 — 사실상 금지
        elif words[i].lstrip('"\'').startswith(WEAK_START):
            s += 40   # 앞말에 붙는 어절 — 다른 자리가 있으면 그쪽으로
        prev = words[i - 1]
        if prev.endswith((',', '.', '!', '?')):
            s -= 3  # 문장부호 뒤 — 최적
        elif GOOD_END.search(prev):
            s -= 1  # 연결어미 뒤 — 좋음
        elif prev.endswith('는'):
            s += 2  # 관형형(-는) 뒤일 가능성 — 뒤 명사와 가르지 않는 쪽을 선호
        return s

    INF = 10 ** 9
    # dp[j] = (비용, 시작 i) — words[:j] 까지 나눴을 때 최소 비용. 큐 하나당 100.
    dp = [(INF, -1)] * (n + 1)
    dp[0] = (0, -1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            L = seg_len(i, j)
            if L > max_len and j - i > 1:
                break  # 어절 하나짜리 초과만 허용
            if dp[i][0] >= INF:
                continue
            cost = dp[i][0] + 100 + (break_score(i) if i > 0 else 0)
            if L > max_len:
                cost += 300  # 초과 어절 벌점 (불가피할 때만)
            if cost < dp[j][0]:
                dp[j] = (cost, i)
    # 역추적
    out, j = [], n
    while j > 0:
        i = dp[j][1]
        out.append(' '.join(words[i:j]))
        j = i
    out.reverse()
    # 큐 끝의 쉼표·마침표는 자막에서 떼는 게 기존 실측 관례
    return [re.sub(r'[.,]+$', '', c).strip() for c in out if c.strip()]


# ── 검사 ──────────────────────────────────────────────────────────────

def parse_srt(path):
    txt = open(path, encoding='utf-8-sig').read()
    cues = []
    for block in re.split(r'\n\s*\n', txt.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) >= 3 and '-->' in lines[1]:
            cues.append((lines[1], ' '.join(lines[2:]).strip()))
    return cues


def check(path):
    cues = parse_srt(path)
    over, badstart = [], []
    for k, (tc, text) in enumerate(cues, 1):
        if len(text) > MAX_LEN:
            over.append((k, len(text), text))
        first = text.split()[0] if text.split() else ''
        if _bad_break(first):
            badstart.append((k, text))
    print(f'{path}: 큐 {len(cues)}개, 최장 {max((len(t) for _, t in cues), default=0)}자')
    for k, L, t in over:
        print(f'  ⚠ #{k} {L}자 > {MAX_LEN}: {t}')
    for k, t in badstart:
        print(f'  ⚠ #{k} 의존명사로 시작 (앞 큐와 가른 자리 확인): {t}')
    if not over and not badstart:
        print('  통과')
    return not over and not badstart


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'check':
        # all(...) 은 첫 False 에서 멈춘다 — 뒤 파일이 검사되지 않는다.
        # 실제로 차11-5 의 위반 4건이 이 때문에 묻혀 있었다.
        ok = all([check(p) for p in sys.argv[2:]])
        sys.exit(0 if ok else 1)
    if len(sys.argv) >= 3 and sys.argv[1] == 'split':
        for c in split_cue(' '.join(sys.argv[2:])):
            print(f'{len(c):2d}  {c}')
        sys.exit(0)
    print(__doc__)
