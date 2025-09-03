#!/usr/bin/env python3
"""
V16 Hybrid Batch Testing with Real Job Data
===========================================

Tests the V16 hybrid template across all available models using
real job posting data from ty_projects/data/postings.
This enables production-scale validation with actual job descriptions.
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
logger = logging.getLogger('v16_batch_testing')

class V16BatchTester:
    """
    V16 hybrid template batch testing with real job data
    Includes model health tracking and automatic blacklisting
    """
    
    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.results_dir = test_dir / "batch_results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Load V16 hybrid prompt
        prompt_file = test_dir / "v16_hybrid_template.txt"
        if not prompt_file.exists():
            raise FileNotFoundError(f"V16 hybrid template not found: {prompt_file}")
        
        self.hybrid_prompt = prompt_file.read_text().strip()
        logger.info(f"✅ Loaded V16 hybrid template ({len(self.hybrid_prompt)} chars)")
        
        # Initialize LLM interface
        self.llm_interface = V16LLMInterface()
        
        # Model health tracking
        self.model_health = {}  # Track success/failure rates per model
        self.blacklisted_models = set()  # Models that consistently fail
        self.model_timeouts = {}  # Track timeout patterns
        
        # Blacklist thresholds
        self.max_consecutive_failures = 3  # Blacklist after 3 consecutive failures
        self.min_success_rate_threshold = 0.2  # Blacklist if success rate < 20% after 5+ attempts
        
        # Comprehensive model list - all available Ollama models
        self.models = [
            # Primary models (larger, high-performance)
            "mistral-nemo:12b",
            "deepseek-r1:8b", 
            "qwen2.5:7b",
            "dolphin3:8b",
            "phi4-mini-reasoning:latest",
            "olmo2:latest",
            "gemma3n:latest",
            "codegemma:latest",
            "gemma2:latest",
            "qwen2.5vl:latest",
            "mistral:latest",
            "qwen3:latest",
            
            # Medium models (balanced performance/speed)
            "llama3.2:latest",
            "granite3.1-moe:3b",
            "gemma3:4b",
            "phi3:3.8b",
            "phi4-mini:latest",
            "qwen3:4b",
            "gemma3n:e2b",
            
            # Compact models (fast, lightweight)
            "qwen3:1.7b",
            "codegemma:2b",
            "llama3.2:1b",
            "gemma3:1b",
            "qwen3:0.6b"
        ]
        
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
            health["consecutive_failures"] = 0  # Reset consecutive failure counter
            health["last_success"] = datetime.now().isoformat()
            
            # Update average response time
            if response_time:
                current_avg = health["avg_response_time"]
                total_successes = health["successes"]
                health["avg_response_time"] = ((current_avg * (total_successes - 1)) + response_time) / total_successes
        else:
            health["failures"] += 1
            health["consecutive_failures"] += 1
            health["last_failure"] = datetime.now().isoformat()
            
            # Track error types
            if error_type:
                if error_type not in health["error_types"]:
                    health["error_types"][error_type] = 0
                health["error_types"][error_type] += 1
        
        # Check for blacklisting conditions
        self._check_blacklist_conditions(model_name)
    
    def _check_blacklist_conditions(self, model_name: str):
        """Check if a model should be blacklisted based on performance"""
        if model_name in self.blacklisted_models:
            return
            
        health = self.model_health[model_name]
        
        # Condition 1: Too many consecutive failures
        if health["consecutive_failures"] >= self.max_consecutive_failures:
            self.blacklisted_models.add(model_name)
            logger.warning(f"🚫 Blacklisted {model_name}: {health['consecutive_failures']} consecutive failures")
            return
        
        # Condition 2: Low success rate after sufficient attempts
        if health["total_attempts"] >= 5:
            success_rate = health["successes"] / health["total_attempts"]
            if success_rate < self.min_success_rate_threshold:
                self.blacklisted_models.add(model_name)
                logger.warning(f"🚫 Blacklisted {model_name}: Low success rate {success_rate:.1%} after {health['total_attempts']} attempts")
                return
    
    def is_model_blacklisted(self, model_name: str) -> bool:
        """Check if a model is blacklisted"""
        return model_name in self.blacklisted_models
    
    def get_healthy_models(self, models: List[str]) -> List[str]:
        """Filter out blacklisted models and return healthy ones"""
        return [model for model in models if not self.is_model_blacklisted(model)]
    
    def save_model_health_report(self):
        """Save detailed model health report"""
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "blacklisted_models": list(self.blacklisted_models),
            "blacklist_thresholds": {
                "max_consecutive_failures": self.max_consecutive_failures,
                "min_success_rate_threshold": self.min_success_rate_threshold
            },
            "model_health_details": self.model_health
        }
        
        health_file = self.results_dir / "model_health_report.json"
        with open(health_file, 'w') as f:
            json.dump(health_report, f, indent=2)
        
        logger.info(f"📊 Model health report saved to {health_file}")
        return health_file
        
    def load_real_job_postings(self) -> List[Dict[str, Any]]:
        """Load all real job postings from ty_projects/data/postings"""
        postings_dir = self.test_dir.parent.parent / "data" / "postings"
        
        if not postings_dir.exists():
            raise FileNotFoundError(
                f"Postings directory not found at: {postings_dir}\n"
                f"Please ensure you're running from ty_projects/v16_hybrid_framework/v16_testing/"
            )
        
        job_files = sorted(list(postings_dir.glob("job*.json")))
        if not job_files:
            raise FileNotFoundError(f"No job files found in: {postings_dir}")
        
        logger.info(f"📁 Found {len(job_files)} job postings to process")
        
        job_postings = []
        for job_file in job_files:
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                    
                # Extract the job description from the nested structure
                if 'job_content' in job_data and 'description' in job_data['job_content']:
                    job_posting = {
                        "job_id": job_data.get('job_metadata', {}).get('job_id', job_file.stem),
                        "job_title": job_data['job_content'].get('title', 'Unknown Title'),
                        "job_description": job_data['job_content']['description'],
                        "source_file": job_file.name,
                        "location": job_data['job_content'].get('location', {}),
                        "employment_details": job_data['job_content'].get('employment_details', {})
                    }
                    job_postings.append(job_posting)
                else:
                    logger.warning(f"⚠️  Skipping {job_file.name}: No job_content.description found")
                    
            except Exception as e:
                logger.warning(f"⚠️  Error loading {job_file.name}: {e}")
                continue
        
        logger.info(f"✅ Successfully loaded {len(job_postings)} job descriptions")
        return job_postings
        
    def build_full_prompt(self, job_description: str) -> str:
        """Build the complete prompt with template and job posting"""
        return f"{self.hybrid_prompt}\n\n[JOB_POSTING]\n{job_description}\n[/JOB_POSTING]"
    
    def test_single_job_single_model(self, job_data: Dict[str, Any], model_name: str) -> Dict[str, Any]:
        """
        Test a single job posting with a single model
        
        Args:
            job_data: Job posting data dictionary
            model_name: Name of the model to test
            
        Returns:
            Test result dictionary
        """
        # Check if model is blacklisted
        if self.is_model_blacklisted(model_name):
            logger.warning(f"⚫ Skipping blacklisted model {model_name} for job {job_data['job_id']}")
            return {
                "job_id": job_data['job_id'],
                "job_title": job_data['job_title'],
                "source_file": job_data['source_file'],
                "model": model_name,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Model blacklisted due to poor performance",
                "error_type": "blacklisted",
                "skipped": True
            }
        
        logger.info(f"🧪 Testing {model_name} with job {job_data['job_id']}...")
        
        # Build full prompt
        full_prompt = self.build_full_prompt(job_data['job_description'])
        
        # Call model
        start_time = time.time()
        result = self.llm_interface.call_model(model_name, full_prompt)
        total_time = time.time() - start_time
        
        # Process result
        test_result = {
            "job_id": job_data['job_id'],
            "job_title": job_data['job_title'],
            "source_file": job_data['source_file'],
            "model": model_name,
            "timestamp": datetime.now().isoformat(),
            "success": result["success"],
            "total_time": total_time,
            "prompt_length": len(full_prompt),
            "job_description_length": len(job_data['job_description'])
        }
        
        if result["success"]:
            test_result.update({
                "response_time": result["elapsed_time"],
                "response_length": len(result["response"]),
                "raw_response": result["response"],
                "parsed_extraction": self._parse_extraction(result["response"])
            })
            logger.info(f"✅ {model_name} - job {job_data['job_id']} - {result['elapsed_time']:.2f}s")
            
            # Update model health (success)
            self.update_model_health(model_name, True, result["elapsed_time"])
        else:
            test_result.update({
                "error": result["error"],
                "error_type": result.get("error_type", "unknown")
            })
            logger.error(f"❌ {model_name} - job {job_data['job_id']} - {result['error']}")
            
            # Update model health (failure)
            self.update_model_health(model_name, False, error_type=result.get("error_type", "unknown"))
        
        return test_result
    
    def _parse_extraction(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response to extract structured data
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed extraction data
        """
        try:
            # Try to find JSON in the response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception as e:
            logger.debug(f"Failed to parse JSON from response: {e}")
        
        # Return raw response if parsing fails
        return {"raw_response": response, "parsing_error": "Could not extract JSON"}
    
    def test_all_jobs_all_models(self, max_jobs: int = None) -> Dict[str, Any]:
        """
        Test all job postings with all available models
        
        Args:
            max_jobs: Maximum number of jobs to test (for testing/debugging)
            
        Returns:
            Complete test results
        """
        logger.info("🚀 Starting V16 batch testing with real job data...")
        
        # Load job postings
        job_postings = self.load_real_job_postings()
        
        # Limit jobs if specified
        if max_jobs:
            job_postings = job_postings[:max_jobs]
            logger.info(f"🔢 Limited to first {max_jobs} jobs for testing")
        
        # Check model availability
        available_models = test_model_availability(self.models)
        if not available_models:
            raise RuntimeError("No models available for testing")
        
        logger.info(f"🤖 Available models: {', '.join(available_models)}")
        
        # Filter out any pre-blacklisted models
        healthy_models = self.get_healthy_models(available_models)
        if len(healthy_models) < len(available_models):
            blacklisted_count = len(available_models) - len(healthy_models)
            logger.warning(f"⚫ {blacklisted_count} models pre-blacklisted: {list(self.blacklisted_models)}")
        
        if not healthy_models:
            raise RuntimeError("No healthy models available for testing")
        
        logger.info(f"💚 Testing with {len(healthy_models)} healthy models")
        
        # Run tests
        all_results = []
        total_tests = len(job_postings) * len(healthy_models)
        current_test = 0
        
        for job_data in job_postings:
            job_results = []
            
            # Get currently healthy models (may change during testing due to blacklisting)
            current_healthy_models = self.get_healthy_models(healthy_models)
            
            for model_name in current_healthy_models:
                current_test += 1
                logger.info(f"📊 Progress: {current_test}/{total_tests} - Job {job_data['job_id']} with {model_name}")
                
                try:
                    result = self.test_single_job_single_model(job_data, model_name)
                    job_results.append(result)
                    
                    # Check if model was just blacklisted
                    if self.is_model_blacklisted(model_name):
                        logger.warning(f"🚫 {model_name} was blacklisted during testing")
                        
                except Exception as e:
                    logger.error(f"❌ Error testing job {job_data['job_id']} with {model_name}: {e}")
                    
                    # Update model health for unexpected errors
                    self.update_model_health(model_name, False, error_type="exception")
                    
                    job_results.append({
                        "job_id": job_data['job_id'],
                        "model": model_name,
                        "success": False,
                        "error": str(e),
                        "error_type": "exception",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.5)
            
            all_results.extend(job_results)
            
            # Save intermediate results per job
            job_file = self.results_dir / f"job_{job_data['job_id']}_results.json"
            with open(job_file, 'w') as f:
                json.dump({
                    "job_metadata": job_data,
                    "model_results": job_results,
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
        
        # Save model health report
        self.save_model_health_report()
        
        # Calculate summary statistics (including blacklisted models in totals)
        total_successes = sum(1 for r in all_results if r["success"])
        total_attempted = len(all_results)
        success_rate = (total_successes / total_attempted) * 100 if total_attempted else 0
        
        # Group results by model (including health data)
        model_stats = {}
        for model in available_models:  # Include all originally available models
            model_results = [r for r in all_results if r["model"] == model]
            model_successes = sum(1 for r in model_results if r["success"])
            
            # Get health data
            health_data = self.model_health.get(model, {})
            
            model_stats[model] = {
                "total_tests": len(model_results),
                "successes": model_successes,
                "success_rate": (model_successes / len(model_results)) * 100 if model_results else 0,
                "avg_response_time": sum(r.get("response_time", 0) for r in model_results if r["success"]) / model_successes if model_successes > 0 else 0,
                "blacklisted": model in self.blacklisted_models,
                "consecutive_failures": health_data.get("consecutive_failures", 0),
                "total_attempts": health_data.get("total_attempts", 0)
            }
        
        # Create comprehensive summary
        summary = {
            "batch_test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_jobs": len(job_postings),
                "total_models": len(available_models),
                "healthy_models": len(healthy_models),
                "blacklisted_models": len(self.blacklisted_models),
                "blacklisted_model_list": list(self.blacklisted_models),
                "total_tests": total_attempted,
                "total_successes": total_successes,
                "overall_success_rate": f"{success_rate:.1f}%",
                "model_statistics": model_stats
            },
            "blacklist_summary": {
                "blacklist_thresholds": {
                    "max_consecutive_failures": self.max_consecutive_failures,
                    "min_success_rate_threshold": self.min_success_rate_threshold
                },
                "blacklisted_models": list(self.blacklisted_models),
                "blacklist_reasons": {
                    model: self.model_health[model] for model in self.blacklisted_models 
                    if model in self.model_health
                }
            },
            "job_metadata": [{"job_id": j["job_id"], "job_title": j["job_title"], "source_file": j["source_file"]} for j in job_postings],
            "detailed_results": all_results
        }
        
        # Save comprehensive results
        summary_file = self.results_dir / "v16_batch_testing_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"✅ Batch testing complete: {total_successes}/{total_attempted} tests succeeded")
        logger.info(f"📊 Overall success rate: {success_rate:.1f}%") 
        logger.info(f"🚫 Models blacklisted: {len(self.blacklisted_models)}")
        if self.blacklisted_models:
            logger.info(f"⚫ Blacklisted models: {', '.join(self.blacklisted_models)}")
        logger.info(f"📊 Summary saved to {summary_file}")
        
        return summary

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="V16 Hybrid Batch Testing with Real Job Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Testing Modes:
  quick      : 3 jobs × 6 primary models (18 tests) - ~5-10 minutes
  medium     : 5 jobs × 12 selected models (60 tests) - ~15-25 minutes  
  comprehensive : 10 jobs × all 25 models (250 tests) - ~45-75 minutes
  full       : ALL jobs × all 25 models (EXTENSIVE) - 2-4+ hours

Examples:
  python3 v16_batch_real_data_testing.py quick
  python3 v16_batch_real_data_testing.py medium
  python3 v16_batch_real_data_testing.py comprehensive
  python3 v16_batch_real_data_testing.py full
  python3 v16_batch_real_data_testing.py --jobs 1 --models deepseek-r1:8b mistral-nemo:12b
        """
    )
    
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["quick", "medium", "comprehensive", "full"],
        default="quick",
        help="Testing mode (default: quick)"
    )
    
    parser.add_argument(
        "--jobs",
        type=int,
        help="Maximum number of jobs to test (overrides mode default)"
    )
    
    parser.add_argument(
        "--models",
        nargs="+",
        help="Specific models to test (overrides mode default)"
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
    if not (test_dir / "v16_hybrid_template.txt").exists():
        raise FileNotFoundError(
            f"V16 template not found. Please run from v16_testing directory.\n"
            f"Current directory: {test_dir}"
        )
    
    print("V16 Hybrid Batch Testing with Real Job Data")
    print("=" * 60)
    print(f"Test Directory: {test_dir}")
    print(f"Results Directory: {test_dir / 'batch_results'}")
    print(f"Testing Mode: {args.mode}")
    print()
    
    try:
        # Initialize tester
        tester = V16BatchTester(test_dir)
        
        # Configure testing parameters based on mode and arguments
        max_jobs = args.jobs  # Use explicit jobs argument if provided
        model_subset = args.models  # Use explicit models if provided
        
        if not max_jobs and not model_subset:
            # Apply mode defaults only if no explicit overrides
            if args.mode == "quick":
                max_jobs = 3
                model_subset = [
                    "deepseek-r1:8b", "mistral-nemo:12b", "qwen2.5:7b",
                    "dolphin3:8b", "phi4-mini-reasoning:latest", "llama3.2:latest"
                ]
                print("🧪 Quick validation: 3 jobs × 6 primary models...")
            elif args.mode == "medium":
                max_jobs = 5
                model_subset = [
                    "mistral-nemo:12b", "deepseek-r1:8b", "qwen2.5:7b", "dolphin3:8b",
                    "phi4-mini-reasoning:latest", "olmo2:latest", "gemma3n:latest", 
                    "granite3.1-moe:3b", "gemma3:4b", "phi3:3.8b", "qwen3:4b", "llama3.2:latest"
                ]
                print("🧪 Medium validation: 5 jobs × 12 selected models...")
            elif args.mode == "comprehensive":
                max_jobs = 10
                print("🚀 Comprehensive validation: 10 jobs × all 25 models...")
            elif args.mode == "full":
                print("🚀 FULL production test: ALL jobs × all 25 models...")
                print("⚠️  This will run hundreds or thousands of tests and take significant time!")
        else:
            # Custom configuration
            job_desc = f"{max_jobs or 'ALL'} jobs"
            model_desc = f"{len(model_subset) if model_subset else 'ALL'} models"
            print(f"🔧 Custom configuration: {job_desc} × {model_desc}")
        
        # Apply model subset if specified
        if model_subset:
            original_models = tester.models
            tester.models = model_subset
            print(f"📊 Using {len(model_subset)} selected models instead of all {len(original_models)}")
        
        if max_jobs:
            print(f"📊 Limited to first {max_jobs} jobs")
        
        print()
        
        # Run batch tests
        summary = tester.test_all_jobs_all_models(max_jobs=max_jobs)
        
        # Print summary
        batch_summary = summary["batch_test_summary"]
        print("\n🎉 V16 Batch Testing Summary")
        print("=" * 60)
        print(f"Total Jobs Tested: {batch_summary['total_jobs']}")
        print(f"Total Models Available: {batch_summary['total_models']}")
        print(f"Healthy Models: {batch_summary['healthy_models']}")
        print(f"Blacklisted Models: {batch_summary['blacklisted_models']}")
        if batch_summary['blacklisted_model_list']:
            print(f"  Blacklisted: {', '.join(batch_summary['blacklisted_model_list'])}")
        print(f"Total Tests: {batch_summary['total_tests']}")
        print(f"Successful Tests: {batch_summary['total_successes']}")
        print(f"Overall Success Rate: {batch_summary['overall_success_rate']}")
        
        print("\n📊 Model Performance:")
        for model, stats in batch_summary["model_statistics"].items():
            status = "🚫 BLACKLISTED" if stats.get('blacklisted', False) else "✅ Active"
            consecutive_failures = f" ({stats.get('consecutive_failures', 0)} consecutive failures)" if stats.get('consecutive_failures', 0) > 0 else ""
            print(f"  {model}: {stats['successes']}/{stats['total_tests']} ({stats['success_rate']:.1f}%) - Avg: {stats['avg_response_time']:.2f}s [{status}]{consecutive_failures}")
        
        print(f"\nDetailed results saved in: {test_dir / 'batch_results'}")
        print(f"Model health report: {test_dir / 'batch_results' / 'model_health_report.json'}")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
