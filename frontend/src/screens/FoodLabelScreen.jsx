import { useEffect, useRef, useState } from 'react'
import { IconTile, TopBar } from '../components/common.jsx'
import { AlertIcon, CameraIcon, CheckIcon, EditIcon, InfoIcon, MealIcon } from '../components/Icons.jsx'
import { api } from '../lib/api.js'
import { mergeParsed, readLabel } from '../lib/ocr.js'

const FIELDS = [
  ['protein', '조단백질', '이상'], ['fat', '조지방', '이상'], ['fiber', '조섬유', '이하'], ['ash', '조회분', '이하'],
  ['calcium', '칼슘', ''], ['phosphorus', '인', ''], ['moisture', '수분', '이하'], ['sodium', '나트륨', '선택'],
]
const STATUS = {
  ok: { tone: 'green', Icon: CheckIcon, label: '적합' },
  warn: { tone: 'poop', Icon: InfoIcon, label: '확인' },
  info: { tone: 'weight', Icon: InfoIcon, label: '참고' },
  bad: { tone: 'danger', Icon: AlertIcon, label: '주의' },
}
const FLAG_LABELS = { kidney: '신장 관리', heart: '심장 관리', joint: '관절', obese: '체중 관리', cognitive: '인지기능' }

const toForm = (n = {}) => Object.fromEntries(FIELDS.map(([k]) => [k, n[k] != null ? String(n[k]) : '']))

/** AI건강 > 사료 성분 분석: 성분표 사진 → 글자 인식 → 수치 확인·수정 → 우리 개 기준 평가 */
export default function FoodLabelScreen({ pet, onBack, onToast }) {
  const [stage, setStage] = useState('pick') // pick · reading · edit · result
  const [photo, setPhoto] = useState(null)
  const [progress, setProgress] = useState({ p: 0, text: '' })
  const [ocrText, setOcrText] = useState('')
  const [form, setForm] = useState(toForm())
  const [kcal, setKcal] = useState('')
  const [keywords, setKeywords] = useState([])
  const [readCount, setReadCount] = useState(null)
  const [suspects, setSuspects] = useState([])
  const [fixedKeys, setFixedKeys] = useState([])
  const [tableMode, setTableMode] = useState(false)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const fileRef = useRef()
  const rootRef = useRef()

  // 단계가 바뀌면 맨 위부터 보이게
  useEffect(() => {
    if (rootRef.current) rootRef.current.scrollTop = 0
    window.scrollTo?.(0, 0)
  }, [stage])

  async function onFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setPhoto(URL.createObjectURL(file))
    setStage('reading')
    try {
      // 1차: 표에 강한 방식(PSM 6). 7개 성분을 다 못 찾으면 2차: 자동 배치 방식(PSM 3)으로 한 번 더 읽고,
      // 많이 찾은 쪽을 기본으로 빈 칸만 다른 쪽 값으로 채워요 (17장 측정에서 정확도 72% → 80%)
      let text = await readLabel(file, (p, t) => setProgress({ p, text: t }), '6')
      let parsed = await api.parseFoodLabel(text)
      if (Object.keys(parsed.nutrients).length < 7) {
        const text2 = await readLabel(file, (p, t) => setProgress({ p, text: t }), '3')
        const parsed2 = await api.parseFoodLabel(text2)
        parsed = mergeParsed(parsed, parsed2)
        text = `${text}\n----- (자동 배치로 다시 읽은 글자) -----\n${text2}`
      }
      setOcrText(text)
      setForm(toForm(parsed.nutrients))
      setKcal(parsed.kcal_per_kg ? String(parsed.kcal_per_kg) : '')
      setKeywords(parsed.keywords)
      setReadCount(Object.keys(parsed.nutrients).length)
      setSuspects(parsed.suspect ?? [])
      setFixedKeys(parsed.found.filter((f) => f.corrected).map((f) => f.key))
      setTableMode(parsed.found.some((f) => f.table))
      setStage('edit')
    } catch (err) {
      onToast(err.message, true)
      setStage('pick')
    }
  }

  function manual() {
    setPhoto(null); setOcrText(''); setReadCount(null); setSuspects([]); setFixedKeys([]); setTableMode(false); setForm(toForm()); setKcal(''); setKeywords([])
    setStage('edit')
  }

  async function analyze() {
    const nutrients = {}
    for (const [k] of FIELDS) {
      const v = form[k].trim().replace(',', '.')
      if (v === '') continue
      const num = Number(v)
      if (!Number.isFinite(num) || num < 0 || num > 100) { onToast('성분 값은 0~100 사이 숫자로 적어 주세요', true); return }
      nutrients[k] = num
    }
    if (!nutrients.protein && !nutrients.fat) { onToast('조단백질이나 조지방 중 하나는 적어 주세요', true); return }
    setBusy(true)
    try {
      setResult(await api.checkFood(pet.id, { nutrients, keywords, kcal_per_kg: kcal ? Number(kcal) : null }))
      setStage('result')
    } catch (err) {
      onToast(err.message, true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="screen" ref={rootRef}>
      <TopBar title="사료 성분 분석" onBack={stage === 'result' ? () => setStage('edit') : onBack} />
      <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden onChange={onFile} />

      {stage === 'pick' && (
        <div className="form-body">
          <div className="food-hero">
            <IconTile tone="meal" Icon={MealIcon} size={48} />
            <p className="t">사료 뒷면 성분표를 찍어 주세요</p>
            <p className="d">
              조단백질 · 지방 · 인 같은 수치를 읽어서, {pet.name}의 나이와 건강 상태에 맞는 사료인지 알려드려요.
            </p>
            <ul className="tips">
              <li>'등록성분' 또는 'Guaranteed Analysis' 부분이 잘 보이게</li>
              <li>밝은 곳에서, 정면으로, 흔들리지 않게</li>
              <li>반짝이는 포장은 빛 반사를 피해서</li>
            </ul>
          </div>
          <button type="button" className="primary-btn" onClick={() => fileRef.current.click()}>
            <CameraIcon />
            성분표 사진 찍기 · 고르기
          </button>
          <button type="button" className="chip" style={{ padding: 14 }} onClick={manual}>
            사진 없이 직접 입력하기
          </button>
          <p className="scale-source">
            글자 인식은 무료 오픈소스 Tesseract로 기기 안에서 처리해요. 처음 한 번은 한국어 데이터를 받느라 조금 걸려요.
          </p>
        </div>
      )}

      {stage === 'reading' && (
        <div className="form-body">
          {photo && <img className="food-photo" src={photo} alt="성분표 사진" />}
          <div className="card">
            <p className="k-label">{progress.text || '준비 중'}…</p>
            <div className="meter-bar" style={{ marginTop: 10 }}>
              <div className="meter-fill full" style={{ width: `${Math.round(progress.p * 100)}%` }} />
            </div>
          </div>
        </div>
      )}

      {stage === 'edit' && (
        <div className="form-body">
          {photo && <img className="food-photo small" src={photo} alt="성분표 사진" />}
          {readCount != null && (
            <div className={'calm-banner ' + (readCount >= 5 ? 'ok' : '')} style={{ margin: 0 }}>
              {readCount >= 5 ? <CheckIcon /> : <InfoIcon />}
              <p>
                성분 {readCount}개를 읽었어요{tableMode ? ' (표 모양 성분표를 열 순서대로 맞췄어요)' : ''}. {readCount >= 5 ? '포장과 숫자가 맞는지 한 번만 확인해 주세요.' : '못 읽은 칸은 포장을 보고 직접 채워 주세요.'}
                {fixedKeys.length > 0 && <><br /><b>노란 칸</b>은 자동으로 보정하거나 추정한 값이에요. 포장과 꼭 비교해 주세요.</>}
              </p>
            </div>
          )}
          {suspects.length > 0 && (
            <div className="alert-card" style={{ padding: 14 }}>
              <IconTile tone="danger" Icon={AlertIcon} size={32} />
              <div>
                <p className="t" style={{ fontSize: 14 }}>이상한 값은 비워 뒀어요</p>
                <p className="m">
                  {suspects.map((x) => `${x.label} ${x.value}%`).join(', ')} — 사료에 나올 수 없는 수치라 잘못 읽은 것 같아요. 포장을 보고 직접 적어 주세요.
                </p>
              </div>
            </div>
          )}
          <div className="nutri-grid">
            {FIELDS.map(([k, label, hint]) => (
              <label key={k} className={'nutri-field' + (form[k] ? ' filled' : '') + (suspects.some((x) => x.key === k) && !form[k] ? ' suspect' : '') + (fixedKeys.includes(k) ? ' fixed' : '')}>
                <span>{label}{hint && <small>{hint}</small>}</span>
                <div className="unit-row">
                  <input type="text" inputMode="decimal" value={form[k]} placeholder="–"
                    onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
                  <em>%</em>
                </div>
              </label>
            ))}
          </div>
          <label className="nutri-field wide">
            <span>대사에너지<small>선택 · 없으면 성분으로 추정</small></span>
            <div className="unit-row">
              <input type="text" inputMode="numeric" value={kcal} placeholder="예: 3600"
                onChange={(e) => setKcal(e.target.value.replace(/[^0-9]/g, ''))} />
              <em>kcal/kg</em>
            </div>
          </label>
          {ocrText && (
            <details className="ocr-raw">
              <summary>인식한 글자 보기</summary>
              <pre>{ocrText}</pre>
              <button type="button" className="link-btn" onClick={() => navigator.clipboard?.writeText(ocrText).then(() => onToast('인식한 글자를 복사했어요'))}>
                글자 복사하기
              </button>
            </details>
          )}
          <button type="button" className="primary-btn" onClick={analyze} disabled={busy}>
            {busy ? '분석 중…' : `${pet.name}에게 맞는지 분석하기`}
          </button>
          {photo && (
            <button type="button" className="chip" style={{ padding: 12 }} onClick={() => fileRef.current.click()}>
              <EditIcon style={{ width: 15, height: 15, verticalAlign: -2, marginRight: 4 }} stroke="currentColor" />
              다른 사진으로 다시 읽기
            </button>
          )}
        </div>
      )}

      {stage === 'result' && result && <FoodResult result={result} pet={pet} onAgain={() => { setStage('pick'); setResult(null) }} />}
    </div>
  )
}

function FoodResult({ result, pet, onAgain }) {
  const v = result.verdict
  const flags = Object.entries(result.flags).filter(([, on]) => on).map(([k]) => FLAG_LABELS[k])
  const dm = result.dry_matter
  const BASE = ['protein_min', 'fat_min', 'calcium', 'phosphorus', 'ca_p_ratio']
  const ORDER = { bad: 0, warn: 1, info: 2, ok: 3 }
  const base = result.checks.filter((c) => BASE.includes(c.code))
  const personal = result.checks.filter((c) => !BASE.includes(c.code)).sort((a, b) => ORDER[a.status] - ORDER[b.status])
  const pct = (v) => (v != null ? `${Math.round(v * 10) / 10}%` : '–')
  return (
    <div className="form-body">
      <div className={`verdict ${v.level}`}>
        <p className="k">{pet.name} 기준 분석 결과</p>
        <p className="t">{v.message}</p>
        {flags.length > 0 && (
          <div className="mini-chips">
            {flags.map((f) => <span key={f}>{f}</span>)}
          </div>
        )}
      </div>

      <div className="dm-row">
        {[['protein', '단백질'], ['fat', '지방'], ['phosphorus', '인']].map(([k, l]) => (
          <div key={k}><b>{pct(dm[k])}</b><span>{l} (건물 기준)</span></div>
        ))}
        <div><b>{result.kcal_per_kg.toLocaleString()}</b><span>kcal/kg{result.kcal_estimated ? ' (추정)' : ''}</span></div>
      </div>

      {personal.length > 0 && <p className="sub-head">{pet.name} 맞춤 체크</p>}
      <div className="check-list">
        {personal.map((c) => {
          const s = STATUS[c.status]
          return (
            <div key={c.code} className={`check-item ${c.status}`}>
              <IconTile tone={s.tone} Icon={s.Icon} size={34} />
              <div>
                <p className="t">{c.title}<span className={`badge ${c.status}`}>{s.label}</span></p>
                <p className="m">{c.message}</p>
                <a href={c.source_url} target="_blank" rel="noreferrer">근거 · {c.source}</a>
              </div>
            </div>
          )
        })}
      </div>

      {base.length > 0 && (
        <>
          <p className="sub-head">기본 영양 기준 · {base.filter((c) => c.status === 'ok').length}/{base.length} 적합</p>
          <div className="base-card">
            {base.map((c) => (
              <div key={c.code} className="base-row">
                <span className={`dot ${c.status}`} />
                <b>{c.title}</b>
                <span className="v">{c.message}</span>
              </div>
            ))}
            <a href={base[0].source_url} target="_blank" rel="noreferrer">근거 · {base[0].source}</a>
          </div>
        </>
      )}

      {result.notes.map((n) => <p key={n} className="scale-source">· {n}</p>)}
      <p className="scale-source">
        건물 기준 = 수분을 뺀 나머지 속 비율이에요. 사료마다 수분이 달라서, 공정하게 비교하려면 이렇게 바꿔서 봐야 해요.
      </p>
      <p className="disclaimer">{result.disclaimer}</p>
      <button type="button" className="primary-btn" onClick={onAgain}>다른 사료 분석하기</button>
    </div>
  )
}
