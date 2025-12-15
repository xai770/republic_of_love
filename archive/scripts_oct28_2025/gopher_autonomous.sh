#!/bin/bash
# Autonomous Gopher-style skill extraction
# Automatically explores ALL branches to build complete hierarchy tree

set -e

MODEL="qwen2.5:7b"
JOB_FILE="${1:-data/postings/job64834.json}"
OUTPUT_FILE="temp/autonomous_hierarchy_$(date +%Y%m%d_%H%M%S).txt"
CONVERSATION_FILE="temp/autonomous_conversation_$(date +%Y%m%d_%H%M%S).txt"

# Database connection
DB_HOST="localhost"
DB_USER="base_admin"
DB_NAME="base_yoga"
export PGPASSWORD="base_yoga_secure_2025"

# Initialize files
> "$CONVERSATION_FILE"
> "$OUTPUT_FILE"

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║         AUTONOMOUS GOPHER: AUTOMATIC HIERARCHY EXPLORER                      ║"
echo "║         (I'll explore all branches automatically)                            ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Job File: $JOB_FILE"
echo "Model: $MODEL"
echo "Output: $OUTPUT_FILE"
echo ""

# Extract job description
JOB_DESCRIPTION=$(jq -r '.job_content.description' "$JOB_FILE")
JOB_TITLE=$(jq -r '.job_content.title' "$JOB_FILE")

echo "📄 Job Title: $JOB_TITLE"
echo ""

# Function to talk with model (returns clean response)
talk() {
    local message="$1"
    
    # Save to conversation file
    echo "USER: $message" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    # Display to user
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💬 ARDEN → $MODEL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$message" | head -10
    echo ""
    
    # Get LLM response
    local llm_response=$(cat "$CONVERSATION_FILE" | ollama run "$MODEL" 2>&1)
    
    # Save response to conversation file
    echo "ASSISTANT: $llm_response" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    # Display response
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤖 $MODEL → ARDEN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$llm_response" | head -20
    echo ""
    
    # Return ONLY the LLM response (no formatting)
    echo "$llm_response"
}

# Function to extract items from response (handles both numbered and non-numbered lists)
extract_items() {
    local response="$1"
    # First try numbered format
    local numbered=$(echo "$response" | grep -E "^[0-9]+\." | sed 's/^[0-9]*\. //' | awk -F' - ' '{print $1}' | sed 's/[[:space:]]*$//')
    
    if [ -n "$numbered" ]; then
        echo "$numbered"
    else
        # Try plain lines (for unnumbered lists from LLM)
        echo "$response" | grep -v "^[[:space:]]*$" | grep -v ":" | grep -v "Based on" | grep -v "^━" | grep -v "^💬" | grep -v "LEAF_NODE" | head -10
    fi
}

# Function to check if we hit a leaf node
is_leaf_node() {
    local response="$1"
    if echo "$response" | grep -qi "LEAF_NODE\|leaf node\|specific skill\|cannot be broken down\|atomic skill"; then
        return 0
    fi
    return 1
}

# Track hierarchy
declare -A HIERARCHY_TREE
LEVEL=0
MAX_DEPTH=6  # Prevent infinite recursion

# LLM-guided navigation function
explore_branch() {
    local current_node="$1"
    local current_path="$2"
    local current_level=$3
    
    # Safety check
    if [ $current_level -ge $MAX_DEPTH ]; then
        echo "⚠️  Max depth ($MAX_DEPTH) reached at: $current_path/$current_node"
        echo "$current_path/$current_node [MAX_DEPTH]" >> "$OUTPUT_FILE"
        return
    fi
    
    echo ""
    echo "🌟 LEVEL $current_level: Exploring '$current_node'"
    if [ -n "$current_path" ]; then
        echo "📍 Path: $current_path"
    fi
    echo ""
    
    # Build prompt based on context
    if [ $current_level -eq 0 ]; then
        # Level 0: Get top categories
        PROMPT="Analyze this job posting and suggest 5-8 TOP-LEVEL skill categories.

JOB TITLE: $JOB_TITLE
JOB DESCRIPTION: $JOB_DESCRIPTION

Examples: TECHNICAL, SOFT_SKILLS, DOMAIN, BUSINESS_ANALYSIS, LEADERSHIP

Output ONLY a numbered list (no other text):
1. CATEGORY_NAME - Brief explanation
2. CATEGORY_NAME - Brief explanation
..."
    else
        # Deeper levels: drill down into current node
        PROMPT="Looking at the job posting, break down '$current_node' into subcategories or specific skills.

Context path: $current_path
Job: $JOB_TITLE

If '$current_node' is already a specific atomic skill that cannot be broken down, respond ONLY with:
LEAF_NODE: This is a specific skill.

Otherwise, list 5-10 subcategories:
1. SUBCATEGORY - Explanation
2. SUBCATEGORY - Explanation
..."
    fi
    
    # Get response from model
    response=$(talk "$PROMPT")
    
    # Check if leaf node
    if is_leaf_node "$response"; then
        full_path="${current_path}/${current_node}"
        echo "✓ LEAF NODE: $full_path"
        echo "$full_path" >> "$OUTPUT_FILE"
        return
    fi
    
    # Extract child items
    items=$(extract_items "$response")
    
    if [ -z "$items" ]; then
        echo "⚠️  No items extracted from response, treating as leaf"
        full_path="${current_path}/${current_node}"
        echo "$full_path" >> "$OUTPUT_FILE"
        return
    fi
    
    # Count children
    child_count=$(echo "$items" | wc -l)
    echo "📊 Found $child_count children under '$current_node'"
    echo ""
    
    # ASK THE LLM which branches to explore
    echo "🤖 Asking $MODEL to decide navigation strategy..."
    NAVIGATION_PROMPT="You previously identified these $child_count subcategories under '$current_node':

$items

Based on the job posting for: $JOB_TITLE

Which of these subcategories are MOST relevant to explore further? 
Pick the 2-3 most important ones that are central to this job's requirements.

Respond with ONLY the category names (one per line, no numbers or explanations):
CATEGORY1
CATEGORY2
..."

    navigation_response=$(talk "$NAVIGATION_PROMPT")
    selected_branches=$(echo "$navigation_response" | grep -v "^[[:space:]]*$" | head -5)
    
    if [ -z "$selected_branches" ]; then
        echo "⚠️  LLM didn't select branches, exploring first 3 by default"
        selected_branches=$(echo "$items" | head -3)
    fi
    
    # Explore LLM-selected branches
    local branch_num=1
    while IFS= read -r branch; do
        if [ -n "$branch" ]; then
            # Clean up branch name
            branch=$(echo "$branch" | sed 's/^[0-9]*\. //' | sed 's/[[:space:]]*$//')
            
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "🧭 LLM selected branch $branch_num: $branch"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            new_path="${current_path}${current_path:+/}${current_node}"
            explore_branch "$branch" "$new_path" $((current_level + 1))
            
            branch_num=$((branch_num + 1))
        fi
    done <<< "$selected_branches"
    
    echo ""
    echo "✓ Completed exploration of '$current_node' (explored $((branch_num - 1)) of $child_count branches)"
}

# Start autonomous exploration
echo "🚀 Starting autonomous exploration..."
echo ""
echo "I'll automatically explore all branches and build the complete hierarchy tree."
echo "This may take several minutes depending on the complexity."
echo ""

explore_branch "ROOT" "" 0

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    AUTONOMOUS EXPLORATION COMPLETE                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 RESULTS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Complete hierarchy tree:"
cat "$OUTPUT_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Hierarchy tree saved to: $OUTPUT_FILE"
echo "📁 Full conversation saved to: $CONVERSATION_FILE"
echo ""
echo "Total leaf nodes discovered: $(wc -l < "$OUTPUT_FILE")"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next steps:"
echo "1. Review the hierarchy tree in: $OUTPUT_FILE"
echo "2. Compare with existing SkillBridge taxonomy"
echo "3. Import new skills and relationships into database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
