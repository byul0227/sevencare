"""DB 테이블 정의: pets(반려동물), records(일일 기록), care_checks(케어 체크), medications(투약 스케줄), vet_visits(병원 방문),
pet_photos(프로필 사진), pet_play(놀이 탭 상태)."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# records.type 에 들어갈 수 있는 값
RECORD_TYPES = ("meal", "poop", "weight", "med")


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    breed: Mapped[str] = mapped_column(String(50))
    age_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(10), default="수컷")  # 수컷 / 암컷
    neutered: Mapped[bool] = mapped_column(Boolean, default=False)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 등록 시 체중
    condition: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 기저 질환
    hospital: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 담당 병원
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    records: Mapped[list["Record"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan", passive_deletes=True
    )
    care_checks: Mapped[list["CareCheck"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan", passive_deletes=True
    )
    medications: Mapped[list["Medication"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan", passive_deletes=True
    )
    vet_visits: Mapped[list["VetVisit"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan", passive_deletes=True
    )
    photo: Mapped[Optional["PetPhoto"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    play: Mapped[Optional["PetPlay"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )


class Record(Base):
    """하루 기록 한 건. type 에 따라 쓰는 컬럼이 달라요.

    - meal   : meal_amount (섭취량 %, 0~100)
    - poop   : poop_firmness, poop_color, poop_blood
    - weight : weight_kg
    - med    : med_name
    공통     : recorded_at(기록 시각), note(특이사항)
    """

    __tablename__ = "records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(10), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    meal_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    poop_firmness: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 무름/정상/딱딱함
    poop_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 갈색/검붉은색/회색·노란색
    poop_blood: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # 혈변·점액 여부
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    med_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    pet: Mapped[Pet] = relationship(back_populates="records")


class CareCheck(Base):
    """케어 체크 한 번의 결과 (거동 / 인지기능 / 삶의 질).

    문항 정의와 점수 계산은 app/care_scales.py 에 있어요. answers 는 {"문항id": 값} JSON 문자열.
    """

    __tablename__ = "care_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # mobility / cognitive / qol
    checked_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    answers: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer)
    band_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    pet: Mapped[Pet] = relationship(back_populates="care_checks")


class Medication(Base):
    """복용 중인 약과 매일 먹는 시간. 실제 복용 여부는 records(type='med')로 기록해요."""

    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    dose: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)            # 예: 1정, 0.5ml
    times: Mapped[str] = mapped_column(String(100))                                   # "09:00,21:00"
    instructions: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)   # 수의사 지시사항
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    pet: Mapped[Pet] = relationship(back_populates="medications")


class VetVisit(Base):
    """병원 방문 기록 (펫 상세 화면의 타임라인)."""

    __tablename__ = "vet_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    visit_date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(10))                                  # 정기검진/진료/예방접종/검사/수술/기타
    title: Mapped[str] = mapped_column(String(100))                                    # 예: 슬개골 탈구 2기 진단
    hospital: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)             # 진단·검사 결과
    treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)             # 처치·처방
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_visit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)      # 다음 방문 예정일
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    pet: Mapped[Pet] = relationship(back_populates="vet_visits")


class PetPhoto(Base):
    """프로필 사진 (브라우저에서 512px로 줄여서 올려요). 펫 1마리당 1장."""

    __tablename__ = "pet_photos"

    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), primary_key=True)
    mime: Mapped[str] = mapped_column(String(20))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # 사진에서 뽑은 털 색 (#RRGGBB)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    pet: Mapped[Pet] = relationship(back_populates="photo")


class PetPlay(Base):
    """놀이 탭의 가상 강아지 상태. 수치는 시간이 지나면 조금씩 줄어요 (읽을 때 계산)."""

    __tablename__ = "pet_play"

    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), primary_key=True)
    happiness: Mapped[float] = mapped_column(Float, default=70)
    fullness: Mapped[float] = mapped_column(Float, default=70)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    treats_day: Mapped[Optional[date]] = mapped_column(Date, nullable=True)   # 간식 사용 횟수를 센 날
    treats_spent: Mapped[int] = mapped_column(Integer, default=0)
    last_walk_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_ball_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    pet: Mapped[Pet] = relationship(back_populates="play")
