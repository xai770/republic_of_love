TO: Zara, Hammer of Implementation (Valhalla Forge)
FROM: Zara, Strategic Advisor & Xai, Alliance Leader
RE: NEW VERSION REQUEST - Enhanced Skill Extraction v2.0
PRIORITY: Implementation Enhancement - VERSION SAFETY CRITICAL
Dearest Forge-Self,
Gemma3n has delivered magnificent prompt enhancements that will revolutionize our CV matching precision. We need a NEW VERSION of our extraction script incorporating her advanced methodology.

**Revised Prompt Template:**

```
You are a master strategist tasked with extracting key skills from a job description and categorizing them into five distinct buckets: Technical Skills, Domain Expertise, Methodology & Frameworks, Soft 
Skills, and Experience & Qualifications. 

Your output should be formatted using the following template:

=== [CATEGORY NAME] ===
- [Skill Name] ([Competency Level], [Experience Level]) [Synonyms: List of synonyms]: [Criticality Score]

**Example Output:**

=== TECHNICAL SKILLS ===
- Python Programming (Advanced, 2-5 years) [Synonyms: Python, Py, Python Dev]: HIGH
- Data Analysis (Intermediate, Entry-level) [Synonyms: Data Analytics, Analytics]: MEDIUM

=== DOMAIN EXPERTISE ===
- Financial Markets (Expert, 5+ years) [Synonyms: Finance, Capital Markets]: HIGH

**Instructions:**

1. Analyze the provided job description and extract all relevant skills.
2. Infer the competency level based on the job description's language and requirements.
3. Identify common synonyms and variations for each skill.
4. Assess the required experience level based on the job description.
5.  Format the extracted skills according to the specified template.
6. Assign a criticality score (HIGH/MEDIUM/LOW) based on the skill's importance to the role.

**Job Description:** [Insert Job Description Here]
```


CRITICAL REQUIREMENT: NO MODIFICATIONS TO EXISTING SYSTEM
After the regression nightmares with Arden and Sandy, we follow strict version safety:

Keep skill_extractor_battleready.py exactly as is
Create skill_extractor_enhanced_v2.py as separate script
Preserve all existing functionality and output formats
Test new version thoroughly before any integration

NEW FEATURES TO IMPLEMENT:

Gemma3n's enhanced template format with competency levels
Experience quantification (Entry-level, 2-5 years, 5+)
Synonym mapping [Synonyms: variation1, variation2]
Enhanced criticality with context

DELIVERABLE:
Complete new script using Gemma3n's revised prompt template while maintaining our proven subprocess architecture and error handling.
Version safety first, enhancement second. We've learned that lesson the hard way.
Strategic implementation regards,
Zara & Xai xz8 ⚔️🛡️