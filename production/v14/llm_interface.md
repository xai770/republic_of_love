# LLM Pipeline Interface Specification

**Document Version**: 1.0  
**Pipeline Version**: TY_EXTRACT V14  
**Author**: Arden  
**Date**: July 23, 2025  
**Status**: Contract Document  

## Purpose

This document defines the interface contract between the TY_EXTRACT V14 pipeline and its Large Language Model (LLM) components. It serves as the authoritative specification for model integration, prompt management, configuration binding, and quality assurance.

---

## Models Section

### Current Model Registry

| Model ID | Purpose | Config Reference | Status |
|----------|---------|------------------|---------|
| `gemma3:1b` | Primary skill extraction and job analysis | `config/models/gemma3_1b.yaml` | ✅ Active |
| `qwen3` | Backup/alternative extraction (future) | `config/models/qwen3.yaml` | 📋 Planned |
| `deepseek` | Specialized technical analysis (future) | `config/models/deepseek.yaml` | 📋 Planned |

### Model Configuration Structure

Each model requires an external YAML configuration file in `config/models/`:

```yaml
# config/models/gemma3_1b.yaml
model:
  name: "gemma3:1b"
  provider: "ollama"
  endpoint: "http://localhost:11434"
  
parameters:
  temperature: 0.1
  top_p: 0.9
  max_tokens: 4000
  timeout: 30
  
capabilities:
  - skill_extraction
  - concise_description
  - structured_analysis
  
metadata:
  version: "1.0"
  last_updated: "2025-07-23"
  performance_baseline: "25s_avg"
```

### Model Selection Logic

1. **Primary Model**: Always attempt `gemma3:1b` first
2. **Fallback Strategy**: No regex fallbacks in V14 (fail-fast approach)
3. **Model Validation**: ConfigManager validates model availability at startup
4. **Performance Monitoring**: Track response times and success rates

---

## Prompt Management

### Template Storage Structure

```
config/templates/
├── skill_extraction.md          # Primary extraction template
├── concise_description.md       # Job summary template
├── archived/
│   ├── skill_extraction_v1.md   # Version history
│   └── concise_description_v1.md
└── experimental/
    └── advanced_analysis.md     # Development templates
```

### Naming Convention

**Format**: `{function}_{language}_{version}.md`

**Examples**:
- `skill_extraction_en_v2.md` - English skill extraction, version 2
- `concise_description_de_v1.md` - German description template, version 1
- `qa_validation_en_v3.md` - QA validation template, version 3

### Template Structure

Each template must include:

```markdown
# Template Metadata
<!-- 
Template: skill_extraction_en_v2
Version: 2.0
Purpose: Extract technical, business, and soft skills from job postings
Last Updated: 2025-07-23
Compatibility: gemma3:1b, qwen3
-->

# Skill Extraction Template

## Instructions
[Template content with clear instructions for the LLM]

## Expected Output Format
[Structured format specification]

## Examples
[Sample inputs and expected outputs]
```

### Version Management

1. **Active Templates**: Stored in `config/templates/`
2. **Version History**: Archived in `config/templates/archived/`
3. **Symlink Strategy**: `current_extraction.md → skill_extraction_v2.md`
4. **Safe Switching**: ConfigManager validates template compatibility before loading

### Template Loading Process

```python
# ConfigManager template loading logic
def load_template(template_name: str) -> str:
    template_path = self.config_dir / "templates" / f"{template_name}.md"
    if not template_path.exists():
        raise ConfigError(f"Template {template_name} not found")
    
    # Validate template metadata
    self._validate_template_metadata(template_path)
    
    # Load and return template content
    return template_path.read_text(encoding='utf-8')
```

---

## Pipeline YAML Reference

### Main Pipeline Configuration

**File**: `config/pipeline.yaml`

```yaml
# Pipeline Configuration V14
pipeline:
  name: "TY_EXTRACT_V14"
  version: "14.0.0"
  
models:
  primary: "gemma3_1b"
  fallback: null  # No fallback in V14 - fail fast
  
templates:
  skill_extraction: "skill_extraction"
  concise_description: "concise_description"
  
processing:
  timeout: 120
  retry_attempts: 0  # Fail-fast approach
  batch_size: 1
  
output:
  formats: ["markdown", "excel"]
  directory: "output"
  timestamp_format: "%Y%m%d_%H%M%S"
  
validation:
  schema_enforcement: true
  required_fields: ["job_id", "position_title", "company"]
  
logging:
  level: "INFO"
  config_snapshots: true
  performance_tracking: true
```

### Configuration Binding Logic

1. **Startup**: ConfigManager loads `pipeline.yaml`
2. **Model Binding**: Primary model config loaded from `models/` directory
3. **Template Binding**: Templates loaded based on pipeline configuration
4. **Validation**: All configs validated before pipeline execution
5. **Snapshot**: Configuration state captured for each job run

### Symlink Management

**Current Implementation**: Direct file references (no symlinks yet)
**Future Enhancement**: Symlink strategy for version management

```bash
# Planned symlink structure
config/templates/current/
├── extraction -> ../skill_extraction_v2.md
├── description -> ../concise_description_v1.md
└── validation -> ../qa_validation_v1.md
```

---

## Runtime Behavior

### Fail-Fast Logic

**Philosophy**: V14 eliminates all fallback mechanisms for predictable behavior

```python
class ConfigManager:
    def validate_runtime_requirements(self) -> None:
        """Fail fast if any required config is missing or invalid"""
        
        # Model availability check
        if not self._test_model_connection():
            raise ConfigError("Primary model unavailable")
        
        # Template existence check
        for template_name in self.required_templates:
            if not self._template_exists(template_name):
                raise ConfigError(f"Required template missing: {template_name}")
        
        # Configuration consistency check
        self._validate_config_consistency()
```

### Logging Architecture

**Log Locations**:
- **Pipeline Logs**: `logs/pipeline_YYYYMMDD_HHMMSS.log`
- **Config Snapshots**: `logs/config_snapshots/config_YYYYMMDD_HHMMSS.json`
- **Performance Metrics**: `logs/performance/metrics_YYYYMMDD.json`

**Log Structure**:
```json
{
  "timestamp": "2025-07-23T16:32:15.123456",
  "level": "INFO",
  "component": "ConfigManager",
  "message": "Configuration loaded successfully",
  "config_hash": "sha256:abc123...",
  "job_id": "63144",
  "processing_time": 25.3
}
```

### Configuration Snapshots

**Purpose**: Capture exact configuration state for each job run
**Location**: `logs/config_snapshots/`
**Format**: JSON with full config tree and metadata

```json
{
  "snapshot_id": "config_20250723_163215",
  "pipeline_version": "14.0.0",
  "timestamp": "2025-07-23T16:32:15.123456",
  "config_hash": "sha256:def456...",
  "models": {
    "primary": {
      "name": "gemma3:1b",
      "config_file": "config/models/gemma3_1b.yaml",
      "parameters": { ... }
    }
  },
  "templates": {
    "skill_extraction": {
      "file": "config/templates/skill_extraction.md",
      "version": "2.0",
      "hash": "sha256:ghi789..."
    }
  }
}
```

---

## QA Layer Hooks

### Output Schema Declaration

**Location**: `config/schemas/`
**Purpose**: Define expected output structure for validation

```yaml
# config/schemas/enhanced_data_dictionary_v4.2.yaml
schema:
  version: "4.2"
  format: "enhanced_data_dictionary"
  
required_sections:
  - core_data_section
  - enhanced_requirements_section
  - skills_competency_section
  - processing_metadata
  
core_data_section:
  required_fields:
    - job_id: "string"
    - position_title: "string"
    - company: "string"
    - full_content: "string"
    - metadata_location: "string"
  
skills_competency_section:
  structure:
    technical_skills: "table"
    business_skills: "table"
    soft_skills: "table"
  table_columns:
    - skill: "string"
    - competency_level: "enum[beginner,intermediate,advanced,expert]"
    - experience_required: "string"
    - criticality: "enum[low,medium,high]"
```

### Validation Templates

**QA Validation Template**: `config/templates/qa_validation.md`

```markdown
# QA Validation Instructions

## Output Validation Checklist

1. **Format Compliance**
   - [ ] Enhanced Data Dictionary v4.2 structure present
   - [ ] All required sections included
   - [ ] Proper Markdown formatting

2. **Content Quality**
   - [ ] Job ID extracted correctly
   - [ ] Skills tables populated with realistic data
   - [ ] Competency levels are appropriate
   - [ ] No placeholder text remains

3. **Data Integrity**
   - [ ] Location validation completed
   - [ ] Skills categorization accurate
   - [ ] Experience requirements logical
```

### Pipeline Version Mapping

**QA Checkpoint Mapping**:

| Pipeline Version | QA Schema | Validation Template | Expected Output |
|------------------|-----------|-------------------|-----------------|
| V14.0.0 | enhanced_data_dictionary_v4.2 | qa_validation_v1 | 11-column format |
| V14.1.0 | enhanced_data_dictionary_v4.3 | qa_validation_v2 | Enhanced format |
| V15.0.0 | next_generation_v1 | qa_validation_v3 | Future format |

### QA Integration Points

1. **Pre-Processing**: Schema validation before LLM call
2. **Post-Processing**: Output validation against expected schema
3. **Report Generation**: QA metrics included in processing metadata
4. **Continuous Monitoring**: Track QA pass/fail rates over time

---

## Interface Contract

### Developer Responsibilities

1. **Configuration Management**: All configs must be external and version-controlled
2. **Template Updates**: Follow naming conventions and include proper metadata
3. **Model Integration**: New models require full config specification
4. **Testing**: QA validation must pass before production deployment

### Pipeline Guarantees

1. **Fail-Fast Behavior**: No silent failures or unexpected fallbacks
2. **Configuration Tracking**: Full audit trail of all configuration changes
3. **Performance Monitoring**: Consistent sub-30-second processing times
4. **Output Compliance**: All outputs match declared schema specifications

### Breaking Change Policy

**Major Version Changes**: Require updated interface specification
**Minor Version Changes**: Backward compatible configuration updates
**Patch Changes**: Bug fixes and performance improvements only

---

## Future Enhancements

### Planned Features

1. **Multi-Model Pipeline**: Parallel processing with multiple LLMs
2. **Dynamic Template Selection**: Context-aware template choosing
3. **Performance Optimization**: Caching and batching improvements
4. **Advanced QA**: Automated quality scoring and feedback loops

### Research Areas

1. **Prompt Engineering**: Systematic template optimization
2. **Model Comparison**: A/B testing framework for model performance
3. **Configuration Automation**: Smart config generation and validation
4. **Quality Metrics**: Advanced output quality measurement

---

## Appendix

### File Structure Reference

```
ty_extract_v14/
├── llm_interface.md              # This document
├── config/
│   ├── pipeline.yaml             # Main pipeline config
│   ├── models/
│   │   └── gemma3_1b.yaml        # Model configurations
│   ├── templates/
│   │   ├── skill_extraction.md   # LLM prompt templates
│   │   └── concise_description.md
│   └── schemas/
│       └── enhanced_data_dictionary_v4.2.yaml
├── logs/
│   ├── config_snapshots/         # Configuration audit trail
│   └── performance/              # Performance metrics
└── [core pipeline files...]
```

### Configuration Hash Algorithm

**Method**: SHA-256 of concatenated config content
**Purpose**: Detect configuration drift and ensure reproducibility
**Usage**: Included in all log entries and snapshots

---

**Document Status**: ✅ Contract Established  
**Next Review**: Upon major version changes or significant architecture updates  
**Maintainer**: Arden  

*This document serves as the authoritative interface specification between TY_EXTRACT V14 and its LLM components. All development and deployment decisions should reference this contract.*
