"""API 테스트. 실행: (backend 폴더에서)  pytest -q"""
import os
import tempfile

# 테스트용 임시 DB (실제 sevencare.db 는 건드리지 않아요) — app import 전에 설정
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SEVENCARE_DB_URL"] = f"sqlite:///{_tmp.name}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:  # lifespan 실행 → 테이블 생성
        yield c


def make_pet(client, **kw):
    body = {"name": "초코", "breed": "골든리트리버", "age_years": 14, "weight_kg": 24.1, **kw}
    r = client.post("/api/pets", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_pet_register_and_get(client):
    pet = make_pet(client)
    assert pet["id"] > 0
    assert pet["gender"] == "수컷"
    assert pet["latest_weight_kg"] == 24.1

    r = client.get(f"/api/pets/{pet['id']}")
    assert r.status_code == 200 and r.json()["name"] == "초코"

    assert any(p["id"] == pet["id"] for p in client.get("/api/pets").json())


def test_pet_validation(client):
    assert client.post("/api/pets", json={"name": "", "breed": "말티즈"}).status_code == 422
    assert client.post("/api/pets", json={"name": "보리"}).status_code == 422
    assert client.get("/api/pets/99999").status_code == 404


def test_pet_update_and_delete(client):
    pet = make_pet(client)
    r = client.patch(f"/api/pets/{pet['id']}", json={"hospital": "노원동물병원"})
    assert r.json()["hospital"] == "노원동물병원"
    assert r.json()["name"] == "초코"  # 안 보낸 필드는 그대로

    client.post(f"/api/pets/{pet['id']}/records", json={"type": "med", "med_name": "진통제"})
    assert client.delete(f"/api/pets/{pet['id']}").status_code == 204
    assert client.get(f"/api/pets/{pet['id']}").status_code == 404


def test_record_crud(client):
    pet = make_pet(client)
    base = f"/api/pets/{pet['id']}/records"

    # Create
    r = client.post(base, json={"type": "meal", "meal_amount": 80, "recorded_at": "2026-09-24T08:00:00"})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["type"] == "meal" and rec["meal_amount"] == 80

    client.post(base, json={
        "type": "poop", "poop_firmness": "정상", "poop_color": "갈색", "poop_blood": False,
        "recorded_at": "2026-09-24T09:30:00",
    })
    client.post(base, json={"type": "med", "med_name": "관절 영양제", "recorded_at": "2026-09-23T09:00:00"})

    # Read (날짜 필터 + 최신순)
    today = client.get(base, params={"on": "2026-09-24"}).json()
    assert [x["type"] for x in today] == ["poop", "meal"]
    assert len(client.get(base).json()) == 3
    assert len(client.get(base, params={"type": "med"}).json()) == 1

    # Update
    r = client.patch(f"/api/records/{rec['id']}", json={"meal_amount": 50, "note": "오래 씹지 못함"})
    assert r.json()["meal_amount"] == 50 and r.json()["note"] == "오래 씹지 못함"
    assert client.patch(f"/api/records/{rec['id']}", json={"meal_amount": None}).status_code == 422

    # Delete
    assert client.delete(f"/api/records/{rec['id']}").status_code == 204
    assert client.get(f"/api/records/{rec['id']}").status_code == 404


def test_record_validation(client):
    pet = make_pet(client)
    base = f"/api/pets/{pet['id']}/records"
    assert client.post(base, json={"type": "weight"}).status_code == 422  # weight_kg 없음
    assert client.post(base, json={"type": "meal", "meal_amount": 150}).status_code == 422
    assert client.post(base, json={"type": "bath"}).status_code == 422
    assert client.post("/api/pets/99999/records", json={"type": "med", "med_name": "x"}).status_code == 404


def test_latest_weight_follows_records(client):
    pet = make_pet(client, weight_kg=24.1)
    base = f"/api/pets/{pet['id']}/records"
    client.post(base, json={"type": "weight", "weight_kg": 23.8, "recorded_at": "2026-09-20T09:00:00"})
    client.post(base, json={"type": "weight", "weight_kg": 23.5, "recorded_at": "2026-09-24T09:00:00"})
    assert client.get(f"/api/pets/{pet['id']}").json()["latest_weight_kg"] == 23.5
