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
    args: (fps) => [
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '12',
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

export function startEncoder({ format, fps, fpsExpr, outFile, width, height, onLog }) {
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
    ...f.args(fps),
    outFile,
  ];
  const proc = spawn(ffmpegPath, args, { stdio: ['pipe', 'ignore', 'pipe'] });
  let err = '';
  proc.stderr.on('data', (d) => {
    err += d.toString();
    if (onLog) onLog(d.toString());
  });

  return {
    write: (buf) =>
      new Promise((resolve, reject) => {
        if (!proc.stdin.write(buf)) proc.stdin.once('drain', resolve);
        else resolve();
        proc.stdin.once('error', reject);
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
