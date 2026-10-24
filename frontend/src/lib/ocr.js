// 사료 성분표 글자 읽기: Tesseract.js (무료 오픈소스 OCR, 브라우저 안에서 실행)
// 스크립트와 한국어 학습 데이터는 처음 한 번 CDN에서 받아요 (인터넷 연결 필요).
const TESSERACT_CDN = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js'

let loading = null
function loadTesseract() {
  if (window.Tesseract) return Promise.resolve(window.Tesseract)
  if (!loading) {
    loading = new Promise((resolve, reject) => {
      const s = document.createElement('script')
      s.src = TESSERACT_CDN
      s.onload = () => resolve(window.Tesseract)
      s.onerror = () => { loading = null; reject(new Error('글자 인식 도구를 불러오지 못했어요. 인터넷 연결을 확인해 주세요')) }
      document.head.appendChild(s)
    })
  }
  return loading
}

/** 인식률을 높이려고: 작은 사진은 키우고(가로 1600px 이상), 흑백으로 바꾸고, 명암을 늘려요 */
export async function preprocess(file) {
  const url = URL.createObjectURL(file)
  try {
    const img = await new Promise((res, rej) => {
      const i = new Image()
      i.onload = () => res(i)
      i.onerror = () => rej(new Error('사진을 열 수 없어요'))
      i.src = url
    })
    const scale = Math.min(3, Math.max(1, 1600 / img.width))
    const c = document.createElement('canvas')
    c.width = Math.round(img.width * scale)
    c.height = Math.round(img.height * scale)
    const ctx = c.getContext('2d')
    ctx.drawImage(img, 0, 0, c.width, c.height)
    const d = ctx.getImageData(0, 0, c.width, c.height)
    const px = d.data
    let lo = 255, hi = 0
    const gray = new Uint8ClampedArray(px.length / 4)
    for (let i = 0, j = 0; i < px.length; i += 4, j++) {
      const g = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
      gray[j] = g
      if (g < lo) lo = g
      if (g > hi) hi = g
    }
    const span = Math.max(1, hi - lo)
    for (let i = 0, j = 0; i < px.length; i += 4, j++) {
      const v = ((gray[j] - lo) / span) * 255
      px[i] = px[i + 1] = px[i + 2] = v
    }
    ctx.putImageData(d, 0, 0)
    return c
  } finally {
    URL.revokeObjectURL(url)
  }
}

/**
 * 사진 → 글자. onProgress(0~1, 단계 설명)
 * psm(페이지 분할 방식): '6' = 한 덩어리 글로 보고 줄 단위로 읽기 (표 모양 성분표에 강함),
 *                         '3' = 자동 배치 분석 (글이 여기저기 흩어진 사진에 강함)
 */
export async function readLabel(file, onProgress, psm = '6') {
  onProgress?.(0.02, '글자 인식 도구 준비 중')
  const T = await loadTesseract()
  const canvas = await preprocess(file)
  const logger = (m) => {
    if (m.status === 'recognizing text') onProgress?.(0.3 + m.progress * 0.7, psm === '6' ? '글자 읽는 중' : '다른 방식으로 다시 읽는 중')
    else if (m.status?.includes('load')) onProgress?.(0.1 + (m.progress ?? 0) * 0.2, '한국어 데이터 받는 중')
  }
  if (T.createWorker) {
    const worker = await T.createWorker('kor+eng', 1, { logger })
    try {
      await worker.setParameters({ tessedit_pageseg_mode: psm, preserve_interword_spaces: '1' })
      const { data } = await worker.recognize(canvas)
      onProgress?.(1, '완료')
      return data.text
    } finally {
      await worker.terminate()
    }
  }
  const { data } = await T.recognize(canvas, 'kor+eng', { logger })
  onProgress?.(1, '완료')
  return data.text
}
