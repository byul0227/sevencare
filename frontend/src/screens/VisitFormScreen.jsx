import { useState } from 'react'
import { ChipGroup, TopBar } from '../components/common.jsx'
import { api } from '../lib/api.js'
import { toDateStr } from '../lib/format.js'

export const VISIT_CATEGORIES = ['정기검진', '진료', '예방접종', '검사', '수술', '기타']

/** 병원 방문 기록 추가/수정. visit 이 있으면 수정 모드 */
export default function VisitFormScreen({ pet, visit, onBack, onSaved, onToast }) {
  const [form, setForm] = useState({
    visit_date: visit?.visit_date ?? toDateStr(),
    category: visit?.category ?? '진료',
    title: visit?.title ?? '',
    hospital: visit?.hospital ?? '',
    diagnosis: visit?.diagnosis ?? '',
    treatment: visit?.treatment ?? '',
    note: visit?.note ?? '',
    next_visit_date: visit?.next_visit_date ?? '',
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e?.target ? e.target.value : e }))

  async function handleSave() {
    if (!form.visit_date) return setError('방문 날짜를 골라 주세요.')
    if (!form.title.trim()) return setError('어떤 방문이었는지 제목을 적어 주세요.')
    if (form.next_visit_date && form.next_visit_date < form.visit_date) {
      return setError('다음 방문 예정일은 방문일보다 뒤여야 해요.')
    }
    const body = {
      visit_date: form.visit_date,
      category: form.category,
      title: form.title.trim(),
      hospital: form.hospital.trim() || null,
      diagnosis: form.diagnosis.trim() || null,
      treatment: form.treatment.trim() || null,
      note: form.note.trim() || null,
      next_visit_date: form.next_visit_date || null,
    }
    setError('')
    setSaving(true)
    try {
      if (visit) await api.updateVisit(visit.id, body)
      else await api.createVisit(pet.id, body)
      onToast(visit ? '방문 기록을 수정했어요' : '방문 기록을 추가했어요')
      onSaved()
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  async function handleDelete() {
    setSaving(true)
    try {
      await api.deleteVisit(visit.id)
      onToast('방문 기록을 삭제했어요')
      onSaved()
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <div className="screen">
      <TopBar title={visit ? '방문 기록 수정' : '병원 방문 기록'} onBack={onBack} />
      <div className="form-body">
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <p className="field-label">방문 날짜</p>
            <input type="date" value={form.visit_date} max={toDateStr()} onChange={set('visit_date')} />
          </div>
          <div style={{ flex: 1 }}>
            <p className="field-label">병원 (선택)</p>
            <input type="text" placeholder={pet.hospital || '예: 노원동물병원'} value={form.hospital} onChange={set('hospital')} />
          </div>
        </div>
        <div>
          <p className="field-label">방문 종류</p>
          <ChipGroup options={VISIT_CATEGORIES} value={form.category} onChange={set('category')} columns={3} />
        </div>
        <div>
          <p className="field-label">제목</p>
          <input type="text" placeholder="예: 정기 혈액검사, 슬개골 탈구 2기 진단" value={form.title} onChange={set('title')} />
        </div>
        <div>
          <p className="field-label">진단 · 검사 결과 (선택)</p>
          <textarea rows={2} placeholder="예: 신장 수치 경계" value={form.diagnosis} onChange={set('diagnosis')} />
        </div>
        <div>
          <p className="field-label">처치 · 처방 (선택)</p>
          <textarea rows={2} placeholder="예: 관절 영양제 처방, 저염식 권장" value={form.treatment} onChange={set('treatment')} />
        </div>
        <div>
          <p className="field-label">메모 (선택)</p>
          <textarea rows={2} placeholder="수의사에게 들은 이야기, 비용 등" value={form.note} onChange={set('note')} />
        </div>
        <div>
          <p className="field-label">다음 방문 예정일 (선택)</p>
          <input type="date" value={form.next_visit_date} min={form.visit_date} onChange={set('next_visit_date')} />
        </div>

        {error && <p className="error-text">{error}</p>}
        <button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>
          {saving ? '저장 중…' : '저장'}
        </button>
        {visit && (confirmDelete ? (
          <div className="alert-banner" style={{ margin: 0, flexDirection: 'column', gap: 12 }}>
            <p>이 방문 기록을 삭제할까요? 되돌릴 수 없어요.</p>
            <div style={{ display: 'flex', gap: 8, width: '100%' }}>
              <button type="button" className="chip" style={{ flex: 1 }} onClick={() => setConfirmDelete(false)}>취소</button>
              <button type="button" className="chip danger" style={{ flex: 1 }} onClick={handleDelete} disabled={saving}>삭제</button>
            </div>
          </div>
        ) : (
          <button type="button" className="text-btn" onClick={() => setConfirmDelete(true)}>이 기록 삭제</button>
        ))}
      </div>
    </div>
  )
}
