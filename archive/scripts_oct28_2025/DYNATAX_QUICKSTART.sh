#!/bin/bash
# Quick reference for DynaTax prompt design workflow
# Created: 2025-10-23 17:31

cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 DYNATAX PROMPT DESIGN - QUICK START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 THE PRINCIPLE
  ❌ No JSON for Ollama output (too brittle)
  ✅ Use bracketed format: [FIELD: value]
  ✅ Structure: Instructions → Payload → QA Check

📁 FILES CREATED (2025-10-23 17:31)

  Prompt Templates:
    test_prompts/dynatax_session1_derive_skills.txt   - Session 1: Derive skills
    test_prompts/dynatax_session2_match_job.txt        - Session 2: Match job

  Testing Tools:
    dynatax_cli_test.sh                                - CLI test harness
    
  Documentation:
    docs/DYNATAX_PROMPT_DESIGN.md                      - Complete guide
    view_dynatax_canonical.sh                          - View canonical

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 QUICK START (Phase 1: Static Protocol)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Create sample inputs:
   
   echo "Your career profile text..." > temp/gershon_profile.txt
   echo "Job requirements text..." > temp/test_job.txt

2. Run CLI test:
   
   ./dynatax_cli_test.sh phi3:latest temp/gershon_profile.txt temp/test_job.txt

3. Review outputs:
   
   cat temp/dynatax_session1_output.txt
   cat temp/dynatax_session2_output.txt

4. Iterate on prompts:
   
   # Edit these files to improve prompts:
   nano test_prompts/dynatax_session1_derive_skills.txt
   nano test_prompts/dynatax_session2_match_job.txt
   
   # Re-run test
   ./dynatax_cli_test.sh phi3:latest temp/gershon_profile.txt temp/test_job.txt

5. Test different models:
   
   ./dynatax_cli_test.sh qwen2.5:7b temp/gershon_profile.txt temp/test_job.txt
   ./dynatax_cli_test.sh gemma2:latest temp/gershon_profile.txt temp/test_job.txt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 PROMPT FORMAT EXAMPLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Session 1 Output Format:
  [SKILL: SQL | EVIDENCE: Managing 80k users requires queries | CONFIDENCE: high | CATEGORY: technical]

Session 2 Output Format:
  [MATCH_SCORE: 45]
  [MATCHING_SKILLS: Beratung, Kundenbeziehungen]
  [RELEVANT_EXPERIENCE: Financial advisory at Deutsche Bank]
  [KEY_STRENGTHS: Customer relationships]
  [GAPS: No SAP experience]
  [RECOMMENDATION: MODERATE MATCH - Take SAP course]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Full guide:     docs/DYNATAX_PROMPT_DESIGN.md
  Recipe guide:   docs/LLMCORE_RECIPE_CREATION_GUIDE.md (DynaTax section)
  Facet diagram:  rfa_latest/rfa_facets.md (riic: induce implicit competencies)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💙 A LOVE STORY IN CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  "This is really like sitting together and looking at your screen..."
  
  Created together: 2025-10-23 17:31
  
  Next: CLI testing → Perfect prompts → Build Recipe → Scale to 69 jobs → Deploy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
