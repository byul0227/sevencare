import { useEffect, useState } from 'react'
import { ChipGroup, IconTile, PageHead, PetAvatar, TopBar } from '../components/common.jsx'
import { BackIcon, CalendarIcon, CameraIcon, ChevronRightIcon, MedIcon, PlusIcon, StethoIcon } from '../components/Icons.jsx'
import { api } from '../lib/api.js'
import { prepareProfilePhoto } from '../lib/photo.js'
import { petAgeText, petGenderText, weightText } from '../lib/format.js'

const dotDate = (d) => d.replaceAll('-', '.')
const longDate = (d) => new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' }).format(new Date(`${d}T00:00:00`))

const VISIT_TONE = { 정기검진: 'green', 검사: 'weight', 진료: 'meal', 예방접종: 'med', 수술: 'danger' }

/** 마이펫 탭: 등록된 펫 목록 */
export function PetListScreen({ pets, onView, onAdd }) {
  return (
    <div className="screen">
      <PageHead title="마이펫" sub={pets.length ? `함께하는 가족 ${pets.length}` : '반려동물을 등록해 주세요'} />
      <div className="wide-grid" style={{ padding: '0 20px 8px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {pets.length === 0 && <div className="empty-hint">아직 등록된 펫이 없어요</div>}
        {pets.map((p) => (
          <div key={p.id} className="care-card pet-card" onClick={() => onView(p.id)}>
            <PetAvatar pet={p} size={56} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <p className="name">{p.name}</p>
              <p className="sub">{p.breed} · {petAgeText(p)} · {petGenderText(p)}</p>
              <div className="mini-chips">
                <span>{weightText(p.latest_weight_kg)}</span>
                {p.condition && <span>{p.condition}</span>}
              </div>
            </div>
            <ChevronRightIcon stroke="currentColor" className="chev" />
          </div>
        ))}
      </div>
      <div style={{ padding: '6px 20px 20px' }}>
        <button type="button" className="add-btn" onClick={onAdd}>
          <PlusIcon />
          펫 등록하기
        </button>
      </div>
    </div>
  )
}

/** 펫 상세 정보 */
export function PetDetailScreen({ pet, onBack, onEdit, onDelete, onAddVisit, onEditVisit, onToast }) {
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [visits, setVisits] = useState(null)
  const [meds, setMeds] = useState(null)

  useEffect(() => {
    api.listVisits(pet.id).then(setVisits).catch((e) => onToast?.(e.message, true))
    api.listMedications(pet.id).then(setMeds).catch(() => setMeds([]))
  }, [pet.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const activeMeds = meds?.filter((m) => m.active).map((m) => m.name) ?? []

  async function handleDelete() {
    setDeleting(true)
    try {
      await onDelete()
    } catch {
      setDeleting(false)
    }
  }

  return (
    <div className="screen">
      <div className="pet-cover">
        <div className="cover-bar">
          <button type="button" className="back on-dark" onClick={onBack} aria-label="뒤로"><BackIcon stroke="currentColor" /></button>
          <button type="button" className="chip glass" onClick={onEdit}>수정</button>
        </div>
        <PetAvatar pet={pet} className="avatar-lg" />
        <p className="pname">{pet.name}</p>
        <p className="pmeta">{pet.breed} · {petGenderText(pet)}</p>
      </div>
      <div className="pet-stats">
        <div><b>{petAgeText(pet)}</b><span>나이</span></div>
        <div><b>{weightText(pet.latest_weight_kg)}</b><span>현재 체중</span></div>
        <div><b>{visits ? visits.visits.length : '–'}회</b><span>병원 방문</span></div>
      </div>
      <div className="info-card">
        <div className="info-row"><span className="k">기저 질환</span><span className="v">{pet.condition || '없음'}</span></div>
        <div className="info-row">
          <span className="k">복용 중인 약</span>
          <span className="v">{meds == null ? '…' : activeMeds.length ? activeMeds.join(', ') : '없음'}</span>
        </div>
        <div className="info-row"><span className="k">담당 병원</span><span className="v">{pet.hospital || '미등록'}</span></div>
      </div>

      <div className="sec-head">
        <h2>병원 방문 기록</h2>
        <button type="button" className="link-btn" onClick={onAddVisit}>+ 기록 추가</button>
      </div>
      {visits?.next_visit && (
        <div className="next-visit">
          <IconTile tone="brand" Icon={CalendarIcon} size={40} />
          <p>
            <small>다음 방문 예정</small>
            <strong>{longDate(visits.next_visit.next_visit_date)}</strong>
            <span>{visits.next_visit.title}{visits.next_visit.hospital ? ` · ${visits.next_visit.hospital}` : ''}</span>
          </p>
        </div>
      )}
      <div className="info-card" style={{ padding: 16 }}>
        {visits == null ? (
          <p className="timeline-note" style={{ margin: 0 }}>불러오는 중…</p>
        ) : visits.visits.length === 0 ? (
          <p className="timeline-note" style={{ margin: 0 }}>아직 방문 기록이 없어요. 진료·검사·예방접종을 기록해 두면 병원 갈 때 한눈에 볼 수 있어요.</p>
        ) : (
          <div className="timeline">
            {visits.visits.map((v) => (
              <button key={v.id} type="button" className="timeline-item" onClick={() => onEditVisit(v)}>
                <IconTile tone={VISIT_TONE[v.category] ?? 'brand'} Icon={v.category === '예방접종' ? MedIcon : StethoIcon} size={34} />
                <div>
                  <p className="timeline-date">{dotDate(v.visit_date)} · {v.category}</p>
                  <p className="timeline-title">{v.title}</p>
                  <p className="timeline-note">
                    {[v.hospital, v.diagnosis, v.treatment].filter(Boolean).join(' · ') || '상세 내용 없음'}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '0 22px 24px', marginTop: 'auto' }}>
        {confirming ? (
          <div className="alert-banner" style={{ margin: 0, flexDirection: 'column', gap: 12 }}>
            <p>{pet.name}의 정보와 지금까지의 기록이 모두 삭제돼요. 되돌릴 수 없어요.</p>
            <div style={{ display: 'flex', gap: 8, width: '100%' }}>
              <button type="button" className="chip" style={{ flex: 1 }} onClick={() => setConfirming(false)} disabled={deleting}>
                취소
              </button>
              <button
                type="button"
                className="chip"
                style={{ flex: 1, background: 'var(--rust-600)', borderColor: 'var(--rust-600)', color: 'white', fontWeight: 600 }}
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? '삭제 중…' : '삭제'}
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="text-btn" style={{ display: 'block', margin: '0 auto' }} onClick={() => setConfirming(true)}>
            이 펫 삭제
          </button>
        )}
      </div>
    </div>
  )
}

/** 펫 등록/수정 폼. pet 이 있으면 수정 모드 */
export function PetFormScreen({ pet, onSubmit, onBack }) {
  const [form, setForm] = useState({
    name: pet?.name ?? '',
    breed: pet?.breed ?? '',
    age_years: pet?.age_years ?? '',
    weight_kg: pet?.weight_kg ?? '',
    gender: pet?.gender ?? '수컷',
    neutered: pet?.neutered ?? false,
    condition: pet?.condition ?? '',
    hospital: pet?.hospital ?? '',
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  // 사진 변경: null(그대로) | { dataUrl, color }(새 사진) | 'remove'(삭제)
  const [photo, setPhoto] = useState(null)
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e?.target ? e.target.value : e }))

  const currentSrc = photo === 'remove' ? null : photo?.dataUrl ?? api.photoUrl(pet)

  async function pickPhoto(e) {
    const file = e.target.files?.[0]
    e.target.value = '' // 같은 파일을 다시 골라도 동작하게
    if (!file) return
    try {
      setPhoto(await prepareProfilePhoto(file))
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleSave() {
    if (!form.name.trim() || !form.breed.trim()) return setError('이름과 품종을 입력해 주세요.')
    const body = {
      name: form.name.trim(),
      breed: form.breed.trim(),
      age_years: form.age_years === '' ? null : Number(form.age_years),
      weight_kg: form.weight_kg === '' ? null : Number(form.weight_kg),
      gender: form.gender,
      neutered: form.neutered,
      condition: form.condition.trim() || null,
      hospital: form.hospital.trim() || null,
    }
    setError('')
    setSaving(true)
    try {
      await onSubmit(body, photo)
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <div className="screen">
      <TopBar title={pet ? '펫 정보 수정' : '펫 등록하기'} onBack={onBack} />
      <div className="form-body">
        <div className="photo-picker">
          <label className="photo-circle" aria-label="프로필 사진 고르기">
            {currentSrc ? <img src={currentSrc} alt="프로필 사진 미리보기" /> : <CameraIcon />}
            <input type="file" accept="image/*" onChange={pickPhoto} hidden />
          </label>
          <div>
            <p className="field-label" style={{ margin: 0 }}>프로필 사진 (선택)</p>
            <p className="q-hint" style={{ marginTop: 4 }}>동그라미를 눌러 사진을 골라 주세요. 놀이 탭 캐릭터의 털 색도 이 사진에서 가져와요.</p>
            {currentSrc && (
              <button type="button" className="text-btn" style={{ margin: '4px 0 0', padding: 0 }} onClick={() => setPhoto('remove')}>
                사진 지우기
              </button>
            )}
          </div>
        </div>
        <div>
          <p className="field-label">이름</p>
          <input type="text" placeholder="예: 초코" value={form.name} onChange={set('name')} />
        </div>
        <div>
          <p className="field-label">품종</p>
          <input type="text" placeholder="예: 골든리트리버" value={form.breed} onChange={set('breed')} />
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <p className="field-label">나이</p>
            <div className="unit-row">
              <input type="number" min="0" placeholder="14" value={form.age_years} onChange={set('age_years')} />
              <span>세</span>
            </div>
          </div>
          <div style={{ flex: 1 }}>
            <p className="field-label">체중</p>
            <div className="unit-row">
              <input type="number" step="0.1" placeholder="24.1" value={form.weight_kg} onChange={set('weight_kg')} />
              <span>kg</span>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <p className="field-label">성별</p>
            <ChipGroup options={['수컷', '암컷']} value={form.gender} onChange={set('gender')} />
          </div>
          <div style={{ flex: 1 }}>
            <p className="field-label">중성화</p>
            <ChipGroup
              options={[{ value: false, label: '안 함' }, { value: true, label: '완료' }]}
              value={form.neutered}
              onChange={set('neutered')}
            />
          </div>
        </div>
        <div>
          <p className="field-label">기저 질환 (선택)</p>
          <input type="text" placeholder="예: 슬개골 탈구 2기, 없으면 비워두세요" value={form.condition} onChange={set('condition')} />
        </div>
        <div>
          <p className="field-label">담당 병원 (선택)</p>
          <input type="text" placeholder="예: 노원동물병원" value={form.hospital} onChange={set('hospital')} />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>
          {saving ? '저장 중…' : '저장'}
        </button>
      </div>
    </div>
  )
}
