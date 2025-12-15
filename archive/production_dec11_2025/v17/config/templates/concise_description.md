# Concise Description Template v2.0
# Professional job summary generation for Enhanced Data Dictionary format

## Purpose
Generate brief, professional job summaries that capture key role information for the Enhanced Requirements Section.

## Template Variables
- `{job_title}`: The job title/position name
- `{job_description}`: The full job description text (truncated to 2000 chars)

## Prompt Template

```
Create a concise, professional summary for this job posting.

Job Title: {job_title}
Job Description: {job_description}

Create a brief overview (2-3 sentences) that captures:
- The main role and key responsibilities
- Essential requirements and qualifications

Keep it professional, engaging, and under 200 words.

CRITICAL: Return ONLY the job description text. Do NOT include:
- Introductory phrases like "Here's a concise overview..." or "This position involves..."
- Meta-commentary about the task
- Explanatory text before or after the description
- Any formatting markers or labels

Start directly with the job description content.
```

## Quality Standards
- **Length**: 2-3 sentences, under 200 words
- **Tone**: Professional and engaging
- **Content**: Role focus, requirements, value proposition
- **Format**: Readable paragraph format (not bullet points)

## Usage Notes
- Description is automatically truncated to 2000 characters
- Used in Enhanced Requirements Section of reports
- Should complement the full job description, not replace it
- No fallback processing - LLM must succeed

## Version History
- v1.0: Basic summary generation
- v2.0: Enhanced with quality standards and usage notes
- v2.1: Added explicit "no commentary" instruction to prevent meta-text in responses (2025-10-22)
