#!/bin/bash
# Integration test runner script for User Story 1
# Usage: ./run_integration_test.sh [--no-cleanup]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "User Story 1 - Integration Test Runner"
echo "========================================"
echo ""

# Check if backend server is running
echo "Checking if backend server is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend server is running${NC}"
else
    echo -e "${YELLOW}⚠ Backend server is not running${NC}"
    echo "Starting backend server..."
    
    # Check if virtual environment exists
    if [ ! -d "backend/venv" ]; then
        echo "Creating virtual environment..."
        cd backend
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd ..
    fi
    
    # Start server in background
    cd backend
    source venv/bin/activate
    nohup python -m src.main > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
    echo "Waiting for server to start..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend server started (PID: $BACKEND_PID)${NC}"
            break
        fi
        if [ $i -eq 10 ]; then
            echo -e "${RED}✗ Failed to start backend server${NC}"
            cat logs/backend.log
            exit 1
        fi
        sleep 2
    done
fi

echo ""

# Install test dependencies if needed
if ! python3 -c "import requests" 2>/dev/null; then
    echo "Installing test dependencies..."
    pip install requests reportlab
fi

# Run the integration test
echo "Running integration test..."
echo ""

cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python tests/test_integration_us1.py "$@"
TEST_RESULT=$?

cd ..

echo ""
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Integration test completed successfully!${NC}"
else
    echo -e "${RED}✗ Integration test failed!${NC}"
    echo "Check logs/backend.log for details"
fi

# If we started the server, ask if user wants to stop it
if [ ! -z "$BACKEND_PID" ]; then
    echo ""
    read -p "Stop the backend server? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $BACKEND_PID
        echo -e "${GREEN}✓ Backend server stopped${NC}"
    else
        echo "Backend server still running (PID: $BACKEND_PID)"
    fi
fi

exit $TEST_RESULT
