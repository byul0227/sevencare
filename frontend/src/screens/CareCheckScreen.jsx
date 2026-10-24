import { useState } from 'react'
import { ChipGroup, TopBar } from '../components/common.jsx'

const shortDate = (iso) => new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric' }).format(new Date(iso))

/** 거동 / 인지기능 / 삶의 질 체크 폼 — 문항은 서버의 척도 정의(scale)로 그려요 */
export default function CareCheckScreen({ scale, latest, onSubmit, onBack }) {
  const [answers, setAnswers] = useState(() => {
    if (scale.input === 'slider') {
      // 지난 결과가 있으면 그 값에서 시작. 없으면 비워두고 직접 움직이게 해요
      // (기본값 5점×7 = 35점이 바로 경계값이라, 그냥 저장하면 오해할 수 있어서)
      return latest ? { ...latest.answers } : {}
    }
    if (scale.kind === 'mobility') {
      // 매일 하는 체크라 '양호'(0)로 시작해서 달라진 것만 고르게
      return Object.fromEntries(scale.questions.map((q) => [q.id, q.options[0].value]))
    }
    return {} // 인지기능은 하나씩 직접 고르도록 비워둠
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const unanswered = scale.questions.filter((q) => answers[q.id] == null).length
  const set = (id) => (v) => setAnswers((a) => ({ ...a, [id]: v }))

  async function handleSave() {
    if (unanswered) return setError(`아직 답하지 않은 문항이 ${unanswered}개 있어요.`)
    setError('')
    setSaving(true)
    try {
      await onSubmit({ kind: scale.kind, answers })
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <div className="screen">
      <TopBar title={scale.title} onBack={onBack} />
      <div className="form-body">
        <p className="field-label" style={{ margin: '-6px 0 0' }}>{scale.instructions}</p>
        {latest && (
          <div className="last-result">
            최근 결과 · {shortDate(latest.checked_at)} ·{' '}
            <strong>{latest.score}/{latest.max_score}점</strong>
            {latest.band && ` · ${latest.band.label}`}
          </div>
        )}

        {scale.questions.map((q, i) =>
          scale.input === 'slider' ? (
            <div key={q.id} className="slider-row">
              <div className="top">
                <span>{q.text}</span>
                <span className="val">{answers[q.id] ?? '선택 전'}</span>
              </div>
              {q.hint && <p className="q-hint">{q.hint}</p>}
              <input
                type="range" min={scale.min} max={scale.max}
                className={answers[q.id] == null ? 'untouched' : undefined}
                value={answers[q.id] ?? Math.round((scale.min + scale.max) / 2)}
                onChange={(e) => set(q.id)(Number(e.target.value))}
                onPointerUp={(e) => set(q.id)(Number(e.target.value))}
                aria-label={q.text}
              />
            </div>
          ) : (
            <div key={q.id}>
              <p className="field-label">
                {scale.kind === 'cognitive' && <span className="q-num">{i + 1}</span>}
                {q.text}
              </p>
              <ChipGroup options={q.options} value={answers[q.id]} onChange={set(q.id)}
                vertical={q.options.some((o) => o.label.length > 14)} compact={q.options.length > 3} />
            </div>
          ),
        )}

        {error && <p className="error-text">{error}</p>}
        <button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>
          {saving ? '저장 중…' : '저장'}
        </button>
        <p className="scale-source">
          출처: <a href={scale.source_url} target="_blank" rel="noreferrer">{scale.source}</a>
        </p>
      </div>
    </div>
  )
}
