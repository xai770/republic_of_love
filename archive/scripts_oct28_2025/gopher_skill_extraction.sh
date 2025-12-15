#!/bin/bash
# Gopher-style interactive skill extraction
# Navigate job posting skills level by level like a Gopher menu

set -e

MODEL="qwen2.5:7b"
JOB_FILE="${1:-data/postings/job64834.json}"
CONVERSATION_FILE="temp/gopher_skill_extraction_$(date +%Y%m%d_%H%M%S).txt"

# Database connection
DB_HOST="localhost"
DB_USER="base_admin"
DB_NAME="base_yoga"
export PGPASSWORD="base_yoga_secure_2025"

# Initialize conversation
> "$CONVERSATION_FILE"

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║              GOPHER-STYLE SKILL EXTRACTION                                   ║"
echo "║              (Interactive Menu Navigation)                                   ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Job File: $JOB_FILE"
echo "Model: $MODEL"
echo ""

# Extract job description
JOB_DESCRIPTION=$(jq -r '.job_content.description' "$JOB_FILE")
JOB_TITLE=$(jq -r '.job_content.title' "$JOB_FILE")

echo "📄 Job Title: $JOB_TITLE"
echo ""

# Function to talk with model
talk() {
    local message="$1"
    
    echo "USER: $message" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💬 GERSHON → $MODEL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$message"
    echo ""
    
    RESPONSE=$(cat "$CONVERSATION_FILE" | ollama run "$MODEL" 2>&1)
    
    echo "ASSISTANT: $RESPONSE" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤖 $MODEL → GERSHON"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$RESPONSE"
    echo ""
}

# Function to check if skill exists in database
check_skill_exists() {
    local skill_name="$1"
    psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT COUNT(*) FROM skill_aliases WHERE skill = lower('$skill_name') OR skill_alias = lower('$skill_name');"
}

# Function to get similar skills from database
find_similar_skills() {
    local search_term="$1"
    psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
        "SELECT sa.skill, sa.display_name, COUNT(so.skill) as uses 
         FROM skill_aliases sa
         LEFT JOIN skill_occurrences so ON sa.skill = so.skill
         WHERE sa.skill ILIKE '%${search_term}%' 
            OR sa.display_name ILIKE '%${search_term}%'
            OR sa.skill_alias ILIKE '%${search_term}%'
         GROUP BY sa.skill, sa.display_name
         ORDER BY uses DESC NULLS LAST, sa.skill
         LIMIT 5;"
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌟 LEVEL 1: TOP CATEGORIES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# LEVEL 1: Get top categories
talk "I'm analyzing this job posting:

TITLE: $JOB_TITLE

DESCRIPTION:
$JOB_DESCRIPTION

Please analyze this job and suggest 5-8 TOP-LEVEL skill categories that apply to this role.

Examples of top categories: TECHNICAL, SOFT_SKILLS, DOMAIN, BUSINESS_ANALYSIS, LEADERSHIP, etc.

Output format:
1. CATEGORY_NAME - Brief explanation
2. CATEGORY_NAME - Brief explanation
...

Only list the top-level categories that are relevant to THIS specific job posting."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌟 LEVEL 2: INTERMEDIATE GROUPINGS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# LEVEL 2: Pick a category and drill down (let's focus on TECHNICAL first)
talk "Let's drill down into the TECHNICAL category.

Based on the job description, what intermediate groupings would you create under TECHNICAL?

Examples: Software_Development, Data_Management, System_Administration, Networking_Infrastructure, Security_Privacy, etc.

Output format:
1. GROUPING_NAME - Brief explanation of what skills belong here
2. GROUPING_NAME - Brief explanation
...

Only list intermediate groupings that are relevant to the skills mentioned in THIS job posting."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌟 LEVEL 3: SUBCATEGORIES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# LEVEL 3: Pick an intermediate grouping and get subcategories
talk "Now let's drill down further. Looking at the job description, what specific SUBCATEGORIES would you create?

For example, if we're looking at Data_Management or Business_Analysis areas, what subcategories apply?

Job mentions: financial models, company valuations, credit analysis, strategic scenarios, presentations, M&A, ECM, DCM, etc.

Output format:
1. SUBCATEGORY - Explanation
2. SUBCATEGORY - Explanation
...

Focus on subcategories that directly relate to the skills/activities mentioned in the job."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌟 LEVEL 4: ACTUAL SKILLS (LEAF NODES)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# LEVEL 4: Get specific skills
talk "Finally, extract the actual SKILLS (leaf nodes) from this job posting.

These should be specific, concrete skills like:
- Financial_Modeling
- Company_Valuation
- Credit_Analysis
- M&A (Mergers and Acquisitions)
- Presentation_Skills
- Excel
- etc.

For each skill, suggest which SUBCATEGORY it belongs to.

Output format:
SUBCATEGORY/SKILL_NAME - Brief description

Example:
FINANCIAL_ANALYSIS/Financial_Modeling - Building financial models
INVESTMENT_BANKING/M&A - Mergers and acquisitions expertise

Extract ALL relevant skills from the job posting."

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    GOPHER NAVIGATION COMPLETE                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📁 Full conversation saved to: $CONVERSATION_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 CHECKING SKILLS AGAINST DATABASE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Now checking which skills already exist in SkillBridge..."
echo ""

# Example: Check a few skills
for skill in "financial_modeling" "m&a" "credit_analysis" "presentation" "excel"; do
    count=$(check_skill_exists "$skill")
    if [ "$count" -gt 0 ]; then
        echo "✅ '$skill' EXISTS in database ($count matches)"
        find_similar_skills "$skill"
    else
        echo "❌ '$skill' NOT FOUND - would create new node"
        echo "   Searching for similar skills..."
        find_similar_skills "$skill"
    fi
    echo ""
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next steps:"
echo "1. Review the extracted skills in: $CONVERSATION_FILE"
echo "2. Decide which skills to add to SkillBridge"
echo "3. Map skills to existing nodes or create new ones"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
