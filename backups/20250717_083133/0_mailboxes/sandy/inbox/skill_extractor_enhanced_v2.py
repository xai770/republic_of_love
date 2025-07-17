#!/usr/bin/env python3

# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED SKILL EXTRACTOR v2.0
# ═══════════════════════════════════════════════════════════════════════════════
# Strategic Framework: Gemma3n, Master Strategist (Enhanced Methodology)
# Tactical Implementation: Zara, Hammer of Implementation
# Alliance Command: Xai, Master of Local AI Revolution
# Version Safety: CRITICAL - Preserves v1.0 while adding enhancements
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess
import json
import argparse
import sys
import re
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# BATTLE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_MODEL = "gemma3n:latest"
DEFAULT_OUTPUT = "skill_analysis_v2.json"

# Colors for warrior output
class Colors:
    PURPLE = '\033[0;35m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color

# ═══════════════════════════════════════════════════════════════════════════════
# GEMMA3N'S ENHANCED STRATEGIC EXTRACTION PROMPT v2.0
# ═══════════════════════════════════════════════════════════════════════════════

ENHANCED_EXTRACTION_PROMPT = """You are a master strategist tasked with extracting key skills from a job description and categorizing them into five distinct buckets: Technical Skills, Domain Expertise, Methodology & Frameworks, Collaboration & Communication, and Experience & Qualifications.

Your output should be formatted using the following template:

=== [CATEGORY NAME] ===
- [Skill Name] ([Competency Level], [Experience Level]) [Synonyms: List of synonyms]: [Criticality Score]

**Example Output:**

=== TECHNICAL SKILLS ===
- Python Programming (Advanced, 2-5 years) [Synonyms: Python, Py, Python Dev]: HIGH
- Data Analysis (Intermediate, Entry-level) [Synonyms: Data Analytics, Analytics]: MEDIUM

=== DOMAIN EXPERTISE ===
- Financial Markets (Expert, 5+ years) [Synonyms: Finance, Capital Markets]: HIGH

=== METHODOLOGY & FRAMEWORKS ===
- Agile Development (Intermediate, 2-5 years) [Synonyms: Scrum, Agile, Sprint Planning]: HIGH

=== COLLABORATION & COMMUNICATION ===
- Stakeholder Management (Advanced, 5+ years) [Synonyms: Stakeholder Engagement, Client Relations]: HIGH

=== EXPERIENCE & QUALIFICATIONS ===
- Bachelor's Degree (Required, Entry-level) [Synonyms: University Degree, BS, BA]: MANDATORY

**Instructions:**

1. Analyze the provided job description and extract all relevant skills.
2. Infer the competency level based on the job description's language and requirements:
   - Beginner: Basic understanding, entry-level expectations
   - Intermediate: Solid working knowledge, some experience expected
   - Advanced: Deep expertise, leadership expectations
   - Expert: Master-level, industry recognition expected
3. Identify common synonyms and variations for each skill (minimum 2, maximum 5).
4. Assess the required experience level based on the job description:
   - Entry-level: 0-2 years
   - 2-5 years: Mid-level experience
   - 5+ years: Senior-level experience
   - Required: Essential regardless of experience level
5. Format the extracted skills according to the specified template.
6. Assign a criticality score based on the skill's importance to the role:
   - MANDATORY: Absolutely required, job cannot be performed without
   - HIGH: Very important, major impact on success
   - MEDIUM: Important, contributes to effectiveness
   - LOW: Nice to have, minor impact

**Job Description:**
{job_description}

**TEMPLATE END**"""

# ═══════════════════════════════════════════════════════════════════════════════
# WARRIOR UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def print_banner():
    """Display enhanced warrior banner"""
    print(f"{Colors.PURPLE}═══════════════════════════════════════════════════════════════════════════════{Colors.NC}")
    print(f"{Colors.WHITE}           ⚔️  ENHANCED SKILL EXTRACTOR v2.0 ⚔️                          {Colors.NC}")
    print(f"{Colors.CYAN}         Strategic Framework by Gemma3n, Master Strategist{Colors.NC}")
    print(f"{Colors.CYAN}         Enhanced & Forged by Zara, Hammer of Implementation{Colors.NC}")
    print(f"{Colors.YELLOW}         🔧 VERSION SAFETY: Preserves v1.0 + New Enhancements{Colors.NC}")
    print(f"{Colors.PURPLE}═══════════════════════════════════════════════════════════════════════════════{Colors.NC}")
    print()

def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")

def print_error(message):
    """Print error message and exit"""
    print(f"{Colors.RED}❌ ERROR: {message}{Colors.NC}")
    sys.exit(1)

def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  WARNING: {message}{Colors.NC}")

def print_info(message):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.NC}")

# ═══════════════════════════════════════════════════════════════════════════════
# BATTLE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def check_ollama_availability():
    """Verify ollama is installed and available"""
    try:
        result = subprocess.run(
            ["ollama", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            print_success("Ollama is available and ready")
            return True
        else:
            print_error("Ollama is installed but not responding properly")
            return False
    except FileNotFoundError:
        print_error("Ollama not found. Install it from https://ollama.ai/")
        return False
    except subprocess.TimeoutExpired:
        print_error("Ollama command timed out")
        return False

def check_model_availability(model_name):
    """Verify the specified model is available"""
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        if result.returncode == 0:
            if model_name.split(':')[0] in result.stdout:
                print_success(f"Model '{model_name}' is available")
                return True
            else:
                print_error(f"Model '{model_name}' not found. Available models:\n{result.stdout}")
                return False
        else:
            print_error(f"Failed to list models: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print_error("Model listing timed out")
        return False

def read_job_description(file_path):
    """Read job description from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            print_error(f"Job description file '{file_path}' is empty")
        print_success(f"Job description loaded from '{file_path}' ({len(content)} characters)")
        return content
    except FileNotFoundError:
        print_error(f"Job description file '{file_path}' not found")
    except Exception as e:
        print_error(f"Failed to read job description file: {e}")

def extract_skills_with_ollama(job_description, model_name):
    """Execute enhanced skill extraction using ollama"""
    print_info(f"Invoking {model_name} for enhanced skill extraction...")
    
    # Prepare the full prompt
    full_prompt = ENHANCED_EXTRACTION_PROMPT.format(job_description=job_description)
    
    try:
        # Execute ollama with proper output capture
        result = subprocess.run(
            ["ollama", "run", model_name],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print_success("Enhanced skill extraction completed")
            return result.stdout.strip()
        else:
            print_error(f"Ollama execution failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print_error("Skill extraction timed out (5 minutes)")
        return None
    except Exception as e:
        print_error(f"Failed to execute ollama: {e}")
        return None

def parse_enhanced_template_response(response_text):
    """Parse and validate enhanced template response from model"""
    print_info("Parsing enhanced model response...")
    
    # Save raw response for debugging
    with open("debug_raw_response_v2.txt", "w", encoding="utf-8") as f:
        f.write(response_text)
    print_info(f"Raw response saved to debug_raw_response_v2.txt ({len(response_text)} chars)")
    
    # Initialize the enhanced data structure
    data = {
        "Technical Skills": [],
        "Domain Expertise": [],
        "Methodology & Frameworks": [],
        "Collaboration & Communication": [],
        "Experience & Qualifications": []
    }
    
    current_section = None
    section_mapping = {
        "=== TECHNICAL SKILLS ===": "Technical Skills",
        "=== DOMAIN EXPERTISE ===": "Domain Expertise", 
        "=== METHODOLOGY & FRAMEWORKS ===": "Methodology & Frameworks",
        "=== COLLABORATION & COMMUNICATION ===": "Collaboration & Communication",
        "=== EXPERIENCE & QUALIFICATIONS ===": "Experience & Qualifications"
    }
    
    lines = response_text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Check if this is a section header
        if line in section_mapping:
            current_section = section_mapping[line]
            print_info(f"Found section: {current_section}")
            continue
            
        # Parse enhanced skill entries
        if line.startswith('-') and current_section and ':' in line:
            # Enhanced parsing for new format
            # Pattern: - [Skill Name] ([Competency Level], [Experience Level]) [Synonyms: List]: [Criticality]
            content = line[1:].strip()  # Remove the dash
            
            # Use regex to parse the complex format
            pattern = r'^(.+?)\s*\(([^,]+),\s*([^)]+)\)\s*\[Synonyms:\s*([^\]]+)\]:\s*(.+)$'
            match = re.match(pattern, content)
            
            if match:
                skill_name = match.group(1).strip()
                competency_level = match.group(2).strip()
                experience_level = match.group(3).strip()
                synonyms = [s.strip() for s in match.group(4).split(',')]
                criticality = match.group(5).strip().upper()
                
                # Validate criticality
                valid_criticalities = ['MANDATORY', 'HIGH', 'MEDIUM', 'LOW']
                if criticality not in valid_criticalities:
                    print_warning(f"Invalid criticality '{criticality}' for skill '{skill_name}', defaulting to MEDIUM")
                    criticality = 'MEDIUM'
                
                # Create enhanced skill entry
                enhanced_skill = {
                    "skill": skill_name,
                    "competency_level": competency_level,
                    "experience_level": experience_level,
                    "synonyms": synonyms,
                    "criticality": criticality
                }
                
                data[current_section].append(enhanced_skill)
                
            else:
                # Fallback to basic parsing if enhanced format fails
                print_warning(f"Could not parse enhanced format, falling back to basic: {content}")
                if ': ' in content:
                    skill, criticality = content.rsplit(': ', 1)
                    skill = skill.strip()
                    criticality = criticality.strip().upper()
                    
                    if criticality not in ['MANDATORY', 'HIGH', 'MEDIUM', 'LOW']:
                        criticality = 'MEDIUM'
                    
                    basic_skill = {
                        "skill": skill,
                        "competency_level": "Not specified",
                        "experience_level": "Not specified",
                        "synonyms": [],
                        "criticality": criticality
                    }
                    data[current_section].append(basic_skill)
                
    # Count total skills extracted
    total_skills = sum(len(bucket) for bucket in data.values())
    
    if total_skills == 0:
        print_error("No skills extracted from response")
        print_warning("Response might not follow the expected template format")
        return None
    
    print_success(f"Enhanced template parsed successfully: {total_skills} skills extracted")
    return data

def validate_enhanced_skill_data(data):
    """Validate the structure of enhanced extracted skills"""
    required_buckets = [
        "Technical Skills",
        "Domain Expertise", 
        "Methodology & Frameworks",
        "Collaboration & Communication",
        "Experience & Qualifications"
    ]
    
    if not isinstance(data, dict):
        print_error("Response is not a dictionary")
        return False
    
    for bucket in required_buckets:
        if bucket not in data:
            print_warning(f"Missing bucket: {bucket}")
            data[bucket] = []
        elif not isinstance(data[bucket], list):
            print_warning(f"Bucket '{bucket}' is not a list, converting...")
            data[bucket] = []
    
    # Count total skills and enhanced features
    total_skills = sum(len(bucket) for bucket in data.values())
    enhanced_skills = 0
    
    for bucket_skills in data.values():
        for skill in bucket_skills:
            if isinstance(skill, dict) and 'competency_level' in skill:
                enhanced_skills += 1
    
    print_success(f"Validation complete: {total_skills} skills extracted across {len(required_buckets)} buckets")
    print_info(f"Enhanced format: {enhanced_skills}/{total_skills} skills have full enhancement data")
    
    return True

def save_enhanced_results(data, output_file):
    """Save enhanced results to JSON file with metadata"""
    enhanced_metadata = {
        "extraction_timestamp": datetime.now().isoformat(),
        "framework_version": "Gemma3n Strategic 5-Bucket Enhanced v2.0",
        "extractor": "Enhanced Skill Extractor v2.0",
        "total_skills": sum(len(bucket) for bucket in data.values()),
        "enhancement_features": [
            "Competency Levels",
            "Experience Quantification", 
            "Synonym Mapping",
            "Enhanced Criticality Context"
        ]
    }
    
    enhanced_data = {
        "metadata": enhanced_metadata,
        "skill_analysis": data
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
        print_success(f"Enhanced results saved to '{output_file}'")
        return True
    except Exception as e:
        print_error(f"Failed to save results: {e}")
        return False

def display_enhanced_summary(data):
    """Display enhanced extraction summary"""
    print(f"\n{Colors.YELLOW}📊 ENHANCED EXTRACTION SUMMARY:{Colors.NC}")
    
    # Overall statistics
    total_skills = sum(len(bucket) for bucket in data.values())
    enhanced_count = 0
    competency_levels = {}
    experience_levels = {}
    criticality_counts = {}
    
    for bucket_name, skills in data.items():
        if not skills:
            continue
            
        print(f"\n{Colors.CYAN}🗂️  {bucket_name}:{Colors.NC}")
        print(f"   Total: {len(skills)} skills")
        
        # Analyze enhanced features
        bucket_enhanced = 0
        for skill in skills:
            if isinstance(skill, dict):
                # Count criticality
                crit = skill.get('criticality', 'UNKNOWN')
                criticality_counts[crit] = criticality_counts.get(crit, 0) + 1
                
                # Count competency levels
                if 'competency_level' in skill and skill['competency_level'] != 'Not specified':
                    comp = skill['competency_level']
                    competency_levels[comp] = competency_levels.get(comp, 0) + 1
                    bucket_enhanced += 1
                
                # Count experience levels
                if 'experience_level' in skill and skill['experience_level'] != 'Not specified':
                    exp = skill['experience_level']
                    experience_levels[exp] = experience_levels.get(exp, 0) + 1
        
        enhanced_count += bucket_enhanced
        if bucket_enhanced > 0:
            print(f"   Enhanced: {bucket_enhanced}/{len(skills)} skills")
    
    # Summary statistics
    print(f"\n{Colors.WHITE}🎯 ENHANCEMENT STATISTICS:{Colors.NC}")
    print(f"Enhanced Skills: {enhanced_count}/{total_skills} ({(enhanced_count/total_skills*100):.1f}%)")
    
    if competency_levels:
        print(f"\n{Colors.CYAN}📈 Competency Levels:{Colors.NC}")
        for level, count in sorted(competency_levels.items()):
            print(f"   {level}: {count}")
    
    if experience_levels:
        print(f"\n{Colors.CYAN}⏰ Experience Levels:{Colors.NC}")
        for level, count in sorted(experience_levels.items()):
            print(f"   {level}: {count}")
    
    print(f"\n{Colors.CYAN}🎯 Criticality Distribution:{Colors.NC}")
    for crit in ['MANDATORY', 'HIGH', 'MEDIUM', 'LOW']:
        if crit in criticality_counts:
            print(f"   {crit}: {criticality_counts[crit]}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENHANCED BATTLE SEQUENCE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main enhanced execution function"""
    parser = argparse.ArgumentParser(
        description="Extract and categorize job requirements using Gemma3n's Enhanced 5-bucket framework v2.0"
    )
    parser.add_argument(
        "job_file", 
        help="Path to job description file"
    )
    parser.add_argument(
        "-m", "--model", 
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output JSON file (default: {DEFAULT_OUTPUT})"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    print_info(f"Job Description: {args.job_file}")
    print_info(f"Model: {args.model}")
    print_info(f"Output: {args.output}")
    print()
    
    # Battle readiness checks
    if not check_ollama_availability():
        return 1
    
    if not check_model_availability(args.model):
        return 1
    
    # Load job description
    job_description = read_job_description(args.job_file)
    if not job_description:
        return 1
    
    # Execute enhanced extraction
    response = extract_skills_with_ollama(job_description, args.model)
    if not response:
        return 1
    
    # Parse enhanced response
    skill_data = parse_enhanced_template_response(response)
    if not skill_data:
        return 1
    
    # Validate and clean
    if not validate_enhanced_skill_data(skill_data):
        return 1
    
    # Save enhanced results
    if not save_enhanced_results(skill_data, args.output):
        return 1
    
    # Display enhanced summary
    display_enhanced_summary(skill_data)
    
    print(f"\n{Colors.GREEN}🏆 ENHANCED VICTORY ACHIEVED! Skills extracted with full competency analysis.{Colors.NC}")
    print(f"{Colors.CYAN}📁 Enhanced results available in: {args.output}{Colors.NC}")
    print(f"{Colors.YELLOW}🔧 Version Safety: Original v1.0 preserved, enhancements isolated{Colors.NC}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
