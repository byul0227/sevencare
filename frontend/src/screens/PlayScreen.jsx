import { useEffect, useRef, useState } from 'react'
import DogCharacter, { earTypeFor } from '../components/DogCharacter.jsx'
import { IconTile, PageHead, PetAvatar } from '../components/common.jsx'
import { BallIcon, BoneIcon, HeartIcon, MealIcon, WalkIcon } from '../components/Icons.jsx'
import { api } from '../lib/api.js'

const ACTIONS = [
  { id: 'treat', label: '간식 주기', Icon: BoneIcon, ms: 1600, tone: 'meal' },
  { id: 'walk', label: '산책 가기', Icon: WalkIcon, ms: 3000, tone: 'green' },
  { id: 'ball', label: '공놀이', Icon: BallIcon, ms: 1800, tone: 'weight' },
  { id: 'pet', label: '쓰다듬기', Icon: HeartIcon, ms: 1500, tone: 'danger' },
]
const ACTION_LINES = { treat: '냠냠! 맛있어요', walk: '산책 최고! 킁킁', ball: '공 잡았다!', pet: '헤헤, 좋아요' }
const EARN_KINDS = [['meal', '식사'], ['poop', '배변'], ['weight', '체중'], ['med', '투약']]

function waitText(iso) {
  const min = Math.max(1, Math.ceil((new Date(iso).getTime() - Date.now()) / 60000))
  return min >= 60 ? `${Math.floor(min / 60)}시간 ${min % 60}분 뒤` : `${min}분 뒤`
}

function Meter({ label, value, cls, Icon }) {
  return (
    <div className="meter">
      <div className="meter-top"><span><Icon stroke="currentColor" />{label}</span><span>{value}</span></div>
      <div className="meter-bar"><div className={`meter-fill ${cls}`} style={{ width: `${value}%` }} /></div>
    </div>
  )
}

/** 놀이 탭: 가상 강아지와 놀기. 간식은 진짜 돌봄 기록으로 모아요 */
export default function PlayScreen({ pet, onToast }) {
  const [state, setState] = useState(null)
  const [action, setAction] = useState(null)
  const [busy, setBusy] = useState(false)
  const timer = useRef()

  useEffect(() => {
    if (!pet) return
    const load = () => api.getPlay(pet.id).then(setState).catch((e) => onToast(e.message, true))
    load()
    const id = setInterval(load, 60000) // 시간이 지나면 수치가 조금씩 줄어서 1분마다 갱신
    return () => { clearInterval(id); clearTimeout(timer.current) }
  }, [pet?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!pet) {
    return (
      <div className="screen">
        <PageHead title="놀이" />
        <div className="calm-banner"><p>반려동물을 먼저 등록하면 같이 놀 수 있어요.</p></div>
      </div>
    )
  }

  async function act(a) {
    if (busy) return
    setBusy(true)
    try {
      const next = await api.playAction(pet.id, a.id)
      setState(next)
      setAction(a.id)
      clearTimeout(timer.current)
      timer.current = setTimeout(() => setAction(null), a.ms)
    } catch (e) {
      onToast(e.message, true)
    } finally {
      setBusy(false)
    }
  }

  const s = state
  const disabledReason = (id) => {
    if (!s) return '…'
    if (id === 'treat' && s.treats_available <= 0) return '간식 없음'
    if (id === 'walk' && s.walk_ready_at) return waitText(s.walk_ready_at)
    if (id === 'ball' && s.ball_ready_at) return waitText(s.ball_ready_at)
    return null
  }

  return (
    <div className="screen">
      <PageHead title="놀이" sub="기록하면 간식이 생겨요"
        right={s && <span className="pill brand"><BoneIcon stroke="currentColor" />간식 {s.treats_available}개</span>} />
      <div className="play-scene">
        <div className="sun" /><div className="cloud c1" /><div className="cloud c2" />
        <div className="scene-badge">
          <PetAvatar pet={pet} size={30} />
          <span>{pet.name}</span>
        </div>
        {s && <div className="speech">{action ? ACTION_LINES[action] : s.says}</div>}
        <div className={`dog-wrap${action ? ` act-${action}` : ''}`}>
          <DogCharacter color={pet.photo_color || undefined} ears={earTypeFor(pet.breed)}
            mood={s?.mood ?? 'happy'} action={action} />
        </div>
        {action === 'treat' && <BoneIcon className="fx fx-bone" />}
        {action === 'ball' && <div className="fx fx-ball"><BallIcon /></div>}
        {action === 'pet' && (
          <>
            <HeartIcon className="fx fx-heart h1" />
            <HeartIcon className="fx fx-heart h2" />
            <HeartIcon className="fx fx-heart h3" />
          </>
        )}
        {action === 'walk' && <div className="fx fx-ground" />}
      </div>

      <div className="meter-grid">
        <Meter label="행복도" value={s?.happiness ?? 0} cls="happy" Icon={HeartIcon} />
        <Meter label="포만감" value={s?.fullness ?? 0} cls="full" Icon={MealIcon} />
      </div>

      {s && (
        <div className="treat-box">
          <div className="treat-top">
            <BoneIcon />
            <span><b>간식 {s.treats_available}개</b> · 오늘 {s.treats_earned}/{s.treats_max}개 모음</span>
          </div>
          <p className="q-hint" style={{ margin: '6px 0 8px' }}>오늘 진짜 돌봄 기록을 남기면 간식이 생겨요. 기록 종류마다 1개, 케어 체크 1번마다 1개예요.</p>
          <div className="earn-chips">
            {EARN_KINDS.map(([k, label]) => (
              <span key={k} className={'earn-chip' + (s.earned_from.record_types.includes(k) ? ' on' : '')}>{label}</span>
            ))}
            <span className={'earn-chip' + (s.earned_from.care_checks ? ' on' : '')}>케어 체크 {s.earned_from.care_checks}회</span>
          </div>
        </div>
      )}

      <div className="play-grid">
        {ACTIONS.map((a) => {
          const reason = disabledReason(a.id)
          return (
            <button key={a.id} type="button" className="play-btn" disabled={Boolean(reason) || busy} onClick={() => act(a)}>
              <IconTile tone={a.tone} Icon={a.Icon} size={40} />
              <span>
                {a.label}
                {reason && reason !== '…' && <small>{reason}</small>}
              </span>
            </button>
          )
        })}
      </div>

      <p className="scale-source" style={{ margin: '14px 20px 24px' }}>
        가상 간식이에요. 실제 간식 양은 체중과 BCS를 보고 챙겨 주세요.
      </p>
    </div>
  )
}
