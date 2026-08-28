#!/usr/bin/env node
/**
 * 차명12 인트로 4컷을 **레이어별로** 렌더한다.
 *
 *   node tools/render-cmg12-layers.mjs
 *
 * 결과는 `out/cmg12/layers/<번호>_<층>/<컷>.<확장자>` — 약 69MB.
 * `out/` 은 gitignore 라 저장소에 안 올라간다. 1분이면 다시 만들어지므로 커밋하지 않는다.
 * 프리미어 조립 잡(`tools/premiere/jobs/m6_build.jsx`)이 이 경로를 그대로 읽는다.
 *
 * 캔들 층만 불투명(mp4)이다 — 스택의 바닥이라 흰 배경을 깔아야 한다.
 * 나머지 넷은 알파(QuickTime RLE .mov). 프리미어가 알파를 확실히 읽는 코덱이다.
 * webm(VP9 알파)이 훨씬 작지만 프리미어에서 알파가 안 잡히는 경우가 있어 쓰지 않는다.
 *
 * 컷2(`cut2-bed`)는 프리셋 타이틀 카드 뒤에 깔리는 조용한 배경이라 라벨이 하나도 없다.
 * 강조·매수매도·텍스트 층에서는 **그릴 것이 없으므로 렌더하지 않는다.**
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const ALL4 = null; // null = --all
const NOBED = 'cut1-rule,cut3-loss,cut4-signal-only';

const JOBS = [
  { layer: 'candle', dir: '1_candle', format: 'mp4', scene: ALL4, 설명: '캔들 + 흰 배경 (스택의 바닥)' },
  { layer: 'ma', dir: '2_ma', format: 'alpha', scene: ALL4, 설명: '5·20 이평선' },
  { layer: 'mark', dir: '3_mark', format: 'alpha', scene: NOBED, 설명: '강조원 · 손실 밴드 · 진입선' },
  { layer: 'tag', dir: '4_tag', format: 'alpha', scene: NOBED, 설명: '매수/매도 태그' },
  { layer: 'text', dir: '5_text', format: 'alpha', scene: NOBED, 설명: '글자 라벨 · 밑줄' },
];

let failed = 0;
for (const j of JOBS) {
  const args = [
    'src/cli.mjs',
    '--config', `scenes/cmg12-layer-${j.layer}.scenes.js`,
    '--format', j.format,
    '--out', `out/cmg12/layers/${j.dir}`,
  ];
  if (j.scene) args.push('--scene', j.scene);
  else args.push('--all');

  console.log(`\n■ ${j.dir}  ${j.설명}  [${j.format}]`);
  const r = spawnSync(process.execPath, args, { cwd: ROOT, stdio: 'inherit' });
  if (r.status !== 0) {
    console.error(`  실패: ${j.layer} (exit ${r.status})`);
    failed++;
  }
}

console.log(failed ? `\n${failed}개 층이 실패했다.` : '\n다섯 층 전부 완료. 이제 프리미어 조립 잡을 돌리면 된다:\n  tools/premiere/run.ps1 -Job m6_build\n');
process.exit(failed ? 1 : 0);
