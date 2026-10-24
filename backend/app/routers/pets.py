"""펫 등록/조회/수정/삭제 API."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Pet, PetPhoto, Record
from ..schemas import PetCreate, PetOut, PetUpdate

router = APIRouter(prefix="/api/pets", tags=["pets"])


def get_pet_or_404(db: Session, pet_id: int) -> Pet:
    pet = db.get(Pet, pet_id)
    if pet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "펫을 찾을 수 없어요")
    return pet


def to_out(db: Session, pet: Pet) -> PetOut:
    latest = db.scalar(
        select(Record.weight_kg)
        .where(Record.pet_id == pet.id, Record.type == "weight")
        .order_by(Record.recorded_at.desc(), Record.id.desc())
        .limit(1)
    )
    out = PetOut.model_validate(pet)
    out.latest_weight_kg = latest if latest is not None else pet.weight_kg
    photo = db.execute(select(PetPhoto.updated_at, PetPhoto.color).where(PetPhoto.pet_id == pet.id)).first()
    if photo:  # 사진 데이터(용량 큼)는 빼고 버전·색만 조회
        out.photo_version = int(photo.updated_at.timestamp() * 1000)
        out.photo_color = photo.color
    return out


@router.get("", response_model=list[PetOut])
def list_pets(db: Session = Depends(get_db)):
    pets = db.scalars(select(Pet).order_by(Pet.id)).all()
    return [to_out(db, p) for p in pets]


@router.post("", response_model=PetOut, status_code=status.HTTP_201_CREATED)
def create_pet(body: PetCreate, db: Session = Depends(get_db)):
    pet = Pet(**body.model_dump())
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return to_out(db, pet)


@router.get("/{pet_id}", response_model=PetOut)
def get_pet(pet_id: int, db: Session = Depends(get_db)):
    return to_out(db, get_pet_or_404(db, pet_id))


@router.patch("/{pet_id}", response_model=PetOut)
def update_pet(pet_id: int, body: PetUpdate, db: Session = Depends(get_db)):
    pet = get_pet_or_404(db, pet_id)
    changes = body.model_dump(exclude_unset=True)
    for required in ("name", "breed", "gender", "neutered"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} 값은 비울 수 없어요")
    for key, value in changes.items():
        setattr(pet, key, value)
    db.commit()
    db.refresh(pet)
    return to_out(db, pet)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(pet_id: int, db: Session = Depends(get_db)):
    pet = get_pet_or_404(db, pet_id)
    db.delete(pet)  # 해당 펫의 기록도 함께 삭제돼요 (cascade)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
