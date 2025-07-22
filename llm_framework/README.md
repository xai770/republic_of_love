#!/usr/bin/env python3
"""
LLM Optimization Framework - README
===================================

A comprehensive framework for evaluating, comparing, and optimizing Large Language Models (LLMs).
"""

# Framework Overview

The LLM Optimization Framework provides a complete toolkit for:

✅ **Dialogue Log Parsing** - Parse and structure LLM response data  
✅ **Quality Assessment** - Multi-dimensional quality scoring  
✅ **Performance Metrics** - Comprehensive performance evaluation  
✅ **Baseline Comparison** - Compare models against baseline performance  
✅ **Professional Reporting** - Generate detailed markdown and JSON reports  
✅ **Flexible Configuration** - Customizable evaluation parameters  

## Quick Start

```python
from llm_optimization_framework import LLMOptimizationFramework
from llm_optimization_framework.configs.settings import PresetConfigs

# Setup with quality-focused configuration
config = PresetConfigs.quality_focused()
config.baseline_model = "gemma3n:latest"

# Initialize framework
framework = LLMOptimizationFramework(config)

# Run complete optimization pipeline
results = framework.run_complete_optimization("path/to/dialogue/logs")

print(f"Top performer: {results['top_performer']}")
```

## Framework Architecture

```
llm_optimization_framework/
├── core/                    # Core optimization logic
│   ├── __init__.py         # Main framework integration
│   ├── comparator.py       # Baseline comparison engine
│   └── metrics.py          # Performance metrics calculation
├── utils/                   # Utility modules
│   ├── dialogue_parser.py  # Parse dialogue logs
│   └── quality_assessor.py # Quality assessment algorithms
├── reporters/               # Report generation
│   └── markdown.py         # Markdown report generator
├── configs/                 # Configuration management
│   └── settings.py         # Configuration classes and presets
└── examples/               # Usage examples
    └── basic_usage.py      # Basic usage demonstration
```

## Key Features

### 🔍 Quality Assessment
- Response completeness analysis
- Structure and format validation
- Content relevance scoring
- Multi-dimensional quality metrics

### 📊 Performance Metrics
- **Quality (40% weight)**: Completeness, structure, relevance
- **Performance (25% weight)**: Task completion, appropriateness
- **Consistency (20% weight)**: Format and quality consistency
- **Efficiency (10% weight)**: Response optimization
- **Reliability (5% weight)**: Error rates and stability

### 🎯 Baseline Comparison
- Similarity analysis across multiple dimensions
- Upgrade recommendation engine
- Risk assessment for model changes
- Confidence scoring for comparisons

### 📄 Professional Reporting
- Comprehensive markdown reports with rankings
- Quick summary reports for rapid assessment
- JSON exports for integration
- Visual performance indicators

## Configuration Presets

The framework includes several preset configurations:

### Quality Focused
```python
config = PresetConfigs.quality_focused()
# Weights: Quality=60%, Performance=20%, Consistency=15%
```

### Performance Focused
```python
config = PresetConfigs.performance_focused()
# Weights: Performance=40%, Quality=30%, Consistency=20%
```

### Production Ready
```python
config = PresetConfigs.production_ready()
# Higher thresholds, balanced weights for production deployment
```

### Custom Configuration
```python
config = ConfigurationManager().create_custom_config(
    project_name="My Optimization",
    baseline_model="my_baseline_model",
    confidence_threshold=0.8
)
```

## Usage Examples

### Basic Optimization
```python
# Simple optimization with default settings
from llm_optimization_framework.core import quick_optimization

results = quick_optimization(
    data_source="dialogue_logs/",
    baseline_model="gemma3n:latest",
    output_dir="results/"
)
```

### Advanced Usage
```python
# Full control over the optimization process
framework = LLMOptimizationFramework(custom_config)

# Load and parse dialogue data
framework.load_dialogue_data("dialogue_logs/")

# Run individual components
quality_results = framework.run_quality_assessment()
metrics = framework.calculate_performance_metrics()
comparisons = framework.run_baseline_comparison()

# Generate reports
reports = framework.generate_reports("output/")
```

### Batch Processing
```python
# Process multiple datasets
datasets = ["dataset1/", "dataset2/", "dataset3/"]
results = []

for dataset in datasets:
    result = quick_optimization(dataset)
    results.append(result)
```

## Report Examples

### Quick Summary Output
```markdown
# Quick LLM Performance Summary

**Generated:** 2024-01-15 14:30 | **Models:** 5

## 🏆 Top Performers

| Rank | Model | Score | Grade |
|------|-------|-------|-------|
| 1 | `claude-3-sonnet` | 0.892 | A |
| 2 | `gpt-4` | 0.876 | A |
| 3 | `gemma3n:latest` | 0.743 | B+ |

## 📊 Category Leaders
- **Quality:** claude-3-sonnet (0.934)
- **Performance:** gpt-4 (0.891)
- **Consistency:** gemma3n:latest (0.812)
```

### Comprehensive Report Features
- Executive summary with key findings
- Detailed model rankings and comparisons
- Individual metric breakdowns
- Baseline comparison analysis
- Strategic recommendations
- Methodology documentation

## Integration Guide

### With Existing Pipelines
```python
# Integration with existing model evaluation
def evaluate_new_model(model_responses):
    # Parse responses into framework format
    entries = convert_to_dialogue_entries(model_responses)
    
    # Run optimization
    framework = LLMOptimizationFramework()
    framework.dialogue_entries = {"new_model": entries}
    
    metrics = framework.calculate_performance_metrics()
    return metrics["new_model"]
```

### With CI/CD Systems
```python
# Automated evaluation in CI/CD
def automated_model_evaluation():
    results = quick_optimization("test_data/")
    
    # Check if top performer meets threshold
    top_score = results["rankings"]["overall"][0][1]
    if top_score < 0.8:
        raise Exception("Model performance below threshold")
    
    return results
```

## Customization Options

### Custom Test Types
```python
# Add custom test configuration
config.test_configs["custom_test"] = TestConfiguration(
    test_id="custom_test",
    display_name="Custom Test",
    key_terms=["custom", "terms"],
    length_range=(100, 500)
)
```

### Custom Metrics
```python
# Extend metrics calculation
class CustomMetrics(PerformanceMetrics):
    def calculate_custom_metric(self, entries):
        # Custom metric implementation
        pass
```

### Custom Reporting
```python
# Create custom report format
class CustomReporter:
    def generate_report(self, metrics):
        # Custom report generation
        pass
```

## Best Practices

### Data Preparation
- Ensure dialogue logs are consistently formatted
- Include diverse test scenarios
- Validate data completeness before processing

### Configuration
- Start with preset configurations
- Adjust weights based on your specific priorities
- Validate configuration before running optimization

### Interpretation
- Consider confidence levels when making decisions
- Use baseline comparisons for model selection
- Focus on consistent performers for production

### Reporting
- Generate both quick and comprehensive reports
- Share reports with stakeholders for decision making
- Archive reports for historical comparison

## Troubleshooting

### Common Issues

**"No dialogue entries found"**
- Check file paths and permissions
- Verify dialogue log format
- Ensure data directory structure is correct

**"Configuration validation failed"**
- Check that weights sum to 1.0
- Verify threshold values are in correct order
- Validate test configuration parameters

**"Baseline model not found"**
- Ensure baseline model exists in data
- Check model name spelling
- Verify baseline model has sufficient data

### Performance Optimization
- Use smaller datasets for initial testing
- Adjust confidence thresholds to filter low-quality data
- Enable detailed logging only when debugging

## Contributing

The framework is designed to be extensible. Areas for contribution:

- Additional quality assessment algorithms
- New performance metrics
- Enhanced reporting formats
- Integration connectors
- Custom configuration templates

## Changelog

### Version 1.0.0
- Initial framework release
- Core optimization pipeline
- Baseline comparison engine
- Markdown reporting
- Configuration presets

---

*For detailed API documentation, see individual module docstrings.*  
*For examples and tutorials, check the `examples/` directory.*
