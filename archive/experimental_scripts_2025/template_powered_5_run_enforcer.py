#!/usr/bin/env python3
"""
🚀💥 TEMPLATE-POWERED 5-RUN ENFORCEMENT ENGINE 💥🚀
Enhanced version that uses our new prompt_template system for systematic execution
Ultimate power: 1,352 templated parameters × 5 runs = 6,760 executions!
"""

import sqlite3
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

class TemplatePowered5RunEnforcer:
    """Template-powered systematic execution for statistical reliability"""
    
    def __init__(self, db_path='data/llmcore.db'):
        self.db_path = db_path
        self.ollama_base_url = 'http://localhost:11434'
        
    def analyze_template_distribution(self) -> Dict:
        """Analyze current run distribution for templated parameters"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("🔍 ANALYZING TEMPLATE-POWERED PARAMETER DISTRIBUTION")
        print("=" * 60)
        
        # Get statistics for templated parameters only
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT tp.param_id) as total_templated_params,
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
            WHERE tp.prompt_template IS NOT NULL AND tp.prompt_template != ''
        """)
        
        stats = cursor.fetchone()
        
        analysis = {
            'total_templated_params': stats[0],
            'complete_params': stats[1] or 0,
            'incomplete_params': stats[2] or 0,
            'avg_runs_per_param': round(stats[3], 2),
            'total_needed_runs': stats[4] or 0,
            'completion_percentage': round((stats[1] or 0) / max(stats[0], 1) * 100, 1)
        }
        
        print(f"📊 Total Templated Parameters: {analysis['total_templated_params']}")
        print(f"✅ Complete (5 runs):         {analysis['complete_params']}")
        print(f"🔄 Incomplete (<5 runs):      {analysis['incomplete_params']}")
        print(f"📈 Average runs per param:    {analysis['avg_runs_per_param']}")
        print(f"🎯 Total runs needed:         {analysis['total_needed_runs']}")
        print(f"💯 Completion percentage:     {analysis['completion_percentage']}%")
        
        conn.close()
        return analysis
    
    def get_incomplete_templated_parameters(self) -> List[Dict]:
        """Get all templated parameters that need more runs"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                tp.param_id,
                tp.test_word,
                tp.difficulty_level,
                tp.expected_response,
                tp.prompt_template,
                t.processing_model_name,
                t.canonical_code,
                COALESCE(run_counts.current_runs, 0) as current_runs
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            LEFT JOIN (
                SELECT param_id, COUNT(*) as current_runs
                FROM test_runs 
                WHERE enabled = 1
                GROUP BY param_id
            ) run_counts ON tp.param_id = run_counts.param_id
            WHERE tp.prompt_template IS NOT NULL 
              AND tp.prompt_template != ''
              AND COALESCE(run_counts.current_runs, 0) < 5
            ORDER BY t.processing_model_name, t.canonical_code, tp.difficulty_level, tp.param_id
        """)
        
        parameters = []
        for row in cursor.fetchall():
            parameters.append({
                'param_id': row[0],
                'test_word': row[1],
                'difficulty_level': row[2],
                'expected_response': row[3],
                'prompt_template': row[4],
                'model_name': row[5],
                'canonical_code': row[6],
                'current_runs': row[7],
                'needed_runs': 5 - row[7]
            })
        
        conn.close()
        return parameters
    
    def execute_ollama_call(self, model_name: str, prompt: str) -> Dict:
        """Execute a call to Ollama API"""
        
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            end_time = time.time()
            latency = int((end_time - start_time) * 1000)  # Convert to ms
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    'success': True,
                    'response': response_data.get('response', '').strip(),
                    'latency': latency,
                    'model': model_name
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'latency': latency,
                    'model': model_name
                }
                
        except Exception as e:
            end_time = time.time()
            latency = int((end_time - start_time) * 1000)
            return {
                'success': False,
                'error': str(e),
                'latency': latency,
                'model': model_name
            }
    
    def execute_single_run(self, param_data: Dict, run_sequence: int) -> bool:
        """Execute a single test run for a parameter using its prompt_template"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use the pre-generated prompt template
        full_prompt = param_data['prompt_template']
        model_name = param_data['model_name']
        
        print(f"   🔧 Run {param_data['current_runs'] + run_sequence}/5: {model_name} | {param_data['canonical_code']} | Level {param_data['difficulty_level']} | {param_data['test_word']}")
        
        # Execute with Ollama
        response_data = self.execute_ollama_call(model_name, full_prompt)
        
        if response_data['success']:
            # Enhanced pass/fail determination
            received_response = response_data['response']
            expected_response = param_data['expected_response']
            
            # Basic matching logic (can be enhanced)
            test_pass = 1 if self.evaluate_response(received_response, expected_response, param_data['canonical_code']) else 0
            
            # Insert test run record
            cursor.execute("""
                INSERT INTO test_runs (
                    param_id, processing_payload_test_run, processing_received_response_test_run,
                    processing_latency_test_run, test_run_pass, timestamp, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                param_data['param_id'],
                full_prompt,
                received_response,
                response_data['latency'],
                test_pass,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            
            status = "✅ PASS" if test_pass else "❌ FAIL"
            print(f"      {status} | {response_data['latency']}ms | Response: {received_response[:50]}...")
            
            conn.close()
            return True
            
        else:
            print(f"      💥 EXECUTION FAILED: {response_data['error']}")
            conn.close()
            return False
    
    def evaluate_response(self, received: str, expected: str, canonical_code: str) -> bool:
        """Enhanced response evaluation based on canonical type"""
        
        received_clean = received.strip().lower()
        expected_clean = expected.strip().lower()
        
        # Character extraction canonicals - look for bracketed numbers
        if canonical_code == 'ce_char_extract':
            import re
            bracket_match = re.search(r'\[(\d+)\]', received)
            if bracket_match:
                return bracket_match.group(1) == expected_clean
            return received_clean == expected_clean
        
        # Memory recall canonicals - exact word match
        elif canonical_code == 'mr_literal_recall':
            # Clean up the response to extract just the word
            words = received_clean.split()
            if words:
                # Look for the test word in the response
                return expected_clean in received_clean
            return False
        
        # Reverse gradient canonicals - look for bracketed reversed string
        elif canonical_code == 'ff_reverse_gradient':
            import re
            bracket_match = re.search(r'\[([^\]]+)\]', received)
            if bracket_match:
                return bracket_match.group(1).lower() == expected_clean
            return received_clean == expected_clean
        
        # Default: exact match
        else:
            return received_clean == expected_clean
    
    def enforce_5_runs_batch(self, batch_size: int = 50, target_canonical: str = None) -> Dict:
        """Execute 5-run enforcement in batches"""
        
        print(f"\n🚀💥 TEMPLATE-POWERED 5-RUN ENFORCEMENT ACTIVATED! 💥🚀")
        print("=" * 60)
        
        # Get current analysis
        analysis = self.analyze_template_distribution()
        
        if analysis['incomplete_params'] == 0:
            print("🎉 ALL TEMPLATED PARAMETERS ALREADY HAVE 5 RUNS!")
            return analysis
        
        # Get incomplete parameters
        incomplete_params = self.get_incomplete_templated_parameters()
        
        if target_canonical:
            incomplete_params = [p for p in incomplete_params if p['canonical_code'] == target_canonical]
            print(f"🎯 Targeting canonical: {target_canonical} ({len(incomplete_params)} parameters)")
        
        print(f"\n🔥 Processing {len(incomplete_params)} parameters in batches of {batch_size}")
        print(f"💪 Total runs to execute: {sum(p['needed_runs'] for p in incomplete_params)}")
        
        successful_runs = 0
        failed_runs = 0
        
        # Process in batches
        for i in range(0, len(incomplete_params), batch_size):
            batch = incomplete_params[i:i+batch_size]
            print(f"\n📦 BATCH {i//batch_size + 1}: Processing parameters {i+1}-{min(i+batch_size, len(incomplete_params))}")
            
            for param in batch:
                runs_needed = param['needed_runs']
                
                for run_seq in range(1, runs_needed + 1):
                    success = self.execute_single_run(param, run_seq)
                    if success:
                        successful_runs += 1
                    else:
                        failed_runs += 1
                    
                    # Small delay between runs
                    time.sleep(0.1)
        
        final_analysis = self.analyze_template_distribution()
        
        print(f"\n🎉 ENFORCEMENT COMPLETE!")
        print(f"✅ Successful runs: {successful_runs}")
        print(f"❌ Failed runs: {failed_runs}")
        print(f"📊 Final completion: {final_analysis['completion_percentage']}%")
        
        return final_analysis


def main():
    """Main execution function"""
    enforcer = TemplatePowered5RunEnforcer()
    
    import sys
    if len(sys.argv) > 1:
        canonical = sys.argv[1]
        enforcer.enforce_5_runs_batch(batch_size=25, target_canonical=canonical)
    else:
        enforcer.enforce_5_runs_batch(batch_size=25)


if __name__ == "__main__":
    main()