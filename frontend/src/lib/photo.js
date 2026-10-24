// 사진을 브라우저에서 512px 로 줄이고(JPEG), 가운데 부분에서 털 색을 뽑아요.
// 서버로는 줄인 사진만 보내서 업로드가 빠르고 DB도 가벼워요.

const MAX_SIDE = 512

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => { URL.revokeObjectURL(url); resolve(img) }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('사진을 읽을 수 없어요. JPG나 PNG 사진을 골라 주세요.')) }
    img.src = url
  })
}

const toHex = (n) => Math.round(n).toString(16).padStart(2, '0')

/** 가운데 40% 영역의 평균 색 (너무 밝은 배경·너무 어두운 그림자는 뺌) */
function sampleColor(img) {
  const c = document.createElement('canvas')
  c.width = c.height = 32
  const ctx = c.getContext('2d')
  const s = Math.min(img.width, img.height) * 0.4
  ctx.drawImage(img, (img.width - s) / 2, (img.height - s) / 2, s, s, 0, 0, 32, 32)
  const { data } = ctx.getImageData(0, 0, 32, 32)
  let r = 0, g = 0, b = 0, n = 0
  for (let i = 0; i < data.length; i += 4) {
    const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
    if (lum > 245 || lum < 18) continue
    r += data[i]; g += data[i + 1]; b += data[i + 2]; n++
  }
  if (!n) return null
  return `#${toHex(r / n)}${toHex(g / n)}${toHex(b / n)}`
}

/** File → { dataUrl, color } */
export async function prepareProfilePhoto(file) {
  if (!file.type.startsWith('image/')) throw new Error('사진 파일만 올릴 수 있어요.')
  const img = await loadImage(file)
  const scale = Math.min(1, MAX_SIDE / Math.max(img.width, img.height))
  const c = document.createElement('canvas')
  c.width = Math.round(img.width * scale)
  c.height = Math.round(img.height * scale)
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height)
  return { dataUrl: c.toDataURL('image/jpeg', 0.85), color: sampleColor(img) }
}
