#!/bin/bash

# ==============================================================================
# Colima Docker Runtime Startup Script (macOS M3 Pro 36GB Optimized)
# ==============================================================================
# Purpose: Start Colima with optimized settings for Docling Serve
# Usage: bash scripts/start_colima.sh
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Optimized Configuration for M3 Pro 36GB
COLIMA_CPU=8
COLIMA_MEMORY=20
COLIMA_DISK=100

# ==============================================================================
# Helper Functions
# ==============================================================================

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ==============================================================================
# OS Detection
# ==============================================================================

detect_os() {
    OS="$(uname -s)"
    case "${OS}" in
        Darwin*)
            print_info "Detected macOS system"
            return 0
            ;;
        Linux*)
            print_warning "Detected Linux system - Colima not required"
            print_info "You can use system Docker directly"
            exit 0
            ;;
        MINGW*|MSYS*|CYGWIN*)
            print_warning "Detected Windows system - Please use Docker Desktop or WSL2"
            exit 0
            ;;
        *)
            print_error "Unknown operating system: ${OS}"
            exit 1
            ;;
    esac
}

# ==============================================================================
# Colima Installation
# ==============================================================================

check_homebrew() {
    if ! command -v brew &> /dev/null; then
        print_error "Homebrew not found. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    print_success "Homebrew found"
}

install_colima() {
    if ! command -v colima &> /dev/null; then
        print_info "Colima not found. Installing via Homebrew..."
        brew install colima
        print_success "Colima installed successfully"
    else
        print_success "Colima already installed (version: $(colima version | head -n 1))"
    fi
}

# ==============================================================================
# Colima Cleanup and Startup
# ==============================================================================

cleanup_colima() {
    print_info "Cleaning up existing Colima instance..."
    
    if colima status &> /dev/null; then
        print_info "Stopping running Colima..."
        colima stop || true
    fi
    
    print_info "Deleting existing Colima instance..."
    colima delete --force || true
    
    print_success "Colima cleanup complete"
}

start_colima() {
    print_info "Starting Colima with optimized configuration:"
    echo "  - CPU: ${COLIMA_CPU} cores"
    echo "  - Memory: ${COLIMA_MEMORY} GB"
    echo "  - Disk: ${COLIMA_DISK} GB"
    echo "  - Arch: aarch64 (Apple Silicon)"
    echo "  - VM Type: vz (Apple Virtualization)"
    echo "  - Rosetta: enabled"
    
    colima start \
        --cpu "${COLIMA_CPU}" \
        --memory "${COLIMA_MEMORY}" \
        --disk "${COLIMA_DISK}" \
        --arch aarch64 \
        --vm-type vz \
        --vz-rosetta \
        || {
            print_warning "Failed to start with VZ + Rosetta, trying without Rosetta..."
            colima start \
                --cpu "${COLIMA_CPU}" \
                --memory "${COLIMA_MEMORY}" \
                --disk "${COLIMA_DISK}" \
                --arch aarch64 \
                --vm-type vz
        }
    
    print_success "Colima started successfully"
}

# ==============================================================================
# Docker Verification
# ==============================================================================

verify_docker() {
    print_info "Verifying Docker environment..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker CLI not found. Please install Docker:"
        echo "  brew install docker"
        exit 1
    fi
    
    # Test Docker connection
    if docker ps &> /dev/null; then
        print_success "Docker is working correctly"
        docker version --format 'Client: {{.Client.Version}} | Server: {{.Server.Version}}'
        echo ""
        docker info --format 'CPUs: {{.NCPU}} | Memory: {{.MemTotal}}'
    else
        print_error "Docker connection failed. Please check Colima status:"
        echo "  colima status"
        echo "  colima logs"
        exit 1
    fi
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    echo "=================================================================="
    echo "  Colima Docker Runtime Startup Script (M3 Pro 36GB Optimized)"
    echo "=================================================================="
    echo ""
    
    detect_os
    check_homebrew
    install_colima
    cleanup_colima
    start_colima
    verify_docker
    
    echo ""
    echo "=================================================================="
    print_success "Colima setup complete! Docker is ready."
    echo "=================================================================="
    echo ""
    echo "Next steps:"
    echo "  1. Start Docling Serve:"
    echo "     cd docker/docling && docker-compose up -d"
    echo "  2. Verify containers: docker ps"
    echo "  3. Monitor resources: docker stats"
    echo ""
    echo "Useful commands:"
    echo "  - Stop Colima:   colima stop"
    echo "  - Restart:       colima restart"
    echo "  - Status:        colima status"
    echo "  - Logs:          colima logs"
    echo ""
}

# Run main function
main
