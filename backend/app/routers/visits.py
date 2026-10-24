"""병원 방문 기록 API.

GET    /api/pets/{id}/vet-visits     방문 기록 (최신순) + 다음 방문 예정
POST   /api/pets/{id}/vet-visits     기록 추가 (병원을 비우면 펫의 담당 병원으로)
GET    /api/vet-visits/{vid}         한 건 조회
PATCH  /api/vet-visits/{vid}         수정
DELETE /api/vet-visits/{vid}         삭제
"""
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import VetVisit
from .pets import get_pet_or_404

router = APIRouter(prefix="/api", tags=["vet-visits"])

Category = Literal["정기검진", "진료", "예방접종", "검사", "수술", "기타"]


class VisitBase(BaseModel):
    visit_date: date
    category: Category = "진료"
    title: str = Field(min_length=1, max_length=100)
    hospital: Optional[str] = Field(default=None, max_length=100)
    diagnosis: Optional[str] = Field(default=None, max_length=1000)
    treatment: Optional[str] = Field(default=None, max_length=1000)
    note: Optional[str] = Field(default=None, max_length=1000)
    next_visit_date: Optional[date] = None

    @model_validator(mode="after")
    def _dates(self):
        if self.next_visit_date and self.next_visit_date < self.visit_date:
            raise ValueError("다음 방문 예정일은 방문일보다 뒤여야 해요")
        return self


class VisitCreate(VisitBase):
    pass


class VisitUpdate(BaseModel):
    visit_date: Optional[date] = None
    category: Optional[Category] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    hospital: Optional[str] = Field(default=None, max_length=100)
    diagnosis: Optional[str] = Field(default=None, max_length=1000)
    treatment: Optional[str] = Field(default=None, max_length=1000)
    note: Optional[str] = Field(default=None, max_length=1000)
    next_visit_date: Optional[date] = None


class VisitOut(VisitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    created_at: datetime


class VisitList(BaseModel):
    visits: list[VisitOut]
    next_visit: Optional[VisitOut]   # 오늘 이후로 가장 가까운 '다음 방문 예정'이 적힌 기록


def get_visit_or_404(db: Session, vid: int) -> VetVisit:
    v = db.get(VetVisit, vid)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "방문 기록을 찾을 수 없어요")
    return v


@router.get("/pets/{pet_id}/vet-visits", response_model=VisitList)
def list_visits(pet_id: int, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    visits = db.scalars(
        select(VetVisit).where(VetVisit.pet_id == pet_id)
        .order_by(VetVisit.visit_date.desc(), VetVisit.id.desc())
    ).all()
    upcoming = [v for v in visits if v.next_visit_date and v.next_visit_date >= date.today()]
    nxt = min(upcoming, key=lambda v: v.next_visit_date) if upcoming else None
    return VisitList(
        visits=[VisitOut.model_validate(v) for v in visits],
        next_visit=VisitOut.model_validate(nxt) if nxt else None,
    )


@router.post("/pets/{pet_id}/vet-visits", response_model=VisitOut, status_code=status.HTTP_201_CREATED)
def create_visit(pet_id: int, body: VisitCreate, db: Session = Depends(get_db)):
    pet = get_pet_or_404(db, pet_id)
    data = body.model_dump()
    if not data["hospital"]:
        data["hospital"] = pet.hospital
    visit = VetVisit(pet_id=pet_id, **data)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


@router.get("/vet-visits/{vid}", response_model=VisitOut)
def get_visit(vid: int, db: Session = Depends(get_db)):
    return get_visit_or_404(db, vid)


@router.patch("/vet-visits/{vid}", response_model=VisitOut)
def update_visit(vid: int, body: VisitUpdate, db: Session = Depends(get_db)):
    visit = get_visit_or_404(db, vid)
    changes = body.model_dump(exclude_unset=True)
    for required in ("visit_date", "category", "title"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} 값은 비울 수 없어요")
    for k, v in changes.items():
        setattr(visit, k, v)
    if visit.next_visit_date and visit.next_visit_date < visit.visit_date:
        raise HTTPException(422, "다음 방문 예정일은 방문일보다 뒤여야 해요")
    db.commit()
    db.refresh(visit)
    return visit


@router.delete("/vet-visits/{vid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(vid: int, db: Session = Depends(get_db)):
    db.delete(get_visit_or_404(db, vid))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
