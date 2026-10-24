// 놀이 탭의 가상 강아지 (SVG로 직접 그린 오리지널 캐릭터)
// color: 털 색(사진에서 뽑은 색), ears: 'floppy' | 'pointy', mood: excited/happy/bored/sad/hungry

const clamp = (n) => Math.max(0, Math.min(255, Math.round(n)))
function parse(hex) {
  const h = (hex || '#C98A4B').replace('#', '')
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16))
}
const toHex = (rgb) => `#${rgb.map((v) => clamp(v).toString(16).padStart(2, '0')).join('')}`
/** amt < 0 이면 어둡게, > 0 이면 흰색 쪽으로 */
function shade(hex, amt) {
  const rgb = parse(hex)
  return toHex(rgb.map((v) => (amt < 0 ? v * (1 + amt) : v + (255 - v) * amt)))
}

// 귀가 서 있는 품종 (나머지는 늘어진 귀로 그려요)
const POINTY = ['진돗', '진도', '시바', '허스키', '코기', '포메', '치와와', '요크', '슈나우저', '프렌치', '프불', '사모예드', '미니핀', '핀셔', '파피용', '빠삐용', '보더']
export const earTypeFor = (breed = '') => (POINTY.some((k) => breed.replace(/\s/g, '').includes(k)) ? 'pointy' : 'floppy')

export default function DogCharacter({ color = '#C98A4B', ears = 'floppy', mood = 'happy', action = null }) {
  const fur = color
  const dark = shade(color, -0.28)
  const light = shade(color, 0.62)
  const happyEyes = mood === 'excited' || mood === 'happy' || action === 'pet' || action === 'treat'
  const openMouth = mood === 'excited' || action === 'ball' || action === 'walk'

  return (
    <svg viewBox="0 0 200 200" className={`dog mood-${mood}${action ? ` act-${action}` : ''}`} role="img"
      aria-label={`가상 강아지 캐릭터, 기분: ${mood}`}>
      {/* 그림자 */}
      <ellipse cx="100" cy="194" rx="58" ry="6" fill="rgba(31,49,40,.12)" />

      {/* 꼬리 */}
      <g className="dog-tail">
        <path d="M138 158 C160 150 168 128 160 116" stroke={fur} strokeWidth="11" strokeLinecap="round" fill="none" />
      </g>

      {/* 몸 */}
      <g className="dog-body">
        <ellipse cx="100" cy="152" rx="46" ry="38" fill={fur} />
        <ellipse cx="100" cy="162" rx="25" ry="24" fill={light} />
        <ellipse cx="80" cy="186" rx="13" ry="8" fill={light} />
        <ellipse cx="120" cy="186" rx="13" ry="8" fill={light} />
      </g>

      {/* 목걸이 (브랜드 골드) */}
      <path d="M68 120 Q100 136 132 120" stroke="var(--gold-500)" strokeWidth="7" strokeLinecap="round" fill="none" />
      <circle cx="100" cy="131" r="5.5" fill="var(--gold-600)" />

      <g className="dog-head">
        {/* 귀 (뒤) */}
        {ears === 'pointy' ? (
          <>
            <path d="M62 66 L60 26 L90 50 Z" fill={dark} strokeLinejoin="round" />
            <path d="M138 66 L140 26 L110 50 Z" fill={dark} strokeLinejoin="round" />
            <path d="M66 58 L65 36 L82 50 Z" fill={light} opacity=".6" />
            <path d="M134 58 L135 36 L118 50 Z" fill={light} opacity=".6" />
          </>
        ) : null}

        {/* 머리 */}
        <circle cx="100" cy="86" r="44" fill={fur} />

        {/* 늘어진 귀 (앞) */}
        {ears === 'floppy' && (
          <>
            <ellipse className="ear-l" cx="58" cy="88" rx="14" ry="29" fill={dark} transform="rotate(18 58 88)" />
            <ellipse className="ear-r" cx="142" cy="88" rx="14" ry="29" fill={dark} transform="rotate(-18 142 88)" />
          </>
        )}

        {/* 주둥이 */}
        <ellipse cx="100" cy="104" rx="23" ry="17" fill={light} />

        {/* 눈 */}
        {happyEyes ? (
          <>
            <path d="M78 83 q6 -8 12 0" stroke="#2B2B2B" strokeWidth="3.2" strokeLinecap="round" fill="none" />
            <path d="M110 83 q6 -8 12 0" stroke="#2B2B2B" strokeWidth="3.2" strokeLinecap="round" fill="none" />
          </>
        ) : (
          <>
            <circle cx="84" cy={mood === 'hungry' ? 80 : 82} r="5.2" fill="#2B2B2B" />
            <circle cx="116" cy={mood === 'hungry' ? 80 : 82} r="5.2" fill="#2B2B2B" />
            <circle cx="85.8" cy={mood === 'hungry' ? 78.2 : 80.2} r="1.6" fill="white" />
            <circle cx="117.8" cy={mood === 'hungry' ? 78.2 : 80.2} r="1.6" fill="white" />
            {mood === 'sad' && (
              <>
                <path d="M76 72 l12 3" stroke="#2B2B2B" strokeWidth="2.4" strokeLinecap="round" />
                <path d="M124 72 l-12 3" stroke="#2B2B2B" strokeWidth="2.4" strokeLinecap="round" />
              </>
            )}
          </>
        )}

        {/* 볼터치 */}
        {(happyEyes || mood === 'excited') && (
          <>
            <ellipse cx="72" cy="98" rx="7" ry="4" fill="#F2A7A0" opacity=".7" />
            <ellipse cx="128" cy="98" rx="7" ry="4" fill="#F2A7A0" opacity=".7" />
          </>
        )}

        {/* 코 */}
        <ellipse cx="100" cy="96" rx="7.5" ry="5.2" fill="#2B2B2B" />
        <ellipse cx="98" cy="94.5" rx="2.2" ry="1.2" fill="white" opacity=".6" />

        {/* 입 */}
        {openMouth ? (
          <>
            <path d="M89 105 q11 16 22 0 z" fill="#5A2B2B" />
            <path d="M95 111 q5 9 10 0" fill="#F28B8B" />
          </>
        ) : mood === 'hungry' ? (
          <ellipse cx="100" cy="110" rx="4" ry="3.5" fill="#5A2B2B" />
        ) : mood === 'sad' ? (
          <path d="M91 112 q9 -6 18 0" stroke="#2B2B2B" strokeWidth="2.6" strokeLinecap="round" fill="none" />
        ) : (
          <path d="M91 106 q4.5 6 9 0 q4.5 6 9 0" stroke="#2B2B2B" strokeWidth="2.6" strokeLinecap="round" fill="none" />
        )}
      </g>
    </svg>
  )
}
