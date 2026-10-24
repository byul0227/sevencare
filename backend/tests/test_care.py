"""케어 체크 API 테스트."""
from test_api import client, make_pet  # noqa: F401

CCDR_IDS = [f"c{i}" for i in range(1, 14)]


def test_scales_endpoint(client):
    scales = client.get("/api/care-scales").json()
    assert set(scales) == {"mobility", "cognitive", "qol", "bcs"}
    assert len(scales["cognitive"]["questions"]) == 13
    assert len(scales["qol"]["questions"]) == 7
    assert scales["cognitive"]["source_url"].startswith("https://")


def test_cognitive_scoring_and_bands(client):
    pid = make_pet(client)["id"]
    base = f"/api/pets/{pid}/care-checks"

    r = client.post(base, json={"kind": "cognitive", "answers": {k: 1 for k in CCDR_IDS}})
    assert r.status_code == 201, r.text
    assert r.json()["score"] == 16 and r.json()["band"]["code"] == "normal"

    answers = {k: 1 for k in CCDR_IDS} | {"c1": 4, "c2": 4, "c4": 3, "c8": 4, "c9": 4, "c11": 4, "c12": 4}
    r = client.post(base, json={"kind": "cognitive", "answers": answers})
    assert r.json()["score"] == 45 and r.json()["band"]["code"] == "risk"

    r = client.post(base, json={"kind": "cognitive", "answers": {k: 5 for k in CCDR_IDS}})
    assert r.json()["score"] == 80 and r.json()["band"]["level"] == "alert"


def test_qol_and_mobility(client):
    pid = make_pet(client)["id"]
    base = f"/api/pets/{pid}/care-checks"
    low = client.post(base, json={"kind": "qol", "answers": {f"q{i}": 5 for i in range(1, 8)}}).json()
    assert low["score"] == 35 and low["band"]["code"] == "low"
    ok = client.post(base, json={"kind": "qol", "answers": {f"q{i}": 6 for i in range(1, 8)}}).json()
    assert ok["score"] == 42 and ok["band"]["code"] == "acceptable"

    mob = client.post(base, json={"kind": "mobility", "answers": {"m1": 0, "m2": 1, "m3": 0, "m4": 2}}).json()
    assert mob["score"] == 3 and mob["band"] is None and mob["max_score"] == 8


def test_validation(client):
    pid = make_pet(client)["id"]
    base = f"/api/pets/{pid}/care-checks"
    assert client.post(base, json={"kind": "mobility", "answers": {"m1": 0}}).status_code == 422
    assert client.post(base, json={"kind": "qol", "answers": {f"q{i}": 11 for i in range(1, 8)}}).status_code == 422
    assert client.post(base, json={"kind": "sleep", "answers": {}}).status_code == 422
    assert client.post("/api/pets/99999/care-checks",
                       json={"kind": "mobility", "answers": {"m1": 0, "m2": 0, "m3": 0, "m4": 0}}).status_code == 404


def test_summary_list_delete_and_cascade(client):
    pid = make_pet(client)["id"]
    base = f"/api/pets/{pid}/care-checks"
    s = client.get(f"/api/pets/{pid}/care-summary").json()
    assert s == {"mobility": None, "mobility_today": False, "cognitive": None, "qol": None}

    client.post(base, json={"kind": "mobility", "answers": {"m1": 1, "m2": 1, "m3": 1, "m4": 1},
                            "checked_at": "2020-01-01T09:00:00"})
    newest = client.post(base, json={"kind": "mobility", "answers": {"m1": 0, "m2": 0, "m3": 0, "m4": 0}}).json()
    s = client.get(f"/api/pets/{pid}/care-summary").json()
    assert s["mobility"]["id"] == newest["id"] and s["mobility_today"] is True

    assert len(client.get(base, params={"kind": "mobility"}).json()) == 2
    assert client.delete(f"/api/care-checks/{newest['id']}").status_code == 204
    assert client.get(f"/api/pets/{pid}/care-summary").json()["mobility_today"] is False

    assert client.delete(f"/api/pets/{pid}").status_code == 204  # 펫 삭제 시 체크 기록도 함께 삭제
