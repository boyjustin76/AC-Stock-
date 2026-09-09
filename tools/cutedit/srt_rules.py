# -*- coding: utf-8 -*-
"""숏폼 자막(.srt) 규칙 — 나누기 + 검사. 표준 라이브러리만 쓴다.

규칙 (2026-09-01 이정찬 피드백 — 룰북과 함께 진본):
  1. 큐 하나는 **띄어쓰기 포함 14자가 최대**다. 더 짧게 끊는 건 언제나 허용.
  2. 가능하면 절/구 단위로 자연스럽게 끊는다 — 쉼표 뒤, 연결어미(-고/-면/-서/…) 뒤가
     좋은 자리다.
  3. **관형형과 의존명사를 가르지 마라.** '~하는 것까지'를 '~하는 | 것까지'로 끊는
     종류의 분리 금지 — 의존명사(것·수·때·만큼·뿐·데·지…)로 큐를 시작하지 않는다.
  4. 텍스트는 대본 표기를 따른다 (STT 오인식 배제 — build_cuts.py 와 같은 원칙).

**금지(검사에서 반려)와 선호(벌점)를 갈라 둔다.** 사람이 확정한 자막에도 보조용언·
방위명사 앞에서 끊은 예가 있어서, 그걸 금지로 두면 납품본이 반려된다. 검사가 잡는
것은 위 규칙이 말하는 14자 초과와 의존명사 시작뿐이다.
나머지는 S015·S016 수정본 49문장으로 채점하며 맞췄다 (끊는 자리 31/53 → 35/53).

사용:
  나누기   from srt_rules import split_cue;  split_cue('문장 하나')  → ['조각', ...]
  검사     python3 tools/cutedit/srt_rules.py check 파일.srt [파일2.srt ...]

split_cue 는 어절 경계 DP다: 큐 수를 최소로 하되, 같은 큐 수면 쉼표/연결어미 뒤에서
끊는 답을 고르고, 의존명사 앞 분리는 사실상 금지(큰 벌점)한다. 한 어절이 14자를
넘으면 그 어절만 초과를 허용하고 검사에서 경고한다.
"""
import re
import sys

MAX_LEN = 14  # 띄어쓰기 포함 — **숏폼(1080x1920 세로)** 기준
# 자막 길이는 소리가 아니라 **화면 폭**이 정한다. 포맷이 바뀌면 이 값도 바뀐다.
#   숏폼 1080x1920 → 3~14자 (중앙값 8)   · 검정 박스 + 흰 글씨
#   롱폼 1920x1080 → 10~21자 (중앙값 15) · 검정 외곽선 + 흰 글씨
# 롱폼 실측은 더원 최종본 L04·L05 자막 21개에서 나온 관측 최댓값이다(확정 상한 아님).
# 롱폼을 다룰 때는 split_cue(..., max_len=21) 로 넘기거나 MAX_LEN 을 바꿔 쓴다.
LONG_MAX_LEN = 21

# 큐를 이걸로 시작하면 어색한 분리 (의존명사·보조용언류).
#
# 앞글자만 보고 판정하면 안 된다. '지'로 시작한다고 걸면 '지금·지수·지지선'이,
# '수'면 '수익을·수많은'이, '바'면 '바로·바닥을'이 걸린다. 실제로 차명 자막 34편을
# 돌렸더니 걸린 것 대부분이 이런 오탐이었다 (바로 12 · 지금 9 · 수익을 8 …).
# 그래서 **어절 전체가 '의존명사 + 조사'** 일 때만 잡는다. '것까지는' = 것+까지+는 ○,
# '지금' ×.
DEP_NOUNS = (
    '것', '수', '때', '때문', '만큼', '뿐', '데', '지', '채', '줄', '쪽', '터',
    '바', '듯', '척', '법', '리', '나름', '필요',
)
# 조사에 **서술격(이-계열)** 도 넣는다. '것이므로' 는 것+이므로 라서, 이게 없으면
# '확인되지 않은 | 것이므로' 처럼 관형형과 의존명사를 가른다 (S016 수정본 실측).
_PARTICLE = (r'(?:이|가|은|는|을|를|에|의|도|만|까지|부터|밖에|과|와|로|으로'
             r'|라도|조차|마저|에서|에게|처럼|보다|이나|나'
             r'|이므로|이고|이며|이라|이면|이지만|이다|이기|입니다)')
DEP_RE = re.compile(r'^(?:' + '|'.join(DEP_NOUNS) + r')' + _PARTICLE + r'*[.,!?]*$')
AUX_PREFIX = ()        # (검사에서 잡는 금지 목록. 규칙 ③은 의존명사만 말한다)
# ── 아래는 **나누기 선호**일 뿐 위반이 아니다 (검사에서 잡지 않는다) ──
# 사람이 확정한 자막에 이 자리에서 끊은 예가 실제로 있다:
#   S015 '일단 들어가보고 | 싶은 분들이 있어요', '방망이를 휘두르진 | 않습니다',
#   S015 '… | 아래 고정 댓글의 링크를'.
# 금지로 두면 납품본이 반려된다. 그래서 벌점으로만 둔다. 벌점은 큐 하나 값(100)
# 보다 커야 '한 큐 늘리더라도 여기서는 안 끊는다'가 된다.
SOFT_AUX = ('않', '싶')  # 보조용언 — '확인되지 | 않은', '들어가보고 | 싶은'
# 방위·위치 명사 — 앞 명사와 붙어 복합명사를 이룬다 ('구름대 안으로', '구름대 상단으로').
# 다만 '아래 고정 댓글' 처럼 뒤 명사를 꾸미기도 해서 금지까지는 못 한다.
POS_NOUN = ('위', '아래', '안', '밖', '상단', '하단', '가장자리', '근처', '부근',
            '사이', '옆', '앞', '뒤', '속', '내부', '외부')
SOFT_PENALTY = 150
# 부정부사 — 뒤 용언과 한 덩어리다. 큐를 이걸로 **끝내면** 안 된다.
# ('답이 안 | 나온다면' 처럼 갈리면 읽는 리듬이 끊긴다. S015 수정본 실측)
NO_END = ('안', '못', '잘', '더', '덜')
# '바로·때로는' 은 의존명사+조사로 갈라지지만 실제로는 부사다. 빼 준다.
NOT_DEP = ('바로', '때로', '때로는', '때때로', '대로', '제대로')
# 의존명사는 아니지만 앞 어절에 붙어 한 덩어리로 읽히는 것들.
# 금지까지는 아니고 벌점만 준다 — 규칙 ②(절/구 단위로 자연스럽게)를 돕는다.
# 실제로 '욕심 | 없이 짧게 수익' 처럼 갈라지는 자리가 나왔다.
WEAK_START = ('없이', '없는', '없을', '있는', '있을', '같은', '같이', '대로', '만한')
# 이 어미로 끝나는 어절 뒤는 끊기 좋은 자리 (절 경계)
GOOD_END = re.compile(r'(고|며|면|서|만|데|요|다|죠|까)[,.!?]?$')


def _bad_break(next_word):
    """금지 수준 — 검사(check)도 이걸 쓴다. 넓히면 납품본이 반려된다."""
    w = next_word.lstrip('"\'“‘')
    if w.rstrip('.,!?') in NOT_DEP:
        return False
    return bool(DEP_RE.match(w)) or w.startswith(AUX_PREFIX)


def _soft_break(next_word):
    """벌점 수준 — 되도록 피하지만 위반은 아니다 (검사에서 안 잡는다)."""
    w = next_word.lstrip('"\'“‘').rstrip('.,!?')
    if w in NOT_DEP:
        return False
    # 짧은 방위명사로 시작하면 앞 명사와 붙은 복합명사일 때가 많다.
    # 길면 딴 낱말이라 길이로 막는다 ('안정적인' 이 걸리면 안 된다).
    return w.startswith(SOFT_AUX) or (len(w) <= 4 and w.startswith(POS_NOUN))


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
        elif _soft_break(words[i]):
            s += SOFT_PENALTY   # 보조용언·복합명사 — 큐를 늘려서라도 피한다
        elif words[i].lstrip('"\'').startswith(WEAK_START):
            s += 40   # 앞말에 붙는 어절 — 다른 자리가 있으면 그쪽으로
        prev = words[i - 1]
        if prev in NO_END:
            s += 500  # 부정부사 뒤 분리 — 사실상 금지
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
    # 큐 끝의 쉼표·마침표는 뗀다 — 큐가 끊긴다는 것 자체가 이미 그 일을 한다.
    # 예외는 **되풀이** 하나다: '여기서도, | 여기서도 다시 밀렸죠?' 에서 쉼표를
    # 빼면 말을 더듬는 것처럼 읽힌다.
    # (S015 는 되풀이라 남겼고, S016 은 '복잡한 일목균형표, | 구름대만 남기세요',
    #  '더원 트레이더였습니다. | 감사합니다' 둘 다 뗐다 — 셋 다 이 규칙으로 맞는다.)
    out = [c.strip() for c in out if c.strip()]
    res = []
    for k, c in enumerate(out):
        nxt = out[k + 1] if k + 1 < len(out) else ''
        last = (c.rstrip('.,!?').split() or [''])[-1]
        first = (nxt.split() or [''])[0].rstrip('.,!?')
        res.append(c if (last and last == first) else re.sub(r'[.,]+$', '', c).strip())
    return [c for c in res if c]


# ── 검사 ──────────────────────────────────────────────────────────────

def parse_srt(path):
    txt = open(path, encoding='utf-8-sig').read()
    cues = []
    for block in re.split(r'\n\s*\n', txt.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) >= 3 and '-->' in lines[1]:
            cues.append((lines[1], ' '.join(lines[2:]).strip()))
    return cues


def check(path, max_len=MAX_LEN):
    cues = parse_srt(path)
    over, badstart = [], []
    for k, (tc, text) in enumerate(cues, 1):
        if len(text) > max_len:
            over.append((k, len(text), text))
        first = text.split()[0] if text.split() else ''
        if _bad_break(first):
            badstart.append((k, text))
    print(f'{path}: 큐 {len(cues)}개, 최장 {max((len(t) for _, t in cues), default=0)}자'
          f'  (기준 {max_len}자)')
    for k, L, t in over:
        print(f'  ⚠ #{k} {L}자 > {max_len}: {t}')
    for k, t in badstart:
        print(f'  ⚠ #{k} 의존명사로 시작 (앞 큐와 가른 자리 확인): {t}')
    if not over and not badstart:
        print('  통과')
    return not over and not badstart


if __name__ == '__main__':
    # --long : 롱폼(1920x1080) 자막은 한 줄에 더 들어간다. 21자 기준으로 본다.
    argv = [a for a in sys.argv if a != '--long']
    ML = LONG_MAX_LEN if '--long' in sys.argv else MAX_LEN
    if len(argv) >= 3 and argv[1] == 'check':
        # all(...) 은 첫 False 에서 멈춘다 — 뒤 파일이 검사되지 않는다.
        # 실제로 차11-5 의 위반 4건이 이 때문에 묻혀 있었다.
        ok = all([check(p, ML) for p in argv[2:]])
        sys.exit(0 if ok else 1)
    if len(argv) >= 3 and argv[1] == 'split':
        for c in split_cue(' '.join(argv[2:]), max_len=ML):
            print(f'{len(c):2d}  {c}')
        sys.exit(0)
    print(__doc__)
