#!/bin/bash
# setup.sh - Automated setup script for PDF LLM Processor
# Version: 1.0.2

set -e

echo "=== PDF LLM Processor - Automated Setup ==="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_info() { echo -e "${YELLOW}[i]${NC} $1"; }
print_step() { echo -e "${BLUE}[→]${NC} $1"; }

# Detect WSL
IS_WSL=false
if grep -qi microsoft /proc/version 2>/dev/null; then
    IS_WSL=true
    print_info "Detected WSL environment"
fi

# Check OS
if ! grep -q "Ubuntu\|Debian" /etc/os-release 2>/dev/null; then
    print_error "This script is designed for Ubuntu/Debian systems"
    exit 1
fi

print_info "Detected OS: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"

# Check not root
if [ "$EUID" -eq 0 ]; then 
    print_error "Do not run this script as root"
    exit 1
fi

# Update packages
print_step "Updating package lists..."
if sudo apt-get update -qq; then
    print_status "Package lists updated"
else
    print_error "Failed to update package lists"
    exit 1
fi

# Install Python
print_step "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_info "Installing Python 3..."
    sudo apt-get install -y python3 python3-pip python3-venv
    print_status "Python 3 installed"
else
    print_status "Python 3 already installed: $(python3 --version)"
fi

# Verify Python version
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    print_error "Python 3.7+ required (found Python $PYTHON_MAJOR.$PYTHON_MINOR)"
    exit 1
fi

# Install pip and venv
print_step "Ensuring pip and venv are installed..."
sudo apt-get install -y python3-pip python3-venv
print_status "pip and venv installed"

# Install system packages
print_step "Installing system dependencies..."
if sudo apt-get install -y curl wget git build-essential; then
    print_status "System dependencies installed"
else
    print_error "Failed to install system dependencies"
    exit 1
fi

# Go to script directory
cd "$(dirname "$0")"
APP_DIR="$(pwd)"
print_info "Application directory: $APP_DIR"

# Create venv
print_step "Creating Python virtual environment..."
if python3 -m venv venv; then
    print_status "Virtual environment created"
else
    print_error "Failed to create virtual environment"
    exit 1
fi

# Activate venv
print_step "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_step "Upgrading pip..."
pip install --upgrade pip setuptools wheel --quiet
print_status "pip upgraded"

# Install dependencies
print_step "Installing Python packages..."
if pip install -r requirements.txt --quiet; then
    print_status "Python dependencies installed"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

# Create structure
print_step "Creating application structure..."
mkdir -p uploads outputs logs
chmod 700 uploads outputs logs 2>/dev/null || true
touch uploads/.gitkeep outputs/.gitkeep logs/.gitkeep
print_status "Application structure created"

# Summary
echo ""
echo "========================================="
print_status "Setup Complete!"
echo "========================================="
echo ""
print_info "Installation directory: $APP_DIR"
echo ""
print_step "To start the application:"
echo "  ./run.sh"
echo ""
print_step "Then open: http://localhost:5000"
echo ""

if [ "$IS_WSL" = true ]; then
    print_info "WSL: Access from Windows at http://localhost:5000"
    echo ""
fi

print_status "✅ All prerequisites installed"
print_status "✅ Virtual environment configured"
print_status "✅ Python dependencies installed"
echo ""

# Verify
print_step "Verifying installation..."
if python3 -c "import flask, PyPDF2, requests; print('OK')" 2>/dev/null; then
    print_status "Python dependencies verified"
else
    print_error "Dependency verification failed"
    exit 1
fi

echo ""
read -p "Start the application now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Starting application..."
    echo ""
    ./run.sh
fi
