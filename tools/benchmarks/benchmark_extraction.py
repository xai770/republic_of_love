#!/usr/bin/env python3
"""
Extraction Model Benchmark

Tests multiple AI models on job description extraction to find the best model
that produces clean, non-degenerate summaries WITH quality grading.

Two-phase testing:
1. CLEANLINESS: Check for degenerate output (loops, repetition)
2. QUALITY: Grade extraction completeness and accuracy using AI teacher

Usage:
    python3 tools/benchmark_extraction.py --posting-ids 7694,8062,5103
    python3 tools/benchmark_extraction.py --problematic 5  # Auto-pick 5 failed extractions
    python3 tools/benchmark_extraction.py --problematic 10 --with-grading  # Include quality grading

Author: Arden, Sandy & xai
Date: December 1, 2025 (Updated Dec 2, 2025 - added quality grading)
"""

import argparse
import json
import sys
import os
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import requests

load_dotenv()

# Models to benchmark - mix of sizes
MODELS_TO_TEST = [
    'llama3.2:latest',# Current extraction model (baseline)
    'qwen2.5:7b',     # Strong performer
    'mistral:latest', # Good all-rounder
    'phi4-mini:latest', # Small but capable
    'gemma3:4b',      # Larger gemma
]

# Model used to grade quality (teacher model)
GRADER_MODEL = 'qwen2.5:7b'

# Extraction prompt template
EXTRACTION_PROMPT = """Create a concise job description summary for this job posting:

{job_description}

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do not add information."""

# Quality grading prompt (used by teacher model)
GRADING_PROMPT = """You are grading a job description summary for accuracy and completeness.

## ORIGINAL JOB POSTING:
{original_posting}

## STUDENT'S SUMMARY:
{extraction}

## GRADING CRITERIA:

1. **ROLE_TITLE (25 points)**: Is the job title correct and complete?
   - 25: Exact match or accurate representation
   - 15: Close but missing qualifier (e.g., "Engineer" vs "Senior Engineer")
   - 5: Wrong title entirely
   - 0: Missing

2. **COMPLETENESS (40 points)**: Are key responsibilities and requirements included?
   - 40: Captures 80%+ of important details
   - 30: Captures 60-80% of details
   - 20: Captures 40-60% of details
   - 10: Captures <40% of details
   - 0: Major sections missing

3. **ACCURACY (25 points)**: Is the information correct? No hallucinations?
   - 25: All information matches original
   - 15: Minor inaccuracies
   - 5: Significant errors or hallucinations
   - 0: Mostly wrong

4. **FORMATTING (10 points)**: Does it follow the template?
   - 10: Perfect format
   - 5: Minor deviations
   - 0: Wrong format

## YOUR RESPONSE:
Provide scores on separate lines, then a brief explanation:

ROLE_TITLE: [0-25]
COMPLETENESS: [0-40]
ACCURACY: [0-25]
FORMATTING: [0-10]
OVERALL: [sum of above, 0-100]
EXPLANATION: [1-2 sentences about main issues if any]"""


class ExtractionBenchmark:
    """Benchmark runner for extraction models"""
    
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        self.results = {}
        
    def get_problematic_postings(self, limit: int = 5) -> List[Dict]:
        """Get postings that failed extraction (went to session_d)"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT 
                p.posting_id,
                p.job_title,
                p.job_description,
                LENGTH(p.job_description) as desc_length
            FROM postings p
            WHERE p.posting_id IN (
                SELECT DISTINCT i.posting_id
                FROM interactions i
                JOIN conversations c ON i.conversation_id = c.conversation_id
                WHERE c.conversation_name = 'session_d_qwen25_improve'
                AND i.status = 'completed'
            )
            AND LENGTH(p.job_description) < 20000  -- Skip massive ones
            ORDER BY RANDOM()
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()
    
    def get_postings_by_ids(self, posting_ids: List[int]) -> List[Dict]:
        """Get specific postings by ID"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT posting_id, job_title, job_description, 
                   LENGTH(job_description) as desc_length
            FROM postings
            WHERE posting_id = ANY(%s)
        """, (posting_ids,))
        return cursor.fetchall()
    
    def call_ollama(self, model: str, prompt: str, timeout: int = 120) -> Dict:
        """Call Ollama API and return response with timing"""
        start = time.time()
        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'num_predict': 2000,  # Limit output length
                        'temperature': 0.3,   # Lower for consistency
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            latency_ms = (time.time() - start) * 1000
            return {
                'success': True,
                'response': data.get('response', ''),
                'latency_ms': latency_ms,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'response': '',
                'latency_ms': (time.time() - start) * 1000,
                'error': str(e)
            }
    
    def check_degeneration(self, text: str) -> Dict[str, Any]:
        """Check for degenerate output patterns"""
        issues = []
        
        # Check for repetition (same line repeated 3+ times)
        lines = text.split('\n')
        line_counts = {}
        for line in lines:
            line = line.strip()
            if len(line) > 10:  # Skip short lines
                line_counts[line] = line_counts.get(line, 0) + 1
        
        max_repeat = max(line_counts.values()) if line_counts else 0
        if max_repeat >= 3:
            issues.append(f"Repetition detected: {max_repeat} repeats of same line")
        
        # Check for looping patterns (substring repeated)
        if len(text) > 500:
            # Look for repeated chunks
            chunk_size = 100
            for i in range(0, len(text) - chunk_size * 2, chunk_size):
                chunk = text[i:i+chunk_size]
                if text.count(chunk) >= 3:
                    issues.append(f"Looping pattern detected")
                    break
        
        # Check output length vs input - suspicious if output >> expected
        if len(text) > 5000:
            issues.append(f"Output too long: {len(text)} chars")
        
        # Check for required sections
        has_role = '**Role:**' in text or 'Role:' in text
        has_responsibilities = 'Responsibilities' in text or 'responsibilities' in text
        has_requirements = 'Requirements' in text or 'requirements' in text
        
        if not has_role:
            issues.append("Missing Role section")
        if not has_responsibilities:
            issues.append("Missing Responsibilities section")
        if not has_requirements:
            issues.append("Missing Requirements section")
        
        return {
            'is_degenerate': len(issues) > 0 and max_repeat >= 3,  # Only degenerate if repetition
            'issues': issues,
            'max_line_repeat': max_repeat,
            'output_length': len(text)
        }
    
    def grade_quality(self, original_posting: str, extraction: str) -> Dict[str, Any]:
        """
        Grade extraction quality using AI teacher model.
        
        Returns dict with:
        - role_title: 0-25
        - completeness: 0-40
        - accuracy: 0-25
        - formatting: 0-10
        - overall: 0-100
        - explanation: str
        """
        prompt = GRADING_PROMPT.format(
            original_posting=original_posting[:8000],  # Truncate if needed
            extraction=extraction
        )
        
        result = self.call_ollama(GRADER_MODEL, prompt, timeout=60)
        
        if not result['success']:
            return {
                'role_title': 0,
                'completeness': 0,
                'accuracy': 0,
                'formatting': 0,
                'overall': 0,
                'explanation': f"Grading failed: {result['error']}",
                'grading_error': True
            }
        
        # Parse the grading response
        response = result['response']
        scores = {
            'role_title': 0,
            'completeness': 0,
            'accuracy': 0,
            'formatting': 0,
            'overall': 0,
            'explanation': '',
            'grading_error': False
        }
        
        try:
            # Extract scores using regex
            role_match = re.search(r'ROLE_TITLE:\s*(\d+)', response)
            comp_match = re.search(r'COMPLETENESS:\s*(\d+)', response)
            acc_match = re.search(r'ACCURACY:\s*(\d+)', response)
            fmt_match = re.search(r'FORMATTING:\s*(\d+)', response)
            overall_match = re.search(r'OVERALL:\s*(\d+)', response)
            expl_match = re.search(r'EXPLANATION:\s*(.+?)(?:\n|$)', response, re.DOTALL)
            
            if role_match:
                scores['role_title'] = min(25, int(role_match.group(1)))
            if comp_match:
                scores['completeness'] = min(40, int(comp_match.group(1)))
            if acc_match:
                scores['accuracy'] = min(25, int(acc_match.group(1)))
            if fmt_match:
                scores['formatting'] = min(10, int(fmt_match.group(1)))
            if overall_match:
                scores['overall'] = min(100, int(overall_match.group(1)))
            else:
                # Calculate overall if not provided
                scores['overall'] = (
                    scores['role_title'] + 
                    scores['completeness'] + 
                    scores['accuracy'] + 
                    scores['formatting']
                )
            if expl_match:
                scores['explanation'] = expl_match.group(1).strip()[:200]
                
        except Exception as e:
            scores['explanation'] = f"Parse error: {e}"
            scores['grading_error'] = True
        
        return scores
    
    def run_benchmark(self, postings: List[Dict], models: List[str] = None, with_grading: bool = False) -> Dict:
        """Run benchmark on all models and postings"""
        if models is None:
            models = MODELS_TO_TEST
        
        print(f"\n🏁 EXTRACTION MODEL BENCHMARK")
        print(f"=" * 60)
        print(f"Postings: {len(postings)}")
        print(f"Models: {len(models)}")
        print(f"Quality Grading: {'✅ Enabled' if with_grading else '❌ Disabled'}")
        if with_grading:
            print(f"Grader Model: {GRADER_MODEL}")
        print(f"=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'postings': len(postings),
            'with_grading': with_grading,
            'grader_model': GRADER_MODEL if with_grading else None,
            'models': {},
            'posting_details': []
        }
        
        # Store posting info
        for p in postings:
            results['posting_details'].append({
                'posting_id': p['posting_id'],
                'job_title': p['job_title'],
                'desc_length': p['desc_length']
            })
        
        for model in models:
            print(f"\n📦 Testing: {model}")
            print("-" * 40)
            
            model_results = {
                'tests': [],
                'total_latency_ms': 0,
                'success_count': 0,
                'degenerate_count': 0,
                'clean_count': 0,
                'total_quality_score': 0,
                'quality_count': 0
            }
            
            for posting in postings:
                posting_id = posting['posting_id']
                job_desc = posting['job_description']
                
                # Truncate very long descriptions
                if len(job_desc) > 15000:
                    job_desc = job_desc[:15000] + "\n\n[... truncated ...]"
                
                prompt = EXTRACTION_PROMPT.format(job_description=job_desc)
                
                print(f"  Posting {posting_id} ({posting['desc_length']} chars)...", end=' ', flush=True)
                
                result = self.call_ollama(model, prompt)
                
                if result['success']:
                    degen_check = self.check_degeneration(result['response'])
                    
                    test_result = {
                        'posting_id': posting_id,
                        'success': True,
                        'latency_ms': result['latency_ms'],
                        'output_length': len(result['response']),
                        'is_degenerate': degen_check['is_degenerate'],
                        'issues': degen_check['issues'],
                        'max_repeat': degen_check['max_line_repeat'],
                        'response_preview': result['response'][:500],
                        'full_response': result['response']
                    }
                    
                    model_results['success_count'] += 1
                    model_results['total_latency_ms'] += result['latency_ms']
                    
                    if degen_check['is_degenerate']:
                        model_results['degenerate_count'] += 1
                        print(f"⚠️  DEGEN ({result['latency_ms']:.0f}ms)", end='')
                    else:
                        model_results['clean_count'] += 1
                        print(f"✅ Clean ({result['latency_ms']:.0f}ms)", end='')
                    
                    # Quality grading (if enabled and not degenerate)
                    if with_grading and not degen_check['is_degenerate']:
                        print(" → grading...", end='', flush=True)
                        quality = self.grade_quality(job_desc, result['response'])
                        test_result['quality'] = quality
                        model_results['total_quality_score'] += quality['overall']
                        model_results['quality_count'] += 1
                        print(f" Q:{quality['overall']}/100")
                    else:
                        print()
                else:
                    test_result = {
                        'posting_id': posting_id,
                        'success': False,
                        'error': result['error'],
                        'latency_ms': result['latency_ms']
                    }
                    print(f"❌ Error: {result['error'][:50]}")
                
                model_results['tests'].append(test_result)
            
            # Calculate averages
            if model_results['success_count'] > 0:
                model_results['avg_latency_ms'] = model_results['total_latency_ms'] / model_results['success_count']
            else:
                model_results['avg_latency_ms'] = 0
            
            model_results['clean_rate'] = model_results['clean_count'] / len(postings) * 100
            
            if model_results['quality_count'] > 0:
                model_results['avg_quality'] = model_results['total_quality_score'] / model_results['quality_count']
            else:
                model_results['avg_quality'] = 0
            
            # Calculate combined score
            # Formula: (clean_rate * 0.2) + (quality * 0.6) + (speed_score * 0.2)
            # Speed score: 100 - (latency_seconds * 5), capped at 0-100
            speed_score = max(0, min(100, 100 - (model_results['avg_latency_ms'] / 1000 * 5)))
            if with_grading:
                model_results['combined_score'] = (
                    model_results['clean_rate'] * 0.2 +
                    model_results['avg_quality'] * 0.6 +
                    speed_score * 0.2
                )
            else:
                # Without grading, weight clean rate and speed equally
                model_results['combined_score'] = (
                    model_results['clean_rate'] * 0.6 +
                    speed_score * 0.4
                )
            
            results['models'][model] = model_results
            
            summary = f"  Summary: {model_results['clean_count']}/{len(postings)} clean"
            if with_grading and model_results['quality_count'] > 0:
                summary += f", avg quality {model_results['avg_quality']:.0f}/100"
            summary += f", avg {model_results['avg_latency_ms']:.0f}ms"
            print(summary)
        
        return results
    
    def generate_report(self, results: Dict, output_file: str):
        """Generate markdown report"""
        with_grading = results.get('with_grading', False)
        
        with open(output_file, 'w') as f:
            f.write("# Extraction Model Benchmark Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Postings Tested:** {results['postings']}\n")
            f.write(f"**Models Tested:** {len(results['models'])}\n")
            f.write(f"**Quality Grading:** {'✅ Enabled' if with_grading else '❌ Disabled'}\n")
            if with_grading:
                f.write(f"**Grader Model:** {results.get('grader_model', 'N/A')}\n")
            f.write("\n")
            
            # Summary table
            f.write("## 📊 Results Summary\n\n")
            
            if with_grading:
                f.write("| Rank | Model | Clean% | Quality | Latency | Score | Recommendation |\n")
                f.write("|------|-------|--------|---------|---------|-------|----------------|\n")
            else:
                f.write("| Rank | Model | Clean Rate | Avg Latency | Degenerate | Recommendation |\n")
                f.write("|------|-------|------------|-------------|------------|----------------|\n")
            
            # Sort by combined score (desc)
            sorted_models = sorted(
                results['models'].items(),
                key=lambda x: -x[1].get('combined_score', 0)
            )
            
            for rank, (model, data) in enumerate(sorted_models, 1):
                clean_rate = data['clean_rate']
                avg_lat = data['avg_latency_ms']
                degen = data['degenerate_count']
                
                if with_grading:
                    avg_quality = data.get('avg_quality', 0)
                    score = data.get('combined_score', 0)
                    
                    if score >= 85 and clean_rate == 100:
                        rec = "✅ CHAMPION" if rank == 1 else "✅ Excellent"
                    elif score >= 70 and clean_rate == 100:
                        rec = "✅ Good"
                    elif clean_rate == 100:
                        rec = "⚠️ Acceptable"
                    else:
                        rec = "❌ Not recommended"
                    
                    f.write(f"| {rank} | `{model}` | {clean_rate:.0f}% | {avg_quality:.0f}/100 | {avg_lat:.0f}ms | {score:.0f} | {rec} |\n")
                else:
                    if clean_rate == 100:
                        rec = "✅ CHAMPION" if avg_lat < 5000 else "✅ Qualified"
                    elif clean_rate >= 80:
                        rec = "⚠️ Acceptable"
                    else:
                        rec = "❌ Not recommended"
                    
                    f.write(f"| {rank} | `{model}` | {clean_rate:.0f}% | {avg_lat:.0f}ms | {degen} | {rec} |\n")
            
            f.write("\n")
            
            # Score explanation
            if with_grading:
                f.write("### Score Formula\n")
                f.write("```\n")
                f.write("Score = (Clean% × 0.2) + (Quality × 0.6) + (Speed × 0.2)\n")
                f.write("Speed = max(0, 100 - latency_seconds × 5)\n")
                f.write("```\n\n")
            
            f.write("---\n\n")
            
            # Detailed results per model
            f.write("## 🔍 Detailed Results\n\n")
            
            for model, data in sorted_models:
                f.write(f"### {model}\n\n")
                f.write(f"- **Clean Rate:** {data['clean_rate']:.0f}%\n")
                f.write(f"- **Avg Latency:** {data['avg_latency_ms']:.0f}ms\n")
                f.write(f"- **Degenerate:** {data['degenerate_count']}\n")
                if with_grading and data.get('avg_quality'):
                    f.write(f"- **Avg Quality:** {data['avg_quality']:.0f}/100\n")
                    f.write(f"- **Combined Score:** {data.get('combined_score', 0):.0f}\n")
                f.write("\n")
                
                if with_grading:
                    f.write("| Posting | Status | Latency | Quality | Issues |\n")
                    f.write("|---------|--------|---------|---------|--------|\n")
                else:
                    f.write("| Posting | Status | Latency | Issues |\n")
                    f.write("|---------|--------|---------|--------|\n")
                
                for test in data['tests']:
                    pid = test['posting_id']
                    if test.get('success'):
                        status = "⚠️ DEGEN" if test.get('is_degenerate') else "✅ Clean"
                        lat = f"{test['latency_ms']:.0f}ms"
                        issues = ', '.join(test.get('issues', [])[:2]) or '-'
                        
                        if with_grading:
                            quality = test.get('quality', {})
                            q_score = quality.get('overall', '-')
                            q_str = f"{q_score}" if isinstance(q_score, int) else q_score
                            f.write(f"| {pid} | {status} | {lat} | {q_str} | {issues} |\n")
                        else:
                            f.write(f"| {pid} | {status} | {lat} | {issues} |\n")
                    else:
                        status = "❌ Error"
                        lat = "-"
                        issues = test.get('error', '')[:30]
                        if with_grading:
                            f.write(f"| {pid} | {status} | {lat} | - | {issues} |\n")
                        else:
                            f.write(f"| {pid} | {status} | {lat} | {issues} |\n")
                
                f.write("\n")
                
                # Quality breakdown for graded tests
                if with_grading:
                    graded_tests = [t for t in data['tests'] if t.get('quality') and not t['quality'].get('grading_error')]
                    if graded_tests:
                        f.write("**Quality Breakdown:**\n\n")
                        f.write("| Posting | Role | Complete | Accurate | Format | Explanation |\n")
                        f.write("|---------|------|----------|----------|--------|-------------|\n")
                        for test in graded_tests:
                            q = test['quality']
                            f.write(f"| {test['posting_id']} | {q['role_title']}/25 | {q['completeness']}/40 | {q['accuracy']}/25 | {q['formatting']}/10 | {q['explanation'][:50]}... |\n")
                        f.write("\n")
            
            # Sample outputs from best model
            if sorted_models:
                best_model, best_data = sorted_models[0]
                f.write(f"## 📝 Sample Output from Best Model ({best_model})\n\n")
                
                for test in best_data['tests'][:2]:  # Show first 2
                    if test.get('success') and not test.get('is_degenerate'):
                        f.write(f"### Posting {test['posting_id']}\n\n")
                        if with_grading and test.get('quality'):
                            q = test['quality']
                            f.write(f"**Quality Score:** {q['overall']}/100\n\n")
                        f.write("```\n")
                        f.write(test.get('response_preview', '')[:1000])
                        f.write("\n...\n```\n\n")
        
        print(f"\n📄 Report saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Benchmark extraction models')
    parser.add_argument('--posting-ids', type=str, help='Comma-separated posting IDs')
    parser.add_argument('--problematic', type=int, default=5, help='Number of problematic postings to test')
    parser.add_argument('--models', type=str, help='Comma-separated model names (optional)')
    parser.add_argument('--output', type=str, help='Output report path')
    parser.add_argument('--with-grading', action='store_true', help='Enable quality grading (slower but more accurate)')
    
    args = parser.parse_args()
    
    benchmark = ExtractionBenchmark()
    
    # Get postings
    if args.posting_ids:
        posting_ids = [int(x.strip()) for x in args.posting_ids.split(',')]
        postings = benchmark.get_postings_by_ids(posting_ids)
    else:
        postings = benchmark.get_problematic_postings(args.problematic)
    
    if not postings:
        print("❌ No postings found")
        return
    
    print(f"📋 Testing {len(postings)} postings:")
    for p in postings:
        print(f"  - {p['posting_id']}: {p['job_title'][:50]}... ({p['desc_length']} chars)")
    
    # Get models
    models = None
    if args.models:
        models = [m.strip() for m in args.models.split(',')]
    
    # Run benchmark
    results = benchmark.run_benchmark(postings, models, with_grading=args.with_grading)
    
    # Generate report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = '_quality' if args.with_grading else ''
    output_file = args.output or f"reports/extraction_benchmark{suffix}_{timestamp}.md"
    benchmark.generate_report(results, output_file)
    
    # Print recommendation
    print("\n" + "=" * 60)
    print("🏆 RECOMMENDATION")
    print("=" * 60)
    
    sorted_models = sorted(
        results['models'].items(),
        key=lambda x: -x[1].get('combined_score', 0)
    )
    
    if sorted_models:
        best_model, best_data = sorted_models[0]
        clean_rate = best_data['clean_rate']
        
        if args.with_grading:
            avg_quality = best_data.get('avg_quality', 0)
            score = best_data.get('combined_score', 0)
            
            print(f"🥇 Best Model: {best_model}")
            print(f"   Combined Score: {score:.0f}/100")
            print(f"   Clean Rate: {clean_rate:.0f}%")
            print(f"   Quality: {avg_quality:.0f}/100")
            print(f"   Avg Latency: {best_data['avg_latency_ms']:.0f}ms")
            
            if score >= 85 and clean_rate == 100:
                print(f"\n✅ RECOMMENDED: Replace current extractor with {best_model}")
            elif score >= 70 and clean_rate == 100:
                print(f"\n✅ ACCEPTABLE: {best_model} is a good choice")
            else:
                print(f"\n⚠️  Consider testing more models or adjusting prompts")
        else:
            if clean_rate == 100:
                print(f"✅ Replace gemma3:1b with {best_model}")
                print(f"   Clean rate: {clean_rate:.0f}%")
                print(f"   Avg latency: {best_data['avg_latency_ms']:.0f}ms")
            else:
                print(f"⚠️ No model achieved 100% clean rate")
                print(f"   Best: {best_model} at {clean_rate:.0f}%")
            
            print(f"\n💡 TIP: Run with --with-grading for quality assessment")


if __name__ == '__main__':
    main()
