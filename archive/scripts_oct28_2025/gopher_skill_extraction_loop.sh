#!/bin/bash
# Interactive Gopher-style skill extraction with unlimited depth
# Navigate through concept hierarchies until you reach leaf nodes

set -e

MODEL="qwen2.5:7b"
JOB_FILE="${1:-data/postings/job64834.json}"
CONVERSATION_FILE="temp/gopher_loop_$(date +%Y%m%d_%H%M%S).txt"

# Database connection
DB_HOST="localhost"
DB_USER="base_admin"
DB_NAME="base_yoga"
export PGPASSWORD="base_yoga_secure_2025"

# Initialize conversation
> "$CONVERSATION_FILE"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║         GOPHER LOOP: INTERACTIVE HIERARCHY EXPLORER                          ║"
echo "║         (Drill down to any depth until you reach leaf nodes)                 ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Job File: $JOB_FILE"
echo "Model: $MODEL"
echo ""

# Extract job description
JOB_DESCRIPTION=$(jq -r '.job_content.description' "$JOB_FILE")
JOB_TITLE=$(jq -r '.job_content.title' "$JOB_FILE")

echo -e "${BLUE}📄 Job Title: $JOB_TITLE${NC}"
echo ""

# Function to talk with model
talk() {
    local message="$1"
    
    echo "USER: $message" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}💬 YOU → $MODEL${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    RESPONSE=$(cat "$CONVERSATION_FILE" | ollama run "$MODEL" 2>&1)
    
    echo "ASSISTANT: $RESPONSE" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo -e "${GREEN}$RESPONSE${NC}"
    echo ""
}

# Function to check if skill exists in database
check_skill_exists() {
    local skill_name="$1"
    psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT COUNT(*) FROM skill_aliases WHERE skill = lower('$skill_name') OR skill_alias = lower('$skill_name');" 2>/dev/null || echo "0"
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
         LIMIT 5;" 2>/dev/null || echo "No similar skills found"
}

# Track hierarchy path
HIERARCHY_PATH=()
LEVEL=0

# Main navigation loop
navigate_level() {
    local current_context="$1"
    local parent_path="$2"
    
    LEVEL=$((LEVEL + 1))
    
    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  LEVEL $LEVEL: $(printf '%-70s' "$current_context")║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    
    if [ ${#HIERARCHY_PATH[@]} -gt 0 ]; then
        echo -e "${BLUE}📍 Path: ${HIERARCHY_PATH[*]}${NC}"
        echo ""
    fi
    
    # Build the prompt based on level and context
    if [ $LEVEL -eq 1 ]; then
        # Level 1: Top categories
        PROMPT="I'm analyzing this job posting:

TITLE: $JOB_TITLE

DESCRIPTION:
$JOB_DESCRIPTION

Please analyze this job and suggest 5-8 TOP-LEVEL skill categories that apply to this role.

Examples of top categories: TECHNICAL, SOFT_SKILLS, DOMAIN, BUSINESS_ANALYSIS, LEADERSHIP, etc.

Output ONLY a numbered list:
1. CATEGORY_NAME - Brief explanation
2. CATEGORY_NAME - Brief explanation
..."
    else
        # Deeper levels: drill down
        PROMPT="Looking at this job posting (focusing on the path: ${HIERARCHY_PATH[*]}), 
what are the subcategories or specific skills under '$current_context'?

Job context reminder:
TITLE: $JOB_TITLE
KEY ACTIVITIES: financial models, company valuations, credit analysis, M&A, ECM, DCM, presentations, project management

If '$current_context' can be broken down further, list 5-10 subcategories.
If '$current_context' is already specific enough (a leaf skill), respond with: 'LEAF_NODE: This is a specific skill.'

Output format (if not a leaf):
1. SUBCATEGORY_NAME - Brief explanation
2. SUBCATEGORY_NAME - Brief explanation
..."
    fi
    
    talk "$PROMPT"
    
    # Check if we hit a leaf node
    if grep -q "LEAF_NODE" <<< "$RESPONSE"; then
        echo -e "${GREEN}✓ Reached leaf node: $current_context${NC}"
        
        # Check if skill exists in database
        count=$(check_skill_exists "$current_context")
        if [ "$count" -gt 0 ]; then
            echo -e "${GREEN}✅ Skill '$current_context' EXISTS in SkillBridge${NC}"
        else
            echo -e "${RED}❌ Skill '$current_context' NOT in SkillBridge - would create new node${NC}"
            echo -e "${BLUE}   Searching for similar skills...${NC}"
            find_similar_skills "$current_context"
        fi
        
        LEVEL=$((LEVEL - 1))
        return
    fi
    
    # Interactive menu
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📋 Select a branch to explore (or type 'back' to go up, 'done' to finish):${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    read -p "Enter number, branch name, 'back', or 'done': " choice
    
    case "$choice" in
        done|DONE|exit|EXIT|quit|QUIT)
            echo -e "${GREEN}✓ Navigation complete!${NC}"
            return
            ;;
        back|BACK|..)
            echo -e "${BLUE}↑ Going back up...${NC}"
            LEVEL=$((LEVEL - 1))
            if [ ${#HIERARCHY_PATH[@]} -gt 0 ]; then
                unset 'HIERARCHY_PATH[-1]'
            fi
            return
            ;;
        [0-9]*)
            # Extract the chosen item from the response
            selected=$(echo "$RESPONSE" | grep "^${choice}\." | sed 's/^[0-9]*\. //' | awk -F' - ' '{print $1}')
            if [ -n "$selected" ]; then
                HIERARCHY_PATH+=("$selected")
                navigate_level "$selected" "${HIERARCHY_PATH[*]}"
                unset 'HIERARCHY_PATH[-1]'
            else
                echo -e "${RED}Invalid selection. Try again.${NC}"
                navigate_level "$current_context" "$parent_path"
            fi
            ;;
        *)
            # Direct name entry
            HIERARCHY_PATH+=("$choice")
            navigate_level "$choice" "${HIERARCHY_PATH[*]}"
            unset 'HIERARCHY_PATH[-1]'
            ;;
    esac
    
    LEVEL=$((LEVEL - 1))
}

# Start navigation from the root
echo -e "${GREEN}Starting Gopher navigation...${NC}"
echo -e "${BLUE}At each level, you can:${NC}"
echo -e "  - Enter a number to select that option"
echo -e "  - Type a branch name directly"
echo -e "  - Type 'back' to go up one level"
echo -e "  - Type 'done' to finish"
echo ""

navigate_level "ROOT: Analyzing entire job posting" ""

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    GOPHER NAVIGATION COMPLETE                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${BLUE}📁 Full conversation saved to: $CONVERSATION_FILE${NC}"
echo ""
echo -e "${GREEN}Summary:${NC}"
echo -e "  - Maximum depth reached: $LEVEL levels"
echo -e "  - Conversation history: $CONVERSATION_FILE"
echo -e "  - Database: $DB_NAME"
