import { useEffect, useRef, useState } from 'react'
import { IconTile, PageHead, TopBar } from '../components/common.jsx'
import { AlertIcon, ChatIcon, ChevronRightIcon, InfoIcon, MapPinIcon, MealIcon, ScaleIcon, SparkIcon } from '../components/Icons.jsx'
import { api } from '../lib/api.js'

const shortDate = (iso) => new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric' }).format(new Date(iso))

function HubCard({ title, badge, desc, onClick, tone, Icon }) {
  return (
    <div className="care-card hub-card" role="button" tabIndex={0} onClick={onClick} onKeyDown={(e) => e.key === 'Enter' && onClick()}>
      <div className="care-row">
        <IconTile tone={tone} Icon={Icon} size={44} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="care-card-top">
            <span className="care-title">{title}</span>
            <span className="care-badge">{badge}</span>
          </div>
          <p className="care-desc">{desc}</p>
        </div>
        <ChevronRightIcon stroke="currentColor" className="chev" />
      </div>
    </div>
  )
}

export function AiHubScreen({ pet, onOpen }) {
  const [ai, setAi] = useState(null)
  useEffect(() => { api.getAiStatus().then(setAi).catch(() => setAi({ available: false })) }, [])
  const name = pet?.name ?? '반려동물'

  if (!pet) {
    return (
      <div className="screen">
        <PageHead title="AI 건강" />
        <div className="calm-banner"><p>반려동물을 먼저 등록하면 AI 건강 기능을 쓸 수 있어요.</p></div>
      </div>
    )
  }
  return (
    <div className="screen">
      <PageHead title="AI 건강" sub={`${name}의 기록을 참고하는 건강 도우미`} />
      <button type="button" className="ai-hero" onClick={() => onOpen('chat')}>
        <span className="ai-hero-ic"><SparkIcon /></span>
        <span className="ai-hero-t">AI 건강 상담</span>
        <span className="ai-hero-d">궁금한 증상을 말하면 {name}의 최근 식사·배변·체중·투약 기록을 참고해서 답해 드려요.</span>
        <span className="ai-hero-q">
          <span>"요즘 밥을 남기는데 괜찮을까요?"</span>
        </span>
        <span className="ai-hero-cta">
          <ChatIcon stroke="currentColor" />
          {ai == null ? '확인 중…' : ai.available ? '대화 시작하기' : '연결 준비 중 · 설정 보기'}
        </span>
      </button>
      <div className="sec-head"><h2>건강 도구</h2></div>
      <div className="wide-grid" style={{ padding: '0 20px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <HubCard title="사료 성분 분석" badge="NEW" tone="meal" Icon={MealIcon}
          desc={`성분표 사진으로 ${name}에게 맞는 사료인지 확인`} onClick={() => onOpen('food')} />
        <HubCard title="비만도 체크" badge="BCS" tone="weight" Icon={ScaleIcon}
          desc="체형 점수와 품종 표준 체중으로 비만도 확인" onClick={() => onOpen('body')} />
        <HubCard title="증상 정보" badge="출처 포함" tone="poop" Icon={InfoIcon}
          desc="흔한 증상별로 병원에 가야 할 신호 정리" onClick={() => onOpen('info')} />
        <HubCard title="내 주변 동물병원" badge="지도" tone="green" Icon={MapPinIcon}
          desc="담당 병원과 가까운 동물병원 찾기" onClick={() => onOpen('vets')} />
      </div>
    </div>
  )
}

export function BodyCheckScreen({ pet, onBack, onCheckBcs, onToast }) {
  const [data, setData] = useState(null)
  useEffect(() => { api.getBodyCheck(pet.id).then(setData).catch((e) => onToast(e.message, true)) }, [pet.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const std = data?.breed_standard
  const w = data?.weight_kg
  // 막대 위치: 표준 범위를 가운데 60%에 두고 현재 체중을 표시
  let pct = null
  if (std && w != null) {
    const lo = std.min_kg ?? 0
    const span = std.max_kg - lo || 1
    pct = Math.max(2, Math.min(98, 20 + ((w - lo) / span) * 60))
  }
  const posText = { below: '표준 범위보다 가벼워요', within: '표준 범위 안이에요', above: '표준 범위보다 무거워요' }
  const bcs = data?.bcs_latest

  return (
    <div className="screen">
      <TopBar title="비만도 체크" onBack={onBack} />
      <div className="form-body">
        {data == null ? <div className="empty-hint">불러오는 중…</div> : (
          <>
            <div className={`card bcs-card ${bcs?.band?.level ?? ''}`}>
              <p className="k">체형 점수 (BCS · 9점 척도)</p>
              {bcs ? (
                <>
                  <p className="big">{bcs.score}<span>/9</span> · {bcs.band.label}</p>
                  <p className="advice">{bcs.band.advice}</p>
                  <p className="k" style={{ marginTop: 8 }}>{shortDate(bcs.checked_at)} 체크 · 4~5점이 이상적인 체형이에요</p>
                </>
              ) : (
                <p className="advice">아직 체크하지 않았어요. 갈비뼈·허리·배 라인을 보고 1분이면 체크할 수 있어요.</p>
              )}
              <button type="button" className="primary-btn" style={{ marginTop: 12 }} onClick={() => onCheckBcs(bcs)}>
                {bcs ? '다시 체크하기' : 'BCS 체크하기'}
              </button>
            </div>

            <div className="card" style={{ background: 'var(--bg-sunk)', border: 'none' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                <div>
                  <p className="k-label">현재 체중</p>
                  <p className="head-num">{w != null ? `${w}kg` : '미측정'}</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <p className="k-label">{std ? `${std.name} 표준` : `${data.breed} 표준`}</p>
                  <p style={{ fontSize: 14, fontWeight: 500, margin: '4px 0 0' }}>
                    {std ? (std.max_only ? `${std.max_kg}kg 이하` : `${std.min_kg} ~ ${std.max_kg}kg`) : '자료 없음'}
                  </p>
                </div>
              </div>
              {pct != null && (
                <>
                  <div className="std-bar" aria-hidden="true">
                    <div className="std-range" />
                    <div className="std-mark" style={{ left: `${pct}%` }} />
                  </div>
                  <p className="k-label" style={{ marginTop: 6 }}>{posText[data.position]}</p>
                </>
              )}
              {std?.note && <p className="k-label" style={{ marginTop: 8 }}>{std.note}</p>}
              {!std && <p className="k-label" style={{ marginTop: 8 }}>품종 표준 체중 자료가 없는 품종이에요. BCS로 판단해 주세요.</p>}
            </div>

            <p className="scale-source">
              품종 표준 체중은 도그쇼 기준 성견 체중이라 개체차가 커요. 비만도는 체중보다 BCS로 판단하는 게 정확해요.<br />
              출처: <a href="https://wsava.org/wp-content/uploads/2020/01/Body-Condition-Score-Dog.pdf" target="_blank" rel="noreferrer">WSAVA Body Condition Score</a>
              {std && <> · <a href={std.source_url} target="_blank" rel="noreferrer">{std.source}</a></>}
            </p>
          </>
        )}
      </div>
    </div>
  )
}

/** 증상 정보 */
export function HealthInfoScreen({ onBack, onToast }) {
  const [items, setItems] = useState(null)
  const [open, setOpen] = useState(null)
  useEffect(() => { api.getHealthInfo().then(setItems).catch((e) => onToast(e.message, true)) }, []) // eslint-disable-line react-hooks/exhaustive-deps
  const item = items?.find((i) => i.id === open)

  return (
    <div className="screen">
      <TopBar title="증상 정보" onBack={onBack} />
      <div style={{ padding: '0 22px 8px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <p className="field-label" style={{ margin: '0 0 4px' }}>궁금한 증상을 골라 주세요</p>
        {items == null ? <div className="empty-hint">불러오는 중…</div> : items.map((i) => (
          <button key={i.id} type="button" className={'log-btn' + (open === i.id ? ' selected' : '')}
            style={{ width: '100%' }} onClick={() => setOpen(open === i.id ? null : i.id)}>
            {i.title}
          </button>
        ))}
      </div>
      {item && (
        <div className="info-detail">
          <p className="summary">{item.summary}</p>
          <p className="h">이럴 땐 병원에 연락하세요</p>
          <ul>{item.when_to_vet.map((t) => <li key={t}>{t}</li>)}</ul>
          {item.emergency && (
            <>
              <p className="h urgent"><AlertIcon /> 함께 보이면 바로 병원으로</p>
              <ul>{item.emergency.map((t) => <li key={t}>{t}</li>)}</ul>
            </>
          )}
          {item.home_tips && (
            <>
              <p className="h">집에서 해볼 수 있는 것</p>
              <ul>{item.home_tips.map((t) => <li key={t}>{t}</li>)}</ul>
            </>
          )}
          <p className="src">
            출처: {item.sources.map((s, n) => (
              <span key={s.url}>{n > 0 && ' · '}<a href={s.url} target="_blank" rel="noreferrer">{s.name}</a></span>
            ))}
          </p>
        </div>
      )}
      <p className="scale-source" style={{ margin: '4px 22px 24px' }}>
        일반적인 안내이며 진단을 대신하지 않아요. 품종별 주의 질환 정보는 출처를 확인하며 추가할 예정이에요.
      </p>
    </div>
  )
}

/** 내 주변 동물병원 (지도 앱 검색 링크) */
export function VetFinderScreen({ pet, onBack }) {
  const kakao = (q) => `https://map.kakao.com/link/search/${encodeURIComponent(q)}`
  const naver = (q) => `https://map.naver.com/p/search/${encodeURIComponent(q)}`
  const links = [
    { title: '근처 동물병원', q: '동물병원' },
    { title: '24시 동물병원', q: '24시 동물병원' },
  ]
  return (
    <div className="screen">
      <TopBar title="내 주변 동물병원" onBack={onBack} />
      <div style={{ padding: '6px 22px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {pet.hospital ? (
          <div className="card">
            <p style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>{pet.hospital}</p>
            <p style={{ fontSize: 12, color: 'var(--pine-500)', margin: '4px 0 10px' }}>{pet.name} 담당 병원</p>
            <div style={{ display: 'flex', gap: 8 }}>
              <a className="chip active link-chip" href={kakao(pet.hospital)} target="_blank" rel="noreferrer">카카오맵</a>
              <a className="chip link-chip" href={naver(pet.hospital)} target="_blank" rel="noreferrer">네이버 지도</a>
            </div>
          </div>
        ) : (
          <div className="empty-hint">마이펫에서 담당 병원을 등록하면 여기서 바로 찾을 수 있어요.</div>
        )}
        {links.map((l) => (
          <div key={l.q} className="card">
            <p style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>{l.title}</p>
            <p style={{ fontSize: 12, color: 'var(--pine-500)', margin: '4px 0 10px' }}>지도 앱에서 현재 위치 기준으로 검색해요</p>
            <div style={{ display: 'flex', gap: 8 }}>
              <a className="chip link-chip" href={kakao(l.q)} target="_blank" rel="noreferrer">카카오맵</a>
              <a className="chip link-chip" href={naver(l.q)} target="_blank" rel="noreferrer">네이버 지도</a>
            </div>
          </div>
        ))}
        <p className="scale-source">응급 상황이면 이동 전에 병원에 먼저 전화해서 진료 가능한지 확인하세요.</p>
      </div>
    </div>
  )
}

/** AI 건강 상담 채팅 */
export function AiChatScreen({ pet, onBack }) {
  const [status, setStatus] = useState(null)
  const [messages, setMessages] = useState([
    { role: 'assistant', content: `안녕하세요! ${pet.name}의 최근 기록을 참고해서 답변드릴게요. 어떤 점이 궁금하세요?` },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef(null)

  useEffect(() => { api.getAiStatus().then(setStatus).catch(() => setStatus({ available: false })) }, [])
  useEffect(() => { listRef.current?.scrollTo(0, listRef.current.scrollHeight) }, [messages, sending])

  async function send() {
    const text = input.trim()
    if (!text || sending) return
    const next = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setInput('')
    setSending(true)
    try {
      // 첫 인사말(assistant)은 빼고, 최근 20개까지만 보내요
      const history = next.slice(1).slice(-20)
      const res = await api.aiChat(pet.id, history)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: e.message, error: true }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="screen">
      <TopBar title="AI 건강 상담" onBack={onBack} />
      {status && !status.available && (
        <div className="calm-banner" style={{ margin: '6px 22px 4px' }}>
          <p>
            <strong>AI 연결이 아직 안 됐어요</strong><br />
            <code>backend/.env</code> 파일에 <code>GEMINI_API_KEY=발급받은 키</code> 를 넣고 백엔드를 다시 켜 주세요. 키는 Google AI Studio에서 무료로 받을 수 있어요.
          </p>
        </div>
      )}
      <div ref={listRef} className="chat-list">
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role === 'user' ? 'user' : 'ai'}${m.error ? ' error' : ''}`}>{m.content}</div>
        ))}
        {sending && <div className="chat-bubble ai typing">기록을 살펴보는 중…</div>}
      </div>
      <p className="scale-source" style={{ margin: '0 22px' }}>AI 답변은 참고용이며 진단을 대신하지 않아요. 응급 상황이면 바로 병원에 연락하세요.</p>
      <div className="chat-input-row">
        <input type="text" placeholder="예: 요즘 계단을 잘 못 올라가요" value={input} maxLength={2000}
          onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && !e.nativeEvent.isComposing && send()} />
        <button type="button" className="send-btn" onClick={send} disabled={sending || !input.trim()} aria-label="보내기">
          <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
        </button>
      </div>
    </div>
  )
}
