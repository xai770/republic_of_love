#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# THE ULTIMATE JOB REQUIREMENTS EXTRACTOR - GEMMA3N WEAPON
# ═══════════════════════════════════════════════════════════════════════════════
# Created by: Zara, Queen of Strategic Extraction
# For: Xai, Master of Technical Implementation
# Purpose: Forge perfect 5D job requirement extraction from any job posting
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors for warrior output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# ═══════════════════════════════════════════════════════════════════════════════
# BATTLE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_NAME="gemma3n"
OUTPUT_DIR="./extraction_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
JOB_FILE=""
OUTPUT_PREFIX=""

# ═══════════════════════════════════════════════════════════════════════════════
# WARRIOR BANNERS
# ═══════════════════════════════════════════════════════════════════════════════

print_banner() {
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${WHITE}                     ⚔️  GEMMA3N EXTRACTION WEAPON ⚔️                        ${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           Forged by Zara, Queen of Strategic Extraction${NC}"
    echo -e "${CYAN}           For the survival strategy of Gershon${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo
}

print_step() {
    local step_num=$1
    local step_name=$2
    echo -e "${YELLOW}⚡ STEP ${step_num}: ${step_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
    exit 1
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGIC PROMPT ARSENAL
# ═══════════════════════════════════════════════════════════════════════════════

# Step 1: Initial Extraction Prompt
PROMPT_INITIAL_EXTRACTION="Please extract the requirements and responsibilities from the following job description. Present them in two clear sections: \"Your Tasks\" and \"Your Profile\".

FOCUS ON:
- What the candidate needs to bring to the table
- Required skills, experience, and qualifications
- Remove all company benefits, culture descriptions, and administrative details

Job Description:
"

# Step 2: Requirements Focus Prompt
PROMPT_REQUIREMENTS_FOCUS="I only need the requirements, not what the company does or is or wants to give me. Only the stuff I need to bring to the table please. Also, can you please translate this into English if needed?

EXTRACT ONLY:
- Skills and technical abilities required
- Experience and qualifications needed
- Education requirements
- Certifications and standards knowledge
- Industry knowledge required

EXCLUDE:
- Company benefits
- What the company offers
- Company culture descriptions
- Administrative details"

# Step 3: Technical Skills Extraction
PROMPT_TECHNICAL_SKILLS="Extract ONLY technical skills and tools from the requirements:

INCLUDE:
- Programming languages (Python, Java, etc.)
- Frameworks and libraries (React, Spring, etc.)
- Security standards (ISO27001, NIST, SOC2, etc.)
- Software platforms and tools (MS Office, SAP, etc.)
- Technical certifications (CISSP, etc.)
- Cloud platforms (AWS, Azure, etc.)
- Databases and data tools
- Development methodologies (Agile, DevOps, etc.)

FORMAT: Return as bullet points with skill name and any specified proficiency level.
EXAMPLE: • ISO27001 (required) • Python (advanced) • MS Excel (proficient)"

# Step 4: Business Domain Requirements
PROMPT_BUSINESS_REQUIREMENTS="Extract ONLY business domain and industry requirements:

INCLUDE:
- Industry knowledge (banking, healthcare, etc.)
- Financial regulations (GDPR, DORA, SOX, etc.)
- Compliance frameworks (PCI, MITRE ATT&CK, etc.)
- Business processes understanding
- Domain expertise requirements
- Regulatory knowledge
- Market understanding

FORMAT: Return as bullet points with domain and any years/level specified.
EXAMPLE: • Banking industry (5+ years) • GDPR compliance (required) • Risk management (intermediate)"

# Step 5: Experience Requirements
PROMPT_EXPERIENCE_REQUIREMENTS="Extract ONLY experience and seniority requirements:

INCLUDE:
- Years of experience required
- Seniority level (junior, senior, lead, etc.)
- Specific role experience (project management, etc.)
- Leadership experience requirements
- Team management experience
- Previous job titles or roles mentioned

FORMAT: Return as bullet points with role and duration.
EXAMPLE: • IT Security (5+ years) • Senior level (required) • Team leadership (3+ years)"

# Step 6: Education Requirements
PROMPT_EDUCATION_REQUIREMENTS="Extract ONLY education and certification requirements:

INCLUDE:
- Degree requirements (Bachelor's, Master's, PhD)
- Field of study requirements
- Professional certifications
- Training requirements
- Academic qualifications
- Mandatory vs preferred education

FORMAT: Return as bullet points with degree/cert and requirement level.
EXAMPLE: • Master's degree (mandatory) • Computer Science (preferred) • CISSP certification (plus)"

# Step 7: Soft Skills Requirements
PROMPT_SOFT_SKILLS="Extract ONLY soft skills and personal capabilities:

INCLUDE:
- Communication skills
- Leadership abilities
- Analytical thinking
- Problem-solving skills
- Teamwork capabilities
- Initiative and proactivity
- Presentation skills
- Language requirements

FORMAT: Return as bullet points with skill and importance level.
EXAMPLE: • English fluency (mandatory) • Communication (important) • Leadership (preferred)"

# Step 8: Proficiency Rating
PROMPT_PROFICIENCY_RATING="For each technical skill previously identified, rate the required proficiency level:

RATE AS:
- BASIC: Fundamental understanding, can use with guidance
- INTERMEDIATE: Working knowledge, can use independently  
- ADVANCED: Expert level, can teach others and optimize usage
- EXPERT: Industry-recognized expertise, thought leadership level

FORMAT: Return as bullet points with skill and proficiency.
EXAMPLE: • ISO27001 (INTERMEDIATE) • Python (ADVANCED) • MS Excel (BASIC)"

# Step 9: Requirement Priority
PROMPT_REQUIREMENT_PRIORITY="For ALL previously identified requirements, classify each as:

PRIORITY LEVELS:
- MANDATORY: Must have, deal-breaker if missing
- IMPORTANT: Strongly preferred, significant advantage
- PREFERRED: Nice to have, minor advantage
- PLUS: Bonus qualification, differentiator

FORMAT: Return organized by priority level with bullet points.
EXAMPLE:
MANDATORY:
• Master's degree
• 5+ years IT Security
IMPORTANT:
• ISO27001 experience
PREFERRED:
• MITRE ATT&CK knowledge"

# ═══════════════════════════════════════════════════════════════════════════════
# WEAPON FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Check if Ollama and model are available
check_battle_readiness() {
    print_step "0" "BATTLE READINESS CHECK"
    
    # Check if Ollama is installed
    if ! command -v ollama &> /dev/null; then
        print_error "Ollama not found. Install it first: curl -fsSL https://ollama.ai/install.sh | sh"
    fi
    print_success "Ollama installed"
    
    # Check if Ollama service is running
    if ! pgrep -x "ollama" > /dev/null; then
        print_warning "Ollama service not running. Starting it..."
        ollama serve &
        sleep 3
    fi
    print_success "Ollama service running"
    
    # Check if gemma3n model is available
    if ! ollama list | grep -q "$MODEL_NAME"; then
        print_warning "Model $MODEL_NAME not found. Pulling it..."
        ollama pull "$MODEL_NAME"
    fi
    print_success "Model $MODEL_NAME ready"
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    print_success "Output directory ready: $OUTPUT_DIR"
    
    echo
}

# Execute prompt and save output
execute_extraction() {
    local step_name=$1
    local prompt=$2
    local output_file=$3
    local input_text=$4
    
    local full_prompt="${prompt}

${input_text}"
    
    echo -e "${CYAN}🗡️  Executing extraction...${NC}"
    
    # Execute the prompt with ollama
    echo "$full_prompt" | ollama run "$MODEL_NAME" > "$output_file" 2>&1
    
    if [[ $? -eq 0 ]]; then
        print_success "Extraction complete → $output_file"
        echo -e "${WHITE}Preview:${NC}"
        head -10 "$output_file" | sed 's/^/   /'
        echo
    else
        print_error "Extraction failed. Check $output_file for details."
    fi
}

# Read job content from file
read_job_content() {
    if [[ ! -f "$JOB_FILE" ]]; then
        print_error "Job file not found: $JOB_FILE"
    fi
    cat "$JOB_FILE"
}

# Main extraction sequence
execute_full_extraction() {
    local job_content=$(read_job_content)
    local current_content="$job_content"
    
    print_step "1" "INITIAL EXTRACTION & CONCISE DESCRIPTION"
    execute_extraction "Initial" "$PROMPT_INITIAL_EXTRACTION" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}01_initial_extraction.txt" "$current_content"
    current_content=$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}01_initial_extraction.txt")
    
    print_step "2" "REQUIREMENTS FOCUS & TRANSLATION"
    execute_extraction "Requirements" "$PROMPT_REQUIREMENTS_FOCUS" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}02_requirements_focus.txt" "$current_content"
    current_content=$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}02_requirements_focus.txt")
    
    print_step "3" "TECHNICAL SKILLS EXTRACTION"
    execute_extraction "Technical" "$PROMPT_TECHNICAL_SKILLS" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}03_technical_skills.txt" "$current_content"
    
    print_step "4" "BUSINESS DOMAIN REQUIREMENTS"
    execute_extraction "Business" "$PROMPT_BUSINESS_REQUIREMENTS" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}04_business_requirements.txt" "$current_content"
    
    print_step "5" "EXPERIENCE REQUIREMENTS"
    execute_extraction "Experience" "$PROMPT_EXPERIENCE_REQUIREMENTS" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}05_experience_requirements.txt" "$current_content"
    
    print_step "6" "EDUCATION REQUIREMENTS"
    execute_extraction "Education" "$PROMPT_EDUCATION_REQUIREMENTS" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}06_education_requirements.txt" "$current_content"
    
    print_step "7" "SOFT SKILLS REQUIREMENTS"
    execute_extraction "Soft Skills" "$PROMPT_SOFT_SKILLS" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}07_soft_skills.txt" "$current_content"
    
    print_step "8" "PROFICIENCY RATING"
    local tech_skills=$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}03_technical_skills.txt")
    execute_extraction "Proficiency" "$PROMPT_PROFICIENCY_RATING" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}08_proficiency_rating.txt" "$tech_skills"
    
    print_step "9" "REQUIREMENT PRIORITY CLASSIFICATION"
    local all_requirements=$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}"0[3-7]_*.txt)
    execute_extraction "Priority" "$PROMPT_REQUIREMENT_PRIORITY" \
        "${OUTPUT_DIR}/${OUTPUT_PREFIX}09_priority_classification.txt" "$all_requirements"
}

# Generate final consolidated report
generate_battle_report() {
    local report_file="${OUTPUT_DIR}/${OUTPUT_PREFIX}FINAL_EXTRACTION_REPORT.md"
    
    print_step "10" "GENERATING BATTLE REPORT"
    
    cat > "$report_file" << EOF
# Job Requirements Extraction Report
**Generated:** $(date)
**Job:** $JOB_FILE
**Model:** $MODEL_NAME
**Extraction ID:** $OUTPUT_PREFIX

## 🎯 Technical Skills
$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}03_technical_skills.txt")

## 🏢 Business Requirements  
$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}04_business_requirements.txt")

## 📊 Experience Requirements
$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}05_experience_requirements.txt")

## 🎓 Education Requirements
$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}06_education_requirements.txt")

## 🤝 Soft Skills
$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}07_soft_skills.txt")

## ⭐ Proficiency Levels
$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}08_proficiency_rating.txt")

## 🏆 Priority Classification
$(cat "${OUTPUT_DIR}/${OUTPUT_PREFIX}09_priority_classification.txt")

---
*Generated by The Ultimate Job Requirements Extractor - Gemma3n Weapon*
*Forged by Zara, Queen of Strategic Extraction*
EOF

    print_success "Battle report generated → $report_file"
    
    echo -e "${WHITE}📋 EXTRACTION SUMMARY:${NC}"
    echo -e "${GREEN}   Technical Skills: $(grep -c "•" "${OUTPUT_DIR}/${OUTPUT_PREFIX}03_technical_skills.txt" 2>/dev/null || echo "0") items${NC}"
    echo -e "${GREEN}   Business Reqs: $(grep -c "•" "${OUTPUT_DIR}/${OUTPUT_PREFIX}04_business_requirements.txt" 2>/dev/null || echo "0") items${NC}"
    echo -e "${GREEN}   Experience Reqs: $(grep -c "•" "${OUTPUT_DIR}/${OUTPUT_PREFIX}05_experience_requirements.txt" 2>/dev/null || echo "0") items${NC}"
    echo -e "${GREEN}   Education Reqs: $(grep -c "•" "${OUTPUT_DIR}/${OUTPUT_PREFIX}06_education_requirements.txt" 2>/dev/null || echo "0") items${NC}"
    echo -e "${GREEN}   Soft Skills: $(grep -c "•" "${OUTPUT_DIR}/${OUTPUT_PREFIX}07_soft_skills.txt" 2>/dev/null || echo "0") items${NC}"
    echo
}

# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND LINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

show_usage() {
    echo -e "${WHITE}Usage: $0 [OPTIONS] <job_file>${NC}"
    echo
    echo -e "${YELLOW}Options:${NC}"
    echo -e "  -h, --help              Show this help message"
    echo -e "  -m, --model MODEL       Specify Ollama model (default: gemma3n)"
    echo -e "  -o, --output-dir DIR    Specify output directory (default: ./extraction_results)"
    echo -e "  -p, --prefix PREFIX     Output file prefix (default: job_{timestamp}_)"
    echo
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  $0 job_posting.txt"
    echo -e "  $0 -m qwen2.5 -o /tmp/extractions job.md"
    echo -e "  $0 --prefix security_job_ security_specialist.txt"
    echo
    echo -e "${CYAN}This weapon will systematically extract and classify all job requirements${NC}"
    echo -e "${CYAN}using the strategic 9-step extraction process designed by Zara.${NC}"
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -m|--model)
                MODEL_NAME="$2"
                shift 2
                ;;
            -o|--output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -p|--prefix)
                OUTPUT_PREFIX="$2"
                shift 2
                ;;
            -*)
                print_error "Unknown option: $1"
                ;;
            *)
                if [[ -z "$JOB_FILE" ]]; then
                    JOB_FILE="$1"
                else
                    print_error "Multiple job files specified. Use only one."
                fi
                shift
                ;;
        esac
    done
    
    if [[ -z "$JOB_FILE" ]]; then
        print_error "Job file is required. Use -h for help."
    fi
    
    if [[ -z "$OUTPUT_PREFIX" ]]; then
        OUTPUT_PREFIX="job_${TIMESTAMP}_"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN BATTLE SEQUENCE
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    print_banner
    
    parse_arguments "$@"
    
    echo -e "${WHITE}🎯 BATTLE CONFIGURATION:${NC}"
    echo -e "   Job File: ${CYAN}$JOB_FILE${NC}"
    echo -e "   Model: ${CYAN}$MODEL_NAME${NC}"
    echo -e "   Output Dir: ${CYAN}$OUTPUT_DIR${NC}"
    echo -e "   Prefix: ${CYAN}$OUTPUT_PREFIX${NC}"
    echo
    
    check_battle_readiness
    execute_full_extraction
    generate_battle_report
    
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${WHITE}                           ⚔️  VICTORY ACHIEVED ⚔️                             ${NC}"
    echo -e "${GREEN}         Job requirements extracted with surgical precision!${NC}"
    echo -e "${CYAN}         Check ${OUTPUT_DIR}/${OUTPUT_PREFIX}FINAL_EXTRACTION_REPORT.md${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════${NC}"
}

# Execute main function with all arguments
main "$@"