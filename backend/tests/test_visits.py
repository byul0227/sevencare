"""병원 방문 기록 API 테스트."""
from datetime import date, timedelta

from test_api import client, make_pet  # noqa: F401


def test_visit_crud_and_order(client):
    pid = make_pet(client, hospital="노원동물병원")["id"]
    base = f"/api/pets/{pid}/vet-visits"

    r = client.post(base, json={"visit_date": "2026-06-15", "category": "검사", "title": "정기 혈액검사",
                                "diagnosis": "신장 수치 경계", "treatment": "저염식 권장"})
    assert r.status_code == 201, r.text
    assert r.json()["hospital"] == "노원동물병원"  # 비우면 담당 병원
    first = r.json()
    client.post(base, json={"visit_date": "2026-08-02", "title": "슬개골 탈구 2기 진단", "hospital": "24시 병원"})

    data = client.get(base).json()
    assert [v["title"] for v in data["visits"]] == ["슬개골 탈구 2기 진단", "정기 혈액검사"]
    assert data["visits"][0]["category"] == "진료" and data["visits"][0]["hospital"] == "24시 병원"

    r = client.patch(f"/api/vet-visits/{first['id']}", json={"note": "3개월 뒤 재검"})
    assert r.json()["note"] == "3개월 뒤 재검" and r.json()["title"] == "정기 혈액검사"

    assert client.delete(f"/api/vet-visits/{first['id']}").status_code == 204
    assert client.get(f"/api/vet-visits/{first['id']}").status_code == 404


def test_visit_validation(client):
    pid = make_pet(client)["id"]
    base = f"/api/pets/{pid}/vet-visits"
    assert client.post(base, json={"visit_date": "2026-09-01", "title": ""}).status_code == 422
    assert client.post(base, json={"visit_date": "2026-09-01", "title": "x", "category": "미용"}).status_code == 422
    assert client.post(base, json={"visit_date": "2026-09-10", "title": "x",
                                   "next_visit_date": "2026-09-01"}).status_code == 422


def test_next_visit(client):
    pid = make_pet(client)["id"]
    base = f"/api/pets/{pid}/vet-visits"
    today = date.today()
    assert client.get(base).json()["next_visit"] is None
    client.post(base, json={"visit_date": (today - timedelta(days=90)).isoformat(), "title": "옛날",
                            "next_visit_date": (today - timedelta(days=1)).isoformat()})  # 이미 지남
    client.post(base, json={"visit_date": (today - timedelta(days=10)).isoformat(), "title": "재검 필요",
                            "next_visit_date": (today + timedelta(days=20)).isoformat()})
    client.post(base, json={"visit_date": (today - timedelta(days=3)).isoformat(), "title": "예방접종",
                            "category": "예방접종", "next_visit_date": (today + timedelta(days=5)).isoformat()})
    nxt = client.get(base).json()["next_visit"]
    assert nxt["title"] == "예방접종"
