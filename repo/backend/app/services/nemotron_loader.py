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
import os
import random
import re
from typing import Any, Dict, Iterator, List, Optional

from ..utils.logger import get_logger

logger = get_logger("mirofish.nemotron")

NEMOTRON_DATASET = os.environ.get("NEMOTRON_DATASET", "nvidia/Nemotron-Personas-Korea")

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
