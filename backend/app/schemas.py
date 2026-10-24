"""요청/응답 스키마 (Pydantic v2)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

RecordType = Literal["meal", "poop", "weight", "med"]
Gender = Literal["수컷", "암컷"]
Firmness = Literal["무름", "정상", "딱딱함"]
PoopColor = Literal["갈색", "검붉은색", "회색/노란색"]


# ---------------- pets ----------------
class PetBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    breed: str = Field(min_length=1, max_length=50)
    age_years: Optional[int] = Field(default=None, ge=0, le=40)
    gender: Gender = "수컷"
    neutered: bool = False
    weight_kg: Optional[float] = Field(default=None, gt=0, le=150)
    condition: Optional[str] = Field(default=None, max_length=200)
    hospital: Optional[str] = Field(default=None, max_length=100)


class PetCreate(PetBase):
    pass


class PetUpdate(BaseModel):
    """부분 수정용: 보낸 필드만 바뀌어요."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    breed: Optional[str] = Field(default=None, min_length=1, max_length=50)
    age_years: Optional[int] = Field(default=None, ge=0, le=40)
    gender: Optional[Gender] = None
    neutered: Optional[bool] = None
    weight_kg: Optional[float] = Field(default=None, gt=0, le=150)
    condition: Optional[str] = Field(default=None, max_length=200)
    hospital: Optional[str] = Field(default=None, max_length=100)


class PetOut(PetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    # 가장 최근 체중 기록 (없으면 등록 시 체중)
    latest_weight_kg: Optional[float] = None
    # 프로필 사진: 버전(바뀔 때마다 달라짐, 없으면 null)과 사진에서 뽑은 털 색
    photo_version: Optional[int] = None
    photo_color: Optional[str] = None


# ---------------- records ----------------
# type 별로 꼭 있어야 하는 필드
REQUIRED_BY_TYPE = {
    "meal": ("meal_amount",),
    "poop": ("poop_firmness",),
    "weight": ("weight_kg",),
    "med": ("med_name",),
}


class RecordFields(BaseModel):
    recorded_at: Optional[datetime] = None
    meal_amount: Optional[int] = Field(default=None, ge=0, le=100)
    poop_firmness: Optional[Firmness] = None
    poop_color: Optional[PoopColor] = None
    poop_blood: Optional[bool] = None
    weight_kg: Optional[float] = Field(default=None, gt=0, le=150)
    med_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    note: Optional[str] = Field(default=None, max_length=500)


class RecordCreate(RecordFields):
    type: RecordType

    @model_validator(mode="after")
    def _check_required(self):
        missing = [f for f in REQUIRED_BY_TYPE[self.type] if getattr(self, f) is None]
        if missing:
            raise ValueError(f"'{self.type}' 기록에는 {', '.join(missing)} 값이 필요해요")
        return self


class RecordUpdate(RecordFields):
    """부분 수정용. type 은 바꿀 수 없어요 (바꾸려면 삭제 후 새로 등록)."""


class RecordOut(RecordFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    type: RecordType
    recorded_at: datetime
    created_at: datetime
