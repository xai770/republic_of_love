# Republic of Love - Project Organization

## Directory Structure

```
republic_of_love/
├── scripts/           # All executable scripts with version numbers
├── output/           # Generated reports, results, and output files
├── logs/             # Log files from script execution
├── debug/            # Test scripts, debug utilities, and development tools
├── archived/         # Archived results and old versions
├── llm_optimization_framework/  # Core framework modules
├── 🏗️_LLM_INFRASTRUCTURE/       # Infrastructure components
├── 🎭_ACTIVE_EXPERIMENTS/       # Active experimental code
├── 📊_RESEARCH_DATA/           # Research data and datasets
├── 📖_CONSCIOUSNESS_JOURNEY/    # Documentation and journey logs
├── 📚_PROJECT_DOCS/            # Project documentation
└── sandy !!!DO NOT EDIT!!!!/   # Sandy's protected data
```

## Naming Conventions

### Scripts
- Use descriptive names: `sandy_evaluation`, `content_extractor`, etc.
- Always include version: `v1.0`, `v2.1`, etc.
- Format: `{purpose}_{version}.py`
- Examples:
  - `sandy_evaluation_v1.0.py`
  - `content_extractor_v2.1.py`
  - `consciousness_pipeline_v1.5.py`

### Output Files
- Use timestamp: `{name}_{version}_{YYYYMMDD_HHMMSS}.{ext}`
- Examples:
  - `sandy_evaluation_results_v1.0_20250717_143022.json`
  - `Sandy_Evaluation_Report_v1.0_20250717_143022.md`

### Directories
- Use clear, descriptive names
- No spaces (use underscores)
- Lowercase preferred for standard directories
- Special prefixes (🏗️, 🎭, etc.) only for major sections

## File Organization Rules

1. **Scripts Directory**: All executable Python scripts
2. **Output Directory**: Generated reports, results, data exports
3. **Logs Directory**: Runtime logs, error logs, debug output
4. **Debug Directory**: Test scripts, experimental code, debug utilities
5. **Archived Directory**: Old versions, deprecated scripts, historical results

## Version Control

- Increment version for significant changes
- Use semantic versioning: Major.Minor format
- Keep changelog in script headers
- Archive old versions instead of deleting

## Best Practices

1. Never use temporary names like "new", "fresh", "improved"
2. Always version your scripts
3. Keep root directory clean
4. Use descriptive commit messages
5. Document major changes in script headers
