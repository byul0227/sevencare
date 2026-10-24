"""AI건강 탭 API 테스트 (실제 AI 호출은 하지 않아요)."""
from test_api import client, make_pet  # noqa: F401


def test_body_check_with_breed_and_bcs(client):
    pid = make_pet(client, breed="말티즈", weight_kg=4.0)["id"]
    r = client.get(f"/api/pets/{pid}/body-check").json()
    assert r["breed_standard"]["name"] == "말티즈" and r["breed_standard"]["max_only"] is True
    assert r["position"] == "above" and r["bcs_latest"] is None

    client.post(f"/api/pets/{pid}/care-checks", json={"kind": "bcs", "answers": {"bcs": 7}})
    r = client.get(f"/api/pets/{pid}/body-check").json()
    assert r["bcs_latest"]["score"] == 7 and r["bcs_latest"]["band"]["code"] == "over"


def test_body_check_unknown_breed(client):
    pid = make_pet(client, breed="믹스견")["id"]
    r = client.get(f"/api/pets/{pid}/body-check").json()
    assert r["breed_standard"] is None and r["position"] is None


def test_health_info_has_sources(client):
    items = client.get("/api/health-info").json()
    assert len(items) >= 4
    assert all(i["sources"] and i["sources"][0]["url"].startswith("https://") for i in items)


def test_ai_chat_without_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    pid = make_pet(client)["id"]
    assert client.get("/api/ai/status").json()["available"] is False
    r = client.post(f"/api/pets/{pid}/ai-chat", json={"messages": [{"role": "user", "content": "밥을 잘 안 먹어요"}]})
    assert r.status_code == 503


def test_ai_context_builds(client):
    """AI에게 보낼 기록 요약이 에러 없이 만들어지는지 (키 없이 확인)."""
    from app.database import SessionLocal
    from app.models import Pet
    from app.routers.ai import build_context

    pid = make_pet(client, name="초코")["id"]
    client.post(f"/api/pets/{pid}/records", json={"type": "meal", "meal_amount": 50})
    client.post(f"/api/pets/{pid}/medications", json={"name": "심장약", "times": ["19:00"]})
    client.post(f"/api/pets/{pid}/vet-visits", json={"visit_date": "2026-08-02", "title": "심장 초음파"})
    with SessionLocal() as db:
        text = build_context(db, db.get(Pet, pid))
    assert "초코" in text and "식사 50%" in text and "심장약" in text and "심장 초음파" in text


def test_gemini_request_and_reply_format():
    """대화 형식 변환 · 답변 추출 (생각 과정 part 는 빼요)."""
    from app.ai_provider import parse_gemini_reply, to_gemini_body

    body = to_gemini_body("SYS", [{"role": "user", "content": "안녕"}, {"role": "assistant", "content": "네"},
                                  {"role": "user", "content": "밥을 안 먹어요"}])
    assert body["systemInstruction"]["parts"][0]["text"] == "SYS"
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]
    data = {"candidates": [{"content": {"parts": [{"text": "생각 중", "thought": True}, {"text": "병원에 연락해 보세요."}]}}]}
    assert parse_gemini_reply(data) == "병원에 연락해 보세요."
    assert parse_gemini_reply({}) == ""


def test_ai_chat_with_gemini_mocked(client, monkeypatch):
    """실제 호출 없이: 키가 있으면 Gemini로 보내고, 첫 모델이 한도 초과면 다음 모델로 넘어가요."""
    import io
    import urllib.error

    from app import ai_provider

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("SEVENCARE_AI_MODEL", raising=False)
    calls = []

    def fake_post(url, body, headers, timeout=40):
        calls.append(url)
        assert headers["x-goog-api-key"] == "test-key" and "[반려견 기록]" in body["systemInstruction"]["parts"][0]["text"]
        if len(calls) == 1:
            raise urllib.error.HTTPError(url, 429, "quota", {}, io.BytesIO(b"{}"))
        return {"candidates": [{"content": {"parts": [{"text": "기록을 보면 식사량이 줄었어요."}]}}]}

    monkeypatch.setattr(ai_provider, "_post_json", fake_post)
    pid = make_pet(client)["id"]
    st = client.get("/api/ai/status").json()
    assert st["available"] is True and st["provider"] == "gemini"
    r = client.post(f"/api/pets/{pid}/ai-chat", json={"messages": [{"role": "user", "content": "밥을 잘 안 먹어요"}]})
    assert r.status_code == 200 and "식사량" in r.json()["reply"]
    assert len(calls) == 2 and r.json()["model"] == ai_provider.GEMINI_MODELS[1]
