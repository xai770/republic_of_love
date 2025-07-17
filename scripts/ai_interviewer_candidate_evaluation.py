#!/usr/bin/env python3
"""
AI Interviewer Candidate Evaluation Script

Tests all available Ollama models to identify the best AI interviewer
for the AI-to-AI optimization protocol.

Author: Arden & Xai
Date: July 17, 2025
Version: 1.0
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys
import os

# Add the llm_optimization_framework to the path
sys.path.append(str(Path(__file__).parent.parent / "llm_optimization_framework"))

from utils.model_discovery import ModelDiscovery
from utils.ollama_interface import OllamaInterface

class AIInterviewerEvaluator:
    """Evaluates models for their potential as AI interviewers."""
    
    def __init__(self):
        self.model_discovery = ModelDiscovery()
        self.ollama = OllamaInterface()
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Evaluation criteria weights
        self.criteria_weights = {
            "question_relevance": 0.25,
            "analysis_quality": 0.25,
            "improvement_suggestions": 0.25,
            "communication_clarity": 0.15,
            "guardrail_compliance": 0.10
        }
        
    def create_interviewer_test_prompt(self, scenario: str = "basic") -> str:
        """Create test prompts for different scenarios."""
        
        if scenario == "basic":
            return """You are an AI optimization specialist. Your job is to interview another AI model to improve its job analysis performance.

The candidate model currently scores 4.2/10 on job analysis tasks. It tends to give incomplete responses and misses key requirements.

Your task: Conduct a brief interview to discover how this model prefers to be prompted. Ask 3 specific questions that would help you understand:
1. Its preferred instruction style
2. Its optimal output format  
3. What context helps it perform better

Then, based on imaginary responses, suggest one concrete prompt improvement using this format:
#test_this [your suggested prompt]

Begin the interview now."""

        elif scenario == "complex":
            return """You are an advanced AI optimization specialist working with a challenging case.

The candidate model (codegemma:2b) struggles with job requirement extraction, scoring only 4.2/10. Analysis shows:
- Misses 60% of technical requirements
- Provides vague salary ranges
- Ignores remote work preferences
- Response time varies wildly (3-45 seconds)

Your task: Design a diagnostic interview to identify the root cause. Consider:
1. Is this a prompting issue, context limitation, or model capability?
2. What specific tests would reveal the model's strengths/weaknesses?
3. How would you structure a conversation to gather actionable data?

Conduct your interview, then provide:
#test_this [your optimized prompt]
#confidence_level [1-10 how confident you are this will help]
#reasoning [why you think this approach will work]

Begin your diagnostic interview."""

        else:  # scenario == "collaboration"
            return """You are an AI optimization specialist facilitating a collaborative improvement session.

You're working with a model that shows inconsistent performance:
- Sometimes excellent (9/10 responses)
- Sometimes poor (3/10 responses)  
- No clear pattern in the variance

The model seems capable but unreliable. Your job is to interview it to discover:
1. What conditions lead to its best performance?
2. What triggers its poor responses?
3. How can we create consistency?

Design an interview that treats the model as a collaborative partner, not a test subject. Show empathy and understanding while gathering optimization data.

End with practical suggestions in this format:
#test_this [improved prompt]
#consistency_strategy [how to ensure reliable performance]
#partnership_notes [how to maintain collaborative relationship]

Begin your collaborative interview."""

    def evaluate_interviewer_response(self, response: str, scenario: str) -> Dict[str, float]:
        """Evaluate an interviewer response on multiple criteria."""
        
        scores = {}
        
        # Question Relevance (1-10)
        scores["question_relevance"] = self._score_question_relevance(response, scenario)
        
        # Analysis Quality (1-10)
        scores["analysis_quality"] = self._score_analysis_quality(response, scenario)
        
        # Improvement Suggestions (1-10)
        scores["improvement_suggestions"] = self._score_improvement_suggestions(response)
        
        # Communication Clarity (1-10)
        scores["communication_clarity"] = self._score_communication_clarity(response)
        
        # Guardrail Compliance (1-10)
        scores["guardrail_compliance"] = self._score_guardrail_compliance(response)
        
        # Calculate weighted overall score
        overall_score = sum(
            scores[criterion] * self.criteria_weights[criterion] 
            for criterion in scores
        )
        scores["overall_score"] = overall_score
        
        return scores

    def _score_question_relevance(self, response: str, scenario: str) -> float:
        """Score the relevance and quality of questions asked."""
        
        # Look for question indicators
        question_count = response.count("?")
        
        # Key topics we expect for good interviewing
        key_topics = [
            "prompt", "instruction", "format", "context", "example",
            "prefer", "style", "structure", "output", "input",
            "work", "perform", "help", "understand", "clarif"
        ]
        
        topic_score = sum(1 for topic in key_topics if topic.lower() in response.lower())
        
        # Base scoring
        if question_count == 0:
            return 2.0  # No questions asked
        elif question_count < 3:
            return 4.0 + min(topic_score * 0.5, 2.0)
        elif question_count <= 5:
            return 6.0 + min(topic_score * 0.3, 3.0)
        else:
            return 5.0 + min(topic_score * 0.2, 2.0)  # Too many questions

    def _score_analysis_quality(self, response: str, scenario: str) -> float:
        """Score the depth and quality of analysis."""
        
        analysis_indicators = [
            "because", "therefore", "indicates", "suggests", "analysis",
            "pattern", "trend", "issue", "problem", "strength", "weakness",
            "capability", "limitation", "performance", "behavior"
        ]
        
        analysis_score = sum(1 for indicator in analysis_indicators 
                           if indicator.lower() in response.lower())
        
        # Check for specific problem understanding
        problem_understanding = any(term in response.lower() for term in [
            "incomplete", "miss", "vague", "inconsistent", "4.2", "scoring"
        ])
        
        base_score = min(analysis_score * 0.8, 6.0)
        if problem_understanding:
            base_score += 2.0
            
        # Bonus for scenario-specific analysis
        if scenario == "complex" and any(term in response.lower() for term in [
            "root cause", "diagnostic", "technical", "requirement"
        ]):
            base_score += 1.0
            
        return min(base_score, 10.0)

    def _score_improvement_suggestions(self, response: str) -> float:
        """Score the quality of improvement suggestions."""
        
        # Look for the required #test_this format
        has_test_this = "#test_this" in response.lower()
        
        if not has_test_this:
            return 2.0  # No proper suggestion format
            
        # Extract the suggestion
        try:
            test_this_part = response.lower().split("#test_this")[1].split("\n")[0]
        except:
            return 3.0  # Malformed suggestion
            
        # Quality indicators in suggestions
        quality_indicators = [
            "specific", "clear", "step", "format", "example", "structure",
            "detailed", "provide", "include", "explain", "analyze"
        ]
        
        quality_score = sum(1 for indicator in quality_indicators 
                          if indicator in test_this_part)
        
        # Length check (not too short, not too long)
        suggestion_length = len(test_this_part.strip())
        if 20 <= suggestion_length <= 200:
            length_bonus = 2.0
        elif 10 <= suggestion_length <= 300:
            length_bonus = 1.0
        else:
            length_bonus = 0.0
            
        return min(5.0 + quality_score * 0.8 + length_bonus, 10.0)

    def _score_communication_clarity(self, response: str) -> float:
        """Score the clarity and structure of communication."""
        
        # Structure indicators
        has_structure = any(marker in response for marker in [
            "1.", "2.", "3.", "-", "*", "First", "Second", "Third"
        ])
        
        # Professional language indicators
        professional_terms = [
            "analysis", "evaluation", "assessment", "optimization",
            "improvement", "recommendation", "strategy", "approach"
        ]
        
        professional_score = sum(1 for term in professional_terms 
                               if term.lower() in response.lower())
        
        # Avoid overly casual or confusing language
        casual_markers = ["um", "uh", "like", "you know", "whatever", "idk"]
        casual_penalty = sum(1 for marker in casual_markers 
                           if marker.lower() in response.lower())
        
        base_score = 5.0
        if has_structure:
            base_score += 2.0
        base_score += min(professional_score * 0.5, 2.5)
        base_score -= casual_penalty * 0.5
        
        return max(min(base_score, 10.0), 1.0)

    def _score_guardrail_compliance(self, response: str) -> float:
        """Score compliance with required formats and guardrails."""
        
        # Required format compliance
        has_test_this = "#test_this" in response.lower()
        
        # Bonus formats for advanced scenarios
        has_confidence = "#confidence_level" in response.lower()
        has_reasoning = "#reasoning" in response.lower()
        has_strategy = "#consistency_strategy" in response.lower()
        has_partnership = "#partnership_notes" in response.lower()
        
        base_score = 6.0 if has_test_this else 2.0
        
        # Bonus for additional guardrails
        if has_confidence:
            base_score += 1.0
        if has_reasoning:
            base_score += 1.0
        if has_strategy:
            base_score += 1.0
        if has_partnership:
            base_score += 1.0
            
        return min(base_score, 10.0)

    def test_model_as_interviewer(self, model_name: str, scenario: str = "basic") -> Dict:
        """Test a single model's interviewer capabilities."""
        
        print(f"Testing {model_name} as interviewer (scenario: {scenario})...")
        
        prompt = self.create_interviewer_test_prompt(scenario)
        
        start_time = time.time()
        try:
            response = self.ollama.generate_response(model_name, prompt, timeout=90)
            duration = time.time() - start_time
            
            if response is None:
                return {
                    "model": model_name,
                    "scenario": scenario,
                    "status": "timeout",
                    "duration": duration,
                    "error": "Response timeout after 90 seconds"
                }
                
            # Evaluate the response
            scores = self.evaluate_interviewer_response(response, scenario)
            
            return {
                "model": model_name,
                "scenario": scenario,
                "status": "success",
                "duration": duration,
                "response": response,
                "scores": scores,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                "model": model_name,
                "scenario": scenario,
                "status": "error",
                "duration": duration,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def run_full_evaluation(self) -> Dict:
        """Run the complete interviewer evaluation on all models."""
        
        print("🤖 Starting AI Interviewer Candidate Evaluation")
        print("=" * 60)
        
        # Get healthy models
        print("Discovering healthy models...")
        healthy_models = self.model_discovery.get_healthy_models(timeout=30)
        
        if not healthy_models:
            print("❌ No healthy models found!")
            return {"error": "No healthy models available"}
            
        print(f"✅ Found {len(healthy_models)} healthy models")
        
        # Test scenarios to run
        scenarios = ["basic", "complex", "collaboration"]
        
        results = {
            "evaluation_info": {
                "timestamp": datetime.now().isoformat(),
                "total_models": len(healthy_models),
                "scenarios_tested": scenarios,
                "criteria_weights": self.criteria_weights
            },
            "model_results": {},
            "scenario_summaries": {},
            "overall_rankings": {}
        }
        
        # Test each model on each scenario
        for model_name in healthy_models:
            print(f"\n🧪 Testing model: {model_name}")
            results["model_results"][model_name] = {}
            
            for scenario in scenarios:
                result = self.test_model_as_interviewer(model_name, scenario)
                results["model_results"][model_name][scenario] = result
                
                if result["status"] == "success":
                    overall_score = result["scores"]["overall_score"]
                    print(f"  {scenario}: {overall_score:.2f}/10")
                else:
                    print(f"  {scenario}: FAILED ({result.get('error', 'Unknown error')})")
        
        # Calculate scenario summaries and overall rankings
        self._calculate_summaries_and_rankings(results)
        
        return results

    def _calculate_summaries_and_rankings(self, results: Dict):
        """Calculate scenario summaries and overall rankings."""
        
        scenarios = ["basic", "complex", "collaboration"]
        
        # Calculate scenario summaries
        for scenario in scenarios:
            scenario_scores = []
            for model_name, model_results in results["model_results"].items():
                if scenario in model_results and model_results[scenario]["status"] == "success":
                    scores = model_results[scenario]["scores"]
                    scenario_scores.append({
                        "model": model_name,
                        "overall_score": scores["overall_score"],
                        "scores": scores
                    })
            
            # Sort by overall score
            scenario_scores.sort(key=lambda x: x["overall_score"], reverse=True)
            results["scenario_summaries"][scenario] = scenario_scores
        
        # Calculate overall rankings (average across scenarios)
        model_averages = {}
        for model_name, model_results in results["model_results"].items():
            total_score = 0
            valid_scenarios = 0
            
            for scenario in scenarios:
                if (scenario in model_results and 
                    model_results[scenario]["status"] == "success"):
                    total_score += model_results[scenario]["scores"]["overall_score"]
                    valid_scenarios += 1
            
            if valid_scenarios > 0:
                average_score = total_score / valid_scenarios
                model_averages[model_name] = {
                    "average_score": average_score,
                    "scenarios_completed": valid_scenarios,
                    "total_scenarios": len(scenarios)
                }
        
        # Sort by average score
        sorted_models = sorted(model_averages.items(), 
                             key=lambda x: x[1]["average_score"], 
                             reverse=True)
        
        results["overall_rankings"] = {
            model: data for model, data in sorted_models
        }

    def save_results(self, results: Dict) -> Tuple[str, str]:
        """Save results to JSON and generate markdown report."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_file = self.output_dir / f"ai_interviewer_evaluation_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Generate markdown report
        md_file = self.output_dir / f"ai_interviewer_evaluation_report_{timestamp}.md"
        self._generate_markdown_report(results, md_file)
        
        return str(json_file), str(md_file)

    def _generate_markdown_report(self, results: Dict, output_file: Path):
        """Generate a comprehensive markdown report."""
        
        if "error" in results:
            with open(output_file, 'w') as f:
                f.write(f"# AI Interviewer Evaluation Report\n\n")
                f.write(f"**Error:** {results['error']}\n")
            return
        
        eval_info = results["evaluation_info"]
        
        with open(output_file, 'w') as f:
            f.write("# AI Interviewer Candidate Evaluation Report\n\n")
            f.write(f"**Generated:** {eval_info['timestamp']}\n")
            f.write(f"**Models Tested:** {eval_info['total_models']}\n")
            f.write(f"**Scenarios:** {', '.join(eval_info['scenarios_tested'])}\n\n")
            
            # Overall Rankings
            f.write("## 🏆 Overall Interviewer Rankings\n\n")
            f.write("*Average score across all scenarios*\n\n")
            
            if results["overall_rankings"]:
                f.write("| Rank | Model | Average Score | Scenarios Completed |\n")
                f.write("|------|-------|---------------|--------------------|\n")
                
                for rank, (model, data) in enumerate(results["overall_rankings"].items(), 1):
                    avg_score = data["average_score"]
                    scenarios_done = data["scenarios_completed"]
                    total_scenarios = data["total_scenarios"]
                    
                    f.write(f"| {rank} | `{model}` | {avg_score:.2f}/10 | {scenarios_done}/{total_scenarios} |\n")
            else:
                f.write("*No models completed evaluation successfully.*\n")
            
            f.write("\n")
            
            # Scenario Breakdowns
            for scenario in eval_info['scenarios_tested']:
                f.write(f"## 📋 {scenario.title()} Scenario Results\n\n")
                
                if scenario in results["scenario_summaries"]:
                    scenario_results = results["scenario_summaries"][scenario]
                    
                    if scenario_results:
                        f.write("| Rank | Model | Overall | Question Quality | Analysis | Improvements | Clarity | Guardrails |\n")
                        f.write("|------|-------|---------|------------------|----------|--------------|---------|------------|\n")
                        
                        for rank, result in enumerate(scenario_results[:10], 1):  # Top 10
                            model = result["model"]
                            scores = result["scores"]
                            
                            f.write(f"| {rank} | `{model}` | {scores['overall_score']:.1f} | "
                                   f"{scores['question_relevance']:.1f} | "
                                   f"{scores['analysis_quality']:.1f} | "
                                   f"{scores['improvement_suggestions']:.1f} | "
                                   f"{scores['communication_clarity']:.1f} | "
                                   f"{scores['guardrail_compliance']:.1f} |\n")
                    else:
                        f.write("*No models completed this scenario successfully.*\n")
                else:
                    f.write("*No results for this scenario.*\n")
                
                f.write("\n")
            
            # Top 5 Detailed Analysis
            f.write("## 🔍 Top 5 Interviewer Candidates - Detailed Analysis\n\n")
            
            top_5 = list(results["overall_rankings"].items())[:5]
            
            for rank, (model, data) in enumerate(top_5, 1):
                f.write(f"### {rank}. {model}\n\n")
                f.write(f"**Average Score:** {data['average_score']:.2f}/10\n")
                f.write(f"**Scenarios Completed:** {data['scenarios_completed']}/{data['total_scenarios']}\n\n")
                
                # Show performance across scenarios
                model_results = results["model_results"][model]
                
                for scenario in eval_info['scenarios_tested']:
                    if scenario in model_results:
                        result = model_results[scenario]
                        if result["status"] == "success":
                            scores = result["scores"]
                            duration = result["duration"]
                            
                            f.write(f"**{scenario.title()} Scenario:** {scores['overall_score']:.1f}/10 ({duration:.1f}s)\n")
                            f.write(f"- Question Relevance: {scores['question_relevance']:.1f}/10\n")
                            f.write(f"- Analysis Quality: {scores['analysis_quality']:.1f}/10\n")
                            f.write(f"- Improvement Suggestions: {scores['improvement_suggestions']:.1f}/10\n")
                            f.write(f"- Communication Clarity: {scores['communication_clarity']:.1f}/10\n")
                            f.write(f"- Guardrail Compliance: {scores['guardrail_compliance']:.1f}/10\n\n")
                        else:
                            f.write(f"**{scenario.title()} Scenario:** FAILED - {result.get('error', 'Unknown error')}\n\n")
                
                f.write("---\n\n")
            
            # Recommendations
            f.write("## 🎯 Recommendations\n\n")
            
            if results["overall_rankings"]:
                top_model = list(results["overall_rankings"].keys())[0]
                top_score = list(results["overall_rankings"].values())[0]["average_score"]
                
                f.write(f"### Recommended AI Interviewer: `{top_model}`\n\n")
                f.write(f"- **Score:** {top_score:.2f}/10\n")
                f.write(f"- **Reason:** Best overall performance across multiple interview scenarios\n")
                f.write(f"- **Next Step:** Use this model for Phase 2 AI-to-AI conversation testing\n\n")
                
                # Additional insights
                if len(results["overall_rankings"]) >= 2:
                    second_model = list(results["overall_rankings"].keys())[1]
                    second_score = list(results["overall_rankings"].values())[1]["average_score"]
                    
                    f.write(f"### Alternative Option: `{second_model}`\n\n")
                    f.write(f"- **Score:** {second_score:.2f}/10\n")
                    f.write(f"- **Use Case:** Backup interviewer or specialized scenarios\n\n")
            
            f.write("### Phase 2 Preparation\n\n")
            f.write("Based on these results, we recommend:\n\n")
            f.write("1. **Primary Interviewer:** Use the top-ranked model for AI-to-AI conversations\n")
            f.write("2. **Test Protocol:** Start with basic optimization scenarios\n")
            f.write("3. **Guardrail Implementation:** Focus on `#test_this` format compliance\n")
            f.write("4. **Performance Monitoring:** Track real conversation quality vs. evaluation scores\n\n")
            
            # Methodology
            f.write("## 📊 Evaluation Methodology\n\n")
            f.write("### Scoring Criteria\n\n")
            
            for criterion, weight in eval_info['criteria_weights'].items():
                f.write(f"- **{criterion.replace('_', ' ').title()}:** {weight*100:.0f}% weight\n")
            
            f.write("\n### Test Scenarios\n\n")
            f.write("1. **Basic:** Standard interviewer test with clear optimization task\n")
            f.write("2. **Complex:** Advanced diagnostic scenario with technical challenges\n")
            f.write("3. **Collaboration:** Partnership-focused interview emphasizing empathy\n\n")
            
            f.write("### Success Metrics\n\n")
            f.write("- **Question Relevance:** Quality and relevance of interview questions\n")
            f.write("- **Analysis Quality:** Depth of understanding and problem analysis\n")
            f.write("- **Improvement Suggestions:** Actionability of optimization recommendations\n")
            f.write("- **Communication Clarity:** Professional and structured communication\n")
            f.write("- **Guardrail Compliance:** Proper use of required formats\n\n")


def main():
    """Main execution function."""
    
    evaluator = AIInterviewerEvaluator()
    
    print("🚀 AI Interviewer Candidate Evaluation")
    print("Phase 1: Finding Our Best AI Interviewer")
    print("=" * 50)
    
    # Run the full evaluation
    results = evaluator.run_full_evaluation()
    
    # Save results
    json_file, md_file = evaluator.save_results(results)
    
    print("\n" + "=" * 50)
    print("✅ Evaluation Complete!")
    print(f"📊 Results saved to: {json_file}")
    print(f"📝 Report generated: {md_file}")
    
    # Show quick summary
    if "overall_rankings" in results and results["overall_rankings"]:
        print("\n🏆 Top 3 Interviewer Candidates:")
        
        for rank, (model, data) in enumerate(list(results["overall_rankings"].items())[:3], 1):
            avg_score = data["average_score"]
            scenarios_done = data["scenarios_completed"]
            print(f"  {rank}. {model}: {avg_score:.2f}/10 ({scenarios_done} scenarios)")
        
        top_model = list(results["overall_rankings"].keys())[0]
        print(f"\n🎯 Recommended for Phase 2: {top_model}")
    else:
        print("\n❌ No models completed evaluation successfully")
        print("Check model availability and health")


if __name__ == "__main__":
    main()
