# CI Gates Configuration

This document outlines the CI gates that enforce the "no merge without green" rule.

## Required Gates

### 1. Test Gate
```yaml
# .github/workflows/test.yml
name: Test Gate
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: make test
      - name: Fail on red
        run: exit $?
```

### 2. Validation Gate  
```yaml
# .github/workflows/validate.yml  
name: Validation Gate
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run validation
        run: make validate
      - name: Fail on red
        run: exit $?
```

### 3. Combined Gate
```yaml
# .github/workflows/ci.yml
name: CI Gate
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: CI Gate Check
        run: make ci-gate
```

## Branch Protection

Configure branch protection rules:
- Require status checks to pass
- Require branches to be up to date
- Include administrators
- Required checks:
  - Test Gate
  - Validation Gate

## Local Testing

Before pushing:
```bash
make test      # Must pass
make validate  # Must pass  
make ci-gate   # Combined check
```

This enforces the operating gate: "No merge to ty_learn surfaces without green eval on the gold set for the affected transaction."
