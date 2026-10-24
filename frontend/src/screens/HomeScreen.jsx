import { useEffect, useState } from 'react'
import { IconTile, PetAvatar } from '../components/common.jsx'
import {
  AlertIcon, ChevronDownIcon, ChevronRightIcon, MealIcon, MedIcon, PlusIcon, PoopIcon, WeightIcon,
} from '../components/Icons.jsx'
import { api } from '../lib/api.js'
import { describeRecord, formatKoreanDate, petAgeText, weightText } from '../lib/format.js'

const LOG_BUTTONS = [
  { type: 'meal', label: '식사량', Icon: MealIcon },
  { type: 'poop', label: '배변', Icon: PoopIcon },
  { type: 'weight', label: '체중', Icon: WeightIcon },
  { type: 'med', label: '투약', Icon: MedIcon },
]
const ICONS = { meal: MealIcon, poop: PoopIcon, weight: WeightIcon, med: MedIcon }
const hhmm = (iso) => iso.slice(11, 16)

export default function HomeScreen({ pets, pet, records, loading, onSelectPet, onOpenForm, onAddPet, onGoTab }) {
  const [switcherOpen, setSwitcherOpen] = useState(false)
  const [extra, setExtra] = useState({})

  // 홈 요약용: 리포트 알림 · 오늘 투약 (실패해도 홈은 그대로 보여요)
  useEffect(() => {
    if (!pet) return
    let alive = true
    Promise.allSettled([api.getReport(pet.id), api.getMedSchedule(pet.id)]).then(([r, m]) => {
      if (!alive) return
      setExtra({
        alerts: r.status === 'fulfilled' ? r.value.alerts : [],
        meds: m.status === 'fulfilled' ? m.value.slots : null,
      })
    })
    return () => { alive = false }
  }, [pet?.id, records.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const count = (t) => records.filter((r) => r.type === t).length
  const medsTaken = extra.meds?.filter((s) => s.record_id).length ?? 0
  const alert = extra.alerts?.[0]

  return (
    <div className="screen home">
      <header className="hero">
        <p className="hero-date">{formatKoreanDate()}</p>
        {pet ? (
          <button type="button" className="hero-pet" onClick={() => setSwitcherOpen(true)}>
            <PetAvatar pet={pet} className="pet-avatar hero-avatar" />
            <div style={{ flex: 1, minWidth: 0 }}>
              <h1>{pet.name}, 오늘도<br />잘 지내고 있나요?</h1>
              <p className="hero-sub">
                {pet.breed} · {petAgeText(pet)} · {weightText(pet.latest_weight_kg)}
                <ChevronDownIcon stroke="currentColor" />
              </p>
            </div>
          </button>
        ) : (
          <button type="button" className="hero-pet" onClick={onAddPet}>
            <div className="pet-avatar hero-avatar"><PlusIcon /></div>
            <div style={{ flex: 1 }}>
              <h1>세븐케어에 오신 걸<br />환영해요</h1>
              <p className="hero-sub">먼저 반려동물을 등록해 주세요</p>
            </div>
          </button>
        )}
        {pet && (
          <div className="hero-stats">
            <div><b>{records.length}</b><span>오늘 기록</span></div>
            <div><b>{extra.meds ? `${medsTaken}/${extra.meds.length}` : '–'}</b><span>투약</span></div>
            <button type="button" onClick={() => onGoTab?.('report')}>
              <b>{extra.alerts ? extra.alerts.length : '–'}</b><span>확인할 알림</span>
            </button>
          </div>
        )}
      </header>

      {alert && (
        <button type="button" className="home-alert" onClick={() => onGoTab?.('report')}>
          <IconTile tone="danger" Icon={AlertIcon} size={36} />
          <span>
            <b>확인이 필요해요{extra.alerts.length > 1 ? ` · ${extra.alerts.length}건` : ''}</b>
            <small>{alert.message}</small>
          </span>
          <ChevronRightIcon stroke="currentColor" className="chev" />
        </button>
      )}

      <div className="home-cols">
      <div className="home-col">
      <div className="sec-head"><h2>오늘 기록하기</h2></div>
      <div className="quick-grid">
        {LOG_BUTTONS.map(({ type, label, Icon }) => (
          <button key={type} type="button" className="quick-btn" aria-label={label} disabled={!pet} onClick={() => onOpenForm(type)}>
            <IconTile tone={type} Icon={Icon} size={46} />
            <span className="q-label">{label}</span>
            <span className={'q-count' + (count(type) ? ' on' : '')}>{count(type) ? `${count(type)}회` : '기록 전'}</span>
          </button>
        ))}
      </div>
      </div>

      <div className="home-col">
      <div className="sec-head"><h2>오늘의 기록</h2>{records.length > 0 && <span className="sec-meta">{records.length}건</span>}</div>
      <div className="feed">
        {loading && records.length === 0 ? (
          <div className="empty-hint">불러오는 중…</div>
        ) : records.length === 0 ? (
          <div className="empty-hint">아직 오늘 기록이 없어요.<br />위 버튼으로 첫 기록을 남겨 보세요.</div>
        ) : (
          records.map((r) => {
            const { label, meta } = describeRecord(r)
            const detail = meta.split(' · ').slice(0, -1).join(' · ')
            const Icon = ICONS[r.type] ?? MealIcon
            return (
              <button key={r.id} type="button" className="feed-item" onClick={() => onOpenForm(r.type, r)} title="눌러서 수정·삭제">
                <IconTile tone={r.type} Icon={Icon} size={38} />
                <span className="feed-main">
                  <b>{label}</b>
                  {detail && <small>{detail}</small>}
                </span>
                <span className="feed-time">{hhmm(r.recorded_at)}</span>
              </button>
            )
          })
        )}
      </div>
      </div>
      </div>

      {switcherOpen && (
        <div className="sheet-overlay" onClick={(e) => e.target === e.currentTarget && setSwitcherOpen(false)}>
          <div className="sheet">
            <p className="sheet-title">보고 있는 펫 전환</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {pets.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={'pet-switch-item' + (p.id === pet?.id ? ' active' : '')}
                  onClick={() => { onSelectPet(p.id); setSwitcherOpen(false) }}
                >
                  <PetAvatar pet={p} />
                  <div>
                    <p className="name">{p.name}</p>
                    <p className="sub">{p.breed} · {petAgeText(p)}</p>
                  </div>
                </button>
              ))}
            </div>
            <button type="button" className="chip" style={{ width: '100%', marginTop: 10 }} onClick={() => setSwitcherOpen(false)}>
              닫기
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
