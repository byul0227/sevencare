"""병원 지참용 리포트 API 테스트."""
from datetime import date, datetime, timedelta

from test_api import client, make_pet  # noqa: F401


def test_vet_summary_empty(client):
    pid = make_pet(client)["id"]
    r = client.get(f"/api/pets/{pid}/vet-summary")
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["pet"]["id"] == pid and s["medications"] == [] and s["visits"] == []
    assert s["care"] == {"cognitive": None, "qol": None, "bcs": None, "mobility": None}
    assert s["notable_records"] == [] and len(s["report"]["weight_series"]) == 5


def test_vet_summary_contents(client):
    pid = make_pet(client, name="초코")["id"]
    start = (date.today() - timedelta(days=13)).isoformat()
    client.post(f"/api/pets/{pid}/medications", json={"name": "심장약", "times": ["00:00"], "start_date": start})
    # 14일 중 어제·그제만 복용 기록
    for back in (1, 2):
        at = datetime.combine(date.today() - timedelta(days=back), datetime.min.time())
        client.post(f"/api/pets/{pid}/records", json={"type": "med", "med_name": "심장약", "recorded_at": at.isoformat()})
    client.post(f"/api/pets/{pid}/records", json={"type": "poop", "poop_firmness": "무름", "poop_blood": True})
    client.post(f"/api/pets/{pid}/records", json={"type": "meal", "meal_amount": 100, "note": "간식을 잔뜩 먹음"})
    client.post(f"/api/pets/{pid}/records", json={"type": "meal", "meal_amount": 80})  # 특이 기록 아님
    client.post(f"/api/pets/{pid}/care-checks", json={"kind": "bcs", "answers": {"bcs": 6}})
    client.post(f"/api/pets/{pid}/vet-visits", json={"visit_date": "2026-08-02", "title": "심장 초음파",
                                                     "next_visit_date": (date.today() + timedelta(days=30)).isoformat()})

    s = client.get(f"/api/pets/{pid}/vet-summary").json()
    med = s["medications"][0]
    # 오늘 00:00 슬롯은 새벽 1시 전이면 아직 '지금 복용'이라 빠질 수 있어요 → 13 또는 14칸
    assert med["name"] == "심장약" and med["taken"] == 2 and med["total"] in (13, 14)
    assert med["adherence_pct"] == round(2 / med["total"] * 100)
    reasons = [(n["reason"], n["note"]) for n in s["notable_records"]]
    assert ("혈변·점액", None) in reasons and (None, "간식을 잔뜩 먹음") in reasons and len(reasons) == 2
    assert s["care"]["bcs"]["score"] == 6
    assert s["visits"][0]["title"] == "심장 초음파" and s["next_visit"]["title"] == "심장 초음파"
    assert any(a["code"] == "poop_blood" for a in s["report"]["alerts"])
