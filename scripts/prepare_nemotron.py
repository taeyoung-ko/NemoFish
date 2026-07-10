#!/usr/bin/env python
"""
Nemotron-Personas-Korea 사전 다운로드 + 전처리 (NemoFish).

데이터셋을 미리 받아 '프로필 dict'로 변환해 로컬 jsonl 풀로 저장한다.
이후 런타임(app.services.nemotron_loader.sample_profiles)은 이 파일만 로드해서
샘플링하므로, 시뮬레이션마다 다운로드/네트워크 스트리밍이 발생하지 않는다(오프라인·즉시).

사용:
    python scripts/prepare_nemotron.py                # 전체(100만 명) 풀 생성 (기본)
    python scripts/prepare_nemotron.py --size 50000   # 표본만(테스트용, 셔플 후 N명)
    NEMOTRON_POOL_PATH=/경로.jsonl python scripts/prepare_nemotron.py

기본은 데이터셋 전체를 포함(샘플링 없음) → 필터가 100만 전체 인구 위에서 동작.
풀이 없어도 동작은 함(자동으로 스트리밍 폴백). 이 스크립트는 '속도·오프라인·전체집단' 최적화.
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(_HERE, "..", "repo", "backend")
sys.path.insert(0, _BACKEND)


def main():
    try:
        from app.services.nemotron_loader import (
            row_to_profile_dict, sample_rows, iter_all_rows, POOL_PATH,
        )
    except Exception as e:
        print(f"[prepare_nemotron] 백엔드 import 실패: {e}\n  → nemofish 환경에서 실행하세요.")
        return 1

    ap = argparse.ArgumentParser()
    # 기본 0 = 전체(100만) 포함. >0 이면 그 수만큼만 셔플 표본(테스트용).
    ap.add_argument("--size", type=int,
                    default=int(os.environ.get("NEMOTRON_POOL_SIZE", "0")),
                    help="풀에 담을 페르소나 수. 0=전체(기본), N>0=표본 N명")
    ap.add_argument("--out", default=POOL_PATH, help="출력 jsonl 경로")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    full = args.size <= 0

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    target_desc = "전체(100만 규모)" if full else f"{args.size}명 표본"
    print(f"[prepare_nemotron] 다운로드+전처리 시작: {target_desc} → {args.out}")
    print("  (스트리밍으로 받아 변환합니다. 전체는 수십 분 소요될 수 있음)")

    if full:
        rows = iter_all_rows(streaming=True)          # 전체 순회(샘플링·셔플 없음)
    else:
        buf = min(args.size, 20000)
        rows = sample_rows(args.size, seed=args.seed, streaming=True, shuffle_buffer=buf)

    # 원자적 쓰기: .tmp에 쓰고 완료 후 교체 → 도중에 죽어도 부분파일이 최종경로에 안 남음
    tmp = args.out + ".tmp"
    n = 0
    with open(tmp, "w", encoding="utf-8") as f:
        for row in rows:
            d = row_to_profile_dict(row)
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
            if n % 50000 == 0:
                print(f"  {n}명 처리 ...", flush=True)
    os.replace(tmp, args.out)

    size_mb = os.path.getsize(args.out) / 1e6
    print(f"[prepare_nemotron] 완료: {n}명 저장 ({size_mb:.1f} MB) → {args.out}")
    print("  이제 시뮬레이션은 이 풀 전체에서 필터/샘플링합니다(다운로드 없음).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
