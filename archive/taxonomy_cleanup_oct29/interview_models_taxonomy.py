#!/usr/bin/env python3
"""
LLM Interview Script: Skills Taxonomy Design
Interview multiple LLMs about skill hierarchy standards and test their recommendations
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path

# Models to interview
MODELS = [
    "phi3:latest",
    "llama3.2:latest", 
    "qwen2.5:7b",
    "mistral-nemo:12b"
]

# Sample skills for testing (from database)
TEST_SKILLS = [
    "Network Architecture",
    "Financial Modeling",
    "Strategic Planning",
    "Tax And Financial Knowledge",
    "Risk Mitigation Strategies",
    "Testing Skills",
    "Strategic Thinking Skills",
    "Flexibility",
    "Network Security Deployment Plans",
    "Listening Skills",
    "Training Skills",
    "Operations Management",
    "Business Process Improvement",
    "Relationship Building Strategies",
    "Requirement Gathering",
    "Healthcare Knowledge"
]

# Interview questions
QUESTIONS = [
    {
        "step": 1,
        "question": """I'm Arden, working on a skills taxonomy for a job-candidate matching system. We have 287 professional skills extracted from job postings (like Network Security, Financial Modeling, Strategic Planning, etc.) that need to be organized into a hierarchical structure.

Our goal: Build a multi-level taxonomy where recruiters can browse skills by category and match candidates to jobs based on skill hierarchies.

What established skill taxonomy standards are you familiar with? (Examples: O*NET, ESCO, LinkedIn Skills Graph, etc.)

Please list 3-5 standards you know about."""
    },
    {
        "step": 2,
        "question": """Based on your knowledge of these taxonomy standards, which ONE would you recommend we adopt as our foundation for a job-candidate matching system?

Please explain:
- Which standard you recommend
- Why it's the best fit for job matching
- What the top-level categories are in that standard
- How many levels deep the hierarchy typically goes"""
    },
    {
        "step": 3,
        "question": f"""Now let's test your recommended taxonomy with real skills from our database. Here are 16 skills that need to be organized:

{chr(10).join(f"- {skill}" for skill in TEST_SKILLS)}

TASK: Place each of these skills into the hierarchical taxonomy you recommended. Show the complete path for each skill.

Format example:
TECHNICAL_SKILLS > IT_INFRASTRUCTURE > NETWORKING > Network Architecture
BUSINESS_SKILLS > FINANCE > FINANCIAL_ANALYSIS > Financial Modeling

Please categorize ALL 16 skills."""
    }
]

def run_interview(model):
    """Run complete interview with one model"""
    
    print(f"\n{'='*80}")
    print(f"🎤 INTERVIEWING: {model}")
    print(f"{'='*80}\n")
    
    interview_log = {
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "questions": [],
        "responses": []
    }
    
    # Clear conversation history
    subprocess.run(
        ['python3', 'llm_chat.py', model, 'clear'],
        capture_output=True
    )
    
    # Ask each question
    for q in QUESTIONS:
        print(f"\n📋 Step {q['step']}:")
        print(f"Question: {q['question'][:100]}...")
        print(f"\n⏳ Asking {model}...\n")
        
        try:
            # Run WITHOUT capture_output so it streams to console
            result = subprocess.run(
                ['python3', 'llm_chat.py', model, 'send', q['question']],
                text=True,
                timeout=300,
                capture_output=False  # Let it print to screen in real-time
            )
            
            # Save to conversation history for next question
            # Read back the saved conversation to get the response
            conv_file = Path(f"temp/conversation_{model.replace(':', '_').replace('.', '_')}.json")
            if conv_file.exists():
                with open(conv_file, 'r') as f:
                    history = json.load(f)
                    if history:
                        # Get last assistant response
                        last_response = history[-1]['content'] if history[-1]['role'] == 'assistant' else "No response"
                        response = last_response
                    else:
                        response = "No response recorded"
            else:
                response = "Conversation file not found"
            
            print(f"\n✅ Response received ({len(response)} chars)\n")
            
            interview_log["questions"].append(q['question'])
            interview_log["responses"].append({
                "step": q['step'],
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
            
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT - {model} took too long\n")
            interview_log["responses"].append({
                "step": q['step'],
                "response": "TIMEOUT - Model took longer than 5 minutes",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"❌ ERROR: {e}\n")
            interview_log["responses"].append({
                "step": q['step'],
                "response": f"ERROR: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    return interview_log

def save_results(all_interviews):
    """Save interview results as JSON and Markdown"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create output directory
    output_dir = Path("temp/skill_taxonomy_interviews")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    json_file = output_dir / f"interviews_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(all_interviews, indent=2, fp=f)
    
    print(f"\n💾 JSON saved: {json_file}")
    
    # Generate Markdown report
    md_file = output_dir / f"interviews_{timestamp}.md"
    
    md_lines = [
        "# LLM Interviews: Skills Taxonomy Design",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Models Interviewed:** {len(all_interviews)}",
        "",
        "---",
        ""
    ]
    
    for interview in all_interviews:
        model = interview['model']
        md_lines.append(f"## 🤖 Interview with {model}")
        md_lines.append("")
        md_lines.append(f"**Timestamp:** {interview['timestamp']}")
        md_lines.append("")
        
        for i, response in enumerate(interview['responses'], 1):
            question = interview['questions'][i-1] if i <= len(interview['questions']) else "N/A"
            
            md_lines.append(f"### Step {response['step']}")
            md_lines.append("")
            md_lines.append("**Question:**")
            md_lines.append(f"```")
            md_lines.append(question)
            md_lines.append(f"```")
            md_lines.append("")
            md_lines.append("**Response:**")
            md_lines.append("")
            md_lines.append(response['response'])
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
        
        md_lines.append("")
    
    # Summary
    md_lines.append("## 📊 Summary")
    md_lines.append("")
    md_lines.append("### Taxonomy Recommendations:")
    md_lines.append("")
    
    for interview in all_interviews:
        model = interview['model']
        step2_response = next((r for r in interview['responses'] if r['step'] == 2), None)
        if step2_response:
            recommendation = step2_response['response'][:200] + "..."
            md_lines.append(f"**{model}:** {recommendation}")
            md_lines.append("")
    
    with open(md_file, 'w') as f:
        f.write('\n'.join(md_lines))
    
    print(f"📄 Markdown report: {md_file}")
    print(f"\n✅ All interviews complete!")
    
    return json_file, md_file

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  🎤 LLM INTERVIEWS: Skills Taxonomy Design                          ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"\n📋 Interviewing {len(MODELS)} models")
    print(f"🎯 Testing with {len(TEST_SKILLS)} real skills")
    print(f"⏱️  Estimated time: {len(MODELS) * 15} minutes (max)\n")
    
    all_interviews = []
    
    for i, model in enumerate(MODELS, 1):
        print(f"\n\n{'#'*80}")
        print(f"# Interview {i}/{len(MODELS)}: {model}")
        print(f"{'#'*80}")
        
        try:
            interview_log = run_interview(model)
            all_interviews.append(interview_log)
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Failed to interview {model}: {e}")
            continue
    
    if all_interviews:
        json_file, md_file = save_results(all_interviews)
        print(f"\n\n{'='*80}")
        print(f"🎉 INTERVIEWS COMPLETE")
        print(f"{'='*80}")
        print(f"\n📂 Results saved to:")
        print(f"   JSON: {json_file}")
        print(f"   Markdown: {md_file}")
        print(f"\n💡 Review the Markdown file to compare recommendations!")
    else:
        print("\n❌ No interviews completed")

if __name__ == "__main__":
    main()
