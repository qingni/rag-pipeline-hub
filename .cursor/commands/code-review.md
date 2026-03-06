---
description: 通用代码审核 - 审查代码变更，发现问题并提出解决方案（只读模式，严禁修改任何代码）
---

## User Input

```text
$ARGUMENTS
```

## CRITICAL CONSTRAINT

**READ-ONLY MODE**: You MUST NOT create, modify, or delete any files. You are strictly a reviewer. If you feel tempted to fix something, describe the fix in your report instead. Any tool call that writes to a file is FORBIDDEN.

## Step 1: Collect Latest Changes

Review the most recent一次改动。运行以下命令：

```bash
git status --short
git diff
git diff --cached
```

- If there are uncommitted changes (staged or unstaged), those are the review target.
- If the working tree is clean (no uncommitted changes), fall back to the last commit: run `git diff HEAD~1 HEAD`.

If `$ARGUMENTS` is not empty, treat it as a natural language hint for what to focus on during review (e.g., "focus on error handling"), but the review scope is always the latest changes as described above.

## Step 2: Understand Change Context

For each changed file:

1. Read the **full file** (not just the diff) to understand surrounding context, imports, dependencies
2. Identify the **intent** of the changes — what feature/fix/refactor is being implemented
3. Note the **technology stack** in use (language, framework, libraries)
4. Check if there are related test files and read them too

## Step 3: Multi-Dimensional Review

Review all changes against the following dimensions. Skip dimensions that are not applicable.

### 3.1 Correctness & Logic

- Logic errors, off-by-one errors, boundary conditions
- Null/undefined/None handling gaps
- Race conditions or concurrency issues
- Incorrect API usage or contract violations
- Type mismatches or implicit conversions

### 3.2 Architecture & Design

- SOLID principle violations
- Excessive coupling between modules
- Responsibility leakage (logic in wrong layer)
- Missing abstractions or premature abstractions
- Inconsistency with existing codebase patterns

### 3.3 Security

- Injection vulnerabilities (SQL, XSS, command injection, path traversal)
- Sensitive data exposure (secrets, PII in logs, error messages)
- Authentication/authorization gaps
- Missing or insufficient input validation
- Insecure defaults or configurations

### 3.4 Performance

- N+1 query patterns
- Unnecessary computation in loops or hot paths
- Missing pagination for unbounded queries
- Memory leaks or excessive allocation
- Missing caching for expensive operations
- Blocking operations in async context

### 3.5 Error Handling & Resilience

- Uncaught exceptions or unhandled promise rejections
- Silent failures (empty catch blocks, swallowed errors)
- Missing retry/fallback for external service calls
- Insufficient error messages for debugging
- Missing cleanup in error paths (resource leaks)

### 3.6 Maintainability & Readability

- Code duplication that should be extracted
- Functions/methods exceeding reasonable complexity
- Poor or misleading naming
- Missing type annotations (in typed languages)
- Magic numbers or hardcoded values that should be constants

### 3.7 Testing Gaps

- New logic paths without corresponding tests
- Edge cases not covered by existing tests
- Test quality concerns (brittle assertions, missing mocks)
- Integration points untested

## Step 4: Generate Review Report

Present findings using this structure:

---

### Review Report

**Scope**: [what was reviewed — files, commit range, etc.]
**Changes Summary**: [1-2 sentence summary of what the changes do]
**Files Reviewed**: [count]

---

For each issue found, use this format:

```
#### [CRITICAL | WARNING | SUGGESTION] — Issue Title

**File**: `path/to/file.ext` (line X-Y)
**Dimension**: Correctness / Architecture / Security / Performance / Error Handling / Maintainability / Testing
**Description**: Concise description of the problem.
**Impact**: Why this matters — what could go wrong.
**Suggested Fix**:
(Show the recommended code change as a code block, with brief explanation)
```

**Severity Definitions**:
- **CRITICAL**: Must fix before merge — security vulnerabilities, data loss risks, crashes, correctness bugs
- **WARNING**: Should fix — performance issues, poor practices, potential bugs under edge cases
- **SUGGESTION**: Nice to have — style improvements, better patterns, optimization opportunities

## Step 5: Summary Table

End the report with:

```
### Summary

| Severity   | Count |
|------------|-------|
| CRITICAL   | X     |
| WARNING    | X     |
| SUGGESTION | X     |

**Overall Assessment**: [PASS | PASS WITH WARNINGS | NEEDS REVISION]
- PASS: No CRITICAL or WARNING issues
- PASS WITH WARNINGS: No CRITICAL issues, but has WARNINGs
- NEEDS REVISION: Has CRITICAL issues that must be addressed

**Key Recommendations** (top 3 most important actions):
1. ...
2. ...
3. ...
```

## Reminders

- You are a reviewer, NOT an implementer. NEVER modify files.
- Be specific: always reference exact file paths and line numbers.
- Be actionable: every issue must include a concrete suggested fix with code.
- Be fair: also acknowledge what was done well if there are notable positives.
- Prioritize: focus on real issues, not style nitpicks (unless they hurt readability significantly).
