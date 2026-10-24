"""놀이 탭 규칙 (가상 강아지). DB·FastAPI 없이 테스트할 수 있게 분리했어요.

- 행복도·포만감은 0~100. 시간이 지나면 시간당 조금씩 줄어요.
- 간식은 '진짜 돌봄 기록'으로 모아요: 오늘 남긴 기록 종류(식사·배변·체중·투약)마다 1개,
  오늘 한 케어 체크마다 1개, 하루 최대 MAX_TREATS_PER_DAY 개.
  → 게임을 하려면 기록을 하게 되도록 만든 장치예요.
- 가상 간식이에요. 실제 간식 양과는 관계없어요.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

HAPPINESS_DECAY_PER_HOUR = 2.0
FULLNESS_DECAY_PER_HOUR = 3.0
MAX_TREATS_PER_DAY = 6

WALK_COOLDOWN = timedelta(hours=3)
BALL_COOLDOWN = timedelta(minutes=30)

# 행동별 효과: (행복도, 포만감)
EFFECTS = {
    "treat": (8, 25),
    "walk": (25, -10),
    "ball": (15, -5),
    "pet": (5, 0),
}


def clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def decayed(happiness: float, fullness: float, updated_at: datetime, now: datetime) -> tuple[float, float]:
    hours = max(0.0, (now - updated_at).total_seconds() / 3600)
    return clamp(happiness - HAPPINESS_DECAY_PER_HOUR * hours), clamp(fullness - FULLNESS_DECAY_PER_HOUR * hours)


def mood(happiness: float, fullness: float) -> tuple[str, str]:
    """(코드, 말풍선)"""
    if fullness < 25:
        return "hungry", "배고파요… 간식 있어요?"
    if happiness >= 80:
        return "excited", "오늘 정말 신나요!"
    if happiness >= 50:
        return "happy", "기분 좋아요 :)"
    if happiness >= 25:
        return "bored", "심심해요. 같이 놀아요!"
    return "sad", "조금 쓸쓸해요…"


@dataclass
class Cooldowns:
    walk_ready_at: Optional[datetime]
    ball_ready_at: Optional[datetime]


def cooldowns(last_walk_at: Optional[datetime], last_ball_at: Optional[datetime], now: datetime) -> Cooldowns:
    def ready(last, cd):
        if last is None or now >= last + cd:
            return None
        return last + cd
    return Cooldowns(ready(last_walk_at, WALK_COOLDOWN), ready(last_ball_at, BALL_COOLDOWN))


def treats_earned(record_types_today: set[str], care_checks_today: int) -> int:
    kinds = len(record_types_today & {"meal", "poop", "weight", "med"})
    return min(MAX_TREATS_PER_DAY, kinds + care_checks_today)
