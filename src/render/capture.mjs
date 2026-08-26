/** Playwright 로 씬을 프레임 단위 캡처해 인코더로 흘려 보낸다. */
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { startServer } from './server.mjs';
import { startEncoder, FORMATS } from './encode.mjs';

/**
 * 실행할 크로미움 찾기.
 * Playwright 가 기대하는 빌드가 없는 환경(미리 설치된 브라우저만 있는 컨테이너 등)에서도
 * 다운로드 없이 동작하도록, 환경변수 → 사전 설치 경로 → 기본값 순으로 찾는다.
 */
function resolveChromium() {
  const candidates = [
    process.env.CHROMIUM_PATH,
    '/opt/pw-browsers/chromium',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
  ].filter(Boolean);
  for (const c of candidates) {
    try {
      if (existsSync(c)) return c;
    } catch { /* 무시하고 다음 후보 */ }
  }
  return undefined; // Playwright 가 관리하는 기본 브라우저 사용
}

export async function withStage(root, fn) {
  const server = await startServer(root);
  const executablePath = resolveChromium();
  const browser = await chromium.launch({
    executablePath,
    args: [
      '--force-color-profile=srgb',
      '--disable-lcd-text',
      '--font-render-hinting=none',
      '--hide-scrollbars',
      '--force-device-scale-factor=1',
    ],
  });
  try {
    return await fn({ server, browser });
  } finally {
    await browser.close();
    await server.close();
  }
}

async function openScene({ server, browser }, { config, sceneId, width, height }) {
  const page = await browser.newPage({
    viewport: { width, height },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('response', (r) => {
    // favicon 같은 부수적 요청은 무시하고, 폰트/모듈 누락만 잡는다
    if (r.status() >= 400 && !r.url().endsWith('/favicon.ico')) {
      errors.push(`${r.status()} ${r.url()}`);
    }
  });
  page.on('console', (m) => {
    if (m.type() === 'error' && !m.text().includes('favicon')) errors.push(m.text());
  });
  const url = `${server.origin}/src/render/scene.html?config=${encodeURIComponent(config)}${sceneId ? `&scene=${encodeURIComponent(sceneId)}` : ''}`;
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__ready === true || window.__error, null, { timeout: 30000 });
  const err = await page.evaluate(() => window.__error);
  if (err) throw new Error(`씬 로딩 실패 (${sceneId}):\n${err}`);
  if (errors.length) throw new Error(`페이지 오류 (${sceneId}):\n${errors.join('\n')}`);
  const meta = await page.evaluate(() => window.__scene);
  return { page, meta, errors };
}

/**
 * 씬 하나를 영상 파일로 렌더한다.
 * @returns {{file:string, frames:number, ms:number}}
 */
export async function renderScene(stage, opts) {
  const {
    config, sceneId, outDir, format = 'mp4', width, height, onProgress,
  } = opts;
  const { page, meta } = await openScene(stage, { config, sceneId, width, height });
  const fmt = FORMATS[format];
  await mkdir(outDir, { recursive: true });
  const outFile = path.join(outDir, `${meta.id}.${fmt.ext}`);

  const enc = startEncoder({
    format,
    fps: meta.fps,
    fpsExpr: meta.fpsExpr,
    outFile,
    width: meta.width,
    height: meta.height,
  });

  const started = Date.now();
  const clip = { x: 0, y: 0, width: meta.width, height: meta.height };
  for (let f = 0; f < meta.totalFrames; f++) {
    await page.evaluate((n) => window.__renderFrame(n), f);
    const buf = await page.screenshot({
      type: 'png',
      clip,
      omitBackground: fmt.alpha,
      animations: 'disabled',
      scale: 'css',
    });
    await enc.write(buf);
    if (onProgress && (f % 15 === 0 || f === meta.totalFrames - 1)) {
      onProgress(f + 1, meta.totalFrames);
    }
  }
  await enc.finish();
  await page.close();
  return { file: outFile, frames: meta.totalFrames, ms: Date.now() - started, meta };
}

/** 씬을 PNG 시퀀스로 렌더 (알파 포함, 편집 프로그램 임포트용) */
export async function renderSequence(stage, opts) {
  const { config, sceneId, outDir, width, height, transparent = false, onProgress } = opts;
  const { page, meta } = await openScene(stage, { config, sceneId, width, height });
  const dir = path.join(outDir, meta.id);
  await mkdir(dir, { recursive: true });
  const clip = { x: 0, y: 0, width: meta.width, height: meta.height };
  for (let f = 0; f < meta.totalFrames; f++) {
    await page.evaluate((n) => window.__renderFrame(n), f);
    const buf = await page.screenshot({ type: 'png', clip, omitBackground: transparent, scale: 'css' });
    await writeFile(path.join(dir, `${meta.id}_${String(f).padStart(5, '0')}.png`), buf);
    if (onProgress && f % 15 === 0) onProgress(f + 1, meta.totalFrames);
  }
  await page.close();
  return { dir, frames: meta.totalFrames, meta };
}

/** 확인용 스틸컷 몇 장만 뽑는다 */
export async function renderStills(stage, opts) {
  const { config, sceneId, outDir, width, height, count = 5, transparent = false } = opts;
  const { page, meta } = await openScene(stage, { config, sceneId, width, height });
  await mkdir(outDir, { recursive: true });
  const files = [];
  const clip = { x: 0, y: 0, width: meta.width, height: meta.height };
  for (let k = 0; k < count; k++) {
    const f = Math.min(meta.totalFrames - 1, Math.round((meta.totalFrames - 1) * (k / Math.max(1, count - 1))));
    await page.evaluate((n) => window.__renderFrame(n), f);
    const buf = await page.screenshot({ type: 'png', clip, omitBackground: transparent, scale: 'css' });
    const file = path.join(outDir, `${meta.id}_t${(f / meta.fps).toFixed(2)}s.png`);
    await writeFile(file, buf);
    files.push(file);
  }
  await page.close();
  return { files, meta };
}

export async function listScenes(stage, { config, width, height }) {
  const { page } = await openScene(stage, { config, sceneId: null, width, height });
  const url = `${stage.server.origin}/${config}`;
  const scenes = await page.evaluate(async (u) => {
    const m = await import(u);
    return m.default.scenes.map((s) => ({ id: s.id, name: s.name, duration: s.duration }));
  }, url);
  await page.close();
  return scenes;
}
