/*  AE 작업실 폴더를 찾아준다 (labdir.py 의 Node 판).

    2026-09-16 이전에는 'C:/aelab' 을 박아 썼다. 작업물을 한 폴더로 모으면서 작업실이
    <통합 폴더>/02_AE작업실_aelab 으로 들어갔고 C:/aelab 은 없앴다.

    찾는 순서: AELAB_DIR 환경변수 → config.json 의 labDir → 위로 올라가며 폴더 이름 찾기 → 옛 자리
*/
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const FOLDER = '02_AE작업실_aelab';
const LEGACY = 'C:/aelab';

function fromConfig() {
  const cfg = join(HERE, 'config.json');
  try {
    const v = JSON.parse(readFileSync(cfg, 'utf8')).labDir || '';
    if (!v) return null;
    return isAbsolute(v) ? v : resolve(HERE, v);
  } catch { return null; }
}

function byWalkingUp() {
  let d = HERE;
  for (let i = 0; i < 8; i++) {
    const c = join(d, FOLDER);
    if (existsSync(c)) return c;
    const nd = dirname(d);
    if (nd === d) break;
    d = nd;
  }
  return null;
}

/** 작업실 폴더를 슬래시 경로로 */
export function labDir() {
  for (const v of [process.env.AELAB_DIR, fromConfig(), byWalkingUp(), LEGACY]) {
    if (v && existsSync(v)) return v.split(String.fromCharCode(92)).join('/');
  }
  return (byWalkingUp() || LEGACY).split(String.fromCharCode(92)).join('/');
}

/** 작업실 아래 경로 만들기 — lab('pack', 'trad_rr') */
export function lab(...parts) {
  return [labDir(), ...parts.map(p => String(p).replace(/^\/+|\/+$/g, ''))].join('/');
}

export default labDir;
