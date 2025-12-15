#!/bin/bash
# Interactive conversation with qwen2.5:7b to design SkillBridge hierarchy prompts
# This script helps us collaborate with the LLM to create better taxonomy structures

MODEL="qwen2.5:7b"
CONVERSATION_FILE="temp/skillbridge_hierarchy_design.txt"

# Initialize conversation
> "$CONVERSATION_FILE"

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║         SkillBridge Hierarchy Design Session with qwen2.5:7b                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Goal: Design prompts for logical multi-level skill hierarchies"
echo "📝 Conversation file: $CONVERSATION_FILE"
echo ""

# Function to send message and get response
ask_model() {
    local message="$1"
    
    echo "USER: $message" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💬 ARDEN → qwen2.5:7b"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$message"
    echo ""
    
    RESPONSE=$(cat "$CONVERSATION_FILE" | ollama run "$MODEL" 2>&1)
    
    echo "ASSISTANT: $RESPONSE" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤖 qwen2.5:7b → ARDEN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$RESPONSE"
    echo ""
}

# Start the conversation

echo "Step 1: Explain the current problem"
ask_model "Hi! I'm building SkillBridge - a system to extract skills from job postings and organize them hierarchically. 

Currently I extract skills like this:
TECHNICAL/PROGRAMMING/Python
TECHNICAL/CLOUD/AWS
TECHNICAL/ACCOUNTING/Tax_Audit_Support

This creates flat hierarchies - TECHNICAL has 41 direct children like: programming, cloud, database, accounting, finance, auditing, business, analytics...

The problem: these should be grouped into logical mid-level categories like:
- IT (containing programming, cloud, database)
- BUSINESS_SYSTEMS (containing accounting, finance, auditing)
- ANALYTICS (containing data_science, business_intelligence)

Do you understand the problem?"

read -p "Press Enter to continue..."

echo ""
echo "Step 2: Ask for grouping approach"
ask_model "Great! So here's my question: When you extract technical skills from a job posting, how can I prompt you to automatically organize them into 4 levels instead of 3?

Current: TECHNICAL/PROGRAMMING/Python (3 levels)
Desired: TECHNICAL/IT/PROGRAMMING/Python (4 levels)

Should I:
A) Ask you to output 4-level paths directly in one pass?
B) First extract 3-level paths, then ask you to suggest logical groupings for subcategories?
C) Give you a predefined list of mid-level categories (IT, BUSINESS_SYSTEMS, etc) and ask you to classify each subcategory?

What would work best for you as a model?"

read -p "Press Enter to continue..."

echo ""
echo "Step 3: Get sample output format"
ask_model "Can you show me an example of how you would extract skills from this job posting using your preferred approach?

Job posting excerpt:
\"The ideal candidate will have experience with Python, JavaScript, PostgreSQL, AWS cloud services, Docker, Git version control, financial reporting, tax compliance, and business process analysis.\"

Please show me the exact format you would output."

read -p "Press Enter to continue..."

echo ""
echo "Step 4: Test with actual complex posting"
echo "📄 Loading actual German job posting (IBC & A Germany Analyst)..."
JOB_TEXT=$(cat /home/xai/Documents/ty_learn/data/postings/job64834.json | jq -r '.job_content.description' | head -c 2000)

ask_model "Now let's test with a real job posting. Here's an excerpt from a Deutsche Bank Corporate Finance position:

$JOB_TEXT

Using the format you suggested, please extract ALL skills you can identify from this posting. Remember to organize them into logical 4-level hierarchies."

read -p "Press Enter to continue..."

echo ""
echo "Step 5: Ask for category definitions"
ask_model "Looking at what you extracted, can you help me create a standardized list of mid-level categories?

For TECHNICAL skills, what are the major subdivisions you think make sense? 

For example:
- IT (programming, cloud, databases, DevOps)
- BUSINESS_SYSTEMS (accounting, finance, ERP)
- ANALYTICS (data science, BI, reporting)

What would you suggest as a complete list of mid-level TECHNICAL categories that would cover most job postings?"

read -p "Press Enter to continue..."

echo ""
echo "Step 6: Design the final prompt"
ask_model "Perfect! Now can you help me write the exact prompt I should use in my extraction system?

Requirements:
1. You will receive a job posting as input
2. You must output ONLY skills in 4-level hierarchical format
3. Output must be between +++OUTPUT START+++ and +++OUTPUT END+++ markers
4. Format: TOP_CATEGORY/MID_CATEGORY/SUBCATEGORY/SKILL
5. One skill per line
6. English only (even for German job postings)
7. Use consistent mid-level categories

Please write the complete prompt I should use."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Conversation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📄 Full conversation saved to: $CONVERSATION_FILE"
echo ""
echo "Next steps:"
echo "1. Review the suggested prompt design"
echo "2. Update Recipe 1120 Session 2 canonical with new 4-level prompt"
echo "3. Test on a few job postings manually"
echo "4. Run batch extraction on all 71 German postings"
echo ""
