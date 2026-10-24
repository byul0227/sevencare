import { useCallback, useEffect, useState } from 'react'
import { IconTile, PageHead, Ring } from '../components/common.jsx'
import { AlertIcon, CheckIcon, FileIcon, MealIcon, PoopIcon, WeightIcon } from '../components/Icons.jsx'
import WeightChart from '../components/WeightChart.jsx'
import { api } from '../lib/api.js'

// 데모 버튼은 개발 서버(npm run dev)에서만 보여요
const SHOW_DEMO = Boolean(import.meta.env?.DEV)
const ALERT_TITLES = { meal_drop: '식사량 감소', weight_drop: '체중 감소', poop_blood: '혈변 · 점액 기록' }
const ALERT_ICONS = { meal_drop: MealIcon, weight_drop: WeightIcon, poop_blood: PoopIcon }

export default function ReportScreen({ pet, onToast, onDataChanged, onExport }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!pet) return
    setLoading(true)
    try {
      setReport(await api.getReport(pet.id))
    } catch (e) {
      onToast(e.message, true)
    } finally {
      setLoading(false)
    }
  }, [pet?.id, onToast]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  async function runDemo(action) {
    setBusy(true)
    try {
      const res = action === 'create' ? await api.createDemoHistory(pet.id) : await api.deleteDemoHistory(pet.id)
      await Promise.all([load(), onDataChanged?.()])
      onToast(action === 'create' ? `데모 기록 ${res.created}개를 만들었어요` : `데모 기록 ${res.deleted}개를 지웠어요`)
    } catch (e) {
      onToast(e.message, true)
    } finally {
      setBusy(false)
    }
  }

  if (!pet) {
    return (
      <div className="screen">
        <PageHead title="건강 리포트" />
        <div className="calm-banner"><p>반려동물을 먼저 등록하면 리포트를 볼 수 있어요.</p></div>
      </div>
    )
  }

  const r = report
  const hasData = r && r.record_count > 0
  const ws = r?.weight_series.filter((p) => p.weight_kg != null) ?? []
  const wFirst = ws[0]?.weight_kg
  const wLast = ws[ws.length - 1]?.weight_kg
  const wc = r?.weight_change_pct

  return (
    <div className="screen">
      <PageHead title="건강 리포트" sub={`${pet.name}의 최근 ${r?.weeks ?? 4}주 변화`}
        right={<span className="pill">최근 {r?.weeks ?? 4}주</span>} />

      {loading && !r ? (
        <div className="calm-banner"><p>리포트를 계산하고 있어요…</p></div>
      ) : !hasData ? (
        <div className="calm-banner"><p>아직 기록이 없어요. 홈에서 식사·배변·체중을 기록하면 여기에 추이가 쌓여요.</p></div>
      ) : r.alerts.length > 0 ? (
        <div className="alert-list">
          {r.alerts.map((a) => (
            <div key={a.code} className={`alert-card ${a.level}`} role="alert">
              <IconTile tone="danger" Icon={ALERT_ICONS[a.code] ?? AlertIcon} size={38} />
              <div>
                <p className="t">{ALERT_TITLES[a.code] ?? '확인이 필요해요'}</p>
                <p className="m">{a.message}</p>
                {a.source && <a className="alert-source" href={a.source_url} target="_blank" rel="noreferrer">근거 · {a.source}</a>}
              </div>
            </div>
          ))}
          <p className="disclaimer">기록을 바탕으로 한 참고용 알림이며, 수의사의 진단을 대신하지 않아요.</p>
        </div>
      ) : (
        <div className="calm-banner ok">
          <CheckIcon />
          <p>최근 {r.weeks}주 동안 눈에 띄는 변화는 없어요. 지금처럼 꾸준히 기록해 주세요.</p>
        </div>
      )}

      {r && (
        <>
          <div className="card chart-card">
            <div className="chart-head">
              <div>
                <p className="label">주별 평균 체중</p>
                <p className="big">{wLast != null ? <>{wLast}<small>kg</small></> : '–'}</p>
              </div>
              {wc != null && (
                <span className={'delta ' + (wc <= -5 || wc >= 5 ? 'bad' : 'ok')}>
                  {wc > 0 ? '▲' : wc < 0 ? '▼' : ''} {Math.abs(wc)}%
                  {wFirst != null && <small>{wFirst}kg → {wLast}kg</small>}
                </span>
              )}
            </div>
            <WeightChart points={r.weight_series} />
          </div>

          <div className="stat-grid">
            <div className="stat-card">
              <Ring size={56} stroke={6} value={r.meal_avg_pct} color="var(--meal)">{r.meal_avg_pct != null ? `${r.meal_avg_pct}%` : '–'}</Ring>
              <div>
                <p className="label">평균 식사량</p>
                <p className="sub">식사 기록 {r.meal_count}회</p>
              </div>
            </div>
            <div className="stat-card">
              <Ring size={56} stroke={6} value={r.poop_normal_pct} color="var(--green)">{r.poop_normal_pct != null ? `${r.poop_normal_pct}%` : '–'}</Ring>
              <div>
                <p className="label">배변 정상</p>
                <p className="sub">배변 기록 {r.poop_count}회</p>
              </div>
            </div>
          </div>
        </>
      )}

      <div style={{ padding: '4px 20px 20px', marginTop: 'auto' }}>
        <button type="button" className="primary-btn" onClick={onExport}>
          <FileIcon />
          병원 지참용 리포트 내보내기
        </button>
        {SHOW_DEMO && (
          <div className="demo-row">
            <button type="button" disabled={busy} onClick={() => runDemo('create')}>데모: 지난 5주 기록 채우기</button>
            <button type="button" disabled={busy} onClick={() => runDemo('delete')}>데모 기록 지우기</button>
          </div>
        )}
      </div>
    </div>
  )
}
