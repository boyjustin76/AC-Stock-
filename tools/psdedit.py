#!/usr/bin/env python3
"""템플릿 .psd 를 그대로 편집한다 — 레이어 구성을 100% 보존하려고.

썸네일을 처음부터 새로 쓰면 그룹·스마트오브젝트·조정레이어·레이어 효과·라이브
텍스트가 전부 날아간다.  그래서 회사 템플릿을 열어 회차 그룹 하나를 통째로
복제하고, 그 안의 차트 픽셀과 타이틀 글자만 바꿔 넣는다.

    from tools.psdedit import Template
    t = Template("차트명가(롱)_하이라이트 - 복사본.psd")
    t.clone_group("#1 쿠라마기", "#11 20일선의 비밀")
    t.set_text("#11 20일선의 비밀", "이동평균선 매매법", "20일선 매매법")
    t.replace_pixels("#11 20일선의 비밀", "차트", chart_png)
    t.solo("#11 20일선의 비밀")
    t.save("out.psd")

레이어 레코드는 아래에서 위 순서로 늘어서 있고, 한 그룹은
    [</Layer group> 끝표시] … 자식들 … [폴더 헤더]
연속 구간이라 그 구간을 통째로 복사하면 그룹이 복제된다.
"""
from __future__ import annotations

import copy
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage
from psd_tools.constants import ChannelID, Compression, Tag
from psd_tools.psd.layer_and_mask import ChannelData, ChannelDataList, ChannelInfo


def _luni(record) -> str | None:
    b = record.tagged_blocks
    if not b:
        return None
    for key in (Tag.UNICODE_LAYER_NAME, b"luni"):
        try:
            v = b.get_data(key)
            if v:
                return str(v).rstrip("\x00")
        except Exception:
            pass
    return None


class Template:
    def __init__(self, path: str | Path):
        self.psd = PSDImage.open(str(path))
        self.li = self.psd._record.layer_and_mask_information.layer_info

    # ── 조회 ───────────────────────────────────────────────────
    @property
    def records(self):
        return self.li.layer_records

    @property
    def channels(self):
        return self.li.channel_image_data

    def name_of(self, i: int) -> str:
        return _luni(self.records[i]) or self.records[i].name

    def index_of(self, name: str) -> int:
        for i in range(len(self.records)):
            if self.name_of(i) == name:
                return i
        raise KeyError(f"'{name}' 레이어가 없습니다")

    def group_span(self, name: str) -> tuple[int, int]:
        """폴더 헤더에서 아래로 내려가며 짝이 맞는 끝표시를 찾는다.

        레코드는 아래→위 순서고 한 그룹은
            [끝표시 lsct=3] … 자식들 … [폴더 헤더 lsct=1|2]
        이므로 헤더에서 인덱스를 줄여 가며 깊이를 세면 구간이 나온다.
        """
        top = self.index_of(name)
        if self._divider(top) not in (1, 2):
            raise ValueError(f"'{name}' 은 그룹이 아닙니다")
        depth = 1
        for i in range(top - 1, -1, -1):
            k = self._divider(i)
            if k in (1, 2):
                depth += 1
            elif k == 3:
                depth -= 1
                if depth == 0:
                    return i, top
        raise ValueError(f"'{name}' 그룹의 끝표시를 찾지 못했습니다")

    def _divider(self, i: int):
        b = self.records[i].tagged_blocks
        if not b:
            return None
        d = b.get_data(Tag.SECTION_DIVIDER_SETTING)
        return int(d.kind) if d else None

    # ── 편집 ───────────────────────────────────────────────────
    def _max_layer_id(self) -> int:
        top = 0
        for r in self.records:
            b = r.tagged_blocks
            v = b.get_data(Tag.LAYER_ID) if b else None
            if v is not None:
                top = max(top, int(v))
        return top

    def clone_group(self, src: str, new_name: str) -> tuple[int, int]:
        """그룹 하나를 통째로 복제한다.

        레이어 ID(lyid)는 반드시 새로 매긴다.  그대로 두면 문서 안에 같은 ID 가
        둘씩 생기고, 합성할 때 복제본이 통째로 빠져 버린다.
        """
        lo, hi = self.group_span(src)
        recs = copy.deepcopy(self.records[lo:hi + 1])
        chs = copy.deepcopy(self.channels[lo:hi + 1])
        nid = self._max_layer_id()
        for r in recs:
            b = r.tagged_blocks
            if b and b.get(Tag.LAYER_ID) is not None:
                nid += 1
                b.set_data(Tag.LAYER_ID, nid)
        self._rename(recs[-1], new_name)
        at = hi + 1
        self.records[at:at] = recs
        self.channels[at:at] = chs
        self.li.layer_count = len(self.records)
        return at, at + len(recs) - 1

    @staticmethod
    def _legacy(name: str) -> str:
        """옛 pascal 이름 칸은 macroman 으로 기록된다.

        원본도 한글을 cp949 로 인코딩한 바이트를 macroman 으로 읽은 깨진 글자로
        담고 있다.  같은 방식으로 넣어야 저장이 되고, 포토샵이 읽는 진짜 이름은
        아래 luni(유니코드) 쪽이다.
        """
        try:
            return name.encode("cp949").decode("mac_roman")
        except Exception:
            return name.encode("ascii", "replace").decode("ascii")

    def _rename(self, record, name: str) -> None:
        record.name = self._legacy(name)
        b = record.tagged_blocks
        if not b:
            return
        for key in (Tag.UNICODE_LAYER_NAME, b"luni"):
            try:
                if b.get(key) is not None:
                    b.set_data(key, name)
                    return
            except Exception:
                pass

    def find_in(self, group: str, layer: str) -> int:
        lo, hi = self.group_span(group)
        for i in range(lo, hi + 1):
            if self.name_of(i) == layer:
                return i
        raise KeyError(f"'{group}' 안에 '{layer}' 가 없습니다")

    def set_text(self, group: str, layer: str, text: str) -> None:
        i = self.find_in(group, layer)
        td = self.records[i].tagged_blocks.get_data(Tag.TYPE_TOOL_OBJECT_SETTING).text_data
        body = text + "\r"
        td[b"Txt "].value = text + "\x00"
        doc = td[b"EngineData"].value["EngineDict"]
        doc["Editor"]["Text"].value = body
        for run in ("StyleRun", "ParagraphRun"):
            arr = doc[run]["RunLengthArray"]
            for k in range(len(arr) - 1, 0, -1):
                del arr[k]
            arr[0].value = len(body)
        self._rename(self.records[i], text)

    def replace_pixels(self, group: str, layer: str, image: str | Path | Image.Image,
                       left: int = 0, top: int = 0) -> None:
        """픽셀 레이어의 내용을 통째로 바꾼다. 위치·크기도 이미지에 맞춘다."""
        i = self.find_in(group, layer)
        img = image if isinstance(image, Image.Image) else Image.open(str(image))
        img = img.convert("RGBA")
        w, h = img.size
        rec = self.records[i]
        rec.left, rec.top = left, top
        rec.right, rec.bottom = left + w, top + h

        r, g, b, a = img.split()
        planes = [(ChannelID.TRANSPARENCY_MASK, a), (ChannelID.CHANNEL_0, r),
                  (ChannelID.CHANNEL_1, g), (ChannelID.CHANNEL_2, b)]
        data, info = [], []
        for cid, band in planes:
            raw = band.tobytes()
            data.append(ChannelData(Compression.RAW, raw))
            info.append(ChannelInfo(id=cid, length=len(raw) + 2))
        rec.channel_info = info
        self.channels[i] = ChannelDataList(data)

    def set_visible(self, name: str, visible: bool) -> None:
        i = self.index_of(name)
        f = self.records[i].flags
        f.visible = visible

    def solo(self, keep: str, always=("고정",)) -> None:
        """회차 그룹 중 하나만 켜고 나머지는 끈다."""
        for i in range(len(self.records)):
            if self._divider(i) not in (1, 2):
                continue
            nm = self.name_of(i)
            if nm.startswith("#"):
                self.records[i].flags.visible = (nm == keep)
            elif nm in always:
                self.records[i].flags.visible = True

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.psd.save(str(p))
        return p

    # ── 확인용 ─────────────────────────────────────────────────
    def tree(self, limit: int = 200) -> str:
        out, depth = [], 0
        for i in range(len(self.records) - 1, -1, -1):
            k = self._divider(i)
            nm = self.name_of(i)
            if k in (1, 2):
                depth += 1
                out.append("  " * (depth - 1) + f"{'●' if self.records[i].flags.visible else '○'} [group ] {nm}")
            elif k == 3:
                depth = max(0, depth - 1)
            else:
                out.append("  " * depth + f"{'●' if self.records[i].flags.visible else '○'} {nm}")
            if len(out) >= limit:
                break
        return "\n".join(out)
