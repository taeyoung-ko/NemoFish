# 🐟 NemoFish

**A fully local, Korean-language public-opinion & scenario simulation engine.**

NemoFish is a local, cloud-free port of [MiroFish](https://github.com/666ghj/MiroFish) (a swarm-intelligence
simulation engine), adapted for the Korean language and Korean population.

- 🧠 **Local LLM serving** — Qwen3.6-27B-FP8 served locally via vLLM (OpenAI-compatible API)
- 🕸️ **Zep cloud → local GraphRAG** — replaced with SQLite + local embedding/reranker (`local_zep`)
- 🇰🇷 **Korean personas** — agents built from the statistically-grounded
  [NVIDIA Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) dataset
- 💬 **Korean GUI** — interface fully localized to Korean
- 🐳 **No Docker** — just conda environments + `python run.py`

---

## Acknowledgments

This project is built on top of:

- **[MiroFish](https://github.com/666ghj/MiroFish)** — the original swarm-intelligence simulation engine
  (AGPL-3.0). NemoFish is a modification of MiroFish for local / Korean use.
- **[NVIDIA Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea)**
  — a synthetic persona dataset grounded in Korean demographics (CC BY 4.0), used for agent persona generation.
- **[OASIS](https://github.com/camel-ai/oasis)** (camel-ai) — the social-media simulation framework.

---

## Requirements

- **NVIDIA GPU** (large VRAM recommended; tested on Blackwell / RTX PRO 6000)
- Recent NVIDIA driver (CUDA 12.8+ / 13.x)
- `conda` (miniconda / anaconda)
- `git`

> Qwen3.6-27B-FP8 is ~27GB and is served in FP8 on a recent GPU. If your VRAM is smaller,
> switch to a smaller model or a more aggressive quantization variant in `.env`.

---

## Installation

### 1) Clone
```bash
git clone https://github.com/taeyoung-ko/NemoFish.git
cd NemoFish
```

### 2) LLM serving environment (`qwen36`) — vLLM
```bash
conda create -n qwen36 python=3.12 -y
conda activate qwen36
pip install -U uv
uv pip install "vllm>=0.19" --torch-backend=auto   # auto-selects the right torch build for your GPU
```

### 3) Backend / dataset environment (`nemofish`)
```bash
conda create -n nemofish python=3.12 -y
conda activate nemofish
pip install -U uv

# Backend deps + Nemotron dataset + local embedding/reranker
uv pip install -r repo/backend/requirements.txt
uv pip install datasets huggingface_hub hf_transfer pandas pyarrow

# Node 20+ for the frontend (required by Vite)
conda install -c conda-forge "nodejs>=20" -y

# Patch OASIS (drop MBTI + inject Nemotron demographics into agent prompts)
python scripts/patch_oasis.py
```

### 4) Frontend deps
```bash
cd repo/frontend && npm install && cd ../..
```

### 5) Environment variables
```bash
cp repo/.env.example repo/.env
```
Edit `repo/.env` for the local stack:
```env
LLM_API_KEY=dummy
LLM_BASE_URL=http://localhost:8000/v1
LLM_MODEL_NAME=Qwen/Qwen3.6-27B-FP8
USE_NEMOTRON_PERSONAS=true
NEMOTRON_AGENT_COUNT=20
```

---

## Running

```bash
conda activate nemofish
python run.py
```

A single `run.py` launches **all three** services:
- Qwen3.6-27B server (`:8000`, `qwen36` env)
- Backend (`:5001`, `nemofish` env)
- Frontend GUI (`:3000`)

When ready, open **http://localhost:3000** in your browser.
Press **Ctrl+C** in the launcher terminal to stop all three.

Options:
```bash
python run.py --no-qwen     # manage the Qwen server yourself
python run.py --skip-npm    # skip npm install
```

---

## Usage (GUI)

1. **Home** — upload source material (PDF/MD/TXT), enter a simulation prompt, set the number of agents → **Start Engine**
2. **Graph Build** — document → ontology → knowledge graph (automatic)
3. **Env Setup** — sample Korean personas from Nemotron + configure the simulation
4. **Simulation** — agents interact on a virtual social platform
5. **Report / Deep Interaction** — generated report + chat/survey with the agents

> For a first run, use a short document with a small number of rounds/agents (27B inference is slow).

---

## Layout

```
NemoFish/
├─ run.py                     # unified launcher
├─ scripts/patch_oasis.py     # OASIS library patch (auto-applied by run.py, or run manually)
└─ repo/                      # the MiroFish app (localized fork)
   ├─ backend/                #   Flask backend
   │  └─ app/
   │     ├─ local_zep/        #   local GraphRAG replacing Zep (SQLite + local models)
   │     └─ services/
   │        ├─ nemotron_loader.py         # Nemotron → agent-profile adapter
   │        └─ oasis_profile_generator.py
   ├─ frontend/               #   Vue 3 GUI (Korean)
   └─ locales/                #   i18n (ko/en/zh)
```

## License

The original MiroFish is AGPL-3.0, so this repository follows the same license.
Nemotron-Personas-Korea is CC BY 4.0.
