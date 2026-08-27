#!/usr/bin/env python3
"""
worklog.db 를 읽어 브라우저에서 바로 보는 한 장짜리 페이지로 만든다.

  python3 log/build_worklog_page.py   → log/worklog.html

DB 가 원본이다. 내용을 고칠 때는 build_worklog_db.py 를 고치고 두 스크립트를 다시 돌린다.
"""
import html
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "log" / "worklog.db"
OUT = ROOT / "log" / "worklog.html"

e = lambda s: html.escape(str(s)) if s is not None else ""


def build():
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()

    ses = q("SELECT * FROM session")[0]

    # ── 대본 타임라인 (프레임 수 비율이 곧 컷 길이) ────────────────
    cuts = q("SELECT scene_id, name, tc_in, tc_out, frames_2997, frames_5994, seconds, text FROM v_cut_sync")
    total = sum(c[4] for c in cuts)
    bar, rows = [], []
    for i, (sid, name, tin, tout, f30, f60, secs, text) in enumerate(cuts, 1):
        pct = f30 / total * 100
        bar.append(
            f'<div class="seg seg-{i}" style="flex:{f30}">'
            f'<span class="seg-n">{i}</span><span class="seg-f">{f30}f</span>'
            f'<span class="seg-p">{pct:.1f}%</span></div>')
        rows.append(
            f"<tr><td class='num'>{i}</td><td><code>{e(sid)}</code><span class='sub'>{e(name)}</span></td>"
            f"<td class='mono nowrap'>{e(tin)}<br>{e(tout)}</td>"
            f"<td class='mono r'>{f30}</td><td class='mono r'>{f60}</td>"
            f"<td class='mono r'>{secs:.3f}</td><td class='line'>{e(text)}</td></tr>")

    # ── 작업 방식 ─────────────────────────────────────────────
    flow_rows = []
    for seq, step, how, who, st, note in q(
            "SELECT seq,step,how,who,status,note FROM workflow_step ORDER BY seq"):
        label = {"ready": "준비됨", "partial": "일부", "todo": "미구현"}[st]
        sub_note = f"<span class='sub'>{e(note)}</span>" if note else ""
        flow_rows.append(
            f"<tr><td class='num'>{seq}</td><td><b>{e(step)}</b>{sub_note}</td>"
            f"<td>{e(how)}</td><td class='nowrap'>{e(who)}</td>"
            f"<td class='nowrap'><span class='pill p-{st}'>{label}</span></td></tr>")
    flow = "".join(flow_rows)

    bench = "".join(
        f"<tr><td class='nowrap'>{e('순차' if mode=='serial' else '병렬')}</td>"
        f"<td class='mono r'>{cores}</td><td class='mono r'>{frames}</td>"
        f"<td class='mono r'>{sv:.2f}s</td><td class='mono r'><b>{ws:.0f}s</b></td>"
        f"<td class='mono r'>{fc:.1f}</td><td>{e(note)}</td></tr>"
        for mode, cores, frames, sv, ws, fc, note in q(
            "SELECT mode,cores,frames,seconds_video,wall_seconds,fps_capture,note FROM benchmark ORDER BY id"))

    VERDICT = {"adopt": ("fixed", "도입"), "local-only": ("worked-around", "로컬 전용"),
               "rejected": ("open", "보류"), "pending": ("open", "검토중")}
    tool_cards = []
    for n, src, pur, req, v, rea in q(
            "SELECT name,source,purpose,requirement,verdict,reason FROM external_tool ORDER BY id"):
        cls, label = VERDICT[v]
        src_row = f"<dt>출처</dt><dd class='ver'>{e(src)}</dd>" if src else ""
        tool_cards.append(
            f"<article class='issue st-{cls}'><h3>{e(n)}<span class='tag'>{label}</span></h3>"
            f"<dl><dt>용도</dt><dd>{e(pur)}</dd>"
            f"<dt>요구</dt><dd>{e(req or '없음')}</dd>"
            f"<dt>판단</dt><dd>{e(rea)}</dd>{src_row}</dl></article>")
    tools = "".join(tool_cards)

    prproj = "".join(
        f"<tr><td class='nowrap'><b>{e(t)}</b></td><td>{e(f)}</td>"
        f"<td class='sub'>{e(m or '')}</td></tr>"
        for t, f, m in q("SELECT topic,finding,method FROM prproj_fact ORDER BY id"))

    # ── 파이프라인 범위 ───────────────────────────────────────
    MK = {"진행중": "here", "자료만": "partial", "미착수": "todo", "해당없음": "none"}
    stage_rows = []
    for fmt, seq, name, owner, in_repo, st, detail in q(
            "SELECT p.format,p.seq,p.name,p.owner,p.in_repo,p.status,p.detail"
            " FROM pipeline_stage p JOIN format f ON f.name=p.format ORDER BY f.id,p.id"):
        num = seq if "." in seq else f"{seq}."
        here = " st-here" if in_repo and st == "진행중" else ""
        stage_rows.append(
            f"<tr class='stage{here}'><td class='nowrap'>{e(fmt)}</td>"
            f"<td><b>{num} {e(name)}</b><span class='sub'>{e(detail)}</span></td>"
            f"<td class='nowrap'>{e(owner)}</td>"
            f"<td class='nowrap'><span class='pill p-{MK[st]}'>{e(st)}</span></td></tr>")
    pipeline = "".join(stage_rows)

    formats = "".join(
        f"<tr><td class='nowrap'><b>{e(n)}</b></td><td class='mono nowrap'>{e(asp)}</td>"
        f"<td>{e(fin)}</td><td>{e(src or '-')}</td><td class='nowrap'>{e(ln or '')}</td>"
        f"<td>{e(tone or '')}</td></tr>"
        for n, asp, fin, src, ln, tone in q(
            "SELECT name,aspect,final_spec,source_spec,length,tone FROM format ORDER BY id"))

    # ── 숏폼 대본 규칙 ────────────────────────────────────────
    TIER = {"필수": "here", "권장": "", "선택": "partial", "수치": "todo"}
    sf_rules = []
    for grp, rule, ev, hits, tot, tier in q(
            "SELECT grp,rule,evidence,hits,total,tier FROM shortform_rule ORDER BY id"):
        cnt = f"<span class='mono sub'>{hits}/{tot}편</span>" if hits else ""
        sf_rules.append(
            f"<tr><td class='nowrap'><span class='pill p-{TIER[tier]}'>{e(tier)}</span></td>"
            f"<td class='nowrap sub'>{e(grp)}</td>"
            f"<td><b>{e(rule)}</b> {cnt}<span class='sub'>{e(ev)}</span></td></tr>")
    sfrules = "".join(sf_rules)

    sfparts = "".join(
        f"<tr><td class='nowrap'><b>{e(nm)}</b></td><td>{e(pur)}</td>"
        f"<td class='mono r nowrap'>{lo}~{hi}자</td>"
        f"<td class='mono r nowrap'>{lo/6.6:.0f}~{hi/6.6:.0f}초</td>"
        f"<td class='sub'>{e(ph or '')}</td></tr>"
        for nm, pur, lo, hi, ph in q(
            "SELECT name,purpose,chars_min,chars_max,phrasing FROM shortform_part ORDER BY seq"))

    sfdocs = "".join(
        f"<tr><td class='mono nowrap'>{e(a)}</td>"
        f"<td class='nowrap'>차{ep:02d}<b>#{no}</b></td>"
        f"<td>{e(fo[7:])}</td>"
        f"<td class='mono r'>{ch}</td><td class='mono r'>{sec:.0f}s</td>"
        f"<td class='mono r'>{'' if w is None else str(w)+'~'+str(w+10)+'%'}</td>"
        f"<td class='mono r'>{'' if n10 is None else f'{n10:.1f}%'}</td></tr>"
        for a, ep, no, fo, ch, sec, w, n10 in q(
            "SELECT aired,ep,no,folder,chars,est_sec,long_window,ngram10 FROM shortform_doc"
            " WHERE rerun=0 ORDER BY ep,no"))

    # ── 세이브 슬롯 ───────────────────────────────────────────
    slots = "".join(
        f"<tr><td class='mono nowrap'>{e(kst)}</td><td class='mono'>{e(tag)}</td>"
        f"<td class='mono sub'>{e(sha or '-')}</td><td>{e(sm)}</td></tr>"
        for tag, kst, sha, sm in q(
            "SELECT tag,kst,sha,summary FROM checkpoint ORDER BY id DESC"))

    # ── 대본 인덱스 ───────────────────────────────────────────
    doc_rows = []
    for no, ep, chars, head, kw, st in q(
            "SELECT ep_no,ep,chars,headline,keywords,status FROM script_doc ORDER BY ep_no, file"):
        pill = "" if st == "작성됨" else "<span class='pill p-todo'>빈 템플릿</span>"
        doc_rows.append(
            f"<tr><td class='num'>{no:02d}</td>"
            f"<td><b>{e(ep.split('_',1)[-1])}</b>{pill}"
            f"<span class='sub'>{e(head or '')}</span></td>"
            f"<td class='mono r'>{chars:,}</td>"
            f"<td class='kw'>{''.join(f'<span>{e(k)}</span>' for k in kw.split(', ')[:7])}</td></tr>")
    docs = "".join(doc_rows)

    prj = "".join(
        f"<tr><td class='nowrap'>{e(ep.split('_',1)[0])}</td><td>{e(nm)}</td>"
        f"<td class='nowrap'><span class='pill{'' if k=='최종' else ' p-partial'}'>{e(k)}</span></td>"
        f"<td class='mono sub'>{e(fid)}</td></tr>"
        for ep, nm, k, fid in q(
            "SELECT ep,name,kind,drive_id FROM episode_prproj ORDER BY ep, kind DESC"))

    motion = "".join(
        f"<tr><td><b>{e(nm)}</b><span class='sub'>{e(note or '')}</span></td>"
        f"<td class='mono nowrap'>{e(par)}</td>"
        f"<td class='mono nowrap'>{e(fv)} → {e(tv)}</td>"
        f"<td class='mono r'>{fr:.0f}f</td><td class='mono r'>{sec:.3f}s</td>"
        f"<td class='nowrap'>{e(ez or '')}</td></tr>"
        for nm, par, fv, tv, fr, sec, ez, note in q(
            "SELECT name,param,from_value,to_value,frames_2997,seconds,easing,note"
            " FROM motion_preset ORDER BY id"))

    # ── 문제와 해결 ────────────────────────────────────────────
    issues = []
    for seq, t, sym, cause, fix, ver, st in q(
            "SELECT seq,title,symptom,root_cause,fix,verification,status FROM issue ORDER BY seq"):
        label = {"fixed": "해결", "worked-around": "우회", "open": "미해결"}[st]
        ver_row = f"<dt>확인</dt><dd class='ver'>{e(ver)}</dd>" if ver else ""
        issues.append(
            f"<article class='issue st-{st}'>"
            f"<h3><span class='seq'>{seq}</span>{e(t)}<span class='tag'>{label}</span></h3>"
            f"<dl><dt>증상</dt><dd>{e(sym)}</dd>"
            f"<dt>원인</dt><dd>{e(cause)}</dd>"
            f"<dt>조치</dt><dd>{e(fix)}</dd>{ver_row}</dl></article>")

    # ── 판단 ──────────────────────────────────────────────────
    decisions = []
    for topic, choice, why, revisit in q(
            "SELECT topic,choice,rationale,revisit_when FROM decision ORDER BY seq"):
        rv = f"<p class='revisit'>다시 볼 때 — {e(revisit)}</p>" if revisit else ""
        decisions.append(
            f"<article class='dec'><h3>{e(topic)}</h3><p class='choice'>{e(choice)}</p>"
            f"<p class='why'>{e(why)}</p>{rv}</article>")

    # ── 브랜드 스펙 ────────────────────────────────────────────
    swatches, spec = [], []
    for cat, name, val, unit, src, note in q(
            "SELECT category,name,value,unit,source,note FROM brand_token ORDER BY id"):
        if val.startswith("#") and len(val) == 7:
            swatches.append(
                f"<figure class='sw'><span class='chip' style='background:{val}'></span>"
                f"<figcaption><b>{e(name)}</b><code>{e(val)}</code></figcaption></figure>")
        spec.append(
            f"<tr><td class='cat'>{e(cat)}</td><td>{e(name)}</td>"
            f"<td class='mono'>{e(val)}{(' ' + e(unit)) if unit else ''}</td>"
            f"<td class='sub'>{e(src)}</td><td class='sub'>{e(note)}</td></tr>")

    # ── 산출물 ────────────────────────────────────────────────
    renders = []
    for path, fmt, frames, b, note in q(
            "SELECT path,format,frames,bytes,note FROM render ORDER BY id"):
        mb = f"{b/1048576:.1f}" if b else "—"
        renders.append(
            f"<tr><td><code>{e(path)}</code></td><td><span class='fmt f-{e(fmt)}'>{e(fmt)}</span></td>"
            f"<td class='mono r'>{frames or '—'}</td><td class='mono r'>{mb}</td>"
            f"<td class='sub'>{e(note)}</td></tr>")

    # ── 진행 ──────────────────────────────────────────────────
    phases = []
    for seq, title, detail in q("SELECT seq,title,detail FROM phase ORDER BY seq"):
        phases.append(f"<li><b>{e(title)}</b><span>{e(detail)}</span></li>")

    # ── 자료 ──────────────────────────────────────────────────
    assets = []
    for kind, name, b, stored, note in q(
            "SELECT kind,name,bytes,stored,note FROM asset ORDER BY id"):
        mb = f"{b/1048576:.0f} MB" if b else "—"
        assets.append(
            f"<tr><td class='cat'>{e(kind)}</td><td>{e(name)}</td>"
            f"<td class='mono r nowrap'>{mb}</td><td class='sub'>{e(stored)}</td>"
            f"<td class='sub'>{e(note)}</td></tr>")

    # ── 커밋 ──────────────────────────────────────────────────
    commits = []
    for sha, subj, f, i, d in q(
            "SELECT sha,subject,files_changed,insertions,deletions FROM commit_log ORDER BY seq DESC"):
        commits.append(
            f"<li><code class='sha'>{sha[:7]}</code><span class='subj'>{e(subj)}</span>"
            f"<span class='stat mono'>{f}<i>f</i> <b class='plus'>+{i}</b> <b class='minus'>−{d}</b></span></li>")


    # ── 시작하기 / 환경 / 명령어 ────────────────────────────────
    start = "".join(
        f"<li><b>{e(step)}</b><span>{e(detail)}</span></li>"
        for _, step, detail in q("SELECT ord,step,detail FROM v_start_here"))
    envs = "".join(
        f"<tr><td><b>{e(n)}</b></td><td class='mono'>{e(v)}</td><td class='mono sub'>{e(loc)}</td>"
        f"<td>{e(inst)}</td><td class='sub'>{e(note)}</td></tr>"
        for n, v, loc, inst, note in q("SELECT name,version,location,install,note FROM env_tool ORDER BY id"))
    runs = "".join(
        f"<article class='run'><h3><span class='seq'>{seq}</span>{e(topic)}</h3>"
        f"<p class='purpose'>{e(purpose)}</p><pre><code>{e(cmd)}</code></pre>"
        + (f"<p class='note'>{e(note)}</p>" if note else "") + "</article>"
        for seq, topic, purpose, cmd, note in q("SELECT seq,topic,purpose,command,note FROM runbook ORDER BY seq"))
    tree = "".join(
        f"<tr><td><code>{e(path)}</code></td><td class='cat'>{e(role)}</td><td class='sub'>{e(note)}</td></tr>"
        for path, role, note in q("SELECT path,role,note FROM repo_file ORDER BY role, path"))
    drive = "".join(
        f"<tr><td class='cat'>{e(kind)}</td><td class='dm'>{e(name)}</td>"
        f"<td class='mono sub nowrap'>{e(did)}</td><td class='sub'>{e(note)}</td></tr>"
        for kind, name, did, note in q("SELECT kind,name,drive_id,note FROM drive_map ORDER BY id"))
    layers = "".join(
        f"<tr><td><code>{e(n)}</code></td><td class='cat'>{e(f)}</td><td>{e(p)}</td>"
        f"<td class='sub mono'>{e(o)}</td></tr>"
        for n, f, p, o in q("SELECT name,family,purpose,key_options FROM layer_catalog ORDER BY family DESC, id"))
    opts = "".join(
        f"<tr><td class='cat'>{e(g)}</td><td><code>{e(k)}</code></td><td>{e(m)}</td>"
        f"<td class='sub mono'>{e(x)}</td></tr>"
        for g, k, m, x in q("SELECT grp,key,meaning,example FROM scene_option ORDER BY id"))
    setups = "".join(
        f"<tr><td><code>{e(c)}</code><span class='sub'>{e(i)}</span></td><td class='mono r'>{en:,.2f}</td>"
        f"<td class='mono r'>{st:,.2f}</td><td class='mono r'>{tg:,.2f}</td><td class='mono'>{e(rr)}</td>"
        f"<td class='mono r'>{hi:,.1f}<span class='sub'>{e(rrun)}</span></td><td class='sub'>{e(note)}</td></tr>"
        for c, i, en, st, tg, rr, hi, rrun, note in q(
            "SELECT config,instrument,entry,stop,target,rr,run_high,run_r,note FROM trade_setup ORDER BY id"))
    cons = "".join(
        f"<tr><td><b>{e(t)}</b></td><td class='mono'>{e(l)}</td><td>{e(wk)}</td></tr>"
        for t, l, wk in q("SELECT topic,limit_value,workaround FROM constraint_note ORDER BY id"))
    nexts = "".join(
        f"<li><b>{e(item)}</b>" + (f"<span class='blk'>대기 · {e(bl)}</span>" if bl else "")
        + f"<span>{e(detail)}</span></li>"
        for _, item, detail, bl in q("SELECT seq,item,detail,blocked_by FROM next_step ORDER BY seq"))

    counts = {n: con.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0]
              for (n,) in q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    con.close()

    page = TEMPLATE
    for token, value in {
        "__DATE__": e(ses[1]), "__REPO__": e(ses[2]), "__BRANCH__": e(ses[3]),
        "__GOAL__": e(ses[4]),
        "__BAR__": "".join(bar), "__CUTROWS__": "".join(rows),
        "__TOTALF__": str(total), "__TOTALS__": f"{total*1001/30000:.3f}",
        "__ISSUES__": "".join(issues), "__DECISIONS__": "".join(decisions),
        "__SWATCHES__": "".join(swatches), "__SPEC__": "".join(spec),
        "__RENDERS__": "".join(renders), "__PHASES__": "".join(phases),
        "__ASSETS__": "".join(assets), "__COMMITS__": "".join(commits),
        "__START__": start, "__ENVS__": envs, "__RUNS__": runs, "__TREE__": tree,
        "__DRIVE__": drive, "__LAYERS__": layers, "__OPTS__": opts, "__SETUPS__": setups,
        "__CONS__": cons, "__NEXTS__": nexts,
        "__FLOW__": flow, "__BENCH__": bench, "__TOOLS__": tools, "__PRPROJ__": prproj,
        "__DOCS__": docs, "__PRJ__": prj, "__MOTION__": motion, "__SLOTS__": slots,
        "__PIPELINE__": pipeline, "__FORMATS__": formats,
        "__SFRULES__": sfrules, "__SFPARTS__": sfparts, "__SFDOCS__": sfdocs,
        "__NSCENE__": str(counts.get("scene", 0)), "__NISSUE__": str(counts.get("issue", 0)),
        "__NTOKEN__": str(counts.get("brand_token", 0)), "__NRENDER__": str(counts.get("render", 0)),
    }.items():
        page = page.replace(token, value)

    OUT.write_text(page, encoding="utf-8")
    return OUT


TEMPLATE = r"""<title>차트명가 컷씬 작업 로그</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&display=swap">
<style>
:root{
  --bg:#F3F7F6; --surface:#FFFFFF; --surface-2:#E9F1EF; --inset:#F7FAF9;
  --ink:#0E1918; --ink-2:#47605C; --ink-3:#7A928E;
  --rule:#D9E6E3; --rule-2:#C4D6D2;
  --accent:#0B8C7F; --accent-ink:#076B60; --accent-soft:#D6ECE8;
  --alert:#C0201F; --alert-soft:#FADFDE;
  --mark:#D1004B; --mark-soft:#FBDCE7;
  --shadow:0 1px 2px rgba(14,25,24,.05), 0 8px 24px -12px rgba(14,25,24,.18);
  --fd:"Gowun Batang", "Nanum Myeongjo", serif;
  --fs:"IBM Plex Sans KR", "Apple SD Gothic Neo", system-ui, sans-serif;
  --fm:"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#0B1312; --surface:#111B1A; --surface-2:#182422; --inset:#0E1817;
  --ink:#E6EFED; --ink-2:#9FB6B2; --ink-3:#6C837F;
  --rule:#22302E; --rule-2:#2E403D;
  --accent:#3EC3B1; --accent-ink:#6FD9CA; --accent-soft:#10312D;
  --alert:#FF7A73; --alert-soft:#361A1A;
  --mark:#FF5E96; --mark-soft:#3A1526;
  --shadow:0 1px 2px rgba(0,0,0,.5), 0 8px 24px -12px rgba(0,0,0,.7);
}}
:root[data-theme="dark"]{
  --bg:#0B1312; --surface:#111B1A; --surface-2:#182422; --inset:#0E1817;
  --ink:#E6EFED; --ink-2:#9FB6B2; --ink-3:#6C837F;
  --rule:#22302E; --rule-2:#2E403D;
  --accent:#3EC3B1; --accent-ink:#6FD9CA; --accent-soft:#10312D;
  --alert:#FF7A73; --alert-soft:#361A1A;
  --mark:#FF5E96; --mark-soft:#3A1526;
  --shadow:0 1px 2px rgba(0,0,0,.5), 0 8px 24px -12px rgba(0,0,0,.7);
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--fs);font-weight:400;
  line-height:1.65;-webkit-font-smoothing:antialiased;margin:0}
.wrap{max-width:1080px;margin:0 auto;padding:0 clamp(18px,4vw,44px) 96px}
a{color:var(--accent-ink)}
code,.mono{font-family:var(--fm);font-variant-numeric:tabular-nums}
.mono{font-size:.92em}
.r{text-align:right}.nowrap{white-space:nowrap}
.sub{color:var(--ink-3);font-size:.86rem;line-height:1.45}

/* ── 머리말 ───────────────────────────────── */
header.top{padding:clamp(56px,9vw,104px) 0 40px;border-bottom:1px solid var(--rule)}
.eyebrow{font-family:var(--fm);font-size:.74rem;letter-spacing:.18em;text-transform:uppercase;
  color:var(--accent-ink);margin:0 0 18px}
h1{font-family:var(--fd);font-weight:700;font-size:clamp(2.3rem,6vw,3.6rem);line-height:1.12;
  letter-spacing:-.01em;margin:0 0 18px;text-wrap:balance}
.goal{font-size:clamp(1rem,2.2vw,1.16rem);color:var(--ink-2);max-width:60ch;margin:0 0 28px}
.meta{display:flex;flex-wrap:wrap;gap:10px 22px;font-family:var(--fm);font-size:.82rem;color:var(--ink-3)}
.meta b{color:var(--ink-2);font-weight:500}
.counts{display:flex;flex-wrap:wrap;gap:8px;margin-top:26px}
.counts span{background:var(--surface);border:1px solid var(--rule);border-radius:999px;
  padding:5px 13px;font-size:.8rem;color:var(--ink-2);box-shadow:var(--shadow)}
.counts b{font-family:var(--fm);color:var(--ink);font-weight:600}

/* ── 섹션 ─────────────────────────────────── */
section{padding-top:clamp(52px,7vw,76px)}
h2{font-family:var(--fd);font-weight:700;font-size:clamp(1.5rem,3.4vw,2rem);margin:0 0 6px;
  letter-spacing:-.01em}
.lede{color:var(--ink-2);margin:0 0 26px;max-width:66ch}

/* ── 타임라인 ─────────────────────────────── */
.bar{display:flex;gap:3px;height:76px;margin-bottom:10px}
.seg{border-radius:5px;display:flex;flex-direction:column;justify-content:center;align-items:center;
  gap:1px;color:#fff;min-width:0;overflow:hidden}
.seg-1{background:#0B8C7F}.seg-2{background:#12A594}
.seg-3{background:#C0201F}.seg-4{background:#D1004B}
.seg-n{font-family:var(--fd);font-size:1.05rem;font-weight:700;line-height:1}
.seg-f{font-family:var(--fm);font-size:.78rem;opacity:.95}
.seg-p{font-family:var(--fm);font-size:.68rem;opacity:.72}
.bar-foot{display:flex;justify-content:space-between;font-family:var(--fm);font-size:.78rem;
  color:var(--ink-3);margin-bottom:30px}

/* ── 표 ───────────────────────────────────── */
.scroll{overflow-x:auto;border:1px solid var(--rule);border-radius:12px;background:var(--surface);
  box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th{font-family:var(--fm);font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-3);text-align:left;font-weight:500;padding:13px 14px;
  border-bottom:1px solid var(--rule-2);white-space:nowrap;background:var(--inset)}
td{padding:12px 14px;border-bottom:1px solid var(--rule);vertical-align:top}
tr:last-child td{border-bottom:0}
td .sub{display:block;margin-top:2px}
td.num{font-family:var(--fd);font-size:1.1rem;font-weight:700;color:var(--accent-ink);width:1%}
td.cat{color:var(--ink-3);font-size:.82rem;white-space:nowrap}
td.line{min-width:22rem}
code{background:var(--surface-2);border-radius:4px;padding:1px 5px;font-size:.85em;color:var(--ink)}
.fmt{font-family:var(--fm);font-size:.74rem;padding:2px 8px;border-radius:4px;
  background:var(--surface-2);color:var(--ink-2);white-space:nowrap}
.f-qtrle,.f-vp9a{background:var(--accent-soft);color:var(--accent-ink)}

/* ── 문제 카드 ────────────────────────────── */
.issues{display:grid;gap:14px}
.issue{background:var(--surface);border:1px solid var(--rule);border-radius:12px;
  padding:20px 22px;box-shadow:var(--shadow)}
.issue h3{display:flex;align-items:center;gap:10px;margin:0 0 14px;font-size:1.02rem;
  font-weight:600;letter-spacing:-.005em}
.issue .seq{font-family:var(--fm);font-size:.78rem;color:var(--ink-3);
  border:1px solid var(--rule-2);border-radius:5px;padding:1px 7px}
.issue .tag{margin-left:auto;font-size:.72rem;font-family:var(--fm);padding:2px 9px;border-radius:999px;
  background:var(--accent-soft);color:var(--accent-ink);white-space:nowrap}
.issue.st-worked-around .tag{background:var(--mark-soft);color:var(--mark)}
.issue.st-open .tag{background:var(--alert-soft);color:var(--alert)}
tr.stage.st-here{background:var(--accent-soft)}
tr.stage.st-here b{color:var(--accent-ink)}
.pill.p-here{background:var(--accent-soft);color:var(--accent-ink)}
.pill.p-none{background:transparent;color:var(--ink-3);border:1px solid var(--rule-2)}
.kw span{display:inline-block;font-size:.72rem;font-family:var(--fm);padding:1px 7px;margin:1px 3px 1px 0;
  border:1px solid var(--rule-2);border-radius:4px;color:var(--ink-2)}
.pill{font-size:.72rem;font-family:var(--fm);padding:2px 9px;border-radius:999px;white-space:nowrap;
  background:var(--accent-soft);color:var(--accent-ink)}
.pill.p-partial{background:var(--mark-soft);color:var(--mark)}
.pill.p-todo{background:var(--alert-soft);color:var(--alert)}
.issue dl{display:grid;grid-template-columns:3.6rem 1fr;gap:7px 14px;margin:0;font-size:.9rem}
.issue dt{font-family:var(--fm);font-size:.74rem;color:var(--ink-3);padding-top:3px}
.issue dd{margin:0;color:var(--ink-2)}
.issue dd.ver{color:var(--accent-ink)}

/* ── 판단 ─────────────────────────────────── */
.decs{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(290px,1fr))}
.dec{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:18px 20px;
  box-shadow:var(--shadow)}
.dec h3{margin:0 0 8px;font-size:.78rem;font-family:var(--fm);letter-spacing:.08em;
  text-transform:uppercase;color:var(--ink-3);font-weight:500}
.dec .choice{margin:0 0 8px;font-weight:600;font-size:1rem;line-height:1.45;color:var(--ink)}
.dec .why{margin:0;font-size:.88rem;color:var(--ink-2)}
.dec .revisit{margin:10px 0 0;font-size:.8rem;color:var(--mark)}

/* ── 색 견본 ──────────────────────────────── */
.sws{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));margin-bottom:26px}
.sw{margin:0;background:var(--surface);border:1px solid var(--rule);border-radius:10px;overflow:hidden;
  box-shadow:var(--shadow)}
.sw .chip{display:block;height:52px}
.sw figcaption{padding:9px 11px;display:flex;flex-direction:column;gap:1px}
.sw b{font-size:.82rem;font-weight:500}
.sw code{background:none;padding:0;font-size:.76rem;color:var(--ink-3)}

/* ── 진행 ─────────────────────────────────── */
ol.phases{list-style:none;counter-reset:p;margin:0;padding:0;display:grid;gap:2px}
ol.phases li{counter-increment:p;display:grid;grid-template-columns:2.2rem 11rem 1fr;gap:14px;
  padding:11px 4px;border-bottom:1px solid var(--rule);align-items:baseline}
ol.phases li::before{content:counter(p,decimal-leading-zero);font-family:var(--fm);font-size:.78rem;
  color:var(--ink-3)}
ol.phases b{font-weight:600;font-size:.94rem}
ol.phases span{color:var(--ink-2);font-size:.88rem}
@media (max-width:720px){ol.phases li{grid-template-columns:2.2rem 1fr}ol.phases span{grid-column:2}}

/* ── 커밋 ─────────────────────────────────── */
ul.commits{list-style:none;margin:0;padding:0}
ul.commits li{display:flex;gap:14px;align-items:baseline;padding:9px 4px;
  border-bottom:1px solid var(--rule);flex-wrap:wrap}
.sha{color:var(--accent-ink);background:none;padding:0}
.subj{flex:1;min-width:14rem;font-size:.92rem}
.stat{font-size:.76rem;color:var(--ink-3);white-space:nowrap}
.stat i{font-style:normal;opacity:.6}
.plus{color:var(--accent-ink);font-weight:500}
.minus{color:var(--alert);font-weight:500}


/* ── 내비 ─────────────────────────────────── */
nav.toc{position:sticky;top:0;z-index:9;background:color-mix(in srgb,var(--bg) 92%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--rule);margin-bottom:-1px}
nav.toc ol{list-style:none;margin:0;padding:11px 0;display:flex;gap:4px;overflow-x:auto;
  font-family:var(--fm);font-size:.76rem}
nav.toc a{display:block;padding:4px 11px;border-radius:999px;color:var(--ink-3);text-decoration:none;
  white-space:nowrap;border:1px solid transparent}
nav.toc a:hover{color:var(--accent-ink);border-color:var(--rule-2);background:var(--surface)}
section{scroll-margin-top:56px}

/* ── 시작하기 ─────────────────────────────── */
ol.start{list-style:none;counter-reset:s;margin:0 0 30px;padding:0;display:grid;gap:2px}
ol.start li{counter-increment:s;display:grid;grid-template-columns:2rem 13rem 1fr;gap:14px;
  padding:11px 4px;border-bottom:1px solid var(--rule);align-items:baseline}
ol.start li::before{content:counter(s);font-family:var(--fd);font-size:1rem;font-weight:700;
  color:var(--accent-ink)}
ol.start b{font-weight:600;font-size:.94rem}
ol.start span{color:var(--ink-2);font-size:.88rem}
@media (max-width:720px){ol.start li{grid-template-columns:2rem 1fr}ol.start span{grid-column:2}}

h3.sub-h{font-family:var(--fm);font-size:.74rem;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);font-weight:500;margin:34px 0 12px}

/* ── 명령어 ───────────────────────────────── */
.runs{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.run{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:16px 18px;
  box-shadow:var(--shadow)}
.run h3{display:flex;align-items:center;gap:9px;margin:0 0 4px;font-size:.98rem;font-weight:600}
.run .seq{font-family:var(--fm);font-size:.74rem;color:var(--ink-3);
  border:1px solid var(--rule-2);border-radius:5px;padding:1px 6px}
.run .purpose{margin:0 0 10px;font-size:.86rem;color:var(--ink-2)}
.run pre{margin:0;background:var(--inset);border:1px solid var(--rule);border-radius:8px;
  padding:11px 13px;overflow-x:auto}
.run pre code{background:none;padding:0;font-size:.78rem;line-height:1.6;white-space:pre}
.run .note{margin:9px 0 0;font-size:.8rem;color:var(--ink-3)}
td.dm{font-variant-numeric:tabular-nums;white-space:pre}

/* ── 다음 할 일 ───────────────────────────── */
ol.next{list-style:none;counter-reset:n;margin:0;padding:0;display:grid;gap:2px}
ol.next li{counter-increment:n;display:grid;grid-template-columns:2rem 1fr;gap:14px;
  padding:13px 4px;border-bottom:1px solid var(--rule)}
ol.next li::before{content:counter(n);font-family:var(--fd);font-size:1rem;font-weight:700;
  color:var(--accent-ink)}
ol.next b{font-weight:600;font-size:.96rem;grid-column:2}
ol.next .blk{grid-column:2;font-family:var(--fm);font-size:.72rem;color:var(--mark);
  background:var(--mark-soft);border-radius:999px;padding:1px 9px;justify-self:start;margin:5px 0 3px}
ol.next span:last-child{grid-column:2;color:var(--ink-2);font-size:.88rem;margin-top:3px}

footer{margin-top:72px;padding-top:22px;border-top:1px solid var(--rule);
  color:var(--ink-3);font-size:.82rem}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>

<div class="wrap">

<header class="top">
  <p class="eyebrow">작업 로그 · __DATE__</p>
  <h1>차트명가 컷씬 작업 로그</h1>
  <p class="goal">__GOAL__</p>
  <div class="meta">
    <span><b>저장소</b> __REPO__</span>
    <span><b>브랜치</b> __BRANCH__</span>
    <span><b>원본 데이터</b> log/worklog.db</span>
  </div>
  <div class="counts">
    <span>컷 <b>__NSCENE__</b></span>
    <span>렌더 <b>__NRENDER__</b></span>
    <span>브랜드 실측값 <b>__NTOKEN__</b></span>
    <span>문제 <b>__NISSUE__</b></span>
  </div>
</header>

<nav class="toc"><ol>
  <li><a href="#start">시작하기</a></li>
  <li><a href="#sync">대본 싱크</a></li>
  <li><a href="#flow">작업 방식</a></li>
  <li><a href="#scripts">대본 인덱스</a></li>
  <li><a href="#shortform">숏폼 대본</a></li>
  <li><a href="#build">컷 짜는 법</a></li>
  <li><a href="#brand">브랜드 스펙</a></li>
  <li><a href="#issues">문제와 해결</a></li>
  <li><a href="#decisions">판단</a></li>
  <li><a href="#drive">원본 자료</a></li>
  <li><a href="#outputs">산출물</a></li>
  <li><a href="#limits">제약</a></li>
  <li><a href="#next">다음 할 일</a></li>
  <li><a href="#history">진행·커밋</a></li>
</ol></nav>

<section id="start">
  <h2>시작하기</h2>
  <p class="lede">컨테이너는 세션이 끝나면 사라집니다. 새로 열었을 때 이 순서대로 보면 됩니다.</p>
  <ol class="start">__START__</ol>

  <h3 class="sub-h">이 저장소가 맡는 곳</h3>
  <p class="lede">영상 한 편은 네 단계를 거칩니다. 이 저장소는 그중 <b>롱폼 3단계</b> 하나만 합니다.
     받는 것은 타임코드가 붙은 대본, 내놓는 것은 차트만 있는 영상 클립입니다.
     자막·타이틀·로고는 2단계에서 이미 들어가므로 렌더에 넣지 않습니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>포맷</th><th>단계</th><th>담당</th><th>상태</th></tr></thead>
    <tbody>__PIPELINE__</tbody>
  </table></div>

  <h3 class="sub-h">롱폼과 숏폼</h3>
  <div class="scroll"><table>
    <thead><tr><th></th><th>화면비</th><th>채널 최종본</th><th>우리가 납품</th><th>길이</th><th>톤앤매너</th></tr></thead>
    <tbody>__FORMATS__</tbody>
  </table></div>

  <h3 class="sub-h">되돌릴 수 있는 시점</h3>
  <p class="lede">한 슬롯 = 그 시점의 저장소 전체.
     <code>python3 log/save.py "어디까지"</code> 로 만들고,
     <code>git restore --source=&lt;해시&gt; -- .</code> 로 되돌립니다.
     이 저장소는 태그 푸시가 막혀 있어 슬롯 이름과 해시의 짝을
     <code>log/data/checkpoints.json</code> 에 적어 함께 올립니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>시각 (KST)</th><th>슬롯</th><th>커밋</th><th>어디까지</th></tr></thead>
    <tbody>__SLOTS__</tbody>
  </table></div>

  <h3 class="sub-h">환경 다시 깔기</h3>
  <div class="scroll"><table>
    <thead><tr><th>도구</th><th>버전</th><th>위치</th><th>설치</th><th>비고</th></tr></thead>
    <tbody>__ENVS__</tbody>
  </table></div>

  <h3 class="sub-h">명령어</h3>
  <div class="runs">__RUNS__</div>

  <h3 class="sub-h">파일 지도</h3>
  <div class="scroll"><table>
    <thead><tr><th>경로</th><th>역할</th><th>설명</th></tr></thead>
    <tbody>__TREE__</tbody>
  </table></div>
</section>

<section id="sync">
  <h2>대본과 컷 싱크</h2>
  <p class="lede">타임코드는 29.97 드롭프레임입니다. 59.94fps(=29.97×2)로 렌더해서
     프레임 수가 정확히 두 배가 되고, 프리미어 29.97 시퀀스에 프레임 단위로 얹힙니다.
     아래 막대의 너비가 실제 컷 길이 비율입니다.</p>
  <div class="bar">__BAR__</div>
  <div class="bar-foot"><span>00;05;26;27 시작</span><span>합계 __TOTALF__프레임 · __TOTALS__초</span></div>
  <div class="scroll"><table>
    <thead><tr><th>#</th><th>컷</th><th>타임코드</th><th>29.97</th><th>59.94</th><th>초</th><th>대사</th></tr></thead>
    <tbody>__CUTROWS__</tbody>
  </table></div>
</section>

<section id="flow">
  <h2>작업 방식</h2>
  <p class="lede">대본 한 편을 받아 컷을 납품하기까지의 순서입니다.
     9단계 중 8단계까지가 코드로 돌아가고, 마지막 프리미어 반입만 아직 손으로 합니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>#</th><th>단계</th><th>방법</th><th>담당</th><th>상태</th></tr></thead>
    <tbody>__FLOW__</tbody>
  </table></div>

  <h3 class="sub-h">렌더에 걸리는 시간</h3>
  <p class="lede">2026-08-26 실측. 컷 4개 956프레임(15.95초) 기준이고,
     병렬 결과물은 순차와 md5 까지 같습니다. 렌더가 결정론적이라 쪼개도 결과가 흔들리지 않습니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>방식</th><th>코어</th><th>프레임</th><th>영상 길이</th><th>실제 소요</th><th>캡처 fps</th><th>비고</th></tr></thead>
    <tbody>__BENCH__</tbody>
  </table></div>

  <h3 class="sub-h">레퍼런스 확인 — .prproj 는 그냥 읽힙니다</h3>
  <p class="lede">프로젝트 파일이 gzip 으로 압축된 XML 이라 프리미어도 MCP 도 없이 표준 도구로 열립니다.
     영상 프레임을 찍어 색을 재는 것보다 빠르고, 값이 렌더링을 거치지 않은 원본이라 더 정확합니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>항목</th><th>확인한 것</th><th>방법</th></tr></thead>
    <tbody>__PRPROJ__</tbody>
  </table></div>

  <h3 class="sub-h">외부 도구 검토</h3>
  <div class="decs">__TOOLS__</div>
</section>

<section id="scripts">
  <h2>대본 인덱스</h2>
  <p class="lede">작업물 폴더 전체를 훑어 회차별 대본을 저장소 안에 넣었습니다.
     이제 드라이브에 붙지 않아도 검색이 됩니다.
     전문 검색은 <code>script_fts MATCH '키워드'</code>, 가중치는 <code>script_keyword</code> 입니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>#</th><th>회차</th><th>분량</th><th>키워드</th></tr></thead>
    <tbody>__DOCS__</tbody>
  </table></div>

  <h3 class="sub-h">회차별 프리미어 프로젝트</h3>
  <p class="lede">레퍼런스 확인 대상입니다. 자동 저장본은 제외했습니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>회차</th><th>파일</th><th>종류</th><th>드라이브 ID</th></tr></thead>
    <tbody>__PRJ__</tbody>
  </table></div>

  <h3 class="sub-h">회사 모션 문법</h3>
  <p class="lede">최종본 <code>.prproj</code> 의 키프레임을 디코드해서 뽑은 값입니다.
     팀장님이 프리미어에서 손으로 만든 움직임이 프레임 단위로 그대로 나옵니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>모션</th><th>파라미터</th><th>값</th><th>29.97</th><th>초</th><th>보간</th></tr></thead>
    <tbody>__MOTION__</tbody>
  </table></div>
</section>

<section id="shortform">
  <h2>숏폼 대본 — 롱폼에서 뽑는 규칙</h2>
  <p class="lede">숏폼 대본을 만드는 방식은 팀장님 머릿속에만 있었습니다.
     나간 숏폼 25편과 그 원본 롱폼 13편을 문장·n-gram 단위로 맞춰 보고 역으로 뽑아낸 규칙입니다.
     핵심은 <b>복붙이 아니라 다시 쓴다</b>는 것 — 10자 n-gram 겹침이 중앙값 2.2%뿐입니다.</p>
  <p class="lede">등급은 기존 24편 중 몇 편이 지켰는지로 나눴습니다.
     5개를 모두 지킨 편은 2편뿐이라, 이건 규칙이라기보다 경향입니다.
     <b>권장·선택은 어겨도 됩니다.</b></p>
  <div class="scroll"><table>
    <thead><tr><th>등급</th><th>갈래</th><th>규칙과 근거</th></tr></thead>
    <tbody>__SFRULES__</tbody>
  </table></div>

  <h3 class="sub-h">뼈대</h3>
  <div class="scroll"><table>
    <thead><tr><th>단</th><th>하는 일</th><th>분량</th><th>길이</th><th>쓰는 말</th></tr></thead>
    <tbody>__SFPARTS__</tbody>
  </table></div>

  <h3 class="sub-h">나간 숏폼 25편</h3>
  <p class="lede">「롱폼 구간」은 그 편이 롱폼의 어느 부분에서 왔는지,
     「10자 겹침」은 원문을 얼마나 그대로 썼는지입니다.
     #1 이 #2 보다 앞 구간에서 오는 것이 12쌍 중 11쌍입니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>방영</th><th>편</th><th>제목</th><th>자수</th><th>길이</th><th>롱폼 구간</th><th>10자 겹침</th></tr></thead>
    <tbody>__SFDOCS__</tbody>
  </table></div>
</section>

<section id="build">
  <h2>컷 짜는 법</h2>
  <p class="lede">새 대본이 오면 <code>scenes/cmg-20ma-runner.scenes.js</code> 를 본떠 만듭니다.
     아래가 그때 쓰는 재료 전부입니다.</p>

  <h3 class="sub-h">레이어 22종</h3>
  <div class="scroll"><table>
    <thead><tr><th>이름</th><th>계열</th><th>쓰임</th><th>주요 옵션</th></tr></thead>
    <tbody>__LAYERS__</tbody>
  </table></div>

  <h3 class="sub-h">씬 설정 키</h3>
  <div class="scroll"><table>
    <thead><tr><th>그룹</th><th>키</th><th>뜻</th><th>예</th></tr></thead>
    <tbody>__OPTS__</tbody>
  </table></div>

  <h3 class="sub-h">컷에 쓴 매매 수치</h3>
  <div class="scroll"><table>
    <thead><tr><th>설정</th><th>진입</th><th>손절</th><th>익절</th><th>손익비</th><th>이후 고점</th><th>비고</th></tr></thead>
    <tbody>__SETUPS__</tbody>
  </table></div>
</section>

<section id="issues">
  <h2>문제와 해결</h2>
  <p class="lede">증상에서 원인까지 내려가 고친 것들. 확인란은 고쳤다고 말할 근거입니다.</p>
  <div class="issues">__ISSUES__</div>
</section>

<section id="decisions">
  <h2>판단과 근거</h2>
  <p class="lede">되돌릴 수 있게 이유를 남겨 둡니다.</p>
  <div class="decs">__DECISIONS__</div>
</section>

<section id="brand">
  <h2>브랜드 스펙</h2>
  <p class="lede">전부 레퍼런스 영상 프레임에서 픽셀 단위로 잰 값입니다. 짐작한 값은 없습니다.</p>
  <div class="sws">__SWATCHES__</div>
  <div class="scroll"><table>
    <thead><tr><th>분류</th><th>항목</th><th>값</th><th>출처</th><th>비고</th></tr></thead>
    <tbody>__SPEC__</tbody>
  </table></div>
</section>

<section id="outputs">
  <h2>산출물</h2>
  <div class="scroll"><table>
    <thead><tr><th>파일</th><th>포맷</th><th>프레임</th><th>MB</th><th>비고</th></tr></thead>
    <tbody>__RENDERS__</tbody>
  </table></div>
</section>

<section id="drive">
  <h2>원본 자료 — 구글 드라이브</h2>
  <p class="lede">공유 폴더는 인증 없이 목록을 볼 수 있습니다.
     폴더 목록 <code>drive.google.com/embeddedfolderview?id=&lt;ID&gt;#list</code> ·
     파일 받기 <code>drive.usercontent.google.com/download?id=&lt;ID&gt;&amp;export=download&amp;confirm=t</code></p>
  <div class="scroll"><table>
    <thead><tr><th>종류</th><th>이름</th><th>Drive ID</th><th>비고</th></tr></thead>
    <tbody>__DRIVE__</tbody>
  </table></div>
</section>

<section>
  <h2>받아 온 자료</h2>
  <div class="scroll"><table>
    <thead><tr><th>종류</th><th>이름</th><th>크기</th><th>처리</th><th>비고</th></tr></thead>
    <tbody>__ASSETS__</tbody>
  </table></div>
</section>

<section id="limits">
  <h2>환경이 거는 제약</h2>
  <p class="lede">한 번씩 부딪혀 본 것들입니다. 같은 벽에 다시 부딪히지 않으려고 적어 둡니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>항목</th><th>한계</th><th>대응</th></tr></thead>
    <tbody>__CONS__</tbody>
  </table></div>
</section>

<section id="next">
  <h2>다음에 할 일</h2>
  <ol class="next">__NEXTS__</ol>
</section>

<section id="history">
  <h2>진행</h2>
  <ol class="phases">__PHASES__</ol>
</section>

<section>
  <h2>커밋</h2>
  <ul class="commits">__COMMITS__</ul>
</section>

<footer>
  이 페이지는 <code>log/worklog.db</code> 에서 만들어집니다 —
  <code>python3 log/build_worklog_db.py --md &amp;&amp; python3 log/build_worklog_page.py</code>
</footer>

</div>
"""

if __name__ == "__main__":
    p = build()
    print(f"{p.relative_to(ROOT)} 생성 완료 ({p.stat().st_size/1024:.0f} KB)")
