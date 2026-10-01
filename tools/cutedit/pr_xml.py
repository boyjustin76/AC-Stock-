# -*- coding: utf-8 -*-
"""컷리스트 → **프리미어가 내보낸 XML 을 틀로 삼아** 시퀀스 XML 을 만든다.

왜 이렇게 하나 (2026-10-01, 마01 캠)
  손으로 쓴 FCP7 XML 은 프리미어가 "프로젝트가 손상되어 열 수 없습니다" 로 거부했다.
  컷이 서넛이면 들어가고 일곱 개부터 막혔는데, 태그 구조·어휘는 성공본과 똑같았다.
  그래서 짐작을 그만두고 **프리미어가 실제로 뱉은 XML 을 틀로 쓴다.**
  틀에서 클립 하나·마커 하나를 떠다가 값만 갈아 끼우므로, 프리미어가 읽는 꼴에서 벗어나지 않는다.

틀에서 가져오는 것 — 시퀀스 뼈대(uuid·rate·format·outputs·labels), 비디오/오디오 클립 한 벌, 마커 한 벌.
갈아 끼우는 것 — 이름, 길이, start/end/in/out, pproTicks, 파일(이름·경로·길이), 링크, 꺼둠 여부.

    python3 tools/cutedit/pr_xml.py <컷리스트.json> <결과.xml> --틀 <프리미어내보내기.xml>
"""
import io, os, sys, json, copy
import xml.etree.ElementTree as ET

틱 = 254016000000          # 프리미어 1초 = 254,016,000,000 틱


def 프레임(초, fps): return int(round(초 * fps))


def 경로url(p):
    """프리미어 꼴 — 드라이브 콜론과 한글을 소문자 퍼센트로, 괄호·대괄호는 그대로 둔다."""
    p = p.replace("\\", "/")
    꼴 = []
    for ch in p:
        # & 를 빼먹으면 `캠용(얼굴&대본)[확보]` 같은 폴더에서 프리미어가 경로를 못 찾는다
        if ch in "/()[]&~!$'*+,;=@_-." or ch.isalnum() and ord(ch) < 128:
            꼴.append(ch)
        elif ch == " ":
            꼴.append("%20")
        else:
            꼴 += ["%%%02x" % b for b in ch.encode("utf-8")]
    return "file://localhost/" + "".join(꼴)


def 글(부모, 길, 값):
    e = 부모.find(길)
    if e is not None: e.text = str(값)
    return e


def 만들기(spec, 틀길):
    fps = float(spec.get("fps", 29.97))
    tb, ntsc = int(round(fps)), ("TRUE" if abs(fps - round(fps)) > 0.001 else "FALSE")
    나무 = ET.parse(틀길)
    뿌리 = 나무.getroot()
    시퀀스 = 뿌리.find("sequence")
    # 틀에서 본보기 떠 놓기
    v트랙들 = 시퀀스.findall("media/video/track")
    a트랙들 = 시퀀스.findall("media/audio/track")
    본보기V = copy.deepcopy(v트랙들[0].find("clipitem"))
    본보기A = copy.deepcopy([c for tr in a트랙들 for c in tr.findall("clipitem")][0])
    본보기마커 = copy.deepcopy(시퀀스.find("marker"))
    본보기V트랙 = copy.deepcopy(v트랙들[0]); 본보기A트랙 = copy.deepcopy(a트랙들[0])
    for tr in (본보기V트랙, 본보기A트랙):
        for c in tr.findall("clipitem"): tr.remove(c)
    for m in 시퀀스.findall("marker"): 시퀀스.remove(m)

    글(시퀀스, "name", spec.get("name", "시퀀스"))
    글(시퀀스, "rate/timebase", tb); 글(시퀀스, "rate/ntsc", ntsc)
    글(시퀀스, "timecode/rate/timebase", tb); 글(시퀀스, "timecode/rate/ntsc", ntsc)
    글(시퀀스, "timecode/displayformat", "DF" if ntsc == "TRUE" else "NDF")
    u = 시퀀스.find("uuid")
    if u is not None: u.text = "00000000-0000-0000-0000-%012d" % (abs(hash(spec.get("name", ""))) % 10 ** 12)

    번호통 = [0]
    def 다음번호():
        번호통[0] += 1
        return 번호통[0]

    원본 = spec.get("sources") or {}
    파일번호 = {k: i for i, k in enumerate(sorted(원본), 1)}
    낸파일 = set()

    def 파일요소(k):
        f = copy.deepcopy(본보기V.find("file"))
        f.set("id", "file-%d" % 파일번호[k])
        if k in 낸파일:
            for c in list(f): f.remove(c)
            return f
        낸파일.add(k)
        경로 = 원본[k]["path"]
        글(f, "name", os.path.basename(경로))
        글(f, "pathurl", 경로url(경로))
        글(f, "duration", 프레임(float(원본[k].get("dur", 0)), fps))
        return f

    # 컷 → 클립
    자리, 트랙컷 = 0.0, {}
    for i, c in enumerate(spec["cuts"], 1):
        k = c["src"] if "src" in c else "_main"
        tr = int(c.get("track", 1))
        s초 = float(c["at"]) if "at" in c else 자리
        길이 = float(c["out"]) - float(c["in"])
        if tr == 1 and c.get("video", True) and "at" not in c: 자리 += 길이
        트랙컷.setdefault(tr, []).append((i, k, c, s초, 길이))

    def 클립(본, i, k, c, s초, 길이, 소리채널=None):
        e = copy.deepcopy(본)
        e.set("id", "clipitem-%d" % 다음번호())
        글(e, "masterclipid", "masterclip-%d" % 파일번호[k])
        글(e, "name", c.get("label") or os.path.basename(원본[k]["path"]))
        글(e, "enabled", "TRUE" if c.get("enabled", True) else "FALSE")
        글(e, "duration", 프레임(float(원본[k].get("dur", 0)), fps))
        글(e, "rate/timebase", tb); 글(e, "rate/ntsc", ntsc)
        s, en = 프레임(s초, fps), 프레임(s초 + 길이, fps)
        i_f = 프레임(float(c["in"]), fps)
        글(e, "start", s); 글(e, "end", en)
        글(e, "in", i_f); 글(e, "out", i_f + (en - s))
        글(e, "pproTicksIn", int(round(i_f / fps * 틱)))
        글(e, "pproTicksOut", int(round((i_f + (en - s)) / fps * 틱)))
        낡 = e.find("file"); e.remove(낡)
        e.insert(list(e).index(e.find("anamorphic")) + 1 if e.find("anamorphic") is not None else 11, 파일요소(k))
        if 소리채널 is not None:
            글(e, "sourcetrack/trackindex", 소리채널)
        for ln in e.findall("link"): e.remove(ln)
        return e

    def 링크(e, 쪽, 영상있음, 소리있음):
        if not (소리있음 and (쪽.get("a1") or 쪽.get("a2"))): return      # 소리 짝이 없으면 링크 없음
        차례 = []
        if 영상있음 and 쪽.get("v"): 차례.append(("video", 쪽["v트랙"], 쪽["v"], None))
        if 소리있음:
            if 쪽.get("a1"): 차례.append(("audio", 1, 쪽["a1"], 1))
            if 쪽.get("a2"): 차례.append(("audio", 2, 쪽["a2"], 1))
        자리 = len(list(e))
        for 꼬리 in ("logginginfo", "colorinfo", "labels"):      # 링크는 이것들 **앞**에 와야 한다
            x = e.find(꼬리)
            if x is not None: 자리 = min(자리, list(e).index(x))
        for 종류, ti, ref, 그룹 in 차례:
            ln = ET.Element("link"); e.insert(자리, ln); 자리 += 1
            ET.SubElement(ln, "linkclipref").text = ref
            ET.SubElement(ln, "mediatype").text = 종류
            ET.SubElement(ln, "trackindex").text = str(ti)
            ET.SubElement(ln, "clipindex").text = str(자리표[ref])
            if 그룹: ET.SubElement(ln, "groupindex").text = "1"

    # 트랙 채우기 — 아이디는 비디오 트랙부터 차례로 하나씩 준다 (프리미어 내보내기와 같은 차례)
    v새, a새, 짝 = {}, {1: [], 2: []}, {}
    자리표 = {}
    for tr, 목록 in sorted(트랙컷.items()):
        목록.sort(key=lambda x: x[3])
        v새[tr] = []
        for n, (i, k, c, s초, 길이) in enumerate(목록, 1):
            if c.get("video", True):
                e = 클립(본보기V, i, k, c, s초, 길이)
                v새[tr].append(e)
                짝.setdefault(i, {})["v"] = e.get("id"); 짝[i]["v트랙"] = tr
                자리표[e.get("id")] = n
    for tr, 목록 in sorted(트랙컷.items()):
        if tr != 1: continue
        n1 = n2 = 0
        for i, k, c, s초, 길이 in 목록:
            if not c.get("audio", True): continue
            n1 += 1; n2 += 1
            e1 = 클립(본보기A, i, k, c, s초, 길이, 소리채널=1); a새[1].append(e1)
            e2 = 클립(본보기A, i, k, c, s초, 길이, 소리채널=2); a새[2].append(e2)
            짝.setdefault(i, {})["a1"] = e1.get("id"); 짝[i]["a2"] = e2.get("id")
            자리표[e1.get("id")] = n1; 자리표[e2.get("id")] = n2
    # 링크는 아이디가 다 정해진 뒤에
    for tr, 목록 in 트랙컷.items():
        for i, k, c, s초, 길이 in 목록:
            쪽 = 짝.get(i, {})
            영상, 소리 = c.get("video", True), c.get("audio", True) and tr == 1
            for 키, 목 in (("v", v새.get(tr, [])), ("a1", a새[1]), ("a2", a새[2])):
                for e in 목:
                    if e.get("id") == 쪽.get(키): 링크(e, 쪽, 영상, 소리)

    # 한 트랙 안에서 1프레임이라도 겹치면 프리미어가 통째로 거부한다 — 뒤로 민다 (2026-10-01)
    def 겹침풀기(목록):
        목록.sort(key=lambda e: int(e.findtext("start")))
        앞끝 = -1
        for e in 목록:
            st, en = int(e.findtext("start")), int(e.findtext("end"))
            if st < 앞끝:
                밀기 = 앞끝 - st
                글(e, "start", st + 밀기); 글(e, "end", en + 밀기)
                en += 밀기
            앞끝 = en
    for 목록 in list(v새.values()) + list(a새.values()): 겹침풀기(목록)

    비디오 = 시퀀스.find("media/video"); 오디오 = 시퀀스.find("media/audio")
    for tr in 비디오.findall("track"): 비디오.remove(tr)
    for tr in 오디오.findall("track"): 오디오.remove(tr)
    for tr in sorted(set(list(v새) + [1])):
        새트랙 = copy.deepcopy(본보기V트랙)
        for e in v새.get(tr, []): 새트랙.insert(list(새트랙).index(새트랙.find("enabled")), e)
        비디오.append(새트랙)
    for ch in (1, 2):
        새트랙 = copy.deepcopy(본보기A트랙)
        글(새트랙, "outputchannelindex", ch)
        for e in a새[ch]: 새트랙.insert(list(새트랙).index(새트랙.find("enabled")), e)
        오디오.append(새트랙)

    끝 = max([프레임(s초 + 길이, fps) for 목록 in 트랙컷.values() for _, _, _, s초, 길이 in 목록] or [0])
    글(시퀀스, "duration", 끝)
    # 마커
    for m in spec.get("markers", []):
        e = copy.deepcopy(본보기마커)
        글(e, "name", m.get("name", "")); 글(e, "comment", m.get("comment", ""))
        a = 프레임(float(m["at"]), fps)
        글(e, "in", a); 글(e, "out", a + 프레임(float(m.get("dur", 0)), fps) if m.get("dur") else -1)
        꼬리 = 시퀀스.find("labels")                              # 마커는 labels 앞에 모인다
        시퀀스.insert(list(시퀀스).index(꼬리) if 꼬리 is not None else len(list(시퀀스)), e)
    return 나무


if __name__ == "__main__":
    인자 = sys.argv[1:]
    틀 = 인자[인자.index("--틀") + 1]; del 인자[인자.index("--틀"):인자.index("--틀") + 2]
    컷길, 낼곳 = 인자[0], 인자[1]
    spec = json.load(io.open(컷길, encoding="utf-8"))
    나무 = 만들기(spec, 틀)
    글자 = ET.tostring(나무.getroot(), encoding="unicode")
    io.open(낼곳, "w", encoding="utf-8", newline="\n").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + 글자 + "\n")
    print("%s · 클립 %d · 마커 %d" % (낼곳, 글자.count("<clipitem"), 글자.count("<marker>")))
