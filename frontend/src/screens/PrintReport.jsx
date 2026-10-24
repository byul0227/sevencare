import { useEffect, useState } from 'react'
import WeightChart from '../components/WeightChart.jsx'
import { api } from '../lib/api.js'
import { petAgeText, petGenderText, toDateStr, weightText } from '../lib/format.js'

const fmtDate = (iso) => new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(iso.length === 10 ? `${iso}T00:00:00` : iso))
const fmtShort = (iso) => new Intl.DateTimeFormat('ko-KR', { month: 'numeric', day: 'numeric' }).format(new Date(iso.length === 10 ? `${iso}T00:00:00` : iso))
const fmtDateTime = (iso) => `${fmtShort(iso)} ${iso.slice(11, 16)}`
const TYPE = { meal: '식사', poop: '배변', weight: '체중', med: '투약' }
const CARE_ROWS = [
  { kind: 'cognitive', label: '인지기능 (CCDR)' },
  { kind: 'qol', label: '삶의 질 (HHHHHMM)' },
  { kind: 'bcs', label: '체형 점수 (BCS)' },
  { kind: 'mobility', label: '거동 간이 체크 (불편 점수)' },
]

/** 병원 지참용 리포트 — 화면에서 확인하고 브라우저 인쇄로 PDF 저장 */
export default function PrintReport({ pet, onClose, onToast }) {
  const [data, setData] = useState(null)
  const [memo, setMemo] = useState('')

  useEffect(() => {
    api.getVetSummary(pet.id).then(setData).catch((e) => { onToast(e.message, true); onClose() })
    document.body.classList.add('printing')
    const prevTitle = document.title
    document.title = `${pet.name}_건강리포트_${toDateStr()}` // PDF 파일 이름이 돼요
    return () => { document.body.classList.remove('printing'); document.title = prevTitle }
  }, [pet.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!data) return <div className="print-wrap"><div className="print-toolbar"><span>리포트를 만드는 중…</span></div></div>

  const { pet: p, report: r, care, medications, visits, notable_records: notes } = data
  return (
    <div className="print-wrap">
      <div className="print-toolbar">
        <button type="button" className="chip" onClick={onClose}>닫기</button>
        <span>내용을 확인하고 PDF로 저장하세요. 인쇄 창에서 대상을 <b>PDF로 저장</b>으로 고르면 돼요.</span>
        <button type="button" className="primary-btn" style={{ width: 'auto', padding: '10px 18px' }} onClick={() => window.print()}>
          PDF로 저장 · 인쇄
        </button>
      </div>

      <article className="print-doc">
        <header className="doc-head">
          <div>
            <p className="doc-kicker">세븐케어 · 병원 지참용 건강 리포트</p>
            <h1>{p.name}</h1>
            <p className="doc-sub">{p.breed} · {petAgeText(p)} · {petGenderText(p)}</p>
          </div>
          <div className="doc-meta">
            <p>작성일 {fmtDate(data.generated_at)}</p>
            <p>기간 {fmtDate(r.start)} ~ {fmtDate(r.end)}</p>
          </div>
        </header>

        <section>
          <h2>기본 정보</h2>
          <table className="kv">
            <tbody>
              <tr><th>최근 체중</th><td>{weightText(p.latest_weight_kg)}</td><th>기저 질환</th><td>{p.condition || '없음'}</td></tr>
              <tr><th>담당 병원</th><td>{p.hospital || '미등록'}</td><th>다음 방문 예정</th><td>{data.next_visit ? `${fmtDate(data.next_visit.date)} (${data.next_visit.title})` : '없음'}</td></tr>
            </tbody>
          </table>
        </section>

        <section>
          <h2>기록에서 확인된 주의 신호</h2>
          {r.alerts.length === 0 ? <p className="muted">이 기간에 해당하는 알림이 없어요.</p> : (
            <ul className="alerts">
              {r.alerts.map((a) => <li key={a.code} className={a.level}>{a.message}</li>)}
            </ul>
          )}
        </section>

        <section className="two-col">
          <div>
            <h2>체중 추이 (주별 평균)</h2>
            <WeightChart points={r.weight_series} />
            <p className="muted" style={{ marginTop: 6 }}>
              {r.weight_series.map((w) => `${w.label} ${w.weight_kg ?? '–'}`).join(' · ')}
              {r.weight_change_pct != null && ` · 기간 변화 ${r.weight_change_pct > 0 ? '+' : ''}${r.weight_change_pct}%`}
            </p>
          </div>
          <div>
            <h2>식사 · 배변</h2>
            <table className="kv narrow">
              <tbody>
                <tr><th>평균 식사량</th><td>{r.meal_avg_pct != null ? `${r.meal_avg_pct}%` : '–'} <span className="muted">({r.meal_count}회 기록)</span></td></tr>
                <tr><th>배변 정상 비율</th><td>{r.poop_normal_pct != null ? `${r.poop_normal_pct}%` : '–'} <span className="muted">({r.poop_count}회 기록)</span></td></tr>
              </tbody>
            </table>
            <p className="muted">식사량은 보호자가 고른 값(거의 안먹음 10 · 절반 50 · 대부분 80 · 전부 100%)의 평균이에요.</p>
          </div>
        </section>

        <section>
          <h2>복용 중인 약 <span className="muted">· 최근 {data.adherence_days}일 복용 기록</span></h2>
          {medications.length === 0 ? <p className="muted">등록된 약이 없어요.</p> : (
            <table className="grid">
              <thead><tr><th>약</th><th>용량</th><th>복용 시간</th><th>지시사항</th><th>복용 기록</th></tr></thead>
              <tbody>
                {medications.map((m) => (
                  <tr key={m.name}>
                    <td>{m.name}</td><td>{m.dose || '–'}</td><td>{m.times.join(', ')}</td><td>{m.instructions || '–'}</td>
                    <td>{m.total ? `${m.taken}/${m.total}회 (${m.adherence_pct}%)` : '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section>
          <h2>케어 체크 최근 결과</h2>
          <table className="grid">
            <thead><tr><th>항목</th><th>날짜</th><th>점수</th><th>해석</th></tr></thead>
            <tbody>
              {CARE_ROWS.map(({ kind, label }) => {
                const c = care[kind]
                return (
                  <tr key={kind}>
                    <td>{label}</td>
                    <td>{c ? fmtShort(c.checked_at) : '–'}</td>
                    <td>{c ? `${c.score}/${c.max_score}` : '미기록'}</td>
                    <td>{c?.band ? c.band.label : c ? '해석 기준 없음' : '–'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>

        <section>
          <h2>최근 {data.notable_days}일 특이 기록</h2>
          {notes.length === 0 ? <p className="muted">특이 기록이 없어요.</p> : (
            <table className="grid">
              <thead><tr><th>일시</th><th>종류</th><th>내용</th></tr></thead>
              <tbody>
                {notes.map((n, i) => (
                  <tr key={i}>
                    <td>{fmtDateTime(n.recorded_at)}</td><td>{TYPE[n.type]}</td>
                    <td>{[n.reason, n.note].filter(Boolean).join(' · ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section>
          <h2>최근 병원 방문</h2>
          {visits.length === 0 ? <p className="muted">기록이 없어요.</p> : (
            <table className="grid">
              <thead><tr><th>날짜</th><th>종류</th><th>내용</th><th>진단 · 처치</th></tr></thead>
              <tbody>
                {visits.map((v, i) => (
                  <tr key={i}>
                    <td>{fmtShort(v.visit_date)}</td><td>{v.category}</td>
                    <td>{v.title}{v.hospital ? ` (${v.hospital})` : ''}</td>
                    <td>{[v.diagnosis, v.treatment].filter(Boolean).join(' · ') || '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section>
          <h2>수의사에게 묻고 싶은 것</h2>
          <textarea className="memo" rows={4} value={memo} onChange={(e) => setMemo(e.target.value)}
            placeholder="인쇄 전에 적어 두세요. 예: 요즘 밤에 자꾸 깨서 돌아다녀요. 관절 영양제를 계속 먹여도 될까요?" />
          <p className="memo-print">{memo || ' '}</p>
        </section>

        <footer className="doc-foot">
          보호자가 앱에 기록한 내용을 모은 참고 자료이며, 진단을 대신하지 않아요. ·
          척도: CCDR (Salvin et al., 2011) · HHHHHMM (Villalobos) · BCS 9점 (WSAVA) · 거동 체크는 서비스 자체 간이 문항
        </footer>
      </article>
    </div>
  )
}
