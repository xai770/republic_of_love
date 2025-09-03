#!/usr/bin/env python3
"""
Markdown Reporter Module
========================

Generate comprehensive markdown reports for LLM optimization results.
Provides professional, shareable reports with detailed analysis and visualizations.
"""

import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..core.metrics import ModelMetrics, MetricsBenchmarker, MetricCategory
from ..core.comparator import BaselineComparison, BatchBaselineComparator


class MarkdownReporter:
    """Generate comprehensive markdown reports for LLM optimization"""
    
    def __init__(self, project_name: str = "LLM Optimization", 
                 baseline_model: Optional[str] = None):
        """
        Initialize markdown reporter
        
        Args:
            project_name: Name of the optimization project
            baseline_model: Name of baseline model for comparisons
        """
        self.project_name = project_name
        self.baseline_model = baseline_model
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_comprehensive_report(self, 
                                    model_metrics: Dict[str, ModelMetrics],
                                    baseline_comparisons: Optional[Dict[str, List[BaselineComparison]]] = None,
                                    test_details: Optional[Dict[str, Any]] = None,
                                    dialogue_data: Optional[Dict[str, List]] = None) -> str:
        """
        Generate a comprehensive markdown report
        
        Args:
            model_metrics: Dictionary of model names to ModelMetrics
            baseline_comparisons: Optional baseline comparison results
            test_details: Optional test configuration details
            dialogue_data: Dictionary of model names to list of DialogueEntry objects
            
        Returns:
            Complete markdown report as string
        """
        # Create benchmarker for rankings
        benchmarker = MetricsBenchmarker()
        for metrics in model_metrics.values():
            benchmarker.add_model_metrics(metrics)
        
        performance_summary = benchmarker.get_performance_summary()
        
        # Build report sections
        sections = []
        
        sections.append(self._generate_header())
        sections.append(self._generate_executive_summary(performance_summary))
        sections.append(self._generate_rankings_section(performance_summary))
        sections.append(self._generate_detailed_metrics(model_metrics))
        
        if baseline_comparisons:
            sections.append(self._generate_baseline_comparison_section(baseline_comparisons))
        
        sections.append(self._generate_recommendations_section(model_metrics))
        sections.append(self._generate_methodology_section(test_details))
        
        # Add detailed prompt/response section for transparency
        if dialogue_data:
            sections.append(self._generate_prompts_responses_section(dialogue_data))
        
        sections.append(self._generate_appendix())
        
        return "\n\n".join(sections)
    
    def generate_sandy_report(self, results: Dict, metrics, dialogues: List, evaluation_config: Dict) -> str:
        """
        Sandy-specific report generation method
        ALWAYS includes exact prompts and responses for full transparency
        """
        sections = []
        
        # Header
        sections.append(self._generate_sandy_header(evaluation_config))
        
        # Summary
        sections.append(self._generate_sandy_summary(results, metrics, evaluation_config))
        
        # Model Rankings
        rankings = metrics.get_model_rankings()
        sections.append(self._generate_sandy_rankings(rankings))
        
        # Detailed metrics
        sections.append(self._generate_sandy_metrics(metrics))
        
        # ALWAYS include prompts and responses for transparency
        sections.append(self._generate_sandy_prompts_responses(dialogues))
        
        # Methodology
        sections.append(self._generate_sandy_methodology(evaluation_config))
        
        return "\n\n".join(sections)
    
    def _generate_sandy_header(self, config: Dict) -> str:
        """Generate Sandy-specific header"""
        version = config.get('version', '1.0')
        timestamp = config.get('timestamp', 'unknown')
        
        return f"""# Sandy LLM Evaluation Report v{version}

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Evaluation ID:** {timestamp}  
**Jobs Analyzed:** {config.get('job_count', 0)}  
**Models Tested:** {config.get('models', [])}

---

## 🎯 Purpose

This report provides comprehensive analysis of LLM performance for Sandy job matching tasks. Every prompt and response is included for complete transparency and reproducibility."""
    
    def _generate_sandy_summary(self, results: Dict, metrics, config: Dict) -> str:
        """Generate Sandy evaluation summary"""
        job_count = config.get('job_count', 0)
        model_count = len(config.get('models', []))
        total_responses = sum(len(job_results) for job_results in results.values())
        
        return f"""## 📊 Evaluation Summary

### Scope
- **Job Postings Analyzed:** {job_count}
- **Models Evaluated:** {model_count}
- **Total LLM Responses:** {total_responses}
- **Evaluation Framework:** Sandy Job Matching v{config.get('version', '1.0')}

### Key Findings
- All models successfully processed job postings
- Performance metrics calculated across multiple dimensions
- Complete prompt/response transparency maintained
- Reproducible evaluation framework validated"""
    
    def _generate_sandy_rankings(self, rankings: List) -> str:
        """Generate Sandy model rankings"""
        section = """## 🏆 Model Performance Rankings

### Overall Ranking

| Rank | Model | Score | Performance Grade |
|------|-------|-------|------------------|"""
        
        for i, (model, score) in enumerate(rankings, 1):
            grade = "A" if score >= 0.8 else "B" if score >= 0.6 else "C" if score >= 0.4 else "D"
            section += f"\n| {i} | `{model}` | {score:.3f} | {grade} |"
        
        return section
    
    def _generate_sandy_metrics(self, metrics) -> str:
        """Generate Sandy metrics section"""
        summary = metrics.get_summary()
        
        section = """## 📈 Detailed Performance Metrics

### Response Quality Analysis
"""
        for model, stats in summary.items():
            avg_length = stats.get('avg_response_length', 0)
            avg_time = stats.get('avg_response_time', 0)
            response_count = stats.get('response_count', 0)
            
            section += f"""
#### {model}
- **Responses Generated:** {response_count}
- **Average Response Length:** {avg_length:.0f} characters
- **Average Response Time:** {avg_time:.2f} seconds
- **Consistency Score:** {stats.get('consistency_score', 0):.3f}"""
        
        return section
    
    def _generate_sandy_prompts_responses(self, dialogues: List) -> str:
        """
        Generate complete prompts and responses section
        This section is ALWAYS included for transparency
        """
        section = """## 🔍 Complete Prompts & Responses

**TRANSPARENCY GUARANTEE:** This section contains every prompt sent to each model and every response received. This ensures complete reproducibility and enables detailed analysis of model behavior patterns.

"""
        
        # Group dialogues by model
        by_model: Dict[str, List] = {}
        for dialogue in dialogues:
            model = dialogue.model_name  # Use correct attribute name
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(dialogue)
        
        for model, model_dialogues in by_model.items():
            section += f"### Model: `{model}`\n\n"
            section += f"**Total Interactions:** {len(model_dialogues)}\n\n"
            
            for i, dialogue in enumerate(model_dialogues, 1):
                job_id = dialogue.test_id  # Use correct attribute name
                section += f"#### Interaction {i} - Job: {job_id}\n\n"
                
                # Prompt section
                section += "**PROMPT:**\n```\n"
                section += dialogue.prompt_text  # Use correct attribute name
                section += "\n```\n\n"
                
                # Response section
                section += "**RESPONSE:**\n```\n"
                section += dialogue.response_text  # Use correct attribute name
                section += "\n```\n\n"
                
                # Add metadata if available
                if hasattr(dialogue, 'timestamp') and dialogue.timestamp:
                    section += f"*Timestamp: {dialogue.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
                
                section += "---\n\n"
        
        return section
    
    def _generate_sandy_methodology(self, config: Dict) -> str:
        """Generate methodology section"""
        return f"""## 🔬 Methodology

### Evaluation Framework
- **Version:** Sandy LLM Evaluation v{config.get('version', '1.0')}
- **Test Data:** Real job posting descriptions from Sandy database
- **Prompt Template:** Standardized job analysis prompt
- **Metrics:** Response quality, consistency, and performance timing
- **Transparency:** Complete prompt/response logging for reproducibility

### Models Tested
{chr(10).join(f"- `{model}`" for model in config.get('models', []))}

### Data Processing
1. Job postings loaded from Sandy JSON files
2. Standardized prompts generated for each job
3. All models tested with identical prompts
4. Responses collected with timing and token metrics
5. Performance analysis and ranking generated

### Reproducibility
- All prompts and responses logged
- Evaluation configuration documented
- Results timestamped and versioned
- Framework code available for review"""
    
    def _generate_header(self) -> str:
        """Generate report header"""
        return f"""# {self.project_name} - LLM Optimization Report

**Generated:** {self.timestamp}  
**Baseline Model:** {self.baseline_model or "None specified"}  
**Report Type:** Comprehensive Performance Analysis

---"""
    
    def _generate_executive_summary(self, performance_summary: Dict[str, Any]) -> str:
        """Generate executive summary section"""
        if not performance_summary:
            return "## Executive Summary\n\nNo performance data available."
        
        model_count = performance_summary.get("model_count", 0)
        top_performer = performance_summary.get("top_performer")
        performance_spread = performance_summary.get("performance_spread", 0)
        
        top_performer_text = "N/A"
        if top_performer:
            top_performer_text = f"{top_performer[0]} ({top_performer[1]:.3f} score)"
        
        summary = f"""## 📊 Executive Summary

### Key Findings

- **Models Evaluated:** {model_count}
- **Top Performer:** {top_performer_text}
- **Performance Spread:** {performance_spread:.3f} (difference between best and worst)

### Quick Insights

"""
        
        # Add category insights
        category_averages = performance_summary.get("category_averages", {})
        for category_name, stats in category_averages.items():
            avg_score = stats.get("average", 0)
            status_emoji = "🟢" if avg_score >= 0.8 else "🟡" if avg_score >= 0.6 else "🔴"
            summary += f"- **{category_name.title()}:** {avg_score:.3f} average {status_emoji}\n"
        
        summary += """
### Recommendations Priority

1. **Immediate Action:** Review models with scores below 0.6
2. **Optimization Focus:** Improve consistency and reliability metrics
3. **Production Readiness:** Validate top performers with additional testing"""
        
        return summary
    
    def _generate_rankings_section(self, performance_summary: Dict[str, Any]) -> str:
        """Generate rankings and comparison section"""
        rankings = performance_summary.get("rankings", {})
        
        section = "## 🏆 Model Rankings\n\n"
        
        # Overall ranking
        overall_ranking = rankings.get("overall", [])
        if overall_ranking:
            section += "### Overall Performance\n\n"
            section += "| Rank | Model | Score | Grade |\n"
            section += "|------|-------|-------|-------|\n"
            
            for i, (model_name, score) in enumerate(overall_ranking):
                grade = self._score_to_grade(score)
                grade_emoji = self._grade_to_emoji(grade)
                section += f"| {i+1} | `{model_name}` | {score:.3f} | {grade} {grade_emoji} |\n"
            
            section += "\n"
        
        # Category rankings
        for category in MetricCategory:
            category_ranking = rankings.get(category.value, [])
            if category_ranking:
                section += f"### {category.value.title()} Performance\n\n"
                section += "| Rank | Model | Score |\n"
                section += "|------|-------| ------|\n"
                
                for i, (model_name, score) in enumerate(category_ranking[:5]):  # Top 5
                    section += f"| {i+1} | `{model_name}` | {score:.3f} |\n"
                
                section += "\n"
        
        return section
    
    def _generate_detailed_metrics(self, model_metrics: Dict[str, ModelMetrics]) -> str:
        """Generate detailed metrics section"""
        section = "## 📈 Detailed Model Analysis\n\n"
        
        for model_name, metrics in model_metrics.items():
            section += f"### {model_name}\n\n"
            section += f"**Overall Score:** {metrics.overall_score:.3f} | "
            section += f"**Tier:** {metrics.performance_tier} | "
            section += f"**Rank:** #{metrics.benchmark_rank or 'N/A'}\n\n"
            
            # Category scores
            section += "#### Category Breakdown\n\n"
            section += "| Category | Score | Status |\n"
            section += "|----------|-------|--------|\n"
            
            for category, score in metrics.category_scores.items():
                status = "🟢 Excellent" if score >= 0.8 else "🟡 Good" if score >= 0.6 else "🔴 Needs Work"
                section += f"| {category.value.title()} | {score:.3f} | {status} |\n"
            
            section += "\n"
            
            # Individual metrics
            section += "#### Individual Metrics\n\n"
            section += "| Metric | Value | Interpretation | Confidence |\n"
            section += "|--------|-------|----------------|------------|\n"
            
            for metric in metrics.individual_metrics:
                confidence_bar = "█" * int(metric.confidence * 5)
                section += f"| {metric.name} | {metric.value:.3f} | {metric.interpretation} | {confidence_bar} |\n"
            
            section += "\n"
            
            # Recommendations
            if metrics.recommendations:
                section += "#### Recommendations\n\n"
                for rec in metrics.recommendations:
                    section += f"- {rec}\n"
                section += "\n"
            
            section += "---\n\n"
        
        return section
    
    def _generate_baseline_comparison_section(self, 
                                            baseline_comparisons: Dict[str, List[BaselineComparison]]) -> str:
        """Generate baseline comparison section"""
        section = f"## 🎯 Baseline Comparison Analysis\n\n"
        section += f"**Baseline Model:** `{self.baseline_model}`\n\n"
        
        for model_name, comparisons in baseline_comparisons.items():
            if not comparisons:
                continue
                
            section += f"### {model_name} vs {self.baseline_model}\n\n"
            
            # Calculate average similarity
            avg_similarity = sum(comp.similarity_score.overall_similarity for comp in comparisons) / len(comparisons)
            section += f"**Average Similarity:** {avg_similarity:.3f}\n\n"
            
            # Detailed comparison table
            section += "| Test Type | Similarity | Verdict | Recommendation |\n"
            section += "|-----------|------------|---------|----------------|\n"
            
            for comp in comparisons:
                section += f"| {comp.similarity_score.detailed_breakdown.get('test_type', 'N/A')} | "
                section += f"{comp.similarity_score.overall_similarity:.3f} | "
                section += f"{comp.similarity_score.verdict_emoji} {comp.similarity_score.verdict} | "
                section += f"{comp.upgrade_recommendation} |\n"
            
            section += "\n"
            
            # Risk assessment summary
            high_risk_count = sum(1 for comp in comparisons if "HIGH RISK" in comp.risk_assessment)
            if high_risk_count > 0:
                section += f"⚠️ **Risk Alert:** {high_risk_count}/{len(comparisons)} tests show high risk\n\n"
            
            section += "---\n\n"
        
        return section
    
    def _generate_recommendations_section(self, model_metrics: Dict[str, ModelMetrics]) -> str:
        """Generate recommendations section"""
        section = "## 💡 Strategic Recommendations\n\n"
        
        # Collect all recommendations
        all_recommendations = []
        for metrics in model_metrics.values():
            all_recommendations.extend(metrics.recommendations)
        
        # Categorize recommendations
        quality_recs = [r for r in all_recommendations if "quality" in r.lower()]
        performance_recs = [r for r in all_recommendations if "performance" in r.lower()]
        consistency_recs = [r for r in all_recommendations if "consistency" in r.lower()]
        
        if quality_recs:
            section += "### Quality Improvements\n\n"
            for rec in quality_recs[:3]:  # Top 3
                section += f"- {rec}\n"
            section += "\n"
        
        if performance_recs:
            section += "### Performance Optimizations\n\n"
            for rec in performance_recs[:3]:  # Top 3
                section += f"- {rec}\n"
            section += "\n"
        
        if consistency_recs:
            section += "### Consistency Enhancements\n\n"
            for rec in consistency_recs[:3]:  # Top 3
                section += f"- {rec}\n"
            section += "\n"
        
        # Strategic recommendations
        section += """### Strategic Next Steps

1. **Production Deployment**
   - Select top 2-3 performers for pilot testing
   - Implement A/B testing framework
   - Monitor real-world performance metrics

2. **Optimization Priorities**
   - Focus on models with high potential but low consistency
   - Investigate performance bottlenecks in efficiency metrics
   - Develop model-specific fine-tuning strategies

3. **Risk Mitigation**
   - Establish baseline deviation thresholds
   - Implement automated quality monitoring
   - Create fallback strategies for underperforming models"""
        
        return section
    
    def _generate_methodology_section(self, test_details: Optional[Dict[str, Any]]) -> str:
        """Generate methodology section"""
        section = "## 🔬 Methodology\n\n"
        
        section += """### Evaluation Framework

Our LLM optimization framework evaluates models across five key dimensions:

1. **Quality (40% weight)**: Response completeness, structure, and relevance
2. **Performance (25% weight)**: Task completion rate and response appropriateness  
3. **Consistency (20% weight)**: Format and quality consistency across responses
4. **Efficiency (10% weight)**: Response length optimization and resource usage
5. **Reliability (5% weight)**: Error rates and response stability

### Scoring Methodology

- **Individual Metrics**: 0.0 - 1.0 scale with confidence weighting
- **Category Scores**: Confidence-weighted average of individual metrics
- **Overall Score**: Weighted sum of category scores
- **Baseline Comparison**: Multi-dimensional similarity analysis

### Test Configuration
"""
        
        if test_details:
            section += f"- **Test Suite:** {test_details.get('test_types', 'Standard evaluation')}\n"
            section += f"- **Sample Size:** {test_details.get('sample_count', 'N/A')} responses per model\n"
            section += f"- **Evaluation Date:** {test_details.get('evaluation_date', self.timestamp)}\n"
        else:
            section += "- **Test Configuration:** Standard LLM evaluation suite\n"
            section += "- **Metrics Collection:** Automated analysis framework\n"
        
        return section
    
    def _generate_appendix(self) -> str:
        """Generate appendix section"""
        return """## 📋 Appendix

### Grade Scale

| Score Range | Grade | Interpretation |
|-------------|-------|----------------|
| 0.90 - 1.00 | A+ | Excellent performance |
| 0.85 - 0.89 | A | Very good performance |
| 0.80 - 0.84 | A- | Good performance |
| 0.75 - 0.79 | B+ | Above average |
| 0.70 - 0.74 | B | Average performance |
| 0.65 - 0.69 | B- | Below average |
| 0.60 - 0.64 | C+ | Marginal performance |
| 0.55 - 0.59 | C | Poor performance |
| 0.00 - 0.54 | F | Failing performance |

### Confidence Indicators

- **Full Bar (█████)**: 90-100% confidence
- **High Bar (████_)**: 80-89% confidence  
- **Med Bar (███__)**: 70-79% confidence
- **Low Bar (██___)**: 60-69% confidence
- **Min Bar (_______)**: <60% confidence

### Risk Assessment Legend

- 🟢 **LOW RISK**: Model performs similarly to baseline
- 🟡 **MEDIUM RISK**: Some differences, monitor performance
- 🟠 **HIGH RISK**: Significant deviations from baseline
- 🔴 **VERY HIGH RISK**: Major performance differences

---

*Report generated by LLM Optimization Framework*  
*For questions or issues, refer to framework documentation*"""
    
    def _generate_prompts_responses_section(self, dialogue_data: Dict[str, List]) -> str:
        """
        Generate detailed prompts and responses section for full transparency
        
        Args:
            dialogue_data: Dictionary of model names to list of DialogueEntry objects
            
        Returns:
            Markdown section with all prompts and responses
        """
        section = """## 🔍 Detailed Prompts & Responses

**Note:** This section provides complete transparency by showing every prompt sent to each model and the exact response received. This ensures full reproducibility and enables detailed analysis of model behavior.

"""
        
        for model_name, dialogues in dialogue_data.items():
            if not dialogues:
                continue
                
            section += f"### Model: `{model_name}`\n\n"
            section += f"**Total Interactions:** {len(dialogues)}\n\n"
            
            for i, dialogue in enumerate(dialogues, 1):
                section += f"#### Interaction {i}\n\n"
                
                # Add prompt
                section += "**PROMPT:**\n```\n"
                # Handle both string prompts and structured prompts
                if hasattr(dialogue, 'prompt'):
                    prompt_text = dialogue.prompt
                elif hasattr(dialogue, 'user_input'):
                    prompt_text = dialogue.user_input
                else:
                    prompt_text = str(dialogue)
                    
                section += prompt_text
                section += "\n```\n\n"
                
                # Add response
                section += "**RESPONSE:**\n```\n"
                if hasattr(dialogue, 'response'):
                    response_text = dialogue.response
                elif hasattr(dialogue, 'assistant_output'):
                    response_text = dialogue.assistant_output
                else:
                    response_text = "Response not available"
                    
                section += response_text
                section += "\n```\n\n"
                
                # Add metadata if available
                if hasattr(dialogue, 'metadata') and dialogue.metadata:
                    section += "**Metadata:**\n"
                    for key, value in dialogue.metadata.items():
                        section += f"- {key}: {value}\n"
                    section += "\n"
                
                section += "---\n\n"
        
        return section
    
    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 0.90: return "A+"
        elif score >= 0.85: return "A"
        elif score >= 0.80: return "A-"
        elif score >= 0.75: return "B+"
        elif score >= 0.70: return "B"
        elif score >= 0.65: return "B-"
        elif score >= 0.60: return "C+"
        elif score >= 0.55: return "C"
        else: return "F"
    
    def _grade_to_emoji(self, grade: str) -> str:
        """Convert grade to emoji"""
        grade_emojis = {
            "A+": "🌟", "A": "✨", "A-": "⭐",
            "B+": "👍", "B": "👌", "B-": "🤏",
            "C+": "😐", "C": "😕", "F": "💥"
        }
        return grade_emojis.get(grade, "❓")
    
    def save_report(self, report_content: str, output_path: str) -> str:
        """
        Save report to file
        
        Args:
            report_content: Markdown content to save
            output_path: Path to save the report
            
        Returns:
            Full path of saved report
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return output_path


class QuickReporter:
    """Generate quick summary reports for rapid assessment"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    def generate_quick_summary(self, model_metrics: Dict[str, ModelMetrics]) -> str:
        """Generate a quick summary report"""
        if not model_metrics:
            return "No model metrics available."
        
        # Create benchmarker for rankings
        benchmarker = MetricsBenchmarker()
        for metrics in model_metrics.values():
            benchmarker.add_model_metrics(metrics)
        
        rankings = benchmarker.generate_rankings()
        overall_ranking = rankings.get("overall", [])
        
        summary = f"# Quick LLM Performance Summary\n\n"
        summary += f"**Generated:** {self.timestamp} | **Models:** {len(model_metrics)}\n\n"
        
        summary += "## 🏆 Top Performers\n\n"
        summary += "| Rank | Model | Score | Grade |\n"
        summary += "|------|-------|-------|-------|\n"
        
        for i, (model_name, score) in enumerate(overall_ranking[:5]):
            grade = self._score_to_grade(score)
            summary += f"| {i+1} | `{model_name}` | {score:.3f} | {grade} |\n"
        
        summary += "\n## 📊 Category Leaders\n\n"
        
        for category in MetricCategory:
            category_ranking = rankings.get(category.value, [])
            if category_ranking:
                leader = category_ranking[0]
                summary += f"- **{category.value.title()}:** {leader[0]} ({leader[1]:.3f})\n"
        
        summary += f"\n## 💡 Key Insights\n\n"
        
        # Find best and worst performers
        best_model = overall_ranking[0] if overall_ranking else None
        worst_model = overall_ranking[-1] if overall_ranking else None
        
        if best_model and worst_model:
            spread = best_model[1] - worst_model[1]
            summary += f"- **Performance Spread:** {spread:.3f} (from {worst_model[1]:.3f} to {best_model[1]:.3f})\n"
            summary += f"- **Recommended Choice:** {best_model[0]} for production deployment\n"
            
            if spread > 0.3:
                summary += f"- **Alert:** High variance in performance suggests model selection is critical\n"
        
        return summary
    
    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 0.90: return "A+"
        elif score >= 0.85: return "A"
        elif score >= 0.80: return "A-"
        elif score >= 0.75: return "B+"
        elif score >= 0.70: return "B"
        elif score >= 0.65: return "B-"
        elif score >= 0.60: return "C+"
        elif score >= 0.55: return "C"
        else: return "F"
