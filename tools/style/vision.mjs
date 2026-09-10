#!/usr/bin/env node
/**
 * 두 비전 모델에 같은 그림·같은 질문을 던지고 답을 나란히 저장한다.
 *
 *   node tools/style/vision.mjs <그림.png> <질문파일.txt|질문문자열> [--out 답.md] [--only gemini|openai]
 *
 * 왜 MCP 가 아니라 직접 호출인가
 *   판독(읽기)은 "그림 + 질문 → 글" 한 번이라 MCP 가 더해 주는 게 없다. 게다가 세션 중에
 *   붙인 MCP 는 다음 세션부터 보이는 경우가 있어, 오늘 일은 이 스크립트로 확실히 한다.
 *   생성·편집은 @houtini/gemini-mcp 가 맡는다.
 *
 * 키는 환경변수에서만 읽는다 (GEMINI_API_KEY · OPENAI_API_KEY). 어디에도 적지 않는다.
 * 등급: Gemini 무료 → 판독 모델은 된다. OpenAI 미인증 조직 → gpt-4.1 판독은 된다.
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import path from 'node:path';

const argv = process.argv.slice(2);
const img = argv[0];
const qArg = argv[1];
const out = argv.includes('--out') ? argv[argv.indexOf('--out') + 1] : null;
const only = argv.includes('--only') ? argv[argv.indexOf('--only') + 1] : null;
/* --model 로 Gemini 모델을 못 박으면 그것만 쓴다 (두 모델 교차 판독용) */
const pin = argv.includes('--model') ? argv[argv.indexOf('--model') + 1] : null;
if (!img || !qArg) {
  console.error('쓰기: node tools/style/vision.mjs <그림> <질문파일|질문> [--out 답.md] [--only gemini|openai]');
  process.exit(1);
}
const question = existsSync(qArg) ? readFileSync(qArg, 'utf8') : qArg;
const b64 = readFileSync(img).toString('base64');
const mime = img.toLowerCase().endsWith('.jpg') || img.toLowerCase().endsWith('.jpeg') ? 'image/jpeg' : 'image/png';

/* 환경변수는 setx 로 넣은 사용자 값이 현재 셸에 없을 수 있어 레지스트리 폴백을 둔다 */
function envKey(name) {
  if (process.env[name]) return process.env[name];
  try {
    const { execSync } = require('node:child_process');
    return execSync(`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('${name}','User')"`, { encoding: 'utf8' }).trim();
  } catch { return ''; }
}
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

async function gemini() {
  const key = envKey('GEMINI_API_KEY');
  if (!key) return '(GEMINI_API_KEY 없음)';
  /* 판독은 3.1 Pro 가 가장 꼼꼼하다. 무료 등급에서 막히면 3 Flash 로 내려간다. */
  for (const model of (pin ? [pin] : ['gemini-3.1-pro-preview', 'gemini-3-flash-preview', 'gemini-2.5-pro', 'gemini-2.5-flash'])) {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ inline_data: { mime_type: mime, data: b64 } }, { text: question }] }],
        generationConfig: { temperature: 0.2 },
      }),
    });
    const j = await r.json();
    if (r.ok && j.candidates?.[0]?.content?.parts) {
      return `<!-- ${model} -->\n` + j.candidates[0].content.parts.map((p) => p.text ?? '').join('');
    }
    const msg = j.error?.message ?? JSON.stringify(j).slice(0, 300);
    console.error(`  gemini ${model}: ${r.status} ${msg.slice(0, 160)}`);
    if (r.status === 429) await new Promise((res) => setTimeout(res, 8000));
  }
  return '(gemini 실패 — 위 로그 참고)';
}

async function openai() {
  const key = envKey('OPENAI_API_KEY');
  if (!key) return '(OPENAI_API_KEY 없음)';
  for (const model of ['gpt-4.1', 'gpt-4o']) {
    const r = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
      body: JSON.stringify({
        model, temperature: 0.2,
        messages: [{ role: 'user', content: [
          { type: 'text', text: question },
          { type: 'image_url', image_url: { url: `data:${mime};base64,${b64}`, detail: 'high' } },
        ] }],
      }),
    });
    const j = await r.json();
    if (r.ok && j.choices?.[0]?.message?.content) return `<!-- ${model} -->\n` + j.choices[0].message.content;
    console.error(`  openai ${model}: ${r.status} ${(j.error?.message ?? '').slice(0, 160)}`);
  }
  return '(openai 실패 — 위 로그 참고)';
}

const t0 = Date.now();
const jobs = [];
if (only !== 'openai') jobs.push(gemini().then((a) => ['Gemini', a]));
if (only !== 'gemini') jobs.push(openai().then((a) => ['OpenAI', a]));
const answers = await Promise.all(jobs);
const md = `# ${path.basename(img)}\n\n질문:\n\n> ${question.replace(/\n/g, '\n> ')}\n\n`
  + answers.map(([who, a]) => `## ${who}\n\n${a}\n`).join('\n')
  + `\n_${((Date.now() - t0) / 1000).toFixed(1)}s_\n`;
if (out) { writeFileSync(out, md, 'utf8'); console.log(`  → ${out} (${((Date.now() - t0) / 1000).toFixed(1)}s)`); }
else console.log(md);
