"""
Nemotron-Personas-Korea 데이터셋 로더/매퍼

Zep 그래프에서 파생한 LLM 생성 퍼소나 대신, NVIDIA의 통계 기반 한국인 합성 퍼소나
(nvidia/Nemotron-Personas-Korea, 100만 명, CC BY 4.0)를 OASIS 에이전트 프로필로 매핑한다.

데이터셋 특징:
- name 컬럼이 없음 → persona 텍스트 첫머리 "{이름} 씨는…" 에서 이름을 추출
- sex(남자/여자), age, occupation, district/province, hobbies_and_interests_list 등 26개 컬럼
- persona(짧은 한 줄) + professional/family/cultural 등 상세 퍼소나 텍스트
"""

import ast
import json
import os
import random
import re
import threading
from typing import Any, Dict, Iterator, List, Optional

from ..utils.logger import get_logger

logger = get_logger("mirofish.nemotron")

NEMOTRON_DATASET = os.environ.get("NEMOTRON_DATASET", "nvidia/Nemotron-Personas-Korea")

# 로컬 사전전처리 풀(jsonl). scripts/prepare_nemotron.py 가 미리 생성.
# 있으면 스트리밍/다운로드 없이 이 파일만 로드해서 샘플링(오프라인·즉시).
POOL_PATH = os.environ.get("NEMOTRON_POOL_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "nemotron_profiles.jsonl"
)
_POOL_CACHE: Optional[List[Dict[str, Any]]] = None  # 프로세스 내 1회 로드 캐시
_POOL_LOCK = threading.Lock()                       # 전체 100만 풀 로드 동시성 보호(중복 로드 방지)

# persona 첫머리에서 이름 추출: "전기태 씨는...", "최은지 씨는..."
_NAME_RE = re.compile(r"^\s*([가-힣]{2,5})\s*(?:씨|님)")

# 이름 추출 실패 시 폴백용 (드물게 persona가 이름으로 시작 안 할 때)
_FALLBACK_SURNAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]
_FALLBACK_GIVEN = ["민준", "서연", "지우", "하은", "도윤", "예은", "시우", "지호", "수아", "은우"]


def _fallback_name(seed_uuid: str) -> str:
    rnd = random.Random(seed_uuid)  # uuid 기반 → 결정적
    return rnd.choice(_FALLBACK_SURNAMES) + rnd.choice(_FALLBACK_GIVEN)


def extract_name(row: Dict[str, Any]) -> str:
    for field in ("persona", "professional_persona", "family_persona", "cultural_background"):
        text = str(row.get(field) or "")
        m = _NAME_RE.match(text)
        if m:
            return m.group(1)
    return _fallback_name(str(row.get("uuid", "")))


def _parse_list(value: Any) -> List[str]:
    """문자열화된 파이썬 리스트('[...]')를 실제 리스트로 파싱."""
    if isinstance(value, list):
        return [str(x) for x in value]
    s = str(value or "").strip()
    if not s:
        return []
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, (list, tuple)):
            return [str(x) for x in parsed]
    except (ValueError, SyntaxError):
        pass
    return [s]


def _gender_en(sex: str) -> str:
    m = {"남자": "male", "남": "male", "여자": "female", "여": "female"}
    return m.get(str(sex or "").strip(), "other")


def row_to_profile_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """Nemotron 행 → OasisAgentProfile 필드 dict. 26개 컬럼을 컬럼별로 각각 매핑.

    - persona: 인물 서사 계열 컬럼(persona/professional/family/sports/arts/travel/culinary
      /cultural_background/career + 스킬·취미 산문)을 이어붙인 하나의 인물 묘사
    - 인구통계·리스트 컬럼은 각각 별도 필드로 분리(병합하지 않음)
    """
    def v(k):
        return str(row.get(k) or "").strip()

    name = extract_name(row)

    # 데이터셋 컬럼 순서대로 이어붙임 (산문형 컬럼만)
    _persona_keys = [
        "professional_persona", "sports_persona", "arts_persona", "travel_persona",
        "culinary_persona", "family_persona", "persona", "cultural_background",
        "skills_and_expertise", "hobbies_and_interests", "career_goals_and_ambitions",
    ]
    full_persona = " ".join(p for p in (v(k) for k in _persona_keys) if p)

    return {
        "name": name,
        "bio": v("persona"),                                   # 짧은 한 줄 소개
        "persona": full_persona or v("persona"),
        "age": int(row["age"]) if v("age").isdigit() else 30,
        "gender": _gender_en(row.get("sex")),
        "country": v("country") or "대한민국",
        "profession": v("occupation"),
        # ↓ 각 컬럼을 개별 필드로 (병합 안 함)
        "interested_topics": _parse_list(row.get("hobbies_and_interests_list"))[:12],  # 취미 리스트
        "skills": _parse_list(row.get("skills_and_expertise_list"))[:12],              # 스킬 리스트
        "province": v("province"),
        "district": v("district"),
        "education_level": v("education_level"),
        "bachelors_field": v("bachelors_field"),
        "marital_status": v("marital_status"),
        "military_status": v("military_status"),
        "family_type": v("family_type"),
        "housing_type": v("housing_type"),
    }


def sample_rows(
    count: int,
    seed: Optional[int] = 42,
    streaming: bool = True,
    shuffle_buffer: int = 10000,
) -> Iterator[Dict[str, Any]]:
    """Nemotron-Personas-Korea에서 count개 행을 랜덤 샘플링해 yield.

    streaming=True(기본): 4GB 전체 다운로드 없이 셔플 버퍼로 샘플링.
    """
    from datasets import load_dataset

    logger.info(f"Nemotron 데이터셋 로드 (streaming={streaming}, count={count})")
    if streaming:
        ds = load_dataset(NEMOTRON_DATASET, split="train", streaming=True)
        ds = ds.shuffle(seed=seed, buffer_size=shuffle_buffer)
        n = 0
        for row in ds:
            yield row
            n += 1
            if n >= count:
                break
    else:
        ds = load_dataset(NEMOTRON_DATASET, split="train")
        ds = ds.shuffle(seed=seed)
        for i in range(min(count, len(ds))):
            yield ds[i]


def iter_all_rows(streaming: bool = True) -> Iterator[Dict[str, Any]]:
    """데이터셋 전체 행을 순서대로 yield(샘플링/셔플 없음).

    전체 100만 명 풀을 사전전처리할 때 사용. count 제한도 셔플 버퍼도 없다.
    """
    from datasets import load_dataset

    logger.info(f"Nemotron 전체 로드 시작 (streaming={streaming})")
    ds = load_dataset(NEMOTRON_DATASET, split="train", streaming=streaming)
    for row in ds:
        yield row


def _load_pool() -> Optional[List[Dict[str, Any]]]:
    """로컬 사전전처리 풀(jsonl)을 1회 로드해 캐시. 없으면 None."""
    global _POOL_CACHE
    if _POOL_CACHE is not None:
        return _POOL_CACHE
    if not os.path.exists(POOL_PATH):
        return None
    # 전체 100만 풀(≈4.6GB, 로드 ~24s)은 1회만 로드. 동시 요청/워밍 스레드가 겹쳐도
    # 락으로 중복 로드를 막는다(락 안에서 재확인).
    with _POOL_LOCK:
        if _POOL_CACHE is not None:
            return _POOL_CACHE
        try:
            with open(POOL_PATH, encoding="utf-8") as f:
                cache = [json.loads(line) for line in f if line.strip()]
            _POOL_CACHE = cache
            logger.info(f"Nemotron 로컬 풀 로드: {len(_POOL_CACHE)}명 ({POOL_PATH})")
            return _POOL_CACHE
        except Exception as e:
            logger.warning(f"Nemotron 로컬 풀 로드 실패({e}) → 스트리밍 폴백")
            return None


def warm_pool_async() -> None:
    """백엔드 기동 시 백그라운드로 풀을 미리 로드(데우기).

    완료 전 필터 UI 첫 호출이 24초 멈추는 걸 방지. 풀 파일이 없으면(아직 생성 중) 조용히 종료.
    """
    if _POOL_CACHE is not None or not os.path.exists(POOL_PATH):
        return

    def _run():
        try:
            _load_pool()
        except Exception:
            pass
    threading.Thread(target=_run, name="nemotron-pool-warm", daemon=True).start()


# 조건 필터에 노출할 범주형(categorical) 필드. GUI가 이 목록으로 선택지를 구성.
# (district/bachelors_field 등 고카디널리티 필드는 제외 — 선택지가 너무 많아짐)
CATEGORICAL_FILTER_FIELDS = [
    "gender", "province", "education_level",
    "marital_status", "military_status", "family_type", "housing_type",
]


def _matches(profile: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
    """프로필 dict가 필터 조건을 모두 만족하는지(AND) 판정.

    filters 형식:
      - 범주형: {"gender": ["female"], "province": ["서울특별시", "경기도"]}  (필드 내 OR)
      - 나이 범위: {"age": {"min": 20, "max": 39}}
    빈 조건(None/""/[]/{})은 무시. 리스트형 프로필 값(interested_topics 등)은 교집합 여부로 판정.
    """
    if not filters:
        return True
    for key, cond in filters.items():
        if cond is None or cond == "" or cond == [] or cond == {}:
            continue
        if key == "age":
            age = profile.get("age")
            if age is None:
                return False
            lo = cond.get("min") if isinstance(cond, dict) else None
            hi = cond.get("max") if isinstance(cond, dict) else None
            if lo is not None and age < lo:
                return False
            if hi is not None and age > hi:
                return False
            continue
        val = profile.get(key)
        allowed = {str(a) for a in (cond if isinstance(cond, list) else [cond])}
        if isinstance(val, list):
            if not ({str(x) for x in val} & allowed):
                return False
        else:
            if str(val) not in allowed:
                return False
    return True


def pool_facets() -> Dict[str, Any]:
    """로컬 풀에서 필터 가능한 필드별 선택지(값+개수)를 집계해 반환.

    GUI가 '조건 필터' UI를 구성하는 데 사용. 풀이 없으면 available=False(그 경우
    GUI는 전체 랜덤만 노출). 범주형은 빈도 내림차순, 나이는 min/max 범위.
    """
    pool = _load_pool()
    if not pool:
        return {"available": False, "total": 0, "fields": {}}

    from collections import Counter
    fields: Dict[str, Any] = {}
    for field_name in CATEGORICAL_FILTER_FIELDS:
        counter: Counter = Counter()
        for p in pool:
            v = p.get(field_name)
            if v is None or v == "":
                continue
            counter[str(v)] += 1
        if counter:
            fields[field_name] = {
                "type": "categorical",
                "values": [{"value": k, "count": n} for k, n in counter.most_common()],
            }

    ages = [p.get("age") for p in pool if isinstance(p.get("age"), int)]
    if ages:
        fields["age"] = {"type": "range", "min": min(ages), "max": max(ages)}

    return {"available": True, "total": len(pool), "fields": fields}


def count_matching(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """필터 조건을 만족하는 로컬 풀 표본 수를 반환(GUI 실시간 미리보기용).

    반환: {"available": bool, "total": 전체수, "matched": 조건만족수}
    풀이 없으면 available=False(전체 랜덤만 가능).
    """
    pool = _load_pool()
    if not pool:
        return {"available": False, "total": 0, "matched": 0}
    if not filters:
        return {"available": True, "total": len(pool), "matched": len(pool)}
    matched = sum(1 for p in pool if _matches(p, filters))
    return {"available": True, "total": len(pool), "matched": matched}


def sample_profiles(
    count: int,
    seed: Optional[int] = 42,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """count명 분의 '프로필 dict'를 반환.

    filters가 주어지면 조건을 만족하는 후보 중에서만 랜덤 샘플링(필터 후 랜덤).
    조건을 만족하는 후보가 count보다 적으면 만족하는 전부를 반환한다.

    1순위: 로컬 사전전처리 풀 → 다운로드/네트워크 없이 즉시.
    폴백: 데이터셋 스트리밍 → row_to_profile_dict 매핑(필터 시 넉넉히 스캔).
    """
    pool = _load_pool()
    if pool:
        rnd = random.Random(seed)
        candidates = [p for p in pool if _matches(p, filters)] if filters else pool
        idxs = list(range(len(candidates)))
        rnd.shuffle(idxs)
        picked = [candidates[i] for i in idxs[:count]]
        if filters:
            logger.info(f"Nemotron 필터 샘플링: 조건만족 {len(candidates)}명 중 {len(picked)}명 선택")
        return picked

    # 폴백: 스트리밍 후 매핑. 필터가 있으면 조건 만족분이 count에 찰 때까지 넉넉히 스캔.
    if filters:
        out: List[Dict[str, Any]] = []
        max_scan = max(count * 200, 20000)
        for r in sample_rows(max_scan, seed=seed, streaming=True):
            d = row_to_profile_dict(r)
            if _matches(d, filters):
                out.append(d)
                if len(out) >= count:
                    break
        return out
    return [row_to_profile_dict(r) for r in sample_rows(count, seed=seed, streaming=True)]
