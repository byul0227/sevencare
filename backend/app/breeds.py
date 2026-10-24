"""품종별 표준 체중 (AKC 품종 체중 차트 기준, 파운드 → kg 환산).

주의: 도그쇼 기준 '성견 표준'이라 반려견은 개체차가 커요. 비만도 판단은 체중보다 BCS(체형 점수)로 해요.
- max_only=True 는 AKC 표준이 "OO 파운드 이하"처럼 상한만 있는 품종이에요.
- 진돗개만 수컷/암컷 범위가 따로 있어요.
- 비글처럼 크기 구분이 복잡한 품종은 넣지 않았어요.
출처: https://www.akc.org/expert-advice/nutrition/breed-weight-chart/
"""
from typing import Optional

LB = 0.4536
SOURCE = "AKC(미국애견협회) Breed Weight Chart"
SOURCE_URL = "https://www.akc.org/expert-advice/nutrition/breed-weight-chart/"

# (표시 이름, 별칭들, 최소 lb, 최대 lb, 상한만 있음)  — 성별 공통
_BREEDS = [
    ("말티즈", ["말티즈", "몰티즈", "maltese"], None, 7, True),
    ("토이 푸들", ["토이푸들", "토이 푸들", "푸들", "toy poodle", "poodle"], 4, 6, False),
    ("미니어처 푸들", ["미니어처푸들", "미니어쳐푸들", "미니푸들", "miniature poodle"], 10, 15, False),
    ("스탠다드 푸들", ["스탠다드푸들", "스탠더드푸들", "standard poodle"], 40, 70, False),
    ("포메라니안", ["포메라니안", "포메", "pomeranian"], 3, 7, False),
    ("시츄", ["시츄", "시추", "shih tzu"], 9, 16, False),
    ("치와와", ["치와와", "chihuahua"], None, 6, True),
    ("요크셔테리어", ["요크셔테리어", "요크셔 테리어", "요키", "yorkshire terrier"], None, 7, True),
    ("비숑 프리제", ["비숑", "비숑프리제", "비숑 프리제", "bichon frise"], 12, 18, False),
    ("골든 리트리버", ["골든리트리버", "골든 리트리버", "골든", "golden retriever"], 55, 75, False),
    ("래브라도 리트리버", ["래브라도", "래브라도리트리버", "라브라도", "labrador retriever"], 55, 80, False),
    ("펨브록 웰시코기", ["웰시코기", "코기", "펨브록웰시코기", "pembroke welsh corgi"], None, 30, True),
    ("닥스훈트", ["닥스훈트", "닥스", "dachshund"], 11, 32, False),
    ("미니어처 슈나우저", ["슈나우저", "미니어처슈나우저", "미니슈나우저", "miniature schnauzer"], 11, 20, False),
    ("시바견", ["시바", "시바견", "시바이누", "shiba inu"], 17, 23, False),
    ("보더콜리", ["보더콜리", "보더 콜리", "border collie"], 30, 55, False),
    ("프렌치 불독", ["프렌치불독", "프렌치 불독", "프불", "french bulldog"], None, 28, True),
    ("카발리에 킹 찰스 스패니얼", ["카발리에", "킹찰스", "cavalier king charles spaniel"], 13, 18, False),
    ("퍼그", ["퍼그", "pug"], 14, 18, False),
    ("시베리안 허스키", ["허스키", "시베리안허스키", "siberian husky"], 35, 60, False),
    ("이탈리안 그레이하운드", ["이탈리안그레이하운드", "이탈리안 그레이하운드", "이탈리안", "italian greyhound"], 7, 14, False),
    ("미니어처 핀셔", ["미니핀", "미니어처핀셔", "미니어처 핀셔", "miniature pinscher"], 8, 10, False),
    ("파피용", ["파피용", "빠삐용", "papillon"], 5, 10, False),
    ("코커 스패니얼", ["코커스패니얼", "코카스파니엘", "코커", "cocker spaniel"], 20, 30, False),
    ("사모예드", ["사모예드", "samoyed"], 35, 65, False),
]

# 진돗개: AKC 차트에 수컷 40–50 lb, 암컷 30–40 lb
_JINDO = {"name": "진돗개", "aliases": ["진돗개", "진도개", "진도", "korean jindo"],
          "수컷": (40, 50), "암컷": (30, 40)}


def _norm(s: str) -> str:
    return s.lower().replace(" ", "")


def find_breed(breed: str, gender: Optional[str] = None) -> Optional[dict]:
    """품종 이름으로 표준 체중(kg)을 찾아요. 못 찾으면 None."""
    key = _norm(breed or "")
    if not key:
        return None
    if any(_norm(a) == key for a in _JINDO["aliases"]):
        lo, hi = _JINDO.get(gender or "", (30, 50))
        return {"name": _JINDO["name"] + (f" ({gender})" if gender in ("수컷", "암컷") else ""),
                "min_kg": round(lo * LB, 1), "max_kg": round(hi * LB, 1), "max_only": False,
                "note": None, "source": SOURCE, "source_url": SOURCE_URL}
    for name, aliases, lo, hi, max_only in _BREEDS:
        if any(_norm(a) == key for a in aliases):
            note = None
            if key in ("푸들", "poodle"):
                note = "푸들은 크기에 따라 토이·미니어처·스탠다드로 나뉘어요. 품종을 '미니어처 푸들'처럼 적으면 더 정확해요."
            return {"name": name, "min_kg": round(lo * LB, 1) if lo else None, "max_kg": round(hi * LB, 1),
                    "max_only": max_only, "note": note, "source": SOURCE, "source_url": SOURCE_URL}
    return None


def compare(weight_kg: Optional[float], std: Optional[dict]) -> Optional[str]:
    """below / within / above (표준 범위 기준). 계산할 수 없으면 None."""
    if weight_kg is None or std is None:
        return None
    if std["min_kg"] is not None and weight_kg < std["min_kg"]:
        return "below"
    if weight_kg > std["max_kg"]:
        return "above"
    return "within"
