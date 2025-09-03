# Skill Extraction Template v2.0
# Optimized for comprehensive job skill analysis

## Purpose
Extract skills from job postings into structured categories for analysis and matching.

## Template Variables
- `{job_title}`: The job title/position name
- `{job_description}`: The full job description text (truncated to 3000 chars)

## Prompt Template

````markdown
# Skill Extraction Template v3.0
# Enhanced robust parsing with multiple format support

## Purpose
Extract skills from job postings into structured categories with flexible formatting for reliable parsing.

## Template Variables
- `{job_title}`: The job title/position name
- `{job_description}`: The full job description text (truncated to 3000 chars)

## Prompt Template

```
Analyze this job posting and extract skills into these categories. Use any of these formatting styles:

Job Title: {job_title}
Job Description: {job_description}

Extract skills into these 5 categories using ONE of these formats:

FORMAT OPTION 1 (Preferred):
TECHNICAL: skill1; skill2; skill3
BUSINESS: skill1; skill2; skill3
SOFT: skill1; skill2; skill3
EXPERIENCE: requirement1; requirement2; requirement3
EDUCATION: requirement1; requirement2; requirement3

FORMAT OPTION 2 (Comma-separated):
Technical Skills: skill1, skill2, skill3
Business Skills: skill1, skill2, skill3
Soft Skills: skill1, skill2, skill3
Experience Requirements: requirement1, requirement2, requirement3
Education Requirements: requirement1, requirement2, requirement3

FORMAT OPTION 3 (Bullet points):
Technical:
• skill1
• skill2
• skill3

Business:
• skill1
• skill2
• skill3

[Continue for all categories]

CATEGORY DEFINITIONS:
- TECHNICAL: Programming languages, software tools, technologies, technical methodologies
- BUSINESS: Domain knowledge, business processes, industry expertise, functional areas
- SOFT: Communication, leadership, problem-solving, interpersonal skills
- EXPERIENCE: Years of experience, specific role backgrounds, seniority requirements
- EDUCATION: Degrees, certifications, training, academic qualifications

EXTRACTION RULES:
1. Only extract skills/requirements explicitly mentioned in the job description
2. Be specific and accurate - avoid generic terms
3. If a category has no clear skills, write "None specified" or leave it blank
4. Extract 3-8 items per category when available
5. Use clear, professional language
6. Separate multiple items with semicolons, commas, or bullet points

Extract skills now:
```

## Usage Notes
- Template supports multiple response formats for robust parsing
- Parser can handle semicolon, comma, or bullet point separation
- Category names are matched with fuzzy logic (case-insensitive)
- Fallback extraction for unstructured responses
- Quality validation ensures meaningful skill extraction

## Parser Compatibility
- Handles variations in category naming
- Supports different list formats (semicolon, comma, bullets)
- Extracts skills from natural language if structured format fails
- Validates minimum skill count and category diversity

## Version History
- v1.0: Basic extraction with categories
- v2.0: Added format requirements and usage notes  
- v3.0: Multiple format support, enhanced parsing robustness, quality validation

````

## Usage Notes
- Description is automatically truncated to 3000 characters for model efficiency
- Response parsing expects exact format with category labels
- No fallback processing - LLM must succeed for extraction to work
- Optimized for accuracy over completeness

## Version History
- v1.0: Basic extraction with categories
- v2.0: Added format requirements and usage notes
