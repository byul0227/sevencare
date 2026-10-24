# 세븐케어 (SevenCare)

초고령견 케어일지 & 데이터 리포트 웹서비스. 데모용으로 **로그인 없이 단일 사용자**로 동작해요.

- 프론트: React 19 + Vite (`frontend/`)
- 백엔드: FastAPI + SQLAlchemy 2 (`backend/`)
- DB: SQLite (`backend/sevencare.db`, 처음 실행하면 자동 생성)
- 디자인 v2: 밝은 뉴트럴 배경 + 애프리콧 오렌지 브랜드, 그림자 카드, 기록 종류별 포인트 컬러, Pretendard 폰트 (토큰은 `frontend/src/styles/tokens.css`). 초기 레퍼런스는 `design-reference.html`

## 폴더 구조

```
sevencare-app/
├─ design-reference.html        # 최종 디자인 레퍼런스
├─ backend/
│  ├─ requirements.txt
│  ├─ pytest.ini
│  ├─ app/
│  │  ├─ main.py                # FastAPI 앱, CORS, 라우터 등록
│  │  ├─ database.py            # SQLite 연결 / 세션
│  │  ├─ models.py              # pets, records, care_checks, medications, vet_visits 테이블
│  │  ├─ care_scales.py         # 케어 체크 척도 정의 (문항·점수·해석·출처)
│  │  ├─ med_schedule.py        # 투약 슬롯 ↔ 복용 기록 짝짓기, 놓침·중복 판단
│  │  ├─ breeds.py              # 품종별 표준 체중 (AKC)
│  │  ├─ health_info.py         # 증상별 '언제 병원에 가야 하나' (출처 포함)
│  │  ├─ play_logic.py          # 놀이 탭 규칙 (수치 감소, 간식 획득, 쿨다운)
│  │  ├─ schemas.py             # 요청·응답 스키마 (검증 규칙)
│  │  ├─ seed.py                # 데모 데이터 (초코, 보리)
│  │  └─ routers/
│  │     ├─ pets.py             # 펫 API
│  │     ├─ records.py          # 기록 CRUD API
│  │     ├─ report.py           # 리포트 + 데모 데이터 API
│  │     ├─ care.py             # 케어 체크 API
│  │     ├─ meds.py             # 약 관리 + 오늘의 투약 체크리스트 API
│  │     ├─ visits.py           # 병원 방문 기록 API
│  │     ├─ ai.py               # 비만도 체크, 증상 정보, AI 상담 API
│  │     ├─ summary.py          # 병원 지참용 리포트 데이터
│  │     ├─ photos.py           # 프로필 사진
│  │     └─ play.py             # 놀이 탭 (가상 강아지)
│  └─ tests/test_api.py
└─ frontend/
   ├─ index.html
   ├─ vite.config.js            # /api → localhost:8000 프록시
   └─ src/
      ├─ main.jsx, App.jsx      # 탭·화면 전환, 데이터 로딩
      ├─ lib/api.js             # API 호출
      ├─ lib/format.js          # 날짜·기록 표시 헬퍼
      ├─ styles/tokens.css      # 색상·폰트 토큰
      ├─ styles/app.css         # 레퍼런스에서 옮긴 스타일
      ├─ components/            # 아이콘, 탭바, 칩, 토스트 등
      └─ screens/
         ├─ HomeScreen.jsx      # 홈 (API 연결 완료)
         ├─ RecordFormScreen.jsx# 식사/배변/체중/투약 입력·수정·삭제
         ├─ PetScreens.jsx      # 마이펫 목록·상세(복용 약, 방문 타임라인)·등록/수정
         ├─ VisitFormScreen.jsx # 병원 방문 기록 추가·수정·삭제
         ├─ ReportScreen.jsx    # 리포트 (API 연결 완료)
         ├─ CareScreen.jsx      # 케어 탭 (API 연결 완료)
         ├─ CareCheckScreen.jsx # 거동·인지기능·삶의 질 체크 폼
         ├─ MedScreens.jsx      # 약 관리 목록·등록/수정, 케어 탭 투약 체크리스트
         ├─ AiScreens.jsx       # AI건강: 허브, 비만도 체크, 증상 정보, 주변 병원, AI 상담
         ├─ PrintReport.jsx     # 병원 지참용 리포트 (A4 인쇄 → PDF 저장)
         ├─ PlayScreen.jsx      # 놀이 탭 (캐릭터는 components/DogCharacter.jsx)
         └─ FoodLabelScreen.jsx # AI건강 > 사료 성분 분석 (글자 인식은 lib/ocr.js)
```

## 실행 방법 (Windows 기준)

터미널 두 개를 열어요.

**1) 백엔드**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed              # (선택) 초코·보리 샘플 데이터
uvicorn app.main:app --reload   # http://localhost:8000/docs 에서 API 확인
```

**2) 프론트엔드**

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

**테스트**: `backend` 폴더에서 `pytest -q`

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/pets` | 펫 목록 |
| POST | `/api/pets` | 펫 등록 |
| GET / PATCH / DELETE | `/api/pets/{id}` | 펫 조회 / 부분 수정 / 삭제(기록도 함께 삭제) |
| GET | `/api/pets/{id}/records?on=YYYY-MM-DD&type=meal` | 기록 목록 (최신순). `start`, `end`로 기간 조회 가능 |
| POST | `/api/pets/{id}/records` | 기록 생성 |
| GET / PATCH / DELETE | `/api/records/{id}` | 기록 조회 / 부분 수정 / 삭제 |
| GET | `/api/pets/{id}/report?weeks=4` | 건강 리포트: 주별 체중 추이, 평균 식사량, 배변 정상 비율, 경고 |
| POST / DELETE | `/api/pets/{id}/demo-history` | (데모용) 지난 5주 기록 자동 생성 / 생성한 데모 기록만 삭제 |
| GET | `/api/care-scales` | 케어 체크 척도 정의 (문항, 보기, 해석 기준, 출처) |
| GET | `/api/pets/{id}/care-summary` | 거동·인지기능·삶의 질 최신 결과 |
| GET / POST | `/api/pets/{id}/care-checks` | 체크 결과 목록 (`?kind=`) / 저장 (서버가 점수 계산) |
| DELETE | `/api/care-checks/{id}` | 체크 결과 삭제 |
| GET / POST | `/api/pets/{id}/medications` | 약 목록 / 등록 (이름, 용량, 매일 복용 시간, 지시사항, 기간) |
| PATCH / DELETE | `/api/medications/{id}` | 약 수정 (중지는 `active: false`) / 삭제 (지난 복용 기록은 유지) |
| GET | `/api/pets/{id}/med-schedule?on=YYYY-MM-DD` | 그날의 복용 체크리스트 + 놓침·중복 알림 |
| GET / POST | `/api/pets/{id}/vet-visits` | 병원 방문 기록 (최신순) + 다음 방문 예정 / 추가 (병원을 비우면 담당 병원) |
| GET / PATCH / DELETE | `/api/vet-visits/{id}` | 방문 기록 조회 / 수정 / 삭제 |
| GET | `/api/pets/{id}/body-check` | 비만도 체크: 최근 체중, 품종 표준 체중, 최근 BCS |
| GET | `/api/health-info` | 증상별 병원 방문 기준 (출처 포함) |
| GET | `/api/ai/status` | AI 상담 사용 가능 여부 |
| POST | `/api/pets/{id}/ai-chat` | AI 상담 (`{messages: [{role, content}]}`), 키가 없으면 503 |
| GET | `/api/pets/{id}/vet-summary?weeks=4` | 병원 지참용 리포트 데이터 (기본 정보, 알림, 체중·식사·배변, 약 복용률, 케어 체크, 특이 기록, 방문 기록) |
| GET / PUT / DELETE | `/api/pets/{id}/photo` | 프로필 사진 보기 / 저장 (`{data_url, color}`) / 삭제 |
| GET | `/api/pets/{id}/play` | 놀이 탭 상태 (행복도, 포만감, 기분, 남은 간식, 쿨다운) |
| POST | `/api/pets/{id}/play/{action}` | `treat` · `walk` · `ball` · `pet` |
| POST | `/api/pets/{id}/med-schedule/check` | 슬롯 체크 → 투약 기록 생성. 체크 해제는 `DELETE /api/records/{record_id}` |
| POST | `/api/food-label/parse` | 성분표 OCR 글자(`{text, mode}`) → 성분 수치 · 칼로리 · 원료 키워드 · 의심값 (`mode=basic`은 비교 실험용 기본 파서) |
| POST | `/api/pets/{id}/food-check` | 성분 수치 → AAFCO 기준 + 우리 개 상태(질환·BCS·인지기능) 평가 |

기록 `type` 별 필수 값:

| type | 필수 | 선택 |
|---|---|---|
| `meal` | `meal_amount` (0~100%, 칩: 거의 안먹음 10 / 절반 50 / 대부분 80 / 전부 100) | `note` |
| `poop` | `poop_firmness` (무름/정상/딱딱함) | `poop_color`, `poop_blood`, `note` |
| `weight` | `weight_kg` | `note` |
| `med` | `med_name` | `note` |

`recorded_at`을 안 보내면 서버의 현재 시각이 들어가요. 시간은 타임존 없는 로컬 시각(`2026-09-24T08:10:00`)으로 주고받아요.
펫 응답의 `latest_weight_kg`는 가장 최근 체중 기록 값이에요. 체중 기록이 없으면 등록할 때 입력한 체중을 보여줘요.

## 리포트 경고 규칙

기준값은 `backend/app/routers/report.py` 맨 위 상수에 있어요. 알림마다 근거 자료 링크가 같이 표시돼요.
수의학 자료에 숫자 기준이 없는 부분은 **서비스 자체 기준**으로 따로 표시했어요.

| 알림 | 단계 | 조건 | 근거 |
|---|---|---|---|
| 체중 감소 | 주의 | 그래프 기간의 첫 체중 기록 대비 **5% 이상** 감소 | 노령견이 1년 안에 5% 넘게 빠지면 진단적 검사가 필요할 수 있음 ([Cortadellas, CEU Cardenal Herrera 대학, Schermerhorn 2017 인용](https://vetsandclinics.com/en/library/weight-loss-in-elderly-dogs)) |
| 체중 감소 | 위험 | **10% 초과** 감소 | 정상 체중의 10%를 넘는 감소는 임상적으로 의미 있음 ([VCA Animal Hospitals](https://vcahospitals.com/know-your-pet/weight-loss-abnormal-in-dogs)) |
| 식사 거부 | 위험 | 어제·오늘 기록된 식사(2회 이상)가 모두 '거의 안먹음' | 24~48시간 넘게 먹지 않으면 진료 권장 ([PetMD, 수의사 작성·감수](https://www.petmd.com/dog/symptoms/why-my-dog-not-eating)) |
| 식욕 감소 | 주의 | 최근 3일 평균 식사량이 그 이전 평균보다 20% 이상 적음 (이전 기록 5회 이상) | 식욕 감소는 수의사에게 연락할 사유 ([AAHA 2023 Senior Care Guidelines](https://www.aaha.org/wp-content/uploads/globalassets/02-guidelines/2023-aaha-senior-care-guidelines-for-dogs-and-cats/resources/aaha-senior-care-guidelines-your-senior-pet.pdf)). 수치 기준은 없어서 **3일·20%는 서비스 자체 기준**. 3일은 먹지 못하면 3~5일 안에 악영향이 나타난다는 문헌의 하한 ([The Veterinary Nurse](https://www.theveterinarynurse.com/content/clinical/nutritional-management-of-hospitalised-dogs-and-cats)) |
| 혈변·검붉은 변 | 위험 | 최근 7일 안에 혈변·점액 또는 검붉은색 변이 1번이라도 있음 | 피 섞인 변, 검고 끈적한 변은 수의사에게 연락 ([AAHA 2023](https://www.aaha.org/wp-content/uploads/globalassets/02-guidelines/2023-aaha-senior-care-guidelines-for-dogs-and-cats/resources/aaha-senior-care-guidelines-your-senior-pet.pdf), [PetMD, 응급의학 전문의 작성](https://www.petmd.com/dog/symptoms/dog-pooping-blood)). 7일은 알림을 보여주는 기간(서비스 기준) |
| 무른 변 | 주의 | 3일 연속 '무름' 기록 (오늘이나 어제까지 이어진 경우) | 묽은 변이 2일 넘게 지속되면 진료 권장 ([VCA Animal Hospitals](https://vcahospitals.com/know-your-pet/diarrhea-in-dogs)) |

'배변 정상 비율'은 통계로만 보여주고 알림은 띄우지 않아요. 근거가 되는 수치 기준을 찾지 못했기 때문이에요.
모든 알림은 기록에 기반한 참고용이며 수의사의 진단을 대신하지 않아요. 화면에도 이 문구를 표시해요.

데모 버튼(리포트 탭 하단)은 `npm run dev`로 실행할 때만 보여요. 데모 기록은 note가 `[데모] 자동 생성 기록`인 기록이라서, 직접 입력한 기록은 지워지지 않아요.

## 케어 체크 척도

문항과 점수 기준은 `backend/app/care_scales.py` 한 곳에 있고, 화면은 이 정의를 받아서 폼을 그려요.

| 체크 | 주기 | 척도 | 점수 해석 |
|---|---|---|---|
| 인지기능 | 한 달에 한 번 | **CCDR** (Canine Cognitive Dysfunction Rating scale), 13문항, 11번 ×2·12번 ×3 가중치, 16~80점 ([Salvin et al. 2011, The Veterinary Journal](https://pubmed.ncbi.nlm.nih.gov/20542455/)) | 40점 미만 정상 / 40~49점 위험군 / 50점 이상 인지기능장애 의심 |
| 삶의 질 | 한 달에 한 번 | **HHHHHMM** 삶의 질 척도, 7항목 × 0~10점 ([Villalobos, IVAPM 2011 개정판](https://caringpathways.com/wp-content/uploads/2018/02/QualityofLifeScale.pdf)) | 35점 초과 양호 / 35점 이하 돌봄 상담 권장 |
| 거동 | 매일 | **서비스 자체 간이 체크** 4문항 (0~2점, 합계 0~8점 불편 점수) | 해석 기준 없음 (추이만 기록) |

- CCDR 한국어 문항은 제가 옮긴 **비공식 번역**이에요. 검증된 한국어판이 아니라는 점을 발표 때 밝혀 주세요.
- 거동 체크는 골관절염 설문 LOAD(Liverpool Osteoarthritis in Dogs)의 주제(휴식 후 뻣뻣함, 절뚝거림, 활동량 등)를 참고했어요. LOAD 원문은 개발자 허가가 있어야 쓸 수 있어서 그대로 싣지 않았고, 그래서 점수 기준도 두지 않았어요 ([LOAD 타당도 연구](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0058125)).
- 상업 서비스로 출시한다면 CCDR·HHHHHMM도 저작권자 이용 허락을 확인해야 해요.

## 투약 스케줄

- 약마다 매일 복용 시간(최대 6개)을 등록하면, 케어 탭에 오늘의 체크리스트가 생겨요.
- 체크리스트에서 체크하면 투약 기록(records)이 만들어져서 홈 '오늘의 기록'과 리포트에도 같이 쌓여요. 홈에서 '투약'으로 기록해도 체크리스트에 반영돼요.
- 기록은 시간이 가장 가까운 슬롯(앞뒤 3시간 안)에 붙어요.
  - 예정 시간 앞뒤 1시간: **지금 복용**
  - 예정 시간 + 1시간이 지나도 기록 없음: **놓침** 알림
  - 이미 복용 완료인 슬롯에 또 기록됨: **중복 투약 확인** 알림
- 목업에 있던 "두 약의 복용 간격이 짧아요" 경고는 넣지 않았어요. 약 사이 간격은 약 조합과 처방마다 달라서 공통 기준이 없어요. 대신 약마다 **수의사 지시사항**(예: 식후 30분, 진통제와 2시간 간격)을 적어두면 체크리스트에 같이 보여줘요.

## AI건강 탭

**비만도 체크**
- WSAVA의 **BCS 9점 척도**로 판단해요. 1~3점은 저체중 쪽, 4~5점은 이상적인 체형, 6~9점은 과체중 쪽이에요 ([WSAVA BCS](https://wsava.org/wp-content/uploads/2020/01/Body-Condition-Score-Dog.pdf)). BCS 결과는 `care_checks`에 `kind='bcs'`로 저장돼요.
- 품종 표준 체중은 **참고용**으로만 보여줘요 ([AKC Breed Weight Chart](https://www.akc.org/expert-advice/nutrition/breed-weight-chart/)). 도그쇼 기준 성견 체중이라 반려견은 개체차가 커요.
- "BCS 1점당 체지방 몇 %"로 이상 체중을 계산하는 방법은 넣지 않았어요. 자료마다 5%, 10~15%로 달라서예요 ([Clinician's Brief](https://www.cliniciansbrief.com/article/body-condition-score-techniques-dogs), [University of Guelph](https://ovcpetnutrition.uoguelph.ca/2021/10/25/scoring-for-health/)).
- 품종 표에는 AKC 표준이 분명한 25개 품종과 진돗개(성별 구분)가 있어요. 비글처럼 크기 구분이 복잡한 품종은 뺐어요.

**증상 정보**: 출처를 확인한 4가지(식욕 부진, 혈변·검은 변, 설사, 체중 감소)만 넣었어요. `backend/app/health_info.py`에 출처와 함께 추가하면 돼요.

**내 주변 동물병원**: 담당 병원, 근처 동물병원, 24시 동물병원을 카카오맵·네이버 지도 검색 링크로 열어요.

**AI 상담 설정** (무료 · Gemini)
1. [Google AI Studio](https://aistudio.google.com/apikey)에 구글 계정으로 로그인해 **Create API key**로 키를 받아요. 무료 티어는 결제 정보 없이 쓸 수 있어요 (분당·하루 요청 수 제한이 있어요).
2. `backend/.env.example`을 복사해 `backend/.env`로 이름을 바꾸고, 키를 넣어요:
   ```
   GEMINI_API_KEY=발급받은 키
   ```
3. 백엔드를 다시 켜면 AI건강 탭의 **AI 건강 상담**이 연결돼요.
4. 모델은 기본 `gemini-3.8-flash`이고, 한도에 걸리거나 모델이 없으면 `gemini-3.5-flash-lite`로 한 번 더 시도해요. 바꾸려면 `.env`에 `SEVENCARE_AI_MODEL=모델이름`을 넣어요.
5. Claude API를 쓰고 싶으면 `.env`에 `ANTHROPIC_API_KEY=키`를 넣어요 (유료, `GEMINI_API_KEY`가 없을 때만 써요).

- 키는 코드나 Git에 올리지 마세요. `.env`는 `.gitignore`에 들어 있어요. 화면 캡처·발표 자료에도 키가 보이지 않게 주의해요.
- 무료 티어에서는 입력 내용이 구글의 서비스 개선에 쓰일 수 있어요. 실제 보호자 개인정보는 넣지 않고, 반려견 기록 요약만 보내요.
- AI에게는 최근 2주 기록, 리포트 알림, 복용 약, 케어 체크 결과, 병원 방문 기록을 요약해서 함께 보내요 (`build_context`).
- 시스템 프롬프트로 이렇게 제한했어요: 진단하지 않기, 응급 신호가 보이면 병원 연락을 먼저 안내하기, 약 용량을 바꾸라고 하지 않기, 기록에 없는 내용 지어내지 않기.

## 병원 지참용 리포트

리포트 탭의 **병원 지참용 리포트 내보내기**를 누르면 A4 문서 화면이 열려요. **PDF로 저장 · 인쇄**를 누르고 인쇄 창에서 대상을 **PDF로 저장**으로 고르면 돼요. 파일 이름은 `이름_건강리포트_날짜`로 자동으로 들어가요.

- 담기는 내용: 기본 정보, 기록에서 확인된 주의 신호, 주별 체중 추이, 식사·배변 요약, 복용 중인 약과 최근 14일 복용 기록, 케어 체크 최근 결과, 최근 14일 특이 기록(혈변·무른 변·거의 안 먹음·메모), 최근 병원 방문
- **수의사에게 묻고 싶은 것** 칸은 인쇄 직전에 적는 메모예요. 저장되지 않아요.
- PDF를 서버에서 만들지 않고 브라우저 인쇄를 쓴 이유: 서버에서 만들면 한글 글꼴 설정이 PC마다 달라지는데, 브라우저 인쇄는 추가 설치 없이 한글이 그대로 나와요.

## 프로필 사진

- 펫 등록·수정 화면 맨 위 동그라미를 눌러 사진을 골라요. 홈, 마이펫, 놀이 탭 아바타에 보여요.
- 브라우저에서 사진을 긴 변 512px JPEG로 줄여서 올려요. 서버는 data URL(JSON)로 받아서 `pet_photos` 테이블에 저장해요. 파일 업로드용 추가 패키지(python-multipart)가 필요 없어요.
- 올릴 때 사진 가운데 부분의 평균 색을 뽑아서(`photo_color`) 놀이 탭 캐릭터의 털 색으로 써요.

## 놀이 탭

> 현재 발표 범위에서 빼서 탭바에서 숨겨 두었어요 (`components/common.jsx`의 `TABS`에서 주석 해제하면 다시 보여요).

- 앱에서 직접 그린(SVG) 오리지널 강아지 캐릭터예요. 털 색은 프로필 사진에서, 귀 모양(선 귀·늘어진 귀)은 품종에서 정해요.
- **간식 주기 · 산책 가기 · 공놀이 · 쓰다듬기**로 행복도와 포만감을 채워요. 두 수치는 시간이 지나면 조금씩 줄어요 (행복도 시간당 2, 포만감 시간당 3).
- 산책은 3시간, 공놀이는 30분마다 할 수 있어요.
- **간식은 진짜 돌봄 기록으로 모아요.** 오늘 남긴 기록 종류(식사·배변·체중·투약)마다 1개, 케어 체크 1번마다 1개, 하루 최대 6개예요. 데모 기록은 세지 않아요. 게임을 하려면 기록을 하게 되도록 만든 장치예요.
- 규칙 숫자는 `backend/app/play_logic.py`에 있어요.
- 가상 간식이라 실제 간식 양과는 관계없다는 안내를 화면에 표시해요.

## 사료 성분 분석 (AI건강 탭)

사료 포장 뒷면 성분표를 찍으면, 이 강아지에게 맞는 사료인지 근거와 함께 알려줘요.

1. **글자 인식 (브라우저)**: Tesseract.js(무료 오픈소스 OCR, `kor+eng`)를 CDN에서 불러와 크롬 안에서 실행해요. 인식 전에 사진을 키우고(가로 1600px 이상) 흑백·명암 보정을 해요. 처음 한 번은 한국어 데이터를 받느라 인터넷이 필요해요.
2. **성분 추출 (`backend/app/food_label.py`)**: 조단백질·조지방·조섬유·조회분·칼슘·인·수분·나트륨과 kcal/kg을 정규식으로 찾아요. OCR이 자주 틀리는 글자(`2O.5`→`20.5`, `1l`→`11`, `O.8`→`0.8`)를 고치고, 사료에 나올 수 없는 값(예: 인 8%)은 비워 두고 사용자에게 확인을 부탁해요. 읽은 값은 화면에서 직접 고칠 수 있어요.
3. **환산**: 포장 표시값을 **건물 기준(DM)** 으로 바꿔요 `값 ÷ (100 − 수분) × 100`. 칼로리 표시가 없으면 **수정 Atwater**로 추정해요 `10 × (3.5×단백질 + 8.5×지방 + 3.5×NFE)`.
4. **평가**

| 대상 | 기준 | 출처 |
|---|---|---|
| 모든 성견·노령견 | 단백질 ≥ 18%, 지방 ≥ 5.5%, 칼슘 0.5~2.5%, 인 0.4~1.6%, 칼슘:인 1~2 (건물 기준) | AAFCO Dog Food Nutrient Profiles (성견 유지) |
| 기저 질환에 '신장' | 인 0.4~1.2 g/1000kcal (신장 처방식 범위), IRIS 2단계부터 식이 관리 | Cline, ACVN (Today's Veterinary Practice) |
| 기저 질환에 '심장·이첨판' | 나트륨 B2 80~99, C 50~79 mg/100kcal | ACVIM MMVD 합의 지침 (2019) |
| 기저 질환에 '관절·슬개골' | 오메가3(EPA·DHA) 원료 여부 | AAHA 2023 Senior Care Guidelines |
| 인지기능 체크 40점 이상 | MCT(중쇄지방산) 원료 여부 | AAHA 2023 Senior Care Guidelines |
| 비만도 BCS 6 이상 | kcal/kg 안내 | 수정 Atwater |

### 인식 정확도 측정 페이지

`http://localhost:5173/eval.html` (개발용). 성분표 사진을 여러 장 올리고 사진마다 정답을 적은 뒤 **전체 측정하기**를 누르면, 네 가지 방법의 칸 단위 정확도(±0.05 이내면 정답)를 비교해요.

| 방법 | 읽기 방식 | 파서 |
|---|---|---|
| 처음 버전 | PSM 3 (자동 배치) | 기본 (`mode=basic`) |
| 읽기 방식만 개선 | PSM 6 (줄 단위) | 기본 |
| 파서만 개선 | PSM 3 | 개선 (표 인식 · 소수점 복원 · 범위 확인) |
| 최종 (앱과 동일) | PSM 6, 4칸 미만이면 PSM 3 재시도 | 개선 |

정답은 브라우저에 자동 저장되고, **정답 저장/불러오기**(JSON)로 옮길 수 있어요. **CSV 내보내기**로 사진별 결과를 받을 수 있어요.

AAFCO에는 '노령견' 별도 기준이 없어서 성견 유지 기준을 써요. 표시값은 보증값(최소·최대)이라 실제 함량과 다를 수 있다는 안내를 함께 보여줘요.

## 배포 (Render 무료 서버)

서버 하나가 API와 화면을 함께 제공해요. `npm run build`로 만든 `frontend/dist`가 있으면 FastAPI가 그 화면도 보여줘서, 주소 하나로 PC·휴대폰 어디서든 접속할 수 있어요.

**로컬에서 배포 모양 그대로 확인하기**
```
cd frontend
npm run build
cd ../backend
.venv\Scripts\python -m uvicorn app.main:app
```
→ `http://localhost:8000` 에서 화면까지 열려요 (Vite 개발 서버 없이).

**Render에 올리기**
1. GitHub에 저장소를 만들고 이 폴더를 올려요 (`.env`, `sevencare.db`, 발표 자료는 `.gitignore`로 빠져요).
2. [Render](https://render.com) → **New → Blueprint** → 저장소 선택. 루트의 `render.yaml`을 읽어서 서비스를 만들어요.
3. 환경변수 `GEMINI_API_KEY`에 키를 입력해요 (코드에는 넣지 않아요).
4. 배포가 끝나면 `https://sevencare-xxxx.onrender.com` 같은 주소가 생겨요.

**무료 서버의 특징**
- 15분 동안 접속이 없으면 잠들고, 다음 접속 때 깨어나는 데 1분 정도 걸려요. 발표 전에 미리 한 번 열어 두세요.
- 서버가 다시 켜지면 DB가 초기화돼요. 그래서 `SEVENCARE_DEMO_SEED=1`로 비어 있을 때 데모 데이터(세븐)를 자동으로 넣어요.

## 다음 단계 후보

- 세부 다듬기 (화면별 문구, 입력 편의, 빈 상태 안내 등)
- 놀이 탭 캐릭터를 AI 이미지로 바꾸기 (이미지 생성 API 키 필요)
- AI 상담 API 키 연결
- 증상 정보·품종별 주의 질환 항목 추가 (출처 확인 후)
