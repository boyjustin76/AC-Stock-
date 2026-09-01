#!/usr/bin/env node
/**
 * 차명12 인트로+후킹 **병합 클립(intro-hook)** 을 레이어별로 렌더한다.
 *
 *   node tools/render-cmg12-layers.mjs
 *
 * [2026-09-01 갱신] 인트로 4컷 + 후킹 2컷이 연속 클립 1개로 병합됐다 (룰북 ⑬,
 * scenes/cmg12-cross.build.js). 층마다 파일이 정확히 1개(intro-hook) 나온다.
 * 결과는 `out/cmg12/layers/<번호>_<층>/intro-hook.<확장자>`.
 * `out/` 은 gitignore 라 저장소에 안 올라간다. 다시 만들면 되므로 커밋하지 않는다.
 *
 * 층 순서 = 트랙/컴포지션 쌓는 순서 (아래→위). **tag(버튼)가 최상위다 — 팀장 규칙 ⑭.**
 * 캔들 층만 불투명(mp4)이다 — 스택의 바닥이라 흰 배경을 깔아야 한다.
 * 나머지 넷은 알파(QuickTime RLE .mov). 프리미어·AE 가 알파를 확실히 읽는 코덱이다.
 * webm(VP9 알파)이 훨씬 작지만 프리미어에서 알파가 안 잡히는 경우가 있어 쓰지 않는다.
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const JOBS = [
  { layer: 'candle', dir: '1_candle', format: 'mp4', 설명: '캔들 + 흰 배경 (스택의 바닥)' },
  { layer: 'ma', dir: '2_ma', format: 'alpha', 설명: '5·20 이평선' },
  { layer: 'mark', dir: '3_mark', format: 'alpha', 설명: '강조원 · 손실 밴드 · 진입선 · 큰 ✕' },
  { layer: 'text', dir: '4_text', format: 'alpha', 설명: '글자 라벨 · 밑줄' },
  { layer: 'tag', dir: '5_tag', format: 'alpha', 설명: '매수/매도/손절 버튼 — 최상위 (팀장 규칙 ⑭)' },
];

let failed = 0;
for (const j of JOBS) {
  const args = [
    'src/cli.mjs',
    '--config', `scenes/cmg12-layer-${j.layer}.scenes.js`,
    '--format', j.format,
    '--out', `out/cmg12/layers/${j.dir}`,
  ];
  args.push('--all');

  console.log(`\n■ ${j.dir}  ${j.설명}  [${j.format}]`);
  const r = spawnSync(process.execPath, args, { cwd: ROOT, stdio: 'inherit' });
  if (r.status !== 0) {
    console.error(`  실패: ${j.layer} (exit ${r.status})`);
    failed++;
  }
}

console.log(failed ? `\n${failed}개 층이 실패했다.` : '\n다섯 층 전부 완료. 이제 프리미어 조립 잡을 돌리면 된다:\n  tools/premiere/run.ps1 -Job m6_build\n');
process.exit(failed ? 1 : 0);
