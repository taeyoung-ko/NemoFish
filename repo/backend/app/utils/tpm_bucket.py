"""
크로스-프로세스 TPM(분당 토큰) 버킷 — 메인(Flask)과 시뮬레이션 서브프로세스가
같은 OpenAI org 한도(200k TPM)를 '하나의 예산'으로 공유하기 위한 파일락 기반 한도기.

왜 필요한가:
  - 메인 프로세스: 온톨로지 생성 등 LLM 호출(llm_client)
  - 서브프로세스: camel/OASIS 에이전트 수십 명의 비동기 LLM 호출(openai_throttle)
  두 프로세스가 각자 인메모리로 한도를 관리하면, 서로를 모르니 합쳐서 200k를 넘겨
  429가 난다(실측: 서브프로세스가 200k를 다 써서 메인의 온톨로지 호출이 429).

동작:
  - 롤링 60초 창의 (timestamp, tokens) 이벤트를 파일에 기록.
  - reserve() 는 flock(LOCK_EX)으로 짧게 잠그고 read-modify-write:
      창 안 누적 + 요청 토큰 <= 예산  → 즉시 기록하고 통과
      아니면                          → 락 풀고 계산된 시간만큼 sleep 후 재시도
  - 예산 = OPENAI_TPM * OPENAI_TPM_SAFETY (기본 200000 * 0.85 = 170000),
    두 프로세스 '합산'이 이 값을 넘지 않는다 → 실제 200k 한도에 15% 헤드룸.

환경변수:
  OPENAI_TPM           분당 토큰 한도(기본 200000)
  OPENAI_TPM_SAFETY    안전계수(기본 0.85)
  OPENAI_TPM_STATE     상태/락 파일 경로 프리픽스(기본 /tmp/nemofish_openai_tpm)
"""
import asyncio
import json
import os
import tempfile
import time

_TPM = int(os.environ.get("OPENAI_TPM", "200000"))
_SAFETY = float(os.environ.get("OPENAI_TPM_SAFETY", "0.85"))
_BUDGET = max(1000, int(_TPM * _SAFETY))
_WINDOW = 60.0

_PREFIX = os.environ.get(
    "OPENAI_TPM_STATE",
    os.path.join(tempfile.gettempdir(), "nemofish_openai_tpm"),
)
_STATE = _PREFIX + ".json"
_LOCK = _PREFIX + ".lock"

try:
    import fcntl  # Linux/유닉스
    _HAVE_FCNTL = True
except Exception:  # pragma: no cover
    _HAVE_FCNTL = False


def budget() -> int:
    return _BUDGET


def _read_events(fd):
    try:
        fd.seek(0)
        data = fd.read()
        if not data:
            return []
        ev = json.loads(data)
        if isinstance(ev, list):
            return ev
    except Exception:
        pass
    return []


def _write_events(fd, events):
    try:
        fd.seek(0)
        fd.truncate()
        fd.write(json.dumps(events))
        fd.flush()
        os.fsync(fd.fileno())
    except Exception:
        pass


def _try_reserve(tokens):
    """예산 내면 즉시 확보 (True, 0). 아니면 (False, 대기초). 크로스-프로세스 원자적."""
    tokens = min(int(tokens), _BUDGET)
    if not _HAVE_FCNTL:
        # 파일락 불가 환경: 안전하게 그냥 통과(호출측 재시도에 맡김)
        return True, 0.0
    now = time.time()
    cutoff = now - _WINDOW
    lf = open(_LOCK, "a+")
    try:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            sf = open(_STATE, "a+")
        except Exception:
            sf = None
        events = _read_events(sf) if sf is not None else []
        events = [e for e in events if isinstance(e, list) and len(e) == 2 and e[0] >= cutoff]
        used = sum(e[1] for e in events)
        if used + tokens <= _BUDGET:
            events.append([now, tokens])
            if sf is not None:
                _write_events(sf, events)
                sf.close()
            return True, 0.0
        # 가장 오래된 이벤트가 창을 벗어나면 자리가 생김
        oldest = min((e[0] for e in events), default=now)
        wait = (oldest + _WINDOW) - now
        if sf is not None:
            sf.close()
        return False, max(0.02, min(wait, 5.0))
    finally:
        try:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        lf.close()


def reserve(tokens):
    """동기: 창 예산 확보(넘으면 대기)."""
    while True:
        ok, wait = _try_reserve(tokens)
        if ok:
            return
        time.sleep(wait)


async def reserve_async(tokens):
    """비동기(에이전트 이벤트루프용): 루프 안 막고 대기."""
    while True:
        ok, wait = _try_reserve(tokens)
        if ok:
            return
        await asyncio.sleep(wait)
