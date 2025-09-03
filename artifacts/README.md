# Artifacts

**Owner**: Shared  
**Purpose**: Experimental outputs and test artifacts

## Structure

- Non-production run results
- Test outputs and validation artifacts
- Experimental data and reports

## Usage

```bash
# Check experimental outputs
ls llm_tasks/

# Review test artifacts
find . -name "*.json" | head -10
```

## Guidelines

- Outputs from experiments and tests (not production)
- Production outputs are in `production/*/output/`
- Temporary and disposable content
- Can be cleaned periodically
