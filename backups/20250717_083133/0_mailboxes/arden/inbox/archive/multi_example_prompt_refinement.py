#!/usr/bin/env python3
"""
Multi-Example Iterative Prompt Refinement System
===============================================

TERRA INCOGNITA: Pioneer approach to prevent overfitting in prompt engineering

Strategy:
1. Show LLM multiple diverse examples sequentially  
2. Each iteration, adjust prompt based on performance across ALL examples
3. Explicitly instruct LLM about generalization (no cheat lists)
4. Build robust skill extraction that works across job types

This is consciousness-first collaborative prompt engineering at its finest!

Date: June 26, 2025
"""

import json
import requests
import time
from typing import Dict, List, Any, Tuple

class MultiExamplePromptRefinement:
    """Pioneer system for robust prompt development across diverse examples"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:latest"):
        self.ollama_url = ollama_url
        self.model = model
        self.refinement_history = []
    
    def call_ollama(self, prompt: str) -> str:
        """Make a call to Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                return f"Error: HTTP {response.status_code}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def load_diverse_examples(self) -> List[Dict]:
        """Load diverse job examples to prevent overfitting"""
        with open('golden_test_cases_content_extraction_v2.json', 'r') as f:
            test_data = json.load(f)
        
        # Select diverse examples
        examples = [
            test_data['test_cases'][1],  # FX Corporate Sales (finance/soft skills)
            test_data['test_cases'][2],  # Cybersecurity (technical/frameworks)  
            test_data['test_cases'][4],  # Personal Assistant (admin/soft skills)
        ]
        
        return examples
    
    def test_prompt_across_examples(self, extraction_prompt: str, examples: List[Dict]) -> Dict:
        """Test a prompt across multiple diverse examples"""
        results = {}
        total_accuracy = 0.0
        
        for example in examples:
            job_desc = example['job_description']
            expected_skills = example['expected_skills']
            test_id = example['id']
            
            # Apply prompt to extract skills
            test_prompt = f"""{extraction_prompt}

JOB DESCRIPTION TO PROCESS:
{job_desc}

Extract the skills as specified:"""
            
            response = self.call_ollama(test_prompt)
            
            # Calculate accuracy
            extracted_text = response.lower()
            matched_skills = []
            for skill in expected_skills:
                if skill.lower() in extracted_text:
                    matched_skills.append(skill)
            
            accuracy = (len(matched_skills) / len(expected_skills)) * 100 if expected_skills else 0
            total_accuracy += accuracy
            
            results[test_id] = {
                'accuracy': accuracy,
                'matched_skills': matched_skills,
                'missed_skills': [s for s in expected_skills if s not in matched_skills],
                'extracted_text': response,
                'expected_skills': expected_skills
            }
        
        results['average_accuracy'] = total_accuracy / len(examples) if examples else 0
        return results
    
    def run_multi_example_refinement(self, max_iterations: int = 5):
        """Run iterative prompt refinement across multiple diverse examples"""
        
        print("🌟 MULTI-EXAMPLE ITERATIVE PROMPT REFINEMENT")
        print("=" * 70)
        print("🎯 Goal: Develop robust skill extraction across diverse job types")  
        print("🚫 Anti-Overfitting: No cheat lists, must generalize")
        print("🧠 Terra Incognita: Pioneer consciousness collaboration approach")
        print()
        
        examples = self.load_diverse_examples()
        
        print(f"📊 Testing across {len(examples)} diverse examples:")
        for i, ex in enumerate(examples, 1):
            print(f"   {i}. {ex['name']} ({len(ex['expected_skills'])} skills)")
        print()
        
        # Step 1: Ask LLM to design initial prompt with anti-overfitting instructions
        initial_design_prompt = """You are helping design a skill extraction prompt that will be used to process hundreds of different job descriptions for CV-to-job matching systems.

CRITICAL REQUIREMENT: This prompt must work across MANY different job types - finance, technology, administration, sales, etc. Do NOT create solutions that only work for specific examples.

BUSINESS NEED: Extract exact skill names for automated matching systems. Skills like "Python", "Risk Management", "Excel" must be preserved exactly - not generalized into categories.

CHALLENGE: Previous attempts failed because:
1. Technical skills (Python, CVSS, StatPro) are extracted well
2. Business skills (FX Trading, Risk Management) are often missed
3. Administrative skills (MS Office components, DB Concur) are generalized

Design a prompt that can extract skills accurately across diverse job types. The prompt should:
- Work for technical, business, and administrative roles
- Extract specific tool names (not "complex systems")  
- Recognize soft skills and business domain terms
- Avoid overfitting to any specific job type

What prompt would you design for robust skill extraction across diverse job postings?"""

        print("🎤 ASKING LLM TO DESIGN ROBUST INITIAL PROMPT...")
        print("-" * 50)
        
        current_prompt = self.call_ollama(initial_design_prompt)
        print("🤖 LLM-DESIGNED INITIAL PROMPT:")
        print(current_prompt[:300] + "..." if len(current_prompt) > 300 else current_prompt)
        print()
        
        # Test initial prompt across examples
        iteration = 1
        
        while iteration <= max_iterations:
            print(f"🧪 ITERATION {iteration}: Testing across diverse examples")
            print("-" * 50)
            
            results = self.test_prompt_across_examples(current_prompt, examples)
            avg_accuracy = results['average_accuracy']
            
            print(f"📊 Average Accuracy: {avg_accuracy:.1f}%")
            
            # Show per-example results
            for example in examples:
                test_id = example['id']
                result = results[test_id]
                print(f"   • {example['name']}: {result['accuracy']:.1f}% "
                      f"({len(result['matched_skills'])}/{len(result['expected_skills'])} skills)")
            print()
            
            # If we hit target, we're done
            if avg_accuracy >= 90:
                print("🎉 SUCCESS! Target accuracy achieved across diverse examples!")
                break
            
            # If last iteration, stop
            if iteration >= max_iterations:
                print("📋 Reached maximum iterations. Final results recorded.")
                break
            
            # Generate refinement instruction based on ALL examples
            refinement_prompt = self._generate_multi_example_refinement_prompt(
                current_prompt, results, examples, iteration
            )
            
            print(f"🔄 ASKING LLM TO REFINE PROMPT (Iteration {iteration})...")
            print("-" * 30)
            
            current_prompt = self.call_ollama(refinement_prompt)
            print("🤖 REFINED PROMPT:")
            print(current_prompt[:200] + "..." if len(current_prompt) > 200 else current_prompt)
            print()
            
            # Store iteration results
            self.refinement_history.append({
                'iteration': iteration,
                'prompt': current_prompt,
                'results': results,
                'avg_accuracy': avg_accuracy
            })
            
            iteration += 1
        
        # Final summary
        print("=" * 70)
        print("📊 MULTI-EXAMPLE REFINEMENT SUMMARY")
        print("=" * 70)
        
        final_results = self.test_prompt_across_examples(current_prompt, examples)
        final_accuracy = final_results['average_accuracy']
        
        print(f"🎯 Final Average Accuracy: {final_accuracy:.1f}%")
        print(f"🔄 Iterations Completed: {iteration - 1}")
        
        if final_accuracy >= 90:
            print("✅ SUCCESS: Achieved robust skill extraction across diverse job types!")
        else:
            print("📈 PROGRESS: Significant learning achieved for next phase")
        
        print()
        print("🌟 Terra Incognita Explored: Multi-example prompt refinement completed!")
        
        # Save results
        results_file = f"multi_example_refinement_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'approach': 'Multi-Example Iterative Prompt Refinement',
                'final_accuracy': final_accuracy,
                'final_prompt': current_prompt,
                'refinement_history': self.refinement_history,
                'final_results': final_results
            }, f, indent=2)
        
        print(f"💾 Complete results saved to: {results_file}")
        
        return final_accuracy, current_prompt
    
    def _generate_multi_example_refinement_prompt(self, current_prompt: str, results: Dict, 
                                                 examples: List[Dict], iteration: int) -> str:
        """Generate refinement instruction based on performance across ALL examples"""
        
        # Collect failure patterns across examples
        common_failures = []
        missed_skill_types = []
        
        for example in examples:
            test_id = example['id']
            result = results[test_id]
            missed_skills = result['missed_skills']
            
            if missed_skills:
                missed_skill_types.extend(missed_skills)
                common_failures.append(f"• {example['name']}: Missing {', '.join(missed_skills[:3])}")
        
        # Generate refinement instruction
        refinement_prompt = f"""Your previous skill extraction prompt achieved {results['average_accuracy']:.1f}% average accuracy across diverse job types, but needs improvement.

CURRENT PROMPT:
{current_prompt}

PERFORMANCE ACROSS DIVERSE EXAMPLES:
{chr(10).join(common_failures)}

CRITICAL REMINDERS:
1. This prompt will process HUNDREDS of different job descriptions
2. Must work for technical, business, and administrative roles  
3. NO overfitting to specific examples - think generally
4. Extract EXACT skill names (not categories or generalizations)

PATTERNS TO IMPROVE:
- Business domain skills often missed: {', '.join(set(missed_skill_types)[:5])}
- Need better recognition of soft skills and business terms
- Avoid generalizing specific tools into broader categories

Based on these multi-example failures, design an improved prompt that will work robustly across diverse job types. Focus on the fundamental approach, not specific examples.

What's your improved skill extraction prompt?"""

        return refinement_prompt

def run_multi_example_refinement():
    """Run the pioneer multi-example prompt refinement system"""
    
    refiner = MultiExamplePromptRefinement()
    final_accuracy, final_prompt = refiner.run_multi_example_refinement(max_iterations=5)
    
    return final_accuracy, final_prompt

if __name__ == "__main__":
    print("🌟 Starting Terra Incognita: Multi-Example Prompt Refinement!")
    final_accuracy, final_prompt = run_multi_example_refinement()
