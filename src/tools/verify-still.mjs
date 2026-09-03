#!/usr/bin/env node
// 정지 검증 (차12 r13): 클립의 두 시각 프레임을 뽑아 md5 를 비교한다.
// 등장 연출 창 밖의 두 시각이 같으면 그 구간에서 화면이 완전 정지라는 뜻이다.
//   node src/tools/verify-still.mjs <mp4> --at t1,t2[,t3...]
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';

const require = createRequire(import.meta.url);
const ffmpeg = require('ffmpeg-static');

const file = process.argv[2];
const i = process.argv.indexOf('--at');
if (!file || i < 0) { console.error('사용법: verify-still.mjs <mp4> --at t1,t2'); process.exit(1); }
const ts = process.argv[i + 1].split(',').map(Number);

const hashes = ts.map((t) => {
  const buf = execFileSync(ffmpeg, ['-hide_banner', '-loglevel', 'error',
    '-ss', String(t), '-i', file, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
    { maxBuffer: 512 * 1024 * 1024 });
  return createHash('md5').update(buf).digest('hex');
});
const same = hashes.every((h) => h === hashes[0]);
console.log(`${file}  ${ts.join(' / ')}s → ${same ? '동일 (정지 확인)' : '다름!'}`);
for (let k = 0; k < ts.length; k++) console.log(`  t=${ts[k]}  ${hashes[k]}`);
process.exit(same ? 0 : 1);
