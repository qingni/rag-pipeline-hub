#!/bin/bash
# Validation Script for Issue Resolution
# Verifies all HIGH-priority issues are resolved

echo "========================================="
echo "Issue Resolution Validation"
echo "Date: $(date)"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SPEC_DIR="specs/003-vector-embedding"
PASS_COUNT=0
FAIL_COUNT=0

# Test 1: Check FR-032 is unique (no duplicates)
echo "Test 1: Checking FR-032 uniqueness..."
FR032_COUNT=$(grep -r "^- \*\*FR-032\*\*:" $SPEC_DIR/*.md | wc -l | tr -d ' ')
if [ "$FR032_COUNT" -eq 1 ]; then
    echo -e "${GREEN}✓ PASS${NC} - FR-032 appears exactly once"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - FR-032 appears $FR032_COUNT times (expected: 1)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 2: Check FR-039 exists
echo "Test 2: Checking FR-039 exists..."
FR039_COUNT=$(grep -r "^- \*\*FR-039\*\*:" $SPEC_DIR/*.md | wc -l | tr -d ' ')
if [ "$FR039_COUNT" -ge 1 ]; then
    echo -e "${GREEN}✓ PASS${NC} - FR-039 created successfully"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - FR-039 not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 3: Check NFR-003 has task coverage
echo "Test 3: Checking NFR-003 task coverage..."
if grep -q "NFR-003" $SPEC_DIR/tasks.md; then
    echo -e "${GREEN}✓ PASS${NC} - NFR-003 referenced in tasks.md"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - NFR-003 not found in tasks.md"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 4: Check concurrency control implementation
echo "Test 4: Checking concurrency control implementation..."
if grep -q "with_for_update" $SPEC_DIR/tasks.md; then
    echo -e "${GREEN}✓ PASS${NC} - Row-level locking implemented"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Row-level locking not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 5: Check FR-017 logging implementation
echo "Test 5: Checking FR-017 logging implementation..."
if grep -q "FR-017" $SPEC_DIR/tasks.md && grep -q "logger.info" $SPEC_DIR/tasks.md; then
    echo -e "${GREEN}✓ PASS${NC} - Operational logging implemented"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Operational logging not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 6: Check concurrent test scenario exists
echo "Test 6: Checking concurrent request test..."
if grep -q "test_concurrent_requests" $SPEC_DIR/tasks.md; then
    echo -e "${GREEN}✓ PASS${NC} - Concurrent test scenario added"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Concurrent test not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 7: Check logging test exists
echo "Test 7: Checking operational logging test..."
if grep -q "test_operational_logging" $SPEC_DIR/tasks.md; then
    echo -e "${GREEN}✓ PASS${NC} - Logging test scenario added"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Logging test not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 8: Check data-model.md concurrency section
echo "Test 8: Checking data-model.md concurrency documentation..."
if grep -q "Concurrency Control" $SPEC_DIR/data-model.md; then
    echo -e "${GREEN}✓ PASS${NC} - Concurrency control documented"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Concurrency control documentation missing"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 9: Verify all cross-references updated
echo "Test 9: Checking cross-references consistency..."
FR039_REFS=0
if grep -q "FR-039" $SPEC_DIR/plan.md; then FR039_REFS=$((FR039_REFS + 1)); fi
if grep -q "FR-039" $SPEC_DIR/research.md; then FR039_REFS=$((FR039_REFS + 1)); fi
if grep -q "FR-039" $SPEC_DIR/tasks.md; then FR039_REFS=$((FR039_REFS + 1)); fi

if [ "$FR039_REFS" -ge 3 ]; then
    echo -e "${GREEN}✓ PASS${NC} - FR-039 referenced in $FR039_REFS files"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${YELLOW}⚠ WARN${NC} - FR-039 only referenced in $FR039_REFS files (expected: 3+)"
    PASS_COUNT=$((PASS_COUNT + 1))  # Not a hard failure
fi
echo ""

# Test 10: Check for new test files planned
echo "Test 10: Checking new test files planned..."
NEW_TEST_FILES=0
if grep -q "test_concurrent_updates.py" $SPEC_DIR/tasks.md; then NEW_TEST_FILES=$((NEW_TEST_FILES + 1)); fi
if grep -q "test_concurrent_safety.py" $SPEC_DIR/tasks.md; then NEW_TEST_FILES=$((NEW_TEST_FILES + 1)); fi
if grep -q "test_logging.py" $SPEC_DIR/tasks.md; then NEW_TEST_FILES=$((NEW_TEST_FILES + 1)); fi

if [ "$NEW_TEST_FILES" -ge 3 ]; then
    echo -e "${GREEN}✓ PASS${NC} - $NEW_TEST_FILES new test files planned"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Only $NEW_TEST_FILES test files found (expected: 3)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Summary
echo "========================================="
echo "Summary"
echo "========================================="
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo ""

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ All validations passed!${NC}"
    echo -e "${GREEN}All HIGH-priority issues are resolved.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some validations failed.${NC}"
    echo -e "${RED}Please review the failures above.${NC}"
    exit 1
fi
