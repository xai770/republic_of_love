#!/usr/bin/env python3
"""
V16 Hybrid Template Testing with Clean LLM Interface
=====================================================

Tests the V16 hybrid template across all available models using
the proven clean LLM interface adapted from V14.
"""

import json
import logging
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
logger = logging.getLogger('v16_hybrid_testing')

class V16HybridTester:
    """
    V16 hybrid template testing with clean model interface
    """
    
    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.results_dir = test_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Load V16 hybrid prompt
        prompt_file = test_dir / "v16_hybrid_template.txt"
        if not prompt_file.exists():
            raise FileNotFoundError(f"V16 hybrid template not found: {prompt_file}")
        
        self.hybrid_prompt = prompt_file.read_text().strip()
        logger.info(f"✅ Loaded V16 hybrid template ({len(self.hybrid_prompt)} chars)")
        
        # Load job posting content
        job_file = test_dir / "dws_business_analyst_posting.txt"
        if not job_file.exists():
            raise FileNotFoundError(f"Job posting not found: {job_file}")
        
        self.job_posting = job_file.read_text().strip()
        logger.info(f"✅ Loaded job posting ({len(self.job_posting)} chars)")
        
        # Initialize LLM interface
        self.llm_interface = V16LLMInterface()
        
        # Model list
        self.models = [
            "deepseek-r1:8b",
            "mistral-nemo:12b", 
            "qwen2.5:7b",
            "llama3.2:latest",
            "dolphin3:8b",
            "phi4-mini-reasoning:latest"
        ]
        
    def build_full_prompt(self) -> str:
        """Build the complete prompt with template and job posting"""
        return f"{self.hybrid_prompt}\n\n[JOB_POSTING]\n{self.job_posting}\n[/JOB_POSTING]"
    
    def test_single_model(self, model_name: str) -> Dict[str, Any]:
        """
        Test a single model with the V16 hybrid template
        
        Args:
            model_name: Name of the model to test
            
        Returns:
            Test result dictionary
        """
        logger.info(f"🧪 Testing {model_name} with V16 hybrid template...")
        
        # Build full prompt
        full_prompt = self.build_full_prompt()
        
        # Call model
        start_time = time.time()
        result = self.llm_interface.call_model(model_name, full_prompt)
        total_time = time.time() - start_time
        
        # Process result
        test_result = {
            "model": model_name,
            "timestamp": datetime.now().isoformat(),
            "success": result["success"],
            "total_time": total_time,
            "prompt_length": len(full_prompt)
        }
        
        if result["success"]:
            test_result.update({
                "response": result["response"],
                "response_length": len(result["response"]),
                "llm_time": result["elapsed_time"]
            })
            logger.info(f"✅ {model_name} - Success ({len(result['response'])} chars)")
        else:
            test_result.update({
                "error": result["error"],
                "llm_time": result.get("elapsed_time", 0)
            })
            logger.error(f"❌ {model_name} - Failed: {result['error']}")
        
        return test_result
    
    def save_result(self, result: Dict[str, Any]) -> None:
        """Save individual model result to file"""
        model_name = result["model"]
        safe_name = model_name.replace(":", "_").replace("/", "_")
        
        # Save detailed result
        result_file = self.results_dir / f"v16_{safe_name}_result.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Save clean response if successful
        if result["success"]:
            response_file = self.results_dir / f"v16_{safe_name}_response.md"
            with open(response_file, 'w') as f:
                f.write(f"# V16 Hybrid Template Result - {model_name}\n\n")
                f.write(f"**Timestamp:** {result['timestamp']}\n")
                f.write(f"**Total Time:** {result['total_time']:.1f}s\n")
                f.write(f"**LLM Time:** {result['llm_time']:.1f}s\n")
                f.write(f"**Response Length:** {result['response_length']} chars\n\n")
                f.write("## Extracted Job Description\n\n")
                f.write(result["response"])
        
        logger.info(f"💾 Saved {model_name} result to {result_file.name}")
    
    def test_all_models(self) -> Dict[str, Any]:
        """
        Test V16 hybrid template across all available models
        
        Returns:
            Summary of all test results
        """
        logger.info("🚀 Starting V16 hybrid template testing across all models...")
        
        # Test model availability first
        logger.info("🔍 Checking model availability...")
        availability = test_model_availability(self.models)
        available_models = [m for m, avail in availability.items() if avail]
        
        if not available_models:
            logger.error("❌ No models available for testing!")
            return {"success": False, "error": "No models available"}
        
        logger.info(f"✅ Found {len(available_models)} available models: {', '.join(available_models)}")
        
        # Test each available model
        results = []
        successes = 0
        
        for model in available_models:
            try:
                result = self.test_single_model(model)
                results.append(result)
                
                # Save individual result
                self.save_result(result)
                
                if result["success"]:
                    successes += 1
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error testing {model}: {e}")
                error_result = {
                    "model": model,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": f"Unexpected error: {e}",
                    "total_time": 0,
                    "llm_time": 0
                }
                results.append(error_result)
                self.save_result(error_result)
        
        # Generate summary
        summary = {
            "test_run": "V16 Hybrid Template Testing",
            "timestamp": datetime.now().isoformat(),
            "total_models": len(available_models),
            "successful_models": successes,
            "success_rate": f"{(successes/len(available_models)*100):.1f}%" if available_models else "0%",
            "results": results
        }
        
        # Save summary
        summary_file = self.results_dir / "v16_testing_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"✅ V16 testing complete: {successes}/{len(available_models)} models succeeded")
        logger.info(f"📊 Summary saved to {summary_file}")
        
        return summary

def main():
    """Main execution function"""
    test_dir = Path("/home/xai/Documents/ty_learn/v16_hybrid_framework/v16_testing")
    
    print("V16 Hybrid Template Testing")
    print("=" * 50)
    print(f"Test Directory: {test_dir}")
    print(f"Results Directory: {test_dir / 'results'}")
    print()
    
    try:
        # Initialize tester
        tester = V16HybridTester(test_dir)
        
        # Run tests
        summary = tester.test_all_models()
        
        # Print summary
        if summary.get("success", True):  # Default to True if not specified
            print("\n🎉 V16 Hybrid Template Testing Summary")
            print("=" * 50)
            print(f"Total Models: {summary['total_models']}")
            print(f"Successful: {summary['successful_models']}")
            print(f"Success Rate: {summary['success_rate']}")
            print(f"\nDetailed results saved in: {test_dir / 'results'}")
        else:
            print(f"\n❌ Testing failed: {summary.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
