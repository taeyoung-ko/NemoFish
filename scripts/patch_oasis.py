#!/usr/bin/env python
"""
OASIS(camel-oasis) 라이브러리 패치 — NemoFish용.

camel-oasis는 pip 패키지라, 클론 후 재설치하면 원본으로 돌아간다.
이 스크립트가 설치된 oasis 패키지에 NemoFish 수정을 (멱등하게) 적용한다:

  1) MBTI 미사용: Nemotron 데이터셋엔 MBTI가 없음 → mbti 직접 인덱싱을 .get()으로
     바꿔 KeyError 방지, 시스템 프롬프트의 MBTI 문구 제거.
  2) Nemotron 인구통계/스킬(직업/학력/전공/거주지/혼인/가구/주거/병역/스킬/관심사)을
     에이전트 시스템 프롬프트에 컬럼별로 개별 주입.

사용:
    python scripts/patch_oasis.py     # 설치 후 1회 (여러 번 실행해도 안전)
"""
import os
import sys

# user.py: 원본(MBTI 포함) description 블록
_USER_OLD = '''                description += (
                    f"You are a {self.profile['other_info']['gender']}, "
                    f"{self.profile['other_info']['age']} years old, with an MBTI "
                    f"personality type of {self.profile['other_info']['mbti']} from "
                    f"{self.profile['other_info']['country']}.")'''

# user.py: 교체할 블록 (MBTI 제거 + Nemotron 상세 배경 개별 주입)
_USER_NEW = '''                oi = self.profile['other_info']
                description += (
                    f"You are a {oi['gender']}, "
                    f"{oi['age']} years old, from "
                    f"{oi['country']}.")
                # Nemotron 상세 배경 — 컬럼별 개별 주입 (있는 것만)
                def _join(x):
                    return ", ".join(x) if isinstance(x, (list, tuple)) else str(x)
                _extra = []
                if oi.get('profession'):
                    _extra.append(f"직업: {oi['profession']}")
                if oi.get('education_level'):
                    _edu = oi['education_level']
                    if oi.get('bachelors_field'):
                        _edu += f"({oi['bachelors_field']})"
                    _extra.append(f"학력: {_edu}")
                if oi.get('province') or oi.get('district'):
                    _extra.append("거주지: " + " ".join(
                        x for x in (oi.get('province'), oi.get('district')) if x))
                if oi.get('marital_status'):
                    _extra.append(f"혼인상태: {oi['marital_status']}")
                if oi.get('family_type'):
                    _extra.append(f"가구형태: {oi['family_type']}")
                if oi.get('housing_type'):
                    _extra.append(f"주거형태: {oi['housing_type']}")
                if oi.get('military_status'):
                    _extra.append(f"병역: {oi['military_status']}")
                if oi.get('skills'):
                    _extra.append("전문 스킬: " + _join(oi['skills']))
                if oi.get('interested_topics'):
                    _extra.append("관심사: " + _join(oi['interested_topics']))
                if _extra:
                    description += " " + " / ".join(_extra) + "."'''

# agents_generator.py: country 라인 뒤에 삽입할 인구통계/스킬 주입 블록
_GEN_COUNTRY = '        profile["other_info"]["country"] = agent_info[i]["country"]\n'
_GEN_INJECT = (
    _GEN_COUNTRY
    + '        # Nemotron 인구통계/스킬 (컬럼별 개별 필드). 없으면 None.\n'
    + '        for _k in ("profession", "skills", "province", "district", "education_level",\n'
    + '                   "bachelors_field", "marital_status", "military_status",\n'
    + '                   "family_type", "housing_type", "interested_topics"):\n'
    + '            profile["other_info"][_k] = agent_info[i].get(_k)\n'
)


def _patch_file(path, transforms, done_marker):
    """transforms: [(old, new), ...] 순차 적용. done_marker 있으면 이미 패치된 것으로 간주."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    if done_marker in src:
        print(f"  - {os.path.basename(path)}: 이미 적용됨(스킵)")
        return False
    new = src
    for old, repl in transforms:
        new = new.replace(old, repl)
    if new == src:
        print(f"  ! {os.path.basename(path)}: 대상 문자열을 못 찾음 (oasis 버전 다름?)")
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"  ✓ {os.path.basename(path)}: 패치 완료")
    return True


def main():
    try:
        import oasis
    except ImportError:
        print("[patch_oasis] oasis 미설치 — 먼저 requirements 설치 후 실행하세요.")
        return 1

    base = os.path.dirname(oasis.__file__)
    ag = os.path.join(base, "social_agent", "agents_generator.py")
    uf = os.path.join(base, "social_platform", "config", "user.py")
    print(f"[patch_oasis] 대상: {base}")

    # agents_generator.py: mbti 직접 인덱싱 → .get, country 뒤 주입 블록 추가
    _patch_file(
        ag,
        [
            ('profile["other_info"]["mbti"] = agent_info[i]["mbti"]',
             'profile["other_info"]["mbti"] = agent_info[i].get("mbti")  # MBTI 미사용: 키 없어도 KeyError 방지'),
            (_GEN_COUNTRY, _GEN_INJECT),
        ],
        done_marker='for _k in ("profession", "skills"',
    )

    # user.py: MBTI 문구 제거 + Nemotron 상세 배경 개별 주입
    _patch_file(
        uf,
        [(_USER_OLD, _USER_NEW)],
        done_marker="# Nemotron 상세 배경",
    )

    print("[patch_oasis] 완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
