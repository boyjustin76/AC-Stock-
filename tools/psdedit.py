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
from psd_tools.compression import compress
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

    def drop_group(self, name: str) -> int:
        """그룹 하나를 레코드에서 통째로 들어낸다.

        템플릿에는 회차 그룹이 10개 들어 있어 파일이 180MB 다.  쓰지 않는 회차를
        빼면 20MB 안팎으로 줄어들고, 남긴 회차 그룹의 내부 구성은 그대로다.
        """
        lo, hi = self.group_span(name)
        n = hi - lo + 1
        del self.records[lo:hi + 1]
        del self.channels[lo:hi + 1]
        self.li.layer_count = len(self.records)
        return n

    def episode_groups(self, depth_wanted: int = 1) -> list[str]:
        """아트보드 바로 밑에 있는 회차 그룹(# 로 시작)만 고른다.

        #10 안에 #10-a · #10-b 처럼 같은 표기의 하위 그룹이 있어서 깊이를 센다.
        레코드는 아래→위 순이라 끝에서부터 훑으면 깊이가 맞아떨어진다.
        """
        out, depth = [], 0
        for i in range(len(self.records) - 1, -1, -1):
            k = self._divider(i)
            if k in (1, 2):
                nm = self.name_of(i)
                if depth == depth_wanted and nm.startswith("#"):
                    out.append(nm)
                depth += 1
            elif k == 3:
                depth -= 1
        return out

    def find_in(self, group: str, layer: str) -> int:
        lo, hi = self.group_span(group)
        for i in range(lo, hi + 1):
            if self.name_of(i) == layer:
                return i
        raise KeyError(f"'{group}' 안에 '{layer}' 가 없습니다")

    def set_text(self, group: str, layer: str, text: str) -> None:
        """라이브 텍스트의 글자를 바꾼다.

        EngineData 에는 글자마다 어떤 스타일이 걸렸는지가 구간(run)으로 들어 있다.
        구간은 두 배열이 짝을 이룬다 — 스타일 자체인 ``RunArray`` 와 각 구간의
        글자 수인 ``RunLengthArray``.  글자 수가 바뀌면 둘을 **함께** 손봐야 한다.
        길이 배열만 줄이고 스타일 배열을 그대로 두면 짝이 어긋나서 포토샵이
        "프로그램 오류로 인하여 열 수 없습니다" 를 낸다 — 실제로 한 번 겪었다.

        구간은 첫 번째 하나만 남긴다.  원본 타이틀은 한 줄에 색이 두세 구간으로
        나뉜 것이 있는데, 우리 타이틀은 줄 전체가 한 색이라 첫 스타일로 통일한다.
        """
        i = self.find_in(group, layer)
        td = self.records[i].tagged_blocks.get_data(Tag.TYPE_TOOL_OBJECT_SETTING).text_data
        body = text + "\r"          # 포토샵은 문단 끝을 \r 로 센다
        td[b"Txt "].value = text + "\x00"
        doc = td[b"EngineData"].value["EngineDict"]
        doc["Editor"]["Text"].value = body
        for run in ("StyleRun", "ParagraphRun"):
            for key in ("RunArray", "RunLengthArray"):
                arr = doc[run][key]
                for k in range(len(arr) - 1, 0, -1):
                    del arr[k]
            doc[run]["RunLengthArray"][0].value = len(body)
        self._rename(self.records[i], text)

    def check(self) -> list[str]:
        """저장하기 전에 포토샵이 걸고 넘어질 만한 것을 훑는다.

        열리지 않는 .psd 를 넘기는 것이 가장 비싼 실수라, 알고 있는 조건은
        전부 여기서 잡는다.
        """
        bad = []
        seen_id = {}
        depth = 0
        for i in range(len(self.records) - 1, -1, -1):
            k = self._divider(i)
            if k in (1, 2):
                depth += 1
            elif k == 3:
                depth -= 1
                if depth < 0:
                    bad.append(f"L{i} 그룹 끝표시가 짝이 없다")
                    depth = 0
            b = self.records[i].tagged_blocks
            if not b:
                continue
            lid = b.get_data(Tag.LAYER_ID) if b.get(Tag.LAYER_ID) is not None else None
            if lid is not None:
                lid = int(lid)
                if lid in seen_id:
                    bad.append(f"L{i} 와 L{seen_id[lid]} 의 lyid 가 {lid} 로 겹친다")
                seen_id[lid] = i
            t = b.get_data(Tag.TYPE_TOOL_OBJECT_SETTING)
            if t is None:
                continue
            ed = t.text_data[b"EngineData"].value["EngineDict"]
            body = ed["Editor"]["Text"].value
            for run in ("StyleRun", "ParagraphRun"):
                ra, la = ed[run]["RunArray"], ed[run]["RunLengthArray"]
                if len(ra) != len(la):
                    bad.append(f"L{i} {run} 스타일 {len(ra)}개 · 길이 {len(la)}개 — 짝이 안 맞는다")
                if sum(int(x.value) for x in la) != len(body):
                    bad.append(f"L{i} {run} 길이 합 {sum(int(x.value) for x in la)} ≠ 글자 수 {len(body)}")
        if depth != 0:
            bad.append(f"그룹 여닫이가 {depth} 만큼 안 맞는다")
        if len(self.records) != self.li.layer_count:
            bad.append(f"레이어 수 {len(self.records)} ≠ 기록된 {self.li.layer_count}")
        if len(self.channels) != len(self.records):
            bad.append(f"채널 묶음 {len(self.channels)} ≠ 레이어 {len(self.records)}")
        return bad

    # ── 라이브 텍스트 + 래스터 ─────────────────────────────────
    def bake_text(self, group: str, layer: str, text: str, font: str | Path,
                  target_width: int = 0, color: tuple[int, int, int] = (255, 255, 0)) -> dict:
        """글자를 바꾸고, 그 글자를 레이어 픽셀에도 구워 넣는다.

        ``set_text`` 만 하면 파일 안 글자는 새것인데 **레이어에 저장된 픽셀은
        템플릿의 옛 글자 그대로**다.  포토샵은 열 때 그 픽셀을 그대로 보여 주기
        때문에, 클릭해서 텍스트를 건드리기 전까지는 옛 문구가 보인다.
        그래서 여기서 새 글자를 직접 그려 넣는다.

        획·그림자는 그리지 않는다.  레이어에 lfx2(획 6px + 그림자)가 살아 있어서
        포토샵이 알아서 얹는다.  여기서 또 그리면 두 겹이 된다.

        글자 크기는 ``target_width`` 에 맞춰 되돌려 계산하고 EngineData 에도 같은
        값을 넣는다.  그래야 나중에 포토샵이 다시 그려도 지금 픽셀과 겹친다.
        """
        self.set_text(group, layer, text)   # 이 시점에 레이어 이름도 text 로 바뀐다
        i = self.find_in(group, text)
        blk = self.records[i].tagged_blocks.get_data(Tag.TYPE_TOOL_OBJECT_SETTING)
        ed = blk.text_data[b"EngineData"].value
        sheet = ed["EngineDict"]["StyleRun"]["RunArray"][0]["StyleSheet"]["StyleSheetData"]

        # 텍스트 레이어는 [배율 0 0 배율 x y] 변환을 들고 있다.
        # 화면에 보이는 크기 = EngineData 의 FontSize x 배율.
        a, _, _, d, tx, ty = blk.transform
        scale = (abs(a) + abs(d)) / 2
        tracking = float(sheet["Tracking"].value) / 1000.0

        px = (target_width and self._fit(text, font, tracking, target_width)) or \
             round(float(sheet["FontSize"].value) * scale)
        sheet["FontSize"].value = px / scale

        img, left_pad, ascent = self._render(text, font, px, tracking, color)
        # Justification 2 = 가운데. 변환의 x 가 글자 가운데, y 가 기준선이다.
        left = round(tx - img.width / 2)
        top = round(ty - ascent)
        self.replace_pixels(group, text, img, left, top)
        return {"px": px, "width": img.width, "left": left, "top": top}

    @staticmethod
    def _measure(text: str, fnt, tracking: float) -> int:
        from PIL import ImageDraw
        d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        gap = round(fnt.size * tracking)
        return round(sum(d.textlength(c, font=fnt) for c in text) + gap * (len(text) - 1))

    @classmethod
    def _fit(cls, text: str, font: str | Path, tracking: float, want: int) -> int:
        from PIL import ImageFont
        lo, hi = 20, 500
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if cls._measure(text, ImageFont.truetype(str(font), mid), tracking) <= want:
                lo = mid
            else:
                hi = mid - 1
        return lo

    @classmethod
    def _render(cls, text: str, font: str | Path, px: int, tracking: float,
                color: tuple[int, int, int]):
        from PIL import ImageDraw, ImageFont
        fnt = ImageFont.truetype(str(font), px)
        ascent, descent = fnt.getmetrics()
        w = cls._measure(text, fnt, tracking)
        pad = round(px * 0.25)                     # 획이 잘리지 않게 여유
        img = Image.new("RGBA", (w + pad * 2, ascent + descent + pad * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        gap = round(px * tracking)
        x = pad
        for ch in text:
            d.text((x, pad), ch, font=fnt, fill=(*color, 255))
            x += d.textlength(ch, font=fnt) + gap
        return img, pad, ascent + pad

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
            # 무압축으로 넣으면 1920x1080 한 장이 8MB 라 파일이 금세 커진다.
            packed = compress(band.tobytes(), Compression.RLE, w, h, 8)
            data.append(ChannelData(Compression.RLE, packed))
            info.append(ChannelInfo(id=cid, length=len(packed) + 2))
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

    def save(self, path: str | Path, force: bool = False) -> Path:
        bad = self.check()
        if bad and not force:
            raise ValueError("저장 안 함 — 포토샵이 못 열 파일이다:\n  " + "\n  ".join(bad))
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
