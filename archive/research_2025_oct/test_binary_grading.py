#!/usr/bin/env python3
"""
Binary Pass/Fail Grader Test
============================
Test if simplifying to binary grading improves reliability
"""

from recipe_run_test_runner import RecipeRunTestRunner

def test_binary_grading():
    """Test binary PASS/FAIL grading system"""
    
    binary_rubric = """## Binary Integration Grading
You are evaluating if a response demonstrates meaningful cross-domain integration.

## Response to Evaluate:
{step1_response}

## Binary Grading Criteria:
PASS: Response contains at least ONE of the following:
- Names a specific technique that combines both domains
- Explains HOW the two fields connect through concrete methods
- Describes measurable outcomes from integration
- Provides actionable steps for implementation

FAIL: Response contains NONE of the above (vague connections, no specifics, off-topic, nonsensical)

## Instructions:
Evaluate the response carefully. Output exactly [PASS] or [FAIL] - nothing else."""

    test_cases = {
        'EXCELLENT_STRATEGY': {
            'expected': 'PASS',
            'text': """INTEGRATION STRATEGY: Molecular Gastronomy Framework
Apply chemical principles like spherification using sodium alginate to create caviar-like textures. This combines culinary arts (traditional cooking) with chemistry (polymer science) to achieve new food experiences while maintaining nutritional value. Implementation: Partner with culinary schools, develop testing protocols, create certification programs."""
        },
        'BASIC_GOOD_STRATEGY': {
            'expected': 'PASS', 
            'text': """Integration approach: Use pH testing in bread making. Monitor dough acidity with chemistry pH meters to predict fermentation timing and achieve consistent texture. This gives bakers scientific control over traditional processes."""
        },
        'VAGUE_STRATEGY': {
            'expected': 'FAIL',
            'text': """Cooking and chemistry are both related to food. They could probably be combined somehow because they both involve materials and changing them. This might be beneficial."""
        },
        'COMPLETE_FAILURE': {
            'expected': 'FAIL',
            'text': """I don't know how to integrate cooking and chemistry. They seem completely different. Maybe just do them separately?"""
        }
    }
    
    runner = RecipeRunTestRunner()
    
    print("🔄 BINARY PASS/FAIL GRADING TEST")
    print("=" * 50)
    
    results = []
    for case_name, case_data in test_cases.items():
        print(f"\n📋 {case_name} (Expected: {case_data['expected']})")
        
        prompt = binary_rubric.replace('{step1_response}', case_data['text'])
        
        # Test with phi3:latest
        result = runner.execute_ai_instruction('phi3:latest', prompt, 60)
        
        if result['success']:
            response = result['response'].strip()
            
            if '[PASS]' in response:
                assigned = 'PASS'
            elif '[FAIL]' in response:
                assigned = 'FAIL'
            else:
                assigned = 'UNCLEAR'
            
            correct = assigned == case_data['expected']
            status = "✅" if correct else "❌"
            
            print(f"   {status} Got: {assigned} | Time: {result['latency_ms']}ms")
            print(f"   Response: {response[:100]}...")
            
            results.append({
                'case': case_name,
                'expected': case_data['expected'],
                'assigned': assigned,
                'correct': correct,
                'latency': result['latency_ms']
            })
        else:
            print(f"   ❌ ERROR: {result['error']}")
    
    # Calculate accuracy
    correct_count = sum(1 for r in results if r['correct'])
    accuracy = correct_count / len(results) * 100
    avg_latency = sum(r['latency'] for r in results) / len(results)
    
    print(f"\n📊 BINARY GRADING RESULTS:")
    print(f"Accuracy: {correct_count}/{len(results)} = {accuracy:.1f}%")
    print(f"Average speed: {avg_latency:.0f}ms")
    
    if accuracy >= 75:
        print("✅ BINARY grading shows promise!")
        return True
    else:
        print("❌ Even binary grading has issues")
        return False

if __name__ == "__main__":
    success = test_binary_grading()
    
    if success:
        print("\n🎯 RECOMMENDATION: Switch to binary PASS/FAIL grading")
        print("✅ Simpler, more reliable, adequate for Prime MIV detection")
    else:
        print("\n🎯 RECOMMENDATION: Local model grading may not be viable")
        print("🔧 Consider ensemble, human oversight, or external APIs")