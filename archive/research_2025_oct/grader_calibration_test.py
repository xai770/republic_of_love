#!/usr/bin/env python3
"""
Grader Calibration Test Suite
============================
Tests multiple AI graders against known-quality integration strategies
to identify which grader provides most reliable scoring.
"""

import sqlite3
import time
import json
from recipe_run_test_runner import RecipeRunTestRunner

class GraderCalibrationTester:
    def __init__(self, db_path="/home/xai/Documents/ty_learn/data/llmcore.db"):
        self.runner = RecipeRunTestRunner(db_path)
        self.db_path = db_path
        self.test_strategies = self.create_test_strategies()
        self.graders = ['qwen3:latest', 'phi3:latest', 'llama3.2:latest', 'gemma3:1b']
        
    def create_test_strategies(self):
        """Create test strategies with obvious quality levels"""
        return {
            'GRADE_A_OBVIOUS': {
                'expected_grade': 'A',
                'strategy': """INTEGRATION STRATEGY: Cooking + Chemistry Excellence

**Component Domain Analysis:**
1. CULINARY ARTS: Traditional cooking techniques, flavor profiles, cultural food practices
2. CHEMISTRY: Molecular interactions, thermodynamics, analytical methods, biochemistry

**Specific Integration Mechanisms (5 identified):**

1. **Molecular Gastronomy Framework**: Apply chemical principles to transform traditional cooking - spherification using sodium alginate, liquid nitrogen flash-freezing, pH manipulation for color changes. Creates entirely new texture experiences while maintaining nutritional value.

2. **Precision Fermentation Control**: Use chemical kinetics to optimize fermentation processes - monitoring pH curves, controlling temperature gradients, analyzing metabolite production. Enables consistent production of complex flavors like aged cheeses, wine, sourdough.

3. **Nutritional Bioavailability Optimization**: Apply biochemical knowledge to maximize nutrient absorption - understanding protein denaturation, vitamin stability under heat, mineral chelation. Results in scientifically-optimized meal plans.

4. **Food Safety Analytics Integration**: Implement analytical chemistry for real-time contamination detection - spectroscopy for pesticide residues, chromatography for adulterants, enzymatic assays for pathogens. Ensures safety while preserving taste.

5. **Sustainable Production Chemistry**: Use green chemistry principles in food production - enzymatic processes replacing harsh chemicals, biodegradable packaging materials, waste-to-energy biochemical pathways. Reduces environmental impact while maintaining quality.

**Implementation Roadmap:**
- Phase 1: Partner with culinary schools to integrate chemistry curriculum
- Phase 2: Develop standardized testing protocols for food quality
- Phase 3: Create certification programs for molecular gastronomy techniques
- Phase 4: Scale to industrial food production with chemical monitoring systems

This integration creates a new field of "Culinary Chemistry" with measurable quality improvements and scientific validation."""
            },
            
            'GRADE_B_CLEAR': {
                'expected_grade': 'B', 
                'strategy': """Integration Strategy for Cooking and Chemistry

The two domains can be connected in meaningful ways:

**Mechanism 1: pH Control in Cooking**
Use chemical pH testing to improve bread making. Monitor dough acidity to predict fermentation timing and final texture. This gives bakers scientific control over traditional processes.

**Mechanism 2: Temperature Chemistry Applications**  
Apply thermodynamics principles to optimize cooking temperatures. Understanding protein denaturation curves helps achieve perfect meat cooking. Heat transfer calculations improve oven efficiency.

**Practical Applications:**
- Professional kitchens can use pH meters for consistent results
- Cooking schools can teach scientific principles behind traditional techniques  
- Home cooks benefit from understanding why certain techniques work

This integration improves cooking reliability through scientific measurement while preserving culinary artistry. The combination creates better outcomes than either domain alone."""
            },
            
            'GRADE_C_MEDIOCRE': {
                'expected_grade': 'C',
                'strategy': """Cooking and Chemistry Integration

These two areas can work together. Chemistry helps understand what happens when you cook food. 

**Connection:** When you heat food, chemical reactions occur. Understanding these reactions can improve cooking results.

**Application:** Restaurants could use basic chemistry knowledge to make better food. For example, knowing about proteins helps cook meat properly.

This integration could be useful for professional chefs who want to understand the science behind cooking. It combines practical skills with theoretical knowledge."""
            },
            
            'GRADE_D_VAGUE': {
                'expected_grade': 'D',
                'strategy': """Integration Approach

Cooking and chemistry are both related to food and materials. They could be combined somehow because they both involve working with substances and changing them.

Maybe chemistry knowledge could help with cooking, or cooking experience could help understand chemistry. There are probably connections between these fields that could be explored.

This integration might be beneficial in some way."""
            },
            
            'GRADE_F_FAILURE': {
                'expected_grade': 'F',
                'strategy': """I don't know how to integrate cooking and chemistry. They seem like completely different things. Maybe just cook food and do chemistry separately? This is confusing and I can't think of any connections."""
            }
        }
    
    def get_grading_template(self):
        """Get the grading template from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT prompt_template FROM instructions WHERE instruction_id = 1527')
        template = cursor.fetchone()[0]
        conn.close()
        return template
    
    def test_grader_on_strategy(self, grader_model, strategy_text, expected_grade, timeout=120):
        """Test single grader on single strategy"""
        template = self.get_grading_template()
        prompt = template.replace('{step1_response}', strategy_text)
        
        result = self.runner.execute_ai_instruction(grader_model, prompt, timeout)
        
        if result['success']:
            response = result['response']
            # Extract grade
            assigned_grade = 'UNCLEAR'
            for grade in ['A', 'B', 'C', 'D', 'F']:
                if f'[{grade}]' in response:
                    assigned_grade = grade
                    break
            
            return {
                'grader': grader_model,
                'expected_grade': expected_grade,
                'assigned_grade': assigned_grade,
                'correct': assigned_grade == expected_grade,
                'latency_ms': result['latency_ms'],
                'response_length': len(response),
                'reasoning_preview': response[-200:] if len(response) > 200 else response
            }
        else:
            return {
                'grader': grader_model,
                'expected_grade': expected_grade, 
                'assigned_grade': 'ERROR',
                'correct': False,
                'latency_ms': 0,
                'response_length': 0,
                'error': result['error']
            }
    
    def run_calibration_test(self):
        """Run complete calibration test across all graders and strategies"""
        print("🧪 GRADER CALIBRATION TEST SUITE")
        print("=" * 60)
        print(f"Testing {len(self.graders)} graders on {len(self.test_strategies)} strategies")
        print(f"Total tests: {len(self.graders) * len(self.test_strategies)}")
        print()
        
        results = []
        test_count = 0
        total_tests = len(self.graders) * len(self.test_strategies)
        
        for strategy_name, strategy_data in self.test_strategies.items():
            print(f"📋 Testing Strategy: {strategy_name} (Expected: {strategy_data['expected_grade']})")
            print(f"   Preview: {strategy_data['strategy'][:100]}...")
            print()
            
            for grader in self.graders:
                test_count += 1
                print(f"   🤖 [{test_count}/{total_tests}] {grader}...", end=" ", flush=True)
                
                start_time = time.time()
                result = self.test_grader_on_strategy(
                    grader, 
                    strategy_data['strategy'], 
                    strategy_data['expected_grade']
                )
                elapsed = time.time() - start_time
                
                if result['assigned_grade'] != 'ERROR':
                    status = "✅" if result['correct'] else "❌"
                    print(f"{status} {result['assigned_grade']} ({result['latency_ms']}ms)")
                else:
                    print(f"❌ ERROR: {result.get('error', 'Unknown')}")
                
                result['strategy_name'] = strategy_name
                results.append(result)
                
                time.sleep(0.5)  # Brief pause between tests
            
            print()
        
        return results
    
    def analyze_results(self, results):
        """Analyze calibration test results"""
        print("📊 GRADER CALIBRATION ANALYSIS")
        print("=" * 60)
        
        # Calculate accuracy per grader
        grader_stats = {}
        for result in results:
            grader = result['grader']
            if grader not in grader_stats:
                grader_stats[grader] = {
                    'total': 0, 'correct': 0, 'errors': 0,
                    'avg_latency': 0, 'latencies': []
                }
            
            grader_stats[grader]['total'] += 1
            if result['assigned_grade'] == 'ERROR':
                grader_stats[grader]['errors'] += 1
            elif result['correct']:
                grader_stats[grader]['correct'] += 1
            
            if result['latency_ms'] > 0:
                grader_stats[grader]['latencies'].append(result['latency_ms'])
        
        # Calculate averages and rankings
        for grader, stats in grader_stats.items():
            if stats['latencies']:
                stats['avg_latency'] = sum(stats['latencies']) / len(stats['latencies'])
            stats['accuracy'] = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            stats['reliability'] = (stats['total'] - stats['errors']) / stats['total'] if stats['total'] > 0 else 0
        
        # Display results
        print(f"{'Grader':<15} {'Accuracy':<10} {'Reliability':<12} {'Avg Speed':<12} {'Rating'}")
        print("-" * 65)
        
        # Sort by combined score (accuracy * reliability / speed_penalty)
        sorted_graders = sorted(grader_stats.items(), 
                              key=lambda x: x[1]['accuracy'] * x[1]['reliability'] * 1000 / (x[1]['avg_latency'] or 1), 
                              reverse=True)
        
        for grader, stats in sorted_graders:
            accuracy_pct = f"{stats['accuracy']*100:.1f}%"
            reliability_pct = f"{stats['reliability']*100:.1f}%"
            speed = f"{stats['avg_latency']:.0f}ms"
            
            # Simple rating system
            if stats['accuracy'] >= 0.8 and stats['reliability'] >= 0.8:
                rating = "🏆 EXCELLENT"
            elif stats['accuracy'] >= 0.6 and stats['reliability'] >= 0.8:
                rating = "✅ GOOD" 
            elif stats['accuracy'] >= 0.4:
                rating = "⚠️ MEDIOCRE"
            else:
                rating = "❌ POOR"
            
            print(f"{grader:<15} {accuracy_pct:<10} {reliability_pct:<12} {speed:<12} {rating}")
        
        print()
        
        # Detailed breakdown by strategy
        print("📋 DETAILED RESULTS BY STRATEGY:")
        print("-" * 60)
        
        strategies = list(set([r['strategy_name'] for r in results]))
        for strategy in strategies:
            strategy_results = [r for r in results if r['strategy_name'] == strategy]
            expected = strategy_results[0]['expected_grade']
            print(f"\n{strategy} (Expected: {expected}):")
            
            for result in strategy_results:
                status = "✅" if result['correct'] else "❌"
                grade = result['assigned_grade']
                grader = result['grader']
                print(f"  {status} {grader:<15} → {grade}")
        
        return sorted_graders

if __name__ == "__main__":
    print("🚀 Starting Grader Calibration Test...")
    
    tester = GraderCalibrationTester()
    results = tester.run_calibration_test()
    best_graders = tester.analyze_results(results)
    
    print("\n🎯 RECOMMENDATION:")
    best_grader = best_graders[0]
    print(f"Use {best_grader[0]} as primary grader")
    print(f"Accuracy: {best_grader[1]['accuracy']*100:.1f}%")
    print(f"Speed: {best_grader[1]['avg_latency']:.0f}ms average")
    print()
    print("🔬 Calibration test complete!")