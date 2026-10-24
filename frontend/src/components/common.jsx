import { api } from '../lib/api.js'
import { AiIcon, BackIcon, CareIcon, CheckIcon, HomeIcon, LeafIcon, PawIcon, ReportIcon } from './Icons.jsx'

export function TopBar({ title, onBack, right }) {
  return (
    <div className="topbar" style={right ? { justifyContent: 'space-between' } : undefined}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {onBack && (
          <button type="button" className="back" onClick={onBack} aria-label="뒤로">
            <BackIcon stroke="currentColor" />
          </button>
        )}
        <h1>{title}</h1>
      </div>
      {right}
    </div>
  )
}

/** 펫 동그라미 아바타: 사진이 있으면 사진, 없으면 잎 아이콘 */
export function PetAvatar({ pet, size, className = 'pet-avatar' }) {
  const src = api.photoUrl(pet)
  return (
    <div className={className + (src ? ' has-photo' : '')} style={size ? { width: size, height: size } : undefined}>
      {src ? <img src={src} alt={`${pet.name} 사진`} /> : <PawIcon />}
    </div>
  )
}

/** 칩 단일 선택. options: [{ value, label }] 또는 문자열 배열 */
export function ChipGroup({ options, value, onChange, columns, compact, vertical }) {
  const opts = options.map((o) => (typeof o === 'string' ? { value: o, label: o } : o))
  return (
    <div className={'chip-row' + (compact ? ' compact' : '') + (vertical ? ' vertical' : '')} style={{ gridTemplateColumns: `repeat(${vertical ? 1 : columns ?? opts.length}, 1fr)` }}>
      {opts.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          className={'chip' + (o.value === value ? ' active' : '')}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Toast({ toast }) {
  return (
    <div className={'toast' + (toast ? ' show' : '') + (toast?.error ? ' error' : '')} role="status">
      <CheckIcon />
      <span>{toast?.text ?? ''}</span>
    </div>
  )
}

export const TABS = [
  { id: 'home', label: '홈', Icon: HomeIcon },
  { id: 'report', label: '리포트', Icon: ReportIcon },
  { id: 'care', label: '케어', Icon: CareIcon },
  { id: 'ai', label: 'AI건강', Icon: AiIcon },
  // 놀이 탭은 발표 범위에서 빼서 숨겨 둠 (PlayScreen 코드는 남아 있어요). 다시 쓰려면 아래 줄 주석 해제
  // { id: 'play', label: '놀이', Icon: PawIcon },
  { id: 'pets', label: '마이펫', Icon: LeafIcon },
]

export function TabBar({ active, onChange }) {
  return (
    <nav className="tabbar">
      <div className="side-brand"><span className="side-logo"><PawIcon /></span><b>세븐케어</b></div>
      {TABS.map(({ id, label, Icon }) => (
        <button
          key={id}
          type="button"
          className={'tab' + (active === id ? ' active' : '')}
          onClick={() => onChange(id)}
        >
          <span className="tab-ic"><Icon stroke="currentColor" /></span>
          <span className="tab-label">{label}</span>
        </button>
      ))}
    </nav>
  )
}

// ---------- v2 리디자인 공통 조각 ----------

/** 기록 종류별 색 아이콘 타일 (meal · poop · weight · med · green · brand) */
export function IconTile({ tone = 'brand', Icon, size = 40 }) {
  return (
    <span className={`ic-tile tone-${tone}`} style={{ width: size, height: size }}>
      <Icon />
    </span>
  )
}

/** 원형 진행 게이지. value 0~100 */
export function Ring({ value, size = 64, stroke = 7, color = 'var(--gold-500)', children }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const v = Math.max(0, Math.min(100, value ?? 0))
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--sage-line)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <div className="ring-label">{children}</div>
    </div>
  )
}

/** 큰 제목 + 작은 설명이 있는 탭 헤더 */
export function PageHead({ title, sub, right }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {sub && <p>{sub}</p>}
      </div>
      {right}
    </div>
  )
}
