import { useEffect, useState } from 'react'
import { IconTile, PageHead } from '../components/common.jsx'
import { BrainIcon, ChevronRightIcon, HeartIcon, WalkIcon } from '../components/Icons.jsx'
import { api } from '../lib/api.js'
import { MedScheduleSection } from './MedScreens.jsx'

const KINDS = ['mobility', 'cognitive', 'qol']
const KIND_LOOK = {
  mobility: { tone: 'green', Icon: WalkIcon },
  cognitive: { tone: 'med', Icon: BrainIcon },
  qol: { tone: 'meal', Icon: HeartIcon },
}

/** 점수 막대: 낮을수록 좋은 척도(CCDR)는 뒤집지 않고 그대로, 색은 결과 단계로 */
function ScoreBar({ kind, check }) {
  if (!check) return null
  let pct
  if (kind === 'mobility') {
    const vals = Object.values(check.answers)
    pct = (vals.filter((v) => v === 0).length / vals.length) * 100
  } else {
    pct = (check.score / check.max_score) * 100
  }
  return (
    <div className="score-bar"><div className={`score-fill ${check.band?.level ?? 'ok'}`} style={{ width: `${pct}%` }} /></div>
  )
}
const shortDate = (iso) => new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric' }).format(new Date(iso))
const daysSince = (iso) => Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)

function badgeText(kind, summary) {
  const latest = summary?.[kind]
  if (kind === 'mobility') {
    if (!summary?.mobility_today) return '오늘 미기록'
    const good = Object.values(latest.answers).filter((v) => v === 0).length
    return `오늘 ${good}/${Object.keys(latest.answers).length} 양호`
  }
  if (!latest) return '미기록'
  if (daysSince(latest.checked_at) >= 30) return '다시 점검할 때예요'
  return `${latest.score}/${latest.max_score}점`
}

function ResultLine({ check }) {
  if (!check?.band) return null
  return (
    <p className={`care-result ${check.band.level}`}>
      {shortDate(check.checked_at)} · {check.band.label} — {check.band.advice}
    </p>
  )
}

/** 케어 탭: 노령견 특화 관찰 기록 */
export default function CareScreen({ pet, scales, onOpenCheck, onManageMeds, onToast }) {
  const [summary, setSummary] = useState(null)

  useEffect(() => {
    if (!pet) return
    let alive = true
    api.getCareSummary(pet.id)
      .then((s) => alive && setSummary(s))
      .catch((e) => onToast(e.message, true))
    return () => { alive = false }
  }, [pet?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!pet) {
    return (
      <div className="screen">
        <PageHead title="케어 체크" />
        <div className="calm-banner"><p>반려동물을 먼저 등록하면 케어 체크를 할 수 있어요.</p></div>
      </div>
    )
  }

  return (
    <div className="screen">
      <PageHead title="케어 체크" sub="노령견에게 필요한 정기 점검" />

      <div className="wide-grid" style={{ padding: '0 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {!scales ? (
          <div className="empty-hint">불러오는 중…</div>
        ) : (
          KINDS.map((kind) => {
            const scale = scales[kind]
            const look = KIND_LOOK[kind]
            return (
              <div key={kind} className="care-card" role="button" tabIndex={0}
                onClick={() => onOpenCheck(kind, summary?.[kind])}
                onKeyDown={(e) => e.key === 'Enter' && onOpenCheck(kind, summary?.[kind])}>
                <div className="care-row">
                  <IconTile tone={look.tone} Icon={look.Icon} size={44} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="care-card-top">
                      <span className="care-title">{scale.title}</span>
                      <span className="care-badge">{summary ? badgeText(kind, summary) : '…'}</span>
                    </div>
                    <p className="care-desc">{scale.description}</p>
                  </div>
                  <ChevronRightIcon stroke="currentColor" className="chev" />
                </div>
                <ScoreBar kind={kind} check={kind === 'mobility' && !summary?.mobility_today ? null : summary?.[kind]} />
                <ResultLine check={summary?.[kind]} />
              </div>
            )
          })
        )}
      </div>

      <MedScheduleSection pet={pet} onManage={onManageMeds} onToast={onToast} />
    </div>
  )
}
