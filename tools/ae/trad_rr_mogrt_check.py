# -*- coding: utf-8 -*-
"""
손익비 (전통) mogrt 13개를 zip 안 definition.json 으로 검사하고, 실패한 이름을 <out>/_only.txt 에 쓴다.

  python tools/ae/trad_rr_mogrt_check.py [--out C:/aelab/trad_rr_mogrt_out]

AE 의 exportAsMotionGraphicsTemplate 는 반환값이 true 여도 가끔 한 개씩 푸티지 누락이 적힌 mogrt 를 낸다
(2026-09-14 실측: 손절 박스 누락 2 → 다음 실행엔 전체 누락 12, 다시 내보내면 0). 반환값 대신 이 검사로 판정한다.
c5x_trad_rr_export.jsx 가 _only.txt 에 적힌 이름만 다시 내보낸다. 종료 코드 0 = 13개 전부 통과.
"""
import argparse, glob, io, json, os, sys, zipfile

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='C:/aelab/trad_rr_mogrt_out')
    ap.add_argument('--rr', default='C:/aelab/pack/trad_rr/footage/rr.json')
    a = ap.parse_args()
    rr = json.load(io.open(a.rr, encoding='utf-8'))
    WANT = [rr['name']] + [i['name'] for i in rr['items']]      # 전체 + 소스 (이름은 trad_rr.py 가 정한다)
    # 예전 이름의 mogrt 가 밖 폴더에 남아 있으면 헷갈린다 — 알려만 준다
    extra = sorted(set(os.path.basename(f)[:-6] for f in glob.glob(a.out + '/*.mogrt')) - set(WANT))
    if extra:
        print('목록에 없는 mogrt (무시):', extra)
    files = {os.path.basename(f)[:-6]: f for f in glob.glob(a.out + '/*.mogrt')}
    bad = []
    for name in WANT:
        path = files.get(name)
        if not path:
            bad.append(name)
            print('%-24s 파일 없음' % name)
            continue
        try:
            z = zipfile.ZipFile(path)
            d = json.loads(z.read('definition.json').decode('utf-8'))
            miss = d['sourceInfoLocalized']['ko_KR'].get('missingassets', {})
            n_miss = sum(len(v) for v in miss.values() if isinstance(v, list))
            good = z.testzip() is None and n_miss == 0 and z.getinfo('thumb.mp4').file_size > 0
        except Exception as e:
            good, n_miss = False, 'ERR %s' % e
        if not good:
            bad.append(name)
            print('%-24s 누락=%s ← 다시' % (name, n_miss))
    io.open(os.path.join(a.out, '_only.txt'), 'w', encoding='utf-8').write('\n'.join(bad) + '\n')
    print('통과 %d / %d · 다시 %d' % (len(WANT) - len(bad), len(WANT), len(bad)))
    sys.exit(0 if not bad else 1)


if __name__ == '__main__':
    main()
