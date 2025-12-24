#!/bin/bash

# ==============================================================================
# Vector Index Module Initialization Script
# ==============================================================================
# Purpose: Initialize the vector index module environment
# Usage: bash backend/scripts/init_vector_index.sh
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_header() {
    echo ""
    echo "=================================================================="
    echo "  $1"
    echo "=================================================================="
    echo ""
}

# ==============================================================================
# Environment Detection
# ==============================================================================

detect_environment() {
    print_header "Environment Detection"
    
    # Detect OS
    OS="$(uname -s)"
    print_info "Operating System: $OS"
    
    # Detect Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_info "Python Version: $PYTHON_VERSION"
    else
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
        print_success "Docker found: $DOCKER_VERSION"
    else
        print_warning "Docker not found. Required for Milvus deployment."
    fi
}

# ==============================================================================
# Directory Setup
# ==============================================================================

setup_directories() {
    print_header "Directory Setup"
    
    # Create data directories
    mkdir -p data/faiss_indexes
    print_success "Created: data/faiss_indexes"
    
    mkdir -p logs
    print_success "Created: logs"
    
    mkdir -p results
    print_success "Created: results"
    
    mkdir -p uploads
    print_success "Created: uploads"
    
    # Create backend specific directories
    mkdir -p backend/results
    print_success "Created: backend/results"
    
    mkdir -p backend/logs
    print_success "Created: backend/logs"
}

# ==============================================================================
# Environment File Setup
# ==============================================================================

setup_env_file() {
    print_header "Environment Configuration"
    
    if [ -f "backend/.env" ]; then
        print_warning "backend/.env already exists. Skipping creation."
        print_info "To reconfigure, delete backend/.env and run this script again."
    else
        if [ -f "backend/.env.example" ]; then
            cp backend/.env.example backend/.env
            print_success "Created backend/.env from .env.example"
            print_warning "Please update backend/.env with your actual configuration!"
        else
            print_error "backend/.env.example not found!"
            exit 1
        fi
    fi
}

# ==============================================================================
# Database Initialization
# ==============================================================================

init_database() {
    print_header "Database Initialization"
    
    # Check if psql is available
    if ! command -v psql &> /dev/null; then
        print_warning "psql not found. Skipping database initialization."
        print_info "Please run migrations manually:"
        echo "  psql -U postgres -d rag_framework -f migrations/vector_index/001_create_vector_indexes_table.sql"
        echo "  psql -U postgres -d rag_framework -f migrations/vector_index/002_create_index_statistics_table.sql"
        echo "  psql -U postgres -d rag_framework -f migrations/vector_index/003_create_vector_metadata_table.sql"
        echo "  psql -U postgres -d rag_framework -f migrations/vector_index/004_create_query_history_table.sql"
        return
    fi
    
    # Source environment variables
    if [ -f "backend/.env" ]; then
        export $(cat backend/.env | grep -v '^#' | xargs)
    fi
    
    # Extract database connection details
    DB_USER=${DB_USER:-postgres}
    DB_NAME=${DB_NAME:-rag_framework}
    
    print_info "Creating database if not exists..."
    psql -U "$DB_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
        psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"
    
    print_success "Database '$DB_NAME' ready"
    
    # Run migrations
    print_info "Running vector index migrations..."
    
    for migration in migrations/vector_index/*.sql; do
        if [ -f "$migration" ]; then
            print_info "Executing: $(basename $migration)"
            psql -U "$DB_USER" -d "$DB_NAME" -f "$migration"
        fi
    done
    
    print_success "Database migrations completed"
}

# ==============================================================================
# Docker/Milvus Setup
# ==============================================================================

setup_milvus() {
    print_header "Milvus Setup"
    
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found. Skipping Milvus setup."
        print_info "To use Milvus:"
        echo "  1. Install Docker"
        echo "  2. macOS: Run 'bash scripts/start_colima.sh'"
        echo "  3. Run 'cd docker/milvus && docker-compose up -d'"
        return
    fi
    
    # Check if running on macOS
    if [[ "$OS" == "Darwin" ]]; then
        print_info "macOS detected. Checking Colima status..."
        
        if command -v colima &> /dev/null; then
            if colima status &> /dev/null; then
                print_success "Colima is running"
            else
                print_warning "Colima not running. Run: bash scripts/start_colima.sh"
            fi
        else
            print_warning "Colima not installed. Run: bash scripts/start_colima.sh"
        fi
    fi
    
    # Check if Milvus docker-compose.yml exists
    if [ -f "docker/milvus/docker-compose.yml" ]; then
        print_info "Milvus configuration found"
        print_info "To start Milvus: cd docker/milvus && docker-compose up -d"
    else
        print_error "Milvus docker-compose.yml not found at docker/milvus/"
    fi
}

# ==============================================================================
# Python Dependencies Check
# ==============================================================================

check_dependencies() {
    print_header "Python Dependencies Check"
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    # Check critical packages
    print_info "Checking critical packages..."
    
    python3 -c "import pymilvus" 2>/dev/null && print_success "pymilvus installed" || print_warning "pymilvus not found (run: pip install -r requirements.txt)"
    python3 -c "import faiss" 2>/dev/null && print_success "faiss installed" || print_warning "faiss not found (run: pip install -r requirements.txt)"
    python3 -c "import fastapi" 2>/dev/null && print_success "fastapi installed" || print_warning "fastapi not found (run: pip install -r requirements.txt)"
    python3 -c "import sqlalchemy" 2>/dev/null && print_success "sqlalchemy installed" || print_warning "sqlalchemy not found (run: pip install -r requirements.txt)"
    
    print_info "To install all dependencies: pip install -r requirements.txt"
}

# ==============================================================================
# Verification
# ==============================================================================

verify_setup() {
    print_header "Setup Verification"
    
    # Check directories
    [ -d "data/faiss_indexes" ] && print_success "✓ FAISS index directory" || print_error "✗ FAISS index directory"
    [ -d "logs" ] && print_success "✓ Logs directory" || print_error "✗ Logs directory"
    [ -d "results" ] && print_success "✓ Results directory" || print_error "✗ Results directory"
    
    # Check config files
    [ -f "backend/.env" ] && print_success "✓ Environment file" || print_error "✗ Environment file"
    [ -f "docker/milvus/docker-compose.yml" ] && print_success "✓ Milvus config" || print_error "✗ Milvus config"
    
    # Check migrations
    [ -f "migrations/vector_index/001_create_vector_indexes_table.sql" ] && print_success "✓ Migration files" || print_error "✗ Migration files"
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    print_header "Vector Index Module Initialization"
    
    detect_environment
    setup_directories
    setup_env_file
    init_database
    setup_milvus
    check_dependencies
    verify_setup
    
    print_header "Initialization Complete"
    
    echo "Next steps:"
    echo ""
    echo "1. Update backend/.env with your configuration"
    echo "2. Install Python dependencies: pip install -r requirements.txt"
    echo "3. Start Milvus (macOS): bash scripts/start_colima.sh && cd docker/milvus && docker-compose up -d"
    echo "4. Start backend: cd backend && python -m uvicorn main:app --reload"
    echo "5. Test Milvus connection: python backend/scripts/test_milvus_connection.py"
    echo ""
    print_success "Ready to start implementing vector index functionality!"
}

# Run main function
main
