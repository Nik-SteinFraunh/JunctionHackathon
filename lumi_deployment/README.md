# LUMI Deployment — JunctionHackathon / Surface Code + DiffQEC

> Quick operational card. See `docs/lumi/README.md` for full docs.

---

## Quick Start

```bash
# 1. Sync from laptop
rsync -avP --exclude='venv/' --exclude='.git/' --exclude='results/' \
  ./ lumi:'$PROJECT/JunctionHackathon/'

# 2. On LUMI — bootstrap (one-time)
cd "$PROJECT/JunctionHackathon/lumi_deployment"
bash setup_lumi_env.sh

# 3. Activate venv
source ../venv/bin/activate

# 4. Run smoke tests
export LUMI_PROJECT_ACCOUNT=project_<your-id>
export SBATCH_ACCOUNT="$LUMI_PROJECT_ACCOUNT"
sbatch --account="$LUMI_PROJECT_ACCOUNT" hello_smoke.sbatch      # 2 min — torch/ROCm check
sbatch --account="$LUMI_PROJECT_ACCOUNT" diffqec_smoke.sbatch   # 10 min — DiffQEC + pytest

# 5. Collect results
rsync -avP lumi:'$PROJECT/JunctionHackathon/results/' ./results/
```

---

## Scripts

| Script | What it does | Walltime |
|---|---|---|
| `setup_lumi_env.sh` | Bootstrap venv + deps under the repo/project area (run once) | N/A |
| `hello_smoke.sbatch` | Minimal torch/ROCm smoke test | 2 min |
| `diffqec_smoke.sbatch` | DiffQEC smoke + pytest | 10 min |
| `env.example` | Template for `.env` (no real secrets) | — |

---

## Key Commands

```bash
# Module stack (always LUMI/25.09)
module --force purge
module load LUMI/25.09
module load partition/G
module load rocm
module load cray-python/3.11.7

# Slurm
sbatch <script>.sbatch
squeue -u $USER
scancel <jobid>
```

---

## Docs

- `docs/lumi/README.md` — overview + index
- `docs/lumi/preflight.md` — first-time setup (~30 min)
- `docs/lumi/deployment.md` — day-of workflow

---

## Safety

- **No GPU work on login nodes** — all GPU jobs go through `sbatch`
- **No hardcoded project IDs** — use `--account="$LUMI_PROJECT_ACCOUNT"` or `SBATCH_ACCOUNT`
- **No large data in `$HOME`** — use `$PROJECT` or `$SCRATCH`
- **No venvs in `$HOME`** — keep envs under `$PROJECT` or explicitly set `VENV_DIR` under `$SCRATCH`
- **Confirm SSH aliases** with your admin — don't assume `lumi`
