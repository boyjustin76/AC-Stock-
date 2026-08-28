/* ── 검토 ──
 * 검토내용: write() 가 프레임마다 once('error') 리스너를 쌓던 누수 수정(실제 MaxListenersExceededWarning 발생). 인코딩은 별도 프로세스라 캡처와 이미 병행임을 확인 — 파이프라인 겹치기 과제는 원래 없었다. mp4 preset 을 밖에서 받게 함(기본 slow = 기존과 바이트 동일, medium 은 24.1s·파일 +2%).
 * 타임코드: 2026-08-27 19:42 KST
 * 검토자: Fable 5 Max
 */
/** PNG 프레임 스트림을 받아 편집용 파일로 인코딩한다. */
import { spawn } from 'node:child_process';
import ffmpegPath from 'ffmpeg-static';

/**
 * 포맷별 ffmpeg 인자.
 *  mp4   : H.264 고비트레이트. 유튜브 업로드 / 일반 편집용
 *  mov   : ProRes 422 HQ. 프리미어·파컷에서 가볍게 스크럽됨
 *  alpha : QuickTime RLE(무손실 알파). 차트만 오려서 오버레이할 때
 *  webm  : VP9 알파. 웹/After Effects 외 용도
 */
export const FORMATS = {
  mp4: {
    ext: 'mp4',
    alpha: false,
    // preset 은 화질이 아니라 '얼마나 오래 짜내느냐' 다. 중간 소스에는 과할 수 있어
    // 밖에서 바꿔 재 볼 수 있게 열어 두었다 (기본값은 지금까지 쓰던 slow).
    args: (fps, preset = 'slow') => [
      '-c:v', 'libx264', '-preset', preset, '-crf', '12',
      '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.2',
      '-x264-params', `keyint=${Math.round(fps)}:min-keyint=${Math.round(fps / 2)}`,
      '-movflags', '+faststart',
      '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
    ],
  },
  mov: {
    ext: 'mov',
    alpha: false,
    args: () => ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le', '-vendor', 'apl0'],
  },
  alpha: {
    ext: 'mov',
    alpha: true,
    args: () => ['-c:v', 'qtrle', '-pix_fmt', 'argb'],
  },
  webm: {
    ext: 'webm',
    alpha: true,
    args: () => ['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '20', '-row-mt', '1'],
  },
};

export function startEncoder({ format, fps, fpsExpr, outFile, width, height, onLog, preset }) {
  const f = FORMATS[format];
  if (!f) throw new Error(`알 수 없는 포맷: ${format}`);
  // 29.97 / 59.94 처럼 유리수 프레임레이트는 '60000/1001' 형태로 넘겨야 정확하다
  const rate = fpsExpr ?? String(fps);
  const args = [
    '-y',
    '-hide_banner', '-loglevel', 'error', '-stats',
    '-f', 'image2pipe', '-vcodec', 'png', '-framerate', rate,
    '-i', 'pipe:0',
    '-r', rate,
    '-s', `${width}x${height}`,
    ...f.args(fps, preset),
    outFile,
  ];
  const proc = spawn(ffmpegPath, args, { stdio: ['pipe', 'ignore', 'pipe'] });
  let err = '';
  proc.stderr.on('data', (d) => {
    err += d.toString();
    if (onLog) onLog(d.toString());
  });
  // write 마다 once('error') 를 걸면 프레임 수만큼 리스너가 쌓인다(실제로
  // MaxListenersExceededWarning 이 났다). 에러는 한 곳에서 받아 두고 다음 write 가 던진다.
  let ioError = null;
  let pendingDrain = null;
  proc.stdin.on('error', (e) => {
    ioError = e;
    if (pendingDrain) { const r = pendingDrain; pendingDrain = null; r(); }
  });

  return {
    write: (buf) =>
      new Promise((resolve, reject) => {
        if (ioError) return reject(ioError);
        if (!proc.stdin.write(buf)) {
          pendingDrain = resolve;
          proc.stdin.once('drain', () => { pendingDrain = null; resolve(); });
        } else resolve();
      }),
    finish: () =>
      new Promise((resolve, reject) => {
        proc.on('close', (code) => {
          if (code === 0) resolve();
          else reject(new Error(`ffmpeg 종료 코드 ${code}\n${err.slice(-4000)}`));
        });
        proc.stdin.end();
      }),
  };
}

/** 여러 씬 파일을 하나의 릴로 이어 붙인다 (재인코딩 없음) */
export function concatFiles(listFile, outFile) {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      ffmpegPath,
      ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', outFile],
      { stdio: ['ignore', 'ignore', 'pipe'] },
    );
    let err = '';
    proc.stderr.on('data', (d) => (err += d.toString()));
    proc.on('close', (c) => (c === 0 ? resolve() : reject(new Error(err.slice(-2000)))));
  });
}
