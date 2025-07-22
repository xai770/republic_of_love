#!/usr/bin/env python3
"""
Automated LLM Model Optimization Framework
==========================================

Self-improving LLM testing system with interviewer-guided optimization.
Implements iterative prompt refinement through LLM-to-LLM conversations.

Author: Arden
Version: 1.0
Date: 2025-07-20
"""

import json
import time
import uuid
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelTestSession:
    """Single model testing session with iterative optimization"""
    
    def __init__(self, 
                 model_name: str,
                 test_case: Dict[str, Any],
                 interviewer_model: str = "llama3.2:latest",
                 max_iterations: int = 5,
                 storage_dir: str = "llm_optimization_results"):
        """
        Initialize testing session
        
        Args:
            model_name: Model to test (e.g., "deepseek-r1:8b")
            test_case: Test case with input/expected output
            interviewer_model: Model to conduct interviews (default: llama3.2:latest)
            max_iterations: Maximum optimization iterations
            storage_dir: Directory to store results
        """
        self.model_name = model_name
        self.test_case = test_case
        self.interviewer_model = interviewer_model
        self.max_iterations = max_iterations
        self.storage_dir = Path(storage_dir)
        
        # Create session directory
        self.session_id = str(uuid.uuid4())[:8]
        self.session_dir = self.storage_dir / f"session_{self.session_id}_{model_name.replace(':', '_')}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize session data
        self.session_data = {
            "session_id": self.session_id,
            "model_name": model_name,
            "interviewer_model": interviewer_model,
            "test_case": test_case,
            "start_time": datetime.now().isoformat(),
            "iterations": [],
            "final_results": {}
        }
        
        logger.info(f"🚀 Started optimization session for {model_name} in {self.session_dir}")
    
    def run_optimization(self) -> Dict[str, Any]:
        """
        Run the complete optimization cycle
        
        Returns:
            Final optimization results
        """
        logger.info(f"🔬 Starting optimization for {self.model_name}")
        
        current_prompt = self.test_case["original_prompt"]
        best_score = 0.0
        best_prompt = current_prompt
        
        for iteration in range(self.max_iterations):
            logger.info(f"📊 Iteration {iteration + 1}/{self.max_iterations}")
            
            # Run test with current prompt
            test_result = self._run_test(current_prompt, iteration)
            
            # Evaluate results
            score = self._evaluate_output(test_result["output"], self.test_case["expected_output"])
            test_result["score"] = score
            
            logger.info(f"📈 Iteration {iteration + 1} score: {score:.2f}")
            
            # Update best if improved
            if score > best_score:
                best_score = score
                best_prompt = current_prompt
                logger.info(f"🎉 New best score: {score:.2f}")
            
            # Store iteration data
            self.session_data["iterations"].append(test_result)
            self._save_session_data()
            
            # Check if we should continue
            if score >= 0.95:  # 95% success threshold
                logger.info(f"✅ Optimization complete - achieved target score: {score:.2f}")
                break
            
            if iteration < self.max_iterations - 1:  # Don't interview after last iteration
                # Conduct interview for improvement
                interview_result = self._conduct_interview(current_prompt, test_result)
                
                if interview_result["has_improvement"]:
                    current_prompt = interview_result["improved_prompt"]
                    logger.info("🔄 Using improved prompt for next iteration")
                else:
                    logger.info("🛑 No improvement suggested - stopping optimization")
                    break
        
        # Finalize results
        self.session_data["final_results"] = {
            "best_score": best_score,
            "best_prompt": best_prompt,
            "total_iterations": len(self.session_data["iterations"]),
            "end_time": datetime.now().isoformat(),
            "optimization_successful": best_score >= 0.8
        }
        
        self._save_session_data()
        self._generate_final_report()
        
        logger.info(f"🏁 Optimization complete for {self.model_name} - Best score: {best_score:.2f}")
        return self.session_data["final_results"]
    
    def _run_test(self, prompt: str, iteration: int) -> Dict[str, Any]:
        """Run a single test with the given prompt"""
        logger.info(f"🧪 Running test iteration {iteration + 1}")
        
        # Prepare full prompt with test input
        full_prompt = prompt.replace("{job_title}", self.test_case["job_title"])
        full_prompt = full_prompt.replace("{job_description}", self.test_case["job_description"])
        
        start_time = time.time()
        
        try:
            # Call Ollama with the model
            result = subprocess.run(
                ['ollama', 'run', self.model_name],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            processing_time = time.time() - start_time
            
            if result.returncode == 0:
                output = result.stdout.strip()
                success = True
                error_message = None
            else:
                output = result.stderr.strip()
                success = False
                error_message = f"Process failed with return code {result.returncode}"
                
        except subprocess.TimeoutExpired:
            processing_time = time.time() - start_time
            output = ""
            success = False
            error_message = "Timeout expired"
        except Exception as e:
            processing_time = time.time() - start_time
            output = ""
            success = False
            error_message = str(e)
        
        test_result = {
            "iteration": iteration + 1,
            "prompt": prompt,
            "full_prompt": full_prompt,
            "output": output,
            "processing_time": processing_time,
            "success": success,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save individual test result
        test_file = self.session_dir / f"test_iteration_{iteration + 1}.json"
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_result, f, indent=2, ensure_ascii=False)
        
        return test_result
    
    def _evaluate_output(self, actual_output: str, expected_output: Dict[str, str]) -> float:
        """
        Evaluate how well the actual output matches expected output
        
        Returns:
            Score between 0.0 and 1.0
        """
        try:
            # Try to parse as JSON (for skills extraction)
            if "technical_requirements" in str(expected_output):
                return self._evaluate_skills_extraction(actual_output, expected_output)
            else:
                # For concise descriptions, use text similarity
                return self._evaluate_text_similarity(actual_output, expected_output)
        except Exception as e:
            logger.warning(f"Evaluation error: {e}")
            return 0.0
    
    def _evaluate_skills_extraction(self, actual_output: str, expected_output: Dict[str, str]) -> float:
        """Evaluate skills extraction output"""
        try:
            # Extract JSON from the output
            import re
            json_match = re.search(r'\\{.*\\}', actual_output, re.DOTALL)
            if not json_match:
                return 0.0
            
            actual_data = json.loads(json_match.group())
            
            # Check if all required keys are present
            required_keys = ["technical_requirements", "business_requirements", "soft_skills", 
                           "experience_requirements", "education_requirements"]
            
            score = 0.0
            for key in required_keys:
                if key in actual_data and actual_data[key]:
                    score += 0.2  # Each field worth 20%
            
            return score
            
        except Exception:
            return 0.0
    
    def _evaluate_text_similarity(self, actual_output: str, expected_pattern: str) -> float:
        """Evaluate text similarity for concise descriptions"""
        # Simple similarity check - can be enhanced with more sophisticated NLP
        actual_lower = actual_output.lower()
        expected_lower = str(expected_pattern).lower()
        
        # Check if output is reasonable length
        if not (20 <= len(actual_output) <= 500):
            return 0.2
        
        # Check for key components
        score = 0.5  # Base score for reasonable length
        
        # Check for professional language indicators
        professional_words = ["manages", "implements", "coordinates", "develops", "analyzes"]
        if any(word in actual_lower for word in professional_words):
            score += 0.3
        
        # Check for appropriate structure
        if 2 <= len(actual_output.split('. ')) <= 4:  # 2-4 sentences
            score += 0.2
        
        return min(score, 1.0)
    
    def _conduct_interview(self, current_prompt: str, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct interview between interviewer and candidate model
        
        Returns:
            Interview results with improvement suggestions
        """
        logger.info("🎤 Conducting interview for prompt improvement")
        
        interview_prompt = f'''
You are an expert LLM optimization consultant. You need to analyze why a model didn't perform well and suggest improvements to the prompt.

CONTEXT:
- Model being tested: {self.model_name}
- Task: {self.test_case.get("task_description", "Skills extraction from job postings")}
- Current prompt: {current_prompt}
- Model output: {test_result["output"]}
- Expected output type: {self.test_case.get("expected_format", "JSON with skills categories")}
- Performance score: {test_result.get("score", 0):.2f}/1.0

ANALYSIS NEEDED:
1. What went wrong with the current prompt?
2. How can the prompt be improved?
3. What specific changes would help this model perform better?

Please provide:
1. Brief analysis of the issues
2. Specific improved prompt (complete, ready to use)
3. Reasoning for the changes

Format your response as:
ANALYSIS: [your analysis]
IMPROVED_PROMPT: [complete improved prompt]
REASONING: [why these changes should help]
'''
        
        try:
            # Get interviewer's analysis
            result = subprocess.run(
                ['ollama', 'run', self.interviewer_model],
                input=interview_prompt,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                interview_response = result.stdout.strip()
                
                # Parse the interview response
                improved_prompt = self._extract_improved_prompt(interview_response)
                
                interview_result = {
                    "interviewer_model": self.interviewer_model,
                    "interview_prompt": interview_prompt,
                    "interview_response": interview_response,
                    "improved_prompt": improved_prompt,
                    "has_improvement": bool(improved_prompt and improved_prompt != current_prompt),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Save interview data
                interview_file = self.session_dir / f"interview_{len(self.session_data['iterations'])}.json"
                with open(interview_file, 'w', encoding='utf-8') as f:
                    json.dump(interview_result, f, indent=2, ensure_ascii=False)
                
                return interview_result
            else:
                logger.error(f"Interview failed: {result.stderr}")
                return {"has_improvement": False, "error": result.stderr}
                
        except Exception as e:
            logger.error(f"Interview error: {e}")
            return {"has_improvement": False, "error": str(e)}
    
    def _extract_improved_prompt(self, interview_response: str) -> Optional[str]:
        """Extract the improved prompt from interview response"""
        try:
            # Look for IMPROVED_PROMPT section
            if "IMPROVED_PROMPT:" in interview_response:
                sections = interview_response.split("IMPROVED_PROMPT:")
                if len(sections) > 1:
                    prompt_section = sections[1].split("REASONING:")[0].strip()
                    return prompt_section
            
            return None
        except Exception:
            return None
    
    def _save_session_data(self):
        """Save session data to file"""
        session_file = self.session_dir / "session_data.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)
    
    def _generate_final_report(self):
        """Generate final optimization report"""
        report_content = f"""# LLM Optimization Report

**Model:** {self.model_name}  
**Session ID:** {self.session_id}  
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Results Summary

- **Best Score:** {self.session_data['final_results']['best_score']:.2f}/1.0
- **Total Iterations:** {self.session_data['final_results']['total_iterations']}
- **Optimization Successful:** {self.session_data['final_results']['optimization_successful']}

## Best Prompt

```
{self.session_data['final_results']['best_prompt']}
```

## Iteration History

"""
        
        for i, iteration in enumerate(self.session_data["iterations"], 1):
            report_content += f"### Iteration {i}\n"
            report_content += f"- **Score:** {iteration.get('score', 0):.2f}\n"
            report_content += f"- **Processing Time:** {iteration['processing_time']:.2f}s\n"
            report_content += f"- **Success:** {iteration['success']}\n\n"
        
        report_file = self.session_dir / "optimization_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)


class LLMOptimizationSuite:
    """Complete LLM optimization suite for multiple models"""
    
    def __init__(self, storage_dir: str = "llm_optimization_results"):
        """Initialize optimization suite"""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
    
    def run_optimization_suite(self, 
                             models_to_test: List[str],
                             test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run optimization for multiple models and test cases
        
        Args:
            models_to_test: List of model names to test
            test_cases: List of test cases to run
            
        Returns:
            Complete optimization results
        """
        logger.info(f"🚀 Starting optimization suite for {len(models_to_test)} models")
        
        suite_results = {
            "suite_id": str(uuid.uuid4())[:8],
            "start_time": datetime.now().isoformat(),
            "models_tested": models_to_test,
            "test_cases": test_cases,
            "model_results": {},
            "summary": {}
        }
        
        for model_name in models_to_test:
            logger.info(f"🔬 Testing model: {model_name}")
            model_results = []
            
            for i, test_case in enumerate(test_cases):
                logger.info(f"📋 Running test case {i + 1}/{len(test_cases)} for {model_name}")
                
                session = ModelTestSession(
                    model_name=model_name,
                    test_case=test_case,
                    storage_dir=str(self.storage_dir)
                )
                
                test_result = session.run_optimization()
                model_results.append(test_result)
            
            suite_results["model_results"][model_name] = model_results
        
        # Generate summary
        suite_results["summary"] = self._generate_suite_summary(suite_results)
        suite_results["end_time"] = datetime.now().isoformat()
        
        # Save suite results
        suite_file = self.storage_dir / f"optimization_suite_{suite_results['suite_id']}.json"
        with open(suite_file, 'w', encoding='utf-8') as f:
            json.dump(suite_results, f, indent=2, ensure_ascii=False)
        
        logger.info("🏁 Optimization suite complete!")
        return suite_results
    
    def _generate_suite_summary(self, suite_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of suite results"""
        summary = {
            "best_model": None,
            "best_average_score": 0.0,
            "model_rankings": []
        }
        
        for model_name, results in suite_results["model_results"].items():
            avg_score = sum(r["best_score"] for r in results) / len(results)
            
            summary["model_rankings"].append({
                "model": model_name,
                "average_score": avg_score,
                "successful_optimizations": sum(1 for r in results if r["optimization_successful"])
            })
            
            if avg_score > summary["best_average_score"]:
                summary["best_average_score"] = avg_score
                summary["best_model"] = model_name
        
        # Sort rankings by score
        summary["model_rankings"].sort(key=lambda x: x["average_score"], reverse=True)
        
        return summary


def create_test_cases_from_ty_extract() -> List[Dict[str, Any]]:
    """Create test cases based on ty_extract implementation"""
    
    return [
        {
            "task_description": "Skills extraction from job posting",
            "job_title": "Software Engineer",
            "job_description": """We are looking for a skilled software engineer with experience in Python, JavaScript, and cloud technologies. The ideal candidate should have strong problem-solving skills and be able to work in an agile environment. Requirements include 3+ years of experience, Bachelor's degree in Computer Science, and experience with AWS.""",
            "original_prompt": """Analyze this job posting and extract skills in exactly this JSON format:

Job Title: {job_title}
Job Description: {job_description}

Please extract and categorize skills into:
1. Technical Skills: Programming languages, software, tools, technologies
2. Business Skills: Domain knowledge, processes, methodologies, business functions
3. Soft Skills: Communication, leadership, teamwork, problem-solving abilities
4. Experience Requirements: Years of experience, specific backgrounds, levels
5. Education Requirements: Degrees, certifications, qualifications

Return ONLY a JSON object with these exact keys:
{
    "technical_requirements": "skill1; skill2; skill3",
    "business_requirements": "skill1; skill2; skill3", 
    "soft_skills": "skill1; skill2; skill3",
    "experience_requirements": "req1; req2; req3",
    "education_requirements": "req1; req2; req3"
}

Extract real skills mentioned in the job description. Use semicolon separation. Be specific and accurate.""",
            "expected_output": {
                "technical_requirements": "Python; JavaScript; AWS; Cloud technologies",
                "business_requirements": "Agile methodology; Software development",
                "soft_skills": "Problem-solving; Teamwork",
                "experience_requirements": "3+ years software engineering experience",
                "education_requirements": "Bachelor's degree in Computer Science"
            },
            "expected_format": "JSON with skills categories"
        },
        {
            "task_description": "Concise description generation",
            "job_title": "Data Analyst", 
            "job_description": """Join our team as a Data Analyst where you will be responsible for analyzing large datasets, creating reports, and providing insights to support business decisions. You will work closely with stakeholders to understand requirements and deliver actionable recommendations.""",
            "original_prompt": """Analyze this job posting and create a concise, professional summary that captures the key responsibilities and role overview.

Job Title: {job_title}
Job Description: {job_description}

Instructions:
1. Create a 2-3 sentence summary of the main responsibilities
2. Focus on what the person will actually DO in this role
3. Include the most important aspects of the job
4. Keep it professional and clear
5. Return ONLY the summary text, no additional formatting

Summary:""",
            "expected_output": "Analyzes large datasets and creates reports to provide actionable insights for business decisions. Works collaboratively with stakeholders to understand requirements and deliver data-driven recommendations.",
            "expected_format": "2-3 sentence professional summary"
        }
    ]


if __name__ == "__main__":
    # Example usage
    print("🚀 LLM Optimization Framework - Automated Testing")
    
    # Models to test (check what's available locally)
    models_to_test = [
        "gemma3n:latest",
        "deepseek-r1:8b", 
        "llama3.2:latest",
        "qwen2.5:7b"
    ]
    
    # Create test cases
    test_cases = create_test_cases_from_ty_extract()
    
    # Run optimization suite
    optimization_suite = LLMOptimizationSuite("llm_optimization_results")
    results = optimization_suite.run_optimization_suite(models_to_test, test_cases)
    
    # Print summary
    print("\\n🏆 OPTIMIZATION RESULTS:")
    print(f"Best Model: {results['summary']['best_model']}")
    print(f"Best Average Score: {results['summary']['best_average_score']:.2f}")
    
    print("\\n📊 Model Rankings:")
    for ranking in results['summary']['model_rankings']:
        print(f"  {ranking['model']}: {ranking['average_score']:.2f} avg score")
