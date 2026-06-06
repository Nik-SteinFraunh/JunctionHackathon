#!/usr/bin/env bash
# setup_lumi_env.sh — bootstrap the JunctionHackathon venv on LUMI-G.
# Verified against the LUMI/25.09 software stack.
#
# Usage on LUMI from this directory:
#   bash setup_lumi_env.sh
#   PROJECT_DIR=/project/<project_id>/$USER/JunctionHackathon bash setup_lumi_env.sh
#   VENV_DIR=$PROJECT_DIR/venv bash setup_lumi_env.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
REQ_FILE="${REQ_FILE:-$PROJECT_DIR/requirements.txt}"

echo "== setup_lumi_env.sh"
echo "== project dir : $PROJECT_DIR"
echo "== venv dir    : $VENV_DIR"
echo "== req file    : $REQ_FILE"

if [[ ! -f "$REQ_FILE" ]]; then
    echo "ERROR: requirements file not found at $REQ_FILE" >&2
    exit 1
fi

# LUMI/25.09 is the current supported software stack.
# LUMI/23.09 is historical/deprecated for this project.
module --force purge
module load LUMI/25.09
module load partition/G
module load rocm
module load cray-python/3.11.7

echo "== module stack:"
module list 2>&1 | sed 's/^/  /'

# Build the venv with --system-site-packages so it can reuse Cray-provided
# optimized packages where available. Keep it under the repo/project area, not
# under $HOME, unless VENV_DIR is explicitly overridden.
if [[ -d "$VENV_DIR" ]]; then
    echo "== venv already exists at $VENV_DIR — activating and updating"
else
    echo "== creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR" --system-site-packages
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "== upgrading pip"
python -m pip install --upgrade pip setuptools wheel

echo "== installing requirements from $REQ_FILE"
python -m pip install -r "$REQ_FILE"

echo "== verifying key imports..."
python - <<'PY'
import importlib
import sys

mods = ["qiskit", "stim", "pymatching", "numpy", "torch"]
failures = []

for name in mods:
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "unknown")
        print(f"  OK: {name} ({ver})")
    except ImportError as exc:
        failures.append((name, str(exc)))
        print(f"  FAIL: {name} -> {exc}")

if failures:
    print("\nMissing required imports:", file=sys.stderr)
    for name, exc in failures:
        print(f"  - {name}: {exc}", file=sys.stderr)
    raise SystemExit(1)

import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"  torch device: {device} (ROCm PyTorch reports GPUs through the cuda API)")
PY

echo "== environment ready at $VENV_DIR"
echo '== next step: sbatch --account="$LUMI_PROJECT_ACCOUNT" hello_smoke.sbatch'
