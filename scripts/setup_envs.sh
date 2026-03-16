#!/bin/bash

################################################################################
# SemBench Environment Setup (using uv)
#
# Creates isolated virtual environments to avoid dependency conflicts
# (e.g., lotus-ai requires numpy<2, palimpzest requires numpy>=2).
#
# What gets created:
#   .venvs/sembench/     - Orchestrator env (runs run.py, evaluation, plotting)
#   .venvs/lotus/        - LOTUS system env
#   .venvs/palimpzest/   - Palimpzest system env
#   .venvs/thalamusdb/   - ThalamusDB system env
#   .venvs/bigquery/     - BigQuery system env
#   ...
#
# Usage:
#   bash scripts/setup_envs.sh                    # Setup sembench + all systems
#   bash scripts/setup_envs.sh lotus palimpzest    # Setup sembench + specific systems
#   bash scripts/setup_envs.sh --list              # List available systems
#
# After setup:
#   source .venvs/sembench/bin/activate
#   python3 src/run.py --systems lotus --use-cases movie --queries 1
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENVS_DIR="$PROJECT_ROOT/.venvs"
REQS_DIR="$PROJECT_ROOT/requirements"
PYTHON_VERSION="3.12"

# All supported systems
ALL_SYSTEMS=(lotus palimpzest thalamusdb bigquery caesura flockmtl)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step()    { echo -e "${BLUE}==>${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error()   { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}!${NC} $1"; }

################################################################################
# Parse arguments
################################################################################

if [[ "$1" == "--list" ]]; then
    echo "Available systems:"
    for sys in "${ALL_SYSTEMS[@]}"; do
        if [[ -f "$REQS_DIR/$sys.txt" ]]; then
            echo "  $sys"
        fi
    done
    exit 0
fi

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: bash scripts/setup_envs.sh [SYSTEM ...]"
    echo ""
    echo "Options:"
    echo "  --list     List available systems"
    echo "  --help     Show this help message"
    echo ""
    echo "If no systems specified, sets up sembench + all: ${ALL_SYSTEMS[*]}"
    exit 0
fi

# Determine which systems to set up
if [[ $# -gt 0 ]]; then
    SYSTEMS=("$@")
else
    SYSTEMS=("${ALL_SYSTEMS[@]}")
fi

################################################################################
# Step 1: Install uv if not present
################################################################################

print_step "Checking for uv..."

if ! command -v uv &> /dev/null; then
    print_warning "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Source the env to make uv available
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        print_error "Failed to install uv. Please install manually: https://docs.astral.sh/uv/"
        exit 1
    fi
fi

print_success "uv $(uv --version) found"

################################################################################
# Step 2: Detect CUDA for PyTorch
################################################################################

TORCH_EXTRA_ARGS=""
if command -v nvidia-smi &> /dev/null; then
    print_step "NVIDIA GPU detected - will install CUDA-enabled PyTorch"
    TORCH_EXTRA_ARGS="--extra-index-url https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match"
else
    print_warning "No NVIDIA GPU detected - will install CPU-only PyTorch"
    TORCH_EXTRA_ARGS="--extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match"
fi

################################################################################
# Step 3: Create sembench orchestrator environment
################################################################################

mkdir -p "$VENVS_DIR"

# Add .venvs to .gitignore if not already there
if ! grep -q "^\.venvs" "$PROJECT_ROOT/.gitignore" 2>/dev/null; then
    echo ".venvs/" >> "$PROJECT_ROOT/.gitignore"
    print_success "Added .venvs/ to .gitignore"
fi

SEMBENCH_VENV="$VENVS_DIR/sembench"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_step "Setting up sembench orchestrator environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ -d "$SEMBENCH_VENV" ]]; then
    print_success "sembench environment already exists (skipping)"
else
    print_step "Creating venv at $SEMBENCH_VENV..."
    uv venv "$SEMBENCH_VENV" --python "$PYTHON_VERSION"

    print_step "Installing orchestrator dependencies..."
    if uv pip install -r "$REQS_DIR/base.txt" $TORCH_EXTRA_ARGS --python "$SEMBENCH_VENV/bin/python" 2>&1; then
        print_success "sembench orchestrator environment ready"
    else
        print_error "Failed to install sembench orchestrator dependencies"
        exit 1
    fi
fi

################################################################################
# Step 4: Create per-system virtual environments
################################################################################

FAILED_SYSTEMS=()

for system in "${SYSTEMS[@]}"; do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_step "Setting up environment for: $system"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    REQS_FILE="$REQS_DIR/$system.txt"
    VENV_PATH="$VENVS_DIR/$system"

    # Check requirements file exists
    if [[ ! -f "$REQS_FILE" ]]; then
        print_error "Requirements file not found: $REQS_FILE"
        FAILED_SYSTEMS+=("$system")
        continue
    fi

    # Remove existing venv if it exists
    if [[ -d "$VENV_PATH" ]]; then
        print_warning "Removing existing venv for $system..."
        rm -rf "$VENV_PATH"
    fi

    # Create virtual environment
    print_step "Creating venv at $VENV_PATH..."
    uv venv "$VENV_PATH" --python "$PYTHON_VERSION"

    # Install dependencies
    print_step "Installing dependencies for $system..."
    if uv pip install -r "$REQS_FILE" $TORCH_EXTRA_ARGS --python "$VENV_PATH/bin/python" 2>&1; then
        print_success "Dependencies installed for $system"
    else
        print_error "Failed to install dependencies for $system"
        FAILED_SYSTEMS+=("$system")
        continue
    fi

    # Verify the system-specific import works
    print_step "Verifying $system installation..."
    case "$system" in
        lotus)
            if "$VENV_PATH/bin/python" -c "import lotus; print('lotus imported successfully')" 2>/dev/null; then
                print_success "$system verified"
            else
                print_error "$system import verification failed"
                FAILED_SYSTEMS+=("$system")
            fi
            ;;
        palimpzest)
            if "$VENV_PATH/bin/python" -c "import palimpzest; print('palimpzest imported successfully')" 2>/dev/null; then
                print_success "$system verified"
            else
                print_error "$system import verification failed"
                FAILED_SYSTEMS+=("$system")
            fi
            ;;
        thalamusdb)
            if "$VENV_PATH/bin/python" -c "from tdb.data.relational import Database; print('thalamusdb imported successfully')" 2>/dev/null; then
                print_success "$system verified"
            else
                print_error "$system import verification failed"
                FAILED_SYSTEMS+=("$system")
            fi
            ;;
        bigquery)
            if "$VENV_PATH/bin/python" -c "from google.cloud import bigquery; print('bigquery imported successfully')" 2>/dev/null; then
                print_success "$system verified"
            else
                print_error "$system import verification failed"
                FAILED_SYSTEMS+=("$system")
            fi
            ;;
        *)
            print_warning "No verification check defined for $system (skipped)"
            ;;
    esac
done

################################################################################
# Summary
################################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ ${#FAILED_SYSTEMS[@]} -eq 0 ]]; then
    echo -e "${GREEN}✓ All environments set up successfully!${NC}"
else
    echo -e "${YELLOW}! Setup completed with errors for: ${FAILED_SYSTEMS[*]}${NC}"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Environments created in: $VENVS_DIR/"
echo ""

# Show sembench env
PYTHON_V=$("$SEMBENCH_VENV/bin/python" --version 2>/dev/null || echo "unknown")
echo -e "  ${GREEN}●${NC} sembench ($PYTHON_V) → $SEMBENCH_VENV  [orchestrator]"

# Show system envs
for system in "${SYSTEMS[@]}"; do
    VENV_PATH="$VENVS_DIR/$system"
    if [[ -d "$VENV_PATH" ]]; then
        PYTHON_V=$("$VENV_PATH/bin/python" --version 2>/dev/null || echo "unknown")
        echo -e "  ${GREEN}●${NC} $system ($PYTHON_V) → $VENV_PATH"
    else
        echo -e "  ${RED}●${NC} $system (not installed)"
    fi
done

echo ""
echo "To get started:"
echo -e "  ${BLUE}source .venvs/sembench/bin/activate${NC}"
echo -e "  ${BLUE}python3 src/run.py --systems lotus --use-cases movie --queries 1 --model gemini-2.5-flash --scale-factor 2000${NC}"
echo ""
echo "run.py automatically detects .venvs/ and dispatches each system"
echo "to its own isolated venv via subprocess. No conda needed."
echo ""
