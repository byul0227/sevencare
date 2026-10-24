"""사료 성분표 분석 API

POST /api/food-label/parse       OCR로 읽은 글자 → 성분 수치 (화면에서 사용자가 고칠 수 있게 돌려줘요)
POST /api/pets/{id}/food-check   성분 수치 → AAFCO 기준 + 우리 개 상태(질환·비만도·인지기능) 평가
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..food_label import evaluate, parse_label
from ..models import CareCheck
from .pets import get_pet_or_404

router = APIRouter(prefix="/api", tags=["food-label"])


class ParseIn(BaseModel):
    text: str = Field(max_length=20000)
    mode: Literal["full", "basic"] = "full"   # basic = 정확도 비교 실험용 기본 파서


class Nutrients(BaseModel):
    protein: Optional[float] = Field(default=None, ge=0, le=100)
    fat: Optional[float] = Field(default=None, ge=0, le=100)
    fiber: Optional[float] = Field(default=None, ge=0, le=100)
    ash: Optional[float] = Field(default=None, ge=0, le=100)
    calcium: Optional[float] = Field(default=None, ge=0, le=100)
    phosphorus: Optional[float] = Field(default=None, ge=0, le=100)
    moisture: Optional[float] = Field(default=None, ge=0, le=95)
    sodium: Optional[float] = Field(default=None, ge=0, le=100)


class CheckIn(BaseModel):
    nutrients: Nutrients
    kcal_per_kg: Optional[float] = Field(default=None, ge=500, le=8000)
    keywords: list[str] = []


@router.post("/food-label/parse")
def parse(body: ParseIn):
    return parse_label(body.text, body.mode)


def _latest_score(db: Session, pet_id: int, kind: str) -> Optional[int]:
    row = db.scalars(
        select(CareCheck).where(CareCheck.pet_id == pet_id, CareCheck.kind == kind)
        .order_by(CareCheck.checked_at.desc(), CareCheck.id.desc()).limit(1)
    ).first()
    return row.score if row else None


@router.post("/pets/{pet_id}/food-check")
def food_check(pet_id: int, body: CheckIn, db: Session = Depends(get_db)):
    pet = get_pet_or_404(db, pet_id)
    bcs = _latest_score(db, pet_id, "bcs")
    ccdr = _latest_score(db, pet_id, "cognitive")
    result = evaluate(body.nutrients.model_dump(exclude_none=True), body.kcal_per_kg, body.keywords,
                      condition=pet.condition, bcs=bcs, ccdr=ccdr)
    result["pet"] = {"name": pet.name, "condition": pet.condition, "bcs": bcs, "ccdr": ccdr}
    return result
