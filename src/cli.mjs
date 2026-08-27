#!/usr/bin/env node
/* ── 검토 ──
 * 검토내용: --capture(canvas|shot)·--preset 플래그 추가. 컷별 병렬 안내는 폐기 대상 — 캡처 교체 후 단일 프로세스가 4코어를 포화시켜 병렬 이득 소멸(순차 26.8s = 병렬 26.8s).
 * 타임코드: 2026-08-27 19:42 KST
 * 검토자: Fable 5 Max
 */
/**
 * 컷씬 렌더 CLI
 *
 *   npm run render -- --all                  # 전체 씬을 mp4 로
 *   npm run render -- --scene 03-entry       # 특정 씬만
 *   npm run render -- --all --format mov     # ProRes 422 HQ
 *   npm run render -- --scene 04-tpsl --format alpha   # 알파 채널 오버레이용
 *   npm run render -- --all --stills 5       # 확인용 스틸컷만
 *   npm run render -- --all --reel           # 전 씬을 이어 붙인 릴까지 생성
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFile, mkdir } from 'node:fs/promises';
import { withStage, renderScene, renderStills, renderSequence } from './render/capture.mjs';
import { concatFiles } from './render/encode.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const [k, inline] = a.slice(2).split('=');
      const next = argv[i + 1];
      if (inline !== undefined) out[k] = inline;
      else if (next && !next.startsWith('--')) { out[k] = next; i++; }
      else out[k] = true;
    } else out._.push(a);
  }
  return out;
}

const bar = (cur, total, width = 28) => {
  const p = total ? cur / total : 0;
  const n = Math.round(p * width);
  return `[${'█'.repeat(n)}${'·'.repeat(width - n)}] ${String(Math.round(p * 100)).padStart(3)}%`;
};

const fmtDur = (ms) => `${(ms / 1000).toFixed(1)}s`;

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const configRel = (args.config ?? 'scenes/nq-basic.scenes.js').replace(/^\.\//, '');
  const project = (await import(pathToFileURL(path.join(ROOT, configRel)).href)).default;

  const width = Number(args.width ?? project.width);
  const height = Number(args.height ?? project.height);
  const format = String(args.format ?? 'mp4');
  const capture = String(args.capture ?? 'canvas'); // canvas | shot(예전 방식)
  const preset = args.preset ? String(args.preset) : undefined; // x264 preset (mp4 만)
  const outDir = path.resolve(ROOT, String(args.out ?? 'out'));

  let scenes = project.scenes;
  if (args.scene && args.scene !== true) {
    const ids = String(args.scene).split(',');
    scenes = project.scenes.filter((s) => ids.includes(s.id));
    if (!scenes.length) {
      console.error(`씬을 찾을 수 없습니다: ${args.scene}`);
      console.error(`사용 가능: ${project.scenes.map((s) => s.id).join(', ')}`);
      process.exit(1);
    }
  } else if (!args.all) {
    console.log(`\n  ${project.title}  —  ${width}x${height} @ ${project.fps}fps\n`);
    console.log('  씬 목록:');
    for (const s of project.scenes) {
      console.log(`    ${s.id.padEnd(18)} ${String(s.duration).padStart(4)}s   ${s.name}`);
    }
    const total = project.scenes.reduce((a, s) => a + s.duration, 0);
    console.log(`\n  합계 ${total.toFixed(1)}초 / ${project.scenes.length}컷`);
    console.log('\n  렌더:  npm run render -- --all\n');
    return;
  }

  console.log(`\n  ${project.title}`);
  console.log(`  ${width}x${height} @ ${project.fps}fps · ${format} · ${scenes.length}컷\n`);

  await withStage(ROOT, async (stage) => {
    const made = [];
    for (const scene of scenes) {
      const label = `${scene.id}  ${scene.name}`;
      process.stdout.write(`  ▸ ${label}\n`);

      if (args.stills) {
        const { files } = await renderStills(stage, {
          config: configRel, sceneId: scene.id, outDir: path.join(outDir, 'stills'),
          width, height, count: Number(args.stills === true ? 5 : args.stills),
          transparent: format === 'alpha', capture,
        });
        console.log(`    스틸 ${files.length}장 → ${path.relative(ROOT, path.join(outDir, 'stills'))}\n`);
        continue;
      }

      if (format === 'png') {
        const r = await renderSequence(stage, {
          config: configRel, sceneId: scene.id, outDir: path.join(outDir, 'seq'),
          width, height, transparent: !!args.transparent, capture,
          onProgress: (c, t) => process.stdout.write(`\r    ${bar(c, t)}`),
        });
        console.log(`\r    ${bar(1, 1)}  ${r.frames}프레임 → ${path.relative(ROOT, r.dir)}\n`);
        continue;
      }

      const r = await renderScene(stage, {
        config: configRel, sceneId: scene.id, outDir, format, width, height, capture, preset,
        onProgress: (c, t) => process.stdout.write(`\r    ${bar(c, t)}`),
      });
      console.log(`\r    ${bar(1, 1)}  ${r.frames}프레임 · ${fmtDur(r.ms)} → ${path.relative(ROOT, r.file)}\n`);
      made.push(r.file);
    }

    if (args.reel && made.length > 1) {
      const listFile = path.join(outDir, '_reel.txt');
      await writeFile(listFile, made.map((f) => `file '${f.replace(/'/g, "'\\''")}'`).join('\n'));
      const reel = path.join(outDir, `_reel.${path.extname(made[0]).slice(1)}`);
      await concatFiles(listFile, reel);
      console.log(`  ● 릴 완성 → ${path.relative(ROOT, reel)}\n`);
    }
  });
}

main().catch((e) => {
  console.error('\n렌더 실패:', e.message);
  process.exit(1);
});
