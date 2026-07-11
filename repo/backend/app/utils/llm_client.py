"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import os
import re
import threading
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config
from . import tpm_bucket as _tpm_bucket  # 서브프로세스와 합산 TPM 예산 공유

# ── OpenAI 레이트리밋 회피(429 애초에 안 걸리게) ──
# OpenAI 공식 문서상 한도는 RPM(요청/분)·TPM(토큰/분) 두 가지이며, 실제 남은 양·리셋시간은
# 응답 헤더 x-ratelimit-remaining-tokens / x-ratelimit-reset-tokens 로 내려온다.
# → 그 헤더를 읽어, 남은 토큰이 한도 대비 낮아지면 리셋까지 잠깐 멈춘다(전역 공유).
# 참고: https://platform.openai.com/docs/guides/rate-limits
_OPENAI_MAX_CONCURRENCY = int(os.environ.get("OPENAI_MAX_CONCURRENCY", "4"))
_OPENAI_HEADROOM = float(os.environ.get("OPENAI_HEADROOM", "0.10"))  # 남은 토큰이 한도의 10% 미만이면 멈춤
_openai_sem = threading.Semaphore(_OPENAI_MAX_CONCURRENCY)
_rl_gate = threading.Lock()
_rl_pause_until = [0.0]


_enc = None
_enc_tried = False


def _estimate_tokens(messages, max_out) -> int:
    """공유 TPM 버킷 예약용 토큰 추정(입력 + 출력상한). 보수적으로 약간 과대."""
    global _enc, _enc_tried
    text = ""
    for m in (messages or []):
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, str):
            text += c
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text += part["text"]
    if not _enc_tried:
        _enc_tried = True
        try:
            import tiktoken
            _enc = tiktoken.get_encoding("o200k_base")
        except Exception:
            _enc = None
    if _enc is not None:
        try:
            n_in = len(_enc.encode(text))
        except Exception:
            n_in = len(text)  # 보수적(과대) — 과소추정하면 예산 초과로 429 위험
    else:
        n_in = len(text)      # tiktoken 없을 때: 1토큰/글자로 보수적 추정
    return n_in + int(max_out or 512) + 8


def _parse_reset(s: str) -> float:
    """'59.393s' / '6m0s' / '500ms' / '1h2m3s' → 초."""
    total = 0.0
    for val, unit in re.findall(r'([0-9.]+)(ms|h|m|s)', s or ''):
        v = float(val)
        total += {'ms': v / 1000, 's': v, 'm': v * 60, 'h': v * 3600}[unit]
    return total


def _rl_wait():
    """직전 응답 헤더 기준으로 리셋까지 멈춤 창이 걸려 있으면 대기."""
    with _rl_gate:
        wait = _rl_pause_until[0] - time.monotonic()
    if wait > 0:
        time.sleep(min(wait, 65.0))


def _rl_update(headers):
    """응답 헤더의 남은 토큰/요청이 한도 대비 낮으면 리셋시간까지 멈춤 창 설정."""
    try:
        lim_t = int(headers.get("x-ratelimit-limit-tokens", 0) or 0)
        rem_t = int(headers.get("x-ratelimit-remaining-tokens", 1 << 30))
        rst_t = _parse_reset(headers.get("x-ratelimit-reset-tokens", "0s"))
        lim_r = int(headers.get("x-ratelimit-limit-requests", 0) or 0)
        rem_r = int(headers.get("x-ratelimit-remaining-requests", 1 << 30))
        rst_r = _parse_reset(headers.get("x-ratelimit-reset-requests", "0s"))
    except Exception:
        return
    pause = 0.0
    if lim_t and rem_t < lim_t * _OPENAI_HEADROOM:
        pause = max(pause, rst_t)
    if lim_r and rem_r < lim_r * _OPENAI_HEADROOM:
        pause = max(pause, rst_r)
    if pause > 0:
        with _rl_gate:
            _rl_pause_until[0] = max(_rl_pause_until[0], time.monotonic() + pause)


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        # OpenAI 공식 API인지(=vLLM 전용 파라미터를 못 보냄). base_url로 판별.
        self._is_openai = "openai.com" in (self.base_url or "")

        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            max_retries=int(os.environ.get("LLM_MAX_RETRIES", "8")),  # 스로틀 뚫려도 최후 보루
            timeout=float(os.environ.get("LLM_TIMEOUT", "120")),
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        extra_body: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            top_p / presence_penalty: 可选采样参数
            extra_body: vLLM 확장 파라미터(예: chat_template_kwargs로 thinking 끄기, top_k/min_p)

        Returns:
            模型响应文本
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if response_format:
            kwargs["response_format"] = response_format

        if self._is_openai:
            # OpenAI 공식 API: vLLM 전용(extra_body/chat_template_kwargs) 미지원 → 제외.
            #   GPT-5 계열은 max_tokens 대신 max_completion_tokens 사용, 커스텀
            #   temperature/top_p/presence_penalty 는 제한적 → 기본값에 맡김.
            if max_tokens:
                kwargs["max_completion_tokens"] = max_tokens
        else:
            # 로컬 vLLM(Qwen): 기존대로 전체 파라미터 전달.
            kwargs["temperature"] = temperature
            kwargs["max_tokens"] = max_tokens
            if top_p is not None:
                kwargs["top_p"] = top_p
            if presence_penalty is not None:
                kwargs["presence_penalty"] = presence_penalty
            if extra_body:
                kwargs["extra_body"] = extra_body

        # OpenAI: 시뮬레이션 서브프로세스와 '합산' TPM 예산을 공유(크로스-프로세스 파일락)해서
        #         두 프로세스 합계가 org 한도를 넘지 않게 사전 분산 → 429를 애초에 회피.
        #         추가로 응답 헤더 기준 리셋 대기 + 동시요청 제한. 로컬 vLLM(Qwen)은 제한 없음.
        if self._is_openai:
            est = _estimate_tokens(messages, kwargs.get("max_completion_tokens"))
            with _openai_sem:
                _rl_wait()
                _tpm_bucket.reserve(est)
                raw = self.client.chat.completions.with_raw_response.create(**kwargs)
                _rl_update(raw.headers)
                response = raw.parse()
        else:
            response = self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        content = msg.content
        # reasoning_parser(qwen3)가 켜진 경우, thinking이 max_tokens를 소진하면 content가 None일 수 있음.
        # 이때 reasoning_content라도 있으면 fallback(잘린 사고라도 JSON 조각이 들어있을 수 있음), 없으면 빈 문자열.
        if content is None:
            content = getattr(msg, "reasoning_content", None) or ""
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        extra_body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            top_p / presence_penalty / extra_body: chat()로 전달되는 선택 파라미터

        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            top_p=top_p,
            presence_penalty=presence_penalty,
            extra_body=extra_body
        )
        # 清理markdown代码块标记
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response}")

