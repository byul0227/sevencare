"""사료 성분표 분석 (순수 로직 — DB·네트워크 없이 테스트 가능)

1) parse_label(text)      : OCR로 읽은 글자에서 등록성분 수치를 뽑아요.
2) to_dry_matter(...)     : 포장 표시값(급여 상태 기준)을 수분을 뺀 건물 기준(DM)으로 환산해요.
3) estimate_kcal(...)     : 대사에너지를 수정 Atwater 계수로 추정해요 (표시가 없을 때).
4) evaluate(...)          : AAFCO 성견 기준 + 우리 개 상태(질환·비만도·인지기능)에 맞춰 평가해요.

국내 사료 포장에는 조단백질·조지방(이상), 조섬유·조회분·수분(이하), 칼슘·인이 표시돼요.
표시값은 '보증값(최소/최대)'이라 실제 함량과 조금 다를 수 있어요.
"""
from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------- 출처
SOURCES = {
    "aafco": ("AAFCO Dog Food Nutrient Profiles (성견 유지, 건물 기준 · 4,000 kcal/kg)",
              "https://www.aafco.org/wp-content/uploads/2023/01/Model_Bills_and_Regulations_Agenda_Midyear_2015_Final_Attachment_A.__Proposed_revisions_to_AAFCO_Nutrient_Profiles_PFC_Final_070214.pdf"),
    "atwater": ("NRC(2006) 수정 Atwater 계수 — AAFCO 칼로리 계산법",
                "https://www.merckvetmanual.com/management-and-nutrition/nutrition-small-animals/nutritional-requirements-of-small-animals"),
    "ckd": ("Cline, ACVN — 신장질환 처방식의 인 0.4~1.2 g/1000kcal · IRIS 2단계부터 식이 관리 권장",
            "https://todaysveterinarypractice.com/nutrition/acvn-nutrition-notesnutritional-management-of-chronic-kidney-disease-in-cats-dogs/"),
    "heart": ("ACVIM 이첨판 질환 합의 지침(2019) — 나트륨 B2 80~99, C 50~79 mg/100kcal",
              "https://onlinelibrary.wiley.com/doi/10.1111/jvim.15488"),
    "aaha": ("AAHA 2023 Senior Care Guidelines — 관절염 오메가3, 인지기능장애 MCT",
             "https://www.aaha.org/resources/2023-aaha-senior-care-guidelines-for-dogs-and-cats/disease-management-nutritional/"),
}

# ---------------------------------------------------------------- 1) 파싱
FIELDS = {
    # key: (표시 이름, 정규식 이름 패턴)
    "protein":    ("조단백질", r"조\s*단\s*백\s*질?|crude\s*protein|protein"),
    "fat":        ("조지방",   r"조\s*지\s*방|crude\s*fat|fat"),
    "fiber":      ("조섬유",   r"조\s*섬\s*유|crude\s*fib(?:er|re)|fib(?:er|re)"),
    "ash":        ("조회분",   r"조\s*회\s*분|crude\s*ash|ash"),
    "calcium":    ("칼슘",     r"칼\s*슘|calcium|\bca\b"),
    "phosphorus": ("인",       r"(?<![가-힣])인(?![가-힣])|phosphorus|\bp\b"),
    "moisture":   ("수분",     r"수\s*분|moisture"),
    "sodium":     ("나트륨",   r"나\s*트\s*륨|sodium|\bna\b"),
}
NUM = r"([0-9]{1,3}(?:[.,][0-9]{1,3})?)"
# 건사료·습식 사료에서 나올 수 있는 범위(급여 상태 %). 벗어나면 OCR 오인식으로 보고 사용자에게 확인을 부탁해요
PLAUSIBLE = {"protein": 80, "fat": 60, "fiber": 30, "ash": 25, "calcium": 5, "phosphorus": 4, "moisture": 85, "sodium": 3}
_KCAL = re.compile(r"([0-9][0-9,.\s]{2,7})\s*k\s*c\s*a\s*l\s*/\s*k\s*g", re.I)
_KCAL_KO = re.compile(r"대\s*사\s*에\s*너\s*지[^0-9]{0,15}([0-9][0-9,.\s]{2,7})", re.I)
KEYWORDS = {
    "omega3": r"오메가\s*-?\s*3|omega\s*-?\s*3|\bEPA\b|\bDHA\b|연어\s*오일|어유|fish\s*oil|salmon\s*oil",
    "mct": r"\bMCT\b|중쇄\s*지방|중쇄\s*트리글리|medium[-\s]*chain",
    "glucosamine": r"글루코사민|glucosamine|콘드로이틴|chondroitin",
}


def _normalize(text: str) -> str:
    t = text.replace("％", "%").replace("：", ":").replace("﹪", "%")
    # OCR이 숫자 사이의 O/o, l/I 를 잘못 읽는 경우 (예: 2O.5 → 20.5, 1l → 11)
    t = re.sub(r"(?<=\d)[Oo](?=\s*[\d.,%])", "0", t)
    t = re.sub(r"(?<=[\d.])[Oo](?=\d)", "0", t)
    t = re.sub(r"(?<=\d)[lI|](?=\s*[\d.,%])", "1", t)
    t = re.sub(r"(?<![A-Za-z0-9])[Oo](?=[.,]\d)", "0", t)       # O.8 → 0.8
    return t


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


CANON = ["protein", "fat", "fiber", "ash", "calcium", "phosphorus", "moisture"]   # 국내 포장의 일반적인 표시 순서
_VAL = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{1,2})?)\s*(%?)")


def _keys_in_order(line: str) -> list[str]:
    """한 줄 안에서 성분 이름이 나오는 순서"""
    hits = []
    for key, (_, name_re) in FIELDS.items():
        m = re.search(name_re, line, re.I)
        if m:
            hits.append((m.start(), key))
    return [k for _, k in sorted(hits)]


def _parse_table(lines: list[str]) -> tuple[dict, list]:
    """표 모양 성분표: 위에 이름 줄, 아래에 숫자 줄.
    예) 조단백질 | 조지방 | 조섬유 | … / 25.0% | 10.0% | 1.3% | …  → 열 순서대로 짝지어요."""
    def vals(line):
        toks = [(m.group(1), m.group(2)) for m in _VAL.finditer(line)]
        return [t for t in toks if t[1] or re.search(r"[.,]", t[0])]   # 소수점이나 %가 있는 것만 값으로

    # 숫자가 4개 이상인 줄을 모두 후보로 (OCR이 한 줄을 두 줄로 나눈 경우도 이어 붙여서 봐요).
    # 원료 목록처럼 숫자가 많은 다른 줄이 있을 수 있어서, %가 많이 붙은 줄부터 차례로 시도해요.
    cands = []
    for i, line in enumerate(lines):
        if len(_keys_in_order(line)) >= 2:
            continue   # '조단백질 26%, 조지방 12%'처럼 이름과 값이 같은 줄에 있으면 표가 아니에요
        a = vals(line)
        if len(a) >= 4:
            cands.append((i, a))
        if i + 1 < len(lines):
            b = vals(lines[i + 1]) if len(_keys_in_order(lines[i + 1])) < 2 else []
            if len(a) >= 2 and len(b) >= 2:
                cands.append((i, a + b))
    cands.sort(key=lambda c: (-sum(1 for _, p in c[1] if p) / len(c[1]), -len(c[1])))
    for row, toks in cands:
        out = _map_row(lines, row, toks)
        if out[0]:
            return out
    return {}, []


def _map_row(lines: list[str], row: int, toks: list) -> tuple[dict, list]:

    # 숫자 줄 위쪽 8줄에서, 한 줄 또는 붙어 있는 두 줄 중 성분 이름을 가장 많이 찾은 순서를 헤더로
    header: list[str] = []
    top = max(0, row - 8)
    # 한 줄짜리 헤더를 먼저 보고, 헤더가 두 줄로 나뉜 경우(서로 다른 성분이 이어지는 경우)만 붙여서 봐요.
    # 한국어 줄 + 영어 줄처럼 같은 성분이 겹치는 두 줄은 붙이지 않아요(순서가 섞여요).
    for j in range(top, row):
        keys = _keys_in_order(lines[j])
        if len(keys) > len(header):
            header = keys
    for j in range(top, row - 1):
        k1, k2 = _keys_in_order(lines[j]), _keys_in_order(lines[j + 1])
        if k1 and k2 and not set(k1) & set(k2) and len(k1) + len(k2) > len(header):
            header = k1 + k2
    n = len(toks)
    guessed = False
    if len(header) < 3:
        # 이름 줄을 거의 못 읽었어도, 값이 딱 7개면 국내 표준 표시 순서로 보고 채워요 (사용자 확인 필요 표시)
        if n != len(CANON):
            return {}, []
        header, guessed = list(CANON), True

    if n == len(header):
        order = header
    elif n > len(header) and [k for k in CANON if k in header] == header:
        # 헤더 몇 칸을 못 읽었으면(예: '수분'을 'FF'로 읽음) 표준 표시 순서로 빈칸을 채워요
        missing = [k for k in CANON if k not in header]
        lo, hi = CANON.index(header[0]), CANON.index(header[-1])
        gaps = [k for k in missing if lo < CANON.index(k) < hi]      # 헤더 사이에 빠진 칸 먼저
        tail = [k for k in missing if CANON.index(k) > hi]            # 그다음 뒤쪽 칸
        head = [k for k in missing if CANON.index(k) < lo]
        need = n - len(header)
        pick = (gaps + tail + head)[:need]
        if len(pick) < need:
            return {}, []
        use = set(header) | set(pick)
        order = [k for k in CANON if k in use]
        if len(order) != n:
            return {}, []
    else:
        return {}, []

    pct_share = sum(1 for _, p in toks if p) / n
    dec_any = any(re.search(r"[.,]", t) for t, _ in toks)
    out, found = {}, []
    for key, (num, pct) in zip(order, toks):
        fixed = False
        # 대부분 %가 붙어 있는데 혼자 없고 소수점 둘째 자리가 7·9면, %를 숫자로 잘못 읽은 것 (0.8% → 0.87)
        if not pct and pct_share >= 0.5 and re.fullmatch(r"\d{1,2}[.,]\d[79]", num):
            num, fixed = num[:-1], True
        # 표 안에 소수점 있는 칸이 있으면 모든 칸이 소수 한 자리로 인쇄된 표로 보고,
        # 소수점이 빠진 2~3자리 숫자를 복원 (25.0% → 250%, 1.3% → 13%, 0.8% → 08%)
        elif dec_any and re.fullmatch(r"\d{2,3}", num):
            num, fixed = num[:-1] + "." + num[-1], True
        out[key] = round(_to_float(num), 3)
        found.append({"key": key, "label": FIELDS[key][0], "value": out[key], "text": num + (pct or ""),
                      "table": True, "corrected": fixed or guessed})
    return out, found


def _parse_basic(t: str) -> tuple[dict, list]:
    """비교 실험용 '기본' 파서 — 처음 만든 방식 그대로.
    이름 뒤 25자 안(줄바꿈 포함)의 첫 숫자를 값으로 봐요. 표 인식·소수점 복원·범위 확인 없음."""
    nutrients, found = {}, []
    for key, (label, name_re) in FIELDS.items():
        m = re.search(rf"(?:{name_re})[^0-9]{{0,25}}?{NUM}\s*%?", t, re.I)
        if m:
            val = _to_float(m.group(1))
            if 0 <= val <= 100:
                nutrients[key] = round(val, 3)
                found.append({"key": key, "label": label, "value": nutrients[key], "text": m.group(0).strip()})
    return nutrients, found


def parse_label(text: str, mode: str = "full") -> dict:
    """OCR 글자 → {'nutrients': {key: 값(%)}, 'kcal_per_kg', 'keywords', 'found': [...], 'suspect': [...]}
    mode='basic' 이면 비교 실험용 기본 파서만 써요."""
    t = _normalize(text)
    nutrients: dict[str, float] = {}
    found = []
    suspect = []
    if mode == "basic":
        nutrients, found = _parse_basic(t)
        return {"nutrients": nutrients, "kcal_per_kg": None, "keywords": [], "found": found, "suspect": []}

    # 1) 표 모양이면 열 순서로 짝짓기
    table, table_found = _parse_table(t.splitlines())
    for f in table_found:
        if f["value"] > PLAUSIBLE[f["key"]]:
            suspect.append({k: f[k] for k in ("key", "label", "value", "text")})
        else:
            nutrients[f["key"]] = f["value"]
            found.append(f)

    # 2) '이름 값%' 이 한 줄에 있거나, 이름 바로 다음 줄에 값이 있는 경우
    for key, (label, name_re) in FIELDS.items():
        if key in nutrients or any(x["key"] == key for x in suspect):
            continue
        pats = [
            re.compile(rf"(?:{name_re})[^0-9\n]{{0,25}}?{NUM}\s*(%|mg\s*/\s*kg|g\s*/\s*kg)?", re.I),
            re.compile(rf"(?:{name_re})[^0-9\n]{{0,25}}\n\s*{NUM}\s*(%)", re.I),
        ]
        for pat in pats:
            m = pat.search(t)
            if not m:
                continue
            val = _to_float(m.group(1))
            unit = (m.group(2) or "%").replace(" ", "").lower()
            if unit == "mg/kg":
                val = val / 10000.0        # mg/kg → %
            elif unit == "g/kg":
                val = val / 10.0           # g/kg → %
            if val > PLAUSIBLE[key]:
                suspect.append({"key": key, "label": label, "value": val, "text": m.group(0).strip()})
            else:
                nutrients[key] = round(val, 3)
                found.append({"key": key, "label": label, "value": nutrients[key], "text": m.group(0).strip()})
            break
    kcal = None
    for rx in (_KCAL, _KCAL_KO):
        m = rx.search(t)
        if m:
            digits = re.sub(r"[^0-9.]", "", m.group(1).replace(",", ""))
            try:
                v = float(digits)
                if 2000 <= v <= 6000:
                    kcal = v
                    break
            except ValueError:
                pass
    kws = [k for k, rx in KEYWORDS.items() if re.search(rx, t, re.I)]
    return {"nutrients": nutrients, "kcal_per_kg": kcal, "keywords": kws, "found": found, "suspect": suspect}


# ---------------------------------------------------------------- 2) 3) 환산
DEFAULT_MOISTURE_DRY = 10.0   # 수분 표시가 없을 때 건사료로 가정
DEFAULT_ASH = 7.0             # 조회분 표시가 없을 때 칼로리 추정용 가정값


def to_dry_matter(value: float, moisture: float) -> float:
    """급여 상태 % → 건물 기준 %.  예) 단백질 26%, 수분 10% → 26/(100-10)*100 = 28.9%"""
    return value / (100.0 - moisture) * 100.0


def estimate_kcal(n: dict) -> float:
    """수정 Atwater: ME(kcal/kg) = 10 × (3.5×단백질 + 8.5×지방 + 3.5×NFE)
    NFE(가용 탄수화물) = 100 − 단백질 − 지방 − 섬유 − 회분 − 수분"""
    p, f = n.get("protein", 0.0), n.get("fat", 0.0)
    nfe = 100.0 - p - f - n.get("fiber", 0.0) - n.get("ash", DEFAULT_ASH) - n.get("moisture", DEFAULT_MOISTURE_DRY)
    return 10.0 * (3.5 * p + 8.5 * f + 3.5 * max(nfe, 0.0))


def per_1000kcal(value_pct: float, kcal_per_kg: float) -> float:
    """급여 상태 % → g/1000kcal.  1kg 안에 value×10 g, 그 1kg이 kcal_per_kg 칼로리"""
    return value_pct * 10.0 / kcal_per_kg * 1000.0


# ---------------------------------------------------------------- 4) 평가
def _check(code, title, status, message, source, value=None):
    name, url = SOURCES[source]
    return {"code": code, "title": title, "status": status, "message": message,
            "value": value, "source": name, "source_url": url}


def pet_flags(condition: Optional[str], bcs: Optional[int], ccdr: Optional[int]) -> dict:
    c = (condition or "").lower()
    return {
        "kidney": bool(re.search(r"신장|신부전|콩팥|kidney|ckd|renal", c)),
        "heart": bool(re.search(r"심장|이첨판|판막|mmvd|heart|심부전", c)),
        "joint": bool(re.search(r"관절|슬개골|탈구|고관절|디스크|arthritis", c)),
        "obese": bcs is not None and bcs >= 6,
        "cognitive": ccdr is not None and ccdr >= 40,
    }


def evaluate(nutrients: dict, kcal_per_kg: Optional[float] = None, keywords: list[str] | None = None,
             condition: Optional[str] = None, bcs: Optional[int] = None, ccdr: Optional[int] = None) -> dict:
    n = {k: float(v) for k, v in nutrients.items() if v is not None}
    keywords = keywords or []
    notes = []
    moisture = n.get("moisture")
    if moisture is None:
        moisture = DEFAULT_MOISTURE_DRY
        notes.append(f"수분 표시가 없어 건사료 기준 {DEFAULT_MOISTURE_DRY:.0f}%로 가정했어요.")
    kcal_est = kcal_per_kg is None
    kcal = kcal_per_kg or estimate_kcal({**n, "moisture": moisture})
    if kcal_est:
        notes.append("칼로리 표시가 없어 성분으로 추정했어요 (수정 Atwater).")
    dm = {k: round(to_dry_matter(v, moisture), 2) for k, v in n.items() if k != "moisture"}

    checks = []
    # --- AAFCO 성견 기준 (모든 성견·노령견 공통. AAFCO에는 '노령견' 별도 기준이 없어요)
    if "protein" in dm:
        ok = dm["protein"] >= 18.0
        checks.append(_check("protein_min", "단백질", "ok" if ok else "bad",
                             f"건물 기준 {dm['protein']:.1f}% (기준 18% 이상)" + ("" if ok else " — 부족해요"), "aafco", dm["protein"]))
    if "fat" in dm:
        ok = dm["fat"] >= 5.5
        checks.append(_check("fat_min", "지방", "ok" if ok else "bad",
                             f"건물 기준 {dm['fat']:.1f}% (기준 5.5% 이상)" + ("" if ok else " — 부족해요"), "aafco", dm["fat"]))
    if "calcium" in dm:
        v = dm["calcium"]; ok = 0.5 <= v <= 2.5
        checks.append(_check("calcium", "칼슘", "ok" if ok else "bad",
                             f"건물 기준 {v:.2f}% (기준 0.5~2.5%)", "aafco", v))
    if "phosphorus" in dm:
        v = dm["phosphorus"]; ok = 0.4 <= v <= 1.6
        checks.append(_check("phosphorus", "인", "ok" if ok else "bad",
                             f"건물 기준 {v:.2f}% (기준 0.4~1.6%)", "aafco", v))
    if "calcium" in dm and "phosphorus" in dm and dm["phosphorus"] > 0:
        r = dm["calcium"] / dm["phosphorus"]; ok = 1.0 <= r <= 2.0
        checks.append(_check("ca_p_ratio", "칼슘:인 비율", "ok" if ok else "warn",
                             f"{r:.2f} : 1 (기준 1:1 ~ 2:1)", "aafco", round(r, 2)))

    # --- 우리 개 상태에 맞춘 평가
    flags = pet_flags(condition, bcs, ccdr)
    if flags["kidney"]:
        if "phosphorus" in n:
            g = per_1000kcal(n["phosphorus"], kcal)
            if g <= 1.2:
                st, msg = "ok", f"인 {g:.2f} g/1000kcal — 신장 처방식 범위(0.4~1.2) 안이에요"
            else:
                st, msg = "bad", f"인 {g:.2f} g/1000kcal — 신장 처방식 범위(0.4~1.2)보다 높아요. 수의사와 상의해 보세요"
            checks.append(_check("kidney_p", "신장 관리 · 인", st, msg, "ckd", round(g, 2)))
        else:
            checks.append(_check("kidney_p", "신장 관리 · 인", "info", "인 함량 표시를 찾지 못했어요. 신장 관리 중이면 꼭 확인해 주세요", "ckd"))
    if flags["heart"]:
        if "sodium" in n:
            mg100 = per_1000kcal(n["sodium"], kcal) * 100.0   # g/1000kcal → mg/100kcal
            st = "ok" if mg100 <= 99 else "bad"
            checks.append(_check("heart_na", "심장 관리 · 나트륨", st,
                                 f"나트륨 {mg100:.0f} mg/100kcal (B2 단계 80~99, C 단계 50~79 권장)", "heart", round(mg100)))
        else:
            checks.append(_check("heart_na", "심장 관리 · 나트륨", "info",
                                 "나트륨 표시가 없어요. 심장 질환이 있으면 제조사에 나트륨 함량을 문의해 보세요", "heart"))
    if flags["joint"]:
        has = "omega3" in keywords
        checks.append(_check("joint_omega3", "관절 · 오메가3", "ok" if has else "info",
                             "오메가3(EPA·DHA) 원료가 들어 있어요" if has else "오메가3(EPA·DHA) 원료를 찾지 못했어요. 관절염엔 오메가3가 도움이 된다고 알려져 있어요",
                             "aaha"))
    if flags["cognitive"]:
        has = "mct" in keywords
        checks.append(_check("cognitive_mct", "인지기능 · MCT", "ok" if has else "info",
                             "MCT(중쇄지방산) 원료가 들어 있어요" if has else "MCT(중쇄지방산) 원료를 찾지 못했어요. 인지기능장애엔 MCT가 권장돼요",
                             "aaha"))
    if flags["obese"]:
        checks.append(_check("obese_kcal", "비만 관리 · 칼로리", "info",
                             f"1kg당 약 {kcal:,.0f} kcal{' (추정)' if kcal_est else ''}. 체형 점수가 높으니 급여량을 수의사와 정해 주세요",
                             "atwater", round(kcal)))

    bad = sum(c["status"] == "bad" for c in checks)
    warn = sum(c["status"] in ("warn", "info") for c in checks)
    if not checks:
        verdict = ("unknown", "성분을 충분히 읽지 못했어요. 숫자를 직접 확인해 주세요")
    elif bad:
        names = [c["title"] for c in checks if c["status"] == "bad"]
        verdict = ("bad", f"{', '.join(names[:2])}{' 외' if len(names) > 2 else ''} 확인이 필요해요")
    elif warn:
        verdict = ("warn", "기본 기준은 맞지만 확인할 점이 있어요")
    else:
        verdict = ("ok", "기준에 잘 맞는 사료예요")
    return {
        "verdict": {"level": verdict[0], "message": verdict[1]},
        "dry_matter": dm, "moisture": moisture,
        "kcal_per_kg": round(kcal), "kcal_estimated": kcal_est,
        "flags": flags, "checks": checks, "notes": notes,
        "disclaimer": "포장 표시값(보증값)을 기준으로 한 참고용 분석이에요. 질환이 있다면 사료 변경 전 수의사와 상의해 주세요.",
    }
