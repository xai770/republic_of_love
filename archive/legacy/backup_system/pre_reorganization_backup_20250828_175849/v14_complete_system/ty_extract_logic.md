# TY_EXTRACT V14 - Complete Processing Logic Cookbook

**Document Version**: 2.0  
**Pipeline Version**: TY_EXTRACT V14  
**Author**: Arden  
**Date**: July 24, 2025  
**Type**: Comprehensive Cookbook & Reference

## Overview

This cookbook documents **ALL** processing approaches in the TY_EXTRACT family - both current V14 methods and historical PROD solutions. It serves as a complete reference for how problems were solved across different versions, providing context for architectural decisions and guidance for future development.

**Complete Coverage**: 
- All Enhanced Data Dictionary v4.3 fields (V14)
- Historical PROD pipeline approaches (legacy reference)
- Problem-solving comparisons across versions
- Migration guidance and lessons learned

---

## Complete Processing Flow Architecture

### High-Level Flow

```
Job File Input (JSON)
    ↓
PHASE 1: Direct Data Extraction
├── Job ID (Direct retrieval)
├── Position Title (Direct retrieval)  
├── Company (Direct retrieval)
├── Full Content (Direct retrieval)
└── Metadata Location (Direct retrieval)
    ↓
PHASE 2: LLM Processing (Two-Step + Five-Category Split)
├── Step 1: Skills Extraction (LLM Call #1)
│   ├── → TECHNICAL skills
│   ├── → BUSINESS skills  
│   ├── → SOFT skills
│   ├── → EXPERIENCE requirements
│   └── → EDUCATION requirements
├── Step 2: Concise Description (LLM Call #2)
│   └── → Human-readable summary
└── Step 3: Location Validation (LLM Call #3 - Future)
    ↓
PHASE 3: Data Transformation (Five Tables from Five Categories)
├── Technical Skills Table (from TECHNICAL category)
├── Business Skills Table (from BUSINESS category)
├── Soft Skills Table (from SOFT category)
├── Experience Requirements Table (from EXPERIENCE category)
└── Education Requirements Table (from EDUCATION category)
    ↓
PHASE 4: Metadata Generation
├── Processing Timestamp (System generated)
├── Pipeline Version (System generated)
└── Extraction Method (System generated)
    ↓
Enhanced Data Dictionary v4.3 Compliant Output
```

### LLM Processing Architecture Details

#### Two-Step Sequential Pattern
1. **Skills Extraction**: Single LLM call that returns 5-category structured output
2. **Description Generation**: Separate LLM call for human-readable summary
3. **Independence**: Each step can succeed/fail independently
4. **Templates**: Each step uses different external template file

#### Five-Category Split Pattern (Within Step 1)
1. **Single LLM Call**: One prompt processes entire job description
2. **Structured Response**: LLM returns exactly 5 categorized lists
3. **Predictable Parsing**: Each category has fixed prefix for extraction
4. **Complete Coverage**: All skills must fit into the 5 predefined buckets

### LLM Usage Patterns

V14 uses LLMs in two distinct ways:

#### 1. Two-Step Sequential Processing
- **Step 1**: Skills extraction with 5-category split
- **Step 2**: Concise description generation
- **Characteristics**: Sequential calls, different templates, combined results

#### 2. Five-Category Skills Split
Within Step 1, the LLM categorizes skills into exactly 5 buckets:
- **TECHNICAL**: Programming, tools, software systems
- **BUSINESS**: Domain knowledge, processes, methodologies  
- **SOFT**: Communication, leadership, interpersonal
- **EXPERIENCE**: Years required, background, levels
- **EDUCATION**: Degrees, certifications, qualifications

### Processing Methods Summary

| Field Category | Method | LLM Required | LLM Pattern |
|---------------|--------|---------------|-------------|
| **Core Data Section** | Direct Retrieval | ❌ No | N/A |
| **Requirements Section** | LLM Processing | ✅ Yes | Two-step sequential |
| **Skills Competency** | LLM + Parsing | ✅ Yes | Five-category split |
| **Processing Metadata** | System Generated | ❌ No | N/A |

---

## PHASE 1: Direct Data Extraction

### Core Data Section Fields
These fields are extracted directly from the JSON job file without LLM processing.

#### Job ID
- **Source**: `job_metadata.job_id` or filename
- **Processing**: Direct string extraction
- **Format**: String with optional URL wrapping
- **Example**: `"63144"` → `"[63144](https://jobs.db.com/job/63144)"`

```python
job_id = job_metadata.get('job_id', job_file.stem)
```

#### Position Title
- **Source**: `job_content.title`
- **Processing**: Direct string extraction
- **Fallback**: `"Unknown Title"` if missing
- **Example**: `"DWS - Business Analyst (E-invoicing) (m/w/d)"`

```python
title = job_content.get('title', 'Unknown Title')
```

#### Company
- **Source**: `job_content.organization.name`
- **Processing**: Direct string extraction
- **Fallback**: `"Unknown Company"` if missing
- **Example**: `"Deutsche Bank"`

```python
company = job_content.get('organization', {}).get('name', 'Unknown Company')
```

#### Full Content
- **Source**: `job_content.description`
- **Processing**: Direct string extraction (full text)
- **Purpose**: Complete job description for LLM processing
- **Size**: No truncation (preserved in full)

```python
description = job_content.get('description', '')
```

#### Metadata Location
- **Source**: `job_content.location`
- **Processing**: Location object construction
- **Components**: City, country, remote options
- **Example**: `"Frankfurt, Deutschland"`

```python
location_data = job_content.get('location', {})
location = JobLocation(
    city=location_data.get('city', 'Unknown'),
    country=location_data.get('country', 'Unknown'),
    is_remote=location_data.get('remote_options', False)
)
```

---

## PHASE 2: LLM Processing (Requirements Section)

### Step 1: Skills Extraction (LLM Call #1)

#### Purpose
Extract and categorize skills from job descriptions into the 5D Requirements framework: Technical Skills, Business Skills, Soft Skills, Experience Required, Education Required.

#### Input
- **Job Description**: Full job posting text (truncated to 3000 chars)
- **Job Title**: Position title for context
- **Template**: `config/templates/skill_extraction.md`

#### Processing Logic

```python
def extract_skills(self, job_description: str, job_title: str) -> JobSkills:
    # 1. Load external template
    template = self.config.get_template('skill_extraction')
    
    # 2. Format template with job data
    prompt = template.format(
        job_title=job_title,
        job_description=job_description[:3000]
    )
    
    # 3. Make LLM call (gemma3:1b)
    response = self._call_llm(prompt)
    
    # 4. Parse structured response
    skills = self._parse_skills_response(response.content)
    
    return skills
```

#### Expected Output Format
LLM returns structured text that gets parsed into 5 categories:

```
TECHNICAL: Python, SQL, Docker, AWS, Excel, MS Office
BUSINESS: Financial Analysis, Risk Management, E-invoicing, Asset Management
SOFT: Communication, Leadership, Problem Solving, Collaboration
EXPERIENCE: 3+ years software development, 2+ years business analysis
EDUCATION: Bachelor's degree in Computer Science, Finance certification
```

#### Skills Categories Mapping (5D Framework)

The LLM is specifically instructed to split ALL extracted skills into exactly 5 categories, following the Enhanced Data Dictionary v4.3 "5D Requirements Framework":

| Category | Purpose | Examples | Template Instruction |
|----------|---------|----------|---------------------|
| **Technical Skills** | Programming languages, tools, software systems | Python, SQL, Docker, AWS, Excel, SAP | "TECHNICAL: [comma-separated list]" |
| **Business Skills** | Domain knowledge, industry expertise, business processes | Financial Analysis, Risk Management, E-invoicing, Asset Management | "BUSINESS: [comma-separated list]" |
| **Soft Skills** | Communication, leadership, interpersonal skills | Communication, Leadership, Problem Solving, Collaboration | "SOFT: [comma-separated list]" |
| **Experience** | Years required, specific experience areas, role requirements | "3+ years software development", "2+ years business analysis" | "EXPERIENCE: [requirements list]" |
| **Education** | Degree requirements, certifications, training | "Bachelor's degree in Computer Science", "Finance certification" | "EDUCATION: [requirements list]" |

#### Five-Category Split Logic

The LLM template enforces this exact structure:

```markdown
## Required Output Format
TECHNICAL: [comma-separated technical skills]
BUSINESS: [comma-separated business skills]  
SOFT: [comma-separated soft skills]
EXPERIENCE: [experience requirements]
EDUCATION: [education requirements]
```

**Critical Design Points**:
- **Exactly 5 categories**: Never more, never less
- **Predictable parsing**: Each category has a prefix for reliable extraction
- **Comprehensive coverage**: All job requirements must fit into these 5 buckets
- **Structured output**: Enables table generation and competency analysis

### Step 2: Concise Description Generation (LLM Call #2)

#### Purpose
Generate a concise, readable summary of the job posting for the Enhanced Requirements section.

#### Input
- **Job Description**: Full job posting text (truncated to 2000 chars)
- **Job Title**: Position title for context
- **Template**: `config/templates/concise_description.md`

#### Processing Logic

```python
def extract_concise_description(self, job_description: str, job_title: str) -> str:
    # 1. Load external template
    template = self.config.get_template('concise_description')
    
    # 2. Format template with job data
    prompt = template.format(
        job_title=job_title,
        job_description=job_description[:2000]
    )
    
    # 3. Make LLM call (gemma3:1b)
    response = self._call_llm(prompt)
    
    # 4. Clean and truncate response
    description = response.content.strip()
    if len(description) > 500:
        description = description[:500] + "..."
    
    return description
```

#### Expected Output
- **Length**: Maximum 500 characters (auto-truncated)
- **Format**: Human-readable paragraph
- **Content**: Key responsibilities, requirements, and company info
- **Purpose**: Enhanced Requirements section display

### Step 3: Location Validation (Future Implementation)

#### Purpose
Validate and standardize location information using LLM-based conflict detection.

#### Current Status
- **V14 Implementation**: Basic location parsing from JSON
- **Future Enhancement**: LLM-based validation with LocationValidationSpecialistLLM v2.0
- **Template**: `config/templates/location_validation.md` (planned)

#### Current Logic
```python
# Current simple implementation
location = JobLocation(
    city=location_data.get('city', 'Unknown'),
    country=location_data.get('country', 'Unknown'),
    is_remote=location_data.get('remote_options', False)
)
validated_location = f"{location.city}, {location.country}"
```

---

## PHASE 3: Data Transformation (Skills Competency Section)

### Skills Competency Tables Generation

The Enhanced Data Dictionary v4.3 requires skills to be presented in individual table format rather than comma-separated lists. This transformation happens after LLM extraction.

#### Technical Skills Table
- **Source**: Technical skills from Step 1 LLM output  
- **Format**: Individual rows per skill with competency/experience/criticality
- **Processing**: Parse comma-separated list into structured table

```python
# Transform: "Python, SQL, Docker, AWS"
# Into table format:
technical_skills = [
    {"skill": "Python", "competency": "Intermediate", "experience": "2+ years", "criticality": "High"},
    {"skill": "SQL", "competency": "Intermediate", "experience": "2+ years", "criticality": "High"},
    {"skill": "Docker", "competency": "Advanced", "experience": "3+ years", "criticality": "Medium"},
    {"skill": "AWS", "competency": "Intermediate", "experience": "2+ years", "criticality": "Medium"}
]
```

#### Business Skills Table  
- **Source**: Business skills from Step 1 LLM output
- **Format**: Business domain skills with experience quantification
- **Processing**: Parse and infer competency levels from job context

#### Soft Skills Table
- **Source**: Soft skills from Step 1 LLM output
- **Format**: Soft skills with importance ratings
- **Processing**: Parse and assign criticality based on job requirements

#### Experience Requirements Table
- **Source**: Experience from Step 1 LLM output
- **Format**: Structured requirements with years and criticality
- **Processing**: Parse experience strings into structured format

```python
# Transform: "3+ years software development, 2+ years business analysis"
# Into table format:
experience_requirements = [
    {"requirement": "3+ years software development", "level": "Required", "years": "3+", "criticality": "High"},
    {"requirement": "2+ years business analysis", "level": "Required", "years": "2+", "criticality": "High"}
]
```

#### Education Requirements Table
- **Source**: Education from Step 1 LLM output
- **Format**: Education and qualification requirements
- **Processing**: Parse education strings into structured format

```python
# Transform: "Bachelor's degree in Computer Science, Finance certification"
# Into table format:
education_requirements = [
    {"requirement": "Bachelor's degree in Computer Science", "level": "Required", "field": "Computer Science", "criticality": "High"},
    {"requirement": "Finance certification", "level": "Preferred", "field": "Finance", "criticality": "Medium"}
]
```

### Competency Level Inference

Skills are assigned competency levels based on job description context:

| Job Language | Inferred Level | Experience Mapping |
|--------------|----------------|-------------------|
| "Expert in", "Advanced" | Expert | 5+ years |
| "Proficient", "Strong" | Advanced | 3+ years |
| "Experience with" | Intermediate | 2+ years |
| "Familiar with" | Beginner | 1+ years |
| No qualifier | Intermediate | 2+ years (default) |

### Criticality Assessment

Skills criticality is determined by position in job description:

| Context | Criticality Level | Examples |
|---------|------------------|----------|
| "Required", "Must have" | High | Core technologies, mandatory skills |
| "Preferred", "Nice to have" | Medium | Bonus skills, secondary requirements |
| "Familiar with" | Low | Optional skills, learning opportunities |

---

## PHASE 4: Metadata Generation (Processing Metadata Section)

### System-Generated Fields

These fields are automatically generated by the pipeline without LLM processing.

#### Processing Timestamp
- **Source**: System clock at job processing time
- **Format**: ISO 8601 datetime string
- **Purpose**: Quality tracking and audit trail
- **Example**: `"2025-07-23T16:32:15.123456"`

```python
processed_at = datetime.now()
timestamp = processed_at.isoformat()
```

#### Pipeline Version
- **Source**: Configuration setting from `config/pipeline.yaml`
- **Format**: Semantic version string
- **Purpose**: Version control and compatibility tracking
- **Example**: `"14.0.0"`

```python
pipeline_version = self.config.pipeline_version
```

#### Extraction Method
- **Source**: Static string identifying processing approach
- **Format**: Descriptive method name
- **Purpose**: Quality tracking and method identification
- **Example**: `"LLM-based two-step extraction"` or `"comprehensive"`

```python
extraction_method = "LLM-based two-step extraction"
```

#### Skills Total (Optional Metadata)
- **Source**: Count of extracted skills across all categories
- **Format**: Integer count
- **Purpose**: Quality assurance metric
- **Example**: `9`

```python
skills_total = skills.total_count()
```

#### Processing Status (Optional Metadata)
- **Source**: Success/failure status of LLM processing
- **Format**: Status string with emoji
- **Purpose**: Quality assurance and monitoring
- **Example**: `"✅ Completed successfully"`

```python
processing_status = "✅ Completed successfully" if success else "❌ Failed"
```

---

## Complete Field Mapping to Enhanced Data Dictionary v4.3

### Core Data Section (5 Fields)
| Field | Processing Method | LLM Required | Data Source |
|-------|------------------|---------------|-------------|
| **Job ID** | Direct Retrieval | ❌ | `job_metadata.job_id` |
| **Position Title** | Direct Retrieval | ❌ | `job_content.title` |
| **Company** | Direct Retrieval | ❌ | `job_content.organization.name` |
| **Full Content** | Direct Retrieval | ❌ | `job_content.description` |
| **Metadata Location** | Direct Retrieval | ❌ | `job_content.location` |

### Enhanced Requirements Section (2 Fields) 
| Field | Processing Method | LLM Required | Template Used |
|-------|------------------|---------------|---------------|
| **Concise Description** | LLM Processing | ✅ | `concise_description.md` |
| **Validated Location** | Basic Parsing* | ❌* | N/A (future: `location_validation.md`) |

*Future enhancement will use LLM-based location validation

### Skills Competency Section (5 Tables)
| Field | Processing Method | LLM Required | Source |
|-------|------------------|---------------|---------|
| **Technical Skills Table** | LLM + Parsing | ✅ | Step 1 TECHNICAL output |
| **Business Skills Table** | LLM + Parsing | ✅ | Step 1 BUSINESS output |
| **Soft Skills Table** | LLM + Parsing | ✅ | Step 1 SOFT output |
| **Experience Requirements Table** | LLM + Parsing | ✅ | Step 1 EXPERIENCE output |
| **Education Requirements Table** | LLM + Parsing | ✅ | Step 1 EDUCATION output |

### Processing Metadata Section (3 Fields)
| Field | Processing Method | LLM Required | Data Source |
|-------|------------------|---------------|-------------|
| **Processing Timestamp** | System Generated | ❌ | `datetime.now()` |
| **Pipeline Version** | System Generated | ❌ | `config.pipeline_version` |
| **Extraction Method** | System Generated | ❌ | Static string |

**Total**: 15 fields across 4 sections (12 main + 3 metadata)

---

## LLM Call Mechanics

### Model Configuration
- **Primary Model**: `gemma3:1b` (Ollama)
- **Endpoint**: `http://localhost:11434`
- **Timeout**: 30 seconds per call
- **Temperature**: 0.1 (low for consistency)

### Request Structure

```python
payload = {
    "model": "gemma3:1b",
    "prompt": formatted_template,
    "stream": False,
    "options": {
        "temperature": 0.1,
        "top_p": 0.9,
        "top_k": 40,
        "num_predict": 1000
    }
}
```

### Response Handling
- **Success**: Parse content according to step requirements
- **Failure**: Raise exception immediately (no fallback)
- **Timeout**: Fail after 30 seconds
- **Connection Error**: Fail immediately

### Per-Step Processing Times
- **Step 1 (Skills Extraction)**: 10-20 seconds average
- **Step 2 (Concise Description)**: 5-15 seconds average  
- **Step 3 (Location Validation)**: Not implemented (future)
- **Total LLM Time**: 15-35 seconds per job

---

## Fail-Fast Philosophy

### No Fallback Logic
V14 eliminates all fallback mechanisms from previous versions:

```python
# V13 (OLD) - Had regex fallbacks
if llm_fails:
    return regex_extraction()

# V14 (NEW) - Fail fast
if llm_fails:
    raise Exception(f"LLM extraction failed: {error}")
```

### Failure Scenarios

| Scenario | V14 Behavior | Rationale |
|----------|--------------|-----------|
| LLM Service Down | ❌ Fail immediately | Better to know service is broken |
| LLM Timeout | ❌ Fail after 30s | Predictable behavior |
| Template Missing | ❌ Fail at startup | Configuration validation |
| Parse Error | ❌ Fail with details | Template needs fixing |

### Benefits of Fail-Fast
1. **Predictable Performance**: No hidden slow fallbacks
2. **Clear Error Messages**: Know exactly what failed
3. **Forced Reliability**: LLM service must work properly
4. **Debugging**: Easy to trace problems

---

## Template System Integration

### External Templates
Both LLM steps use external Markdown templates:

```
config/templates/
├── skill_extraction.md      # Step 1 template
├── concise_description.md   # Step 2 template
└── archived/               # Version history
```

### Template Loading
Templates are loaded at runtime by ConfigManager:

```python
# ConfigManager loads templates
template = self.config.get_template('skill_extraction')

# Template contains placeholders
prompt = template.format(
    job_title=title,
    job_description=description
)
```

### Template Structure
Each template includes:
- **Instructions**: What the LLM should do
- **Format Examples**: Expected output structure
- **Context Variables**: `{job_title}`, `{job_description}`

---

## Performance Characteristics

### Timing Expectations
- **Step 1 (Skills)**: 10-20 seconds average
- **Step 2 (Description)**: 5-15 seconds average
- **Total Time**: 15-35 seconds per job
- **Parallel Processing**: None (sequential steps)

### Resource Usage
- **Memory**: Low (single job processing)
- **Network**: Two HTTP calls to Ollama
- **CPU**: Minimal (LLM runs on separate service)

### Comparison with Previous Versions
- **V13 PROD**: 390 seconds (6.5 minutes) with fallbacks
- **V14**: 25 seconds (93.6% faster) without fallbacks

---

## Quality Assurance

### Input Validation
- Job description must be non-empty
- Templates must exist and be valid
- LLM service must be reachable

### Output Validation
- Skills must be parseable into 5 categories
- Description must be valid string
- All outputs logged for audit

### Error Tracking
Every LLM call is logged with:
- **Input**: Job title, description length
- **Output**: Success/failure, response time
- **Errors**: Full error messages and stack traces

---

## Configuration Management

### LLM Settings
Defined in `config/models/gemma3_1b.yaml`:

```yaml
model:
  name: "gemma3:1b"
  provider: "ollama"
  endpoint: "http://localhost:11434"
  
parameters:
  temperature: 0.1
  timeout: 30
  max_tokens: 4000
```

### Template References
Defined in `config/pipeline.yaml`:

```yaml
templates:
  skill_extraction: "skill_extraction"
  concise_description: "concise_description"
```

### Runtime Loading
- **Startup**: ConfigManager validates all configs
- **Per Job**: Templates loaded fresh for each call
- **Errors**: Fail fast if any config is missing

---

## Development Guidelines

### Adding New LLM Steps
1. Create new template in `config/templates/`
2. Add template reference to `pipeline.yaml`
3. Implement method in `LLMInterface`
4. Add call to `TyExtractPipeline`
5. Update this documentation

### Template Development
1. Follow naming convention: `{function}_{language}_{version}.md`
2. Include clear instructions and examples
3. Use placeholder variables: `{job_title}`, `{job_description}`
4. Test with representative job postings
5. Archive old versions in `archived/`

### Error Handling
1. **Never add fallbacks** - maintain fail-fast philosophy
2. **Log everything** - full context for debugging
3. **Clear messages** - explain what failed and why
4. **Fast failure** - don't wait if something is broken

---

## Historical Approach: PROD Pipeline (Legacy Methods)

**Purpose**: Document how similar problems were solved in the PROD version to serve as a cookbook for future reference.

### PROD Architecture Overview

The PROD pipeline (`ty_extract_PROD`) used a fundamentally different approach with fallback mechanisms and hardcoded prompt logic.

#### Key Philosophical Differences

| Aspect | V14 Approach | PROD Approach |
|--------|--------------|---------------|
| **Failure Handling** | Fail-fast (no fallbacks) | LLM + Regex fallback |
| **Configuration** | External YAML/Markdown | Hardcoded prompts |
| **Processing Time** | 15-35 seconds | 390+ seconds |
| **Error Behavior** | Immediate failure | Silent fallback to regex |
| **Maintainability** | Template-driven | Code-embedded logic |

### PROD Processing Flow

```
Job File Input
    ↓
MinimalExtractor.extract_job_data()
    ↓
Try LLM Extraction (60+ second timeout)
    ↓
[If LLM fails OR times out]
    ↓
Fallback to Regex Extraction
    ↓
Generate Output
```

### PROD LLM Processing

#### Model Configuration (Hardcoded)
```python
class LLMExtractor:
    def __init__(self, model_name: str = "gemma3n:latest"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434"
```

#### Prompt Structure (Hardcoded in Code)
```python
prompt = f"""
Analyze this job posting and extract skills in exactly this JSON format:

Job Title: {job_title}
Job Description: {job_description}

Please extract and categorize skills into:
1. Technical Skills: Programming languages, software, tools, technologies
2. Business Skills: Domain knowledge, processes, methodologies, business functions
3. Soft Skills: Communication, leadership, teamwork, problem-solving abilities
4. Experience Requirements: Years of experience, specific backgrounds, levels
5. Education Requirements: Degrees, certifications, qualifications

Return ONLY a JSON object with these exact keys:
{{
    "technical_requirements": "skill1; skill2; skill3",
    "business_requirements": "skill1; skill2; skill3", 
    "soft_skills": "skill1; skill2; skill3",
    "experience_requirements": "req1; req2; req3",
    "education_requirements": "req1; req2; req3"
}}
"""
```

#### PROD LLM Call Logic
```python
def extract_skills_llm(self, job_description: str, job_title: str) -> Dict[str, Any]:
    """Extract skills using LLM analysis with hardcoded prompt"""
    
    # Hardcoded prompt (not externally configurable)
    prompt = f"[...hardcoded prompt template...]"
    
    try:
        # Long timeout, no fail-fast
        response = self._call_ollama(prompt)
        
        # Parse JSON response
        result = json.loads(response)
        
        # Validate results
        if self._validate_llm_results(result):
            return result
        else:
            raise Exception("LLM validation failed")
            
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        raise  # Will trigger regex fallback
```

### PROD Regex Fallback System

**Philosophy**: When LLM fails, use comprehensive regex patterns to extract similar information.

#### Technical Skills Extraction (Regex)
```python
def _extract_technical_requirements(self, text: str) -> str:
    """Extract technical requirements using comprehensive pattern matching"""
    
    technical_patterns = [
        # Software & Programming
        r'(SAP\s+\w+)', r'(MS\s+Office)', r'(Microsoft\s+Office)', 
        r'(Excel)', r'(SQL)', r'(Python)', r'(Java)', r'(JavaScript)',
        r'(HTML)', r'(CSS)', r'(React)', r'(Angular)', r'(Vue)',
        r'(SimCorp\s+\w+)', r'(Oracle)', r'(SWIFT)', r'(ISO\s+\d+)',
        
        # General technical terms
        r'(frameworks?)', r'(systems?)', r'(applications?)', r'(software)',
        r'(tools?)', r'(platforms?)', r'(databases?)', r'(technologies)',
        
        # German technical terms
        r'(Systeme)', r'(Anwendungen)', r'(Software)', r'(Technologien)',
        
        # Banking/Finance specific
        r'(Risk\s+management)', r'(Compliance)', r'(Regulatory)',
        r'(Trading\s+systems)', r'(Portfolio\s+management)',
        
        # Project management tools
        r'(Project\s+management)', r'(Agile)', r'(Scrum)', r'(Kanban)'
    ]
    
    technical_skills = []
    for pattern in technical_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        technical_skills.extend(matches)
    
    return "; ".join(set(technical_skills))
```

#### Business Skills Extraction (Regex)
```python
def _extract_business_requirements(self, text: str) -> str:
    """Extract business requirements using pattern matching"""
    
    business_patterns = [
        # Financial services
        r'(investment\s+\w+)', r'(portfolio\s+\w+)', r'(risk\s+\w+)',
        r'(compliance)', r'(regulatory)', r'(audit)', r'(reporting)',
        
        # Process & methodology
        r'(process\s+\w+)', r'(methodology)', r'(framework)',
        r'(analysis)', r'(strategy)', r'(planning)', r'(management)',
        
        # Industry specific
        r'(banking)', r'(finance)', r'(insurance)', r'(trading)',
        r'(investment)', r'(asset\s+management)', r'(wealth\s+management)'
    ]
    
    # Similar pattern matching logic...
    return "; ".join(extracted_business_skills)
```

### PROD vs V14 Problem-Solving Comparison

#### Problem: LLM Service Unavailable

**PROD Solution**:
```python
def extract_job_data(self, job_description: str, job_title: str = "") -> Dict[str, Any]:
    # Try LLM extraction first
    if self.llm_available:
        try:
            llm_result = self.llm_extractor.extract_skills_llm(job_description, job_title)
            if self._validate_llm_results(llm_result):
                return llm_result
        except Exception as e:
            logger.error(f"LLM failed: {e}, falling back to regex")
    
    # Fallback to regex extraction
    return self._extract_with_regex(job_description, job_title)
```

**V14 Solution**:
```python
def extract_skills(self, job_description: str, job_title: str) -> JobSkills:
    response = self._call_llm(prompt)
    
    if not response.success:
        # NO FALLBACK - fail immediately
        raise Exception(f"LLM extraction failed: {response.error_message}")
    
    return self._parse_skills_response(response.content)
```

#### Problem: LLM Response Parsing Failure

**PROD Solution**:
```python
def _validate_llm_results(self, llm_result: Dict[str, Any]) -> bool:
    """Validate and fix LLM results"""
    if not llm_result:
        return False
    
    required_keys = ['technical_requirements', 'business_requirements', 'soft_skills']
    for key in required_keys:
        if key not in llm_result:
            return False
        if len(str(llm_result[key]).strip()) <= 5:  # Minimal content check
            return False
    
    return True
```

**V14 Solution**:
```python
def _parse_skills_response(self, response: str) -> JobSkills:
    """Parse structured response - fail if unparseable"""
    skills = {"technical": [], "business": [], "soft": [], "experience": [], "education": []}
    
    for line in response.split('\n'):
        if line.startswith('TECHNICAL:'):
            skills['technical'] = self._extract_skills_from_line(line, 'TECHNICAL:')
        # ... other categories
    
    if not any(skills.values()):
        raise Exception("Failed to parse any skills from LLM response")
    
    return JobSkills(**skills)
```

#### Problem: Template Management

**PROD Solution**: Hardcoded prompts in Python code
```python
# Prompt embedded directly in method
prompt = f"""
Analyze this job posting and extract skills in exactly this JSON format:
[...rest of prompt hardcoded...]
"""
```

**V14 Solution**: External template files
```python
# Template loaded from external file
template = self.config.get_template('skill_extraction')
prompt = template.format(job_title=job_title, job_description=job_description)
```

#### Problem: Configuration Management

**PROD Solution**: Hardcoded configuration values
```python
class LLMExtractor:
    def __init__(self, model_name: str = "gemma3n:latest"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434"  # Hardcoded
        # No external config
```

**V14 Solution**: External YAML configuration
```yaml
# config/models/gemma3_1b.yaml
model:
  name: "gemma3:1b"
  provider: "ollama"
  endpoint: "http://localhost:11434"
parameters:
  temperature: 0.1
  timeout: 30
```

### PROD Lessons Learned

#### What Worked Well
1. **Robust Fallback**: Regex ensured some output even when LLM failed
2. **Comprehensive Patterns**: Extensive regex patterns caught many skills
3. **Multi-language Support**: German and English patterns in regex
4. **Industry-Specific**: Banking/finance-specific skill recognition

#### What Caused Problems
1. **Silent Failures**: Regex fallback masked LLM problems
2. **Slow Performance**: 390 seconds due to LLM timeouts
3. **Hardcoded Logic**: Prompts and config buried in code
4. **Maintenance Burden**: Updating patterns required code changes
5. **Unpredictable Behavior**: Sometimes LLM, sometimes regex, users never knew

#### Key Insights for V14 Design

1. **Fail-Fast Philosophy**: Better to know immediately when LLM fails
2. **External Configuration**: Templates and config should be editable without code changes
3. **Predictable Performance**: Consistent behavior more valuable than robustness
4. **Clear Error Messages**: Explicit failures better than silent degradation
5. **Simplified Architecture**: Two clear approaches better than hybrid complexity

### Migration Path

When moving from PROD to V14 approach:

1. **Identify Hardcoded Prompts**: Extract to external templates
2. **Remove Fallback Logic**: Replace with fail-fast error handling
3. **Externalize Configuration**: Move settings to YAML files
4. **Update Error Handling**: Clear error messages instead of silent fallbacks
5. **Performance Optimization**: Shorter timeouts, faster models
6. **Documentation**: Document all processing logic clearly

This historical perspective provides context for why V14 made specific architectural choices and serves as a reference for future pipeline evolution.

### Potential Improvements
1. **Parallel Processing**: Run both steps simultaneously
2. **Batch Processing**: Multiple jobs in single LLM call
3. **Model Selection**: Dynamic model choice per step
4. **Response Caching**: Cache similar job extractions
5. **Quality Scoring**: Automatic output quality assessment

### Research Areas
1. **Prompt Optimization**: A/B testing of templates
2. **Model Comparison**: Performance of different LLMs
3. **Structured Output**: JSON mode for more reliable parsing
4. **Multi-language**: Templates for different languages

---

## Troubleshooting

### Common Issues

**"LLM service unavailable"**
- Check Ollama service is running: `ollama serve`
- Verify model is pulled: `ollama pull gemma3:1b`
- Test connection: `curl http://localhost:11434/api/tags`

**"Template not found"**
- Verify files exist in `config/templates/`
- Check `pipeline.yaml` template references
- Ensure template names match exactly

**"Skills parsing failed"**
- Check LLM output format matches expected structure
- Review template instructions for clarity
- Verify model hasn't changed behavior

**"Timeout errors"**
- Increase timeout in model config
- Check system resources (RAM, CPU)
- Consider shorter input text

---

## Appendix

### Complete Processing Example

```python
# Input job file
job_data = {
    "job_metadata": {"job_id": "63144"},
    "job_content": {
        "title": "DWS - Business Analyst (E-invoicing) (m/w/d)",
        "description": "We seek a business analyst with 5+ years experience in financial processes...",
        "organization": {"name": "Deutsche Bank"},
        "location": {"city": "Frankfurt", "country": "Deutschland"}
    }
}

# PHASE 1: Direct Data Extraction
job_id = "63144"
title = "DWS - Business Analyst (E-invoicing) (m/w/d)"
company = "Deutsche Bank"
full_content = "We seek a business analyst with 5+ years experience..."
metadata_location = "Frankfurt, Deutschland"

# PHASE 2: LLM Processing
# Step 1: Skills extraction
skills = llm.extract_skills(
    job_description="We seek a business analyst...",
    job_title="DWS - Business Analyst (E-invoicing) (m/w/d)"
)
# → JobSkills(technical=['Excel', 'SAP'], business=['E-invoicing', 'Financial Analysis'], ...)

# Step 2: Concise description  
concise_description = llm.extract_concise_description(
    job_description="We seek a business analyst...",
    job_title="DWS - Business Analyst (E-invoicing) (m/w/d)"
)
# → "Deutsche Bank seeks a Business Analyst for e-invoicing processes with 5+ years..."

# PHASE 3: Data Transformation
# Transform skills into competency tables
technical_skills_table = [
    {"skill": "Excel", "competency": "Intermediate", "experience": "2+ years", "criticality": "High"},
    {"skill": "SAP", "competency": "Intermediate", "experience": "2+ years", "criticality": "High"}
]

business_skills_table = [
    {"skill": "E-invoicing", "competency": "Intermediate", "experience": "2+ years", "criticality": "Medium"},
    {"skill": "Financial Analysis", "competency": "Intermediate", "experience": "2+ years", "criticality": "Medium"}
]

experience_requirements_table = [
    {"requirement": "5+ years business analysis", "level": "Required", "years": "5+", "criticality": "High"}
]

education_requirements_table = [
    {"requirement": "Bachelor's degree in Finance", "level": "Required", "field": "Finance", "criticality": "High"}
]

# PHASE 4: Metadata Generation
processing_timestamp = "2025-07-23T16:32:15.123456"
pipeline_version = "14.0.0"
extraction_method = "LLM-based two-step extraction"

# Final Enhanced Data Dictionary v4.3 compliant result
extracted_job = ExtractedJob(
    # Core Data Section
    job_id="63144",
    title="DWS - Business Analyst (E-invoicing) (m/w/d)", 
    company="Deutsche Bank",
    full_content="We seek a business analyst with 5+ years...",
    metadata_location="Frankfurt, Deutschland",
    
    # Enhanced Requirements Section
    concise_description="Deutsche Bank seeks a Business Analyst for e-invoicing...",
    validated_location="Frankfurt, Deutschland",
    
    # Skills Competency Section
    technical_skills=technical_skills_table,
    business_skills=business_skills_table,
    soft_skills=soft_skills_table,
    experience_requirements=experience_requirements_table,
    education_requirements=education_requirements_table,
    
    # Processing Metadata Section
    processed_at=processing_timestamp,
    pipeline_version=pipeline_version,
    extraction_method=extraction_method
)
```

### Template Example

**`config/templates/skill_extraction.md`**:
```markdown
# Skill Extraction Instructions

Extract skills from the following job posting and categorize them.

## Job Title
{job_title}

## Job Description  
{job_description}

## Required Output Format
TECHNICAL: [comma-separated technical skills]
BUSINESS: [comma-separated business skills]  
SOFT: [comma-separated soft skills]
EXPERIENCE: [experience requirements]
EDUCATION: [education requirements]

## Example Output
TECHNICAL: Python, SQL, Docker, AWS
BUSINESS: Financial Analysis, Risk Management
SOFT: Communication, Leadership, Problem Solving
EXPERIENCE: 3+ years software development
EDUCATION: Bachelor's degree in Computer Science
```

---

**Document Status**: ✅ Complete Cookbook - All V14 Fields + Historical PROD Methods  
**Next Update**: When new processing approaches are developed or architectural changes made  
**Maintainer**: Arden

*This cookbook provides the definitive reference for ALL processing approaches in the TY_EXTRACT family. It documents current V14 methods, historical PROD solutions, and the reasoning behind architectural evolution. Use this when implementing new features, debugging issues, or making architectural decisions.*
