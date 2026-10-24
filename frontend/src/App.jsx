import { useCallback, useEffect, useRef, useState } from 'react'
import { TabBar, Toast } from './components/common.jsx'
import { api } from './lib/api.js'
import { toDateStr } from './lib/format.js'
import HomeScreen from './screens/HomeScreen.jsx'
import { PetDetailScreen, PetFormScreen, PetListScreen } from './screens/PetScreens.jsx'
import RecordFormScreen from './screens/RecordFormScreen.jsx'
import ReportScreen from './screens/ReportScreen.jsx'
import CareCheckScreen from './screens/CareCheckScreen.jsx'
import CareScreen from './screens/CareScreen.jsx'
import { MedFormScreen, MedListScreen } from './screens/MedScreens.jsx'
import VisitFormScreen from './screens/VisitFormScreen.jsx'
import PrintReport from './screens/PrintReport.jsx'
import PlayScreen from './screens/PlayScreen.jsx'
import FoodLabelScreen from './screens/FoodLabelScreen.jsx'
import { AiChatScreen, AiHubScreen, BodyCheckScreen, HealthInfoScreen, VetFinderScreen } from './screens/AiScreens.jsx'

const HOME_PET_KEY = 'sevencare.homePetId'
const TOAST_LABEL = { meal: '식사', poop: '배변 활동', weight: '체중', med: '투약' }

function loadHomePetId() {
  try { return Number(localStorage.getItem(HOME_PET_KEY)) || null } catch { return null }
}

export default function App() {
  const [tab, setTab] = useState('home')
  // 탭 위에 덮이는 화면: { name: 'record-form', type, record? } | { name: 'pet-form', pet? } | { name: 'pet-detail', petId }
  const [overlay, setOverlay] = useState(null)

  const [pets, setPets] = useState([])
  const [homePetId, setHomePetId] = useState(loadHomePetId)
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [careScales, setCareScales] = useState(null)

  const [toast, setToast] = useState(null)
  const toastTimer = useRef()
  const showToast = useCallback((text, error = false) => {
    clearTimeout(toastTimer.current)
    setToast({ text, error })
    toastTimer.current = setTimeout(() => setToast(null), 1600)
  }, [])

  // 화면이 바뀌면 맨 위로 (긴 폼을 열 때 중간부터 보이지 않게)
  useEffect(() => { window.scrollTo(0, 0) }, [overlay, tab])

  const homePet = pets.find((p) => p.id === homePetId) ?? pets[0] ?? null

  // ---- 데이터 불러오기 ----
  const refreshPets = useCallback(async () => {
    const list = await api.listPets()
    setPets(list)
    return list
  }, [])

  const refreshRecords = useCallback(async (petId) => {
    if (!petId) { setRecords([]); return }
    setRecords(await api.listRecords(petId, { on: toDateStr() }))
  }, [])

  useEffect(() => {
    api.getCareScales().then(setCareScales).catch(() => {})
    refreshPets()
      .catch(() => showToast('서버에 연결할 수 없어요. 백엔드가 켜져 있는지 확인해 주세요', true))
      .finally(() => setLoading(false))
  }, [refreshPets, showToast])

  useEffect(() => {
    if (!homePet) { setRecords([]); return }
    try { localStorage.setItem(HOME_PET_KEY, String(homePet.id)) } catch { /* 저장 불가 환경 */ }
    setLoading(true)
    refreshRecords(homePet.id)
      .catch((e) => showToast(e.message, true))
      .finally(() => setLoading(false))
  }, [homePet?.id, refreshRecords, showToast]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (tab === 'home' && !overlay && homePet) refreshRecords(homePet.id).catch(() => {})
  }, [tab, overlay]) // eslint-disable-line react-hooks/exhaustive-deps

  // ---- 기록 저장/수정/삭제 ----
  async function submitRecord(body) {
    const { type, record } = overlay
    if (record) await api.updateRecord(record.id, body)
    else await api.createRecord(homePet.id, body)
    await Promise.all([refreshRecords(homePet.id), type === 'weight' ? refreshPets() : null])
    setOverlay(null)
    showToast(`${TOAST_LABEL[type]} 기록이 ${record ? '수정' : '저장'}됐어요`)
  }

  async function deleteRecord() {
    const { type, record } = overlay
    try {
      await api.deleteRecord(record.id)
      await Promise.all([refreshRecords(homePet.id), type === 'weight' ? refreshPets() : null])
      setOverlay(null)
      showToast(`${TOAST_LABEL[type]} 기록을 삭제했어요`)
    } catch (e) {
      showToast(e.message, true)
    }
  }

  // ---- 펫 등록/수정 ----
  async function submitPet(body, photo) {
    const editing = overlay.pet
    const saved = editing ? await api.updatePet(editing.id, body) : await api.createPet(body)
    // 사진은 펫 저장 뒤에 따로 올려요. 사진만 실패해도 펫 정보는 저장된 상태로 넘어가요 (중복 등록 방지)
    let photoFailed = false
    try {
      if (photo === 'remove') await api.deletePhoto(saved.id)
      else if (photo) await api.uploadPhoto(saved.id, photo.dataUrl, photo.color)
    } catch {
      photoFailed = true
    }
    await refreshPets()
    if (photoFailed) {
      showToast('정보는 저장됐지만 사진을 올리지 못했어요. 수정 화면에서 다시 시도해 주세요', true)
      setOverlay(editing ? { name: 'pet-detail', petId: saved.id } : null)
      return
    }
    if (editing) {
      setOverlay({ name: 'pet-detail', petId: saved.id })
      showToast('펫 정보가 수정됐어요')
    } else {
      if (!homePet) setHomePetId(saved.id)
      setOverlay(null)
      showToast(`${saved.name} 등록됐어요`)
    }
  }

  // ---- 케어 체크 저장 ----
  async function submitCareCheck(body) {
    const saved = await api.createCareCheck(homePet.id, body)
    setOverlay(overlay?.returnTo ?? null)
    const title = careScales[body.kind].title
    showToast(`${title} 저장 · ${saved.score}/${saved.max_score}점${saved.band ? ` · ${saved.band.label}` : ''}`)
  }

  // ---- 펫 삭제 (기록도 함께 삭제됨) ----
  async function deletePet(pet) {
    try {
      await api.deletePet(pet.id)
      if (homePetId === pet.id) setHomePetId(null) // 홈은 남은 첫 번째 펫으로
      await refreshPets()
      setOverlay(null)
      showToast(`${pet.name} 정보를 삭제했어요`)
    } catch (e) {
      showToast(e.message, true)
      throw e
    }
  }

  // ---- 화면 선택 ----
  let content
  if (overlay?.name === 'record-form') {
    content = (
      <RecordFormScreen
        key={overlay.record?.id ?? overlay.type}
        type={overlay.type}
        record={overlay.record}
        petId={homePet?.id}
        onSubmit={submitRecord}
        onDelete={deleteRecord}
        onBack={() => setOverlay(null)}
      />
    )
  } else if (overlay?.name === 'care-form') {
    content = (
      <CareCheckScreen
        scale={careScales[overlay.kind]}
        latest={overlay.latest}
        onSubmit={submitCareCheck}
        onBack={() => setOverlay(overlay.returnTo ?? null)}
      />
    )
  } else if (overlay?.name === 'med-list') {
    content = (
      <MedListScreen
        pet={homePet}
        onBack={() => setOverlay(null)}
        onAdd={() => setOverlay({ name: 'med-form' })}
        onEdit={(med) => setOverlay({ name: 'med-form', med })}
        onToast={showToast}
      />
    )
  } else if (overlay?.name === 'med-form') {
    content = (
      <MedFormScreen
        key={overlay.med?.id ?? 'new'}
        pet={homePet}
        med={overlay.med}
        onBack={() => setOverlay({ name: 'med-list' })}
        onSaved={() => setOverlay({ name: 'med-list' })}
        onToast={showToast}
      />
    )
  } else if (overlay?.name === 'ai-sub' && homePet) {
    const back = () => setOverlay(null)
    const sub = overlay.screen
    if (sub === 'chat') content = <AiChatScreen key={homePet.id} pet={homePet} onBack={back} />
    else if (sub === 'body') {
      content = (
        <BodyCheckScreen
          pet={homePet}
          onBack={back}
          onCheckBcs={(latest) => setOverlay({ name: 'care-form', kind: 'bcs', latest, returnTo: { name: 'ai-sub', screen: 'body' } })}
          onToast={showToast}
        />
      )
    } else if (sub === 'info') content = <HealthInfoScreen onBack={back} onToast={showToast} />
    else if (sub === 'food') content = <FoodLabelScreen key={homePet.id} pet={homePet} onBack={back} onToast={showToast} />
    else content = <VetFinderScreen pet={homePet} onBack={back} />
  } else if (overlay?.name === 'visit-form') {
    const pet = pets.find((p) => p.id === overlay.petId)
    const back = () => setOverlay({ name: 'pet-detail', petId: overlay.petId })
    content = pet && (
      <VisitFormScreen
        key={overlay.visit?.id ?? 'new'}
        pet={pet}
        visit={overlay.visit}
        onBack={back}
        onSaved={back}
        onToast={showToast}
      />
    )
  } else if (overlay?.name === 'pet-form') {
    content = (
      <PetFormScreen
        pet={overlay.pet}
        onSubmit={submitPet}
        onBack={() => setOverlay(overlay.pet ? { name: 'pet-detail', petId: overlay.pet.id } : null)}
      />
    )
  } else if (overlay?.name === 'pet-detail') {
    const pet = pets.find((p) => p.id === overlay.petId)
    content = pet && (
      <PetDetailScreen pet={pet} onBack={() => setOverlay(null)} onEdit={() => setOverlay({ name: 'pet-form', pet })}
        onDelete={() => deletePet(pet)}
        onAddVisit={() => setOverlay({ name: 'visit-form', petId: pet.id })}
        onEditVisit={(visit) => setOverlay({ name: 'visit-form', petId: pet.id, visit })}
        onToast={showToast}
      />
    )
  } else if (tab === 'home') {
    content = (
      <HomeScreen
        pets={pets}
        pet={homePet}
        records={records}
        loading={loading}
        onSelectPet={setHomePetId}
        onOpenForm={(type, record) => setOverlay({ name: 'record-form', type, record })}
        onAddPet={() => setOverlay({ name: 'pet-form' })}
        onGoTab={setTab}
      />
    )
  } else if (tab === 'report') {
    content = (
      <ReportScreen
        pet={homePet}
        onToast={showToast}
        onDataChanged={() => Promise.all([refreshPets(), homePet && refreshRecords(homePet.id)])}
        onExport={() => setOverlay({ name: 'print' })}
      />
    )
  }
  else if (tab === 'care') {
    content = (
      <CareScreen
        pet={homePet}
        scales={careScales}
        onOpenCheck={(kind, latest) => setOverlay({ name: 'care-form', kind, latest })}
        onManageMeds={() => setOverlay({ name: 'med-list' })}
        onToast={showToast}
      />
    )
  }
  else if (tab === 'play') content = <PlayScreen key={homePet?.id} pet={homePet} onToast={showToast} />
  else if (tab === 'ai') content = <AiHubScreen pet={homePet} onOpen={(screen) => setOverlay({ name: 'ai-sub', screen })} />
  else if (tab === 'pets') {
    content = (
      <PetListScreen
        pets={pets}
        onView={(petId) => setOverlay({ name: 'pet-detail', petId })}
        onAdd={() => setOverlay({ name: 'pet-form' })}
      />
    )
  }

  // 입력 폼에서는 탭바를 숨겨요 (레퍼런스와 동일)
  const showTabBar = !overlay

  // 병원 지참용 리포트는 폰 프레임 밖에서 A4 문서로 보여줘요
  if (overlay?.name === 'print' && homePet) {
    return (
      <>
        <PrintReport pet={homePet} onClose={() => setOverlay(null)} onToast={showToast} />
        <div className="print-toast"><Toast toast={toast} /></div>
      </>
    )
  }

  return (
    <div>
      <div className={'phone' + (showTabBar ? ' has-tabs' : ' no-tabs')}>
        {content}
        <Toast toast={toast} />
        {showTabBar && <TabBar active={tab} onChange={(t) => { setTab(t); setOverlay(null) }} />}
      </div>
      <p className="caption">세븐케어 — 초고령견 케어일지 & 데이터 리포트</p>
    </div>
  )
}
