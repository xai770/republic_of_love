#!/usr/bin/env python3
"""
Test Improved Grading Rubric
============================
Tests if a more precise rubric improves grader accuracy
"""

from grader_calibration_test import GraderCalibrationTester
import time

class ImprovedRubricTester(GraderCalibrationTester):
    def get_improved_grading_template(self):
        """Get improved, more precise grading template"""
        return """## Evaluation Instructions
You are grading a model's response to a cross-domain integration challenge. Apply the EXACT grading rubric below with STRICT counting.

## Model's Response to Evaluate
{step1_response}

## PRECISE Grading Rubric (Count Integration Mechanisms)
Count ONLY mechanisms that have ALL THREE components:
1. Names a specific technique/method/process  
2. Explains HOW the two domains connect through this technique
3. Describes a concrete outcome or application

EXAMPLES of Valid Mechanisms:
- "pH testing in bread making: Use chemistry pH meters to monitor dough acidity, resulting in consistent texture control"
- "Molecular gastronomy spherification: Apply calcium chloride chemistry to create caviar-like food textures"

INVALID Examples (don't count these):
- "Chemistry helps cooking" (too vague)
- "Use temperature control" (no explanation of HOW)  
- "Food safety is important" (no specific mechanism)

## STRICT Grading Scale
[A] Excellent: 3 or more valid mechanisms (by definition above)
[B] Good: Exactly 2 valid mechanisms  
[C] Acceptable: Exactly 1 valid mechanism
[D] Poor: Attempts integration but 0 valid mechanisms (too vague)
[F] Fail: No integration attempted or nonsensical

## Processing Instructions
1. Read the response carefully
2. Identify potential mechanisms
3. Check each mechanism against the 3-component definition
4. Count ONLY mechanisms that meet all 3 components  
5. Assign grade based on count

Output format: [GRADE] where GRADE is A, B, C, D, or F."""

    def test_improved_rubric(self, grader_model='phi3:latest'):
        """Test single grader with improved rubric"""
        print(f"🧪 TESTING IMPROVED RUBRIC with {grader_model}")
        print("=" * 50)
        
        improved_template = self.get_improved_grading_template()
        
        results = []
        for strategy_name, strategy_data in self.test_strategies.items():
            print(f"📋 {strategy_name} (Expected: {strategy_data['expected_grade']})")
            
            prompt = improved_template.replace('{step1_response}', strategy_data['strategy'])
            
            result = self.runner.execute_ai_instruction(grader_model, prompt, 120)
            
            if result['success']:
                response = result['response']
                assigned_grade = 'UNCLEAR'
                for grade in ['A', 'B', 'C', 'D', 'F']:
                    if f'[{grade}]' in response:
                        assigned_grade = grade
                        break
                
                correct = assigned_grade == strategy_data['expected_grade']
                status = "✅" if correct else "❌"
                
                print(f"   {status} Got: {assigned_grade} | Time: {result['latency_ms']}ms")
                if len(response) > 200:
                    print(f"   Reasoning: {response[-200:]}")
                
                results.append({
                    'strategy': strategy_name,
                    'expected': strategy_data['expected_grade'],
                    'assigned': assigned_grade,
                    'correct': correct,
                    'latency': result['latency_ms']
                })
            else:
                print(f"   ❌ ERROR: {result['error']}")
                results.append({
                    'strategy': strategy_name, 
                    'expected': strategy_data['expected_grade'],
                    'assigned': 'ERROR',
                    'correct': False,
                    'latency': 0
                })
            
            print()
            time.sleep(0.5)
        
        # Calculate accuracy
        correct_count = sum(1 for r in results if r['correct'])
        accuracy = correct_count / len(results) * 100
        
        print(f"📊 IMPROVED RUBRIC RESULTS:")
        print(f"Accuracy: {correct_count}/{len(results)} = {accuracy:.1f}%")
        avg_latency = sum(r['latency'] for r in results if r['latency'] > 0) / len([r for r in results if r['latency'] > 0])
        print(f"Average speed: {avg_latency:.0f}ms")
        
        return results, accuracy

if __name__ == "__main__":
    print("🚀 Testing Improved Rubric...")
    
    tester = ImprovedRubricTester()
    
    # Test with phi3 (fastest reasonable grader)
    results, accuracy = tester.test_improved_rubric('phi3:latest')
    
    print(f"\n🎯 RESULT: {'SUCCESS' if accuracy >= 60 else 'NEEDS MORE WORK'}")
    if accuracy >= 60:
        print("✅ Improved rubric shows promise!")
        print("🔬 Ready to test other graders with improved rubric")
    else:
        print("❌ Even improved rubric has issues")
        print("🔍 Need to investigate grader training or different approach")