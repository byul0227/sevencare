"""케어 체크 척도 정의 (질문·보기·점수·해석 기준·출처).

프론트엔드는 GET /api/care-scales 로 이 정의를 받아 폼을 그려요. 질문을 바꾸려면 여기만 고치면 돼요.

- cognitive : CCDR (Canine Cognitive Dysfunction Rating scale, Salvin et al. 2011) — 한국어는 비공식 번역
- qol       : HHHHHMM 삶의 질 척도 (Villalobos)
- bcs       : 신체충실지수(BCS) 9점 척도 (WSAVA) — AI건강 탭 '비만도 체크'에서 사용
- mobility  : 일일 거동 간이 체크 — LOAD 설문의 주제(휴식 후 뻣뻣함, 절뚝거림, 활동량 등)를 참고해
              서비스가 만든 문항이에요. 검증된 척도가 아니라서 점수 해석 기준은 두지 않아요.
              (LOAD 원문은 개발자 허가가 필요해서 그대로 싣지 않았어요)
"""

FREQ = [  # CCDR 1~6번
    {"value": 1, "label": "없음"},
    {"value": 2, "label": "월 1회"},
    {"value": 3, "label": "주 1회"},
    {"value": 4, "label": "하루 1회"},
    {"value": 5, "label": "하루 2회 이상"},
]
PERCENT = [  # CCDR 7번
    {"value": 1, "label": "전혀"},
    {"value": 2, "label": "1~30%"},
    {"value": 3, "label": "31~60%"},
    {"value": 4, "label": "61~99%"},
    {"value": 5, "label": "항상"},
]
CHANGE = [  # CCDR 8~12번: 6개월 전과 비교
    {"value": 1, "label": "훨씬 줄었음"},
    {"value": 2, "label": "조금 줄었음"},
    {"value": 3, "label": "비슷함"},
    {"value": 4, "label": "조금 늘었음"},
    {"value": 5, "label": "훨씬 늘었음"},
]
CHANGE_REVERSED = [  # CCDR 13번: 활동 시간은 줄수록 점수가 높음
    {"value": 1, "label": "훨씬 늘었음"},
    {"value": 2, "label": "조금 늘었음"},
    {"value": 3, "label": "비슷함"},
    {"value": 4, "label": "조금 줄었음"},
    {"value": 5, "label": "훨씬 줄었음"},
]

SCALES = {
    "mobility": {
        "kind": "mobility",
        "title": "거동 체크",
        "cadence": "매일",
        "description": "기상 · 계단 · 절뚝거림 · 활동량을 매일 체크해요",
        "instructions": "오늘 하루 모습을 떠올리며 골라 주세요.",
        "input": "choice",
        "questions": [
            {"id": "m1", "text": "쉬고 난 뒤 일어날 때", "options": [
                {"value": 0, "label": "바로 일어남"}, {"value": 1, "label": "약간 뻣뻣함"}, {"value": 2, "label": "많이 힘들어함"}]},
            {"id": "m2", "text": "계단 · 턱 오르내리기", "options": [
                {"value": 0, "label": "수월함"}, {"value": 1, "label": "주저함"}, {"value": 2, "label": "못 함"}]},
            {"id": "m3", "text": "걸을 때 절뚝거림", "options": [
                {"value": 0, "label": "없음"}, {"value": 1, "label": "가끔"}, {"value": 2, "label": "자주"}]},
            {"id": "m4", "text": "오늘 활동량", "options": [
                {"value": 0, "label": "평소와 같음"}, {"value": 1, "label": "감소"}, {"value": 2, "label": "거의 없음"}]},
        ],
        "max_score": 8,  # 불편 점수: 높을수록 불편
        "bands": [],     # 검증된 척도가 아니라 해석 기준 없음
        "source": "LOAD(Liverpool Osteoarthritis in Dogs) 설문 주제를 참고한 서비스 자체 간이 체크 (검증된 척도 아님)",
        "source_url": "https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0058125",
    },
    "cognitive": {
        "kind": "cognitive",
        "title": "인지기능 체크",
        "cadence": "매월",
        "description": "배회 · 멍하니 있기 · 알아보지 못함 등 13문항 (CCDR) · 한 달에 한 번",
        "instructions": "최근 모습(1~7번)과 6개월 전과 비교한 변화(8~13번)를 골라 주세요. 한 달에 한 번 정도 점검하면 변화를 보기 좋아요.",
        "input": "choice",
        "questions": [
            {"id": "c1", "text": "목적 없이 서성이거나, 빙빙 돌거나, 배회한다", "options": FREQ},
            {"id": "c2", "text": "벽이나 바닥을 멍하니 바라본다", "options": FREQ},
            {"id": "c3", "text": "가구 뒤나 구석 같은 곳에 끼어 빠져나오지 못한다", "options": FREQ},
            {"id": "c4", "text": "익숙한 사람이나 다른 반려동물을 알아보지 못한다", "options": FREQ},
            {"id": "c5", "text": "벽이나 문에 부딪힌다", "options": FREQ},
            {"id": "c6", "text": "쓰다듬으려 하면 피하거나 자리를 뜬다", "options": FREQ},
            {"id": "c7", "text": "바닥에 떨어진 음식을 찾지 못하는 경우", "options": PERCENT},
            {"id": "c8", "text": "[6개월 전보다] 서성이기 · 빙빙 돌기 · 배회", "options": CHANGE},
            {"id": "c9", "text": "[6개월 전보다] 멍하니 바라보기", "options": CHANGE},
            {"id": "c10", "text": "[6개월 전보다] 전에는 깨끗이 쓰던 곳에 배변 실수", "options": CHANGE},
            {"id": "c11", "text": "[6개월 전보다] 떨어진 음식을 찾지 못함", "options": CHANGE, "weight": 2},
            {"id": "c12", "text": "[6개월 전보다] 익숙한 사람 · 동물을 알아보지 못함", "options": CHANGE, "weight": 3},
            {"id": "c13", "text": "[6개월 전보다] 활발하게 활동하는 시간", "options": CHANGE_REVERSED},
        ],
        "max_score": 80,  # 최소 16점
        "bands": [
            {"min": 50, "code": "ccd", "level": "alert", "label": "인지기능장애 의심",
             "advice": "50점 이상은 인지기능장애(CCD) 소견에 해당해요. 수의사 진료를 권해요."},
            {"min": 40, "code": "risk", "level": "warn", "label": "위험군",
             "advice": "40~49점은 인지기능장애 위험군이에요. 정기적으로 다시 점검하고 수의사와 상의해 보세요."},
            {"min": 0, "code": "normal", "level": "ok", "label": "정상 범위",
             "advice": "40점 미만은 정상 범위예요."},
        ],
        "source": "Salvin et al. (2011) The canine cognitive dysfunction rating scale (CCDR), The Veterinary Journal · 한국어 문항은 비공식 번역",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/20542455/",
    },
    "qol": {
        "kind": "qol",
        "title": "삶의 질 평가",
        "cadence": "매월",
        "description": "통증 · 식욕 · 위생 · 행복감 등 7개 항목 (HHHHHMM) · 한 달에 한 번",
        "instructions": "각 항목을 0~10점으로 평가해 주세요. 10점이 가장 좋은 상태예요. 모든 항목의 막대를 한 번씩 움직여 주세요.",
        "input": "slider",
        "min": 0,
        "max": 10,
        "questions": [
            {"id": "q1", "text": "통증 (Hurt)", "hint": "통증이 잘 조절되고 숨쉬기가 편한가요? 호흡 곤란은 무엇보다 중요해요."},
            {"id": "q2", "text": "식욕 (Hunger)", "hint": "충분히 먹고 있나요? 손으로 먹여야 하나요?"},
            {"id": "q3", "text": "수분 (Hydration)", "hint": "물을 충분히 마시나요? 탈수 기미는 없나요?"},
            {"id": "q4", "text": "위생 (Hygiene)", "hint": "배변 후 깨끗하게 관리되나요? 욕창은 없나요?"},
            {"id": "q5", "text": "행복감 (Happiness)", "hint": "가족이나 장난감에 반응하고 즐거움을 표현하나요?"},
            {"id": "q6", "text": "거동 (Mobility)", "hint": "도움 없이 일어나고 움직일 수 있나요?"},
            {"id": "q7", "text": "좋은 날이 더 많음 (More good days)", "hint": "요즘 힘든 날보다 좋은 날이 더 많나요?"},
        ],
        "max_score": 70,
        "bands": [
            {"min": 36, "code": "acceptable", "level": "ok", "label": "양호",
             "advice": "35점을 넘으면 삶의 질이 유지되고 있는 것으로 봐요."},
            {"min": 0, "code": "low", "level": "alert", "label": "돌봄 상담 권장",
             "advice": "35점 이하는 삶의 질이 많이 낮아졌을 수 있다는 신호예요. 통증 관리와 돌봄 계획을 수의사와 상담해 보세요."},
        ],
        "source": "Villalobos, Quality of Life Scale (HHHHHMM) · IVAPM 2011 완화의료 가이드라인 개정판",
        "source_url": "https://caringpathways.com/wp-content/uploads/2018/02/QualityofLifeScale.pdf",
    },
    "bcs": {
        "kind": "bcs",
        "title": "비만도 체크 (BCS)",
        "cadence": "한 달에 한 번",
        "description": "갈비뼈 · 허리 · 배 라인으로 보는 9점 체형 점수 (WSAVA)",
        "instructions": "갈비뼈를 손으로 만져 보고, 위에서 허리를, 옆에서 배 라인을 본 뒤 가장 비슷한 설명을 골라 주세요.",
        "input": "choice",
        "questions": [
            {"id": "bcs", "text": "지금 체형과 가장 비슷한 것", "options": [
                {"value": 1, "label": "1 · 멀리서도 갈비뼈·허리뼈·골반뼈가 보이고 근육이 눈에 띄게 줄었어요. 만져지는 지방이 없어요."},
                {"value": 2, "label": "2 · 갈비뼈·허리뼈·골반뼈가 쉽게 보이고 만져지는 지방이 없어요. 근육이 조금 줄었어요."},
                {"value": 3, "label": "3 · 갈비뼈가 쉽게 만져지고 보이기도 해요. 허리와 배 라인이 뚜렷하게 들어가 있어요."},
                {"value": 4, "label": "4 · 갈비뼈가 얇은 지방 아래로 쉽게 만져져요. 위에서 허리가 보이고 옆에서 배가 올라가 있어요."},
                {"value": 5, "label": "5 · 갈비뼈가 과한 지방 없이 만져져요. 위에서 갈비뼈 뒤로 허리가 보이고, 옆에서 배가 올라가 있어요."},
                {"value": 6, "label": "6 · 갈비뼈가 두꺼운 지방 아래로 만져져요. 위에서 허리가 잘 안 보이고 배 라인이 약해요."},
                {"value": 7, "label": "7 · 갈비뼈가 아주 두꺼운 지방 때문에 잘 안 만져져요. 허리가 없고 허리 위에 지방이 두꺼워요."},
                {"value": 8, "label": "8 · 갈비뼈가 만져지지 않아요. 허리와 배 라인이 없고 목·다리에도 지방이 붙었어요."},
                {"value": 9, "label": "9 · 8번에 더해 배가 눈에 띄게 불룩해요."},
            ]},
        ],
        "max_score": 9,
        "bands": [
            {"min": 6, "code": "over", "level": "warn", "label": "과체중 쪽",
             "advice": "6점 이상은 이상 체형(4~5점)보다 무거운 상태예요. 급여량과 체중 관리 계획을 수의사와 상의해 보세요."},
            {"min": 4, "code": "ideal", "level": "ok", "label": "이상적인 체형",
             "advice": "4~5점은 이상적인 체형이에요."},
            {"min": 1, "code": "under", "level": "warn", "label": "저체중 쪽",
             "advice": "3점 이하는 이상 체형보다 마른 상태예요. 노령견은 근육 감소나 질병 때문일 수 있어 수의사와 상담해 보세요."},
        ],
        "source": "WSAVA Global Nutrition Committee, Body Condition Score (9점 척도) · 한국어 설명은 요약 번역",
        "source_url": "https://wsava.org/wp-content/uploads/2020/01/Body-Condition-Score-Dog.pdf",
    },
}


class ScaleError(ValueError):
    pass


def score_answers(kind: str, answers: dict) -> dict:
    """답변을 검증하고 점수·해석을 계산해요. 잘못된 답이면 ScaleError."""
    scale = SCALES.get(kind)
    if scale is None:
        raise ScaleError(f"알 수 없는 체크 종류예요: {kind}")

    total = 0
    clean = {}
    for q in scale["questions"]:
        if q["id"] not in answers:
            raise ScaleError(f"'{q['text']}' 문항에 답해 주세요")
        v = answers[q["id"]]
        if isinstance(v, bool) or not isinstance(v, int):
            raise ScaleError(f"'{q['text']}' 답이 올바르지 않아요")
        if scale["input"] == "slider":
            if not scale["min"] <= v <= scale["max"]:
                raise ScaleError(f"'{q['text']}' 점수는 {scale['min']}~{scale['max']} 사이여야 해요")
        elif v not in {o["value"] for o in q["options"]}:
            raise ScaleError(f"'{q['text']}' 답이 올바르지 않아요")
        clean[q["id"]] = v
        total += v * q.get("weight", 1)

    extra = set(answers) - set(clean)
    if extra:
        raise ScaleError(f"알 수 없는 문항이 있어요: {', '.join(sorted(extra))}")

    band = next((b for b in scale["bands"] if total >= b["min"]), None)
    return {"answers": clean, "score": total, "band": band}
