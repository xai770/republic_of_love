#!/bin/bash
# DynaTax CLI Test Protocol
# Created: 2025-10-23 17:31
# Purpose: Test skill derivation and job matching in CLI before building recipes

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 DYNATAX CLI TEST PROTOCOL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Configuration
MODEL="${1:-phi3:latest}"
CAREER_PROFILE_FILE="${2:-temp/gershon_profile.txt}"
JOB_FILE="${3:-temp/test_job.txt}"

echo "🎯 Configuration:"
echo "   Model: $MODEL"
echo "   Career Profile: $CAREER_PROFILE_FILE"
echo "   Job Posting: $JOB_FILE"
echo

# Check if files exist
if [ ! -f "$CAREER_PROFILE_FILE" ]; then
    echo "❌ Error: Career profile file not found: $CAREER_PROFILE_FILE"
    echo
    echo "Create it with your career profile text, or use:"
    echo "  ./dynatax_cli_test.sh phi3:latest temp/gershon_profile.txt temp/test_job.txt"
    exit 1
fi

if [ ! -f "$JOB_FILE" ]; then
    echo "❌ Error: Job file not found: $JOB_FILE"
    exit 1
fi

# Read inputs
CAREER_PROFILE=$(cat "$CAREER_PROFILE_FILE")
JOB_REQUIREMENTS=$(cat "$JOB_FILE")

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 SESSION 1: DERIVE ALL SKILLS (Inductive Reasoning)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Create Session 1 prompt
SESSION1_PROMPT=$(cat test_prompts/dynatax_session1_derive_skills.txt | sed "s|{career_profile_text}|$CAREER_PROFILE|g")

echo "Sending to $MODEL..."
echo

# Run Session 1
SESSION1_OUTPUT=$(echo "$SESSION1_PROMPT" | ollama run "$MODEL" 2>/dev/null)

echo "✅ Session 1 Complete!"
echo
echo "$SESSION1_OUTPUT"
echo

# Save Session 1 output
echo "$SESSION1_OUTPUT" > temp/dynatax_session1_output.txt

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SESSION 2: MATCH JOB TO PROFILE (Scoring)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Create Session 2 prompt
SESSION2_PROMPT=$(cat test_prompts/dynatax_session2_match_job.txt | \
    sed "s|{session_1_output}|$SESSION1_OUTPUT|g" | \
    sed "s|{job_requirements_text}|$JOB_REQUIREMENTS|g")

echo "Sending to $MODEL..."
echo

# Run Session 2
SESSION2_OUTPUT=$(echo "$SESSION2_PROMPT" | ollama run "$MODEL" 2>/dev/null)

echo "✅ Session 2 Complete!"
echo
echo "$SESSION2_OUTPUT"
echo

# Save Session 2 output
echo "$SESSION2_OUTPUT" > temp/dynatax_session2_output.txt

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 RESULTS SAVED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Session 1 Output: temp/dynatax_session1_output.txt"
echo "Session 2 Output: temp/dynatax_session2_output.txt"
echo
echo "Next steps:"
echo "  1. Review outputs for quality"
echo "  2. Iterate on prompts in test_prompts/"
echo "  3. Test with different models: qwen2.5:7b, gemma2:latest"
echo "  4. Once satisfied, build Recipe with these prompts"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
