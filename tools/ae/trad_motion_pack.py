# -*- coding: utf-8 -*-
"""
신규안 v2 전통 — 애니메이션이 계획돼 있던 소스만 골라 AE 모션 꾸러미의 재료를 만든다.

  python tools/ae/trad_motion_pack.py [--src C:/aelab/pack/trad_ae/footage] [--dst C:/aelab/pack/trad_motion]

입력은 tools/style/trad.py --split 이 쓴 manifest.json (레이어마다 'anim' 메타가 붙어 있다).
계획된 모션은 셋뿐이다 (신규안_v2_전통/결과.md '남은 것'):
  stamp   낙관 '쾅' 찍힘    — 낙관 PNG 전부 (원형 낙관 一二三 · 두인 포함)
  drawon  붓 원 드로우온    — 붓 원 PNG
  scroll  족자 펼침         — 족자 자막 (글자·축은 AE 네이티브, 종이만 PNG)
같은 PNG 가 여러 컴포지션에 있으면(총집합·틀의 채널 낙관·족자) 하나만 만든다.

출력:  <dst>/footage/<컴포>/<파일>.png · <dst>/footage/jokja_paper.png · <dst>/footage/motion.json · motion.jsx
"""
import argparse, io, json, os, shutil

SUB = {'전통_총집합': 'sources', '전통_틀': 'frame', '전통_로고': 'logo', '전통_아웃트로': 'outro'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='C:/aelab/pack/trad_ae/footage')
    ap.add_argument('--dst', default='C:/aelab/pack/trad_motion')
    a = ap.parse_args()
    man = json.load(io.open(os.path.join(a.src, 'manifest.json'), encoding='utf-8'))
    foot = os.path.join(a.dst, 'footage')
    if os.path.isdir(foot):
        shutil.rmtree(foot)
    os.makedirs(foot)
    items, seen, skipped = [], set(), []
    for c in man['comps']:
        sub = SUB[c['comp']]
        for L in c['layers']:
            an = L.get('anim')
            if not an:
                continue
            if an['type'] == 'scroll':
                key = ('scroll', an['text'], an['size'], an['y'])
            else:
                # 이름+자리로 가린다 — 낙관은 인주 노이즈가 그릴 때마다 달라 파일 해시로는 같은 요소를 못 알아본다
                key = (an['title'], L['x'], L['y'], L['w'], L['h'])
            if key in seen:
                skipped.append('%s/%s' % (sub, L['file']))
                continue
            seen.add(key)
            it = dict(an)
            it.update({'kind': an['type'], 'x': L['x'], 'y0': L['y'], 'w': L['w'], 'h': L['h']})
            if an['type'] != 'scroll':
                os.makedirs(os.path.join(foot, sub), exist_ok=True)
                shutil.copy2(os.path.join(a.src, sub, L['file']), os.path.join(foot, sub, L['file']))
                it['file'] = sub + '/' + L['file']
            items.append(it)
    shutil.copy2(os.path.join(a.src, 'jokja_paper.png'), os.path.join(foot, 'jokja_paper.png'))
    titles = [i['title'] for i in items]
    assert len(titles) == len(set(titles)), '템플릿 이름이 겹친다: %s' % titles
    out = {'fps': 30, 'dur': 5, 'items': items}
    io.open(os.path.join(foot, 'motion.json'), 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    io.open(os.path.join(foot, 'motion.jsx'), 'w', encoding='ascii').write('var MOTION = ' + json.dumps(out, ensure_ascii=True) + ';\n')
    kinds = {}
    for i in items:
        kinds[i['kind']] = kinds.get(i['kind'], 0) + 1
    print('모션 소스', len(items), kinds, '| 중복이라 뺀 것', skipped)


if __name__ == '__main__':
    main()
