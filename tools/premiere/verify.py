#!/usr/bin/env python3
"""저장된 .prproj 를 gunzip 해서 숫자로 검사한다.

만드는 쪽(프리미어 안의 .jsx)과 검사하는 쪽을 처음부터 따로 둔다 (§3-5).
프리미어를 거치지 않으므로 프리미어가 "됐다"고 말한 것과 무관하게 파일이 진실을 말한다.

    python tools/premiere/verify.py C:/pprolab/src.prproj C:/pprolab/m1_out.prproj
"""
import gzip
import re
import sys
from collections import Counter

TICKS_PER_SEC = 254_016_000_000


def load(path):
    with gzip.open(path, "rb") as f:
        return f.read().decode("utf-8")


SEQ_RE = re.compile(r'<Sequence [^>]*ObjectUID="([0-9a-f-]+)"[^>]*>(.*?)</Sequence>', re.S)


def sequences(xml):
    """(uid, name) 목록. 시퀀스 정의는 ObjectUID 를 단 <Sequence> 뿐이다 —
    ObjectRef 만 단 <Sequence> 는 참조라 세면 안 된다 (실측: 정의 9 vs 태그 27)."""
    return [(m.group(1), (re.search(r"<Name>(.*?)</Name>", m.group(2)) or [None, "(?)"])[1])
            for m in SEQ_RE.finditer(xml)]


def facts(xml):
    seqs = sequences(xml)
    return {
        "xml_bytes": len(xml),
        "Sequence_ObjectID": len(seqs),
        "sequence_names": [n for _, n in seqs],
        "sequence_uids": [u for u, _ in seqs],
        "framerates": Counter(re.findall(r"<FrameRate>(\d+)</FrameRate>", xml)),
        "media_paths": len(re.findall(r"<ActualMediaFilePath>", xml)),
        "keyframes_blocks": len(re.findall(r"<Keyframes>", xml)),
        "root_version": (re.search(r"<PremiereData Version=\"(\d+)\"", xml) or [None, "?"])[1],
    }


def show(tag, f):
    print(f"[{tag}]")
    print(f"  PremiereData Version : {f['root_version']}")
    print(f"  XML bytes            : {f['xml_bytes']:,}")
    print(f"  시퀀스 정의          : {f['Sequence_ObjectID']}")
    for u, n in zip(f["sequence_uids"], f["sequence_names"]):
        print(f"    {u}  {n}")
    print(f"  <ActualMediaFilePath>: {f['media_paths']}")
    print(f"  <Keyframes>          : {f['keyframes_blocks']}")
    print("  FrameRate 틱:")
    for ticks, n in sorted(f["framerates"].items(), key=lambda kv: -kv[1]):
        t = int(ticks)
        fps = TICKS_PER_SEC / t if t else 0
        print(f"    {ticks:>14}  x{n:<4}  = {fps:.4f}" + ("  (29.97 드롭프레임)" if ticks == "8475667200"
              else "  (30.0)" if ticks == "8467200000" else ""))
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    paths = sys.argv[1:]
    all_facts = []
    for p in paths:
        f = facts(load(p))
        all_facts.append((p, f))
        show(p, f)

    if len(all_facts) == 2:
        (pa, a), (pb, b) = all_facts
        print("[비교]")
        d = b["Sequence_ObjectID"] - a["Sequence_ObjectID"]
        print(f"  시퀀스 수      : {a['Sequence_ObjectID']} -> {b['Sequence_ObjectID']}  ({d:+d})")
        same = a["framerates"] == b["framerates"]
        print(f"  FrameRate 분포 : {'그대로' if same else '바뀌었다'}")
        if not same:
            for k in sorted(set(a["framerates"]) | set(b["framerates"])):
                if a["framerates"][k] != b["framerates"][k]:
                    print(f"    {k}: {a['framerates'][k]} -> {b['framerates'][k]}")
        print(f"  미디어 참조 수 : {a['media_paths']} -> {b['media_paths']}")
        print(f"  키프레임 블록  : {a['keyframes_blocks']} -> {b['keyframes_blocks']}")
        added = [u for u in b["sequence_uids"] if u not in a["sequence_uids"]]
        gone = [u for u in a["sequence_uids"] if u not in b["sequence_uids"]]
        names = dict(zip(b["sequence_uids"], b["sequence_names"]))
        anames = dict(zip(a["sequence_uids"], a["sequence_names"]))
        print(f"  늘어난 시퀀스  : {', '.join(f'{names[u]} ({u})' for u in added) or '(없음)'}")
        print(f"  사라진 시퀀스  : {', '.join(f'{anames[u]} ({u})' for u in gone) or '(없음)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
