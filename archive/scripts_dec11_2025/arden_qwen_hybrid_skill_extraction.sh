#!/bin/bash
# Arden asks Qwen to enhance Recipe 1122 for hybrid skill extraction

cd /home/xai/Documents/ty_learn
source llm_conversation.sh qwen2.5:7b

init_conversation

talk_to_llm "Hello Qwen! We need to enhance Recipe 1122 Session 2 to extract skills with proficiency + years metadata.

**CURRENT OUTPUT (simple array):**
\`\`\`json
['Oracle', 'RMAN', 'PL/SQL Development', 'Linux']
\`\`\`

**TARGET OUTPUT (hybrid structure):**
\`\`\`json
[
  {
    \"skill\": \"Oracle\",
    \"proficiency\": \"expert\",
    \"years_experience\": 12,
    \"context\": \"Used in 3 recent positions as Senior DBA\"
  },
  {
    \"skill\": \"RMAN\",
    \"proficiency\": \"expert\",
    \"years_experience\": 10,
    \"context\": \"Backup/recovery specialist\"
  }
]
\`\`\`

**PROFICIENCY LEVELS:**
- **expert**: Deep expertise, can teach others, handles complex scenarios
- **advanced**: Strong working knowledge, handles most scenarios independently
- **intermediate**: Working knowledge, needs occasional guidance
- **beginner**: Basic familiarity, needs supervision

**YEARS EXTRACTION RULES:**
1. If explicitly stated: 'Oracle DBA for 12 years' → 12
2. If from job duration: Senior Oracle DBA (2015-2020) + DBA (2010-2015) → 10 years
3. If recent: 'Currently using Azure' + job started 2020 → 5 years (2025-2020)
4. If unclear: Use 'null' or estimate conservatively

**YOUR TASK:**
Enhance the CURRENT prompt to extract this hybrid structure. The prompt should:
1. Extract skill name (as before)
2. Infer proficiency from job titles, responsibilities, achievements
3. Calculate years from job history, explicit mentions, or dates
4. Add brief context explaining where skill was used

Return the ENHANCED prompt that will produce the hybrid JSON structure."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 Qwen's enhanced prompt will enable hybrid skill extraction"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
