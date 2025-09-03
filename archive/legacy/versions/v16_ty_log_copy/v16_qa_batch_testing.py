#!/usr/bin/env python3
"""
V16.1 QA Batch Testing - Misty's Strategy Implementation
=======================================================

Tests the V16 hybrid template using Misty's approved 10-model mix
and standardized 10-job selection for consistent QA validation.
Supports separate tester tracking (dexi, river, qa).
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import sys
sys.path.append('v16.1_qa_source_package/raw_inputs')
from v16_clean_llm_interface import V16LLMInterface, test_model_availability

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('v16_qa_testing')

class V16QATester:
    """
    V16.1 QA batch testing with Misty's approved model selection
    and standardized job list for consistent cross-tester validation
    """
    
    def __init__(self, test_dir: Path, tester_id: str = "default"):
        self.test_dir = test_dir
        self.tester_id = tester_id
        
        # Create tester-specific output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_base = Path("/home/xai/Documents/ty_learn/ty_log/testing/v16_exec")
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
        
        # Misty's approved 10-model mix
        self.models = [
            "mistral-nemo:12b",       # Large, instruction-tuned baseline
            "llama3.2:latest",        # General large model anchor  
            "bge-m3:567m",           # Tiny embedding model edge-case
            "deepseek-r1:8b",        # Hybrid reasoning
            "phi4-mini-reasoning",    # Reasoning-optimized
            "gemma3:4b",             # Mid-sized instruction precision
            "qwen2.5:7b",            # Large multilingual
            "granite3.1-moe:3b",     # MoE mid-size topology
            "dolphin3:8b",           # Versatile hybrid
            "codegemma:2b"           # Code-focused extraction
        ]
        
        # Standardized 10-job test list (stratified per Misty's categories)
        self.standardized_jobs = [
            # Engineering (Technical-Heavy) - 2 jobs
            "job59021.json",  # Senior Software Engineer
            "job64451.json",  # DevOps Engineer
            
            # Risk/Compliance (Linguistic Nuance) - 2 jobs  
            "job61127.json",  # Risk Analyst
            "job63144.json",  # Compliance Officer
            
            # HR/Admin (Structure Variance) - 2 jobs
            "job62118.json",  # HR Business Partner
            "job64006.json",  # Administrative Coordinator
            
            # Finance/Product (Multi-Role Complexity) - 2 jobs
            "job60463.json",  # Product Manager
            "job63625.json",  # Financial Analyst
            
            # Ambiguous/Uncategorized (Edge Cases) - 2 jobs
            "job64658.json",  # Mixed role
            "job65047.json"   # Hybrid position
        ]
        
        logger.info(f"📋 Using Misty's 10-model strategy")
        logger.info(f"📊 Using standardized 10-job test set")
        
    def validate_models(self) -> List[str]:
        """Validate all required models are available, no auto-pull"""
        logger.info("🔍 Validating Misty's model requirements...")
        
        available_models = []
        missing_models = []
        
        for model in self.models:
            # Check exact name first
            try:
                interface = V16LLMInterface()
                result = interface.call_model(model, "Hello")
                if result.get("success"):
                    available_models.append(model)
                    logger.info(f"  ✅ {model}")
                else:
                    # Try with :latest tag if not specified
                    if ":" not in model:
                        test_name = f"{model}:latest"
                        result = interface.call_model(test_name, "Hello")
                        if result.get("success"):
                            available_models.append(test_name)
                            logger.info(f"  ✅ {test_name} (resolved from {model})")
                        else:
                            missing_models.append(model)
                            logger.error(f"  ❌ {model} - NOT AVAILABLE")
                    else:
                        missing_models.append(model)
                        logger.error(f"  ❌ {model} - NOT AVAILABLE")
            except Exception as e:
                missing_models.append(model)
                logger.error(f"  ❌ {model} - Error: {e}")
        
        if missing_models:
            logger.error(f"🚫 Missing required models: {missing_models}")
            logger.error("Please install missing models with 'ollama pull <model>'")
            raise SystemExit(f"Missing required models: {missing_models}")
        
        logger.info(f"✅ All {len(available_models)} required models available")
        return available_models
        
    def load_standardized_jobs(self) -> List[Dict[str, Any]]:
        """Load the standardized 10-job test set"""
        logger.info("📂 Loading standardized job test set...")
        
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
                            "filename": job_file,
                            "data": job_data
                        })
                    logger.info(f"  ✅ {job_file}")
                except Exception as e:
                    logger.error(f"  ❌ {job_file} - Error loading: {e}")
                    missing_jobs.append(job_file)
            else:
                logger.error(f"  ❌ {job_file} - File not found")
                missing_jobs.append(job_file)
        
        if missing_jobs:
            logger.error(f"🚫 Missing required job files: {missing_jobs}")
            raise SystemExit(f"Missing required job files: {missing_jobs}")
        
        logger.info(f"✅ Loaded {len(loaded_jobs)} standardized test jobs")
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
                
    def test_single_job_model(self, job: Dict[str, Any], model_name: str) -> Dict[str, Any]:
        """Test a single job with a single model"""
        if model_name in self.blacklisted_models:
            return {
                "job_file": job["filename"],
                "model": model_name,
                "success": False,
                "error": "Model blacklisted",
                "response_time": 0,
                "result": None,
                "blacklisted": True
            }
        
        job_description = job["data"]["job_content"]["description"]
        start_time = time.time()
        
        try:
            # Make API call to model
            result = self.llm_interface.call_model(
                model_name, 
                f"{self.hybrid_prompt}\n\n{job_description}"
            )
            
            response_time = time.time() - start_time
            
            if result and result.get("success"):
                self.update_model_health(model_name, True, response_time)
                return {
                    "job_file": job["filename"],
                    "model": model_name,
                    "success": True,
                    "response_time": response_time,
                    "result": result["response"],
                    "blacklisted": False
                }
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response"
                self.update_model_health(model_name, False, None, error_msg)
                return {
                    "job_file": job["filename"],
                    "model": model_name,
                    "success": False,
                    "error": error_msg,
                    "response_time": response_time,
                    "result": None,
                    "blacklisted": False
                }
                
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            self.update_model_health(model_name, False, None, error_msg)
            return {
                "job_file": job["filename"],
                "model": model_name,
                "success": False,
                "error": error_msg,
                "response_time": response_time,
                "result": None,
                "blacklisted": False
            }
    
    def run_qa_validation(self) -> Dict[str, Any]:
        """Run the complete QA validation test suite"""
        logger.info("🚀 Starting V16.1 QA Validation Test Suite")
        logger.info(f"👤 Tester: {self.tester_id.upper()}")
        
        # Validate models and jobs
        available_models = self.validate_models()
        test_jobs = self.load_standardized_jobs()
        
        logger.info(f"🎯 Testing: {len(test_jobs)} jobs × {len(available_models)} models = {len(test_jobs) * len(available_models)} total tests")
        
        all_results = []
        total_tests = len(test_jobs) * len(available_models)
        completed_tests = 0
        
        # Run all tests
        for job in test_jobs:
            logger.info(f"\n📋 Testing job: {job['filename']}")
            
            for model in available_models:
                if model in self.blacklisted_models:
                    logger.info(f"  ⚫ {model} - BLACKLISTED")
                    continue
                    
                logger.info(f"  🔄 {model}...")
                result = self.test_single_job_model(job, model)
                all_results.append(result)
                
                completed_tests += 1
                if result["success"]:
                    logger.info(f"    ✅ Success ({result['response_time']:.2f}s)")
                else:
                    logger.info(f"    ❌ Failed: {result['error']}")
                
                # Progress indicator
                progress = (completed_tests / total_tests) * 100
                logger.info(f"  📊 Progress: {completed_tests}/{total_tests} ({progress:.1f}%)")
        
        # Generate summary
        summary = self._generate_qa_summary(all_results, test_jobs, available_models)
        
        # Save results
        self._save_qa_results(all_results, summary)
        
        return summary
    
    def _generate_qa_summary(self, results: List[Dict], jobs: List[Dict], models: List[str]) -> Dict[str, Any]:
        """Generate comprehensive QA test summary"""
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        # Model statistics
        model_stats = {}
        for model in models:
            model_results = [r for r in results if r["model"] == model]
            model_successes = [r for r in model_results if r["success"]]
            
            if model_results:
                avg_time = sum(r["response_time"] for r in model_successes) / len(model_successes) if model_successes else 0
                model_stats[model] = {
                    "total_tests": len(model_results),
                    "successes": len(model_successes),
                    "success_rate": len(model_successes) / len(model_results) * 100,
                    "avg_response_time": avg_time,
                    "blacklisted": model in self.blacklisted_models,
                    "consecutive_failures": self.model_health.get(model, {}).get("consecutive_failures", 0)
                }
        
        return {
            "qa_test_summary": {
                "tester_id": self.tester_id,
                "timestamp": datetime.now().isoformat(),
                "total_jobs": len(jobs),
                "total_models": len(models),
                "healthy_models": len(models) - len(self.blacklisted_models),
                "blacklisted_models": len(self.blacklisted_models),
                "blacklisted_model_list": list(self.blacklisted_models),
                "total_tests": len(results),
                "total_successes": len(successful_results),
                "total_failures": len(failed_results),
                "overall_success_rate": len(successful_results) / len(results) * 100 if results else 0,
                "model_statistics": model_stats
            },
            "detailed_results": results,
            "model_health": self.model_health
        }
    
    def _save_qa_results(self, results: List[Dict], summary: Dict[str, Any]):
        """Save QA test results and summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = self.results_dir / f"detailed_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save summary
        summary_file = self.results_dir / f"qa_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save model health report
        health_file = self.results_dir / f"model_health_{timestamp}.json"
        with open(health_file, 'w') as f:
            json.dump(self.model_health, f, indent=2)
        
        logger.info(f"💾 Results saved:")
        logger.info(f"  📝 Detailed: {results_file}")
        logger.info(f"  📊 Summary: {summary_file}")
        logger.info(f"  🏥 Health: {health_file}")

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="V16.1 QA Batch Testing - Misty's Strategy Implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Tester ID Options:
  dexi    : Dexi's validation run
  river   : River's technical validation  
  qa      : QA team validation
  sage    : Sage's QA review
  custom  : Custom tester identifier

Examples:
  python3 v16_qa_batch_testing.py --tester-id dexi
  python3 v16_qa_batch_testing.py --tester-id river
  python3 v16_qa_batch_testing.py --tester-id qa
  python3 v16_qa_batch_testing.py --tester-id sage
        """
    )
    
    parser.add_argument(
        "--tester-id",
        type=str,
        default="default",
        help="Tester identifier for separate result tracking (default: default)"
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
    
    test_dir = Path.cwd()
    
    # Validate we're in the correct directory
    required_files = [
        "v16.1_qa_source_package/raw_inputs/v16_hybrid_template.txt",
        "v16.1_qa_source_package/raw_inputs/v16_clean_llm_interface.py",
        "v16.1_qa_source_package/STANDARDIZED_TEST_JOBS.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (test_dir / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        logger.error("Please run from the v16_hybrid_framework directory")
        return 1
    
    try:
        # Create and run tester
        tester = V16QATester(test_dir, args.tester_id)
        
        print(f"\n🎯 V16.1 QA Validation - Tester: {args.tester_id.upper()}")
        print("=" * 60)
        print("📋 Misty's Approved Strategy:")
        print("  • 10 strategically selected models")
        print("  • 10 standardized job postings")
        print("  • Cross-tester result consistency")
        print("  • Complete audit trail")
        print()
        
        # Run QA validation
        summary = tester.run_qa_validation()
        
        # Print summary
        qa_summary = summary["qa_test_summary"]
        print("\n🎉 V16.1 QA Validation Complete")
        print("=" * 60)
        print(f"Tester: {qa_summary['tester_id'].upper()}")
        print(f"Jobs Tested: {qa_summary['total_jobs']}")
        print(f"Models Available: {qa_summary['total_models']}")
        print(f"Healthy Models: {qa_summary['healthy_models']}")
        print(f"Blacklisted Models: {qa_summary['blacklisted_models']}")
        if qa_summary['blacklisted_model_list']:
            print(f"  Blacklisted: {', '.join(qa_summary['blacklisted_model_list'])}")
        print(f"Total Tests: {qa_summary['total_tests']}")
        print(f"Successful Tests: {qa_summary['total_successes']}")
        print(f"Overall Success Rate: {qa_summary['overall_success_rate']:.1f}%")
        
        print("\n📊 Model Performance:")
        for model, stats in qa_summary["model_statistics"].items():
            status = "🚫 BLACKLISTED" if stats.get('blacklisted', False) else "✅ Active"
            consecutive_failures = f" ({stats.get('consecutive_failures', 0)} consecutive failures)" if stats.get('consecutive_failures', 0) > 0 else ""
            print(f"  {model}: {stats['successes']}/{stats['total_tests']} ({stats['success_rate']:.1f}%) - Avg: {stats['avg_response_time']:.2f}s [{status}]{consecutive_failures}")
        
        print(f"\nResults Location: {tester.results_dir}")
        print(f"Tester Directory: /home/xai/Documents/ty_learn/ty_log/testing/v16_exec/{args.tester_id}_runs/")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
