import { useState } from 'react'

const W = 320
const H = 120
const PAD_X = 8
const PAD_TOP = 22 // 마지막 값 라벨 자리
const PAD_BOTTOM = 8

/**
 * 주별 체중 추이 라인 차트 (단일 시리즈라 범례 없음).
 * points: [{ label, weight_kg | null }]
 */
export default function WeightChart({ points }) {
  const [hover, setHover] = useState(null)
  const values = points.map((p) => p.weight_kg).filter((v) => v != null)

  if (values.length === 0) {
    return <div className="chart-empty">체중을 기록하면 주별 추이를 보여드려요</div>
  }

  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(max - min, max * 0.02, 0.2) // 변화가 거의 없을 때 선이 과하게 요동치지 않게
  const mid = (max + min) / 2
  const lo = mid - span / 2
  const step = (W - PAD_X * 2) / Math.max(points.length - 1, 1)

  const xy = points.map((p, i) => ({
    ...p,
    x: PAD_X + step * i,
    y: p.weight_kg == null ? null : PAD_TOP + (1 - (p.weight_kg - lo) / span) * (H - PAD_TOP - PAD_BOTTOM),
  }))
  const drawn = xy.filter((p) => p.y != null)
  const last = drawn[drawn.length - 1]
  const hovered = hover != null ? xy[hover] : null

  return (
    <div className="weight-chart" onMouseLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: H, overflow: 'visible' }} role="img"
        aria-label={`주별 평균 체중: ${xy.map((p) => `${p.label} ${p.weight_kg ?? '기록 없음'}`).join(', ')}`}>
        {hovered && <line x1={hovered.x} x2={hovered.x} y1={4} y2={H} stroke="var(--sage-line)" strokeWidth="1" />}
        <defs>
          <linearGradient id="wc-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--weight)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--weight)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={0} x2={W} y1={PAD_TOP + f * (H - PAD_TOP - PAD_BOTTOM)} y2={PAD_TOP + f * (H - PAD_TOP - PAD_BOTTOM)}
            stroke="var(--sage-line)" strokeDasharray="3 4" />
        ))}
        {drawn.length > 1 && (
          <path d={`M${drawn[0].x},${H} ` + drawn.map((p) => `L${p.x},${p.y}`).join(' ') + ` L${last.x},${H} Z`} fill="url(#wc-fill)" />
        )}
        {drawn.length > 1 && (
          <polyline
            points={drawn.map((p) => `${p.x},${p.y}`).join(' ')}
            fill="none" stroke="var(--weight)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          />
        )}
        {drawn.map((p) => {
          const isLast = p === last
          return (
            <circle key={p.label} cx={p.x} cy={p.y} r={isLast ? 4.5 : 4}
              fill={isLast ? 'var(--weight)' : 'var(--bg-card)'}
              stroke={isLast ? 'var(--bg-card)' : 'var(--weight)'} strokeWidth={isLast ? 3 : 2} />
          )
        })}
        {!hovered && (
          <text x={last.x} y={last.y - 11} textAnchor={last.x > W - 40 ? 'end' : 'middle'}
            fontSize="12" fontWeight="600" fill="var(--pine-900)">
            {last.weight_kg}kg
          </text>
        )}
        {/* 호버 영역: 점보다 넓게 */}
        {xy.map((p, i) => (
          <rect key={p.label} x={p.x - step / 2} y={0} width={step} height={H} fill="transparent"
            onMouseEnter={() => setHover(i)} onClick={() => setHover(i)} />
        ))}
      </svg>
      {hovered && (
        <div className="chart-tip" style={{ left: `${(hovered.x / W) * 100}%` }}>
          <span className="k">{hovered.label}</span>
          <span className="v">{hovered.weight_kg != null ? `${hovered.weight_kg}kg` : '기록 없음'}</span>
        </div>
      )}
      <div className="chart-axis">{points.map((p) => <span key={p.label}>{p.label}</span>)}</div>
    </div>
  )
}
