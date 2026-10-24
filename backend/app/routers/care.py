"""케어 체크 API (거동 / 인지기능 / 삶의 질).

GET    /api/care-scales                 척도 정의 (문항·보기·해석 기준·출처)
GET    /api/pets/{id}/care-summary      종류별 최신 결과
GET    /api/pets/{id}/care-checks       결과 목록 (?kind=cognitive&limit=10)
POST   /api/pets/{id}/care-checks       체크 저장 → 서버가 점수 계산
DELETE /api/care-checks/{id}            삭제
"""
import json
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..care_scales import SCALES, ScaleError, score_answers
from ..database import get_db
from ..models import CareCheck
from .pets import get_pet_or_404

router = APIRouter(prefix="/api", tags=["care"])

CareKind = Literal["mobility", "cognitive", "qol", "bcs"]


class Band(BaseModel):
    code: str
    level: str      # ok / warn / alert
    label: str
    advice: str


class CareCheckCreate(BaseModel):
    kind: CareKind
    answers: dict[str, int]
    checked_at: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=500)


class CareCheckOut(BaseModel):
    id: int
    pet_id: int
    kind: CareKind
    checked_at: datetime
    answers: dict[str, int]
    score: int
    max_score: int
    band: Optional[Band]
    note: Optional[str]


class CareSummary(BaseModel):
    mobility: Optional[CareCheckOut]
    mobility_today: bool
    cognitive: Optional[CareCheckOut]
    qol: Optional[CareCheckOut]


def to_out(c: CareCheck) -> CareCheckOut:
    scale = SCALES[c.kind]
    band = next((b for b in scale["bands"] if b["code"] == c.band_code), None)
    return CareCheckOut(
        id=c.id, pet_id=c.pet_id, kind=c.kind, checked_at=c.checked_at,
        answers=json.loads(c.answers), score=c.score, max_score=scale["max_score"],
        band=Band(**{k: band[k] for k in ("code", "level", "label", "advice")}) if band else None,
        note=c.note,
    )


def _latest(db: Session, pet_id: int, kind: str) -> Optional[CareCheck]:
    return db.scalar(
        select(CareCheck).where(CareCheck.pet_id == pet_id, CareCheck.kind == kind)
        .order_by(CareCheck.checked_at.desc(), CareCheck.id.desc()).limit(1)
    )


@router.get("/care-scales")
def get_scales():
    return SCALES


@router.get("/pets/{pet_id}/care-summary", response_model=CareSummary)
def care_summary(pet_id: int, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    latest = {k: _latest(db, pet_id, k) for k in ("mobility", "cognitive", "qol")}
    mob = latest["mobility"]
    return CareSummary(
        mobility=to_out(mob) if mob else None,
        mobility_today=bool(mob and mob.checked_at.date() == date.today()),
        cognitive=to_out(latest["cognitive"]) if latest["cognitive"] else None,
        qol=to_out(latest["qol"]) if latest["qol"] else None,
    )


@router.get("/pets/{pet_id}/care-checks", response_model=list[CareCheckOut])
def list_checks(
    pet_id: int,
    kind: Optional[CareKind] = None,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    get_pet_or_404(db, pet_id)
    stmt = select(CareCheck).where(CareCheck.pet_id == pet_id)
    if kind:
        stmt = stmt.where(CareCheck.kind == kind)
    stmt = stmt.order_by(CareCheck.checked_at.desc(), CareCheck.id.desc()).limit(limit)
    return [to_out(c) for c in db.scalars(stmt).all()]


@router.post("/pets/{pet_id}/care-checks", response_model=CareCheckOut, status_code=status.HTTP_201_CREATED)
def create_check(pet_id: int, body: CareCheckCreate, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    try:
        result = score_answers(body.kind, body.answers)
    except ScaleError as e:
        raise HTTPException(422, str(e))
    check = CareCheck(
        pet_id=pet_id, kind=body.kind,
        checked_at=body.checked_at or datetime.now(),
        answers=json.dumps(result["answers"]),
        score=result["score"],
        band_code=result["band"]["code"] if result["band"] else None,
        note=body.note,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return to_out(check)


@router.delete("/care-checks/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_check(check_id: int, db: Session = Depends(get_db)):
    check = db.get(CareCheck, check_id)
    if check is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "체크 기록을 찾을 수 없어요")
    db.delete(check)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
