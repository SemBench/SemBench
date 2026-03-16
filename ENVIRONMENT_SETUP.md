# SemBench Environment Setup Guide

## Quick Setup

```bash
bash scripts/setup_envs.sh
```

This creates all environments using [uv](https://docs.astral.sh/uv/) (installed automatically):

| Environment | Location | Purpose |
|-------------|----------|---------|
| `sembench` | `.venvs/sembench/` | Orchestrator — runs `run.py`, evaluation, plotting |
| `lotus` | `.venvs/lotus/` | LOTUS system (numpy<2) |
| `palimpzest` | `.venvs/palimpzest/` | Palimpzest system (numpy>=2) |
| `thalamusdb` | `.venvs/thalamusdb/` | ThalamusDB system |
| `bigquery` | `.venvs/bigquery/` | Google BigQuery system |
| `caesura` | `.venvs/caesura/` | CAESURA system |
| `flockmtl` | `.venvs/flockmtl/` | FlockMTL system |

Setup specific systems only:
```bash
bash scripts/setup_envs.sh lotus palimpzest
```

## Running Benchmarks

```bash
source .venvs/sembench/bin/activate
python3 src/run.py --systems lotus --use-cases movie --queries 1 --model gemini-2.5-flash --scale-factor 2000
```

That's it. `run.py` automatically detects `.venvs/{system}/` and dispatches
each system to its own isolated venv via subprocess. No conda needed.

```bash
# Compare multiple systems
python3 src/run.py --systems lotus palimpzest thalamusdb bigquery --use-cases movie --queries 1 --model gemini-2.5-flash --scale-factor 2000

# Disable isolation (run everything in current process)
python3 src/run.py --systems thalamusdb --no-isolation
```

---

## How It Works

Each system has its own requirements file in `requirements/`:

| File | Contents |
|------|----------|
| `base.txt` | Shared framework deps (pandas, torch, litellm, scikit-learn, ...) |
| `lotus.txt` | `-r base.txt` + lotus-ai==1.1.3 |
| `palimpzest.txt` | `-r base.txt` + palimpzest @ git+...@0.8.2.sem_agg |
| `thalamusdb.txt` | `-r base.txt` + thalamusdb==0.1.15 |
| `bigquery.txt` | `-r base.txt` + google-cloud-bigquery, ... |

When you run `python3 src/run.py --systems lotus thalamusdb`:

1. `run.py` (in `sembench` venv) detects `.venvs/lotus/` and `.venvs/thalamusdb/`
2. Spawns a subprocess for each: `.venvs/lotus/bin/python src/run_worker.py --system lotus ...`
3. Worker runs queries and saves results/metrics to disk
4. `run.py` runs evaluation on saved results

### Adding a New System

1. Create `requirements/newsystem.txt`:
   ```
   -r base.txt
   new-system-package==1.0.0
   ```
2. Run `bash scripts/setup_envs.sh newsystem`
3. Implement the runner in `src/scenario/{use_case}/runner/newsystem_runner/`
4. Add the system to `get_runner_class()` in `src/run.py`

---

## Why Per-System Venvs?

- **Zero conflicts**: lotus needs numpy<2, palimpzest needs numpy>=2 — impossible in one env
- **Fast**: uv installs are 10-100x faster than pip, with aggressive caching
- **Easy to extend**: adding a new system = one requirements file
- **No conda**: everything managed by uv, fully self-contained in `.venvs/`
