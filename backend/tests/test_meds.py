"""투약 스케줄 API 테스트."""
from datetime import date, datetime, timedelta

from test_api import client, make_pet  # noqa: F401


def add_med(client, pid, **kw):
    body = {"name": "관절 영양제", "dose": "1정", "times": ["21:00", "09:00"], **kw}
    r = client.post(f"/api/pets/{pid}/medications", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_medication_crud(client):
    pid = make_pet(client)["id"]
    med = add_med(client, pid)
    assert med["times"] == ["09:00", "21:00"]  # 정렬돼서 저장
    assert med["active"] is True and med["start_date"] == date.today().isoformat()

    r = client.patch(f"/api/medications/{med['id']}", json={"times": ["08:30"], "instructions": "식후"})
    assert r.json()["times"] == ["08:30"] and r.json()["instructions"] == "식후"

    assert len(client.get(f"/api/pets/{pid}/medications").json()) == 1
    assert client.delete(f"/api/medications/{med['id']}").status_code == 204
    assert client.get(f"/api/pets/{pid}/medications").json() == []


def test_medication_validation(client):
    pid = make_pet(client)["id"]
    base = f"/api/pets/{pid}/medications"
    assert client.post(base, json={"name": "약", "times": []}).status_code == 422
    assert client.post(base, json={"name": "약", "times": ["25:00"]}).status_code == 422
    assert client.post(base, json={"name": "약", "times": ["9:00"]}).status_code == 422
    assert client.post(base, json={"name": "약", "times": ["09:00"],
                                   "start_date": "2026-09-10", "end_date": "2026-09-01"}).status_code == 422


def test_schedule_check_and_uncheck(client):
    pid = make_pet(client)["id"]
    med = add_med(client, pid, times=["00:00", "23:59"])
    sched = client.get(f"/api/pets/{pid}/med-schedule").json()
    assert [s["time"] for s in sched["slots"]] == ["00:00", "23:59"]
    assert all(s["record_id"] is None for s in sched["slots"])

    r = client.post(f"/api/pets/{pid}/med-schedule/check", json={"medication_id": med["id"], "time": "00:00"})
    assert r.status_code == 200, r.text
    first = r.json()["slots"][0]
    assert first["status"] == "taken" and first["record_id"]

    # 두 번 눌러도 기록은 하나
    client.post(f"/api/pets/{pid}/med-schedule/check", json={"medication_id": med["id"], "time": "00:00"})
    today = date.today().isoformat()
    meds_today = client.get(f"/api/pets/{pid}/records", params={"on": today, "type": "med"}).json()
    assert len(meds_today) == 1 and meds_today[0]["med_name"] == "관절 영양제"

    # 체크 해제 = 기록 삭제
    client.delete(f"/api/records/{first['record_id']}")
    assert client.get(f"/api/pets/{pid}/med-schedule").json()["slots"][0]["record_id"] is None

    # 스케줄에 없는 시간은 거절
    bad = client.post(f"/api/pets/{pid}/med-schedule/check", json={"medication_id": med["id"], "time": "12:00"})
    assert bad.status_code == 422


def test_home_record_matches_slot_and_duplicate_alert(client):
    pid = make_pet(client)["id"]
    add_med(client, pid, name="심장약", times=["09:00"])
    yesterday = date.today() - timedelta(days=1)
    for minute in (5, 40):  # 홈에서 두 번 기록
        at = datetime.combine(yesterday, datetime.min.time()).replace(hour=9, minute=minute)
        client.post(f"/api/pets/{pid}/records", json={"type": "med", "med_name": "심장약", "recorded_at": at.isoformat()})
    # 약 등록 시작일(오늘) 이전 날짜는 스케줄이 없음 → 시작일을 어제로
    med = client.get(f"/api/pets/{pid}/medications").json()[0]
    client.patch(f"/api/medications/{med['id']}", json={"start_date": yesterday.isoformat()})

    s = client.get(f"/api/pets/{pid}/med-schedule", params={"on": yesterday.isoformat()}).json()
    assert s["slots"][0]["status"] == "taken"
    assert [a["code"] for a in s["alerts"]] == ["duplicate"]


def test_missed_and_inactive(client):
    pid = make_pet(client)["id"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    add_med(client, pid, name="어제약", times=["09:00"], start_date=yesterday)
    add_med(client, pid, name="중지약", times=["09:00"], start_date=yesterday, active=False)
    s = client.get(f"/api/pets/{pid}/med-schedule", params={"on": yesterday}).json()
    assert [x["name"] for x in s["slots"]] == ["어제약"]
    assert s["slots"][0]["status"] == "missed"
    assert s["alerts"][0]["code"] == "missed"
