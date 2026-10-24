"""프로필 사진 + 놀이 탭 API 테스트."""
import base64

from test_api import client, make_pet  # noqa: F401

# 1x1 PNG
PNG = base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)).decode()


def test_photo_upload_get_delete(client):
    pid = make_pet(client)["id"]
    assert client.get(f"/api/pets/{pid}/photo").status_code == 404
    assert client.get(f"/api/pets/{pid}").json()["photo_version"] is None

    r = client.put(f"/api/pets/{pid}/photo", json={"data_url": f"data:image/png;base64,{PNG}", "color": "#C98A4B"})
    assert r.status_code == 200, r.text
    assert r.json()["photo_version"] and r.json()["photo_color"] == "#C98A4B"

    img = client.get(f"/api/pets/{pid}/photo")
    assert img.status_code == 200 and img.headers["content-type"] == "image/png" and img.content.startswith(b"\x89PNG")
    listed = next(p for p in client.get("/api/pets").json() if p["id"] == pid)
    assert listed["photo_version"] == r.json()["photo_version"]  # 목록에도 버전이 실려요

    assert client.delete(f"/api/pets/{pid}/photo").status_code == 204
    assert client.get(f"/api/pets/{pid}").json()["photo_version"] is None


def test_photo_validation(client):
    pid = make_pet(client)["id"]
    url = f"/api/pets/{pid}/photo"
    assert client.put(url, json={"data_url": "data:image/gif;base64,R0lGOD"}).status_code == 422
    assert client.put(url, json={"data_url": "data:image/png;base64,@@@"}).status_code == 422
    assert client.put(url, json={"data_url": f"data:image/png;base64,{PNG}", "color": "red"}).status_code == 422


def test_play_actions_and_treats(client):
    pid = make_pet(client)["id"]
    s = client.get(f"/api/pets/{pid}/play").json()
    assert s["happiness"] == 70 and s["treats_available"] == 0

    # 간식이 없으면 못 줘요
    assert client.post(f"/api/pets/{pid}/play/treat").status_code == 409

    # 진짜 기록 2종류 + 케어 체크 1번 → 간식 3개
    client.post(f"/api/pets/{pid}/records", json={"type": "meal", "meal_amount": 80})
    client.post(f"/api/pets/{pid}/records", json={"type": "meal", "meal_amount": 100})  # 같은 종류는 1개로
    client.post(f"/api/pets/{pid}/records", json={"type": "weight", "weight_kg": 5.0})
    client.post(f"/api/pets/{pid}/care-checks", json={"kind": "bcs", "answers": {"bcs": 5}})
    s = client.get(f"/api/pets/{pid}/play").json()
    assert s["treats_available"] == 3 and s["treats_earned"] == 3

    s = client.post(f"/api/pets/{pid}/play/treat").json()
    assert s["treats_available"] == 2 and s["fullness"] >= 90

    s = client.post(f"/api/pets/{pid}/play/walk").json()
    assert s["walk_ready_at"] is not None and s["happiness"] >= 95
    assert client.post(f"/api/pets/{pid}/play/walk").status_code == 409  # 쿨다운

    assert client.post(f"/api/pets/{pid}/play/pet").status_code == 200
    assert client.post(f"/api/pets/{pid}/play/dance").status_code == 422


def test_demo_records_do_not_earn_treats(client):
    pid = make_pet(client)["id"]
    client.post(f"/api/pets/{pid}/records", json={"type": "meal", "meal_amount": 80, "note": "[데모] 자동 생성 기록"})
    assert client.get(f"/api/pets/{pid}/play").json()["treats_available"] == 0
