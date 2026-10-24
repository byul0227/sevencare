import { useEffect, useMemo, useRef, useState } from 'react'
import { readLabel } from '../lib/ocr.js'

// 성분표 인식 정확도 측정 (개발용 페이지: /eval.html)
// 사진마다 정답을 한 번 적어 두면, 네 가지 방법으로 읽어서 "몇 칸을 맞게 읽었나"를 비교해요.

const FIELDS = [
  ['protein', '조단백질'], ['fat', '조지방'], ['fiber', '조섬유'], ['ash', '조회분'],
  ['calcium', '칼슘'], ['phosphorus', '인'], ['moisture', '수분'],
]
const METHODS = [
  { id: 'v1', name: '처음 버전', desc: '자동 배치 읽기(PSM 3) + 기본 파서' },
  { id: 'psmOnly', name: '읽기 방식만 개선', desc: '줄 단위 읽기(PSM 6) + 기본 파서' },
  { id: 'parserOnly', name: '파서만 개선', desc: 'PSM 3 + 개선 파서(표 인식·소수점 복원)' },
  { id: 'final', name: '최종 (앱과 동일)', desc: 'PSM 6 + 개선 파서, 4칸 미만이면 PSM 3 재시도' },
]
const TOL = 0.05
const STORE = 'sevencare-eval-truth'

const loadTruth = () => { try { return JSON.parse(localStorage.getItem(STORE) || '{}') } catch { return {} } }
const saveTruth = (t) => { try { localStorage.setItem(STORE, JSON.stringify(t)) } catch { /* 저장 불가 환경 */ } }

async function parse(text, mode) {
  const res = await fetch('/api/food-label/parse', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, mode }),
  })
  if (!res.ok) throw new Error(`서버 오류 ${res.status} — 백엔드가 켜져 있는지 확인해 주세요`)
  return res.json()
}

function score(pred, truth) {
  let total = 0, correct = 0
  const cells = {}
  for (const [k] of FIELDS) {
    const t = truth[k]
    if (t === '' || t == null) continue
    total++
    const p = pred?.[k]
    const ok = p != null && Math.abs(p - Number(t)) <= TOL
    if (ok) correct++
    cells[k] = { p, ok }
  }
  return { total, correct, cells }
}

function download(name, text, type = 'text/plain') {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type }))
  a.download = name
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

export default function EvalApp() {
  const [items, setItems] = useState([])        // {name, file, url, result}
  const [truth, setTruth] = useState(loadTruth)  // {파일명: {protein: '25', ...}}
  const [running, setRunning] = useState(null)   // {i, n, step}
  const [error, setError] = useState('')
  const importRef = useRef()

  useEffect(() => saveTruth(truth), [truth])

  function addFiles(files) {
    const next = [...files].filter((f) => f.type.startsWith('image/')).map((f) => ({ name: f.name, file: f, url: URL.createObjectURL(f), result: null }))
    setItems((prev) => [...prev.filter((p) => !next.some((n) => n.name === p.name)), ...next])
  }

  const setCell = (name, k, v) => setTruth((t) => ({ ...t, [name]: { ...(t[name] || {}), [k]: v.replace(',', '.').replace(/[^0-9.]/g, '') } }))
  const filled = (name) => FIELDS.some(([k]) => truth[name]?.[k])

  async function run() {
    setError('')
    const targets = items.filter((it) => filled(it.name))
    if (!targets.length) { setError('정답을 적은 사진이 없어요. 사진마다 포장에 적힌 값을 먼저 입력해 주세요.'); return }
    try {
      for (let i = 0; i < targets.length; i++) {
        const it = targets[i]
        const t0 = performance.now()
        setRunning({ i: i + 1, n: targets.length, step: '줄 단위(PSM 6)로 읽는 중' })
        const text6 = await readLabel(it.file, null, '6')
        setRunning({ i: i + 1, n: targets.length, step: '자동 배치(PSM 3)로 읽는 중' })
        const text3 = await readLabel(it.file, null, '3')
        const [b3, b6, f3, f6] = await Promise.all([parse(text3, 'basic'), parse(text6, 'basic'), parse(text3, 'full'), parse(text6, 'full')])
        const n6 = Object.keys(f6.nutrients).length
        const final = n6 >= 4 || Object.keys(f3.nutrients).length <= n6 ? f6 : f3
        const result = {
          ms: Math.round(performance.now() - t0),
          text6, text3,
          preds: { v1: b3.nutrients, psmOnly: b6.nutrients, parserOnly: f3.nutrients, final: final.nutrients },
          corrected: final.found.filter((f) => f.corrected).map((f) => f.key),
        }
        setItems((prev) => prev.map((p) => (p.name === it.name ? { ...p, result } : p)))
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(null)
    }
  }

  const summary = useMemo(() => {
    const done = items.filter((it) => it.result && filled(it.name))
    const out = {}
    for (const m of METHODS) {
      let total = 0, correct = 0, perfect = 0
      for (const it of done) {
        const s = score(it.result.preds[m.id], truth[it.name])
        total += s.total; correct += s.correct
        if (s.total && s.correct === s.total) perfect++
      }
      out[m.id] = { total, correct, perfect, pct: total ? (correct / total) * 100 : null }
    }
    let fixedTotal = 0, fixedRight = 0
    for (const it of done) {
      const s = score(it.result.preds.final, truth[it.name])
      for (const k of it.result.corrected) {
        if (s.cells[k]) { fixedTotal++; if (s.cells[k].ok) fixedRight++ }
      }
    }
    const avgMs = done.length ? Math.round(done.reduce((a, it) => a + it.result.ms, 0) / done.length) : null
    return { n: done.length, methods: out, fixedTotal, fixedRight, avgMs }
  }, [items, truth]) // eslint-disable-line react-hooks/exhaustive-deps

  function exportCsv() {
    const head = ['사진', ...FIELDS.map(([, l]) => `정답_${l}`), ...METHODS.flatMap((m) => FIELDS.map(([, l]) => `${m.name}_${l}`)), ...METHODS.map((m) => `${m.name}_맞은칸`), '시간ms']
    const rows = items.filter((it) => it.result).map((it) => {
      const t = truth[it.name] || {}
      return [
        it.name, ...FIELDS.map(([k]) => t[k] ?? ''),
        ...METHODS.flatMap((m) => FIELDS.map(([k]) => it.result.preds[m.id][k] ?? '')),
        ...METHODS.map((m) => { const s = score(it.result.preds[m.id], t); return `${s.correct}/${s.total}` }),
        it.result.ms,
      ]
    })
    const csv = [head, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
    download('성분표_인식_정확도.csv', '﻿' + csv, 'text/csv')
  }

  function importTruth(e) {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    f.text().then((s) => setTruth((t) => ({ ...t, ...JSON.parse(s) }))).catch(() => setError('정답 파일을 읽지 못했어요'))
  }

  return (
    <div className="ev">
      <header className="ev-head">
        <div>
          <p className="ev-kicker">세븐케어 · 개발용</p>
          <h1>성분표 인식 정확도 측정</h1>
          <p className="ev-sub">사진마다 포장에 적힌 정답을 한 번 적어 두고 측정하면, 네 가지 방법의 정확도를 비교해요. 값이 ±{TOL} 안이면 맞은 걸로 봐요.</p>
        </div>
        <div className="ev-actions">
          <label className="ev-btn primary">
            사진 추가
            <input type="file" accept="image/*" multiple hidden onChange={(e) => { addFiles(e.target.files); e.target.value = '' }} />
          </label>
          <button type="button" className="ev-btn" onClick={() => download('성분표_정답.json', JSON.stringify(truth, null, 2), 'application/json')}>정답 저장</button>
          <button type="button" className="ev-btn" onClick={() => importRef.current.click()}>정답 불러오기</button>
          <input ref={importRef} type="file" accept="application/json" hidden onChange={importTruth} />
        </div>
      </header>

      {error && <p className="ev-error">{error}</p>}

      <section className="ev-summary">
        <div className="ev-sum-top">
          <h2>결과 요약 {summary.n > 0 && <span>사진 {summary.n}장 · 장당 평균 {(summary.avgMs / 1000).toFixed(1)}초</span>}</h2>
          <div className="ev-actions">
            <button type="button" className="ev-btn primary" disabled={!!running || !items.length} onClick={run}>
              {running ? `측정 중 ${running.i}/${running.n} · ${running.step}` : '전체 측정하기'}
            </button>
            <button type="button" className="ev-btn" disabled={!summary.n} onClick={exportCsv}>CSV 내보내기</button>
          </div>
        </div>
        <div className="ev-methods">
          {METHODS.map((m) => {
            const s = summary.methods[m.id]
            return (
              <div key={m.id} className={'ev-method' + (m.id === 'final' ? ' best' : '')}>
                <p className="n">{m.name}</p>
                <p className="d">{m.desc}</p>
                <p className="pct">{s.pct == null ? '–' : `${s.pct.toFixed(1)}%`}</p>
                <div className="bar"><div style={{ width: `${s.pct ?? 0}%` }} /></div>
                <p className="d">{s.total ? `${s.correct}/${s.total}칸 · 전부 맞은 사진 ${s.perfect}/${summary.n}장` : '측정 전'}</p>
              </div>
            )
          })}
        </div>
        {summary.fixedTotal > 0 && (
          <p className="ev-note">최종 방식에서 자동 보정한 칸 {summary.fixedTotal}개 중 {summary.fixedRight}개가 정답이었어요 ({((summary.fixedRight / summary.fixedTotal) * 100).toFixed(0)}%).</p>
        )}
      </section>

      {items.length === 0 ? (
        <div className="ev-empty">
          <p><b>사진 추가</b>로 성분표 사진을 여러 장 올려 주세요.</p>
          <p>사진마다 포장에 적힌 값을 칸에 적으면 이 브라우저에 자동으로 저장돼요. 파일 이름이 같으면 다음에도 불러와져요.</p>
        </div>
      ) : (
        <div className="ev-list">
          {items.map((it) => {
            const t = truth[it.name] || {}
            const r = it.result
            const s = r ? score(r.preds.final, t) : null
            return (
              <article key={it.name} className="ev-item">
                <img src={it.url} alt={it.name} />
                <div className="ev-body">
                  <div className="ev-item-top">
                    <b>{it.name}</b>
                    {s && <span className={'ev-chip ' + (s.correct === s.total ? 'ok' : 'bad')}>최종 {s.correct}/{s.total}칸</span>}
                    {r && <span className="ev-chip">{(r.ms / 1000).toFixed(1)}초</span>}
                    <button type="button" className="ev-x" onClick={() => setItems((p) => p.filter((x) => x.name !== it.name))}>빼기</button>
                  </div>
                  <table className="ev-table">
                    <thead>
                      <tr><th />{FIELDS.map(([k, l]) => <th key={k}>{l}</th>)}</tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="rowh">정답</td>
                        {FIELDS.map(([k]) => (
                          <td key={k}><input value={t[k] ?? ''} placeholder="–" inputMode="decimal" onChange={(e) => setCell(it.name, k, e.target.value)} /></td>
                        ))}
                      </tr>
                      {r && METHODS.map((m) => {
                        const sc = score(r.preds[m.id], t)
                        return (
                          <tr key={m.id} className={m.id === 'final' ? 'final' : ''}>
                            <td className="rowh">{m.name}</td>
                            {FIELDS.map(([k]) => {
                              const c = sc.cells[k]
                              const p = r.preds[m.id][k]
                              return (
                                <td key={k} className={c ? (c.ok ? 'ok' : 'bad') : ''}>
                                  {p ?? '–'}{m.id === 'final' && r.corrected.includes(k) && <sup>보정</sup>}
                                </td>
                              )
                            })}
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  {r && (
                    <details>
                      <summary>인식한 글자 보기</summary>
                      <div className="ev-texts">
                        <div><p>PSM 6</p><pre>{r.text6}</pre></div>
                        <div><p>PSM 3</p><pre>{r.text3}</pre></div>
                      </div>
                    </details>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
