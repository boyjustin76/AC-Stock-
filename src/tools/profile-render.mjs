/* ── 검토 ──
 * 검토내용: 조각 측정은 유효하나 ffmpeg 경합이 빠져 실전(90.2ms/f)과 34ms 차이 — 총평가는 exp-capture.mjs 의 실전 루프 수치를 쓸 것. toDataURL 13.1ms 는 문자열 전송 제외값이라 실전은 23.6ms.
 * 타임코드: 2026-08-27 19:42 KST
 * 검토자: Fable 5 Max
 */
/**
 * 렌더 한 프레임이 어디에 시간을 쓰는지 쪼개서 잰다.
 *
 * benchmark 테이블에는 총 시간만 있어서 "왜 느린가" 를 답할 수 없었다.
 * 이 스크립트는 한 프레임을 네 조각으로 나눠 재고, 지금 쓰는 방식 말고
 * 다른 캡처 경로 두 가지도 같이 재서 비교한다.
 *
 *   node src/tools/profile-render.mjs [씬ID] [프레임수]
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { withStage } from '../render/capture.mjs';
import { startEncoder } from '../render/encode.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const CONFIG = 'scenes/cmg-20ma-runner.scenes.js';
const SCENE = process.argv[2] || null;
const N = Number(process.argv[3] || 120);

const ms = () => Number(process.hrtime.bigint() / 1000000n);

await withStage(ROOT, async ({ server, browser }) => {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const url = `${server.origin}/src/render/scene.html?config=${encodeURIComponent(CONFIG)}${SCENE ? `&scene=${SCENE}` : ''}`;
  const t0 = ms();
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__ready === true || window.__error, null, { timeout: 30000 });
  const meta = await page.evaluate(() => window.__scene);
  const bootMs = ms() - t0;
  console.log(`씬 ${meta.id}  ${meta.width}x${meta.height}  총 ${meta.totalFrames}프레임  기동 ${bootMs}ms`);

  const clip = { x: 0, y: 0, width: meta.width, height: meta.height };
  const frames = Math.min(N, meta.totalFrames);

  // 1) 캔버스 그리기만
  let t = ms();
  for (let f = 0; f < frames; f++) await page.evaluate((n) => window.__renderFrame(n), f);
  const drawMs = ms() - t;

  // 2) 그리기 + PNG 스크린샷
  t = ms();
  let bytes = 0;
  const bufs = [];
  for (let f = 0; f < frames; f++) {
    await page.evaluate((n) => window.__renderFrame(n), f);
    const b = await page.screenshot({ type: 'png', clip, animations: 'disabled', scale: 'css' });
    bytes += b.length;
    if (bufs.length < frames) bufs.push(b);
  }
  const shotMs = ms() - t;

  // 3) 이미 뜬 PNG 를 ffmpeg 에 흘려 넣기만.
  //    지금 쓰는 -preset slow 말고 빠른 프리셋도 같이 재서 값이 얼마나 되는지 본다.
  //    이건 프리미어로 들어가는 중간 소스라 최종 업로드본만큼 조일 이유가 없다.
  const encRuns = {};
  for (const preset of ['slow', 'medium', 'fast', 'veryfast']) {
    const out = path.join(ROOT, `out/_profile-${preset}.mp4`);
    const enc = startEncoder({ format: 'mp4', fps: meta.fps, fpsExpr: meta.fpsExpr,
      outFile: out, width: meta.width, height: meta.height, preset });
    const t2 = ms();
    for (const b of bufs) await enc.write(b);
    await enc.finish();
    const { size } = await import('node:fs/promises').then((m) => m.stat(out));
    encRuns[preset] = { ms: ms() - t2, bytes: size };
  }
  const encMs = encRuns.slow.ms;

  // 4) 캔버스에서 직접 PNG 를 뽑으면(toDataURL) 스크린샷보다 빠른가
  t = ms();
  for (let f = 0; f < frames; f++) {
    await page.evaluate((n) => {
      window.__renderFrame(n);
      return document.querySelector('canvas').toDataURL('image/png').length;
    }, f);
  }
  const dataUrlMs = ms() - t;

  // 5) CDP 로 캡처하면 (Playwright 왕복 없이)
  const cdp = await page.context().newCDPSession(page);
  t = ms();
  for (let f = 0; f < frames; f++) {
    await page.evaluate((n) => window.__renderFrame(n), f);
    await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  }
  const cdpMs = ms() - t;

  const per = (v) => (v / frames).toFixed(1).padStart(7);
  console.log(`\n  ${frames}프레임 기준, 프레임당 ms`);
  console.log(`    그리기만 (evaluate)          ${per(drawMs)}`);
  console.log(`    그리기 + PNG 스크린샷        ${per(shotMs)}   ← 지금 방식`);
  console.log(`      그중 스크린샷 몫            ${per(shotMs - drawMs)}`);
  console.log(`    ffmpeg 에 흘려 넣기          ${per(encMs)}`);
  console.log(`    canvas.toDataURL             ${per(dataUrlMs)}`);
  console.log(`    CDP captureScreenshot        ${per(cdpMs)}`);
  console.log(`\n  ffmpeg 프리셋별 (프레임당 ms · 결과 크기)`);
  for (const [k, v] of Object.entries(encRuns)) {
    console.log(`    -preset ${k.padEnd(9)} ${(v.ms / frames).toFixed(1).padStart(6)} ms   ${(v.bytes / 1024).toFixed(0).padStart(6)} KB`);
  }
  console.log(`\n  PNG 평균 ${(bytes / frames / 1024).toFixed(0)} KB`);
  console.log(`  지금 방식 실효 ${(1000 / (shotMs / frames)).toFixed(1)} fps`);
  await page.close();
});
