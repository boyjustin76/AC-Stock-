#!/usr/bin/env node
/**
 * AE 납품 꾸러미를 만든다 — **어디에 풀어도 소스를 안 찾아 헤매는** 형태.
 *
 *   node tools/ae/pack.mjs sl-11-4
 *
 * 왜 이 구조인가 —
 *   AE 는 푸티지를 절대경로로 기억하되, 그 경로가 없으면 **프로젝트 파일 기준
 *   상대경로**로 다시 찾는다. 그래서 .aep 와 footage/ 를 나란히 두고 그 관계만
 *   유지하면 폴더째 어디로 옮겨도 "파일 없음" 이 안 뜬다.
 *   (AE 의 Collect Files 를 스크립트로 부르는 공식 API 가 없어 직접 배치한다.)
 *
 * 꾸러미:
 *   <슬러그>/
 *     <슬러그>.aep        컷별 컴포지션
 *     footage/<컷>.mov    차트 바닥 (알파 QuickTime RLE)
 *     읽어보기.txt        프리미어에서 쓰는 법
 */
import { readFileSync, writeFileSync, existsSync, statSync, readdirSync } from 'node:fs';
import path from 'node:path';

const LAB = 'C:/aelab';
const slug = process.argv[2];
if (!slug) { console.error('쓰기: node tools/ae/pack.mjs <슬러그>'); process.exit(1); }

const meta0 = JSON.parse(readFileSync(`${LAB}/ae/${slug}.json`, 'utf8'));
const dir = `${LAB}/pack/${meta0.packName || slug}`;
const aep = `${dir}/${slug}.aep`;
const foot = `${dir}/footage`;
const meta = meta0;

if (!existsSync(aep)) { console.error('aep 이 없다: ' + aep); process.exit(1); }

/* 꾸러미가 온전한지 먼저 본다 — 컷마다 바닥이 하나씩 있어야 한다 */
const missing = meta.cuts.filter((c) => !existsSync(`${foot}/${c.id}.mov`));
if (missing.length) {
  console.error('바닥이 빠졌다: ' + missing.map((c) => c.id).join(', '));
  process.exit(1);
}
const extra = readdirSync(foot).filter((f) => !meta.cuts.some((c) => c.id + '.mov' === f));
if (extra.length) console.log('  (쓰지 않는 파일: ' + extra.join(', ') + ')');

const mb = (n) => (n / 1048576).toFixed(1) + 'MB';
const rows = meta.cuts.map((c) => {
  const s = statSync(`${foot}/${c.id}.mov`).size;
  return `  ${c.id.padEnd(22)} ${String(c.frames).padStart(4)}f  ${(c.frames / meta.fps).toFixed(2).padStart(6)}s   ${mb(s).padStart(8)}`;
}).join('\n');

const readme = `${meta.title}
AE 소스 꾸러미 — ${slug}

이 폴더는 통째로 옮겨야 한다. .aep 이 footage/ 를 상대경로로 찾는다.
따로 떼어 놓으면 AE 가 "파일 없음" 을 띄운다.

─────────────────────────────────────────────
[1] 프리미어로 가져오기
─────────────────────────────────────────────
  파일 > 가져오기 > Adobe Dynamic Link > After Effects 컴포지션 가져오기
    → 이 폴더의 ${slug}.aep 선택
    → 컴포지션 전부 선택 > 확인
    → 프로젝트 패널에서 타임라인으로 드래그

─────────────────────────────────────────────
[2] 고치기
─────────────────────────────────────────────
  클립 우클릭 > 원본 편집  →  After Effects 로 넘어간다
    → 고칠 레이어를 클릭
    → 오른쪽 [속성] 패널에서 **"모양 속성" · "모양 변형"** 두 개만 건드린다
       ("레이어 변형" 은 건드리지 말 것 — 좌표 추적이 깨진다)
    → AE 에서 저장(Ctrl+S)하면 프리미어에 바로 반영된다

  색·굵기·위치·크기·회전이 전부 "모양" 쪽에 있다.
  등장/사라짐 시각은 타임라인의 불투명도 키프레임을 끌면 된다.

─────────────────────────────────────────────
[3] 컴포지션 안에 무엇이 있나
─────────────────────────────────────────────
  차트 카메라   숨김·잠금. 차트 좌표를 나르는 부품이라 건드릴 일이 없다.
                (보려면 타임라인 위 사람 모양 'shy' 아이콘을 누른다)
  차트 바닥     footage/ 의 mov — 캔들·이평선. 알파라 밑에 무엇을 깔아도 된다.
  그 위 레이어  주석. 이름 앞 번호가 **그리는 순서**(작을수록 아래)다.
                버튼(매수·매도·익절·손절)이 항상 맨 위에 온다 — 팀장 규칙 ⑭.

─────────────────────────────────────────────
[4] 규격
─────────────────────────────────────────────
  1080 × 1080 / 30fps
  세이프 에어리어  위 23px · 아래 135px 가림 → 유효 1080 × 922
  글꼴  GmarketSansBold · S-CoreDream-5Medium
        (없으면 AE 가 대체 글꼴로 열어 글자 폭이 달라진다 — 먼저 설치할 것)

─────────────────────────────────────────────
[5] 들어 있는 컷
─────────────────────────────────────────────
${rows}

  ${meta.cuts.length}컷 · 합계 ${(meta.cuts.reduce((a, c) => a + c.frames, 0) / meta.fps).toFixed(2)}초

이 파일들은 저장소의 scenes/${slug}.scenes.js 에서 자동으로 만들어진다.
씬이 바뀌면 사람이 손보는 게 아니라 다시 뽑는다.
`;

writeFileSync(`${dir}/읽어보기.txt`, readme, 'utf8');

const total = [aep, ...meta.cuts.map((c) => `${foot}/${c.id}.mov`)]
  .reduce((a, f) => a + statSync(f).size, 0);
console.log(`\n  ${slug}  준비 완료`);
console.log(`   aep ${mb(statSync(aep).size)} · 바닥 ${meta.cuts.length}개 · 합계 ${mb(total)}`);
console.log(`   → ${dir}\n`);
