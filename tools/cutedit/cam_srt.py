# -*- coding: utf-8 -*-
"""컷 시퀀스에 맞춘 자막(.srt) — 받아쓴 말이 아니라 **대본 문장**을 쓴다.

aligned.json 은 대본 문장마다 '이어 붙인 캠 타임라인'에서의 시각을 갖고 있고,
컷리스트는 그 구간을 잘라 시퀀스에 늘어놓은 것이다. 둘을 맞추면 컷 시퀀스 기준 자막이 된다.
받아쓴 글은 오타가 많아 자막으로 못 쓴다 — 글자는 대본에서 가져온다.

    python3 tools/cutedit/cam_srt.py <작업폴더> <컷리스트.json> <결과.srt> [--줄당 24]
"""
import io, os, re, sys, json, difflib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ko_clause

군더더기 = re.compile(r"[\s'\"‘’“”.,!?()\[\]/·…~\-+:;]")
맨글 = lambda t: 군더더기.sub("", t)


def 낱말시각(문장, 들, 토막들):
    """문장을 쪼갠 큐 조각마다 **실제 발화 낱말의 시각**을 찾아 준다.

    글자 수에 비례해 시간을 나누면 말이 빨라지거나 느려지는 대목에서 자막이 밀린다
    (마01 실측: 긴 문장 11조각 가운데 셋이 받아쓴 말과 0.2 아래로 어긋났다).
    대본 문장과 받아쓴 말을 글자 단위로 맞춘 뒤, 조각의 글자 자리를 낱말로 되짚는다.

    `들` 은 (낱말, 시작, 끝) 목록이다. **컷에 남은 낱말을 시퀀스 시각으로** 주면
    재촬영을 이어 붙인 문장도 맞는다 — 정렬 구간(마지막 테이크)만 보면 앞 테이크를
    쓴 조각이 엉뚱한 자리로 간다 (마01 문장 13 실측 2026-10-01).
    돌려주는 것은 (조각마다의 (시작, 끝) 또는 None, 마지막으로 쓴 낱말 번호).
    """
    들 = [w for w in 들 if w[0]]
    if not 들:
        return None, -1
    들글, 자리 = "", []                               # 자리[i] = 들글 i번째 글자가 몇 번째 낱말인지
    for k, (g, _, _) in enumerate(들):
        들글 += g
        자리 += [k] * len(g)
    원글 = 맨글(문장)
    짝 = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, 원글, 들글, autojunk=False).get_opcodes():
        if op == "equal":
            for d in range(i2 - i1): 짝[i1 + d] = j1 + d
    if not 짝:
        return None, -1

    def 되짚기(i):                                    # 맞은 자리가 없으면 가장 가까운 자리로
        if i in 짝: return 짝[i]
        return 짝[min(짝, key=lambda k: abs(k - i))]

    자, 결과, 마지막 = 0, [], -1
    for 조 in 토막들:
        n = len(맨글(조))
        if n == 0:
            결과.append(None); continue
        a, b = 되짚기(자), 되짚기(min(len(원글) - 1, 자 + n - 1))
        자 += n
        if a > b: a, b = b, a
        낱a, 낱b = 자리[a], 자리[b]
        결과.append((들[낱a][1], 들[낱b][2]))
        마지막 = max(마지막, 낱b)
    return 결과, 마지막

줄당기본 = ko_clause.최대기본   # 큐 글자 수는 **기준이 아니라 한계**다 — ko_clause 가 진본
창넓이 = 12.0        # 낱말을 찾을 창을 정렬 구간 양쪽으로 이만큼 넓힌다 (초) — 재촬영 이어짐 때문
당김 = 0.15           # 자막은 말보다 조금 먼저 뜬다 (L08 실측: 0.15초가 사람 수정본과 가장 가깝다)


def 시각(t):
    t = max(0.0, t)
    h, 남 = divmod(t, 3600); m, s = divmod(남, 60)
    return "%02d:%02d:%06.3f" % (h, m, s).replace(".", ",") if False else "%02d:%02d:%02d,%03d" % (h, m, int(s), round((s - int(s)) * 1000))


def 두줄(글, 줄당):
    낱말, 줄, 지금 = 글.split(), [], ""
    for w in 낱말:
        if len(지금) + len(w) + 1 > 줄당 and 지금:
            줄.append(지금); 지금 = w
        else:
            지금 = (지금 + " " + w).strip()
    if 지금: 줄.append(지금)
    return "\n".join(줄[:2]) if len(줄) <= 2 else "\n".join([" ".join(줄[:len(줄)//2]), " ".join(줄[len(줄)//2:])])


def 만들기(작업, 컷리스트, 줄당=줄당기본, fps=29.97):
    """시각은 **프레임으로 센다.** 초로 더하면 XML 보다 최대 0.08초 늦는다 (L08 불량 넷째)."""
    프레임 = lambda t: round(t * fps) / fps
    정렬 = json.load(io.open(os.path.join(작업, "aligned.json"), encoding="utf-8"))
    파일들 = json.load(io.open(os.path.join(작업, "cam_files.json"), encoding="utf-8"))
    받 = json.load(io.open(os.path.join(작업, "cam_transcript.json"), encoding="utf-8"))
    모든낱말 = sorted((w for s in 받 for w in (s.get("words") or [])), key=lambda w: float(w["s"]))
    컷들 = [c for c in 컷리스트["cuts"] if c.get("track", 1) == 1]
    시작맵 = {f["파일"][:8]: f["시작"] for f in 파일들}
    # 컷마다 (이어 붙인 시각 구간 → 시퀀스 시각) 변환표
    표, 자리프 = [], 0                                   # 자리는 프레임으로 센다
    for c in 컷들:
        바닥 = 시작맵.get(c["src"], 0.0)
        길이프 = round(c["out"] * fps) - round(c["in"] * fps)
        표.append((바닥 + c["in"], 바닥 + c["out"], 자리프 / fps))
        자리프 += 길이프
    def 옮기기(t, 앞으로=False):
        """원본 시각 → 시퀀스 시각.

        **덜어낸 자리에 떨어진 시각을 버리면 안 된다.** 컷에서 무음·박수를 빼내면 문장 가운데가
        비는데, 거기 떨어진 큐를 버리면 자막이 통째로 사라진다 — D 가 컷을 69개로 다듬은 뒤
        57문장 중 51문장이 날아갔다 (2026-10-01 실측). 가장 가까운 컷 경계로 붙인다.
        큐 **시작**은 다음 컷 머리로(앞으로=True), 큐 **끝**은 앞 컷 꼬리로 붙인다.
        """
        for a, b, s in 표:
            if a - 1e-6 <= t <= b + 1e-6: return s + (t - a)
        if 앞으로:
            뒤쪽 = [(a, s) for a, b, s in 표 if a > t]
            if 뒤쪽: return min(뒤쪽)[1]
        앞쪽 = [(b, s, a) for a, b, s in 표 if b < t]
        if 앞쪽:
            b, s, a = max(앞쪽); return s + (b - a)
        return 표[0][2] if 표 else None

    # 컷에 **남은** 낱말만 시퀀스 시각으로 늘어놓는다 — 자막 시각의 진본이다.
    # 덜어낸 무음·박수·재촬영은 여기 없으니, 이어 붙인 테이크도 저절로 맞는다.
    시간표 = []
    for w in 모든낱말:
        ws, we = float(w["s"]), float(w["e"])
        for a, b, s in 표:
            if ws < b and we > a:
                시간표.append((맨글(w.get("w", "")),
                               s + max(0.0, ws - a), s + min(b - a, we - a)))
                break
    시간표 = [w for w in 시간표 if w[0]]

    줄들 = []
    for r in 정렬:
        if r.get("s") is None or (r.get("score") or 0) < 0.75: continue
        글 = re.sub(r"\s+", " ", (r.get("text") or "").strip())
        # 글머리 기호만 뗀다. `\d` 를 넣으면 `1차 익절 …` 의 1 이 떨어진다 (마01 실측 2026-10-01).
        글 = re.sub(r"^(?:[•·]|\(\d+\))\s*", "", 글)
        if not 글 or 글.startswith("("): continue        # (차트를 보며 …) 같은 지시문은 뺀다
        시, 끝 = 옮기기(r["s"], 앞으로=True), 옮기기(r["e"])
        if 시 is None or 끝 is None or 끝 <= 시: continue
        # 한 문장이 길면 **구·절 단위로 쪼갠다**(ko_clause). 글자 수로 쪼개면 `알려 | 주는` 처럼
        # 말이 안 되는 자리에서 끊긴다 (이정찬 지적 2026-10-01). 안 쪼개면 90자 큐가 나온다.
        조각 = [c for c in ko_clause.조각내기(글, 최대=줄당) if c.strip()]
        # 조각마다의 시각은 **타임라인에 남은 낱말**에서 가져온다 (비례 분배는 말이 빨라지면 밀린다).
        # 창은 정렬 구간을 시퀀스로 옮긴 자리에서 **양쪽으로 넉넉히** 잡는다.
        # 재촬영을 이어 붙인 문장은 정렬 구간이 앞 테이크를 가리키고 이어지는 뒤 테이크가
        # 그 **뒤에** 붙어 있다 — 한쪽만 넓히면 반쪽만 보고 어긋난다 (마01 문장 13 실측).
        창 = [w for w in 시간표 if w[2] >= 시 - 창넓이 and w[1] <= 끝 + 창넓이]
        때, _ = 낱말시각(글, 창, 조각)
        총글자 = sum(len(맨글(c)) for c in 조각) or 1
        쌓 = 0
        for 자리, 조 in enumerate(조각):
            k = len(맨글(조))
            a, b = 시 + (끝 - 시) * 쌓 / 총글자, 시 + (끝 - 시) * (쌓 + k) / 총글자
            쌓 += k
            if 때 and 때[자리] and 때[자리][1] > 때[자리][0]:
                a, b = 때[자리]
            줄들.append((프레임(max(0.0, a - 당김)), 프레임(b), 조))
    줄들.sort()
    # 겹치면 앞 자막을 당겨 끊는다
    for i in range(len(줄들) - 1):
        if 줄들[i][1] > 줄들[i + 1][0]:
            줄들[i] = (줄들[i][0], max(줄들[i][0] + 0.3, 줄들[i + 1][0] - 0.05), 줄들[i][2])
    줄들 = [(a, b, t) for a, b, t in 줄들 if b > a]
    out = []
    for i, (a, b, 글) in enumerate(줄들, 1):
        out.append("%d\n%s --> %s\n%s\n" % (i, 시각(a), 시각(b), 두줄(글, 줄당)))
    return "\n".join(out), 줄들


if __name__ == "__main__":
    작업, 컷길, 낼곳 = sys.argv[1:4]
    줄당 = int(sys.argv[sys.argv.index("--줄당") + 1]) if "--줄당" in sys.argv else 줄당기본
    컷리스트 = json.load(io.open(컷길, encoding="utf-8"))
    글, 줄들 = 만들기(작업, 컷리스트, 줄당)
    io.open(낼곳, "w", encoding="utf-8").write(글)
    총 = sum(b - a for a, b, _ in 줄들)
    print("%s · 자막 %d줄 · 말하는 시간 %.1f분 · 평균 %.1f초" %
          (낼곳, len(줄들), 총 / 60, 총 / max(1, len(줄들))))
