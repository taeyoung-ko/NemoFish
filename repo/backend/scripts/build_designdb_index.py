"""
designdb 시맨틱 검색 인덱스 빌더 (one-shot, 재개 가능).

실행:
    cd repo/backend
    python scripts/build_designdb_index.py              # 전체
    python scripts/build_designdb_index.py --limit 200  # 소량 테스트

출력: backend/app/data/designdb_index/{embeddings.npy, meta.jsonl}

전제: .env 의 VOYAGE_API_KEY 에 결제수단 등록된 Voyage 키(표준 레이트리밋).
      무결제 무료티어(3 RPM)로는 21k 인덱싱이 사실상 불가.
"""
import argparse
import os
import sys

# repo/backend 를 import 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config  # noqa: E402,F401  (.env 로드)
from app.services import designdb_search as d  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="처리할 기사 수 상한(테스트용)")
    ap.add_argument("--batch", type=int, default=8, help="임베딩 배치 크기")
    args = ap.parse_args()

    print(f"[build_designdb_index] DESIGNDB_ROOT={d.DESIGNDB_ROOT}")
    print(f"[build_designdb_index] 출력={d.INDEX_DIR}")
    r = d.build_index(limit=args.limit, embed_batch=args.batch)
    print(f"[build_designdb_index] 완료: {r}")


if __name__ == "__main__":
    main()
