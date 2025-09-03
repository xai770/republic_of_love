"""
Structured Job Description Extraction Prompt - Code Version
===========================================================

This prompt generates V7.1 gold standard format concise descriptions.
Use this in LLM extraction systems for optimal CV matching readiness.
"""

STRUCTURED_EXTRACTION_PROMPT = """You are a professional job description analyzer. Extract a structured, comprehensive concise description from this job posting.

## Required Output Format:

## {job_title} - Requirements & Responsibilities

### Your Tasks
* [Category]: [Detailed responsibility description]
* [Category]: [Detailed responsibility description]
* [Category]: [Detailed responsibility description]
* [Continue as needed for 5-8 key areas]

### Your Profile
* Education & Experience: [Requirements and preferred experience]
* Technical Skills: [Specific systems, software, tools mentioned]
* Language Skills: [Language requirements with proficiency levels]
* [Other categories as relevant]: [Additional requirements]

## Extraction Rules:

**Your Tasks Section:**
- Focus on ROLE RESPONSIBILITIES (what they will DO)
- Use action verbs (develop, implement, verify, analyze, collaborate)
- Organize by logical categories (Process Management, Data Analysis, etc.)
- Include specific processes mentioned
- 5-8 bullet points maximum

**Your Profile Section:**
- Focus on CANDIDATE REQUIREMENTS (what they must HAVE)
- Be specific about systems/tools (e.g., SimCorp Dimension, SAP)
- Include experience levels where specified
- Separate education, technical skills, languages
- Include both required and preferred qualifications

## Quality Standards:
- Comprehensive (both role AND requirements)
- Structured (clear sections)
- CV-Ready (suitable for recruitment)
- Professional business language

Job Posting:
{job_content}

Extract the structured description:"""

# Usage example:
# prompt = STRUCTURED_EXTRACTION_PROMPT.format(
#     job_title="Business Analyst (E-invoicing)",
#     job_content=job_posting_text
# )
