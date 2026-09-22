"""batch_capture 결과 → 콘티 한 장(PNG) + AE 잡 입력(conti_in.json)  (next_step 45 ②)

    python tools/mt5/conti_sheet.py <콘티폴더> [--title 차10] [--cps 6.82]

  <콘티폴더>/콘티.png          비트마다 차트 · 번호 · 장면 · 종목주기 · 대본 첫머리 · 고른 이유
  <AE작업실>/conti_in.json     tools/ae/jobs/d1_conti_build.jsx 가 읽는다 (그림 경로·길이·글)

비트 길이: 대본에 타임코드가 없어 **글자 수 ÷ 초당 글자수** 로 추정한다. 기본 6.82 는 숏폼 자막 13편 실측
(shortform_srt). 롱폼 성우 속도는 안 재 봤다 — 추정이라고 json 에 적는다. 3초 아래로는 안 내린다.
"""
import argparse
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
_FONTS = os.path.join(os.environ.get('WINDIR', ''), 'Fonts')    # 경로를 박지 않는다 (tests/test_no_path_literals.py)
FONT = os.path.join(_FONTS, 'malgun.ttf')
FONT_B = os.path.join(_FONTS, 'malgunbd.ttf')


def ae_lab():
    """AE 작업실 — _labdir 와 같은 규칙: 환경변수 AELAB_DIR, 없으면 저장소 위로 올라가며 02_AE작업실_aelab."""
    env = os.environ.get('AELAB_DIR')
    if env:
        return env
    d = HERE
    for _ in range(8):
        d = os.path.dirname(d)
        cand = os.path.join(d, '02_AE작업실_aelab')
        if os.path.isdir(cand):
            return cand
    raise SystemExit('02_AE작업실_aelab 을 못 찾았다 — AELAB_DIR 을 주라')


def wrap(draw, text, font, width):
    lines, cur = [], ''
    for ch in text:
        if draw.textlength(cur + ch, font=font) > width:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def sheet(conti, folder, title, out):
    cols, tw = 3, 600
    th = int(tw * 915 / 1920)
    cell_h = th + 190
    rows = (len(conti) + cols - 1) // cols
    W, H = cols * tw + (cols + 1) * 24, 110 + rows * (cell_h + 24)
    im = Image.new('RGB', (W, H), (246, 246, 244))
    d = ImageDraw.Draw(im)
    f_t, f_b, f_s = ImageFont.truetype(FONT_B, 40), ImageFont.truetype(FONT_B, 24), ImageFont.truetype(FONT, 19)
    d.text((24, 30), f'{title} 차트 장면 콘티 · {len(conti)}비트', font=f_t, fill=(20, 20, 20))
    for k, c in enumerate(conti):
        x = 24 + (k % cols) * (tw + 24)
        y = 110 + (k // cols) * (cell_h + 24)
        d.rectangle((x, y, x + tw, y + cell_h), fill=(255, 255, 255), outline=(210, 210, 210))
        if c.get('png') and os.path.exists(os.path.join(folder, c['png'])):
            th_im = Image.open(os.path.join(folder, c['png'])).convert('RGB').resize((tw, th))
            im.paste(th_im, (x, y))
        else:
            d.text((x + 20, y + th // 2), '그림 없음', font=f_b, fill=(180, 0, 0))
        ty = y + th + 10
        head = f"({c['id']}) {c.get('pattern', '')}"
        sub = f"{c.get('symbol', '')} {c.get('period', '')} · {','.join(c.get('indicators') or []) or '지표 없음'} · {c.get('sec', 0):.1f}초"
        d.text((x + 12, ty), head, font=f_b, fill=(20, 20, 20))
        d.text((x + 12, ty + 32), sub, font=f_s, fill=(90, 90, 90))
        for i, ln in enumerate(wrap(d, c.get('text', ''), f_s, tw - 24)[:3]):
            d.text((x + 12, ty + 62 + i * 25), ln, font=f_s, fill=(40, 40, 40))
        why = f"왜: {c.get('why', '')} [{c.get('by', '')}]"
        d.text((x + 12, ty + 142), wrap(d, why, f_s, tw - 24)[0], font=f_s, fill=(0, 110, 100))
        if c.get('warn'):
            d.text((x + 12, ty + 165), '⚠ ' + c['warn'][:40], font=f_s, fill=(200, 0, 0))
    im.save(out)
    return im.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--title', default='차10')
    ap.add_argument('--cps', type=float, default=6.82)
    a = ap.parse_args()
    folder = os.path.abspath(a.folder)
    conti = json.load(io.open(os.path.join(folder, '콘티.json'), encoding='utf-8'))
    for c in conti:
        c['sec'] = max(3.0, round(len(c.get('text', '').replace(' ', '')) / a.cps, 1))
    size = sheet(conti, folder, a.title, os.path.join(folder, '콘티.png'))
    print(f'콘티.png {size[0]}x{size[1]}')

    lab = ae_lab()
    ae_in = {
        'title': a.title,
        'aep': (os.path.join(lab, 'conti', f'{a.title}_차트장면.aep')).replace('\\', '/'),
        'fps': 59.94, 'w': 1920, 'h': 1080,
        '길이_근거': f'대본 글자 수 ÷ {a.cps}자/초 (숏폼 자막 실측) — 롱폼 성우 속도는 미측정, 추정값',
        'beats': [{'id': c['id'], 'png': os.path.join(folder, c['png']).replace('\\', '/') if c.get('png') else '',
                   'sec': c['sec'], 'text': c.get('text', ''),
                   'why': f"{c.get('pattern', '')} · {c.get('symbol', '')} {c.get('period', '')} · {c.get('why', '')} [{c.get('by', '')}]"}
                  for c in conti],
    }
    os.makedirs(os.path.join(lab, 'conti'), exist_ok=True)
    p = os.path.join(lab, 'conti_in.json')
    with io.open(p, 'w', encoding='utf-8') as f:            # BOM 없이 — jsx 는 BOM 을 안 뗀다
        json.dump(ae_in, f, ensure_ascii=False, indent=1)
    print(f'AE 입력 {len(conti)}비트 · 합계 {sum(c["sec"] for c in conti):.1f}초 → conti_in.json')


if __name__ == '__main__':
    sys.exit(main())
