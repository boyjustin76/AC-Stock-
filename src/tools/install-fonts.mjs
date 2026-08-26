#!/usr/bin/env node
/**
 * Pretendard / JetBrains Mono 를 시스템 폰트로 등록한다.
 *
 * 렌더 페이지는 @font-face 로도 폰트를 불러오지만, 캔버스 텍스트 폭 계산이
 * 시스템에 폰트가 있을 때 더 안정적이라 리눅스에서는 한 번 등록해 두는 편이 좋다.
 * (macOS / Windows 는 @font-face 만으로 충분하므로 그냥 넘어간다)
 */
import { cp, mkdir, readdir } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

if (process.platform !== 'linux') {
  console.log('리눅스가 아니면 별도 설치가 필요 없습니다. (@font-face 로 로드됨)');
  process.exit(0);
}

const dest = path.join(os.homedir(), '.fonts');
await mkdir(dest, { recursive: true });

const jobs = [
  { dir: 'node_modules/pretendard/dist/public/static', match: (f) => f.endsWith('.otf') },
  {
    dir: 'node_modules/@fontsource/jetbrains-mono/files',
    match: (f) => /^jetbrains-mono-latin-\d00-normal\.woff2$/.test(f),
  },
];

let n = 0;
for (const job of jobs) {
  const src = path.join(ROOT, job.dir);
  let files = [];
  try {
    files = (await readdir(src)).filter(job.match);
  } catch {
    console.warn(`건너뜀 — 경로 없음: ${job.dir}  (npm install 을 먼저 실행하세요)`);
    continue;
  }
  for (const f of files) {
    await cp(path.join(src, f), path.join(dest, f));
    n++;
  }
}

try {
  await run('fc-cache', ['-f']);
} catch {
  console.warn('fc-cache 실행 실패 — fontconfig 가 없어도 렌더에는 지장 없습니다.');
}
console.log(`폰트 ${n}개를 ${dest} 에 등록했습니다.`);
