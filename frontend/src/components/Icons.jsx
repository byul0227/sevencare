// design-reference.html 에서 쓰던 SVG 아이콘 (lucide 스타일, stroke 기반)
const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
}

const make = (children) => (props) => <svg {...base} {...props}>{children}</svg>

export const LeafIcon = make(<>
  <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
  <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6" />
</>)
export const ChevronDownIcon = make(<polyline points="6 9 12 15 18 9" />)
export const BackIcon = make(<polyline points="15 18 9 12 15 6" />)
export const CheckIcon = make(<polyline points="20 6 9 17 4 12" />)
export const PlusIcon = make(<><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></>)
export const AlertIcon = make(<>
  <path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
  <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
</>)
export const FileIcon = make(<>
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
</>)

// 기록 종류
export const MealIcon = make(<>
  <path d="M18 8h1a4 4 0 0 1 0 8h-1" /><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4Z" />
  <line x1="6" y1="2" x2="6" y2="4" /><line x1="10" y1="2" x2="10" y2="4" /><line x1="14" y1="2" x2="14" y2="4" />
</>)
export const PoopIcon = make(<path d="M12 2.69s-5 5.6-5 9.31a5 5 0 0 0 10 0c0-3.71-5-9.31-5-9.31Z" />)
export const WeightIcon = make(<><circle cx="12" cy="12" r="10" /><path d="M12 8v4l3 3" /></>)
export const MedIcon = make(<>
  <path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z" /><path d="m8.5 8.5 7 7" />
</>)

// 탭바
export const HomeIcon = make(<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />)
export const ReportIcon = make(<><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-3 3" /></>)
export const CareIcon = make(<><path d="M12 21c0-4-4-6-4-10a4 4 0 0 1 8 0c0 4-4 6-4 10Z" /><path d="M12 3v3" /></>)
export const AiIcon = make(<>
  <rect x="3" y="11" width="18" height="10" rx="2" /><circle cx="12" cy="5" r="2" />
  <line x1="12" y1="7" x2="12" y2="11" /><line x1="8" y1="16" x2="8" y2="16" /><line x1="16" y1="16" x2="16" y2="16" />
</>)
export const PawIcon = make(<>
  <circle cx="11" cy="4" r="2" /><circle cx="18" cy="8" r="2" /><circle cx="20" cy="16" r="2" />
  <path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10Z" />
</>)
export const BoneIcon = make(<path d="M17 10c.7-.7 1.69 0 2.5 0a2.5 2.5 0 1 0 0-5 .5.5 0 0 1-.5-.5 2.5 2.5 0 1 0-5 0c0 .81.7 1.8 0 2.5l-7 7c-.7.7-1.69 0-2.5 0a2.5 2.5 0 0 0 0 5c.28 0 .5.22.5.5a2.5 2.5 0 1 0 5 0c0-.81-.7-1.8 0-2.5Z" />)
export const BallIcon = make(<><circle cx="12" cy="12" r="9" /><path d="M5.6 5.6c3.5 3.5 3.5 9.3 0 12.8" /><path d="M18.4 5.6c-3.5 3.5-3.5 9.3 0 12.8" /></>)
export const HeartIcon = make(<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />)
export const CameraIcon = make(<><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" /><circle cx="12" cy="13" r="3" /></>)

// v2 리디자인에서 추가
export const ChevronRightIcon = make(<polyline points="9 18 15 12 9 6" />)
export const BrainIcon = make(<>
  <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
  <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
  <path d="M12 5v13" />
</>)
export const ChatIcon = make(<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />)
export const ScaleIcon = make(<>
  <path d="M5 21h14a2 2 0 0 0 2-2V8.5a5.5 5.5 0 0 0-5.5-5.5h-7A5.5 5.5 0 0 0 3 8.5V19a2 2 0 0 0 2 2Z" />
  <path d="m12 8.5 2-2.5" /><path d="M8.5 10a4 4 0 0 1 7 0" />
</>)
export const InfoIcon = make(<><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></>)
export const MapPinIcon = make(<><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></>)
export const SparkIcon = make(<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />)
export const CalendarIcon = make(<><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4" /><path d="M8 2v4" /><path d="M3 10h18" /></>)
export const StethoIcon = make(<>
  <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6 6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3" />
  <path d="M8 15v1a6 6 0 0 0 6 6 6 6 0 0 0 6-6v-4" /><circle cx="20" cy="10" r="2" />
</>)
export const WalkIcon = make(<>
  <circle cx="13" cy="4" r="2" /><path d="m9 20 3-6 3 2v5" /><path d="m7 12 3-4 4 1 3 3" /><path d="M10 8 8 14" />
</>)
export const EditIcon = make(<><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" /></>)
