// 날짜·기록 표시용 헬퍼

const pad = (n) => String(n).padStart(2, '0')

/** 로컬 기준 YYYY-MM-DD */
export const toDateStr = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

/** 로컬 기준 HH:MM */
export const toTimeStr = (d = new Date()) => `${pad(d.getHours())}:${pad(d.getMinutes())}`

/** 서버로 보낼 로컬 datetime (타임존 없이) */
export const toLocalIso = (dateStr, timeStr) => `${dateStr}T${timeStr}:00`

/** "2026년 9월 24일 목요일" */
export const formatKoreanDate = (d = new Date()) =>
  new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }).format(d)

// 식사량: 칩 ↔ 퍼센트 (리포트에서 평균 식사량 % 계산에 사용)
export const MEAL_OPTIONS = [
  { value: 10, label: '거의 안먹음' },
  { value: 50, label: '절반' },
  { value: 80, label: '대부분' },
  { value: 100, label: '전부' },
]
export const mealLabel = (pct) =>
  MEAL_OPTIONS.reduce((best, o) => (Math.abs(o.value - pct) < Math.abs(best.value - pct) ? o : best)).label

const mealTitle = (hour) => (hour < 11 ? '아침 식사' : hour < 16 ? '점심 식사' : '저녁 식사')

/** 홈 '오늘의 기록' 한 줄: { label, meta } */
export function describeRecord(r) {
  const at = new Date(r.recorded_at)
  const time = toTimeStr(at)
  switch (r.type) {
    case 'meal':
      return { label: mealTitle(at.getHours()), meta: `${mealLabel(r.meal_amount)} · ${time}` }
    case 'poop':
      return {
        label: '배변 활동',
        meta: `${r.poop_firmness}${r.poop_blood ? ' · 혈변/점액' : ''} · ${time}`,
      }
    case 'weight':
      return { label: `체중 ${r.weight_kg}kg`, meta: `측정 · ${time}` }
    case 'med':
      return { label: r.med_name, meta: `복용 · ${time}` }
    default:
      return { label: r.type, meta: time }
  }
}

export const RECORD_TITLES = { meal: '식사 기록', poop: '배변 기록', weight: '체중 기록', med: '투약 기록' }

export const petAgeText = (p) => (p.age_years != null ? `${p.age_years}세` : '나이 미상')
export const petGenderText = (p) => `${p.gender}${p.neutered ? '(중성화)' : ''}`
export const weightText = (kg) => (kg != null ? `${kg}kg` : '미측정')
