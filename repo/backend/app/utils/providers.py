"""
Provider 설정 (클라우드 단일 모드, .env 기반).

로컬 Qwen 경로는 제거됨. 모든 LLM 호출은 .env의 OpenAI, 임베딩/리랭킹은 .env의 Voyage를 사용한다.
- LLM     : Config.LLM_*  (LLM_BASE_URL=OpenAI, LLM_MODEL_NAME=gpt-5.4-nano, LLM_API_KEY)
- 임베더  : GRAPH_EMBED_PROVIDER=voyage + VOYAGE_API_KEY + VOYAGE_EMBED_MODEL
- 리랭커  : GRAPH_RERANK_PROVIDER=voyage + VOYAGE_API_KEY + VOYAGE_RERANK_MODEL

resolve_providers/project_providers 는 하위호환용 인터페이스로 남기되, 항상 env 설정을 반환한다.
"""
import os
from typing import Any, Dict

from ..config import Config


def _env_providers() -> Dict[str, Dict[str, Any]]:
    voyage_key = os.environ.get("VOYAGE_API_KEY")
    return {
        "mode": "cloud",
        "llm": {
            "provider": "openai",
            "base_url": Config.LLM_BASE_URL,
            "model": Config.LLM_MODEL_NAME,
            "api_key": Config.LLM_API_KEY,
        },
        "embed": {
            "provider": os.environ.get("GRAPH_EMBED_PROVIDER", "voyage"),
            "model": os.environ.get("VOYAGE_EMBED_MODEL", "voyage-4-lite"),
            "api_key": voyage_key,
        },
        "rerank": {
            "provider": os.environ.get("GRAPH_RERANK_PROVIDER", "voyage"),
            "model": os.environ.get("VOYAGE_RERANK_MODEL", "rerank-2.5-lite"),
            "api_key": voyage_key,
        },
    }


def resolve_providers(*_args, **_kwargs) -> Dict[str, Dict[str, Any]]:
    """항상 .env 기반 클라우드 설정 반환(인자 무시 — 하위호환용)."""
    return _env_providers()


def project_providers(_project: Any = None) -> Dict[str, Dict[str, Any]]:
    """프로젝트별 모드 구분 없이 .env 설정 반환."""
    return _env_providers()
