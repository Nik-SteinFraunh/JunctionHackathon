# LUMI Documentation — JunctionHackathon / Surface Code + DiffQEC

> LUMI allocation: **20,000 CPU-hours, 1,000 GPU-hours, 1,000 TB-hours**
> Hardware: **LUMI-G** (AMD MI250X, 8 GCDs/node, 56 cores in low-noise mode)
> Current stack: **LUMI/25.09** + `partition/G` + `rocm` + `cray-python/3.11.7`

---

## Docs Index

| Document | What it's for |
|---|---|
| **[preflight.md](./preflight.md)** | First-time LUMI setup checklist (~30 min) |
| **[deployment.md](./deployment.md)** | Day-of workflow: sync, setup, submit jobs, collect results |

## Quick Reference

### SSH (confirm aliases with your admin — don't assume)

```bash
ssh lumi              # login node
ssh lumidt            # data transfer node
```

### Module stack (always use LUMI/25.09)

```bash
module --force purge
module load LUMI/25.09
module load partition/G    # GPU partition
module load rocm           # AMD ROCm
module load cray-python/3.11.7
```

### Slurm basics

```bash
sbatch <script>.sbatch          # submit
squeue -u $USER                 # list jobs
scancel <jobid>                 # cancel
```

### Path conventions

| Path | Use for |
|---|---|
| `$PROJECT` | Code, env, final outputs, git repos |
| `$SCRATCH` | Large active datasets, checkpoints |
| `$HOME` | SSH config, dotfiles only — avoid for data and venvs |

### Key commands for this project

```bash
# Smoke test
python -m diffqec.smoke_test

# Unit + integration tests
pytest tests/test_diffqec.py -v

# Set account (replace with your project ID from lumi-allocations)
export LUMI_PROJECT_ACCOUNT=project_REPLACE_ME
export SBATCH_ACCOUNT="$LUMI_PROJECT_ACCOUNT"
```

## LUMI-G Hardware Facts

- **GPU**: AMD MI250X (1 GCD = 1 Slurm GPU)
- **GCDs per node**: 8
- **CPU cores (low-noise mode)**: 56 (do NOT request 64)
- **Login nodes**: CPU-only — no GPU work allowed interactively

## Common Issues

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'LUMI'` | Use `module load LUMI/25.09` — NOT 23.09 |
| `Job violates accounting/QOS policy` | Check budget via `lumi-allocations`; submit with `--account="$LUMI_PROJECT_ACCOUNT"` or export `SBATCH_ACCOUNT` |
| `ModuleNotFoundError: No module named 'rocm'` | Run `module load partition/G` before `module load rocm` |
| GPU work on login node | All GPU jobs MUST go through `sbatch` |
| Home quota pressure | Move envs/data back under `$PROJECT` or `$SCRATCH`; do not build venvs in `$HOME` |

## Scripts in `lumi_deployment/`

| Script | Description |
|---|---|
| `setup_lumi_env.sh` | Bootstrap venv + install deps (run once) |
| `hello_smoke.sbatch` | Minimal 2-min smoke test (torch/ROCm check) |
| `diffqec_smoke.sbatch` | Run DiffQEC smoke test + pytest (10 min) |
| `env.example` | Template for local env vars (gitignored) |
| `README.md` | This directory's quick card |

## Non-Goals

- Do NOT run GPU work interactively on login nodes
- Do NOT hardcode project IDs or account numbers
- Do NOT put large data in `$HOME`
- Do NOT use deprecated LUMI/23.09 stack
