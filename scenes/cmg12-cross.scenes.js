/**
 * 차트명가 #12 인트로 4컷 — 합본 (한 장에 다 그린다)
 *
 * 정의는 전부 `cmg12-cross.build.js` 에 있다. 이 파일은 미리보기·스틸 확인용
 * 진입점일 뿐이다. 프리미어에 실제로 얹는 것은 층으로 나눈 아래 다섯 개다:
 *
 *   cmg12-layer-candle.scenes.js   캔들 (불투명, 스택 바닥)
 *   cmg12-layer-ma.scenes.js       이평선
 *   cmg12-layer-mark.scenes.js     강조원·손실 밴드·진입선
 *   cmg12-layer-tag.scenes.js      매수/매도 태그
 *   cmg12-layer-text.scenes.js     글자 라벨·밑줄
 */
export { default } from './cmg12-cross.build.js';
