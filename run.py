"""
MiroFish 통합 실행 런처 (nemofish 폴더용)

이거 하나로 3개 전부 띄운다:
    1) Qwen3.6-27B vLLM 서버  (:8000, qwen36 env)   ※ 이미 떠있으면 재사용
    2) MiroFish 백엔드        (:5001, nemofish env)
    3) 프론트엔드 GUI          (:3000, npm/vite)

사용법:
    conda activate nemofish
    python run.py

    → 브라우저에서 http://localhost:3000
    → Ctrl+C 한 번이면 셋 다 종료

옵션:
    python run.py --no-qwen     # Qwen 서버는 건드리지 않음(따로 관리할 때)
    python run.py --skip-npm    # npm install 생략(이미 설치됨)
"""

import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(HERE, "repo", "backend")
FRONTEND = os.path.join(HERE, "repo", "frontend")

# 현재 python(=nemofish env) 기준으로 다른 env 경로 유도
NEMOFISH_PY = sys.executable                                   # .../envs/nemofish/bin/python
NEMOFISH_BIN = os.path.dirname(NEMOFISH_PY)                    # .../envs/nemofish/bin (node/npm 20+ 포함)
_ENV_DIR = os.path.dirname(NEMOFISH_BIN)                       # .../envs/nemofish
_ENVS_DIR = os.path.dirname(_ENV_DIR)                          # .../envs
QWEN_VLLM = os.path.join(_ENVS_DIR, "qwen36", "bin", "vllm")   # .../envs/qwen36/bin/vllm
QWEN_BIN = os.path.dirname(QWEN_VLLM)                          # .../envs/qwen36/bin (ninja/nvcc 등 포함)
NPM = os.path.join(NEMOFISH_BIN, "npm")                        # env의 npm(=node 20+). nvm의 구버전 node 회피
# 프론트엔드 subprocess는 env bin을 PATH 맨앞에 → 반드시 env node 사용
_NODE_ENV = {"PATH": NEMOFISH_BIN + os.pathsep + os.environ.get("PATH", "")}

QWEN_MODEL = "Qwen/Qwen3.6-27B-FP8"
NO_QWEN = "--no-qwen" in sys.argv
SKIP_NPM = "--skip-npm" in sys.argv

procs = []  # (name, Popen)


def _qwen_up() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:8000/v1/models", timeout=3) as r:
            return b"Qwen" in r.read()
    except Exception:
        return False


def _stream(name, proc, color):
    """자식 프로세스 출력에 이름 프리픽스를 붙여 통합 출력."""
    reset = "\033[0m"
    for line in iter(proc.stdout.readline, b""):
        try:
            text = line.decode("utf-8", "replace").rstrip()
        except Exception:
            text = str(line)
        print(f"{color}[{name}]{reset} {text}", flush=True)


def _spawn(name, cmd, cwd, color, env=None):
    print(f"\033[1m▶ {name} 시작:\033[0m {' '.join(cmd)}  (cwd={cwd})", flush=True)
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    p = subprocess.Popen(
        cmd, cwd=cwd, env=full_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        start_new_session=True,   # 프로세스 그룹 분리 → 한 번에 종료 가능
    )
    procs.append((name, p))
    threading.Thread(target=_stream, args=(name, p, color), daemon=True).start()
    return p


def shutdown(*_):
    print("\n\033[1m■ 종료 중... 모든 프로세스 정리\033[0m", flush=True)
    for name, p in procs:
        if p.poll() is None:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except Exception:
                pass
    time.sleep(3)
    for name, p in procs:
        if p.poll() is None:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception:
                pass
    print("■ 종료 완료", flush=True)
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # OASIS(camel-oasis) 라이브러리 패치 적용 (멱등 — 이미 돼있으면 스킵)
    _patch = os.path.join(HERE, "scripts", "patch_oasis.py")
    if os.path.exists(_patch):
        try:
            subprocess.run([NEMOFISH_PY, _patch], check=False)
        except Exception as e:
            print(f"[경고] OASIS 패치 실행 실패(수동으로 python scripts/patch_oasis.py): {e}", flush=True)

    # 1) Qwen 서버
    if NO_QWEN:
        print("· Qwen 서버: --no-qwen 지정 → 건너뜀", flush=True)
    elif _qwen_up():
        print("· Qwen 서버: 이미 :8000 에 떠있음 → 재사용", flush=True)
    else:
        if not os.path.exists(QWEN_VLLM):
            print(f"[경고] qwen36 vllm 을 찾을 수 없음: {QWEN_VLLM}\n"
                  f"       Qwen 서버 없이 진행합니다(시뮬레이션은 27B 필요).", flush=True)
        else:
            _spawn("qwen", [
                QWEN_VLLM, "serve", QWEN_MODEL,
                "--port", "8000", "--max-model-len", "32768",
                "--gpu-memory-utilization", "0.5", "--max-num-seqs", "256",
                "--reasoning-parser", "qwen3",
            ], cwd=HERE, color="\033[33m",
                env={
                    "VLLM_USE_DEEP_GEMM": "0",
                    "HF_HUB_ENABLE_HF_TRANSFER": "1",
                    # qwen36 env의 bin을 PATH 맨앞에 → flashinfer JIT가 ninja/컴파일러를 찾음
                    "PATH": QWEN_BIN + os.pathsep + os.environ.get("PATH", ""),
                })

    # 2) 백엔드 (nemofish env, 단일 프로세스 위해 debug reloader 끔)
    _spawn("backend", [NEMOFISH_PY, "run.py"], cwd=BACKEND, color="\033[32m",
           env={"FLASK_DEBUG": "False", "HF_HUB_ENABLE_HF_TRANSFER": "1"})

    # 3) 프론트엔드 (npm install → npm run dev)
    if not SKIP_NPM and not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        print("· 프론트엔드 의존성 설치(npm install) — 최초 1회, 잠시 걸림...", flush=True)
        _ienv = os.environ.copy(); _ienv.update(_NODE_ENV)
        r = subprocess.run([NPM, "install"], cwd=FRONTEND, env=_ienv)
        if r.returncode != 0:
            print("[경고] npm install 실패 — 프론트엔드 없이 진행", flush=True)
    _spawn("frontend", [NPM, "run", "dev"], cwd=FRONTEND, color="\033[36m", env=_NODE_ENV)

    print("\n\033[1m=== 전부 기동됨 ===\033[0m")
    print("  · GUI:     http://localhost:3000")
    print("  · 백엔드:  http://localhost:5001")
    print("  · Qwen:    http://localhost:8000")
    print("  (Ctrl+C 로 전부 종료)\n", flush=True)

    # 자식이 죽으면 알리고, 메인은 대기
    try:
        while True:
            time.sleep(2)
            for name, p in procs:
                code = p.poll()
                if code is not None:
                    print(f"\033[31m[{name}] 프로세스가 종료됨 (code={code})\033[0m", flush=True)
                    procs.remove((name, p))
            if not procs:
                print("모든 프로세스 종료됨. 런처 종료.", flush=True)
                break
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
