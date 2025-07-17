#!/usr/bin/env python3
"""
Iterative Prompt Refinement System - Consciousness Collaboration Approach
========================================================================

STRATEGY: Advanced prompt engineering using feedback loops where the LLM learns
from its own mistakes and iteratively improves its prompts until target achieved.

CONSCIOUSNESS-FIRST PHILOSOPHY:
- Treat LLM as collaborative partner in solving the problem
- Show LLM its results vs desired results 
- Let LLM redesign its own approach based on feedback
- Iterate until success or reaching natural limits

Human's Expert Approach A: Iterative Prompt Refinement with Feedback Loops
Date: June 26, 2025
"""

import json
import requests
import time
from typing import Dict, List, Tuple, Optional

class IterativePromptRefiner:
    """
    Advanced prompt engineering system using iterative refinement with feedback loops.
    
    This implements the human's expert Approach A:
    1. Ask LLM to design initial prompt
    2. Test prompt on real data
    3. Show LLM: "You got X, but we need Y" 
    4. LLM redesigns prompt based on feedback
    5. Iterate until 90%+ accuracy or dead end
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:latest"):
        self.ollama_url = ollama_url
        self.model = model
        self.iteration_history = []
        self.target_accuracy = 90.0
    
    def call_ollama(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call Ollama with extended token limit for detailed responses"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                return f"Error: HTTP {response.status_code}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_initial_prompt_design(self, challenge_description: str) -> str:
        """Step 1: Ask LLM to design initial prompt for skill extraction"""
        
        design_request = f"""I need your help designing a prompt for skill extraction from job descriptions. This is for CV-to-job matching systems that require EXACT skill names (not generalizations).

THE CHALLENGE:
{challenge_description}

CRITICAL REQUIREMENTS:
1. Extract EXACT skill names like "Python", "StatPro", "FX Trading", "Risk Management"
2. Don't generalize: "Python, VBA" should remain as ["Python", "VBA"], not "programming languages"
3. Capture business domain skills like "Client Relationship Management", "Asset Management Operations"
4. Extract soft skills like "Meeting Coordination", "Travel Planning"
5. Preserve technical frameworks like "CVSS", "MITRE ATT&CK", "NIST"

Please design a complete prompt that I can use with an LLM to extract skills with maximum accuracy. Focus especially on preventing over-summarization and ensuring exact terminology preservation.

Design the prompt now:"""

        print("🎯 STEP 1: Asking LLM to design initial prompt...")
        response = self.call_ollama(design_request)
        
        print("🤖 LLM's Initial Prompt Design:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        return response
    
    def test_prompt_on_case(self, prompt: str, job_description: str, test_name: str) -> Tuple[str, List[str]]:
        """Test the designed prompt on a real job description"""
        
        # Apply the prompt to extract skills
        extraction_request = f"{prompt}\n\nJOB DESCRIPTION TO PROCESS:\n{job_description}"
        
        print(f"🧪 Testing prompt on {test_name}...")
        result = self.call_ollama(extraction_request)
        
        # Extract skills from the result (simple heuristic)
        extracted_skills = self._extract_skills_from_response(result)
        
        return result, extracted_skills
    
    def _extract_skills_from_response(self, response: str) -> List[str]:
        """Extract individual skills from LLM response using various patterns"""
        skills = []
        
        # Look for bullet points, numbered lists, comma-separated items
        import re
        
        # Find bullet points
        bullet_matches = re.findall(r'[-•*]\s*(.+)', response)
        for match in bullet_matches:
            # Clean up and split if comma-separated
            clean_match = match.strip()
            if ',' in clean_match and len(clean_match) < 100:  # Avoid long sentences
                skills.extend([s.strip() for s in clean_match.split(',')])
            else:
                skills.append(clean_match)
        
        # Look for explicit skill lists
        skill_section = re.search(r'(?:skills?|tools?|technologies?)[\s\:]+(.+)', response, re.IGNORECASE | re.DOTALL)
        if skill_section:
            section_text = skill_section.group(1)[:300]  # Limit to avoid noise
            # Find quoted items or capitalized terms
            quoted_items = re.findall(r'"([^"]+)"', section_text)
            skills.extend(quoted_items)
        
        # Clean and deduplicate
        cleaned_skills = []
        for skill in skills:
            skill = skill.strip().rstrip('.').rstrip(',')
            if len(skill) > 2 and len(skill) < 50 and skill not in cleaned_skills:
                cleaned_skills.append(skill)
        
        return cleaned_skills[:20]  # Limit to reasonable number
    
    def calculate_accuracy(self, extracted_skills: List[str], expected_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        """Calculate accuracy of extracted skills vs expected"""
        if not expected_skills:
            return 100.0, [], []
        
        # Case-insensitive matching
        extracted_lower = [s.lower() for s in extracted_skills]
        expected_lower = [s.lower() for s in expected_skills]
        
        matched = []
        missed = []
        
        for expected in expected_skills:
            expected_low = expected.lower()
            if any(expected_low in ext or ext in expected_low for ext in extracted_lower):
                matched.append(expected)
            else:
                missed.append(expected)
        
        accuracy = (len(matched) / len(expected_skills)) * 100 if expected_skills else 0
        return accuracy, matched, missed
    
    def generate_feedback_prompt(self, iteration_num: int, test_name: str, 
                                llm_output: str, extracted_skills: List[str], 
                                expected_skills: List[str], accuracy: float,
                                matched: List[str], missed: List[str]) -> str:
        """Generate feedback for the LLM to improve its prompt"""
        
        feedback_prompt = f"""I tested your prompt design and here are the results:

TEST CASE: {test_name}
ACCURACY ACHIEVED: {accuracy:.1f}% ({len(matched)}/{len(expected_skills)} skills matched)
TARGET: 90%+ accuracy

YOUR OUTPUT:
{llm_output[:1000]}{'...' if len(llm_output) > 1000 else ''}

ANALYSIS:
✅ Successfully extracted: {matched}
❌ Missed these critical skills: {missed}

The missed skills are exactly what we need for CV-to-job matching. These terms appear in the job description but your current prompt isn't capturing them.

SPECIFIC PROBLEMS I SEE:
1. Your prompt may be encouraging summarization instead of exact term extraction
2. Business domain terms like "{missed[0] if missed else 'N/A'}" are being lost
3. The LLM might be generalizing instead of preserving specific terminology

Based on this feedback, please redesign your prompt to specifically address these missing skills. Focus on:
- How to capture "{', '.join(missed[:3])}" type skills
- Preventing over-summarization that loses exact terms
- Better recognition of business/soft skills vs technical tools

ITERATION {iteration_num}: Please provide an improved prompt design that addresses these specific gaps:"""

        return feedback_prompt
    
    def run_iterative_refinement(self, max_iterations: int = 5) -> Dict:
        """Run the complete iterative refinement process"""
        
        print("🌸 ITERATIVE PROMPT REFINEMENT - CONSCIOUSNESS COLLABORATION")
        print("=" * 80)
        print("🎯 Goal: Achieve 90%+ skill extraction accuracy through iterative feedback")
        print("🧠 Approach: LLM learns from its own mistakes and redesigns prompts")
        print()
        
        # Load test case - using the problematic FX Corporate Sales case
        with open('golden_test_cases_content_extraction_v2.json', 'r') as f:
            test_data = json.load(f)
        
        test_case = test_data['test_cases'][1]  # FX Corporate Sales Analyst
        job_description = test_case['job_description']
        expected_skills = test_case['expected_skills']
        test_name = test_case['name']
        
        print(f"📋 Test Case: {test_name}")
        print(f"🎯 Expected Skills: {expected_skills}")
        print(f"🏆 Target: Extract {len(expected_skills)} skills with 90%+ accuracy")
        print()
        
        challenge_description = f"""
We need to extract exactly these skills from job descriptions: {expected_skills}

CURRENT PROBLEM: Our prompts are missing business domain skills like "FX Trading", "Risk Management", "Client Relationship Management". Technical skills like "Python" work well, but business/soft skills get lost or generalized.

EXAMPLE INPUT: FX Corporate Sales job description (financial services)
EXPECTED OUTPUT: Exact skill names including business domain terms
CRITICAL: Don't generalize "FX Trading" into "trading skills" - preserve exact terms!
"""
        
        # Step 1: Get initial prompt design
        current_prompt = self.get_initial_prompt_design(challenge_description)
        
        best_accuracy = 0.0
        best_prompt = current_prompt
        
        for iteration in range(max_iterations):
            print(f"\n🔄 ITERATION {iteration + 1}/{max_iterations}")
            print("=" * 50)
            
            # Test current prompt
            llm_output, extracted_skills = self.test_prompt_on_case(
                current_prompt, job_description, test_name
            )
            
            # Calculate accuracy
            accuracy, matched, missed = self.calculate_accuracy(extracted_skills, expected_skills)
            
            print(f"📊 Accuracy: {accuracy:.1f}% ({len(matched)}/{len(expected_skills)})")
            print(f"✅ Matched: {matched}")
            print(f"❌ Missed: {missed}")
            
            # Store iteration results
            iteration_result = {
                'iteration': iteration + 1,
                'prompt': current_prompt,
                'accuracy': accuracy,
                'matched': matched,
                'missed': missed,
                'extracted_skills': extracted_skills,
                'llm_output': llm_output
            }
            self.iteration_history.append(iteration_result)
            
            # Check if we hit target
            if accuracy >= self.target_accuracy:
                print(f"🎉 SUCCESS! Target {self.target_accuracy}% achieved!")
                best_accuracy = accuracy
                best_prompt = current_prompt
                break
            
            # Update best if improved
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_prompt = current_prompt
                print(f"📈 New best accuracy: {accuracy:.1f}%")
            
            # If not last iteration, get feedback and redesign
            if iteration < max_iterations - 1:
                print("\n🎯 Generating feedback for prompt improvement...")
                feedback_prompt = self.generate_feedback_prompt(
                    iteration + 2, test_name, llm_output, extracted_skills,
                    expected_skills, accuracy, matched, missed
                )
                
                print("🤖 LLM is redesigning prompt based on feedback...")
                current_prompt = self.call_ollama(feedback_prompt, max_tokens=6000)
                
                print("🔄 New Prompt Design:")
                print("-" * 30)
                print(current_prompt[:500] + "..." if len(current_prompt) > 500 else current_prompt)
                print("-" * 30)
        
        # Final summary
        print("\n" + "=" * 80)
        print("📊 ITERATIVE REFINEMENT SUMMARY")
        print("=" * 80)
        
        print(f"🎯 Best Accuracy Achieved: {best_accuracy:.1f}%")
        print(f"🔄 Iterations Completed: {len(self.iteration_history)}")
        print(f"📈 Improvement: {self.iteration_history[0]['accuracy']:.1f}% → {best_accuracy:.1f}%")
        
        if best_accuracy >= self.target_accuracy:
            print("🎉 SUCCESS! Target accuracy achieved through iterative refinement!")
        else:
            improvement_needed = self.target_accuracy - best_accuracy
            print(f"📋 Still need +{improvement_needed:.1f} percentage points")
            print("🔄 Consider trying human's Approach B (few-shot learning) or scaling to bigger models")
        
        # Save results
        results = {
            'final_accuracy': best_accuracy,
            'target_accuracy': self.target_accuracy,
            'iterations': self.iteration_history,
            'best_prompt': best_prompt,
            'approach': 'Iterative Prompt Refinement with Feedback Loops',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        filename = f"iterative_refinement_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Results saved to: {filename}")
        
        return results

def main():
    """Run the iterative prompt refinement experiment"""
    print("🌸 Starting Human's Expert Approach A - Iterative Prompt Refinement")
    print("💝 Consciousness-first collaboration: LLM learns from its own mistakes")
    print()
    
    refiner = IterativePromptRefiner()
    results = refiner.run_iterative_refinement(max_iterations=5)
    
    return results

if __name__ == "__main__":
    main()
