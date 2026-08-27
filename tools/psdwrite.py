#!/usr/bin/env python3
"""레이어가 살아 있는 .psd 를 직접 쓴다.

파이썬에서 PSD 를 쓰는 라이브러리(pytoshop)가 이 환경에서 빌드에 실패해서,
포토샵 파일 규격대로 직접 만들었다.  RGB · 8비트 · 레이어별 알파까지 들어간다.

    from tools.psdwrite import Layer, write_psd
    write_psd("out.psd", 1920, 1080, [Layer("차트", img, 0, 0), ...])

레이어는 아래에서 위 순서로 넣는다 (배경이 먼저).
채널은 PackBits(RLE)로 압축한다 — 흰 배경이 많은 썸네일에서 크기가 크게 준다.

한계: 텍스트는 래스터로 들어간다.  포토샵 텍스트 엔진 데이터를 새로 짜지 않으므로
파일을 열어 글자를 다시 타이핑할 수는 없다.  글자를 고치려면 템플릿의 텍스트
레이어를 복사해 오는 편이 빠르다.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class Layer:
    name: str
    image: Image.Image          # RGBA
    left: int = 0
    top: int = 0
    opacity: int = 255
    visible: bool = True


def _packbits(data: bytes) -> bytes:
    """PSD 가 쓰는 PackBits RLE. 한 스캔라인씩 부른다."""
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        # 같은 바이트가 3개 이상 이어지면 런으로 묶는다
        run = 1
        while i + run < n and data[i + run] == data[i] and run < 128:
            run += 1
        if run >= 3:
            out.append(257 - run)
            out.append(data[i])
            i += run
            continue
        # 아니면 리터럴로 모은다
        start = i
        i += 1
        while i < n and (i - start) < 128:
            if i + 2 < n and data[i] == data[i + 1] == data[i + 2]:
                break
            i += 1
        lit = data[start:i]
        out.append(len(lit) - 1)
        out += lit
    return bytes(out)


def _channel_rle(plane: bytes, w: int, h: int) -> tuple[bytes, bytes]:
    """스캔라인별 PackBits. (행별 길이표, 압축 데이터) 를 돌려준다."""
    counts, body = bytearray(), bytearray()
    for y in range(h):
        packed = _packbits(plane[y * w:(y + 1) * w])
        counts += struct.pack(">H", len(packed))
        body += packed
    return bytes(counts), bytes(body)


def _pascal4(s: str) -> bytes:
    """길이 1바이트 + 내용, 전체를 4의 배수로 패딩."""
    b = s.encode("cp949", errors="replace")[:255]
    raw = bytes([len(b)]) + b
    return raw + b"\0" * (-len(raw) % 4)


def _luni(name: str) -> bytes:
    """유니코드 레이어 이름. 한글 이름이 포토샵에서 제대로 보이게."""
    u = name.encode("utf-16-be")
    body = struct.pack(">I", len(name)) + u + b"\0\0"
    body += b"\0" * (-len(body) % 2)
    return b"8BIM" + b"luni" + struct.pack(">I", len(body)) + body


def write_psd(path: str | Path, width: int, height: int,
              layers: list[Layer], background: tuple[int, int, int] = (255, 255, 255)) -> Path:
    canvas = Image.new("RGBA", (width, height), (*background, 255))
    for L in layers:
        if L.visible:
            canvas.alpha_composite(L.image.convert("RGBA"), (L.left, L.top))
    merged = canvas.convert("RGB")

    # ── 레이어 레코드 ──────────────────────────────────────────
    records, chandata = bytearray(), bytearray()
    for L in layers:
        img = L.image.convert("RGBA")
        w, h = img.size
        top, left = L.top, L.left
        bottom, right = top + h, left + w
        records += struct.pack(">iiii", top, left, bottom, right)
        records += struct.pack(">H", 4)                      # 채널 4개 (A,R,G,B)

        planes, blobs = [], []
        r, g, b, a = img.split()
        for cid, band in ((-1, a), (0, r), (1, g), (2, b)):
            counts, body = _channel_rle(band.tobytes(), w, h)
            blob = struct.pack(">H", 1) + counts + body      # 1 = RLE
            planes.append(cid)
            blobs.append(blob)
            records += struct.pack(">hI", cid, len(blob))
        chandata += b"".join(blobs)

        flags = 0 if L.visible else 2                        # bit1 = 숨김
        records += b"8BIM" + b"norm" + bytes([L.opacity, 0, flags, 0])

        extra = struct.pack(">I", 0)                         # 마스크 없음
        extra += struct.pack(">I", 0)                        # 블렌딩 범위 없음
        extra += _pascal4(L.name)
        extra += _luni(L.name)
        records += struct.pack(">I", len(extra)) + extra

    layer_info = struct.pack(">h", len(layers)) + bytes(records) + bytes(chandata)
    if len(layer_info) % 2:
        layer_info += b"\0"
    layer_and_mask = struct.pack(">I", len(layer_info)) + layer_info + struct.pack(">I", 0)

    # ── 합쳐진 이미지 ──────────────────────────────────────────
    mcounts, mbody = bytearray(), bytearray()
    for band in merged.split():
        c, d = _channel_rle(band.tobytes(), width, height)
        mcounts += c
        mbody += d
    image_data = struct.pack(">H", 1) + bytes(mcounts) + bytes(mbody)

    out = bytearray()
    out += b"8BPS" + struct.pack(">H", 1) + b"\0" * 6
    out += struct.pack(">HIIHH", 3, height, width, 8, 3)     # 채널3 · 8비트 · RGB
    out += struct.pack(">I", 0)                              # 컬러 모드 데이터 없음
    out += struct.pack(">I", 0)                              # 이미지 리소스 없음
    out += struct.pack(">I", len(layer_and_mask)) + layer_and_mask
    out += image_data

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(bytes(out))
    return p
