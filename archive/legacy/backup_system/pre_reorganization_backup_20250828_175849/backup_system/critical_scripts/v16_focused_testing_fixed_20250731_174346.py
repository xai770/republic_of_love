#!/usr/bin/env python3
"""
V16.2 Focused Quality Testing - Phase 2
=======================================

River's focused testing approach: 4 proven quality models × 20 diverse job postings
This provides higher quality validation with optimized resource usage.
Based on River's quality analysis of V16.1 results.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from v16_clean_llm_interface import V16LLMInterface, test_model_availability

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('v16.2_focused_testing')

class V16FocusedTester:
    """
    V16.2 focused quality testing with River's top 4 models
    Tests 4 proven models × 20 diverse job postings = 80 high-quality tests
    """
    
    def __init__(self, tester_id: str, test_dir: Path):
        self.test_dir = test_dir
        self.tester_id = tester_id
        
        # Create tester-specific output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_base = Path("/home/xai/Documents/ty_learn/ty_log/ty_projects/v16_hybrid_framework/v16.2_testing")
        self.results_dir = output_base / f"{tester_id}_runs" / f"run_{timestamp}"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎯 Tester: {tester_id.upper()}")
        logger.info(f"📁 Results: {self.results_dir}")
        
        # Load V16 hybrid prompt
        prompt_file = test_dir / "v16.1_qa_source_package" / "raw_inputs" / "v16_hybrid_template.txt"
        if not prompt_file.exists():
            raise FileNotFoundError(f"V16 hybrid template not found: {prompt_file}")
        
        self.hybrid_prompt = prompt_file.read_text().strip()
        logger.info(f"✅ Loaded V16 hybrid template ({len(self.hybrid_prompt)} chars)")
        
        # Initialize LLM interface
        self.llm_interface = V16LLMInterface()
        
        # Model health tracking
        self.model_health = {}
        self.blacklisted_models = set()
        
        # Blacklist thresholds
        self.max_consecutive_failures = 3
        self.min_success_rate_threshold = 0.2
        
        # River's top 4 quality-proven models (based on V16.1 analysis)
        self.models = [
            "mistral-nemo:12b",    # Quality champion - 37/40 score
            "deepseek-r1:8b",      # Thoughtful analyzer - 34/40 score  
            "llama3.2:latest",     # Speed/quality balance - 32/40 score
            "gemma3:4b"            # Fast & reliable - 31/40 score
        ]
        
        # River's selected 20 diverse job postings (curated for maximum variety)
        self.standardized_jobs = [
            # Finance Sector (5 jobs)
            "job59021.json",  # Senior Coverage Specialist - Complex financial
            "job60463.json",  # Product Manager - Multi-role complexity
            "job63625.json",  # Financial Analyst - Quantitative focus
            "job61127.json",  # Risk Analyst - Regulatory language
            "job63144.json",  # Compliance Officer - Policy interpretation
            
            # Technology Sector (5 jobs)
            "job64451.json",  # DevOps Engineer - Technical infrastructure
            "job64006.json",  # Administrative Coordinator - Tech support
            "job64658.json",  # Mixed role - Technical/business hybrid
            "job65047.json",  # Hybrid position - Multiple departments
            "job62118.json",  # HR Business Partner - Tech-oriented
            
            # Additional Diverse Roles (10 jobs)
            "job15929.json",  # Entry-level position
            "job44161.json",  # Mid-level role
            "job44162.json",  # Senior-level role
            "job50571.json",  # Executive-level role
            "job50579.json",  # Consulting role
            "job53333.json",  # Operations role
            "job55025.json",  # Strategy role
            "job56411.json",  # Marketing role
            "job59213.json",  # Sales role
            "job59386.json"   # International role
        ]
        
        logger.info(f"🏆 Using River's 4 proven quality models")
        logger.info(f"📊 Using curated 20-job diverse test set")
        
    def validate_models(self) -> List[str]:
        """Validate all required models are available, no auto-pull"""
        logger.info("🔍 Validating River's quality model selection...")
        
        # Use the corrected test_model_availability function that expects a list
        availability_results = test_model_availability(self.models)
        
        available_models = []
        missing_models = []
        
        for model in self.models:
            if availability_results.get(model, False):
                logger.info(f"  ✅ {model}")
                available_models.append(model)
            else:
                logger.error(f"  ❌ {model} - NOT AVAILABLE")
                missing_models.append(model)
        
        if missing_models:
            logger.error(f"🚫 Missing required models: {missing_models}")
            logger.error("Please install missing models with 'ollama pull <model>'")
            raise RuntimeError(f"Missing required models: {missing_models}")
        
        logger.info(f"✅ All {len(available_models)} quality models available")
        return available_models
        
    def load_diverse_jobs(self) -> List[Dict[str, Any]]:
        """Load River's curated 20-job diverse test set"""
        logger.info("📂 Loading River's diverse job test set...")
        
        jobs_dir = self.test_dir / "v16.1_qa_source_package" / "raw_inputs"
        loaded_jobs = []
        missing_jobs = []
        
        for job_file in self.standardized_jobs:
            job_path = jobs_dir / job_file
            if job_path.exists():
                try:
                    with open(job_path, 'r') as f:
                        job_data = json.load(f)
                    loaded_jobs.append({
                        'filename': job_file,
                        'data': job_data
                    })
                    logger.info(f"  ✅ {job_file}")
                except Exception as e:
                    logger.error(f"  ❌ {job_file} - Load error: {e}")
                    missing_jobs.append(job_file)
            else:
                logger.error(f"  ❌ {job_file} - File not found")
                missing_jobs.append(job_file)
        
        if missing_jobs:
            logger.error(f"🚫 Missing job files: {missing_jobs}")
            raise RuntimeError(f"Missing job files: {missing_jobs}")
        
        logger.info(f"✅ Loaded {len(loaded_jobs)} diverse test jobs")
        return loaded_jobs
    
    def update_model_health(self, model_name: str, success: bool, response_time: float = None, error_type: str = None):
        """Update model health tracking and check for blacklisting"""
        if model_name not in self.model_health:
            self.model_health[model_name] = {
                "total_attempts": 0,
                "successes": 0,
                "failures": 0,
                "consecutive_failures": 0,
                "avg_response_time": 0.0,
                "error_types": {},
                "last_success": None,
                "last_failure": None
            }
        
        health = self.model_health[model_name]
        health["total_attempts"] += 1
        
        if success:
            health["successes"] += 1
            health["consecutive_failures"] = 0
            health["last_success"] = datetime.now().isoformat()
            
            if response_time:
                current_avg = health["avg_response_time"]
                total_successes = health["successes"]
                health["avg_response_time"] = ((current_avg * (total_successes - 1)) + response_time) / total_successes
        else:
            health["failures"] += 1
            health["consecutive_failures"] += 1
            health["last_failure"] = datetime.now().isoformat()
            
            if error_type:
                if error_type not in health["error_types"]:
                    health["error_types"][error_type] = 0
                health["error_types"][error_type] += 1
        
        self._check_blacklist_conditions(model_name)
    
    def _check_blacklist_conditions(self, model_name: str):
        """Check if a model should be blacklisted based on performance"""
        if model_name in self.blacklisted_models:
            return
            
        health = self.model_health[model_name]
        
        if health["consecutive_failures"] >= self.max_consecutive_failures:
            self.blacklisted_models.add(model_name)
            logger.warning(f"🚫 Blacklisted {model_name}: {health['consecutive_failures']} consecutive failures")
            return
        
        if health["total_attempts"] >= 5:
            success_rate = health["successes"] / health["total_attempts"]
            if success_rate < self.min_success_rate_threshold:
                self.blacklisted_models.add(model_name)
                logger.warning(f"🚫 Blacklisted {model_name}: {success_rate:.1%} success rate")
    
    def test_single_job_single_model(self, job_data: Dict[str, Any], model_name: str) -> Dict[str, Any]:
        """Test a single job with a single model"""
        if model_name in self.blacklisted_models:
            return {
                "success": False,
                "error": "Model blacklisted",
                "response_time": 0,
                "result": None
            }
        
        try:
            # Extract job description
            job_description = job_data.get('job_content', {}).get('description', '')
            if not job_description:
                raise ValueError("No job description found")
            
            # Create full prompt
            full_prompt = f"{self.hybrid_prompt}\n\nJob Description:\n{job_description}"
            
            # Call model using the correct interface
            logger.info(f"🔄 Calling model {model_name}...")
            start_time = time.time()
            
            result = self.llm_interface.call_model(model_name, full_prompt)
            
            end_time = time.time()
            actual_response_time = end_time - start_time
            
            if result.get("success", False):
                logger.info(f"✅ Model {model_name} completed in {actual_response_time:.1f}s")
                self.update_model_health(model_name, True, actual_response_time)
                return {
                    "success": True,
                    "error": None,
                    "response_time": actual_response_time,
                    "result": result.get("response", "")
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ Model {model_name} failed: {error_msg}")
                self.update_model_health(model_name, False, error_type=str(error_msg))
                return {
                    "success": False,
                    "error": str(error_msg),
                    "response_time": actual_response_time,
                    "result": None
                }
                
        except Exception as e:
            logger.error(f"❌ Unexpected error with {model_name}: {e}")
            self.update_model_health(model_name, False, error_type=str(e))
            return {
                "success": False,
                "error": str(e),
                "response_time": 0,
                "result": None
            }
    
    def run_focused_testing(self) -> Dict[str, Any]:
        """Run River's focused quality testing (4 models × 20 jobs = 80 tests)"""
        logger.info("🚀 Starting V16.2 Focused Quality Testing")
        logger.info(f"👤 Tester: {self.tester_id.upper()}")
        
        # Validate models
        available_models = self.validate_models()
        
        # Load job data
        test_jobs = self.load_diverse_jobs()
        
        logger.info(f"🎯 Testing: {len(test_jobs)} jobs × {len(available_models)} models = {len(test_jobs) * len(available_models)} total tests")
        
        all_results = []
        test_count = 0
        total_tests = len(test_jobs) * len(available_models)
        
        for job_info in test_jobs:
            job_file = job_info['filename']
            job_data = job_info['data']
            
            logger.info(f"\n📋 Testing job: {job_file}")
            
            for model_name in available_models:
                if model_name in self.blacklisted_models:
                    logger.warning(f"  ⚫ {model_name} - BLACKLISTED")
                    continue
                
                logger.info(f"  🔄 {model_name}...")
                
                result = self.test_single_job_single_model(job_data, model_name)
                
                # Store result
                test_result = {
                    "job_file": job_file,
                    "model": model_name,
                    "success": result["success"],
                    "response_time": result["response_time"],
                    "result": result["result"],
                    "blacklisted": model_name in self.blacklisted_models
                }
                
                if result["success"]:
                    logger.info(f"    ✅ Success ({result['response_time']:.2f}s)")
                else:
                    logger.info(f"    ❌ Failed: {result['error']}")
                
                all_results.append(test_result)
                test_count += 1
                
                logger.info(f"  📊 Progress: {test_count}/{total_tests} ({test_count/total_tests*100:.1f}%)")
        
        # Generate summary
        successful_tests = sum(1 for r in all_results if r["success"])
        total_tests_run = len(all_results)
        
        summary = {
            "focused_test_summary": {
                "tester_id": self.tester_id,
                "timestamp": datetime.now().isoformat(),
                "test_type": "V16.2 Focused Quality Testing",
                "total_jobs": len(test_jobs),
                "total_models": len(available_models),
                "quality_models": len(available_models),
                "blacklisted_models": len(self.blacklisted_models),
                "blacklisted_model_list": list(self.blacklisted_models),
                "total_tests": total_tests_run,
                "total_successes": successful_tests,
                "total_failures": total_tests_run - successful_tests,
                "overall_success_rate": (successful_tests / total_tests_run * 100) if total_tests_run > 0 else 0,
                "model_statistics": {}
            },
            "detailed_results": all_results
        }
        
        # Calculate per-model statistics
        for model in available_models:
            model_results = [r for r in all_results if r["model"] == model]
            model_successes = sum(1 for r in model_results if r["success"])
            model_times = [r["response_time"] for r in model_results if r["success"]]
            
            health = self.model_health.get(model, {})
            
            summary["focused_test_summary"]["model_statistics"][model] = {
                "total_tests": len(model_results),
                "successes": model_successes,
                "success_rate": (model_successes / len(model_results) * 100) if model_results else 0,
                "avg_response_time": sum(model_times) / len(model_times) if model_times else 0,
                "blacklisted": model in self.blacklisted_models,
                "consecutive_failures": health.get("consecutive_failures", 0)
            }
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Detailed results
        detailed_file = self.results_dir / f"detailed_results_{timestamp}.json"
        with open(detailed_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        # Summary
        summary_file = self.results_dir / f"focused_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Model health
        health_file = self.results_dir / f"model_health_{timestamp}.json"
        with open(health_file, 'w') as f:
            json.dump(self.model_health, f, indent=2)
        
        logger.info("💾 Results saved:")
        logger.info(f"  📝 Detailed: {detailed_file}")
        logger.info(f"  📊 Summary: {summary_file}")
        logger.info(f"  🏥 Health: {health_file}")
        
        return summary

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="V16.2 Focused Quality Testing - River's Phase 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
River's Quality-Focused Testing Approach:
  4 proven quality models × 20 diverse job postings = 80 optimized tests
  
Quality Models (based on V16.1 analysis):
  - mistral-nemo:12b (Quality champion - 37/40 score)
  - deepseek-r1:8b (Thoughtful analyzer - 34/40 score)  
  - llama3.2:latest (Speed/quality balance - 32/40 score)
  - gemma3:4b (Fast & reliable - 31/40 score)

Examples:
  python3 v16_focused_testing.py --tester-id arden
  python3 v16_focused_testing.py --tester-id river
  python3 v16_focused_testing.py --tester-id qa
        """
    )
    
    parser.add_argument(
        "--tester-id",
        type=str,
        default="default",
        help="Tester identifier for result separation (default: default)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    test_dir = Path.cwd()  # Use current working directory
    
    # Validate we're in the correct directory
    if not (test_dir / "v16.1_qa_source_package").exists():
        logger.error("❌ v16.1_qa_source_package not found")
        logger.error("Please run from ty_projects/v16_hybrid_framework directory")
        return 1
    
    try:
        print(f"\n🎯 V16.2 Focused Quality Testing - Tester: {args.tester_id.upper()}")
        print("=" * 70)
        print("🏆 River's Quality-Focused Strategy:")
        print("  • 4 proven quality models (top performers from V16.1)")
        print("  • 20 diverse job postings (curated for maximum variety)")
        print("  • 80 optimized tests (higher quality, efficient resource usage)")
        print("  • Manual quality scoring for definitive ranking")
        print()
        
        # Create tester and run focused testing
        tester = V16FocusedTester(args.tester_id, test_dir)
        
        print()
        
        # Run focused tests
        summary = tester.run_focused_testing()
        
        # Print summary
        test_summary = summary["focused_test_summary"]
        print("\n🎉 V16.2 Focused Quality Testing Complete")
        print("=" * 70)
        print(f"Tester: {test_summary['tester_id'].upper()}")
        print(f"Jobs Tested: {test_summary['total_jobs']}")
        print(f"Quality Models: {test_summary['quality_models']}")
        print(f"Blacklisted Models: {test_summary['blacklisted_models']}")
        if test_summary['blacklisted_model_list']:
            print(f"  Blacklisted: {', '.join(test_summary['blacklisted_model_list'])}")
        print(f"Total Tests: {test_summary['total_tests']}")
        print(f"Successful Tests: {test_summary['total_successes']}")
        print(f"Overall Success Rate: {test_summary['overall_success_rate']:.1f}%")
        
        print("\n📊 Quality Model Performance:")
        for model, stats in test_summary["model_statistics"].items():
            status = "🚫 BLACKLISTED" if stats.get('blacklisted', False) else "✅ Active"
            consecutive_failures = f" ({stats.get('consecutive_failures', 0)} consecutive failures)" if stats.get('consecutive_failures', 0) > 0 else ""
            print(f"  {model}: {stats['successes']}/{stats['total_tests']} ({stats['success_rate']:.1f}%) - Avg: {stats['avg_response_time']:.2f}s [{status}]{consecutive_failures}")
        
        print(f"\nResults Location: {tester.results_dir}")
        print(f"Ready for River's quality analysis and manual scoring! 🎯")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
