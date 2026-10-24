"""AI 상담에 쓰는 모델 호출부.

두 가지 중 키가 있는 쪽을 써요 (둘 다 있으면 Gemini 우선 — 무료라서).
- GEMINI_API_KEY    : Google AI Studio 무료 키 (https://aistudio.google.com/apikey)
- ANTHROPIC_API_KEY : Claude API 키 (유료)

Gemini는 추가 패키지 없이 REST(urllib)로 불러요.
무료 한도에 걸리거나 모델이 없으면 다음 후보 모델로 한 번 더 시도해요.
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request

GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]  # 무료 티어 Flash 계열
RETRY_WAITS = [0, 2, 4]  # 서버 혼잡(503)이면 같은 모델로 잠깐 쉬었다 다시 시도 (초)
CLAUDE_MODEL = "claude-sonnet-5"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class AIError(Exception):
    """사용자에게 그대로 보여줄 수 있는 한국어 메시지를 담아요."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


class AIBusy(AIError):
    """Gemini 서버 혼잡(503) — 잠깐 기다렸다 다시 시도할 만한 오류."""


def provider() -> str | None:
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "claude"
    return None


def model_candidates() -> list[str]:
    custom = os.getenv("SEVENCARE_AI_MODEL")
    if provider() == "gemini":
        return [custom] + [m for m in GEMINI_MODELS if m != custom] if custom else list(GEMINI_MODELS)
    return [custom or CLAUDE_MODEL]


def to_gemini_body(system: str, messages: list[dict]) -> dict:
    """[{role: user|assistant, content}] → Gemini generateContent 요청 형식."""
    return {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ],
        "generationConfig": {
            "maxOutputTokens": 2048, "temperature": 0.6,
            # 상담 답변은 길게 생각할 필요가 없어서 생각 단계를 줄여 응답을 빠르게 해요
            "thinkingConfig": {"thinkingLevel": "low"},
        },
    }


def parse_gemini_reply(data: dict) -> str:
    """응답에서 답변 텍스트만 꺼내요 (생각 과정 part 는 제외)."""
    for cand in data.get("candidates") or []:
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if text.strip():
            return text.strip()
    return ""


def _post_json(url: str, body: dict, headers: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _gemini(system: str, messages: list[dict]) -> tuple[str, str]:
    key = os.environ["GEMINI_API_KEY"]
    body = to_gemini_body(system, messages)
    last = AIError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.")
    attempts = [(m, w) for m in model_candidates() for w in RETRY_WAITS]
    for i, (model, wait) in enumerate(attempts):
        if wait:
            if not isinstance(last, AIBusy):
                continue  # 혼잡(503)일 때만 같은 모델 재시도
            time.sleep(wait)
        try:
            try:
                data = _post_json(GEMINI_URL.format(model=model), body, {"x-goog-api-key": key})
            except urllib.error.HTTPError as e:
                # 생각 단계 설정을 모르는 모델이면 그 설정만 빼고 한 번 더
                if e.code == 400 and "thinking" in e.read().decode("utf-8", "ignore").lower():
                    plain = {**body, "generationConfig": {k: v for k, v in body["generationConfig"].items() if k != "thinkingConfig"}}
                    data = _post_json(GEMINI_URL.format(model=model), plain, {"x-goog-api-key": key})
                else:
                    raise
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")
            if e.code in (401, 403) or (e.code == 400 and ("API_KEY" in detail or "API key" in detail)):
                raise AIError("Gemini API 키가 올바르지 않아요. backend/.env 의 GEMINI_API_KEY 를 확인해 주세요.", 503)
            if e.code == 429:
                last = AIError("무료 사용 한도에 잠시 걸렸어요. 1분쯤 뒤 다시 물어봐 주세요.", 429)
            elif e.code in (500, 503):
                last = AIBusy("지금 AI 서버(Gemini)가 붐벼요. 잠시 뒤 다시 물어봐 주세요.", 503)
            else:
                last = AIError(f"AI 응답을 받지 못했어요 (Gemini {e.code}).")
            continue  # 404(모델 없음) · 429 · 5xx → 다음 후보 모델
        except (TimeoutError, socket.timeout):
            last = AIError("AI 답변이 너무 오래 걸렸어요. 잠시 뒤 다시 물어봐 주세요.", 504)
            continue  # 더 가벼운 다음 모델로
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                last = AIError("AI 답변이 너무 오래 걸렸어요. 잠시 뒤 다시 물어봐 주세요.", 504)
                continue
            raise AIError(f"AI 서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요. ({type(e.reason).__name__})")
        reply = parse_gemini_reply(data)
        if reply:
            return reply, model
        last = AIError("답변을 만들지 못했어요. 질문을 조금 바꿔서 다시 물어봐 주세요.")
    raise last


def _claude(system: str, messages: list[dict]) -> tuple[str, str]:
    try:
        import anthropic  # Claude 키를 쓸 때만 필요
    except ImportError:
        raise AIError("anthropic 패키지가 설치되지 않았어요. pip install anthropic 을 실행해 주세요.", 503)
    model = model_candidates()[0]
    try:
        resp = anthropic.Anthropic().messages.create(model=model, max_tokens=800, system=system, messages=messages)
    except Exception as e:  # 네트워크·키 오류 등
        raise AIError(f"AI 응답을 받지 못했어요: {type(e).__name__}")
    return "".join(getattr(b, "text", "") for b in resp.content).strip(), model


def chat(system: str, messages: list[dict]) -> tuple[str, str]:
    """(답변, 실제로 쓴 모델) 을 돌려줘요."""
    p = provider()
    if p == "gemini":
        return _gemini(system, messages)
    if p == "claude":
        return _claude(system, messages)
    raise AIError("AI 상담이 아직 설정되지 않았어요. backend/.env 에 GEMINI_API_KEY 를 넣어 주세요.", 503)
