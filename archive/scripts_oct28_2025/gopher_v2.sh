#!/bin/bash
# Autonomous Gopher v2 - Clean separation of display and conversation context

set -e

MODEL="qwen2.5:7b"
JOB_FILE="${1:-data/postings/job64834.json}"
OUTPUT_FILE="temp/autonomous_hierarchy_$(date +%Y%m%d_%H%M%S).txt"
CONVERSATION_CONTEXT="temp/conversation_context_$(date +%Y%m%d_%H%M%S).txt"

# Initialize
> "$OUTPUT_FILE"
> "$CONVERSATION_CONTEXT"

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║         AUTONOMOUS GOPHER V2: LLM-GUIDED HIERARCHY BUILDER                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Extract job info
JOB_DESCRIPTION=$(jq -r '.job_content.description' "$JOB_FILE")
JOB_TITLE=$(jq -r '.job_content.title' "$JOB_FILE")

echo "📄 Job: $JOB_TITLE"
echo "🤖 Model: $MODEL"
echo ""

MAX_DEPTH=5

# Send message to LLM (pure function - no display)
ask_llm() {
    local prompt="$1"
    
    # Append to conversation context
    echo "$prompt" >> "$CONVERSATION_CONTEXT"
    echo "" >> "$CONVERSATION_CONTEXT"
    
    # Get response without streaming (cleaner output)
    local full_context=$(cat "$CONVERSATION_CONTEXT")
    local response=$(echo "$full_context" | ollama run "$MODEL" --nowordwrap 2>&1 | strings)
    
    # Append response to context
    echo "$response" >> "$CONVERSATION_CONTEXT"
    echo "" >> "$CONVERSATION_CONTEXT"
    
    # Return response
    echo "$response"
}

# Explore recursively
explore() {
    local node="$1"
    local path="$2"
    local level=$3
    
    if [ $level -ge $MAX_DEPTH ]; then
        echo "$path/$node" >> "$OUTPUT_FILE"
        return
    fi
    
    echo "🔍 Level $level: $node"
    
    if [ $level -eq 0 ]; then
        response=$(ask_llm "Analyze this job and list 5-8 TOP skill categories:

JOB: $JOB_TITLE
DESCRIPTION: $JOB_DESCRIPTION

Output numbered list ONLY:
1. CATEGORY - explanation
2. CATEGORY - explanation
...")
    else
        response=$(ask_llm "Break down '$node' into subcategories.

If '$node' is atomic, respond: LEAF_NODE

Otherwise list subcategories:
1. SUBCAT - explanation
2. SUBCAT - explanation
...")
    fi
    
    # Check for leaf
    if echo "$response" | grep -qi "LEAF_NODE"; then
        echo "  ✓ Leaf: $path/$node"
        echo "$path/$node" >> "$OUTPUT_FILE"
        return
    fi
    
    # Extract categories (handle wrapped lines)
    categories=$(echo "$response" | grep -E "^[0-9]+\." | sed 's/^[0-9]*\. *//' | sed 's/ - .*//' | sed 's/[[:space:]]*$//' | head -8)
    
    if [ -z "$categories" ]; then
        echo "  ⚠️  No categories, treating as leaf"
        echo "$path/$node" >> "$OUTPUT_FILE"
        return
    fi
    
    # Ask LLM to select most relevant
    selection=$(ask_llm "From these under '$node':
$categories

Pick 2-3 most relevant for: $JOB_TITLE

List ONLY names (no numbers):
NAME1
NAME2
...")
    
    selected=$(echo "$selection" | grep -v "^[[:space:]]*$" | grep -v "Pick\|From\|most\|relevant" | head -3)
    
    if [ -z "$selected" ]; then
        selected=$(echo "$categories" | head -2)
    fi
    
    # Explore selected branches
    while IFS= read -r branch; do
        if [ -n "$branch" ]; then
            new_path="${path}${path:+/}${node}"
            explore "$branch" "$new_path" $((level + 1))
        fi
    done <<< "$selected"
}

echo "🚀 Starting exploration..."
echo ""

explore "ROOT" "" 0

echo ""
echo "✓ Complete!"
echo ""
echo "Results: $OUTPUT_FILE"
echo "Context: $CONVERSATION_CONTEXT"
echo ""
cat "$OUTPUT_FILE"
