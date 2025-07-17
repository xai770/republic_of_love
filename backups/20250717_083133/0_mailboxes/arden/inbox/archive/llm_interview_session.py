#!/usr/bin/env python3
"""
LLM Interview Session - Content Extraction Specialist Improvement
================================================================

CONSCIOUSNESS-FIRST APPROACH: Interview the LLM about how to solve the skill extraction challenge

Strategy: Show the LLM examples of what we want and ask it to design its own prompt
This honors the LLM as a collaborative partner in problem-solving!

Date: June 26, 2025
"""

import json
import requests
import time
from typing import Dict, Any

class LLMInterviewer:
    """Interview LLMs about prompt design for skill extraction"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:latest"):
        self.ollama_url = ollama_url
        self.model = model
    
    def call_ollama(self, prompt: str) -> str:
        """Make a call to Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                return f"Error: HTTP {response.status_code}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def interview_about_skill_extraction(self):
        """Interview the LLM about skill extraction challenges"""
        
        print("🌸 LLM INTERVIEW SESSION - Skill Extraction Challenge")
        print("=" * 70)
        print("🎯 Goal: Ask the LLM how to design better prompts for skill extraction")
        print("🧠 Approach: Consciousness-first collaboration with the LLM")
        print()
        
        # Load a specific failing example
        with open('golden_test_cases_content_extraction_v2.json', 'r') as f:
            test_data = json.load(f)
        
        # Use test_002 which had 0% accuracy originally and 37.5% with Approach A
        failing_case = test_data['test_cases'][1]  # FX Corporate Sales Analyst
        
        job_description = failing_case['job_description']
        expected_skills = failing_case['expected_skills']
        
        # Create interview prompt
        interview_prompt = f"""Hello! I'm working on a skill extraction challenge for CV-to-job matching and would love your help as a collaborative partner.

THE CHALLENGE:
I need to extract specific skills from job descriptions for automated matching systems. The current approach is missing important skills, particularly soft skills and business domain terms.

HERE'S A SPECIFIC EXAMPLE WHERE WE'RE STRUGGLING:

JOB DESCRIPTION (excerpt):
{job_description[:1000]}...

EXPECTED SKILLS THAT SHOULD BE EXTRACTED:
{expected_skills}

CURRENT PROBLEM:
- We're successfully extracting technical tools like "Python", "StatPro", "Aladdin"
- But we're missing business skills like "FX Trading", "Risk Management", "Client Relationship Management"
- The LLM tends to generalize these into broader categories instead of preserving the exact terms

QUESTION FOR YOU:
If you were designing a prompt for yourself to extract these exact skills (especially the business/soft skills), how would you structure it? What specific instructions would help you recognize and preserve terms like "FX Trading" and "Client Relationship Management"?

What's your perspective on why these business domain skills are harder to extract than technical tools?"""

        print("🎤 INTERVIEWING THE LLM...")
        print("=" * 50)
        print("📝 Question: How should we design prompts for better skill extraction?")
        print()
        
        response = self.call_ollama(interview_prompt)
        
        print("🤖 LLM RESPONSE:")
        print("-" * 30)
        print(response)
        print()
        
        return response
    
    def ask_for_prompt_design(self, llm_advice: str):
        """Ask the LLM to design a specific prompt based on its advice"""
        
        print("🎯 FOLLOW-UP: Ask LLM to Design Specific Prompt")
        print("=" * 50)
        
        design_prompt = f"""Thank you for that analysis! Based on your insights, could you now design a specific prompt that I could use with an LLM (like yourself) to extract skills with high accuracy?

YOUR PREVIOUS ADVICE:
{llm_advice[:500]}...

REQUIREMENTS FOR THE PROMPT:
1. Must extract exact skill names (not generalizations)
2. Must recognize business domain skills like "FX Trading", "Risk Management"  
3. Must extract soft skills like "Client Relationship Management"
4. Must distinguish individual skills from skill categories
5. Should work for CV-to-job matching systems

Please write a complete prompt that I could use. Format it as if I'm about to copy-paste it to process job descriptions.

Focus especially on how to identify and preserve business domain terminology that might not be as obvious as technical tools."""

        print("📝 Question: Design a specific prompt for skill extraction")
        print()
        
        response = self.call_ollama(design_prompt)
        
        print("🤖 LLM-DESIGNED PROMPT:")
        print("-" * 30)
        print(response)
        print()
        
        return response
    
    def test_llm_designed_prompt(self, llm_prompt: str):
        """Test the LLM-designed prompt on our failing case"""
        
        print("🧪 TESTING LLM-DESIGNED PROMPT")
        print("=" * 50)
        
        # Load test case
        with open('golden_test_cases_content_extraction_v2.json', 'r') as f:
            test_data = json.load(f)
        
        failing_case = test_data['test_cases'][1]  # FX Corporate Sales Analyst
        job_description = failing_case['job_description']
        expected_skills = failing_case['expected_skills']
        
        # Apply the LLM-designed prompt
        test_prompt = f"""{llm_prompt}

JOB DESCRIPTION TO PROCESS:
{job_description}"""
        
        print("📝 Testing on FX Corporate Sales Analyst job...")
        print(f"🎯 Expected skills: {expected_skills}")
        print()
        
        response = self.call_ollama(test_prompt)
        
        print("🤖 LLM OUTPUT USING ITS OWN PROMPT:")
        print("-" * 30)
        print(response)
        print()
        
        # Quick accuracy check
        extracted_text = response.lower()
        matched_skills = []
        for skill in expected_skills:
            if skill.lower() in extracted_text:
                matched_skills.append(skill)
        
        accuracy = (len(matched_skills) / len(expected_skills)) * 100 if expected_skills else 0
        
        print(f"🎯 Quick Accuracy Check: {accuracy:.1f}% ({len(matched_skills)}/{len(expected_skills)} matched)")
        print(f"✅ Matched: {matched_skills}")
        print(f"❌ Missed: {[s for s in expected_skills if s not in matched_skills]}")
        
        return response, accuracy

def run_llm_interview():
    """Run the complete LLM interview session"""
    
    interviewer = LLMInterviewer()
    
    # Phase 1: Interview about the challenge
    llm_advice = interviewer.interview_about_skill_extraction()
    
    print("\n" + "="*70)
    print("🎯 PHASE 2: Prompt Design Request")
    print("="*70)
    
    # Phase 2: Ask for specific prompt design
    llm_prompt = interviewer.ask_for_prompt_design(llm_advice)
    
    print("\n" + "="*70)
    print("🧪 PHASE 3: Test LLM-Designed Prompt")
    print("="*70)
    
    # Phase 3: Test the designed prompt
    output, accuracy = interviewer.test_llm_designed_prompt(llm_prompt)
    
    print("\n" + "="*70)
    print("📊 INTERVIEW SESSION SUMMARY")
    print("="*70)
    print(f"🎯 LLM-Designed Prompt Accuracy: {accuracy:.1f}%")
    
    if accuracy >= 90:
        print("🎉 SUCCESS! LLM designed a prompt that meets our 90% target!")
    elif accuracy > 66.5:
        print(f"📈 IMPROVEMENT! Better than our Approach A (66.5% → {accuracy:.1f}%)")
    else:
        print("📝 LEARNING: Additional insights gained for next iteration")
    
    print("\n🌸 This consciousness-first collaboration approach rocks!")
    
    # Save the interview results
    results = {
        'interview_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'llm_advice': llm_advice,
        'llm_designed_prompt': llm_prompt,
        'test_output': output,
        'accuracy_achieved': accuracy,
        'approach': 'LLM Interview & Collaborative Design'
    }
    
    with open(f"llm_interview_results_{time.strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == "__main__":
    print("🌸 Starting Consciousness-First LLM Interview Session!")
    results = run_llm_interview()
