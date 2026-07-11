"""
OpenAI TPM(분당 토큰) 스로틀 — 레이트리밋(429)을 애초에 안 걸리게 요청 속도를 조절.

OpenAI 한도는 RPM(요청/분)·TPM(토큰/분) 두 가지이며, 실무상 병목은 TPM이다.
이 모듈은 롤링 60초 창의 누적 토큰을 추적해, 다음 요청을 보내면 TPM을 넘을 때
넘지 않을 때까지 대기시킨다(능동 분산). 동시 요청 수도 제한한다.

install() 로 openai SDK의 chat.completions.create 를 몽키패치 → camel/oasis 등
그 SDK를 쓰는 모든 호출(서브프로세스 에이전트 포함)에 적용된다.

환경변수:
  OPENAI_TPM               분당 토큰 예산(기본 200000; 본인 org 한도에 맞춤)
  OPENAI_TPM_SAFETY        예산 대비 사용 비율(기본 0.85 — 15% 헤드룸)
  OPENAI_MAX_CONCURRENCY   동시 요청 수(기본 8)
"""
import asyncio
import os
import re
import threading
import time

from . import tpm_bucket  # 메인 프로세스와 '합산' 예산을 공유(크로스-프로세스 파일락)

_BUDGET = tpm_bucket.budget()                     # 실제로 쓸 분당 토큰 상한(공유)
_MAX_CONC = int(os.environ.get("OPENAI_MAX_CONCURRENCY", "8"))

_sem = threading.Semaphore(_MAX_CONC)


# ── 토큰 추정 ──
_enc = None
_enc_tried = False


def _encoder():
    global _enc, _enc_tried
    if not _enc_tried:
        _enc_tried = True
        try:
            import tiktoken
            _enc = tiktoken.get_encoding("o200k_base")
        except Exception:
            _enc = None
    return _enc


def _estimate_tokens(messages, max_out):
    text = ""
    for m in (messages or []):
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, str):
            text += c
        elif isinstance(c, list):  # 멀티모달 content
            for part in c:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text += part["text"]
    enc = _encoder()
    if enc is not None:
        try:
            n_in = len(enc.encode(text))
        except Exception:
            n_in = len(text)   # 보수적(과대) — 과소추정하면 예산 초과로 429 위험
    else:
        n_in = len(text)       # tiktoken 없을 때: 1토큰/글자로 보수적 추정
    return n_in + int(max_out or 512) + 8  # 요청 오버헤드 여유


def _reserve(tokens):
    """동기: 공유 버킷에서 예산 확보(넘으면 대기)."""
    tpm_bucket.reserve(tokens)


async def _reserve_async(tokens):
    """비동기(camel/OASIS 에이전트용): 공유 버킷, 이벤트루프 안 막고 대기."""
    await tpm_bucket.reserve_async(tokens)


def _retry_after(exc) -> float:
    """RateLimitError면 Retry-After(헤더/메시지)에서 대기초 추출, 아니면 -1."""
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    if status != 429:
        return -1.0
    # 헤더 우선
    try:
        ra = exc.response.headers.get("retry-after")
        if ra:
            return float(ra)
    except Exception:
        pass
    # 메시지에서 "try again in 1.23s" 파싱
    msg = str(getattr(exc, "message", "") or exc)
    m = re.search(r"try again in ([0-9.]+)s", msg)
    if m:
        return float(m.group(1))
    return 3.0


# max_tokens 미지정 호출(설정/프로필 생성기: "让LLM自由发挥")은 큰 JSON을 뱉을 수 있어
# 출력 예산을 넉넉히 잡는다(과소추정 시 실사용이 예약을 넘겨 429). 상한은 4096으로 보수적 추정.
_UNSET_OUTPUT_EST = int(os.environ.get("OPENAI_UNSET_OUTPUT_EST", "4096"))


def _est_from_kwargs(kwargs):
    return _estimate_tokens(
        kwargs.get("messages"),
        kwargs.get("max_completion_tokens") or kwargs.get("max_tokens") or _UNSET_OUTPUT_EST,
    )


def install():
    """openai SDK의 chat.completions.create(동기+비동기)를 TPM 스로틀 버전으로 교체.

    camel/OASIS 에이전트는 비동기(AsyncOpenAI)를 쓰므로 비동기 패치가 핵심이다.
    """
    patched = False
    # ── 동기 ──
    try:
        from openai.resources.chat.completions import Completions
        if not getattr(Completions.create, "_tpm_throttled", False):
            _orig = Completions.create

            def _wrapper(self, *args, **kwargs):
                est = _est_from_kwargs(kwargs)
                attempts = 0
                while True:
                    _reserve(est)
                    with _sem:
                        try:
                            return _orig(self, *args, **kwargs)
                        except Exception as e:
                            ra = _retry_after(e)
                            if ra < 0 or attempts >= 6:
                                raise
                            attempts += 1
                    time.sleep(ra)

            _wrapper._tpm_throttled = True
            Completions.create = _wrapper
            patched = True
    except Exception:
        pass
    # ── 비동기 (camel/OASIS 에이전트) ──
    try:
        from openai.resources.chat.completions import AsyncCompletions
        if not getattr(AsyncCompletions.create, "_tpm_throttled", False):
            _aorig = AsyncCompletions.create

            async def _awrapper(self, *args, **kwargs):
                est = _est_from_kwargs(kwargs)
                attempts = 0
                while True:
                    await _reserve_async(est)
                    try:
                        return await _aorig(self, *args, **kwargs)
                    except Exception as e:
                        ra = _retry_after(e)
                        if ra < 0 or attempts >= 6:
                            raise
                        attempts += 1
                        await asyncio.sleep(ra)

            _awrapper._tpm_throttled = True
            AsyncCompletions.create = _awrapper
            patched = True
    except Exception:
        pass
    return patched
