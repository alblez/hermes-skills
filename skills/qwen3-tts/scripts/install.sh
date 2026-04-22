#!/usr/bin/env bash
# install.sh — Full end-to-end setup for qwen3-tts skill on Apple Silicon.
#
# Creates the conda env, installs MLX deps, brew tools, spanish-tts CLI,
# and configures the MCP server in Hermes.
#
# Usage:
#   bash install.sh
#   bash install.sh --spanish-tts-path ~/Projects/spanish-tts
#   bash install.sh --skip-mcp --skip-brew
#
# Safe to re-run — every step checks if already done before acting.

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────
SPANISH_TTS_PATH="${HOME}/.qwen3-tts-spanish-voices"
HERMES_HOME="${HOME}/.hermes"
SKIP_MCP=false
SKIP_BREW=false
CONDA_ENV="qwen3-tts"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SPANISH_TTS_REPO="https://github.com/alblez/qwen3-tts-spanish-voices.git"

# ── Colors ───────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[✗]${NC} $*" >&2; }
step()  { echo -e "\n${BOLD}── $* ──${NC}"; }

# ── Parse args ───────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --spanish-tts-path) SPANISH_TTS_PATH="$2"; shift 2 ;;
        --hermes-home)      HERMES_HOME="$2"; shift 2 ;;
        --skip-mcp)         SKIP_MCP=true; shift ;;
        --skip-brew)        SKIP_BREW=true; shift ;;
        --help|-h)
            echo "Usage: bash install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --spanish-tts-path PATH  Path to spanish-tts repo (default: ~/.qwen3-tts-spanish-voices)"
            echo "  --hermes-home PATH       Hermes config directory (default: ~/.hermes)"
            echo "  --skip-mcp              Skip MCP config.yaml modification"
            echo "  --skip-brew             Skip Homebrew installs (ffmpeg, sox)"
            echo "  --help                  Show this help"
            exit 0
            ;;
        *) err "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Step 1: Prerequisites ────────────────────────────────────────────
step "Step 1: Checking prerequisites"

if [[ "$(uname)" != "Darwin" ]]; then
    err "This script requires macOS. For Linux, see SKILL.md PyTorch setup."
    exit 1
fi
info "macOS detected"

if [[ "$(uname -m)" != "arm64" ]]; then
    err "This script requires Apple Silicon (arm64). Got: $(uname -m)"
    err "For Intel Macs, MLX is not available. See SKILL.md PyTorch setup."
    exit 1
fi
info "Apple Silicon (arm64) detected"

if ! command -v conda &>/dev/null; then
    err "conda not found on PATH."
    err "Install Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi
info "conda found: $(conda --version 2>&1)"

if [[ "$SKIP_BREW" == false ]] && ! command -v brew &>/dev/null; then
    err "brew not found on PATH."
    err "Install Homebrew: https://brew.sh"
    exit 1
fi
if [[ "$SKIP_BREW" == false ]]; then
    info "brew found"
fi

# ── Step 2: Conda env ────────────────────────────────────────────────
step "Step 2: Conda environment"

if conda env list 2>/dev/null | grep -q "^${CONDA_ENV} "; then
    info "Conda env '${CONDA_ENV}' already exists — skipping creation"
else
    info "Creating conda env '${CONDA_ENV}' with Python 3.12..."
    conda create -n "$CONDA_ENV" python=3.12 -y
    info "Conda env created"
fi

# ── Step 3: MLX deps ─────────────────────────────────────────────────
step "Step 3: MLX dependencies"

REQUIREMENTS_FILE="$SKILL_DIR/requirements.txt"
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    info "Installing from $REQUIREMENTS_FILE..."
    conda run -n "$CONDA_ENV" pip install -r "$REQUIREMENTS_FILE"
else
    warn "requirements.txt not found at $REQUIREMENTS_FILE — installing inline"
    conda run -n "$CONDA_ENV" pip install \
        "mlx-audio>=0.4.0,<0.5" \
        "mlx-lm>=0.31.0,<0.32" \
        "transformers>=5.0.0,<6.0" \
        "numpy>=1.26,<3" \
        "soundfile>=0.12"
fi
info "MLX dependencies installed"

# ── Step 4: Brew tools ───────────────────────────────────────────────
step "Step 4: System tools (ffmpeg, sox)"

if [[ "$SKIP_BREW" == true ]]; then
    warn "Skipping brew installs (--skip-brew)"
else
    BREW_NEEDED=()
    command -v ffmpeg &>/dev/null || BREW_NEEDED+=(ffmpeg)
    command -v sox &>/dev/null    || BREW_NEEDED+=(sox)

    if [[ ${#BREW_NEEDED[@]} -eq 0 ]]; then
        info "ffmpeg and sox already installed"
    else
        info "Installing: ${BREW_NEEDED[*]}..."
        brew install "${BREW_NEEDED[@]}"
        info "Brew tools installed"
    fi
fi

# ── Step 5: Clone spanish-tts ────────────────────────────────────────
step "Step 5: spanish-tts repository"

SPANISH_TTS_PATH="${SPANISH_TTS_PATH/#\~/$HOME}"  # Expand tilde
if [[ -f "$SPANISH_TTS_PATH/pyproject.toml" ]]; then
    info "spanish-tts repo already exists at $SPANISH_TTS_PATH — skipping clone"
else
    PARENT_DIR="$(dirname "$SPANISH_TTS_PATH")"
    mkdir -p "$PARENT_DIR"
    info "Cloning spanish-tts to $SPANISH_TTS_PATH..."
    git clone "$SPANISH_TTS_REPO" "$SPANISH_TTS_PATH"
    info "Repository cloned"
fi

# ── Step 6: Install spanish-tts ──────────────────────────────────────
step "Step 6: spanish-tts package"

info "Installing spanish-tts with [mlx,mcp] extras..."
conda run -n "$CONDA_ENV" pip install -e "$SPANISH_TTS_PATH[mlx,mcp]"
info "spanish-tts installed"

# ── Step 7: MCP config ──────────────────────────────────────────────
step "Step 7: MCP server configuration"

HERMES_CONFIG="${HERMES_HOME}/config.yaml"

if [[ "$SKIP_MCP" == true ]]; then
    warn "Skipping MCP config (--skip-mcp)"
elif [[ ! -f "$HERMES_CONFIG" ]]; then
    warn "Hermes config not found at $HERMES_CONFIG — skipping MCP setup"
    warn "Install Hermes first: https://hermes-agent.nousresearch.com/docs/getting-started/installation"
else
    info "Updating MCP config in $HERMES_CONFIG..."
    CONDA_PYTHON="$(conda run -n "$CONDA_ENV" which python 2>/dev/null)"
    if [[ -z "$CONDA_PYTHON" ]]; then
        warn "Could not detect conda env Python path — skipping MCP config"
        warn "Manually add spanish-tts to mcp_servers in config.yaml"
    else
        info "Detected Python: $CONDA_PYTHON"
        python3 << PYEOF
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("  [!] PyYAML not available in system Python. Install: pip3 install pyyaml", file=sys.stderr)
    print("  [!] Or manually add mcp_servers.spanish-tts to config.yaml", file=sys.stderr)
    sys.exit(0)  # Non-fatal

config_path = Path("${HERMES_CONFIG}").expanduser()
with open(config_path) as f:
    config = yaml.safe_load(f) or {}

python_cmd = "${CONDA_PYTHON}"
correct_args = ["-m", "spanish_tts.mcp_server"]

mcp = config.setdefault("mcp_servers", {})
existing = mcp.get("spanish-tts", {})

needs_update = False
if not existing:
    needs_update = True
elif existing.get("command") != python_cmd:
    needs_update = True
elif existing.get("args") != correct_args:
    needs_update = True
elif existing.get("enabled") is False:
    needs_update = True

if needs_update:
    mcp["spanish-tts"] = {
        "command": python_cmd,
        "args": correct_args,
    }
    config["mcp_servers"] = mcp
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"  [✓] MCP config updated (command: {python_cmd}, args: {correct_args})")
else:
    print("  [✓] MCP config already correct")
PYEOF
    fi
    info "MCP configuration done"
fi

# ── Step 8: Smoke test ───────────────────────────────────────────────
step "Step 8: Smoke test"

if conda run -n "$CONDA_ENV" python -c "from mlx_audio.tts import load_model; print('  MLX audio: OK')" 2>/dev/null; then
    info "MLX audio import OK"
else
    warn "MLX audio import failed — model loading may still work on first use"
fi

if conda run -n "$CONDA_ENV" spanish-tts list &>/dev/null; then
    info "spanish-tts CLI OK"
    conda run -n "$CONDA_ENV" spanish-tts list
else
    warn "spanish-tts CLI test failed — check installation"
fi

# ── Step 9: Summary ──────────────────────────────────────────────────
step "Setup complete"

echo ""
echo "  Conda env:       $CONDA_ENV"
echo "  Run prefix:      conda run -n $CONDA_ENV (default)"
echo "  spanish-tts:     $SPANISH_TTS_PATH"
echo "  MCP configured:  $(if [[ "$SKIP_MCP" == false ]]; then echo "yes"; else echo "skipped"; fi)"
echo "  Hermes config:   $HERMES_CONFIG"
echo ""
echo "  Next steps:"
echo "    1. Restart Hermes to pick up MCP changes"
echo "    2. Test: hermes chat -q \"List the available Spanish TTS voices\""
echo "    3. Test: hermes chat -q \"Say 'Hello world' in English\""
echo ""
echo "  To use a venv instead of conda:"
echo "    hermes config set skills.config.qwen3-tts.run-prefix '/path/to/venv/bin/'"
echo ""
