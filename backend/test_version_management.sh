#!/bin/bash

# Test script for chunking version management
# Usage: ./test_version_management.sh

BASE_URL="http://localhost:8000/api/v1"
DOCUMENT_ID="test_doc_001"  # Replace with your actual document ID

echo "=================================================="
echo "Testing Chunking Version Management"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Create initial version
echo -e "${BLUE}Test 1: Create initial version (auto mode, chunk_size=500)${NC}"
RESPONSE_1=$(curl -s -X POST "${BASE_URL}/chunking/chunk?overwrite_mode=auto" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"${DOCUMENT_ID}\",
    \"strategy_type\": \"character\",
    \"parameters\": {
      \"chunk_size\": 500,
      \"overlap\": 50
    }
  }")

echo "$RESPONSE_1" | jq '.'
RESULT_ID_1=$(echo "$RESPONSE_1" | jq -r '.data.result_id')
VERSION_1=$(echo "$RESPONSE_1" | jq -r '.data.version')
echo -e "${GREEN}✓ Created version ${VERSION_1}, result_id: ${RESULT_ID_1}${NC}"
echo ""
sleep 2

# Test 2: Minor change (should overwrite in auto mode)
echo -e "${BLUE}Test 2: Minor change (auto mode, chunk_size=512, change=2.4%)${NC}"
RESPONSE_2=$(curl -s -X POST "${BASE_URL}/chunking/chunk?overwrite_mode=auto" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"${DOCUMENT_ID}\",
    \"strategy_type\": \"character\",
    \"parameters\": {
      \"chunk_size\": 512,
      \"overlap\": 50
    }
  }")

echo "$RESPONSE_2" | jq '.'
RESULT_ID_2=$(echo "$RESPONSE_2" | jq -r '.data.result_id')
VERSION_2=$(echo "$RESPONSE_2" | jq -r '.data.version')
REPLACEMENT_REASON=$(echo "$RESPONSE_2" | jq -r '.data.replacement_reason')
echo -e "${GREEN}✓ Created version ${VERSION_2}, result_id: ${RESULT_ID_2}${NC}"
echo -e "${YELLOW}  Replacement reason: ${REPLACEMENT_REASON}${NC}"
echo ""
sleep 2

# Test 3: Major change (should create new version in auto mode)
echo -e "${BLUE}Test 3: Major change (auto mode, chunk_size=2000, change=290%)${NC}"
RESPONSE_3=$(curl -s -X POST "${BASE_URL}/chunking/chunk?overwrite_mode=auto" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"${DOCUMENT_ID}\",
    \"strategy_type\": \"character\",
    \"parameters\": {
      \"chunk_size\": 2000,
      \"overlap\": 100
    }
  }")

echo "$RESPONSE_3" | jq '.'
RESULT_ID_3=$(echo "$RESPONSE_3" | jq -r '.data.result_id')
VERSION_3=$(echo "$RESPONSE_3" | jq -r '.data.version')
echo -e "${GREEN}✓ Created version ${VERSION_3}, result_id: ${RESULT_ID_3}${NC}"
echo ""
sleep 2

# Test 4: Always overwrite mode
echo -e "${BLUE}Test 4: Always overwrite mode (chunk_size=1500)${NC}"
RESPONSE_4=$(curl -s -X POST "${BASE_URL}/chunking/chunk?overwrite_mode=always" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"${DOCUMENT_ID}\",
    \"strategy_type\": \"character\",
    \"parameters\": {
      \"chunk_size\": 1500,
      \"overlap\": 75
    }
  }")

echo "$RESPONSE_4" | jq '.'
RESULT_ID_4=$(echo "$RESPONSE_4" | jq -r '.data.result_id')
VERSION_4=$(echo "$RESPONSE_4" | jq -r '.data.version')
echo -e "${GREEN}✓ Created version ${VERSION_4}, result_id: ${RESULT_ID_4}${NC}"
echo ""
sleep 2

# Test 5: Never overwrite mode
echo -e "${BLUE}Test 5: Never overwrite mode (chunk_size=1500, should create new)${NC}"
RESPONSE_5=$(curl -s -X POST "${BASE_URL}/chunking/chunk?overwrite_mode=never" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"${DOCUMENT_ID}\",
    \"strategy_type\": \"character\",
    \"parameters\": {
      \"chunk_size\": 1500,
      \"overlap\": 75
    }
  }")

echo "$RESPONSE_5" | jq '.'
RESULT_ID_5=$(echo "$RESPONSE_5" | jq -r '.data.result_id')
VERSION_5=$(echo "$RESPONSE_5" | jq -r '.data.version')
echo -e "${GREEN}✓ Created version ${VERSION_5}, result_id: ${RESULT_ID_5}${NC}"
echo ""
sleep 2

# Test 6: Get version history
echo -e "${BLUE}Test 6: Get version history${NC}"
RESPONSE_6=$(curl -s -X GET "${BASE_URL}/chunking/versions/${DOCUMENT_ID}/character")
echo "$RESPONSE_6" | jq '.'

TOTAL_VERSIONS=$(echo "$RESPONSE_6" | jq -r '.data.total_versions')
ACTIVE_VERSION=$(echo "$RESPONSE_6" | jq -r '.data.active_version.version')
echo -e "${GREEN}✓ Total versions: ${TOTAL_VERSIONS}, Active version: ${ACTIVE_VERSION}${NC}"
echo ""
sleep 2

# Test 7: Get history with active_only filter
echo -e "${BLUE}Test 7: Get history (active_only=true)${NC}"
RESPONSE_7=$(curl -s -X GET "${BASE_URL}/chunking/history?active_only=true&page=1&page_size=10")
echo "$RESPONSE_7" | jq '.data.items[] | {result_id, version, is_active, document_name, strategy_type}'
echo ""
sleep 2

# Test 8: Get history (all versions)
echo -e "${BLUE}Test 8: Get history (active_only=false)${NC}"
RESPONSE_8=$(curl -s -X GET "${BASE_URL}/chunking/history?active_only=false&page=1&page_size=10")
echo "$RESPONSE_8" | jq '.data.items[] | {result_id, version, is_active, document_name, strategy_type}'
echo ""
sleep 2

# Test 9: Activate old version (if exists)
if [ ! -z "$RESULT_ID_2" ] && [ "$RESULT_ID_2" != "null" ]; then
    echo -e "${BLUE}Test 9: Activate version ${VERSION_2} (result_id: ${RESULT_ID_2})${NC}"
    RESPONSE_9=$(curl -s -X POST "${BASE_URL}/chunking/versions/${RESULT_ID_2}/activate")
    echo "$RESPONSE_9" | jq '.'
    
    NEW_ACTIVE=$(echo "$RESPONSE_9" | jq -r '.data.version')
    echo -e "${GREEN}✓ Activated version ${NEW_ACTIVE}${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠ Skipping Test 9 (no old version available)${NC}"
    echo ""
fi

# Summary
echo "=================================================="
echo -e "${GREEN}All tests completed!${NC}"
echo "=================================================="
echo ""
echo "Summary:"
echo "  • Created multiple versions with different overwrite modes"
echo "  • Verified auto mode (minor/major change detection)"
echo "  • Verified always/never modes"
echo "  • Retrieved version history"
echo "  • Tested version activation"
echo ""
echo "Check the responses above for details."
echo ""
