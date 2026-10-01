# -*- coding: utf-8 -*-
"""컷 시퀀스에 맞춘 자막(.srt) — 받아쓴 말이 아니라 **대본 문장**을 쓴다.

aligned.json 은 대본 문장마다 '이어 붙인 캠 타임라인'에서의 시각을 갖고 있고,
컷리스트는 그 구간을 잘라 시퀀스에 늘어놓은 것이다. 둘을 맞추면 컷 시퀀스 기준 자막이 된다.
받아쓴 글은 오타가 많아 자막으로 못 쓴다 — 글자는 대본에서 가져온다.

    python3 tools/cutedit/cam_srt.py <작업폴더> <컷리스트.json> <결과.srt> [--줄당 24]
"""
import io, os, re, sys, json

줄당기본 = 24          # 한 줄 글자 수 (회사 숏폼 자막 실측 14자보다 길게 — 롱폼은 두 줄까지 쓴다)
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
    컷들 = [c for c in 컷리스트["cuts"] if c.get("track", 1) == 1]
    시작맵 = {f["파일"][:8]: f["시작"] for f in 파일들}
    # 컷마다 (이어 붙인 시각 구간 → 시퀀스 시각) 변환표
    표, 자리프 = [], 0                                   # 자리는 프레임으로 센다
    for c in 컷들:
        바닥 = 시작맵.get(c["src"], 0.0)
        길이프 = round(c["out"] * fps) - round(c["in"] * fps)
        표.append((바닥 + c["in"], 바닥 + c["out"], 자리프 / fps))
        자리프 += 길이프
    def 옮기기(t):
        for a, b, s in 표:
            if a <= t <= b: return s + (t - a)
        return None
    줄들 = []
    for r in 정렬:
        if r.get("s") is None or (r.get("score") or 0) < 0.75: continue
        글 = re.sub(r"\s+", " ", (r.get("text") or "").strip())
        글 = re.sub(r"^[•\-\d.)\s]+", "", 글)            # 대본의 글머리 기호는 자막에 안 쓴다
        if not 글 or 글.startswith("("): continue        # (차트를 보며 …) 같은 지시문은 뺀다
        시, 끝 = 옮기기(r["s"]), 옮기기(r["e"])
        if 시 is None or 끝 is None or 끝 <= 시: continue
        시, 끝 = 프레임(max(0.0, 시 - 당김)), 프레임(끝)     # 당김 뒤 프레임에 맞춘다
        if 끝 <= 시: continue
        줄들.append((시, 끝, 글))
    줄들.sort()
    # 겹치면 앞 자막을 당겨 끊는다
    for i in range(len(줄들) - 1):
        if 줄들[i][1] > 줄들[i + 1][0]:
            줄들[i] = (줄들[i][0], max(줄들[i][0] + 0.3, 줄들[i + 1][0] - 0.05), 줄들[i][2])
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
