#!/usr/bin/env python3
# 최종본 실측: scene.txt(전 프레임 장면점수) + freeze.txt(차트영역 정지) → 컷/디졸브/정지 통계
import sys, re, json

def parse_scene(path):
    rows = []  # (pts_time, score)
    t = None
    for line in open(path, encoding='utf8', errors='replace'):
        m = re.search(r'pts_time:([\d.]+)', line)
        if m: t = float(m.group(1)); continue
        m = re.search(r'scene_score=([\d.]+)', line)
        if m and t is not None: rows.append((t, float(m.group(1)))); t = None
    return rows

def parse_freeze(path):
    starts, ends = [], []
    for line in open(path, encoding='utf8', errors='replace'):
        m = re.search(r'freeze_start: ([\d.]+)', line)
        if m: starts.append(float(m.group(1)))
        m = re.search(r'freeze_end: ([\d.]+)', line)
        if m: ends.append(float(m.group(1)))
    segs = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else None
        segs.append((s, e))
    return segs

def analyze(name, hard=0.35, soft_lo=0.015, soft_hi=0.30):
    sc = parse_scene(f'{name}_scene.txt')
    dur = sc[-1][0] if sc else 0
    # 하드 컷
    cuts = [t for t, s in sc if s >= hard]
    # 디졸브 후보: 중간 점수가 연속으로 이어지는 구간 (하드컷 프레임 제외)
    runs = []
    run = None
    for t, s in sc:
        if soft_lo <= s < hard:
            if run is None: run = [t, t, 0]
            run[1] = t; run[2] += 1
        else:
            if run and run[2] >= 6: runs.append(tuple(run))
            run = None
    if run and run[2] >= 6: runs.append(tuple(run))
    # 컷 길이 분포 (하드컷+긴 디졸브 중심을 경계로)
    bounds = sorted(set([0.0] + cuts + [ (a+b)/2 for a,b,n in runs ] + [dur]))
    # 0.5초 이내 중복 경계 병합
    merged = [bounds[0]]
    for b in bounds[1:]:
        if b - merged[-1] > 0.5: merged.append(b)
    lens = [round(merged[i+1]-merged[i],2) for i in range(len(merged)-1)]
    fz = parse_freeze(f'{name}_freeze.txt')
    fz_total = sum((e if e else dur) - s for s, e in fz)
    print(f'== {name}  길이 {dur:.1f}s  프레임 {len(sc)}')
    print(f'하드컷(score>={hard}): {len(cuts)}개')
    print(f'디졸브 후보(중간점수 {soft_lo}~{hard} 가 6프레임+ 연속): {len(runs)}개, 길이 중앙값 {sorted([round(b-a,2) for a,b,n in runs])[len(runs)//2] if runs else 0}s')
    print(f'경계(병합) {len(merged)-1}구간, 구간 길이: 중앙값 {sorted(lens)[len(lens)//2]}s  min {min(lens)}  max {max(lens)}')
    print(f'차트영역(800x560@1050,260) 정지: {len(fz)}구간, 합계 {fz_total:.1f}s = 영상의 {100*fz_total/dur:.1f}%')
    longest = sorted(fz, key=lambda x: ((x[1] or dur)-x[0]), reverse=True)[:5]
    print('  최장 정지 5개:', [(round(s,1), round((e or dur)-s,1)) for s,e in longest])
    json.dump({'cuts':cuts,'dissolves':runs,'bounds':merged,'freeze':fz,'dur':dur},
              open(f'{name}_analysis.json','w'))

for n in sys.argv[1:]:
    analyze(n)
