#!/usr/bin/env node
/**
 * 렌더러가 **실제로 찍은** 글자의 치수를 재서 내보낸다.
 *
 *   node tools/ae/text-metrics.mjs scenes/sl-11-4.scenes.js cut3-conditions
 *   node tools/ae/text-metrics.mjs scenes/sl-11-4.scenes.js --all --out C:/aelab/ae
 *
 * 왜 필요한가
 *   AE 이식에서 글자만 배지 기준 +3.5px 오른쪽 / +5px 아래로 어긋난다. 글자 폭은
 *   같으니(258 vs 257px 실측) 어긋난 건 **기준점**이다. 캔버스는 textBaseline 'middle'
 *   로 찍는데 AE 의 점 텍스트 원점은 알파벳 베이스라인이라, 그 차이를 폰트에서 재서
 *   넘겨야 한다. 크로미움이 재는 값이 진실이므로 **그 페이지 안에서** 재야 한다.
 *
 * 어떻게
 *   fillText/strokeText 를 감싸 호출을 받아 적는다. 렌더는 건드리지 않는다 —
 *   원래 함수를 그대로 부르고 옆에서 기록만 한다. 레이어를 가리려면 렌더러의
 *   pass 기능으로 한 층씩만 그린다 (split 이 쓰는 그 길이다).
 *
 * 총괄이 얹은 함정 셋 (2026-09-03, 검토-글자치수)
 *   ① 글자가 늘 본 캔버스에 찍히지 않는다. premTextShadow 의 그림자 실루엣은
 *      오프스크린 스크래치(_shadowScratch)에 찍고 drawImage 로 합성한다 — 그 좌표는
 *      스크래치 로컬이다. 호출마다 ctx.canvas 가 본 캔버스인지 가려 버린다.
 *   ② 차명10 기울임은 ctx.transform 전단이다. fillText 좌표가 축정렬이 아니니
 *      호출마다 getTransform() 을 같이 적어 CTM 을 통과시킨다.
 *   ③ 블러 씬은 engine.js 가 차트 ctx 를 _blurLayer 로 바꿔치기한다 — ①의 필터에
 *      같이 걸린다(본 캔버스가 아니므로).
 */
import path from 'node:path';
import { writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const CAP = await import(pathToFileURL(path.join(ROOT, 'src/render/capture.mjs')).href);

/* ── 페이지 안에서 도는 코드 ────────────────────────────────────────────
   page.evaluate 로 문자열째 넘어간다. 바깥 변수를 쓰면 안 된다. */
function installProbe() {
  const rt = window.__runtime;
  const P = CanvasRenderingContext2D.prototype;
  const oFill = P.fillText;
  const oStroke = P.strokeText;
  let log = null;

  /** 'alphabetic' 기준과 지금 기준선의 세로 차이. 알파벳 베이스라인 = y + 이 값. */
  function baselineShift(ctx, text) {
    const keep = ctx.textBaseline;
    if (keep === 'alphabetic') return 0;
    /*  actualBoundingBoxAscent 는 '넘긴 y 에서 잉크 꼭대기까지'다. 잉크 꼭대기는
        기준선을 뭘 쓰든 같은 자리이므로, 두 기준의 ascent 차이가 곧 기준선 사이
        거리다. 글자마다 잉크가 달라 fontBoundingBox 로도 한 번 재 둔다.  */
    const a = ctx.measureText(text);
    ctx.textBaseline = 'alphabetic';
    const b = ctx.measureText(text);
    ctx.textBaseline = keep;
    return {
      ink: b.actualBoundingBoxAscent - a.actualBoundingBoxAscent,
      font: b.fontBoundingBoxAscent - a.fontBoundingBoxAscent,
    };
  }

  function rec(ctx, kind, text, x, y) {
    /* ① 본 캔버스가 아니면 버린다 (그림자 스크래치 · 블러 레이어) */
    if (ctx.canvas !== rt.canvas) return;
    const s = String(text);
    if (s === '') return;
    const m = ctx.measureText(s);
    const sh = baselineShift(ctx, s);
    /* ② CTM 을 같이 적는다 — 기울임/흔들림이 걸린 채로 찍히는 자리가 있다 */
    const t = ctx.getTransform();
    log.push({
      kind,
      text: s,
      font: ctx.font,
      align: ctx.textAlign,
      baseline: ctx.textBaseline,
      letterSpacing: ctx.letterSpacing ?? '0px',
      alpha: Math.round(ctx.globalAlpha * 1000) / 1000,
      x, y,
      ctm: [t.a, t.b, t.c, t.d, t.e, t.f],
      /* 전진폭(advance) — AE 의 자간과 맞대 볼 값 */
      advance: m.width,
      inkLeft: m.actualBoundingBoxLeft,
      inkRight: m.actualBoundingBoxRight,
      inkAscent: m.actualBoundingBoxAscent,
      inkDescent: m.actualBoundingBoxDescent,
      fontAscent: m.fontBoundingBoxAscent,
      fontDescent: m.fontBoundingBoxDescent,
      /* 알파벳 베이스라인으로 옮기는 보정값 (AE 점 텍스트가 쓰는 기준) */
      toAlphabetic: sh === 0 ? { ink: 0, font: 0 } : sh,
    });
  }

  P.fillText = function (text, x, y, mw) {
    if (log) { try { rec(this, 'fill', text, x, y); } catch (e) { /* 재기 실패는 렌더를 막지 않는다 */ } }
    return mw === undefined ? oFill.call(this, text, x, y) : oFill.call(this, text, x, y, mw);
  };
  P.strokeText = function (text, x, y, mw) {
    if (log) { try { rec(this, 'stroke', text, x, y); } catch (e) { /* 위와 같다 */ } }
    return mw === undefined ? oStroke.call(this, text, x, y) : oStroke.call(this, text, x, y, mw);
  };

  /** 한 층만 그리고 그 층이 찍은 글자를 돌려준다. layer 가 null 이면 전부 */
  window.__textAt = (frame, layer) => {
    const keep = rt.pass;
    rt.pass = layer == null ? null : { chart: false, layers: [layer] };
    log = [];
    try { rt.renderFrame(frame); } finally { rt.pass = keep; }
    const out = log;
    log = null;
    return out;
  };
}

/* ── 바깥 ─────────────────────────────────────────────────────────── */

async function openPage(stage, { config, sceneId, width, height }) {
  const page = await stage.browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  const url = `${stage.server.origin}/src/render/scene.html?config=${encodeURIComponent(config)}&scene=${encodeURIComponent(sceneId)}`;
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__ready === true || window.__error, null, { timeout: 30000 });
  const err = await page.evaluate(() => window.__error);
  if (err) throw new Error(`씬 로딩 실패 (${sceneId}):\n${err}`);
  const meta = await page.evaluate(() => window.__scene);
  await page.evaluate(installProbe);
  return { page, meta };
}

/**
 * 컷 하나의 글자 치수를 모은다.
 * 레이어마다 **그 층이 실제로 글자를 찍는 프레임**을 찾아 거기서 잰다 — 등장 중에는
 * 알파가 0 이라 안 찍히는 층이 있다.
 */
async function measureCut(stage, { config, sceneId, layers, width, height }) {
  const { page, meta } = await openPage(stage, { config, sceneId, width, height });
  const total = meta.totalFrames;
  /* 훑을 프레임: 고르게 9곳 + 끝에서 두 번째. 등장·퇴장에 걸쳐도 하나는 걸린다 */
  const probes = [];
  for (let k = 1; k <= 9; k++) probes.push(Math.round((total - 1) * (k / 10)));
  probes.push(total - 2);
  const out = [];
  for (let i = 0; i < layers; i++) {
    let best = null;
    for (const f of probes) {
      const calls = await page.evaluate(([fr, ly]) => window.__textAt(fr, ly), [f, i]);
      if (!calls.length) continue;
      /* 알파가 가장 큰 프레임을 고른다 — 완전히 자리 잡은 모습이다 */
      const a = Math.max(...calls.map((c) => c.alpha));
      if (!best || a > best.alpha) best = { frame: f, alpha: a, calls };
      if (a >= 0.999) break;
    }
    if (best) out.push({ layer: i, frame: best.frame, calls: best.calls });
  }
  await page.close();
  return { id: sceneId, totalFrames: total, layers: out };
}

/**
 * 프로젝트 전체를 재서 `{ 컷id: { 레이어번호: [호출…] } }` 로 돌려준다.
 * scene-export 가 이걸 불러 레이어에 붙인다 — 좌표와 글자 치수가 한 번에 나가야
 * "재는 걸 깜빡해서 조용히 비는" 일이 없다.
 */
export async function measureProject(config, project) {
  const map = {};
  await CAP.withStage(ROOT, async (stage) => {
    for (const s of project.scenes) {
      const r = await measureCut(stage, {
        config, sceneId: s.id, layers: (s.layers ?? []).length,
        width: project.width, height: project.height,
      });
      const byLayer = {};
      for (const L of r.layers) byLayer[L.layer] = L.calls;
      map[s.id] = byLayer;
    }
  });
  return map;
}

async function main() {
  const argv = process.argv.slice(2);
  const config = argv[0];
  if (!config) {
    console.error('쓰기: node tools/ae/text-metrics.mjs <씬파일> [<컷id> | --all] [--out <폴더>]');
    process.exit(1);
  }
  const outIx = argv.indexOf('--out');
  const outDir = outIx >= 0 ? argv[outIx + 1] : null;
  const all = argv.includes('--all');
  const only = argv.find((a, i) => i > 0 && !a.startsWith('--') && argv[i - 1] !== '--out');

  const project = (await import(pathToFileURL(path.join(ROOT, config)).href)).default;
  const scenes = project.scenes.filter((s) => (all ? true : s.id === only));
  if (!scenes.length) {
    console.error(`씬을 찾을 수 없습니다: ${only}\n사용 가능: ${project.scenes.map((s) => s.id).join(', ')}`);
    process.exit(1);
  }

  const width = project.width, height = project.height;
  const cuts = [];
  await CAP.withStage(ROOT, async (stage) => {
    for (const s of scenes) {
      const r = await measureCut(stage, {
        config, sceneId: s.id, layers: (s.layers ?? []).length, width, height,
      });
      cuts.push(r);
      const n = r.layers.reduce((a, l) => a + l.calls.length, 0);
      console.log(`  ${s.id.padEnd(22)} 글자를 찍는 층 ${String(r.layers.length).padStart(2)}개 · 호출 ${n}건`);
    }
  });

  const doc = { slug: project.slug ?? path.basename(config, '.scenes.js'), cuts };
  if (outDir) {
    await mkdir(outDir, { recursive: true });
    const f = path.join(outDir, `${doc.slug}.text.json`);
    await writeFile(f, JSON.stringify(doc, null, 1), 'utf8');
    console.log(`\n  → ${f}`);
  } else {
    console.log(JSON.stringify(doc, null, 1));
  }
}

/*  라이브러리로 불러 쓸 때는 CLI 를 돌리지 않는다 (scene-export 가 import 한다) */
if (import.meta.url === pathToFileURL(process.argv[1]).href) await main();
