#!/bin/bash
# Interactive session with qwen2.5:7b to design better hierarchy extraction prompts
# No manual pauses - runs continuously

set -e

MODEL="qwen2.5:7b"
CONVERSATION_FILE="temp/hierarchy_design_conversation.txt"

# Initialize conversation
> "$CONVERSATION_FILE"

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║          HIERARCHY PROMPT DESIGN SESSION WITH $MODEL                    ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Function to talk with model
talk() {
    local message="$1"
    
    echo "USER: $message" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💬 ARDEN → $MODEL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$message"
    echo ""
    
    RESPONSE=$(cat "$CONVERSATION_FILE" | ollama run "$MODEL" 2>&1)
    
    echo "ASSISTANT: $RESPONSE" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤖 $MODEL → ARDEN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$RESPONSE"
    echo ""
}

# ROUND 1: Introduce the problem
talk "I'm working on a skill extraction system. Currently, I extract skills in a 3-level hierarchy: CATEGORY/SUBCATEGORY/SKILL.

For example:
TECHNICAL/PROGRAMMING/Python
TECHNICAL/DATABASE/PostgreSQL
SOFT_SKILLS/COMMUNICATION/Public_Speaking

The problem: When I have many skills, the TECHNICAL category ends up with 41 direct subcategories, which makes the hierarchy too flat and hard to navigate. I need an intermediate grouping level.

Question: How would you design a 4-level hierarchy that adds logical intermediate groupings? For example: TECHNICAL → IT → PROGRAMMING → Python."

# ROUND 2: Get specific structure recommendations
talk "Based on that structure, can you give me 5-10 example intermediate groupings that would sit between TECHNICAL and its subcategories?

For context, the current subcategories under TECHNICAL include: programming, database, cloud, networking, cyber_security, data_science, machine_learning, api, automation, web_development, mobile_development, devops, system_administration, and about 28 more.

What intermediate categories would you create?"

# ROUND 3: Get the extraction prompt
talk "Perfect! Now, can you write me a prompt that I can use to extract skills in this 4-level format from job descriptions?

The prompt should:
1. Output one skill per line
2. Format: TOP_CATEGORY/MID_CATEGORY/SUBCATEGORY/SKILL
3. Only output English skill names (even if job description is in German)
4. Use underscores instead of spaces
5. Be wrapped in +++OUTPUT START+++ and +++OUTPUT END+++ markers

Can you draft this extraction prompt for me?"

# ROUND 4: Test with real example
talk "Let's test that prompt on a real job description. Here's an excerpt from a Deutsche Bank Investment Banking position:

\"IBC & A Germany Analyst - Your key responsibilities: You will perform sector and company research, work on complex and highly quantitative analyses, such as financial models, company valuations, credit analysis and analysis of strategic scenarios. You will also support the preparation of client presentations and pitches. Your skills and experiences: University degree in economics, business administration, law or similar, ideally with an international focus and focus on corporate finance. Ideally experience in corporate finance (M&A, ECM, DCM, LDCM) at a bulge bracket investment bank. Strong analytical and financial modelling capabilities.\"

Using the extraction prompt you just created, what skills would you extract from this job posting? Show me the actual output in the 4-level format."

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                         CONVERSATION COMPLETE                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Conversation saved to: $CONVERSATION_FILE"
echo ""
echo "You can review the full conversation with:"
echo "  cat $CONVERSATION_FILE"
