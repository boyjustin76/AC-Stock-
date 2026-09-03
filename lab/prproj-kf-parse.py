#!/usr/bin/env python3
# 차트명가 prproj 실측 파서
import gzip, re, os, sys, json, statistics, collections

TICKS_PER_SEC = 254016000000
TICKS_PER_FRAME = 254016000000 * 1001 // 30000  # 8475667200 @29.97

EPS = ['ep01','ep02','ep03','ep04','ep05','ep06','ep07','ep08','ep09','ep10','ep14']

def frames(ticks): return ticks / TICKS_PER_FRAME

def classify(name):
    if name == '위치': return 'position'
    if name in ('비율 조정',): return 'scale'
    if name in ('높이 비율 조정','폭 비율 조정'): return 'scale_hw'
    if name == '불투명도': return 'opacity'
    if name in ('왼쪽','오른쪽','위','아래','위쪽','아래쪽'): return 'crop'
    if name == '회전': return 'rotation'
    if name == '기준점': return 'anchor'
    return 'other:'+ (name or '?')

def parse_ep(ep):
    path = ep + '.prproj'
    x = gzip.open(path,'rt',encoding='utf-8',errors='replace').read()
    out = {'ep': ep}

    # 1. assets
    paths = re.findall(r'<ActualMediaFilePath>([^<]+)</ActualMediaFilePath>', x)
    basenames = sorted(set(os.path.basename(p.replace('\\','/')) for p in paths))
    exts = collections.Counter(os.path.splitext(b)[1].lower() for b in basenames)
    shots = [b for b in basenames if '스크린샷' in b or '\uc2a4\ud06c\ub9b0\uc0f7' in b]
    out['n_assets'] = len(basenames)
    out['exts'] = dict(exts.most_common())
    out['screenshots'] = shots

    # 2. transitions
    trans = []
    for m in re.finditer(r'<TransitionTrackItem[^>]*>.*?</TransitionTrackItem>', x, re.S):
        blk = m.group(0)
        s = re.search(r'<Start>(\d+)</Start>', blk)
        e = re.search(r'<End>(\d+)</End>', blk)
        mn = re.search(r'<MatchName>([^<]+)</MatchName>', blk)
        if s and e and mn:
            trans.append((mn.group(1), int(e.group(1))-int(s.group(1))))
    tnames = collections.Counter(t[0] for t in trans)
    out['transitions'] = dict(tnames.most_common())
    diss = [round(frames(d)) for n,d in trans if 'Dissolve' in n or 'dissolve' in n]
    out['dissolve_frames'] = sorted(collections.Counter(diss).items())
    out['dissolve_median'] = statistics.median(diss) if diss else None

    # 3-4. keyframed params
    kf_counts = collections.Counter()   # kind -> total keyframe count
    kf_params = collections.Counter()   # kind -> keyframed param count
    appear = collections.Counter()      # (kind, dur_frames) for 2-kf 0.1~0.7s
    pos_samples = []
    scale_list = []
    for m in re.finditer(r'<(VideoComponentParam|PointComponentParam|ArbVideoComponentParam)\b[^>]*>(.*?)</\1>', x, re.S):
        blk = m.group(2)
        if '<IsTimeVarying>true</IsTimeVarying>' not in blk: continue
        km = re.search(r'<Keyframes>([^<]*)</Keyframes>', blk)
        if not km or not km.group(1).strip(): continue
        nm = re.search(r'<Name>([^<]*)</Name>', blk)
        name = nm.group(1) if nm else ''
        kind = classify(name)
        entries = [e for e in km.group(1).strip().split(';') if e]
        kfs = []
        for e in entries:
            parts = e.split(',')
            try: t = int(parts[0])
            except: continue
            kfs.append((t, parts[1] if len(parts)>1 else ''))
        if len(kfs) < 2: continue
        kf_counts[kind] += len(kfs)
        kf_params[kind] += 1
        dur_t = kfs[-1][0]-kfs[0][0]
        dur_f = frames(dur_t)
        if len(kfs)==2 and 0.1 <= dur_t/TICKS_PER_SEC <= 0.7:
            appear[(kind, round(dur_f))] += 1
        if kind=='position' and len(kfs)==2 and 0.1 <= dur_t/TICKS_PER_SEC <= 0.7 and len(pos_samples)<6:
            def px(v):
                try:
                    a,b = v.split(':')[:2]
                    return (round(float(a)*1920), round(float(b)*1080))
                except: return v
            pos_samples.append((px(kfs[0][1]), px(kfs[1][1]), round(dur_f)))
        if kind=='scale':
            try:
                f0=float(kfs[0][1]); f1=float(kfs[-1][1])
                scale_list.append((round(f0,1), round(f1,1), round(dur_f), len(kfs)))
            except: pass
    out['kf_params'] = dict(kf_params)
    out['kf_counts'] = dict(kf_counts)
    out['appear'] = {f'{k}@{d}f': c for (k,d),c in sorted(appear.items())}
    out['pos_samples'] = pos_samples
    out['scale_list'] = scale_list
    return out

res = []
for ep in EPS:
    try:
        r = parse_ep(ep)
        res.append(r)
        sys.stderr.write(ep+' ok\n')
    except Exception as ex:
        res.append({'ep':ep,'error':str(ex)})
        sys.stderr.write(ep+' FAIL '+str(ex)+'\n')
print(json.dumps(res, ensure_ascii=False, indent=1))
