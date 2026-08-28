#!/usr/bin/env python3
"""저장된 .prproj 를 gunzip 해서 숫자로 검사한다.

만드는 쪽(프리미어 안의 .jsx)과 검사하는 쪽을 처음부터 따로 둔다 (§3-5).
프리미어를 거치지 않으므로, 프리미어가 "됐다"고 말한 것과 무관하게 파일이 진실을 말한다.

기준선은 **원본이 아니라 "열고 아무것도 안 하고 saveAs 한 파일"** 이다 (§3-5 보강 / prproj_fact 22).
app.openDocument() 만으로 프리미어가 파일을 정규화하므로 원본 대비로 재면 그 정규화가
내 작업의 손실처럼 보인다.

[정정 2026-08-28 — D 대조군 실측] "열기만 한 파일"(in-place 재작성)은 기준선으로 쓰면 안 된다.
in-place 재작성은 부분 기록이라 saveAs 출력과 24종의 태그에서 다르다
(VideoComponentParam 2224 vs 2249, RangeLocked 102 vs 52, StartKeyframe 2688 vs 2728).
기준선은 **산출물과 같은 기록 경로(saveAs)를 지난 파일**이어야 한다 — 안 그러면
기록 경로 차이가 작업 손실로 둔갑한다. 실제로 그렇게 잡힌 가짜 손실이 RangeLocked -36 이었다.

    python tools/premiere/verify.py <저장본>
    python tools/premiere/verify.py <저장본> --baseline <다른 기준선>
    python tools/premiere/verify.py <저장본> --seq-delta 0     # 시퀀스가 안 늘어야 하는 작업

지표 (prproj_fact 23 / 클라우드·B 와 합의):
  * 키프레임은 컨테이너(<Keyframes>)가 아니라 **점(StartKeyframe)** 을 센다.
    컨테이너는 부분 복제를 놓친다.
  * **시퀀스 단위 객체 8종이 전부 같은 폭으로 늘었는지 전수 검사**한다.
    하나라도 안 늘었으면 반쪽 복제다.
  * 줄어든 태그는 전부 손실 후보로 보고한다.
"""
import argparse
import gzip
import os
import re
import sys
from collections import Counter

TICKS_PER_SEC = 254_016_000_000

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_BASELINE = os.path.join(REPO, "lab", "premiere", "baseline_open_save.prproj")

# 시퀀스 하나당 정확히 하나씩 있는 구조 객체. 복제하면 전부 같이 늘어야 한다.
# 기준선에서 개수 == 시퀀스 정의 수(9) 인 것들 중 시퀀스 객체 그래프의 척추만 골랐다.
SEQ_UNIT_TAGS = [
    "Sequence",              # 시퀀스 정의 자체 (ObjectUID 를 단 것만)
    "VideoSequenceSource",
    "AudioSequenceSource",
    "TrackGroups",
    "VideoTrackGroup",
    "AudioTrackGroup",
    "DataTrackGroup",
    "MasterTrack",
]

KEYFRAME_TAGS = ["StartKeyframe", "StartKeyframePosition", "StartKeyframeValue"]

# 편집기 세션 상태 — 내용물이 아니다. 어떤 시퀀스 탭이 열려 있었는지, 패널 트리가
# 펼쳐져 있었는지 같은 것. 좁게만 잡는다. 넓히면 진짜 손실을 가린다.
UI_STATE_PREFIXES = (
    "MZ.PrefixKey.",            # OpenSequenceGuidList — 열려 있던 시퀀스 탭
    "list.view.expanded.state.",  # 프로젝트 패널 트리 펼침
    "project.icon.view.",       # 아이콘 보기 정렬
)


def is_ui_state(tag):
    return tag.startswith(UI_STATE_PREFIXES)

SEQ_RE = re.compile(r'<Sequence [^>]*ObjectUID="([0-9a-f-]+)"[^>]*>(.*?)</Sequence>', re.S)
TAG_RE = re.compile(r"<([A-Za-z][A-Za-z0-9_.]*)[ />]")
MEDIA_RE = re.compile(r"<ActualMediaFilePath>(.*?)</ActualMediaFilePath>")


def load(path):
    with gzip.open(path, "rb") as f:
        return f.read().decode("utf-8")


def sequences(xml):
    """(uid, name) 목록. 시퀀스 정의는 ObjectUID 를 단 <Sequence> 뿐이다 —
    ObjectRef 만 단 <Sequence> 는 참조라 세면 안 된다 (실측: 정의 9 vs 태그 27)."""
    return [(m.group(1), (re.search(r"<Name>(.*?)</Name>", m.group(2)) or [None, "(?)"])[1])
            for m in SEQ_RE.finditer(xml)]


def facts(xml):
    seqs = sequences(xml)
    tags = Counter(TAG_RE.findall(xml))
    tags["Sequence"] = len(seqs)          # 참조가 아니라 정의만 센다
    paths = MEDIA_RE.findall(xml)
    return {
        "xml_bytes": len(xml),
        "root_version": (re.search(r'<PremiereData Version="(\d+)"', xml) or [None, "?"])[1],
        "seq_uids": [u for u, _ in seqs],
        "seq_names": dict(seqs),
        "tags": tags,
        "keyframe_tags": {t: tags.get(t, 0) for t in KEYFRAME_TAGS},
        "keyframe_raw": xml.count("StartKeyframe"),   # 클라우드·B 와 합의된 문자열 지표
        "keyframe_blocks": len(re.findall(r"<Keyframes>", xml)),
        "media_refs": len(paths),
        "media_unique": sorted(set(p for p in paths if ":" in p)),
        "framerates": Counter(re.findall(r"<FrameRate>(\d+)</FrameRate>", xml)),
    }


def secs(ticks):
    return int(ticks) / TICKS_PER_SEC


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("target", help="검사할 .prproj")
    ap.add_argument("--baseline", default=DEFAULT_BASELINE, help="기준선 .prproj")
    ap.add_argument("--seq-delta", type=int, default=None,
                    help="시퀀스가 몇 개 늘어야 하는지. 생략하면 실측값을 그대로 기대값으로 쓴다")
    args = ap.parse_args()

    a = facts(load(args.baseline))
    b = facts(load(args.target))
    ok = True

    print(f"기준선 : {args.baseline}")
    print(f"대상   : {args.target}")
    print(f"         PremiereData v{a['root_version']} → v{b['root_version']} · "
          f"XML {a['xml_bytes']:,} → {b['xml_bytes']:,} 바이트")
    print()

    # ---- 1. 시퀀스 -------------------------------------------------------
    added = [u for u in b["seq_uids"] if u not in a["seq_uids"]]
    gone = [u for u in a["seq_uids"] if u not in b["seq_uids"]]
    delta = len(b["seq_uids"]) - len(a["seq_uids"])
    expect = args.seq_delta if args.seq_delta is not None else delta

    print(f"[시퀀스]  {len(a['seq_uids'])} → {len(b['seq_uids'])}  ({delta:+d}, 기대 {expect:+d})")
    for u in added:
        print(f"  + {b['seq_names'][u]}  ({u})")
    for u in gone:
        print(f"  - {a['seq_names'][u]}  ({u})   ← 사라졌다")
        ok = False
    if delta != expect:
        print(f"  ✗ 시퀀스 증감이 기대와 다르다")
        ok = False
    print()

    # ---- 2. 시퀀스 단위 객체 전수 검사 -----------------------------------
    print(f"[시퀀스 단위 객체 전수 검사]  {len(SEQ_UNIT_TAGS)}종이 전부 {expect:+d} 여야 한다")
    for t in SEQ_UNIT_TAGS:
        na, nb = a["tags"].get(t, 0), b["tags"].get(t, 0)
        d = nb - na
        mark = "✓" if d == expect else "✗"
        if d != expect:
            ok = False
        print(f"  {mark} {t:<22} {na:>4} → {nb:>4}  ({d:+d})")
    print()

    # ---- 3. 키프레임 점 --------------------------------------------------
    print("[키프레임 — 컨테이너 말고 점을 센다]")
    for t in KEYFRAME_TAGS:
        na, nb = a["keyframe_tags"][t], b["keyframe_tags"][t]
        print(f"    {t:<22} {na:>6} → {nb:>6}  ({nb - na:+d})")
    print(f"    {'문자열 출현(합의 지표)':<22} {a['keyframe_raw']:>6} → {b['keyframe_raw']:>6}"
          f"  ({b['keyframe_raw'] - a['keyframe_raw']:+d})")
    print(f"    {'<Keyframes> 컨테이너':<22} {a['keyframe_blocks']:>6} → {b['keyframe_blocks']:>6}"
          f"  ({b['keyframe_blocks'] - a['keyframe_blocks']:+d})")
    if b["keyframe_tags"]["StartKeyframe"] < a["keyframe_tags"]["StartKeyframe"]:
        print("    ✗ StartKeyframe 점이 줄었다 — 키프레임 손실")
        ok = False
    print()

    # ---- 4. 줄어든 태그 = 손실 후보 --------------------------------------
    shrank = sorted(((b["tags"].get(t, 0) - a["tags"][t], t) for t in a["tags"]
                     if b["tags"].get(t, 0) < a["tags"][t]))
    lost = [(d, t) for d, t in shrank if not is_ui_state(t)]
    ui = [(d, t) for d, t in shrank if is_ui_state(t)]

    print(f"[줄어든 태그]  내용물 {len(lost)}종 · 편집기 세션 상태 {len(ui)}종")
    if not lost:
        print("  ✓ 내용물 손실 없음 — 기준선에 있던 것은 전부 살아 있다")
    for d, t in lost[:30]:
        print(f"  ✗ {t:<40} {a['tags'][t]:>5} → {b['tags'].get(t, 0):>5}  ({d:+d})")
        ok = False
    if len(lost) > 30:
        print(f"  … 그 밖에 {len(lost) - 30}종")
    for d, t in ui:
        print(f"  · {t:<40} {a['tags'][t]:>5} → {b['tags'].get(t, 0):>5}  ({d:+d})   (세션 상태, 무시)")
    print()

    # ---- 5. 미디어 경로 --------------------------------------------------
    ma, mb = set(a["media_unique"]), set(b["media_unique"])
    print(f"[미디어]  참조 {a['media_refs']} → {b['media_refs']} · "
          f"고유 경로 {len(ma)} → {len(mb)}")
    for p in sorted(mb - ma):
        print(f"  + {p}")
    for p in sorted(ma - mb):
        print(f"  - {p}")
    if not (mb - ma) and not (ma - mb):
        print("  (고유 경로 변화 없음)")
    print()

    # ---- 6. FrameRate ----------------------------------------------------
    print("[FrameRate 틱]")
    for t in sorted(set(a["framerates"]) | set(b["framerates"]), key=lambda k: -int(k)):
        na, nb = a["framerates"][t], b["framerates"][t]
        fps = TICKS_PER_SEC / int(t)
        note = "  (29.97 드롭프레임)" if t == "8475667200" else "  (30.0)" if t == "8467200000" else ""
        print(f"    {t:>14}  {na:>4} → {nb:>4}   = {fps:.4f}{note}")
    if set(a["framerates"]) != set(b["framerates"]):
        print("    ✗ FrameRate 값 집합이 바뀌었다")
        ok = False
    else:
        print("    ✓ 값 집합 불변")
    print()

    print("=" * 60)
    print("판정: " + ("통과 ✓" if ok else "실패 ✗"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
