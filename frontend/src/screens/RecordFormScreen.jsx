import { useEffect, useState } from 'react'
import { ChipGroup, TopBar } from '../components/common.jsx'
import { api } from '../lib/api.js'
import { MEAL_OPTIONS, RECORD_TITLES, mealLabel, toDateStr, toLocalIso, toTimeStr } from '../lib/format.js'

const CUSTOM = '__custom__'

/** 식사/배변/체중/투약 입력 폼. record 가 있으면 수정 모드 */
export default function RecordFormScreen({ type, record, petId, onSubmit, onDelete, onBack }) {
  const editing = Boolean(record)
  const initialAt = record ? new Date(record.recorded_at) : new Date()

  const [time, setTime] = useState(toTimeStr(initialAt))
  const [note, setNote] = useState(record?.note ?? '')
  // meal
  const [mealAmount, setMealAmount] = useState(
    record?.meal_amount != null ? MEAL_OPTIONS.find((o) => o.label === mealLabel(record.meal_amount)).value : 80,
  )
  // poop
  const [firmness, setFirmness] = useState(record?.poop_firmness ?? '정상')
  const [color, setColor] = useState(record?.poop_color ?? '갈색')
  const [blood, setBlood] = useState(record?.poop_blood ?? false)
  // weight
  const [weight, setWeight] = useState(record?.weight_kg != null ? String(record.weight_kg) : '')
  // med
  // 약 종류 칩 = 케어 탭 '약 관리'에 등록한 복용 중인 약
  const [medPresets, setMedPresets] = useState([])
  const [medChoice, setMedChoice] = useState(record?.med_name ? CUSTOM : null)
  const [medCustom, setMedCustom] = useState(record?.med_name ?? '')
  useEffect(() => {
    if (type !== 'med' || !petId) return
    api.listMedications(petId).then((meds) => {
      const names = [...new Set(meds.filter((m) => m.active).map((m) => m.name))]
      setMedPresets(names)
      const current = record?.med_name
      if (current && names.includes(current)) { setMedChoice(current); setMedCustom('') }
      else if (!current) setMedChoice(names[0] ?? CUSTOM)
    }).catch(() => setMedChoice((c) => c ?? CUSTOM))
  }, [type, petId]) // eslint-disable-line react-hooks/exhaustive-deps

  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function buildBody() {
    const body = { recorded_at: toLocalIso(toDateStr(initialAt), time || toTimeStr()) }
    if (type === 'meal') Object.assign(body, { meal_amount: mealAmount, note: note.trim() || null })
    if (type === 'poop') Object.assign(body, { poop_firmness: firmness, poop_color: color, poop_blood: blood, note: note.trim() || null })
    if (type === 'weight') {
      const kg = Number(weight)
      if (!weight || !(kg > 0) || kg > 150) return { error: '체중을 입력해 주세요.' }
      body.weight_kg = Math.round(kg * 10) / 10
    }
    if (type === 'med') {
      const name = medChoice === CUSTOM ? medCustom.trim() : medChoice
      if (!name) return { error: '약 이름을 입력해 주세요.' }
      body.med_name = name
    }
    return { body }
  }

  async function handleSave() {
    const { body, error: err } = buildBody()
    if (err) return setError(err)
    setError('')
    setSaving(true)
    try {
      await onSubmit(editing ? body : { type, ...body })
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  const timeField = (
    <div>
      <p className="field-label">시간</p>
      <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
    </div>
  )
  const noteField = (placeholder) => (
    <div>
      <p className="field-label">특이사항 (선택)</p>
      <textarea rows={2} placeholder={placeholder} value={note} onChange={(e) => setNote(e.target.value)} />
    </div>
  )

  return (
    <div className="screen">
      <TopBar title={RECORD_TITLES[type] + (editing ? ' 수정' : '')} onBack={onBack} />
      <div className="form-body">
        {type === 'meal' && (
          <>
            {timeField}
            <div>
              <p className="field-label">섭취량</p>
              <ChipGroup options={MEAL_OPTIONS} value={mealAmount} onChange={setMealAmount} />
            </div>
            {noteField('예: 사료를 오래 씹지 못함')}
          </>
        )}

        {type === 'poop' && (
          <>
            {timeField}
            <div>
              <p className="field-label">굳기</p>
              <ChipGroup options={['무름', '정상', '딱딱함']} value={firmness} onChange={setFirmness} />
            </div>
            <div>
              <p className="field-label">색깔</p>
              <ChipGroup options={['갈색', '검붉은색', '회색/노란색']} value={color} onChange={setColor} />
            </div>
            <div>
              <p className="field-label">혈변 · 점액</p>
              <ChipGroup options={[{ value: false, label: '없음' }, { value: true, label: '있음' }]} value={blood} onChange={setBlood} />
            </div>
            {noteField('예: 평소보다 힘들어함, 양이 적음')}
          </>
        )}

        {type === 'weight' && (
          <div>
            <p className="field-label">측정 체중</p>
            <div className="unit-row">
              <input
                type="number" inputMode="decimal" step="0.1" placeholder="24.1" autoFocus
                value={weight} onChange={(e) => setWeight(e.target.value)}
              />
              <span>kg</span>
            </div>
          </div>
        )}

        {type === 'med' && (
          <>
            <div>
              <p className="field-label">약 종류</p>
              <ChipGroup
                options={[...medPresets, { value: CUSTOM, label: '직접 입력' }]}
                value={medChoice}
                onChange={setMedChoice}
                columns={Math.min(medPresets.length + 1, 3)}
              />
              {medPresets.length === 0 && (
                <p className="q-hint" style={{ marginTop: 8 }}>케어 탭의 '약 관리'에서 약을 등록하면 여기서 바로 고를 수 있어요.</p>
              )}
              {medChoice === CUSTOM && (
                <input
                  type="text" placeholder="예: 심장약" style={{ marginTop: 8 }} autoFocus
                  value={medCustom} onChange={(e) => setMedCustom(e.target.value)}
                />
              )}
            </div>
            {timeField}
          </>
        )}

        {error && <p className="error-text">{error}</p>}
        <button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>
          {saving ? '저장 중…' : '저장'}
        </button>
        {editing && (
          <button type="button" className="text-btn" onClick={onDelete} disabled={saving}>
            이 기록 삭제
          </button>
        )}
      </div>
    </div>
  )
}
