import { useEffect, useState } from 'react'
import { ChipGroup, TopBar } from '../components/common.jsx'
import { MedIcon, PlusIcon } from '../components/Icons.jsx'
import { api } from '../lib/api.js'
import { toDateStr } from '../lib/format.js'

/** 약 관리: 등록된 약 목록 */
export function MedListScreen({ pet, onBack, onAdd, onEdit, onToast }) {
  const [meds, setMeds] = useState(null)

  useEffect(() => {
    api.listMedications(pet.id).then(setMeds).catch((e) => onToast(e.message, true))
  }, [pet.id]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="screen">
      <TopBar title="약 관리" onBack={onBack} />
      <p className="section-label" style={{ marginTop: 2 }}>{pet.name}가 먹는 약과 복용 시간</p>
      <div style={{ padding: '0 22px 8px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {meds == null ? (
          <div className="empty-hint">불러오는 중…</div>
        ) : meds.length === 0 ? (
          <div className="empty-hint">등록된 약이 없어요. 약을 등록하면 케어 탭에 매일 복용 체크리스트가 생겨요.</div>
        ) : (
          meds.map((m) => (
            <div key={m.id} className="care-card" role="button" tabIndex={0}
              onClick={() => onEdit(m)} onKeyDown={(e) => e.key === 'Enter' && onEdit(m)}
              style={m.active ? undefined : { opacity: 0.6 }}>
              <div className="care-card-top">
                <span className="care-title">{m.name}{m.dose ? ` · ${m.dose}` : ''}</span>
                <span className="care-badge">{m.active ? '복용 중' : '중지'}</span>
              </div>
              <p className="care-desc">
                매일 {m.times.join(', ')}
                {m.end_date ? ` · ${m.end_date}까지` : ''}
                {m.instructions ? ` · ${m.instructions}` : ''}
              </p>
            </div>
          ))
        )}
      </div>
      <div style={{ padding: '6px 22px 20px' }}>
        <button type="button" className="log-btn"
          style={{ width: '100%', justifyContent: 'center', gap: 8, borderStyle: 'dashed', color: 'var(--gold-600)' }}
          onClick={onAdd}>
          <PlusIcon />
          약 등록하기
        </button>
      </div>
    </div>
  )
}

/** 약 등록/수정. med 가 있으면 수정 모드 */
export function MedFormScreen({ pet, med, onBack, onSaved, onToast }) {
  const [name, setName] = useState(med?.name ?? '')
  const [dose, setDose] = useState(med?.dose ?? '')
  const [times, setTimes] = useState(med?.times ?? ['09:00'])
  const [instructions, setInstructions] = useState(med?.instructions ?? '')
  const [active, setActive] = useState(med?.active ?? true)
  const [startDate, setStartDate] = useState(med?.start_date ?? toDateStr())
  const [endDate, setEndDate] = useState(med?.end_date ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const setTime = (i) => (e) => setTimes((ts) => ts.map((t, j) => (j === i ? e.target.value : t)))

  async function handleSave() {
    const clean = times.filter(Boolean)
    if (!name.trim()) return setError('약 이름을 입력해 주세요.')
    if (clean.length === 0) return setError('복용 시간을 하나 이상 넣어 주세요.')
    if (new Set(clean).size !== clean.length) return setError('같은 복용 시간이 두 번 들어가 있어요.')
    const body = {
      name: name.trim(), dose: dose.trim() || null, times: clean,
      instructions: instructions.trim() || null, active,
      start_date: startDate, end_date: endDate || null,
    }
    setError('')
    setSaving(true)
    try {
      if (med) await api.updateMedication(med.id, body)
      else await api.createMedication(pet.id, body)
      onToast(`${body.name} ${med ? '수정' : '등록'}됐어요`)
      onSaved()
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  async function handleDelete() {
    setSaving(true)
    try {
      await api.deleteMedication(med.id)
      onToast(`${med.name}을(를) 삭제했어요. 지난 복용 기록은 남아 있어요`)
      onSaved()
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <div className="screen">
      <TopBar title={med ? '약 정보 수정' : '약 등록하기'} onBack={onBack} />
      <div className="form-body">
        <div>
          <p className="field-label">약 이름</p>
          <input type="text" placeholder="예: 관절 영양제" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <p className="field-label">1회 용량 (선택)</p>
          <input type="text" placeholder="예: 1정, 0.5ml" value={dose} onChange={(e) => setDose(e.target.value)} />
        </div>
        <div>
          <p className="field-label">매일 복용 시간</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {times.map((t, i) => (
              <div key={i} className="unit-row">
                <input type="time" value={t} onChange={setTime(i)} aria-label={`복용 시간 ${i + 1}`} />
                {times.length > 1 && (
                  <button type="button" className="chip" style={{ padding: '10px 12px', flexShrink: 0 }}
                    onClick={() => setTimes((ts) => ts.filter((_, j) => j !== i))}>삭제</button>
                )}
              </div>
            ))}
            {times.length < 6 && (
              <button type="button" className="chip" style={{ borderStyle: 'dashed' }}
                onClick={() => setTimes((ts) => [...ts, ''])}>+ 시간 추가</button>
            )}
          </div>
        </div>
        <div>
          <p className="field-label">수의사 지시사항 (선택)</p>
          <input type="text" placeholder="예: 식후 30분, 진통제와 2시간 간격" value={instructions}
            onChange={(e) => setInstructions(e.target.value)} />
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <p className="field-label">시작일</p>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div style={{ flex: 1 }}>
            <p className="field-label">종료일 (선택)</p>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
        </div>
        {med && (
          <div>
            <p className="field-label">상태</p>
            <ChipGroup options={[{ value: true, label: '복용 중' }, { value: false, label: '중지' }]}
              value={active} onChange={setActive} />
          </div>
        )}

        {error && <p className="error-text">{error}</p>}
        <button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>
          {saving ? '저장 중…' : '저장'}
        </button>
        {med && (confirmDelete ? (
          <div className="alert-banner" style={{ margin: 0, flexDirection: 'column', gap: 12 }}>
            <p>{med.name}을(를) 목록에서 삭제할까요? 지난 복용 기록은 지워지지 않아요.</p>
            <div style={{ display: 'flex', gap: 8, width: '100%' }}>
              <button type="button" className="chip" style={{ flex: 1 }} onClick={() => setConfirmDelete(false)}>취소</button>
              <button type="button" className="chip danger" style={{ flex: 1 }} onClick={handleDelete} disabled={saving}>삭제</button>
            </div>
          </div>
        ) : (
          <button type="button" className="text-btn" onClick={() => setConfirmDelete(true)}>이 약 삭제</button>
        ))}
      </div>
    </div>
  )
}

const STATUS = {
  taken: { label: '복용 완료', cls: 'ok' },
  due: { label: '지금 복용', cls: 'due' },
  missed: { label: '기록 없음', cls: 'missed' },
  upcoming: { label: '예정', cls: 'upcoming' },
}
const hhmm = (iso) => iso?.slice(11, 16)

/** 케어 탭 안의 '오늘의 약물 스케줄' 섹션 */
export function MedScheduleSection({ pet, onManage, onToast }) {
  const [sched, setSched] = useState(null)
  const [busy, setBusy] = useState(null)

  useEffect(() => {
    api.getMedSchedule(pet.id).then(setSched).catch((e) => onToast(e.message, true))
  }, [pet.id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function toggle(slot) {
    const key = `${slot.medication_id}-${slot.time}`
    setBusy(key)
    try {
      if (slot.record_id) {
        await api.deleteRecord(slot.record_id)
        setSched(await api.getMedSchedule(pet.id))
      } else {
        setSched(await api.checkMedSlot(pet.id, { medication_id: slot.medication_id, time: slot.time }))
        onToast(`${slot.name} ${slot.time} 복용 기록했어요`)
      }
    } catch (e) {
      onToast(e.message, true)
    } finally {
      setBusy(null)
    }
  }

  return (
    <>
      <div className="section-row">
        <p className="section-label" style={{ margin: 0 }}>오늘의 약물 스케줄</p>
        <button type="button" className="link-btn" onClick={onManage}>약 관리</button>
      </div>
      <div style={{ padding: '0 22px 28px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sched?.alerts.map((a) => (
          <div key={a.code} className="alert-banner" style={{ margin: 0 }} role="alert">
            <MedIcon />
            <p>{a.message}</p>
          </div>
        ))}
        {sched == null ? (
          <div className="empty-hint">불러오는 중…</div>
        ) : sched.slots.length === 0 ? (
          <button type="button" className="empty-hint" style={{ border: 'none', cursor: 'pointer', width: '100%' }} onClick={onManage}>
            등록된 약이 없어요. 눌러서 약과 복용 시간을 등록해 주세요.
          </button>
        ) : (
          sched.slots.map((s) => {
            const st = STATUS[s.status]
            const key = `${s.medication_id}-${s.time}`
            return (
              <label key={key} className={`med-row ${s.status}`}>
                <input type="checkbox" checked={Boolean(s.record_id)} disabled={busy === key} onChange={() => toggle(s)} />
                <span style={{ flex: 1 }}>
                  {s.name}{s.dose ? ` ${s.dose}` : ''} · {s.time}
                  {s.instructions && <span className="med-note">{s.instructions}</span>}
                </span>
                <span className={`med-status ${st.cls}`}>
                  {s.status === 'taken' && s.taken_at && hhmm(s.taken_at) !== s.time ? `${hhmm(s.taken_at)} 복용` : st.label}
                </span>
              </label>
            )
          })
        )}
      </div>
    </>
  )
}
