"""프로필 사진 API.

PUT    /api/pets/{id}/photo   사진 저장 (브라우저에서 줄인 이미지를 data URL 로 보내요)
GET    /api/pets/{id}/photo   사진 보기 (<img src> 로 사용, ?v=버전 을 붙이면 캐시돼요)
DELETE /api/pets/{id}/photo   사진 삭제

multipart 업로드 대신 data URL(JSON)을 받아서 python-multipart 같은 추가 패키지가 필요 없어요.
"""
import base64
import binascii
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PetPhoto
from .pets import get_pet_or_404, to_out

router = APIRouter(prefix="/api/pets", tags=["photos"])

MAX_BYTES = 1_500_000  # 1.5MB (512px JPEG 는 보통 100KB 안팎)
DATA_URL_RE = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,(.+)$", re.S)
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class PhotoIn(BaseModel):
    data_url: str = Field(max_length=2_100_000)
    color: Optional[str] = None  # 사진에서 뽑은 털 색 (#RRGGBB) — 놀이 탭 캐릭터 색으로 써요


@router.put("/{pet_id}/photo")
def put_photo(pet_id: int, body: PhotoIn, db: Session = Depends(get_db)):
    pet = get_pet_or_404(db, pet_id)
    m = DATA_URL_RE.match(body.data_url)
    if not m:
        raise HTTPException(422, "JPG, PNG, WEBP 이미지만 올릴 수 있어요")
    try:
        data = base64.b64decode(m.group(2), validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "이미지 데이터가 올바르지 않아요")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "사진이 너무 커요 (1.5MB 이하)")
    if body.color and not COLOR_RE.match(body.color):
        raise HTTPException(422, "색상 형식이 올바르지 않아요 (#RRGGBB)")

    photo = db.get(PetPhoto, pet_id) or PetPhoto(pet_id=pet_id)
    photo.mime, photo.data, photo.color, photo.updated_at = m.group(1), data, body.color, datetime.now()
    db.add(photo)
    db.commit()
    return to_out(db, pet)


@router.get("/{pet_id}/photo")
def get_photo(pet_id: int, db: Session = Depends(get_db)):
    photo = db.get(PetPhoto, pet_id)
    if photo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사진이 없어요")
    # URL 에 ?v=버전 이 붙어 있어서 사진이 바뀌면 주소도 바뀌어요 → 오래 캐시해도 안전
    return Response(content=photo.data, media_type=photo.mime,
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})


@router.delete("/{pet_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(pet_id: int, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    photo = db.get(PetPhoto, pet_id)
    if photo:
        db.delete(photo)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
