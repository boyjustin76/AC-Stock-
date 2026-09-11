#!/usr/bin/env node
/* Gemini 이미지 편집/생성 REST 직접 호출 (무료 등급 시험용).
   node tools/style/imgedit.mjs <출력.png> "<프롬프트>" [입력.png ...] [--model gemini-3.1-flash-image] */
import { readFileSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
const argv = process.argv.slice(2);
const out = argv[0], prompt = argv[1];
const mi = argv.indexOf('--model'); const model = mi >= 0 ? argv[mi + 1] : 'gemini-3.1-flash-image';
const inputs = argv.slice(2).filter((a, i, arr) => !a.startsWith('--') && arr[i - 1] !== '--model');
const key = process.env.GEMINI_API_KEY || execSync(`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')"`, { encoding: 'utf8' }).trim();
const parts = inputs.map((p) => ({ inline_data: { mime_type: p.endsWith('.jpg') ? 'image/jpeg' : 'image/png', data: readFileSync(p).toString('base64') } }));
parts.push({ text: prompt });
const t0 = Date.now();
const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ contents: [{ parts }], generationConfig: { responseModalities: ['IMAGE', 'TEXT'] } }),
});
const j = await r.json();
if (!r.ok) { console.error(`  ${model}: ${r.status} ${(j.error?.message ?? '').slice(0, 200)}`); process.exit(1); }
const ps = j.candidates?.[0]?.content?.parts ?? [];
const img = ps.find((p) => p.inlineData || p.inline_data);
if (!img) { console.error('  이미지 없음:', JSON.stringify(j).slice(0, 300)); process.exit(1); }
const d = (img.inlineData ?? img.inline_data).data;
writeFileSync(out, Buffer.from(d, 'base64'));
console.log(`  → ${out} (${model}, ${((Date.now() - t0) / 1000).toFixed(1)}s)`, ps.filter((p) => p.text).map((p) => p.text.slice(0, 120)).join(' | '));
