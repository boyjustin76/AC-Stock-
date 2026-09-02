#!/usr/bin/env node
/**
 * AE 컴포지션과 렌더러를 **픽셀로** 맞대 본다.
 *
 *   node tools/ae/diff.mjs cut4-buy 30,90,120,155
 *
 * "AE 에서 잘 나온다" 는 증거가 아니다. 렌더러가 낸 같은 프레임과 대조해야 안다.
 * 파일럿에서 셰이프 그룹 순서가 뒤집힌 것도, 라벨판이 안 그려진 것도 눈이 아니라
 * 이 대조가 잡았다.
 *
 * 준비물
 *   AE 프레임   C:/aelab/ae/frames/<컷>/f<N>.png        (b3_frame 잡이 뽑는다)
 *   렌더러 프레임 C:/aelab/ae/ref/seq/<컷>/<컷>_<NNNNN>.png
 *                 node src/cli.mjs --config <씬> --scene <컷> --format png --out C:/aelab/ae/ref
 *
 * AE 프레임은 바닥이 알파라 **흰 바탕에 얹어** 비교한다(렌더러 테마 배경이 #FFFFFF).
 */
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import ffmpeg from 'ffmpeg-static';

const LAB = 'C:/aelab/ae';
const cut = process.argv[2];
const frames = (process.argv[3] ?? '30,90,120,155').split(',').map(Number);
if (!cut) { console.error('쓰기: node tools/ae/diff.mjs <컷id> [프레임,쉼표로]'); process.exit(1); }

const AE = `${LAB}/frames/${cut}`;
const REF = `${LAB}/ref/seq/${cut}`;
const OUT = `${LAB}/diff/${cut}`;
mkdirSync(OUT, { recursive: true });

const ff = (args) => spawnSync(ffmpeg, args, { encoding: 'utf8' });
const pad5 = (n) => String(n).padStart(5, '0');

console.log(`\n  ${cut}  —  AE vs 렌더러\n`);
console.log('   프레임    PSNR       평균오차   최대   >8차이   >64차이   판정');

let worst = 0, worstPct = 0;
for (const f of frames) {
  const a = `${AE}/f${f}.png`;
  const r = `${REF}/${cut}_${pad5(f)}.png`;
  if (!existsSync(a)) { console.log(`   f${f}  AE 프레임이 없다: ${a}`); continue; }
  if (!existsSync(r)) { console.log(`   f${f}  렌더러 프레임이 없다: ${r}`); continue; }

  /*  알파를 흰 바탕에 얹는다.
      ⚠ AE 의 saveFrameToPng 는 **알파가 미리 곱해진(premultiplied)** PNG 를 낸다.
      그냥 얹으면 반투명한 곳이 전부 검정 쪽으로 어두워진다 — 9% 주황 띠가
      정확히 '검정 9%' 값으로 나와서 잡았다.
      unpremultiply 로 되돌린 뒤 얹으면 맞긴 한데, 8비트에서 나눴다 다시 곱하느라
      1레벨쯤 반올림 오차가 생긴다. 미리 곱해진 채로 바로 더하는 게 정확하다:
          결과 = 미리곱한색 + 흰바탕 × (1 - 알파)                                   */
  const flat = `${OUT}/ae_f${f}.png`;
  const bg = "255*(1-alpha(X,Y)/255)";
  ff(['-y', '-hide_banner', '-loglevel', 'error', '-i', a,
      '-vf', `format=rgba,geq=r='r(X,Y)+${bg}':g='g(X,Y)+${bg}':b='b(X,Y)+${bg}':a=255,format=rgb24`,
      '-frames:v', '1', flat]);

  const p = ff(['-hide_banner', '-i', flat, '-i', r, '-filter_complex', 'psnr', '-f', 'null', '-']);
  const psnr = (p.stderr.match(/average:([0-9.]+)/) ?? [])[1];

  const s = ff(['-hide_banner', '-loglevel', 'info', '-i', flat, '-i', r, '-filter_complex',
    '[0:v]format=rgb24[a];[1:v]format=rgb24[b];[a][b]blend=all_mode=difference,signalstats,metadata=print',
    '-f', 'null', '-']);
  const avg = Number((s.stderr.match(/YAVG=([0-9.]+)/) ?? [])[1] ?? 0);
  const max = Number((s.stderr.match(/YMAX=([0-9]+)/) ?? [])[1] ?? 0);
  worst = Math.max(worst, avg);

  /*  AE | 렌더러 | 차이(20배 증폭) — 눈으로 원인을 찾을 때 쓴다.
      colorlevels 로 0~12/255 를 0~255 로 편다. contrast 로 만졌더니 1/255 짜리
      차이가 흰 화면에 묻혀 안 보였다.
      입력 패드는 한 번만 쓸 수 있어 split 으로 갈라야 한다 — 두 번 쓰면 ffmpeg 이
      실패하는데 조용해서, 낡은 파일을 새 결과로 착각하고 한참 봤다.               */
  const tri = ff(['-y', '-hide_banner', '-loglevel', 'error', '-i', flat, '-i', r, '-filter_complex',
      '[0:v]split=2[a0][a1];[1:v]split=2[b0][b1];'
      + '[a0]scale=540:540[x];[b0]scale=540:540[y];'
      + '[a1][b1]blend=all_mode=difference,colorlevels=rimax=0.05:gimax=0.05:bimax=0.05,'
      + 'negate,scale=540:540[z];[x][y][z]hstack=inputs=3',
      `${OUT}/tri_f${f}.png`]);
  if (tri.status !== 0) console.log(`   f${f} 대조 이미지 실패: ${tri.stderr.trim().split('\n').pop()}`);

  /*  평균오차보다 **몇 %가 얼마나 다른가** 가 읽기 쉽다.
      가장자리 안티에일리어싱은 적은 픽셀이 크게 다르므로 평균은 작고 PSNR 은 나쁘다.  */
  const over = (t) => {
    const q = ff(['-hide_banner', '-loglevel', 'info', '-i', flat, '-i', r, '-filter_complex',
      `[0:v]format=gray[a];[1:v]format=gray[b];[a][b]blend=all_mode=difference,`
      + `geq=lum='if(gt(lum(X,Y),${t}),255,0)',signalstats,metadata=print`, '-f', 'null', '-']);
    return Number((q.stderr.match(/YAVG=([0-9.]+)/) ?? [])[1] ?? 0) / 255 * 100;
  };
  const o8 = over(8), o64 = over(64);
  worstPct = Math.max(worstPct, o8);

  /*  크게 다른 픽셀만 남긴 지도 — 원인이 어디 있는지 한눈에 보인다.
      dilation 은 **밝은 쪽**을 넓히므로, 반전은 넓힌 뒤에 해야 한다(반대로 했다가 침식됐다).  */
  ff(['-y', '-hide_banner', '-loglevel', 'error', '-i', flat, '-i', r, '-filter_complex',
      `[0:v]format=gray[a];[1:v]format=gray[b];[a][b]blend=all_mode=difference,`
      + `geq=lum='if(gt(lum(X,Y),64),255,0)',dilation,dilation,negate`, `${OUT}/hot_f${f}.png`]);

  const verdict = o8 < 0.5 ? '거의 같다' : o8 < 3 ? '가장자리만' : '**다르다**';
  console.log(`   f${String(f).padEnd(6)} ${String(psnr).padStart(7)}dB  ${avg.toFixed(3).padStart(8)}  ${String(max).padStart(6)}`
            + `  ${o8.toFixed(2).padStart(6)}%  ${o64.toFixed(2).padStart(6)}%   ${verdict}`);
}
console.log(`\n   최악: 8 넘게 다른 픽셀 ${worstPct.toFixed(2)}%`);
console.log(`   대조 → ${OUT}/tri_f*.png · 크게 다른 곳 → ${OUT}/hot_f*.png\n`);
