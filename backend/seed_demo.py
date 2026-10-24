"""시연용 데모 데이터 넣기

백엔드 서버를 켠 상태에서 다른 터미널에서 실행하세요.
    cd backend
    .venv\\Scripts\\python seed_demo.py

- '세븐'이라는 펫이 이미 있으면 그 펫에 채우고, 없으면 새로 등록해요.
- 여러 번 실행해도 약 · 병원 기록 · 케어 체크가 중복으로 쌓이지 않아요.
- 지난 5주 기록은 '[데모] 자동 생성 기록'으로 들어가서, 리포트 화면의
  '데모 기록 지우기'로 언제든 지울 수 있어요.
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import date

BASE = "http://localhost:8000/api"
PET = {
    "name": "세븐", "breed": "토이 푸들", "age_years": 18, "gender": "수컷", "neutered": True,
    "weight_kg": 2.4, "condition": "슬개골 탈구 2기, 신장 수치 경계", "hospital": "노원동물병원",
}


def call(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        with urllib.request.urlopen(req) as res:
            raw = res.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"요청 실패 {method} {path}: {e.code} {e.read().decode(errors='ignore')}")
    except urllib.error.URLError:
        raise SystemExit("서버에 연결할 수 없어요. 먼저 백엔드(uvicorn)를 켜 주세요.")


def seed(call):
    """call(method, path, body) 로 API를 불러 데모 데이터를 채워요 (HTTP · 서버 내부 둘 다 사용)."""
    today = date.today().isoformat()

    # 1) 펫
    pets = call("GET", "/pets")
    pet = next((p for p in pets if p["name"] == PET["name"]), None)
    if pet is None:
        pet = call("POST", "/pets", PET)
        print(f"펫 등록: {pet['name']} (id {pet['id']})")
    else:
        print(f"기존 펫 사용: {pet['name']} (id {pet['id']})")
        if "신장" not in (pet.get("condition") or ""):
            # 사료 분석에서 신장 관리 평가가 보이도록 (6월 혈액검사 '신장 수치 경계'와 맞춤)
            pet = call("PATCH", f"/pets/{pet['id']}", {"condition": PET["condition"]})
    pid = pet["id"]

    # 2) 지난 5주 기록 (식사 · 배변 · 체중) — 최근 식사량 감소 · 체중 감소 알림이 뜨도록
    demo = call("POST", f"/pets/{pid}/demo-history")
    print(f"지난 5주 데모 기록: {demo['created']}개")

    # 3) 약
    meds = call("GET", f"/pets/{pid}/medications")
    if not meds:
        call("POST", f"/pets/{pid}/medications", {
            "name": "관절 영양제", "dose": "1정", "times": ["09:00", "21:00"], "instructions": "식후"})
        call("POST", f"/pets/{pid}/medications", {
            "name": "심장약", "dose": "0.5정", "times": ["08:00"], "instructions": "진통제와 2시간 간격"})
        print("약 2개 등록")

    # 4) 케어 체크 (인지기능 · 삶의 질 · 거동 · 비만도)
    summary = call("GET", f"/pets/{pid}/care-summary")
    if not summary.get("cognitive"):
        checks = [
            ("cognitive", {"c1": 4, "c2": 3, "c3": 2, "c4": 2, "c5": 2, "c6": 1, "c7": 2,
                           "c8": 4, "c9": 4, "c10": 3, "c11": 3, "c12": 3, "c13": 4}),
            ("qol", {"q1": 6, "q2": 5, "q3": 7, "q4": 7, "q5": 7, "q6": 4, "q7": 6}),
            ("mobility", {"m1": 1, "m2": 1, "m3": 0, "m4": 0}),
            ("bcs", {"bcs": 4}),
        ]
        for kind, answers in checks:
            call("POST", f"/pets/{pid}/care-checks", {"kind": kind, "answers": answers})
        print("케어 체크 4종 저장")

    # 5) 병원 방문 기록
    visits = call("GET", f"/pets/{pid}/vet-visits")
    if not visits["visits"]:
        for v in [
            {"visit_date": "2026-03-10", "category": "정기검진", "title": "예방접종 · 건강검진",
             "hospital": "노원동물병원", "diagnosis": "전반적으로 양호"},
            {"visit_date": "2026-06-15", "category": "검사", "title": "정기 혈액검사",
             "hospital": "노원동물병원", "diagnosis": "신장 수치 경계", "treatment": "저염식 권장"},
            {"visit_date": "2026-08-02", "category": "진료", "title": "슬개골 탈구 2기 진단",
             "hospital": "노원동물병원", "treatment": "관절 영양제 처방", "next_visit_date": "2026-10-20"},
        ]:
            call("POST", f"/pets/{pid}/vet-visits", v)
        print("병원 방문 기록 3건")

    # 6) 오늘 기록 (홈 화면용) — 오늘 기록이 없을 때만
    records = call("GET", f"/pets/{pid}/records?on={today}")
    if not records:
        call("POST", f"/pets/{pid}/records", {"type": "meal", "meal_amount": 50, "recorded_at": f"{today}T08:10:00"})
        call("POST", f"/pets/{pid}/records", {"type": "poop", "poop_firmness": "정상", "poop_color": "갈색",
                                              "poop_blood": False, "recorded_at": f"{today}T09:30:00"})
        med = next(m for m in call("GET", f"/pets/{pid}/medications") if m["name"] == "관절 영양제")
        call("POST", f"/pets/{pid}/med-schedule/check", {"medication_id": med["id"], "time": "09:00"})
        print("오늘 기록 3건 (식사 · 배변 · 관절 영양제)")



def main():
    seed(call)
    print("\n완료! 크롬에서 새로고침(F5) 해 주세요.")


if __name__ == "__main__":
    sys.exit(main())
