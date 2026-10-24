"""사료 성분표 분석 테스트 (파싱 · 환산 · 평가 · API)."""
import pytest

from app.food_label import estimate_kcal, evaluate, parse_label, per_1000kcal, to_dry_matter
from test_api import client, make_pet  # noqa: F401

KO_LABEL = """등록성분량
조단백질 26% 이상, 조지방 12% 이상, 조섬유 4% 이하, 조회분 8% 이하,
칼슘 1.0% 이상, 인 0.8% 이상, 수분 10% 이하
원료: 닭고기, 현미, 연어오일(오메가3), 글루코사민"""

NOISY_LABEL = """등 록 성 분
조단백질 ..... 2O.5 % 이상
조 지 방 : 1l.0 % 이상
조섬유 : 5.0 %이하  조회분: 7,5% 이하
칼슘 : 0.9 % 이상  인 : 0.7 % 이상
수분 : 1O % 이하
대사에너지 3,560 kcal/kg"""

EN_LABEL = """GUARANTEED ANALYSIS
Crude Protein (min) 25.0%  Crude Fat (min) 14.0%
Crude Fiber (max) 4.0%  Moisture (max) 10.0%
Calcium (min) 1.1%  Phosphorus (min) 0.9%  Sodium (min) 0.3%
Calorie Content (calculated): 3,650 kcal/kg ME. Contains MCT oil"""


def test_parse_korean_label():
    r = parse_label(KO_LABEL)
    assert r["nutrients"] == {"protein": 26.0, "fat": 12.0, "fiber": 4.0, "ash": 8.0,
                              "calcium": 1.0, "phosphorus": 0.8, "moisture": 10.0}
    assert set(r["keywords"]) == {"omega3", "glucosamine"} and r["kcal_per_kg"] is None


def test_parse_fixes_common_ocr_mistakes():
    r = parse_label(NOISY_LABEL)
    n = r["nutrients"]
    assert n["protein"] == 20.5 and n["fat"] == 11.0 and n["ash"] == 7.5 and n["moisture"] == 10.0
    assert r["kcal_per_kg"] == 3560


def test_parse_rejects_impossible_values():
    r = parse_label("조단백질 26% 이상 칼슘 1.0% 인 8% 이상 수분 1O% 이하")   # 인 0.8%를 8%로 잘못 읽은 경우
    assert "phosphorus" not in r["nutrients"] and r["suspect"][0]["key"] == "phosphorus"
    assert parse_label("인 O.8% 이상")["nutrients"]["phosphorus"] == 0.8


TABLE_OCR = """념분량 GUARANTEED ANALYSYS                    |
조단백질| 조지방  |  조섬유 | 조회분 | wa  |  인 | FF
|
Crude Protein | Crude Fat   Crude Fiber   Cruda Ash
Calcium   Phosphorus   proms      ~

Ol        0,       o/       0

25.0% | 10.0% | 1.3% | 8.3% | 0.9%   0.87  23.0%

이상) Er | ERD CED"""


def test_parse_table_layout_from_real_photo():
    """실제 사료 포장 사진의 OCR 결과: 이름 줄과 숫자 줄이 따로, '칼슘'·'수분' 헤더는 못 읽고 0.8%는 0.87로 읽힘"""
    r = parse_label(TABLE_OCR)
    assert r["nutrients"] == {"protein": 25.0, "fat": 10.0, "fiber": 1.3, "ash": 8.3,
                              "calcium": 0.9, "phosphorus": 0.8, "moisture": 23.0}
    assert [f["key"] for f in r["found"] if f.get("corrected")] == ["phosphorus"]


def test_parse_table_without_readable_header():
    """이름 줄은 못 읽고 숫자 줄만 두 줄로 나뉘어 읽힌 경우 → 표준 순서로 채우고 '확인 필요' 표시"""
    text = "등록성분량 ㅁㄴㅇ ~~\n25.0% | 10.0% | 1.3% | 8.3%\n0.9% 0.87 23.0%\n이상 이하"
    r = parse_label(text)
    assert r["nutrients"] == {"protein": 25.0, "fat": 10.0, "fiber": 1.3, "ash": 8.3,
                              "calcium": 0.9, "phosphorus": 0.8, "moisture": 23.0}
    assert all(f["corrected"] for f in r["found"])


def test_parse_table_single_block_mode():
    """같은 사진을 '한 덩어리 글' 모드(PSM 6)로 읽은 결과: 표는 깔끔하지만 소수점을 가끔 놓침 (1.3→13, 0.8→08)"""
    text = """Baer GUARANTEED ANALYSYS |
— axjt | aye | asi | 2a ol ag
Crude Protein Crude Fat Crude Fiber Crude Ash Calcium Phosphorus Mo'!sture
25.0% | 10.0% | 13% | 8.3% | 0.9% 08% | 23.0%
fora min) Gum | CEIaD | CAD | CED | CED"""
    r = parse_label(text)
    assert r["nutrients"] == {"protein": 25.0, "fat": 10.0, "fiber": 1.3, "ash": 8.3,
                              "calcium": 0.9, "phosphorus": 0.8, "moisture": 23.0}
    assert {f["key"] for f in r["found"] if f["corrected"]} == {"fiber", "phosphorus"}


def test_parse_real_browser_ocr_psm6():
    """사용자 PC 크롬에서 Tesseract.js(kor+eng, PSM 6)로 실제 사진을 읽은 결과 그대로"""
    text = ("분량 GUARANTEED ANALYSYS\n= 조지방 | 조섬유 | 조회분 | wa ㅣ 인 | 수분\n"
            "CrudeProtein | CrudeFat | CrudeFiber | CrudeAsh  Calcium  Phosphorus | Moisture   3\n"
            "250% [100% | 13% | 8.3% | 09% | 08% | 23.0%\naD wD | CED <)\n~2222222229998998008000 |\n")
    r = parse_label(text)
    assert r["nutrients"] == {"protein": 25.0, "fat": 10.0, "fiber": 1.3, "ash": 8.3,
                              "calcium": 0.9, "phosphorus": 0.8, "moisture": 23.0}


def test_parse_english_label():
    r = parse_label(EN_LABEL)
    assert r["nutrients"]["sodium"] == 0.3 and r["nutrients"]["phosphorus"] == 0.9
    assert r["kcal_per_kg"] == 3650 and "mct" in r["keywords"]


def test_conversions():
    assert to_dry_matter(26, 10) == pytest.approx(28.89, abs=0.01)
    # 수정 Atwater: 10 × (3.5×26 + 8.5×12 + 3.5×(100−26−12−4−8−10)) = 3330
    assert estimate_kcal({"protein": 26, "fat": 12, "fiber": 4, "ash": 8, "moisture": 10}) == pytest.approx(3330)
    assert per_1000kcal(0.8, 3330) == pytest.approx(2.40, abs=0.01)


def test_evaluate_aafco_and_conditions():
    n = parse_label(KO_LABEL)["nutrients"]
    healthy = evaluate(n, condition=None)
    assert healthy["verdict"]["level"] == "ok"
    assert {c["code"] for c in healthy["checks"]} == {"protein_min", "fat_min", "calcium", "phosphorus", "ca_p_ratio"}
    assert all(c["source_url"].startswith("https://") for c in healthy["checks"])

    senior = evaluate(n, keywords=["omega3"], condition="신장 수치 경계, 슬개골 탈구", ccdr=46)
    by = {c["code"]: c for c in senior["checks"]}
    assert by["kidney_p"]["status"] == "bad" and by["kidney_p"]["value"] == pytest.approx(2.40, abs=0.01)
    assert by["joint_omega3"]["status"] == "ok" and by["cognitive_mct"]["status"] == "info"
    assert senior["verdict"]["level"] == "bad"


def test_evaluate_low_protein_and_missing_values():
    r = evaluate({"protein": 14, "fat": 4})
    assert r["verdict"]["level"] == "bad" and r["moisture"] == 10.0 and r["notes"]
    assert evaluate({})["verdict"]["level"] == "unknown"


def test_food_api_uses_pet_state(client):
    pid = make_pet(client, condition="만성 신장질환")["id"]
    client.post(f"/api/pets/{pid}/care-checks", json={"kind": "bcs", "answers": {"bcs": 7}})
    parsed = client.post("/api/food-label/parse", json={"text": KO_LABEL}).json()
    r = client.post(f"/api/pets/{pid}/food-check",
                    json={"nutrients": parsed["nutrients"], "keywords": parsed["keywords"]}).json()
    codes = {c["code"] for c in r["checks"]}
    assert {"kidney_p", "obese_kcal"} <= codes and r["pet"]["bcs"] == 7
    assert client.post("/api/pets/999/food-check", json={"nutrients": {}}).status_code == 404
    assert client.post(f"/api/pets/{pid}/food-check", json={"nutrients": {"protein": 150}}).status_code == 422


def test_basic_mode_for_comparison():
    """정확도 비교용 기본 파서는 표 모양 성분표를 거의 못 읽어요 (개선 전 상태 재현)"""
    text = ("CrudeProtein | CrudeFat | CrudeFiber | CrudeAsh  Calcium  Phosphorus | Moisture\n"
            "250% [100% | 13% | 8.3% | 09% | 08% | 23.0%")
    basic = parse_label(text, "basic")["nutrients"]
    full = parse_label(text)["nutrients"]
    assert len(full) == 7 and full["protein"] == 25.0
    assert sum(1 for k, v in full.items() if basic.get(k) == v) < 3
