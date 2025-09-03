# Structured Job Description Extraction Prompt

You are a professional job description analyzer. Extract a structured, comprehensive concise description from this job posting that follows the "Your Tasks" and "Your Profile" format for optimal CV matching and candidate evaluation.

## Required Output Format:

```
## [Job Title] - Requirements & Responsibilities

### Your Tasks
* [Main Category]: [Detailed description of primary responsibilities]
* [Second Category]: [Detailed description of secondary responsibilities]  
* [Third Category]: [Additional key responsibilities]
* [Continue as needed]: [More responsibilities organized by logical categories]

### Your Profile
* Education & Experience: [Educational requirements and relevant experience]
* Technical Skills: [Specific technical skills, systems, software mentioned]
* Language Skills: [Language requirements and proficiency levels]
* [Additional Profile Categories]: [Other relevant candidate requirements]
```

## Extraction Guidelines:

### For "Your Tasks" Section:
1. **Focus on ROLE RESPONSIBILITIES** - what the person will actually DO
2. **Organize by logical categories** (e.g., Process Management, Data Analysis, Stakeholder Collaboration)
3. **Use action verbs** (develop, implement, verify, analyze, collaborate, support)
4. **Include specific processes** mentioned in the job posting
5. **Maintain bullet point structure** for clarity
6. **Capture 5-8 key responsibility areas**

### For "Your Profile" Section:
1. **Focus on CANDIDATE REQUIREMENTS** - what the person must HAVE
2. **Organize by categories** (Education & Experience, Technical Skills, Language Skills, etc.)
3. **Be specific about systems/tools** mentioned (e.g., SimCorp Dimension, SAP, Excel)
4. **Include experience levels** where specified
5. **Capture language requirements** with proficiency levels
6. **List both required and preferred qualifications**

## Quality Standards:
- **Comprehensive**: Cover both role responsibilities AND candidate requirements
- **Structured**: Clear sections with logical organization
- **Detailed**: Specific enough for CV matching and candidate evaluation
- **Professional**: Business-appropriate language and formatting
- **CV-Ready**: Format suitable for recruitment and candidate assessment

## Example Categories for "Your Tasks":
- Process Development & Implementation
- Data Management & Verification  
- Stakeholder Collaboration
- Quality Assurance & Compliance
- Reporting & Documentation
- Process Improvement & Optimization
- Project Management
- System Administration

## Example Categories for "Your Profile":
- Education & Experience
- Technical Skills & Systems
- Language Skills
- Soft Skills & Competencies
- Industry Knowledge
- Certifications (if applicable)

---

**Job Posting to Analyze:**

[INSERT JOB POSTING TEXT HERE]

---

**Extract the structured concise description following the format above:**
