"""리포트 API 테스트. test_api.py 와 같은 임시 DB 를 써요."""
from datetime import date, datetime, time, timedelta

from test_api import client, make_pet  # noqa: F401  (fixture 재사용)


def at(days_ago: int, h: int = 9) -> str:
    return datetime.combine(date.today() - timedelta(days=days_ago), time(h, 0)).isoformat()


def post(client, pet_id, **body):
    r = client.post(f"/api/pets/{pet_id}/records", json=body)
    assert r.status_code == 201, r.text


def test_empty_report(client):
    pet = make_pet(client)
    r = client.get(f"/api/pets/{pet['id']}/report")
    assert r.status_code == 200, r.text
    rep = r.json()
    assert [p["label"] for p in rep["weight_series"]] == ["4주 전", "3주 전", "2주 전", "1주 전", "이번주"]
    assert all(p["weight_kg"] is None for p in rep["weight_series"])
    assert rep["meal_avg_pct"] is None and rep["poop_normal_pct"] is None
    assert rep["alerts"] == []


def test_report_stats_and_alerts(client):
    pet = make_pet(client, weight_kg=10.0)
    pid = pet["id"]
    # 체중: 4주 전 10.0 → 이번주 9.4 (6% 감소)
    post(client, pid, type="weight", weight_kg=10.0, recorded_at=at(30))
    post(client, pid, type="weight", weight_kg=9.8, recorded_at=at(14))
    post(client, pid, type="weight", weight_kg=9.4, recorded_at=at(1))
    # 식사: 평소 100% 6회, 최근 3일 50% 2회
    for d in range(4, 10):
        post(client, pid, type="meal", meal_amount=100, recorded_at=at(d))
    post(client, pid, type="meal", meal_amount=50, recorded_at=at(1))
    post(client, pid, type="meal", meal_amount=50, recorded_at=at(0, 8))
    # 배변: 정상 3, 무름 1(혈변)
    for d in (5, 6, 7):
        post(client, pid, type="poop", poop_firmness="정상", recorded_at=at(d))
    post(client, pid, type="poop", poop_firmness="무름", poop_blood=True, recorded_at=at(2))

    rep = client.get(f"/api/pets/{pid}/report").json()
    series = {p["label"]: p["weight_kg"] for p in rep["weight_series"]}
    assert series["4주 전"] == 10.0 and series["2주 전"] == 9.8 and series["이번주"] == 9.4
    assert series["3주 전"] is None
    assert rep["weight_change_pct"] == -6.0
    assert rep["meal_avg_pct"] == round((600 + 100) / 8)
    assert rep["poop_normal_pct"] == 75
    codes = {a["code"] for a in rep["alerts"]}
    assert codes == {"meal_drop", "weight_drop", "poop_blood"}
    meal_msg = next(a["message"] for a in rep["alerts"] if a["code"] == "meal_drop")
    assert "50%" in meal_msg


def test_demo_history_roundtrip(client):
    pet = make_pet(client, weight_kg=24.1)
    pid = pet["id"]
    post(client, pid, type="med", med_name="진통제", recorded_at=at(0))  # 직접 입력한 오늘 기록

    r = client.post(f"/api/pets/{pid}/demo-history")
    assert r.status_code == 200 and r.json()["created"] > 50
    again = client.post(f"/api/pets/{pid}/demo-history").json()
    assert again["deleted"] == r.json()["created"]  # 다시 만들면 이전 데모는 교체

    rep = client.get(f"/api/pets/{pid}/report").json()
    assert sum(p["weight_kg"] is not None for p in rep["weight_series"]) >= 4
    assert "meal_drop" in {a["code"] for a in rep["alerts"]}

    assert client.delete(f"/api/pets/{pid}/demo-history").json()["deleted"] == again["created"]
    left = client.get(f"/api/pets/{pid}/records").json()
    assert [x["med_name"] for x in left] == ["진통제"]  # 직접 입력한 기록은 그대로


def test_alerts_have_sources(client):
    pet = make_pet(client, weight_kg=10.0)
    pid = pet["id"]
    post(client, pid, type="poop", poop_firmness="정상", poop_color="검붉은색", recorded_at=at(1))
    alerts = client.get(f"/api/pets/{pid}/report").json()["alerts"]
    assert [a["code"] for a in alerts] == ["poop_blood"]
    assert "검붉은 변 1번" in alerts[0]["message"]
    assert alerts[0]["source"] and alerts[0]["source_url"].startswith("https://")


def test_weight_drop_levels(client):
    pid = make_pet(client)["id"]
    post(client, pid, type="weight", weight_kg=10.0, recorded_at=at(20))
    post(client, pid, type="weight", weight_kg=8.9, recorded_at=at(1))  # -11%
    w = next(a for a in client.get(f"/api/pets/{pid}/report").json()["alerts"] if a["code"] == "weight_drop")
    assert w["level"] == "critical"


def test_food_refusal_replaces_meal_drop(client):
    pid = make_pet(client)["id"]
    for d in range(4, 10):
        post(client, pid, type="meal", meal_amount=100, recorded_at=at(d))
    post(client, pid, type="meal", meal_amount=10, recorded_at=at(1))
    post(client, pid, type="meal", meal_amount=10, recorded_at=at(0, 8))
    codes = [a["code"] for a in client.get(f"/api/pets/{pid}/report").json()["alerts"]]
    assert codes == ["food_refusal"]


def test_loose_stool_three_days(client):
    pid = make_pet(client)["id"]
    for d in (1, 2):
        post(client, pid, type="poop", poop_firmness="무름", recorded_at=at(d))
    assert client.get(f"/api/pets/{pid}/report").json()["alerts"] == []  # 2일은 아직
    post(client, pid, type="poop", poop_firmness="무름", recorded_at=at(3))
    codes = [a["code"] for a in client.get(f"/api/pets/{pid}/report").json()["alerts"]]
    assert codes == ["loose_stool"]
