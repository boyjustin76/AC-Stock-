/* ── 검토 ──
 * 검토내용: 이번 리뷰의 판정 도구(직접 작성). 픽셀·mp4 md5 동일성 증명, raw 경로 746ms/f 탈락 판정, 프리셋 결정의 근거를 만들었다. 재검증은 node src/tools/exp-capture.mjs 120 3.
 * 타임코드: 2026-08-27 19:42 KST
 * 검토자: Fable 5 Max
 */
/**
 * 캡처 경로별 실전 루프 실측 + 픽셀 동일성 대조.
 *
 * profile-render.mjs 는 조각(그리기/캡처/인코드)을 따로 쟀다. 그런데 실제 루프에서는
 * ffmpeg 이 별도 프로세스로 같이 돌며 캡처와 CPU 를 다투므로, 합이 조각의 합과 다르다
 * (실측: 조각 합 56ms vs 전체 렌더 97ms/프레임). 여기서는 변형별로
 * '그리기→캡처→인코드' 루프를 끝까지 돌려 벽시계로 재고,
 * 캡처 경로를 바꿔도 픽셀이 정말 같은지까지 대조한다.
 *
 *   node src/tools/exp-capture.mjs [프레임수=120] [반복=3]
 *
 * 변형:
 *   shot     지금 방식. page.screenshot({type:'png'})
 *   dataurl  canvas.toDataURL — base64 문자열을 노드로 가져와 디코드 (전송비 포함)
 *   raw      getImageData → localhost HTTP POST → ffmpeg rawvideo (PNG 인코드/디코드 둘 다 없음)
 */
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, stat, readFile } from 'node:fs/promises';
import ffmpegPath from 'ffmpeg-static';
import { withStage } from '../render/capture.mjs';
import { startEncoder } from '../render/encode.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const N = Number(process.argv[2] || 120);
const RUNS = Number(process.argv[3] || 3);
const OUT = path.join(ROOT, 'out/_exp');
const ms = () => Number(process.hrtime.bigint() / 1000000n);
const md5 = (b) => createHash('md5').update(b).digest('hex').slice(0, 12);

async function openScene(browser, origin, config) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const t0 = ms();
  await page.goto(`${origin}/src/render/scene.html?config=${encodeURIComponent(config)}`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__ready === true || window.__error, null, { timeout: 30000 });
  const err = await page.evaluate(() => window.__error);
  if (err) throw new Error(err);
  const meta = await page.evaluate(() => window.__scene);
  const bootMs = ms() - t0;
  // 페이지 쪽 캡처 도우미 설치
  await page.evaluate(() => {
    const rt = window.__runtime;
    window.__grabRaw = async (n, url) => {
      rt.renderFrame(n);
      const d = rt.ctx.getImageData(0, 0, rt.w, rt.h);
      const r = await fetch(url, { method: 'POST', body: d.data });
      if (!r.ok) throw new Error('upload ' + r.status);
    };
    window.__grabDataUrl = (n) => {
      rt.renderFrame(n);
      return document.querySelector('canvas').toDataURL('image/png');
    };
  });
  return { page, meta, bootMs };
}

/** PNG buf → ffmpeg 디코드 → RGBA raw Buffer */
function pngRaw(buf) {
  return new Promise((resolve, reject) => {
    const p = spawn(ffmpegPath, ['-hide_banner', '-loglevel', 'error', '-i', 'pipe:0', '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1']);
    const chunks = [];
    p.stdout.on('data', (d) => chunks.push(d));
    let err = '';
    p.stderr.on('data', (d) => (err += d));
    p.on('close', (c) => (c === 0 ? resolve(Buffer.concat(chunks)) : reject(new Error('png decode: ' + err))));
    p.stdin.end(buf);
  });
}

function diffStats(a, b) {
  if (a.length !== b.length) return { max: 255, cnt: -1, note: `길이 다름 ${a.length} vs ${b.length}` };
  let max = 0, cnt = 0;
  for (let i = 0; i < a.length; i++) {
    const d = Math.abs(a[i] - b[i]);
    if (d) { cnt++; if (d > max) max = d; }
  }
  return { max, cnt };
}

/** rawvideo(rgba) 입력 인코더 — PNG 단계가 아예 없다. 출력 인자는 encode.mjs 의 mp4 와 동일 */
function startRawEncoder({ fps, fpsExpr, outFile, width, height, preset }) {
  const rate = fpsExpr ?? String(fps);
  const args = ['-y', '-hide_banner', '-loglevel', 'error',
    '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${width}x${height}`, '-framerate', rate, '-i', 'pipe:0',
    '-r', rate,
    '-c:v', 'libx264', '-preset', preset, '-crf', '12',
    '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.2',
    '-x264-params', `keyint=${Math.round(fps)}:min-keyint=${Math.round(fps / 2)}`,
    '-movflags', '+faststart',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
    outFile];
  const proc = spawn(ffmpegPath, args, { stdio: ['pipe', 'ignore', 'pipe'] });
  proc.stdin.setMaxListeners(0);
  let err = '';
  proc.stderr.on('data', (d) => (err += d));
  return {
    write: (buf) => new Promise((resolve, reject) => {
      if (!proc.stdin.write(buf)) proc.stdin.once('drain', resolve); else resolve();
      proc.stdin.once('error', reject);
    }),
    finish: () => new Promise((resolve, reject) => {
      proc.on('close', (c) => (c === 0 ? resolve() : reject(new Error(err.slice(-2000)))));
      proc.stdin.end();
    }),
  };
}

// ---- 브라우저 → 노드 프레임 업로드 서버 (raw 경로용) ----
let sink = null;
const up = http.createServer((req, res) => {
  const cors = { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST', 'access-control-allow-headers': '*' };
  if (req.method === 'OPTIONS') { res.writeHead(204, cors).end(); return; }
  const chunks = [];
  req.on('data', (d) => chunks.push(d));
  req.on('end', async () => {
    try { await sink(Buffer.concat(chunks)); res.writeHead(200, cors).end('ok'); }
    catch (e) { res.writeHead(500, cors).end(String(e)); }
  });
});
await new Promise((r) => up.listen(0, '127.0.0.1', r));
const upUrl = `http://127.0.0.1:${up.address().port}/frame`;

/** 변형 하나를 실전 루프로 frames 만큼 돌린다 */
async function runVariant(page, meta, cap, preset, frames, outFile) {
  const clip = { x: 0, y: 0, width: meta.width, height: meta.height };
  const enc = cap === 'raw'
    ? startRawEncoder({ fps: meta.fps, fpsExpr: meta.fpsExpr, outFile, width: meta.width, height: meta.height, preset })
    : startEncoder({ format: 'mp4', fps: meta.fps, fpsExpr: meta.fpsExpr, outFile, width: meta.width, height: meta.height, preset });
  if (cap === 'raw') sink = (b) => enc.write(b);
  const t0 = ms();
  for (let f = 0; f < frames; f++) {
    if (cap === 'shot') {
      await page.evaluate((n) => window.__renderFrame(n), f);
      await enc.write(await page.screenshot({ type: 'png', clip, animations: 'disabled', scale: 'css' }));
    } else if (cap === 'dataurl') {
      const s = await page.evaluate((n) => window.__grabDataUrl(n), f);
      await enc.write(Buffer.from(s.slice(s.indexOf(',') + 1), 'base64'));
    } else {
      await page.evaluate(([n, u]) => window.__grabRaw(n, u), [f, upUrl]);
    }
  }
  await enc.finish();
  const dt = ms() - t0;
  const { size } = await stat(outFile);
  return { dt, size };
}

await mkdir(OUT, { recursive: true });
await withStage(ROOT, async ({ server, browser }) => {
  const { page, meta, bootMs } = await openScene(browser, server.origin, 'scenes/cmg-20ma-runner.scenes.js');
  console.log(`씬 ${meta.id}  ${meta.width}x${meta.height}  기동 ${bootMs}ms\n`);

  if (!process.env.SKIP_EQ) {
  // ---- 1) 픽셀 동일성: screenshot vs toDataURL vs getImageData ----
  console.log('== 픽셀 동일성 (불투명 씬) ==');
  const clip = { x: 0, y: 0, width: meta.width, height: meta.height };
  for (const f of [0, 59, 119]) {
    await page.evaluate((n) => window.__renderFrame(n), f);
    const shot = await pngRaw(await page.screenshot({ type: 'png', clip, animations: 'disabled', scale: 'css' }));
    const s = await page.evaluate((n) => window.__grabDataUrl(n), f);
    const durl = await pngRaw(Buffer.from(s.slice(s.indexOf(',') + 1), 'base64'));
    let rawBuf = null; sink = async (b) => { rawBuf = b; };
    await page.evaluate(([n, u]) => window.__grabRaw(n, u), [f, upUrl]);
    const m = [md5(shot), md5(durl), md5(rawBuf)];
    const same = m[0] === m[1] && m[1] === m[2];
    let extra = '';
    if (!same) {
      const d1 = diffStats(shot, durl); const d2 = diffStats(shot, rawBuf);
      extra = `  shot↔dataurl max${d1.max}/${d1.cnt}px  shot↔raw max${d2.max}/${d2.cnt}px`;
    }
    console.log(`  f${String(f).padEnd(4)} shot ${m[0]}  dataurl ${m[1]}  raw ${m[2]}  ${same ? '완전 동일' : '다름!'}${extra}`);
  }

  // 알파(투명 배경) 씬도 같은 대조
  console.log('\n== 픽셀 동일성 (투명 씬 thumb-a) ==');
  const ta = await openScene(browser, server.origin, 'scenes/thumb-ch11.scenes.js');
  for (const f of [0, Math.floor(ta.meta.totalFrames / 2)]) {
    await ta.page.evaluate((n) => window.__renderFrame(n), f);
    const shot = await pngRaw(await ta.page.screenshot({ type: 'png', clip, omitBackground: true, animations: 'disabled', scale: 'css' }));
    const s = await ta.page.evaluate((n) => window.__grabDataUrl(n), f);
    const durl = await pngRaw(Buffer.from(s.slice(s.indexOf(',') + 1), 'base64'));
    let rawBuf = null; sink = async (b) => { rawBuf = b; };
    await ta.page.evaluate(([n, u]) => window.__grabRaw(n, u), [f, upUrl]);
    const m = [md5(shot), md5(durl), md5(rawBuf)];
    const same = m[0] === m[1] && m[1] === m[2];
    let extra = '';
    if (!same) {
      const d1 = diffStats(shot, durl); const d2 = diffStats(shot, rawBuf);
      extra = `  shot↔dataurl max${d1.max}/${d1.cnt}px  shot↔raw max${d2.max}/${d2.cnt}px`;
    }
    console.log(`  f${String(f).padEnd(4)} shot ${m[0]}  dataurl ${m[1]}  raw ${m[2]}  ${same ? '완전 동일' : '다름!'}${extra}`);
  }
  await ta.page.close();

  // ---- 2) mp4 결정성: 같은 픽셀을 다른 경로로 넣어도 출력 파일이 같은가 (preset slow, 60프레임) ----
  console.log('\n== mp4 출력 동일성 (60프레임, preset slow) ==');
  for (const cap of ['shot', 'dataurl', 'raw']) {
    const f = path.join(OUT, `det-${cap}.mp4`);
    await runVariant(page, meta, cap, 'slow', 60, f);
    console.log(`  ${cap.padEnd(8)} ${md5(await readFile(f))}`);
  }

  }
  // ---- 3) 실전 루프 시간 (변형 × 반복) ----
  console.log(`\n== 실전 루프: ${N}프레임, ${RUNS}회 반복, 프레임당 ms ==`);
  const variants = (process.env.VARIANTS || 'shot-slow,shot-medium,dataurl-slow,dataurl-medium')
    .split(',').map((s) => s.split('-'));
  for (const [cap, preset] of variants) {
    const times = [];
    let size = 0;
    for (let r = 0; r < RUNS; r++) {
      const f = path.join(OUT, `t-${cap}-${preset}.mp4`);
      const res = await runVariant(page, meta, cap, preset, Math.min(N, meta.totalFrames), f);
      times.push(res.dt / Math.min(N, meta.totalFrames));
      size = res.size;
    }
    const mean = times.reduce((a, b) => a + b) / times.length;
    console.log(`  ${(cap + '+' + preset).padEnd(18)} ${mean.toFixed(1).padStart(6)} ms  (${times.map((t) => t.toFixed(1)).join(' / ')})  → ${(1000 / mean).toFixed(1)} fps · ${(size / 1024).toFixed(0)} KB`);
  }
  await page.close();
});
up.close();
