#!/bin/bash
# Arden asks Qwen to improve Recipe 1122 Session 2 extraction prompt

cd /home/xai/Documents/ty_learn
source llm_conversation.sh qwen2.5:7b

init_conversation

talk_to_llm "Hello Qwen! I need your help improving a skill extraction prompt for Recipe 1122.

**THE PROBLEM:**
We have a profile for 'Ellie Larrison - Senior Oracle Database Administrator' with 12 years Oracle RAC, RMAN, Data Guard experience. But our current extraction gives generic skills like 'postgresql', 'financial_services', 'data_governance' instead of Oracle-specific skills.

**CURRENT PROMPT:**
\`\`\`
# Task: Extract Skills from Profile

You are analyzing a candidate profile. Extract ALL skills mentioned or implied.

## Input Summary
{session_1_output}

## Full Profile Text
{variations_param_1}

## Instructions
1. Review both the summary and full profile text
2. Extract technical skills (programming languages, tools, platforms)
3. Extract domain skills (SAM, compliance, project management, etc.)
4. Extract soft skills (leadership, communication, etc.)
5. Include skills from:
   - Explicitly mentioned tools/technologies
   - Work responsibilities (e.g., 'managed team' → Leadership)
   - Achievements (e.g., 'negotiated contracts' → Negotiation)
   - Industry context (e.g., 'banking' → Financial Services)

## Guidelines
- Extract 10-30 skills
- Use specific names (e.g., 'Python' not 'programming')
- Include both technical and soft skills
- Extract in original language (German or English)
- Avoid duplicates
- Infer reasonable skills from context

## Output
Return ONLY a JSON array of extracted skills:
['skill1', 'skill2', ...]
\`\`\`

**YOUR TASK:**
Improve this prompt to extract SPECIFIC, CONCRETE skills. The profile literally says 'Oracle Database Administrator' with 'Oracle RAC', 'RMAN', 'Data Guard', 'PL/SQL' but current extraction misses these!

**KEY IMPROVEMENTS NEEDED:**
1. Prioritize explicitly mentioned technologies/tools BY NAME
2. Extract certifications verbatim (e.g., 'Oracle Certified Professional')
3. Extract specific methodologies/tools (RAC, RMAN, not just 'database admin')
4. Job title itself is a skill (Oracle DBA → extract 'Oracle')
5. Don't over-generalize (Oracle → Oracle, NOT → 'database management')

Please rewrite the prompt to be more explicit and extraction-focused. Make it crystal clear to extract:
- Product names (Oracle, SAP, Salesforce)
- Version numbers when mentioned (Oracle 19c → 'Oracle 19c')
- Acronyms (RAC, RMAN, CI/CD)
- Certifications (full name)
- Technologies stack items

Return the improved prompt."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 Qwen's response will help us fix Recipe 1122 Session 2"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
