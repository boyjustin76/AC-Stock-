/**
 * 씬을 프리미어 트랙으로 갈라 쌓기 위한 패스 계획 + FCP7 XML 생성.
 *
 * 왜 이게 필요한가 —
 *   .mogrt 도, AE 컴포지션을 Dynamic Link 로 건 것도, 프리미어 안에서는 **클립 하나**다.
 *   레이어가 갈라지지 않는다. 그래서 자막을 보며 주석 하나만 싱크를 미는 편집이 안 된다.
 *   갈라진 트랙을 원하면 조각을 따로 렌더해 쌓는 수밖에 없고, 그게 이 파일이다.
 *
 * 얻는 것: 조각별 싱크·온오프·불투명도·위치 — 프리미어 모션 컨트롤 전부.
 * 못 얻는 것: 클립 안의 문구·색 변경(픽셀이니까). 그건 재렌더가 답이다.
 */

/** 레이어 타입 → 타임라인에 뜰 이름 */
const TYPE_KO = {
  cmgLevel: '수평선', cmgArrow: '화살표', cmgBadge: '배지', cmgMissed: '빗금',
  cmgNote: '문구', cmgUnderline: '밑줄', cmgCircle: '동그라미', cmgTrace: '궤적',
  cmgProfit: '수익', cmgCross: '엑스', trend: '추세선', range: '박스',
  zone: '존', pullback: '눌림목', ema: '이평선', flash: '플래시',
  titleCard: '타이틀', image: '이미지', text: '글자',
};

/** 레이어 하나를 사람이 알아볼 이름으로 */
function layerName(l, i) {
  const base = TYPE_KO[l.type] ?? l.type;
  const tag = l.label ?? l.text ?? (l.dir === 'buy' ? '매수' : l.dir === 'sell' ? '매도' : null);
  const n = String(i + 1).padStart(2, '0');
  return tag ? `${n} ${base} ${String(tag).replace(/\s+/g, ' ').trim()}` : `${n} ${base}`;
}

/**
 * 패스 계획. 기본은 **레이어 하나당 트랙 하나** — 가장 잘게 가른 형태다.
 * 트랙이 너무 많으면 그때 묶으면 되지만, 묶인 걸 다시 가르는 건 사람이 못 한다.
 *
 * @param groups 선택 — [[0,1],[2]] 처럼 묶을 인덱스. 안 주면 전부 따로.
 */
export function planPasses(scene, groups = null) {
  const layers = scene.layers ?? [];
  const passes = [{ key: 'p00', name: '차트 바닥', chart: true, layers: [] }];
  const gs = groups ?? layers.map((_, i) => [i]);
  gs.forEach((idxs, gi) => {
    const first = layers[idxs[0]];
    if (!first) return;
    const name = idxs.length === 1
      ? layerName(first, idxs[0])
      : `${String(gi + 1).padStart(2, '0')} ` + idxs.map((i) => TYPE_KO[layers[i].type] ?? layers[i].type).join('+');
    passes.push({ key: `p${String(gi + 1).padStart(2, '0')}`, name, chart: false, layers: idxs });
  });
  return passes;
}

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
/** 윈도우 경로 → FCP7 pathurl. 한글·공백은 퍼센트 인코딩한다 */
const WINSEP = String.fromCharCode(92);   /* 역슬래시. 정규식 이스케이프를 피한다 */
const pathurl = (p) => 'file://localhost/'
  + encodeURI(p.split(WINSEP).join('/').replace(/^[/]+/, ''));
const rate = (fps) => `<rate><timebase>${fps}</timebase><ntsc>FALSE</ntsc></rate>`;

/**
 * 트랙마다 클립 하나씩인 시퀀스 XML.
 * 첫 트랙이 V1(맨 아래)이므로 바닥 패스를 먼저 넣는다.
 *
 * @param audio 선택 — {file, inFrame, outFrame} 내레이션에서 이 컷에 해당하는 구간
 */
export function buildXml({ name, fps, width, height, frames, passes, audio = null }) {
  const vtracks = passes.map((ps, i) => {
    const f = `file-v${i + 1}`;
    return `   <track>`
      + `<clipitem id="v${i + 1}"><name>${esc(ps.name)}</name><enabled>TRUE</enabled>`
      + `<duration>${frames}</duration>${rate(fps)}`
      + `<start>0</start><end>${frames}</end><in>0</in><out>${frames}</out>`
      + `<file id="${f}"><name>${esc(ps.name)}</name><pathurl>${pathurl(ps.file)}</pathurl>`
      + `${rate(fps)}<duration>${frames}</duration>`
      + `<media><video><samplecharacteristics><width>${width}</width><height>${height}</height>`
      + `</samplecharacteristics></video></media></file>`
      /* 알파를 살리려면 합성 모드가 normal 이어야 한다 (qtrle 는 argb 라 알파가 파일에 있다) */
      + `<compositemode>normal</compositemode>`
      + `</clipitem></track>`;
  }).join('\n');

  const atrack = audio ? `  <audio><track>`
    + `<clipitem id="a1"><name>내레이션</name><enabled>TRUE</enabled>`
    + `<duration>${audio.outFrame - audio.inFrame}</duration>${rate(fps)}`
    + `<start>0</start><end>${audio.outFrame - audio.inFrame}</end>`
    + `<in>${audio.inFrame}</in><out>${audio.outFrame}</out>`
    + `<file id="file-a1"><name>narration.wav</name><pathurl>${pathurl(audio.file)}</pathurl>`
    + `${rate(fps)}<duration>${audio.outFrame}</duration>`
    + `<media><audio><samplecharacteristics><samplerate>48000</samplerate><depth>16</depth>`
    + `</samplecharacteristics><channelcount>2</channelcount></audio></media></file>`
    + `<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>`
    + `</clipitem></track></audio>\n` : '';

  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
<sequence id="${esc(name)}">
 <name>${esc(name)}</name>
 <duration>${frames}</duration>
 ${rate(fps)}
 <media>
  <video>
   <format><samplecharacteristics>${rate(fps)}<width>${width}</width><height>${height}</height>
    <pixelaspectratio>square</pixelaspectratio><anamorphic>FALSE</anamorphic>
   </samplecharacteristics></format>
${vtracks}
  </video>
${atrack} </media>
</sequence>
</xmeml>
`;
}
