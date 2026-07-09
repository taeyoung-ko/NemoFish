#!/usr/bin/env python
"""
Nemotron-Personas-Korea 사전 다운로드 + 전처리 (NemoFish).

데이터셋을 미리 받아 '프로필 dict'로 변환해 로컬 jsonl 풀로 저장한다.
이후 런타임(app.services.nemotron_loader.sample_profiles)은 이 파일만 로드해서
샘플링하므로, 시뮬레이션마다 다운로드/네트워크 스트리밍이 발생하지 않는다(오프라인·즉시).

사용:
    python scripts/prepare_nemotron.py                # 기본 20000명 풀 생성
    python scripts/prepare_nemotron.py --size 50000   # 더 큰 풀
    NEMOTRON_POOL_PATH=/경로.jsonl python scripts/prepare_nemotron.py

풀이 없어도 동작은 함(자동으로 스트리밍 폴백). 이 스크립트는 '속도·오프라인' 최적화.
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
        from app.services.nemotron_loader import row_to_profile_dict, sample_rows, POOL_PATH
    except Exception as e:
        print(f"[prepare_nemotron] 백엔드 import 실패: {e}\n  → nemofish 환경에서 실행하세요.")
        return 1

    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int,
                    default=int(os.environ.get("NEMOTRON_POOL_SIZE", "20000")),
                    help="풀에 담을 페르소나 수(기본 20000)")
    ap.add_argument("--out", default=POOL_PATH, help="출력 jsonl 경로")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    print(f"[prepare_nemotron] 다운로드+전처리 시작: {args.size}명 → {args.out}")
    print("  (스트리밍으로 받아 변환합니다. 수 분 소요될 수 있음)")

    n = 0
    buf = min(args.size, 20000)
    with open(args.out, "w", encoding="utf-8") as f:
        for row in sample_rows(args.size, seed=args.seed, streaming=True, shuffle_buffer=buf):
            d = row_to_profile_dict(row)
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
            if n % 2000 == 0:
                print(f"  {n}/{args.size} ...", flush=True)

    size_mb = os.path.getsize(args.out) / 1e6
    print(f"[prepare_nemotron] 완료: {n}명 저장 ({size_mb:.1f} MB) → {args.out}")
    print("  이제 시뮬레이션은 이 풀에서 즉시 샘플링합니다(다운로드 없음).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
