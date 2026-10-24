"""놀이 탭 API (가상 강아지).

GET  /api/pets/{id}/play          상태 (행복도·포만감·기분·남은 간식·쿨다운)
POST /api/pets/{id}/play/{action} 행동: treat(간식) / walk(산책) / ball(공놀이) / pet(쓰다듬기)
"""
from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CareCheck, PetPlay, Record
from ..play_logic import EFFECTS, MAX_TREATS_PER_DAY, clamp, cooldowns, decayed, mood, treats_earned
from .pets import get_pet_or_404

router = APIRouter(prefix="/api/pets", tags=["play"])

Action = Literal["treat", "walk", "ball", "pet"]
DEMO_PREFIX = "[데모]"


def _today_bounds():
    today = date.today()
    return today, datetime.combine(today, time.min), datetime.combine(today + timedelta(days=1), time.min)


def _earned_today(db: Session, pet_id: int) -> tuple[int, dict]:
    today, lo, hi = _today_bounds()
    rows = db.execute(select(Record.type, Record.note).where(
        Record.pet_id == pet_id, Record.recorded_at >= lo, Record.recorded_at < hi)).all()
    types = {t for t, note in rows if not (note or "").startswith(DEMO_PREFIX)}
    checks = db.scalar(select(func.count(CareCheck.id)).where(
        CareCheck.pet_id == pet_id, CareCheck.checked_at >= lo, CareCheck.checked_at < hi)) or 0
    return treats_earned(types, checks), {"record_types": sorted(types), "care_checks": checks}


def _load(db: Session, pet_id: int) -> PetPlay:
    play = db.get(PetPlay, pet_id)
    if play is None:
        play = PetPlay(pet_id=pet_id, happiness=70, fullness=70, updated_at=datetime.now(), treats_spent=0)
        db.add(play)
        db.flush()
    return play


def _state(db: Session, pet_id: int, play: PetPlay, now: datetime) -> dict:
    h, f = decayed(play.happiness, play.fullness, play.updated_at, now)
    earned, detail = _earned_today(db, pet_id)
    spent = play.treats_spent if play.treats_day == date.today() else 0
    code, line = mood(h, f)
    cd = cooldowns(play.last_walk_at, play.last_ball_at, now)
    return {
        "happiness": round(h), "fullness": round(f),
        "mood": code, "says": line,
        "treats_available": max(0, earned - spent), "treats_earned": earned, "treats_max": MAX_TREATS_PER_DAY,
        "earned_from": detail,
        "walk_ready_at": cd.walk_ready_at, "ball_ready_at": cd.ball_ready_at,
    }


@router.get("/{pet_id}/play")
def get_play(pet_id: int, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    play = _load(db, pet_id)
    db.commit()
    return _state(db, pet_id, play, datetime.now())


@router.post("/{pet_id}/play/{action}")
def do_action(pet_id: int, action: Action, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    now = datetime.now()
    play = _load(db, pet_id)
    state = _state(db, pet_id, play, now)

    if action == "treat" and state["treats_available"] <= 0:
        raise HTTPException(409, "간식이 없어요. 오늘 식사·배변·체중·투약을 기록하거나 케어 체크를 하면 간식이 생겨요!")
    if action == "walk" and state["walk_ready_at"]:
        raise HTTPException(409, "방금 산책했어요. 조금 쉬었다가 다시 가요!")
    if action == "ball" and state["ball_ready_at"]:
        raise HTTPException(409, "숨 좀 고르고 다시 놀아요!")

    dh, df = EFFECTS[action]
    play.happiness = clamp(state["happiness"] + dh)
    play.fullness = clamp(state["fullness"] + df)
    play.updated_at = now
    if action == "treat":
        if play.treats_day != date.today():
            play.treats_day, play.treats_spent = date.today(), 0
        play.treats_spent += 1
    elif action == "walk":
        play.last_walk_at = now
    elif action == "ball":
        play.last_ball_at = now
    db.commit()
    return _state(db, pet_id, play, now)
