#!/bin/bash
# Conversational LLM interface for Arden
# Maintains context across multiple turns
# Usage: Source this file, then use talk_to_llm function

MODEL="${1:-phi3:latest}"
CONVERSATION_FILE="temp/llm_conversation_${MODEL//[:\.]/_}.txt"

# Initialize or clear conversation
init_conversation() {
    > "$CONVERSATION_FILE"
    echo "🎯 Started new conversation with $MODEL"
    echo "Conversation file: $CONVERSATION_FILE"
}

# Send a message and get response (maintains context)
talk_to_llm() {
    local message="$1"
    
    if [ -z "$message" ]; then
        echo "Usage: talk_to_llm 'your message here'"
        return 1
    fi
    
    # Add user message to conversation
    echo "USER: $message" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💬 ARDEN → $MODEL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$message"
    echo ""
    
    # Send entire conversation context to model
    RESPONSE=$(cat "$CONVERSATION_FILE" | ollama run "$MODEL" 2>&1)
    
    # Add response to conversation
    echo "ASSISTANT: $RESPONSE" >> "$CONVERSATION_FILE"
    echo "" >> "$CONVERSATION_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤖 $MODEL → ARDEN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$RESPONSE"
    echo ""
    
    # Return response for further processing
    echo "$RESPONSE"
}

# Show conversation history
show_conversation() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📜 CONVERSATION HISTORY WITH $MODEL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat "$CONVERSATION_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Export functions
export -f talk_to_llm
export -f show_conversation

echo "🎯 LLM Conversation Interface Ready"
echo "Model: $MODEL"
echo ""
echo "Commands:"
echo "  talk_to_llm 'your message'  - Send a message and get response"
echo "  show_conversation            - View full conversation history"
echo "  init_conversation            - Start fresh conversation"
