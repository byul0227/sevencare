// FastAPI 호출 모음. 개발 중에는 Vite 프록시가 /api → http://localhost:8000 으로 넘겨줘요.
const BASE = import.meta.env?.VITE_API_BASE ?? ''

async function request(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let message = `요청 실패 (${res.status})`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') message = data.detail
      else if (Array.isArray(data.detail)) message = data.detail.map((d) => d.msg).join(', ')
    } catch { /* 본문 없음 */ }
    throw new Error(message)
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  // pets
  listPets: () => request('GET', '/api/pets'),
  getPet: (id) => request('GET', `/api/pets/${id}`),
  createPet: (body) => request('POST', '/api/pets', body),
  updatePet: (id, body) => request('PATCH', `/api/pets/${id}`, body),
  deletePet: (id) => request('DELETE', `/api/pets/${id}`),

  // records
  listRecords: (petId, params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null)).toString()
    return request('GET', `/api/pets/${petId}/records${qs ? `?${qs}` : ''}`)
  },
  createRecord: (petId, body) => request('POST', `/api/pets/${petId}/records`, body),
  updateRecord: (id, body) => request('PATCH', `/api/records/${id}`, body),
  deleteRecord: (id) => request('DELETE', `/api/records/${id}`),

  // report
  getReport: (petId, weeks = 4) => request('GET', `/api/pets/${petId}/report?weeks=${weeks}`),
  createDemoHistory: (petId) => request('POST', `/api/pets/${petId}/demo-history`),
  deleteDemoHistory: (petId) => request('DELETE', `/api/pets/${petId}/demo-history`),

  // care checks
  getCareScales: () => request('GET', '/api/care-scales'),
  getCareSummary: (petId) => request('GET', `/api/pets/${petId}/care-summary`),
  createCareCheck: (petId, body) => request('POST', `/api/pets/${petId}/care-checks`, body),
  deleteCareCheck: (id) => request('DELETE', `/api/care-checks/${id}`),

  // medications
  listMedications: (petId) => request('GET', `/api/pets/${petId}/medications`),
  createMedication: (petId, body) => request('POST', `/api/pets/${petId}/medications`, body),
  updateMedication: (id, body) => request('PATCH', `/api/medications/${id}`, body),
  deleteMedication: (id) => request('DELETE', `/api/medications/${id}`),
  getMedSchedule: (petId, on) => request('GET', `/api/pets/${petId}/med-schedule${on ? `?on=${on}` : ''}`),
  checkMedSlot: (petId, body) => request('POST', `/api/pets/${petId}/med-schedule/check`, body),

  // vet visits
  listVisits: (petId) => request('GET', `/api/pets/${petId}/vet-visits`),
  createVisit: (petId, body) => request('POST', `/api/pets/${petId}/vet-visits`, body),
  updateVisit: (id, body) => request('PATCH', `/api/vet-visits/${id}`, body),
  deleteVisit: (id) => request('DELETE', `/api/vet-visits/${id}`),

  // AI 건강
  getBodyCheck: (petId) => request('GET', `/api/pets/${petId}/body-check`),
  getHealthInfo: () => request('GET', '/api/health-info'),
  getAiStatus: () => request('GET', '/api/ai/status'),
  aiChat: (petId, messages) => request('POST', `/api/pets/${petId}/ai-chat`, { messages }),

  // 프로필 사진
  photoUrl: (pet) => (pet?.photo_version ? `${BASE}/api/pets/${pet.id}/photo?v=${pet.photo_version}` : null),
  uploadPhoto: (petId, dataUrl, color) => request('PUT', `/api/pets/${petId}/photo`, { data_url: dataUrl, color }),
  deletePhoto: (petId) => request('DELETE', `/api/pets/${petId}/photo`),

  // 놀이 탭
  getPlay: (petId) => request('GET', `/api/pets/${petId}/play`),
  playAction: (petId, action) => request('POST', `/api/pets/${petId}/play/${action}`),

  // 사료 성분표 분석
  parseFoodLabel: (text) => request('POST', '/api/food-label/parse', { text }),
  checkFood: (petId, body) => request('POST', `/api/pets/${petId}/food-check`, body),

  // 병원 지참용 리포트
  getVetSummary: (petId, weeks = 4) => request('GET', `/api/pets/${petId}/vet-summary?weeks=${weeks}`),
}
