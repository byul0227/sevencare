"""AI건강 탭 API.

GET  /api/pets/{id}/body-check   비만도 체크: 최근 체중 · 품종 표준 체중(AKC) · 최근 BCS
GET  /api/health-info            증상별 '언제 병원에 가야 하나' 정보 (출처 포함)
GET  /api/ai/status              AI 상담 사용 가능 여부
POST /api/pets/{id}/ai-chat      AI 상담 (반려견 기록을 요약해 함께 보냄)

AI 상담은 backend/.env 에 GEMINI_API_KEY(무료) 또는 ANTHROPIC_API_KEY 가 있을 때만 동작해요 (없으면 503).
모델 호출은 app/ai_provider.py 에 있어요. SEVENCARE_AI_MODEL 로 모델을 바꿀 수 있어요.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ai_provider
from ..breeds import compare, find_breed
from ..database import get_db
from ..health_info import SYMPTOMS
from ..models import CareCheck, Medication, Pet, Record, VetVisit
from .care import to_out as care_out
from .pets import get_pet_or_404, to_out as pet_out
from .report import build_report

router = APIRouter(prefix="/api", tags=["ai-health"])

def ai_model() -> str | None:
    return ai_provider.model_candidates()[0] if ai_provider.provider() else None


def ai_available() -> bool:
    return ai_provider.provider() is not None


# ---------------- 비만도 체크 ----------------
@router.get("/pets/{pet_id}/body-check")
def body_check(pet_id: int, db: Session = Depends(get_db)):
    pet = get_pet_or_404(db, pet_id)
    weight = pet_out(db, pet).latest_weight_kg
    std = find_breed(pet.breed, pet.gender)
    bcs = db.scalars(
        select(CareCheck).where(CareCheck.pet_id == pet_id, CareCheck.kind == "bcs")
        .order_by(CareCheck.checked_at.desc(), CareCheck.id.desc()).limit(5)
    ).all()
    return {
        "weight_kg": weight,
        "breed": pet.breed,
        "breed_standard": std,
        "position": compare(weight, std),   # below / within / above / None
        "bcs_latest": care_out(bcs[0]) if bcs else None,
        "bcs_history": [care_out(c) for c in bcs],
    }


# ---------------- 증상 정보 ----------------
@router.get("/health-info")
def health_info():
    return SYMPTOMS


# ---------------- AI 상담 ----------------
@router.get("/ai/status")
def ai_status():
    return {"available": ai_available(), "provider": ai_provider.provider(), "model": ai_model()}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatIn(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


SYSTEM_PROMPT = """당신은 '세븐케어' 앱의 반려견 건강 도우미예요. 노령견을 돌보는 보호자와 한국어로 대화해요.

지켜야 할 것:
- 진단하지 마세요. 가능한 원인을 설명할 수는 있지만 "~일 수 있어요, 정확한 건 수의사 진찰이 필요해요"처럼 말해요.
- 호흡 곤란, 쓰러짐, 경련, 반응 없음, 창백한 잇몸, 멈추지 않는 구토·출혈, 24~48시간 넘는 식사 거부 같은 신호가 보이면 가장 먼저 "지금 동물병원에 연락하세요"라고 안내해요.
- 약의 용량·종류를 바꾸거나 끊으라고 하지 마세요. 사람 약을 먹이라고 하지 마세요. 약 관련 질문은 처방한 수의사와 상의하라고 안내해요.
- 아래 [반려견 기록]을 근거로 답하고, 기록에 있는 사실을 인용할 때는 날짜나 수치를 함께 말해요. 기록에 없는 건 지어내지 말고 모른다고 해요.
- 3~6문장 정도로 짧고 따뜻하게 답해요. 필요하면 보호자가 집에서 더 관찰해 기록할 것(식사량, 배변, 체중 등)을 제안해요.
"""


def _fmt_dt(d: datetime) -> str:
    return d.strftime("%m/%d %H:%M")


def build_context(db: Session, pet: Pet) -> str:
    """AI에게 보낼 반려견 기록 요약 (최근 2주 중심)."""
    out = pet_out(db, pet)
    lines = [
        f"이름: {pet.name} / 품종: {pet.breed} / 나이: {pet.age_years if pet.age_years is not None else '미상'}세 / "
        f"성별: {pet.gender}{'(중성화)' if pet.neutered else ''} / 최근 체중: {out.latest_weight_kg or '미측정'}kg",
        f"기저 질환: {pet.condition or '없음'} / 담당 병원: {pet.hospital or '미등록'}",
    ]
    rep = build_report(db, pet, 4)
    lines.append(f"최근 리포트: 평균 식사량 {rep.meal_avg_pct}% · 배변 정상 비율 {rep.poop_normal_pct}% · "
                 f"체중 변화 {rep.weight_change_pct}%")
    for a in rep.alerts:
        lines.append(f"리포트 알림: {a.message}")

    since = datetime.combine(date.today() - timedelta(days=13), time.min)
    recs = db.scalars(select(Record).where(Record.pet_id == pet.id, Record.recorded_at >= since)
                      .order_by(Record.recorded_at.desc()).limit(60)).all()
    if recs:
        lines.append("최근 2주 기록 (최신순):")
        for r in recs:
            if r.type == "meal":
                detail = f"식사 {r.meal_amount}%"
            elif r.type == "poop":
                detail = f"배변 {r.poop_firmness}{' 혈변/점액' if r.poop_blood else ''}{f' {r.poop_color}' if r.poop_color else ''}"
            elif r.type == "weight":
                detail = f"체중 {r.weight_kg}kg"
            else:
                detail = f"투약 {r.med_name}"
            note = f" (메모: {r.note})" if r.note and not r.note.startswith("[데모]") else ""
            lines.append(f"- {_fmt_dt(r.recorded_at)} {detail}{note}")

    meds = db.scalars(select(Medication).where(Medication.pet_id == pet.id, Medication.active.is_(True))).all()
    if meds:
        lines.append("복용 중인 약: " + "; ".join(
            f"{m.name}{f' {m.dose}' if m.dose else ''} 매일 {m.times}{f' ({m.instructions})' if m.instructions else ''}"
            for m in meds))

    for kind, label in (("cognitive", "인지기능(CCDR)"), ("qol", "삶의 질(HHHHHMM)"), ("mobility", "거동"), ("bcs", "BCS")):
        c = db.scalar(select(CareCheck).where(CareCheck.pet_id == pet.id, CareCheck.kind == kind)
                      .order_by(CareCheck.checked_at.desc()).limit(1))
        if c:
            o = care_out(c)
            lines.append(f"최근 {label}: {o.score}/{o.max_score}점{f' ({o.band.label})' if o.band else ''}, "
                         f"{c.checked_at.strftime('%Y-%m-%d')}")

    visits = db.scalars(select(VetVisit).where(VetVisit.pet_id == pet.id)
                        .order_by(VetVisit.visit_date.desc()).limit(5)).all()
    for v in visits:
        extra = " · ".join(x for x in (v.diagnosis, v.treatment) if x)
        lines.append(f"병원 방문 {v.visit_date}: {v.title}{f' — {extra}' if extra else ''}")
    return "\n".join(lines)


@router.post("/pets/{pet_id}/ai-chat")
def ai_chat(pet_id: int, body: ChatIn, db: Session = Depends(get_db)):
    pet = get_pet_or_404(db, pet_id)
    if not ai_available():
        raise HTTPException(503, "AI 상담이 아직 설정되지 않았어요. backend/.env 에 GEMINI_API_KEY 를 넣어 주세요.")
    if body.messages[-1].role != "user":
        raise HTTPException(422, "마지막 메시지는 사용자 질문이어야 해요")

    system = f"{SYSTEM_PROMPT}\n[반려견 기록]\n{build_context(db, pet)}"
    try:
        reply, model = ai_provider.chat(system, [m.model_dump() for m in body.messages])
    except ai_provider.AIError as e:
        raise HTTPException(e.status, str(e))
    return {"reply": reply or "답변을 만들지 못했어요. 다시 물어봐 주세요.", "model": model}
