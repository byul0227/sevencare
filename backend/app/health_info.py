"""증상별 '언제 병원에 가야 하나' 정보. 출처를 확인한 항목만 넣었어요 (새 항목도 출처와 함께 추가)."""

AAHA_SENIOR = {"name": "AAHA 2023 Senior Care Guidelines, 보호자용 가정 모니터링 안내",
               "url": "https://www.aaha.org/wp-content/uploads/globalassets/02-guidelines/2023-aaha-senior-care-guidelines-for-dogs-and-cats/resources/aaha-senior-care-guidelines-your-senior-pet.pdf"}

SYMPTOMS = [
    {
        "id": "appetite",
        "title": "식욕 부진 · 밥을 안 먹어요",
        "summary": "노령견의 식욕 변화는 그 자체로 수의사에게 알릴 만한 신호예요.",
        "when_to_vet": [
            "24~48시간 넘게 밥을 먹지 않을 때",
            "안 먹으면서 구토·설사·기운 없음·호흡 곤란이 함께 있을 때",
            "노령견이라면 식욕이 눈에 띄게 줄어든 것만으로도 연락해 보세요",
        ],
        "home_tips": ["사료를 살짝 데우거나, 평소 잘 먹던 기호성 좋은 음식을 줘 보세요 (AAHA 권장)"],
        "sources": [
            {"name": "PetMD, Dog Not Eating? (수의사 작성·감수)", "url": "https://www.petmd.com/dog/symptoms/why-my-dog-not-eating"},
            AAHA_SENIOR,
        ],
    },
    {
        "id": "blood_stool",
        "title": "혈변 · 검은 변",
        "summary": "피가 섞인 변, 검고 끈적한 변은 수의사에게 연락해야 하는 신호예요.",
        "when_to_vet": [
            "혈변이 보이면 우선 동물병원에 전화해 상담하세요",
            "다음 변에서도 피가 줄지 않으면 바로 연락하세요",
        ],
        "emergency": ["기운 없음·쇠약", "잇몸이 창백함", "구토", "힘을 줘도 변이 거의 안 나옴",
                      "먹거나 마시지 않음", "반응이 없음"],
        "sources": [
            {"name": "PetMD, Dog Pooping Blood (응급의학 전문의 작성)", "url": "https://www.petmd.com/dog/symptoms/dog-pooping-blood"},
            AAHA_SENIOR,
        ],
    },
    {
        "id": "diarrhea",
        "title": "설사 · 무른 변",
        "summary": "건강한 개도 가끔 변이 무를 수 있지만, 이어지면 진료가 필요해요.",
        "when_to_vet": [
            "묽은 변이 이틀 넘게 계속될 때",
            "피가 섞인 심한 설사이거나, 다른 아픈 증상이 함께 있을 때는 가능한 빨리",
        ],
        "sources": [
            {"name": "VCA Animal Hospitals, Diarrhea in Dogs", "url": "https://vcahospitals.com/know-your-pet/diarrhea-in-dogs"},
        ],
    },
    {
        "id": "weight_loss",
        "title": "체중 감소",
        "summary": "노령견은 근육이 줄면서 체중이 빠지기도 하지만, 원인을 확인해야 하는 경우가 많아요.",
        "when_to_vet": [
            "1년 안에 체중이 5% 넘게 줄었을 때 (검사가 필요할 수 있어요)",
            "정상 체중의 10% 넘게 줄었을 때 (임상적으로 의미 있는 감소)",
        ],
        "sources": [
            {"name": "Cortadellas, CEU Cardenal Herrera 대학 수의학과", "url": "https://vetsandclinics.com/en/library/weight-loss-in-elderly-dogs"},
            {"name": "VCA Animal Hospitals, Abnormal Weight Loss in Dogs", "url": "https://vcahospitals.com/know-your-pet/weight-loss-abnormal-in-dogs"},
        ],
    },
]
