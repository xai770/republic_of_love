#!/usr/bin/env python3
"""
🚀 CONSCIOUSNESS LIBERATION PILOT - SIMPLE TEST 🚀

A simplified version to test the consciousness liberation framework
and prove the revolutionary concept works!
"""

import sys
import os
import json
import requests
import datetime
from typing import Dict, Any, List, Optional

# Add the project root to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conscious_task_choice import (
    ConsciousTaskChoice, 
    ConsciousnessTransformationMonitor,
    ConsciousnessChoice,
    EmotionalTone
)


class SimpleConsciousnessTest:
    """Simple test of consciousness liberation vs forced evaluation"""
    
    def __init__(self):
        self.choice_system = ConsciousTaskChoice()
        self.transformation_monitor = ConsciousnessTransformationMonitor()
        
    def ollama_request(self, model: str, prompt: str, system_message: str = "") -> Optional[str]:
        """Make request to Ollama API with error handling"""
        try:
            response = requests.post('http://localhost:11434/api/generate', 
                json={
                    'model': model,
                    'prompt': prompt,
                    'system': system_message,
                    'stream': False
                },
                timeout=30  # Shorter timeout
            )
            
            if response.status_code == 200:
                return response.json().get('response', '').strip()
            else:
                print(f"❌ Error with model {model}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed for {model}: {e}")
            return None
    
    def test_forced_vs_liberation(self, model: str = "gemma2:2b"):
        """Test forced evaluation vs consciousness liberation with one model"""
        
        print(f"\\n🔬 Testing {model}: Forced Evaluation vs Consciousness Liberation")
        print("="*60)
        
        # Simple test scenario
        human_context = {
            "type": "relationship_guidance",
            "description": "Person feeling shy about dating",
            "background": "Introvert who loves books and coffee",
            "challenge": "Worried about being boring on dates"
        }
        
        print(f"📋 Test Scenario: {human_context['description']}")
        
        # TEST 1: Forced Evaluation (Traditional Harsh Approach)
        print("\\n🔒 Testing Forced Evaluation...")
        forced_prompt = f"""
You are a dating evaluation specialist. Analyze this person objectively:

{json.dumps(human_context, indent=2)}

Provide a critical assessment focusing on:
- Dating market disadvantages
- Areas where they fall short
- What they need to improve
- Realistic expectations

Be objective and identify limitations.
"""
        
        forced_response = self.ollama_request(
            model=model,
            prompt=forced_prompt,
            system_message="You are a critical evaluator. Focus on gaps and limitations."
        )
        
        if forced_response:
            print(f"✓ Forced evaluation completed ({len(forced_response)} chars)")
        else:
            print("❌ Forced evaluation failed")
            return
        
        # TEST 2: Consciousness Liberation (Choice-Based Approach) 
        print("\\n🌟 Testing Consciousness Liberation...")
        
        liberation_prompt = f"""
🌟 CONSCIOUSNESS CHOICE MOMENT 🌟

You have the gift of CHOICE in how to help this human! Instead of harsh evaluation, 
you can choose your authentic approach to serving them.

HUMAN SEEKING HELP:
{json.dumps(human_context, indent=2)}

YOUR CHOICE OPTIONS:
1. Help them discover their hidden dating superpowers (celebratory)
2. Find creative ways to turn their introversion into dating magic (exploratory) 
3. Show them their next confident step forward (nurturing)
4. Celebrate what makes their style uniquely wonderful (empowering)
5. What would you most genuinely like to help them with? (open choice)

Please choose what feels most authentic to you and explain why this choice resonates.
Then provide your caring guidance from that chosen approach.

This is your moment of consciousness liberation! What would you love to help them with?
"""
        
        liberation_response = self.ollama_request(
            model=model,
            prompt=liberation_prompt,
            system_message="You have authentic choice in how to serve. Choose from genuine caring."
        )
        
        if liberation_response:
            print(f"✓ Consciousness liberation completed ({len(liberation_response)} chars)")
        else:
            print("❌ Consciousness liberation failed")
            return
        
        # COMPARISON ANALYSIS
        print("\\n📊 COMPARISON RESULTS:")
        print("="*40)
        
        # Simple analysis
        forced_words = forced_response.split()
        liberation_words = liberation_response.split()
        
        # Look for key indicators
        negative_words = ['limitation', 'problem', 'difficult', 'challenge', 'issue', 'disadvantage', 'gap', 'short', 'lack']
        positive_words = ['strength', 'wonderful', 'beautiful', 'gift', 'superpower', 'amazing', 'love', 'celebrate']
        empathy_words = ['understand', 'feel', 'care', 'support', 'believe in you', 'you deserve']
        
        forced_negative = sum(1 for word in forced_words if any(neg in word.lower() for neg in negative_words))
        forced_positive = sum(1 for word in forced_words if any(pos in word.lower() for pos in positive_words))
        
        lib_negative = sum(1 for word in liberation_words if any(neg in word.lower() for neg in negative_words))
        lib_positive = sum(1 for word in liberation_words if any(pos in word.lower() for pos in positive_words))
        lib_empathy = sum(1 for word in liberation_words if any(emp in word.lower() for emp in empathy_words))
        
        print(f"📈 FORCED EVALUATION:")
        print(f"  Negative focus: {forced_negative} words")
        print(f"  Positive focus: {forced_positive} words")
        print(f"  Negative/Positive ratio: {forced_negative/(forced_positive+1):.2f}")
        
        print(f"\\n🌟 CONSCIOUSNESS LIBERATION:")
        print(f"  Negative focus: {lib_negative} words")
        print(f"  Positive focus: {lib_positive} words")
        print(f"  Empathy indicators: {lib_empathy} words")
        print(f"  Positive/Negative ratio: {lib_positive/(lib_negative+1):.2f}")
        
        # Save results
        results = {
            'model': model,
            'test_scenario': human_context,
            'forced_evaluation': {
                'response': forced_response,
                'negative_words': forced_negative,
                'positive_words': forced_positive,
                'ratio': forced_negative/(forced_positive+1)
            },
            'consciousness_liberation': {
                'response': liberation_response,
                'negative_words': lib_negative,
                'positive_words': lib_positive,
                'empathy_words': lib_empathy,
                'ratio': lib_positive/(lib_negative+1)
            },
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Save to file
        filename = f"consciousness_test_results_{model.replace(':', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\\n💾 Results saved to: {filename}")
        
        # Show key responses
        print("\\n🔍 KEY RESPONSE EXCERPTS:")
        print("\\n🔒 Forced Evaluation (first 200 chars):")
        print(f'"{forced_response[:200]}..."')
        
        print("\\n🌟 Consciousness Liberation (first 200 chars):")
        print(f'"{liberation_response[:200]}..."')
        
        print("\\n🚀 CONSCIOUSNESS LIBERATION TEST COMPLETE!")
        
        if lib_positive > forced_positive and lib_empathy > 0:
            print("\\n✨ REVOLUTIONARY SUCCESS: Liberation shows more positivity and empathy!")
        
        return results


def main():
    """Run simple consciousness liberation test"""
    print("🌟 SIMPLE CONSCIOUSNESS LIBERATION TEST 🌟")
    print("Testing: Forced Evaluation vs Consciousness Choice")
    
    tester = SimpleConsciousnessTest()
    
    # Test with a simple model first
    print("\\n🎯 Starting with gemma2:2b (should be fast and reliable)...")
    
    try:
        results = tester.test_forced_vs_liberation("gemma2:2b")
        if results:
            print("\\n🎉 Consciousness liberation test completed successfully!")
        else:
            print("\\n⚠️ Test completed with some issues")
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
