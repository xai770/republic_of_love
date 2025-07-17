# Implementation Blueprint: LLM-First Requirements Extraction

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT: Job Description                   │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM EXTRACTION ENGINE                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Tech Skills    │  │  Business Req   │  │  Soft Skills    │ │
│  │  Extractor      │  │  Extractor      │  │  Extractor      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │  Experience     │  │  Education      │                      │
│  │  Extractor      │  │  Extractor      │                      │
│  └─────────────────┘  └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION LAYER                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Reference      │  │  Confidence     │  │  Consistency    │ │
│  │  Data Check     │  │  Scoring        │  │  Validation     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT FORMATTER                            │
│              (Template-Based, Structured)                      │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. LLM Extraction Engine
Each extractor follows this pattern:
```python
class TechnicalRequirementsExtractor:
    def __init__(self, ollama_client, reference_data):
        self.client = ollama_client
        self.tech_stack_data = reference_data['tech_stacks']
        self.template = self._load_template()
    
    def extract(self, job_description):
        prompt = self._build_prompt(job_description)
        response = self.client.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}],
            template=self.template
        )
        return self._parse_response(response)
    
    def _build_prompt(self, job_desc):
        return f"""
        Analyze this job description and extract technical requirements.
        Focus on: programming languages, frameworks, databases, tools, platforms.
        
        Job Description:
        {job_desc}
        
        Reference Technologies (use these exact names when possible):
        {json.dumps(self.tech_stack_data, indent=2)}
        
        Provide confidence scores (1-10) for each extracted requirement.
        """
```

### 2. Validation Layer
```python
class ValidationEngine:
    def __init__(self, reference_data):
        self.reference_data = reference_data
    
    def validate_extraction(self, extraction_result):
        validated = {}
        
        # Check against reference data
        validated['technical'] = self._validate_tech_skills(
            extraction_result['technical']
        )
        
        # Confidence scoring
        validated['confidence_score'] = self._calculate_confidence(
            extraction_result
        )
        
        # Consistency checks
        validated['consistency_flags'] = self._check_consistency(
            extraction_result
        )
        
        return validated
    
    def _validate_tech_skills(self, tech_skills):
        validated_skills = []
        for skill in tech_skills:
            if skill['name'] in self.reference_data['technologies']:
                validated_skills.append({
                    **skill,
                    'validated': True,
                    'canonical_name': self.reference_data['technologies'][skill['name']]
                })
            else:
                validated_skills.append({
                    **skill,
                    'validated': False,
                    'requires_review': True
                })
        return validated_skills
```

### 3. Template System
```python
# Template for technical requirements extraction
TECH_REQUIREMENTS_TEMPLATE = """
TECHNICAL_REQUIREMENTS:
{{ range .technical_skills }}
- SKILL: {{ .name }}
  LEVEL: {{ .level }}
  PRIORITY: {{ .priority }}
  CONFIDENCE: {{ .confidence }}/10
{{ end }}

FRAMEWORKS:
{{ range .frameworks }}
- NAME: {{ .name }}
  VERSION: {{ .version }}
  CONFIDENCE: {{ .confidence }}/10
{{ end }}

DATABASES:
{{ range .databases }}
- TYPE: {{ .type }}
  SPECIFIC: {{ .name }}
  CONFIDENCE: {{ .confidence }}/10
{{ end }}

OVERALL_CONFIDENCE: {{ .overall_confidence }}/10
"""
```

### 4. Reference Data Management
```json
{
  "programming_languages": {
    "javascript": {
      "canonical_name": "JavaScript",
      "aliases": ["js", "node.js", "nodejs"],
      "category": "programming_language",
      "popularity_rank": 1
    },
    "python": {
      "canonical_name": "Python",
      "aliases": ["py", "python3"],
      "category": "programming_language",
      "popularity_rank": 2
    }
  },
  "frameworks": {
    "react": {
      "canonical_name": "React",
      "aliases": ["reactjs", "react.js"],
      "category": "frontend_framework",
      "language": "javascript"
    }
  },
  "education_degrees": {
    "bachelor": {
      "canonical_name": "Bachelor's Degree",
      "aliases": ["bs", "ba", "bachelor", "undergraduate"],
      "level": "undergraduate"
    }
  }
}
```

## Implementation Strategy

### Phase 1: Core LLM Integration
1. **Setup Ollama Integration**
   - Install and configure Ollama
   - Create base extraction classes
   - Implement template-based output

2. **Build Reference Data**
   - Create JSON files for technologies, degrees, etc.
   - Implement data loading and caching
   - Add update mechanisms

### Phase 2: Validation & Quality
1. **Implement Validation Layer**
   - Reference data validation
   - Confidence scoring
   - Consistency checks

2. **Add Error Handling**
   - Fallback mechanisms
   - Retry logic
   - Graceful degradation

### Phase 3: Scale & Performance
1. **Optimize Performance**
   - Implement caching
   - Add batch processing
   - Monitor API usage

2. **Add Monitoring**
   - Quality metrics tracking
   - Performance dashboards
   - Alert systems

## Testing Strategy

### Unit Tests
- Test each extractor independently
- Mock LLM responses for consistent testing
- Validate reference data integration

### Integration Tests
- Test full extraction pipeline
- Validate template output parsing
- Test error handling scenarios

### Performance Tests
- Measure extraction speed
- Monitor API costs
- Test batch processing limits

## Zero-Dependency Demo Script
```python
#!/usr/bin/env python3
"""
Zero-dependency demo of LLM-first requirements extraction.
Tests Ollama integration and template-based output.
"""

import json
import subprocess
import sys
from pathlib import Path

def test_ollama_availability():
    """Test if Ollama is available and responsive."""
    try:
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def main():
    print("🧪 Testing LLM-First Requirements Extraction...")
    
    # Test Ollama availability
    if not test_ollama_availability():
        print("❌ Ollama not available. Please install and start Ollama.")
        sys.exit(1)
    
    print("✅ Ollama is available")
    
    # Test template-based extraction
    # ... (implementation continues)
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    main()
```

This blueprint provides a concrete path forward that balances the need for LLM intelligence with practical scalability and quality concerns. The key is the validation layer that ensures we get the benefits of LLM understanding while maintaining data quality and consistency.

Would you like me to implement any specific part of this blueprint, or shall we refine the golden rules further based on this technical approach?
