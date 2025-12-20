#!/bin/bash

################################################################################
# SemBench Environment Setup Script
#
# This script automatically sets up the sembench conda environment with all
# required dependencies for running benchmarks on Lotus, Palimpzest,
# ThalamusDB, and BigQuery.
#
# Usage: bash scripts/setup_environment.sh [ENV_NAME]
#        ENV_NAME: Optional name for the conda environment (default: sembench)
#
# Example: bash scripts/setup_environment.sh sembench
################################################################################

set -e  # Exit on any error

# Configuration
ENV_NAME="${1:-sembench}"  # Use first argument or default to 'sembench'

# Disable conda plugins to avoid compatibility issues
export CONDA_NO_PLUGINS=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

################################################################################
# Step 1: Check if conda is installed
################################################################################

print_step "Checking conda installation..."

if ! command -v conda &> /dev/null; then
    print_error "Conda is not installed or not in PATH"
    echo "Please install Miniconda or Anaconda first:"
    echo "https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

print_success "Conda found: $(conda --version)"

################################################################################
# Step 2: Remove existing environment if it exists
################################################################################

print_step "Checking for existing '$ENV_NAME' environment..."

if CONDA_NO_PLUGINS=true conda env list | grep -q "^$ENV_NAME "; then
    print_warning "Existing '$ENV_NAME' environment found"
    read -p "Remove and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Removing existing environment..."
        conda env remove -n "$ENV_NAME" -y
        print_success "Removed existing environment"
    else
        print_error "Setup cancelled"
        exit 1
    fi
fi

################################################################################
# Step 3: Create conda environment
################################################################################

print_step "Creating conda environment '$ENV_NAME' with Python 3.12..."

conda create -n "$ENV_NAME" python=3.12 -y --solver classic

print_success "Environment created"

################################################################################
# Step 4: Install conda packages (optimized scientific stack)
################################################################################

print_step "Installing core scientific packages via conda..."

conda install -n "$ENV_NAME" -c conda-forge -y --solver classic \
    numpy \
    pandas \
    scikit-learn \
    scipy \
    matplotlib \
    seaborn \
    pillow

print_success "Core packages installed"

################################################################################
# Step 5: Install PyTorch with CUDA support
################################################################################

print_step "Installing PyTorch with CUDA 12.4 support..."

conda install -n "$ENV_NAME" -c pytorch -c nvidia -y --solver classic \
    pytorch \
    torchvision \
    torchaudio \
    pytorch-cuda=12.4

print_success "PyTorch with CUDA installed"

################################################################################
# Step 6: Install pip packages
################################################################################

print_step "Installing pip packages (handling version conflicts)..."

# Get the conda environment path
ENV_PATH=$(CONDA_NO_PLUGINS=true conda env list | grep "^$ENV_NAME " | awk '{print $NF}')
PIP_PATH="$ENV_PATH/bin/pip"

# Install lotus-ai first (requires numpy<2.0.0)
print_step "Installing lotus-ai..."
$PIP_PATH install lotus-ai==1.1.3

# Install palimpzest without dependencies (to avoid numpy conflict)
print_step "Installing palimpzest..."
$PIP_PATH install palimpzest==0.8.2 --no-deps

# Install palimpzest dependencies separately
print_step "Installing palimpzest dependencies..."
$PIP_PATH install smolagents prettytable psutil PyLD tabulate together colorama

# Create temporary requirements file excluding lotus-ai and palimpzest
print_step "Installing remaining packages..."
grep -v "^lotus-ai" requirements.txt | grep -v "^palimpzest" > /tmp/requirements_temp.txt
$PIP_PATH install -r /tmp/requirements_temp.txt
rm /tmp/requirements_temp.txt

# Install BigQuery dependencies
print_step "Installing BigQuery dependencies..."
$PIP_PATH install google-cloud-bigquery google-cloud-bigquery-storage google-cloud-storage 

# Install remaining dependencies
print_step "Installing other dependencies..."
$PIP_PATH install dotenv overrides jinja2 db-dtypes duckdb tomli cdlib 

print_success "All pip packages installed"

################################################################################
# Step 7: Verify installation
################################################################################

print_step "Verifying installation..."

PYTHON_PATH="$ENV_PATH/bin/python"

# Test system-specific imports
if $PYTHON_PATH -c "import lotus" 2>/dev/null; then
    print_success "Lotus (lotus-ai) - OK"
else
    print_error "Lotus import failed"
fi

if $PYTHON_PATH -c "import palimpzest" 2>/dev/null; then
    print_success "Palimpzest - OK"
else
    print_error "Palimpzest import failed"
fi

if $PYTHON_PATH -c "from tdb.data.relational import Database" 2>/dev/null; then
    print_success "ThalamusDB - OK"
else
    print_error "ThalamusDB import failed"
fi

if $PYTHON_PATH -c "from google.cloud import bigquery" 2>/dev/null; then
    print_success "BigQuery - OK"
else
    print_error "BigQuery import failed"
fi

################################################################################
# Step 8: Display summary
################################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Environment: $ENV_NAME"
echo "Python: $($PYTHON_PATH --version)"
echo ""
echo "To activate the environment, run:"
echo -e "  ${BLUE}conda activate $ENV_NAME${NC}"
echo ""
echo "To test the installation, run:"
echo -e "  ${BLUE}python3 src/run.py --systems lotus --use-cases movie --queries 1 --model gemini-2.5-flash --scale-factor 2000${NC}"
echo ""
echo "For more information, see ENVIRONMENT_SETUP.md"
echo ""
