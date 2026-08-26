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

<section>
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

<section>
  <h2>문제와 해결</h2>
  <p class="lede">증상에서 원인까지 내려가 고친 것들. 확인란은 고쳤다고 말할 근거입니다.</p>
  <div class="issues">__ISSUES__</div>
</section>

<section>
  <h2>판단과 근거</h2>
  <p class="lede">되돌릴 수 있게 이유를 남겨 둡니다.</p>
  <div class="decs">__DECISIONS__</div>
</section>

<section>
  <h2>브랜드 스펙</h2>
  <p class="lede">전부 레퍼런스 영상 프레임에서 픽셀 단위로 잰 값입니다. 짐작한 값은 없습니다.</p>
  <div class="sws">__SWATCHES__</div>
  <div class="scroll"><table>
    <thead><tr><th>분류</th><th>항목</th><th>값</th><th>출처</th><th>비고</th></tr></thead>
    <tbody>__SPEC__</tbody>
  </table></div>
</section>

<section>
  <h2>산출물</h2>
  <div class="scroll"><table>
    <thead><tr><th>파일</th><th>포맷</th><th>프레임</th><th>MB</th><th>비고</th></tr></thead>
    <tbody>__RENDERS__</tbody>
  </table></div>
</section>

<section>
  <h2>받아 온 자료</h2>
  <div class="scroll"><table>
    <thead><tr><th>종류</th><th>이름</th><th>크기</th><th>처리</th><th>비고</th></tr></thead>
    <tbody>__ASSETS__</tbody>
  </table></div>
</section>

<section>
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
