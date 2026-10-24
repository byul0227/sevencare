"""투약 스케줄 계산 (DB·FastAPI 없이 테스트할 수 있게 분리).

약마다 정해진 시간(슬롯)과, 그날 남긴 투약 기록(records.type='med')을 짝지어서
각 슬롯이 복용 완료 / 지금 복용 / 예정 / 놓침 중 무엇인지 계산해요.

짝짓는 규칙: 같은 약 이름의 기록을 시간이 가장 가까운 슬롯에 붙여요 (앞뒤 MATCH_WINDOW 안에서만).
그 슬롯이 이미 복용 완료라면 '중복 기록'으로 알려줘요.
(놓친 약을 다음 복용 직전에 먹이면 가까운 다음 슬롯과 겹쳐서 중복으로 잡혀요. 이중 투약 위험을 알리기 위한 의도예요.)
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional

MATCH_WINDOW = timedelta(hours=3)   # 기록을 슬롯에 붙일 수 있는 최대 시간 차
DUE_WINDOW = timedelta(hours=1)     # 예정 시간 앞뒤 1시간은 '지금 복용'
# 예정 시간 + 1시간이 지나도 기록이 없으면 '놓침'


@dataclass
class Slot:
    medication_id: int
    name: str
    dose: Optional[str]
    instructions: Optional[str]
    time: str                      # "09:00"
    at: datetime
    status: str = "upcoming"       # taken / due / missed / upcoming
    record_id: Optional[int] = None
    taken_at: Optional[datetime] = None


@dataclass
class Schedule:
    date: date
    slots: list[Slot] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)


def parse_times(times: str) -> list[str]:
    return [t for t in times.split(",") if t]


def is_active_on(med, on: date) -> bool:
    return bool(med.active) and med.start_date <= on and (med.end_date is None or on <= med.end_date)


def build_schedule(meds, records, on: date, now: datetime) -> Schedule:
    """meds: Medication 목록, records: 그날의 type='med' 기록 목록 (recorded_at, med_name, id)."""
    sched = Schedule(date=on)
    by_name: dict[str, list[Slot]] = {}

    for med in meds:
        if not is_active_on(med, on):
            continue
        for t in parse_times(med.times):
            hh, mm = map(int, t.split(":"))
            slot = Slot(medication_id=med.id, name=med.name, dose=med.dose,
                        instructions=med.instructions, time=t, at=datetime.combine(on, time(hh, mm)))
            sched.slots.append(slot)
            by_name.setdefault(med.name, []).append(slot)

    duplicates: dict[str, int] = {}
    for rec in sorted(records, key=lambda r: r.recorded_at):
        candidates = [s for s in by_name.get(rec.med_name, []) if abs(s.at - rec.recorded_at) <= MATCH_WINDOW]
        if not candidates:
            continue  # 스케줄에 없는 약이거나 시간이 멀면 그냥 일반 기록
        best = min(candidates, key=lambda s: abs(s.at - rec.recorded_at))
        if best.record_id is None:
            best.record_id, best.taken_at = rec.id, rec.recorded_at
        else:
            duplicates[rec.med_name] = duplicates.get(rec.med_name, 0) + 1

    for s in sched.slots:
        if s.record_id is not None:
            s.status = "taken"
        elif now >= s.at + DUE_WINDOW:
            s.status = "missed"
        elif now >= s.at - DUE_WINDOW:
            s.status = "due"
        else:
            s.status = "upcoming"
    sched.slots.sort(key=lambda s: (s.at, s.name))

    missed = [s for s in sched.slots if s.status == "missed"]
    if missed:
        names = ", ".join(f"{s.name}({s.time})" for s in missed)
        sched.alerts.append({"level": "warning", "code": "missed",
                             "message": f"아직 복용 기록이 없어요: {names}. 먹였다면 체크해 주세요."})
    for name, n in duplicates.items():
        sched.alerts.append({"level": "critical", "code": "duplicate",
                             "message": f"{name} 복용이 같은 시간대에 {n + 1}번 기록됐어요. 중복 투약이 아닌지 확인해 주세요."})
    return sched
