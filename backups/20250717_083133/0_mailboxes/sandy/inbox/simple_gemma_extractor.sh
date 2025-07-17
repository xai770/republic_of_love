#!/bin/bash

# Simple Gemma3n Job Requirements Extractor
# Replicate exactly what xai did manually
# Step by step, secure handover approach

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
MODEL="gemma3n:latest"
JOB_FILE=""
OUTPUT_DIR="./simple_extraction"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

print_step() {
    echo -e "${CYAN}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
    exit 1
}

# Check if ollama is ready
check_ollama() {
    if ! command -v ollama &> /dev/null; then
        print_error "Ollama not found"
    fi
    
    if ! ollama list | grep -q "gemma3n"; then
        print_error "Model gemma3n not found. Run: ollama pull gemma3n"
    fi
    
    print_success "Ollama and $MODEL ready"
}

# Execute single prompt and save result
run_prompt() {
    local step_name="$1"
    local prompt="$2"
    local input_content="$3"
    local output_file="$4"
    
    print_step "STEP: $step_name"
    
    # Combine prompt and content
    local full_prompt="${prompt}

${input_content}"
    
    # Execute with ollama
    echo "$full_prompt" | ollama run "$MODEL" > "$output_file" 2>&1
    
    if [[ $? -eq 0 ]]; then
        print_success "Saved to: $output_file"
        echo -e "${YELLOW}Preview:${NC}"
        head -5 "$output_file" | sed 's/^/  /'
        echo
    else
        print_error "Failed to execute step: $step_name"
    fi
}

# Main extraction sequence - exactly what xai did
main() {
    # Parse arguments
    if [[ $# -ne 1 ]]; then
        echo "Usage: $0 <job_file>"
        echo "Example: $0 job_59213.md"
        exit 1
    fi
    
    JOB_FILE="$1"
    
    if [[ ! -f "$JOB_FILE" ]]; then
        print_error "Job file not found: $JOB_FILE"
    fi
    
    # Setup
    mkdir -p "$OUTPUT_DIR"
    check_ollama
    
    echo -e "${CYAN}Job File: $JOB_FILE${NC}"
    echo -e "${CYAN}Output Dir: $OUTPUT_DIR${NC}"
    echo
    
    # Read job content
    local job_content=$(cat "$JOB_FILE")
    
    # Step 1: Initial extraction (like xai's first prompt)
    local prompt1="Please extract the requirements and responsibilities from the following job description. Present them in two clear sections: \"Your Tasks\" and \"Your Profile\"."
    
    run_prompt "1 - Initial Extraction" \
        "$prompt1" \
        "$job_content" \
        "$OUTPUT_DIR/step1_initial_extraction.txt"
    
    # Get result from step 1 for step 2
    local step1_result=$(cat "$OUTPUT_DIR/step1_initial_extraction.txt")
    
    # Step 2: Requirements focus (like xai's second prompt)
    local prompt2="I only need the requirements, not what the company does or is or wants to give me. Only the stuff I need to bring to the table please. Also, can you please translate this into English?"
    
    run_prompt "2 - Requirements Focus" \
        "$prompt2" \
        "$step1_result" \
        "$OUTPUT_DIR/step2_requirements_only.txt"
    
    # Final summary
    echo -e "${GREEN}=== EXTRACTION COMPLETE ===${NC}"
    echo -e "${CYAN}Results saved in: $OUTPUT_DIR${NC}"
    echo -e "${CYAN}Key files:${NC}"
    echo -e "  step1_initial_extraction.txt"
    echo -e "  step2_requirements_only.txt"
    echo
    echo -e "${YELLOW}Next: Review step2_requirements_only.txt for quality${NC}"
}

main "$@"