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
    # OCR이 자주 틀리는 글자도 같이 찾아요 (조→소, 단백→다백·단맥, 지방→지망, 회분→희분, 칼슘→칼슴·갈숨·칼숍 …)
    "protein":    ("조단백질", r"[조소]\s*[단다]\s*[백맥]\s*질?|crude\s*protein|protein"),
    "fat":        ("조지방",   r"[조소]\s*지\s*[방망]|crude\s*fat|\bfat\b"),
    "fiber":      ("조섬유",   r"[조소]\s*섬\s*유|crude\s*fib(?:er|re)|fib(?:er|re)"),
    "ash":        ("조회분",   r"[조소]\s*[회희]\s*[분본]|crude\s*ash|\bash\b"),
    "calcium":    ("칼슘",     r"(?<![가-힣])[칼갈]\s*[슘슴숨숍숌]|ca[lk]cium|\bca\b"),
    "phosphorus": ("인",       r"(?<![가-힣])인(?![가-힣])|phosphorus|\bp\b"),
    "moisture":   ("수분",     r"수\s*분|moisture"),
    "sodium":     ("나트륨",   r"나\s*트\s*륨|sodium|\bna\b"),
}
# 비교 실험용 '처음 버전' 파서가 쓰던 이름 패턴 (정확도 비교를 공정하게 하려고 그대로 둬요)
BASIC_FIELDS = {
    "protein": r"조\s*단\s*백\s*질?|crude\s*protein|protein",
    "fat": r"조\s*지\s*방|crude\s*fat|fat",
    "fiber": r"조\s*섬\s*유|crude\s*fib(?:er|re)|fib(?:er|re)",
    "ash": r"조\s*회\s*분|crude\s*ash|ash",
    "calcium": r"칼\s*슘|calcium|\bca\b",
    "phosphorus": r"(?<![가-힣])인(?![가-힣])|phosphorus|\bp\b",
    "moisture": r"수\s*분|moisture",
    "sodium": r"나\s*트\s*륨|sodium|\bna\b",
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


def _normalize(text: str, basic: bool = False) -> str:
    t = text.replace("％", "%").replace("：", ":").replace("﹪", "%")
    # OCR이 숫자 사이의 O/o, l/I 를 잘못 읽는 경우 (예: 2O.5 → 20.5, 1l → 11)
    t = re.sub(r"(?<=\d)[Oo](?=\s*[\d.,%])", "0", t)
    t = re.sub(r"(?<=[\d.])[Oo](?=\d)", "0", t)
    t = re.sub(r"(?<=\d)[lI|](?=\s*[\d.,%])", "1", t)
    t = re.sub(r"(?<![A-Za-z0-9])[Oo](?=[.,]\d)", "0", t)       # O.8 → 0.8
    if basic:
        return t   # 비교 실험용 '처음 버전'은 여기까지만
    t = re.sub(r"(\d[.,]\d)96(?=\s*(?:이상|이하|min|max|$))", r"\1%", t, flags=re.M)   # 0.5% → 0.596
    t = re.sub(r"\(\d{3,8}\)", " ", t)   # 괄호 속 영어를 숫자로 잘못 읽은 것 (예: '칼슘 (Calcium)' → '(09000)')
    return t


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


CANON = ["protein", "fat", "fiber", "ash", "calcium", "phosphorus", "moisture"]   # 국내 포장의 일반적인 표시 순서
MIN_KEYS = ["protein", "fat", "calcium", "phosphorus"]    # 포장에 '이상(min)'으로 표시되는 성분
MAX_KEYS = ["fiber", "ash", "moisture"]                   # '이하(max)'로 표시되는 성분
_VAL = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{1,2})?)(?!\d)\s*(%?)")
_MIN = re.compile(r"이\s*상|\bmin|more", re.I)
_MAX = re.compile(r"이\s*하|\bmax|less", re.I)


def _keys_in_order(line: str) -> list[str]:
    """한 줄 안에서 성분 이름이 나오는 순서"""
    hits = []
    for key, (_, name_re) in FIELDS.items():
        m = re.search(name_re, line, re.I)
        if m:
            hits.append((m.start(), key))
    return [k for _, k in sorted(hits)]


def _tokens(line: str) -> list[dict]:
    """한 줄의 값 칸들: 숫자 · % 여부 · 이상/이하 표시 · 줄 안 위치"""
    line = re.sub(r"\d[\d,.\s]*k\s*c\s*a\s*l\S*", " ", line, flags=re.I)   # 3,200kcal/kg 같은 칼로리 칸은 빼요
    ms = [m for m in _VAL.finditer(line) if m.group(2) or re.search(r"[.,]", m.group(1))]
    out = []
    for i, m in enumerate(ms):
        tail = line[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(line)]
        mk = "min" if _MIN.search(tail) else "max" if _MAX.search(tail) else None
        out.append({"num": m.group(1), "pct": m.group(2), "mk": mk, "x": m.start()})
    return out


def _cells(line: str) -> list[tuple[int, Optional[str]]]:
    """헤더 줄을 칸으로 나눠요 (|나 넓은 공백 기준). 글자가 없는 칸은 버리고, 못 읽은 칸은 None"""
    out = []
    for m in re.finditer(r"[^\s|｜](?:[^\s|｜]| (?=[^\s|｜]))*", line):   # 한 칸 띄어쓰기는 같은 칸
        part = m.group(0)
        if not re.search(r"[가-힣A-Za-z]", part):
            continue
        keys = _keys_in_order(part)
        out.append((m.start(), keys[0] if keys else None))
    return out


def _fits(key: str, value: float, mk: Optional[str]) -> bool:
    """못 읽은 칸에 어떤 성분이 올 수 있는지: 이상/이하 표시와 값의 크기로 판단"""
    if mk == "min" and key not in MIN_KEYS or mk == "max" and key not in MAX_KEYS:
        return False
    if key in ("calcium", "phosphorus"):
        return value <= 3
    if key == "protein":
        return value >= 10
    return 0.3 <= value <= PLAUSIBLE[key]


def _num(tok: dict) -> float:
    return _to_float(tok["num"])


def _fix_tokens(toks: list[dict], keys: list[str]) -> list[tuple[str, float, bool]]:
    """OCR이 자주 틀리는 숫자를 바로잡아요. (key, 값, 보정했는지)"""
    n = len(toks)
    pct_share = sum(1 for t in toks if t["pct"]) / n
    dec_any = any(re.search(r"[.,]", t["num"]) for t in toks)
    one_dec = sum(1 for t in toks if re.fullmatch(r"\d+[.,]\d", t["num"]))
    out = []
    for key, tok in zip(keys, toks):
        num, fixed = tok["num"], False
        # %를 숫자 9·7로 읽은 경우 (0.8% → 0.87, 29.0% → 29.09%)
        if re.fullmatch(r"\d{1,2}[.,]\d[79]", num) and (not tok["pct"] and pct_share >= 0.5 or tok["pct"] and one_dec >= 2):
            num, fixed = num[:-1], True
        # 소수점이 빠진 숫자 (25.0% → 250%, 0.8% → 08%, 1.3% → 13%): 3자리이거나, 0으로 시작하거나,
        # 칼슘·인·조섬유처럼 작은 값인데 2자리로 읽힌 경우만 (22%·12%처럼 원래 정수인 칸은 그대로)
        elif dec_any and (re.fullmatch(r"\d{3}", num) or re.fullmatch(r"0\d", num)
                          or re.fullmatch(r"\d{2}", num) and (key in ("calcium", "phosphorus", "fiber") or float(num) > PLAUSIBLE[key])):
            num, fixed = num[:-1] + "." + num[-1], True
        v = _to_float(num)
        # 칸 테두리를 1로 읽은 경우 (11.0% → 111.0%)
        if v > PLAUSIBLE[key] and num.startswith("1") and _to_float(num[1:]) <= PLAUSIBLE[key]:
            v, fixed = _to_float(num[1:]), True
        out.append((key, round(v, 3), fixed))
    return out


def _header_order(lines: list[str], row: int, toks: list[dict]) -> Optional[list[Optional[str]]]:
    """숫자 줄 위쪽에서 가까운 헤더 줄부터 보고, 값 칸마다 성분 이름(못 읽으면 None)을 정해요"""
    n = len(toks)
    cands = []
    for j in range(row - 1, max(-1, row - 9), -1):
        cands.append(lines[j])
        if j + 1 < row:
            k1, k2 = _keys_in_order(lines[j]), _keys_in_order(lines[j + 1])
            if k1 and k2 and not set(k1) & set(k2):   # 헤더가 두 줄로 나뉜 경우
                cands.append(lines[j] + "  " + lines[j + 1])
    for line in cands:
        keys = _keys_in_order(line)
        cells = _cells(line)
        if _tokens(line):
            continue                                  # 숫자가 있는 줄(값 줄·막대그래프 등)은 헤더가 아니에요
        if len(cells) == n and sum(1 for _, k in cells if k) >= max(2, n - 2) and len({k for _, k in cells if k}) == sum(1 for _, k in cells if k):
            return [k for _, k in cells]
        if len(keys) == n and n >= 2:
            return keys
        if len(keys) >= 3 and n > len(keys) and [k for k in CANON if k in keys] == keys:
            # 헤더 몇 칸을 못 읽었으면 표준 표시 순서로 빈칸을 채워요
            missing = [k for k in CANON if k not in keys]
            lo, hi = CANON.index(keys[0]), CANON.index(keys[-1])
            pick = ([k for k in missing if lo < CANON.index(k) < hi] + [k for k in missing if CANON.index(k) > hi]
                    + [k for k in missing if CANON.index(k) < lo])[: n - len(keys)]
            if len(pick) == n - len(keys):
                use = set(keys) | set(pick)
                return [k for k in CANON if k in use]
        known = [(x, k) for x, k in cells if k]
        if len(cells) >= n and len(known) >= 2:
            # 칸 수가 안 맞으면 글자 위치로 가장 가까운 칸에 짝지어요
            idx = [min(range(len(cells)), key=lambda c: abs(cells[c][0] - t["x"])) for t in toks]
            if len(set(idx)) == n:
                return [cells[i][1] for i in idx]
    return None


def _assign_by_marker(toks: list[dict]) -> Optional[list[str]]:
    """헤더가 없을 때: '이상' 칸은 단백질·지방·칼슘·인, '이하' 칸은 섬유·회분·수분 순서로.
    칼슘·인은 보통 칼슘이 더 많아서(칼슘:인 1~2:1) 큰 값을 칼슘으로 봐요"""
    mins = [t for t in toks if t["mk"] == "min"]
    maxs = [t for t in toks if t["mk"] == "max"]
    if len(mins) + len(maxs) != len(toks) or len(mins) > 4 or len(maxs) > 3 or len(toks) < 3:
        return None
    keys = {}
    # '이상' 칸은 보통 단백질 → 지방 → 칼슘·인 순서로 적혀 있어요
    first, rest = mins[:2], mins[2:]
    if len(first) == 2 and _num(first[0]) < 10:
        return None
    for k, t in zip(["protein", "fat"], first):
        keys[id(t)] = k
    for k, t in zip(["calcium", "phosphorus"], sorted(rest, key=_num, reverse=True)):
        keys[id(t)] = k
    for k, t in zip(MAX_KEYS, maxs):
        keys[id(t)] = k
    if len(keys) != len(toks):
        return None
    return [keys[id(t)] for t in toks]


def _parse_table(lines: list[str]) -> tuple[dict, list]:
    """표 모양 성분표: 이름 줄 아래에 숫자 줄. 카드형처럼 표가 두 덩어리로 나뉜 경우도 합쳐요.
    헤더를 못 읽은 줄은 '이상/이하' 표시나 국내 표준 표시 순서로 채우고 '확인 필요'로 표시해요."""
    rows = []
    for i, line in enumerate(lines):
        if _keys_in_order(line):
            continue   # '조단백질 26%, 조지방 12%'처럼 이름과 값이 같은 줄에 있으면 표가 아니에요 (아래 줄 단위 파서가 처리)
        toks = _tokens(line)
        if len(toks) >= 2 and sum(1 for t in toks if t["pct"]) * 2 >= len(toks):
            if i + 1 < len(lines) and any(t["mk"] is None for t in toks):
                below = re.findall(r"이\s*[상하]|\bmin\b|\bmax\b", lines[i + 1], re.I)
                if len(below) == len(toks) and not _tokens(lines[i + 1]):   # 값 아래 줄에 '이상 이상 이하 …'
                    for t, w in zip(toks, below):
                        t["mk"] = "max" if re.search(r"하|max", w, re.I) else "min"
            rows.append((i, toks))

    out, found = {}, []

    def take(pairs, guessed):
        for key, v, fixed in pairs:
            if key and key not in out:
                out[key] = v
                found.append({"key": key, "label": FIELDS[key][0], "value": v, "text": str(v),
                              "table": True, "corrected": fixed or guessed})

    loose = []   # 헤더 없이 이어지는 숫자 줄들
    for i, toks in rows:
        order = _header_order(lines, i, toks)
        if order and any(k and (t["mk"] == "min" and k in MAX_KEYS or t["mk"] == "max" and k in MIN_KEYS)
                         for k, t in zip(order, toks)):
            order = None   # 헤더로 짝지은 결과가 '이상/이하' 표시와 안 맞으면 잘못 짝지은 거예요
        if order and sum(1 for k in order if k) >= 2:
            # 못 읽은 칸(None)은 아직 안 나온 성분 중 이상/이하·크기가 맞는 것으로
            used = set(out) | {k for k in order if k}
            filled, guessed_any = [], False
            for k, t in zip(order, toks):
                if k is None:
                    k = next((c for c in CANON if c not in used and _fits(c, _num(t), t["mk"])), None)
                    if k:
                        used.add(k); guessed_any = True
                filled.append(k)
            keep = [(k, t) for k, t in zip(filled, toks) if k]
            fixed = _fix_tokens([t for _, t in keep], [k for k, _ in keep])
            take([(k, v, f or (guessed_any and order[idx] is None)) for idx, (k, v, f) in
                  zip([filled.index(k) for k, _ in keep], fixed)], False)
        else:
            loose.append((i, toks))

    # 헤더 없는 숫자 줄: 붙어 있는 줄끼리 묶어서
    groups, cur = [], []
    for i, toks in loose:
        if cur and i - cur[-1][0] > 2:
            groups.append(cur); cur = []
        cur.append((i, toks))
    if cur:
        groups.append(cur)
    for g in groups:
        toks = [t for _, ts in g for t in ts]
        keys = _assign_by_marker(toks)
        if keys is None and len(toks) == len(CANON):
            keys = list(CANON)
        if keys:
            take(_fix_tokens(toks, keys), True)
    return out, found


def _parse_basic(t: str) -> tuple[dict, list]:
    """비교 실험용 '기본' 파서 — 처음 만든 방식 그대로.
    이름 뒤 25자 안(줄바꿈 포함)의 첫 숫자를 값으로 봐요. 표 인식·소수점 복원·범위 확인 없음."""
    nutrients, found = {}, []
    for key, name_re in BASIC_FIELDS.items():
        label = FIELDS[key][0]
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
    t = _normalize(text, basic=(mode == "basic"))
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
            # 이름과 값 사이에 'Crude Fat   more than' 같은 글자가 길게 끼어도 같은 줄이면 찾아요
            re.compile(rf"(?:{name_re})([^0-9\n]{{0,60}}?){NUM}\s*(%|mg\s*/\s*kg|g\s*/\s*kg)?", re.I),
            re.compile(rf"(?:{name_re})([^0-9\n]{{0,25}}\n\s*){NUM}\s*(%)", re.I),
        ]
        for pat in pats:
            # 사이에 다른 성분 이름이 끼면 안 돼요 ('조단백질 Crude Protein'처럼 같은 성분의 영어 이름은 괜찮아요)
            # '비타민4'처럼 %도 소수점도 없는 숫자는 성분 값이 아니에요
            m = next((m for m in pat.finditer(t) if set(_keys_in_order(m.group(1))) <= {key}
                      and (m.group(3) or re.search(r"[.,]", m.group(2)))), None)
            if not m:
                continue
            raw = m.group(2)
            val = _to_float(raw)
            unit = (m.group(3) or "%").replace(" ", "").lower()
            if unit == "mg/kg":
                val = val / 10000.0        # mg/kg → %
            elif unit == "g/kg":
                val = val / 10.0           # g/kg → %
            elif val > PLAUSIBLE[key] and re.fullmatch(r"\d{2,3}", raw) or re.fullmatch(r"0\d", raw):
                val = _to_float(raw[:-1] + "." + raw[-1])   # 소수점이 빠진 숫자 (8.0% → 80%, 0.7% → 07%)
            if val == 0:
                break                      # 0%는 잘못 읽은 값
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
