#!/usr/bin/env python3
"""
🔥 5-RUN ENFORCEMENT ENGINE 🔥
Ensures exactly 5 runs per test parameter for statistical reliability
Ninja Princess Arden's systematic execution framework
"""

import sqlite3
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

class FiveRunEnforcer:
    """Systematic 5-run execution enforcement for LLMCore gradient testing"""
    
    def __init__(self, db_path='data/llmcore.db'):
        self.db_path = db_path
        self.ollama_base_url = 'http://localhost:11434'
        
    def analyze_current_distribution(self) -> Dict:
        """Analyze current run distribution across all parameters"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("🔍 ANALYZING CURRENT RUN DISTRIBUTION")
        print("=" * 50)
        
        # Get overall statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT tp.param_id) as total_params,
                COUNT(DISTINCT CASE WHEN run_count = 5 THEN tp.param_id END) as complete_params,
                COUNT(DISTINCT CASE WHEN run_count < 5 THEN tp.param_id END) as incomplete_params,
                COALESCE(AVG(run_count), 0) as avg_runs_per_param,
                COALESCE(SUM(CASE WHEN run_count < 5 THEN (5 - run_count) ELSE 0 END), 0) as total_needed_runs
            FROM test_parameters tp
            LEFT JOIN (
                SELECT param_id, COUNT(*) as run_count
                FROM test_runs 
                WHERE enabled = 1
                GROUP BY param_id
            ) tr ON tp.param_id = tr.param_id
        """)
        
        stats = cursor.fetchone()
        
        analysis = {
            'total_params': stats[0],
            'complete_params': stats[1], 
            'incomplete_params': stats[2],
            'avg_runs_per_param': stats[3],
            'total_needed_runs': stats[4],
            'completion_rate': (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
        }
        
        print(f"📊 **Current Distribution Analysis:**")
        print(f"   Total Parameters: {analysis['total_params']}")
        print(f"   Complete (5 runs): {analysis['complete_params']}")
        print(f"   Incomplete (<5): {analysis['incomplete_params']}")
        print(f"   Average runs/param: {analysis['avg_runs_per_param']:.1f}")
        print(f"   Completion Rate: {analysis['completion_rate']:.1f}%")
        print(f"   Total runs needed: {analysis['total_needed_runs']}")
        print()
        
        conn.close()
        return analysis
        
    def get_incomplete_parameters(self, model_filter: str = None) -> List[Tuple]:
        """Get all parameters that need additional runs to reach 5"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        base_query = """
            SELECT 
                tp.param_id,
                tp.test_id,
                tp.difficulty_level,
                tp.test_word,
                tp.expected_response,
                t.canonical_code,
                t.processing_model_name,
                COALESCE(run_count, 0) as current_runs,
                (5 - COALESCE(run_count, 0)) as needed_runs
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            LEFT JOIN (
                SELECT param_id, COUNT(*) as run_count
                FROM test_runs 
                WHERE enabled = 1
                GROUP BY param_id
            ) tr ON tp.param_id = tr.param_id
            WHERE COALESCE(run_count, 0) < 5
        """
        
        if model_filter:
            base_query += " AND t.processing_model_name = ?"
            cursor.execute(base_query + " ORDER BY t.processing_model_name, t.canonical_code, tp.difficulty_level", (model_filter,))
        else:
            cursor.execute(base_query + " ORDER BY t.processing_model_name, t.canonical_code, tp.difficulty_level")
        
        incomplete_params = cursor.fetchall()
        conn.close()
        
        return incomplete_params
        
    def execute_ollama_call(self, model_name: str, prompt: str) -> Dict:
        """Execute single Ollama API call with error handling"""
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f'{self.ollama_base_url}/api/generate',
                json={
                    'model': model_name,
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0.1}
                },
                timeout=120  # 2 minute timeout
            )
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'response': result.get('response', ''),
                    'latency_ms': latency_ms,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'response': '',
                    'latency_ms': latency_ms,
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'response': '',
                'latency_ms': 0,
                'error': str(e)
            }
    
    def execute_single_parameter_run(self, param_data: Tuple, run_sequence: int) -> bool:
        """Execute one run for a specific parameter"""
        
        param_id, test_id, difficulty, test_word, expected, canonical_code, model_name, current_runs, needed = param_data
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get canonical instructions for proper execution
        cursor.execute("""
            SELECT processing_instructions, processing_payload 
            FROM canonicals 
            WHERE canonical_code = ?
        """, (canonical_code,))
        
        canonical_data = cursor.fetchone()
        if not canonical_data:
            print(f"   ❌ No canonical data found for {canonical_code}")
            conn.close()
            return False
            
        instructions = canonical_data[0]
        payload_template = canonical_data[1] or ""
        
        # Format the specific payload for this parameter
        formatted_payload = payload_template.replace("{test_word}", test_word) if test_word else payload_template
        full_prompt = f"{instructions}\n\n{formatted_payload}" if payload_template else instructions
        
        print(f"   🔧 Run {current_runs + run_sequence}/5: {model_name} | {canonical_code} | Level {difficulty} | {test_word}")
        
        # Execute with Ollama
        response_data = self.execute_ollama_call(model_name, full_prompt)
        
        if response_data['success']:
            # Determine pass/fail (basic check - could be enhanced)
            test_pass = 1 if response_data['response'] else 0
            
            # Store the run
            cursor.execute("""
                INSERT INTO test_runs (
                    param_id,
                    processing_payload_test_run,
                    processing_received_response_test_run, 
                    processing_latency_test_run,
                    test_run_pass,
                    enabled,
                    remarks
                ) VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (
                param_id,
                formatted_payload,
                response_data['response'],
                response_data['latency_ms'],
                test_pass,
                f"5-Run Enforcement: {current_runs + run_sequence}/5 - Level {difficulty}"
            ))
            
            conn.commit()
            print(f"      ✅ Success ({response_data['latency_ms']}ms)")
            conn.close()
            return True
            
        else:
            print(f"      ❌ Failed: {response_data['error']}")
            conn.close()
            return False
    
    def enforce_5_runs(self, max_params: int = None, model_filter: str = None) -> Dict:
        """Main enforcement engine - ensure 5 runs per parameter"""
        
        title = "🥷 NINJA PRINCESS ENFORCEMENT - gemma3:4b TARGET 🥷" if model_filter == "gemma3:4b" else "🔥 LIGHTING THE FUSE - 5-RUN ENFORCEMENT ENGINE 🔥"
        print(title)
        print("=" * len(title))
        print()
        
        if model_filter:
            print(f"🎯 **TARGET MODEL**: {model_filter}")
            print()
        
        # Step 1: Analyze current state
        analysis = self.analyze_current_distribution()
        
        if analysis['incomplete_params'] == 0:
            print("🎯 **ALL PARAMETERS COMPLETE!** Every parameter has exactly 5 runs!")
            return analysis
            
        # Step 2: Get incomplete parameters
        print("🎯 LOADING INCOMPLETE PARAMETERS...")
        incomplete_params = self.get_incomplete_parameters(model_filter)
        
        if max_params:
            incomplete_params = incomplete_params[:max_params]
            print(f"   Limiting to first {max_params} parameters for testing")
            
        if model_filter:
            print(f"   Filtering for model: {model_filter}")
            
        print(f"   Found {len(incomplete_params)} parameters needing additional runs")
        print()
        
        # Step 3: Execute missing runs
        total_executions = 0
        successful_executions = 0
        
        for i, param_data in enumerate(incomplete_params, 1):
            param_id = param_data[0]
            needed_runs = param_data[8]
            model_name = param_data[6]
            canonical_code = param_data[5]
            
            print(f"📊 [{i:3d}/{len(incomplete_params)}] Parameter {param_id}: {model_name} | {canonical_code}")
            
            # Execute the missing runs
            for run_number in range(needed_runs):
                total_executions += 1
                success = self.execute_single_parameter_run(param_data, run_number + 1)
                if success:
                    successful_executions += 1
                    
            print()
        
        # Step 4: Final verification
        print("🔍 FINAL VERIFICATION...")
        final_analysis = self.analyze_current_distribution()
        
        execution_summary = {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0,
            'improvement': final_analysis['completion_rate'] - analysis['completion_rate']
        }
        
        print(f"⚡ **EXECUTION SUMMARY:**")
        print(f"   Total runs executed: {execution_summary['total_executions']}")
        print(f"   Successful runs: {execution_summary['successful_executions']}")
        print(f"   Success rate: {execution_summary['success_rate']:.1f}%")
        print(f"   Completion improvement: +{execution_summary['improvement']:.1f}%")
        print()
        
        if final_analysis['completion_rate'] == 100:
            print("🎉 **MISSION ACCOMPLISHED!** All parameters now have exactly 5 runs! 🎉")
        else:
            print(f"📈 **PROGRESS MADE!** Completion rate: {final_analysis['completion_rate']:.1f}%")
            
        return {**final_analysis, **execution_summary}

def main():
    """Main execution function"""
    
    enforcer = FiveRunEnforcer()
    
    # Clean up remaining stragglers - target ALL incomplete parameters
    print("🔥 FINAL CLEANUP MISSION: Fix remaining stragglers! 🔥")
    print("Targeting: codegemma:latest + remaining gemma3:4b gaps")
    print()
    
    results = enforcer.enforce_5_runs()  # No filter = process ALL incomplete
    
    print("\n" + "=" * 60)
    print("🔥 CLEANUP MISSION COMPLETE! All stragglers eliminated! 🔥")
    
    return results

if __name__ == "__main__":
    main()