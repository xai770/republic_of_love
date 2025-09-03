#!/usr/bin/env python3
"""
LLM Optimization Framework - Core Integration Module
===================================================

This module demonstrates how to integrate the framework components
for end-to-end LLM optimization workflows.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import all framework components
from ..utils.dialogue_parser import DialogueParser, DialogueEntry
from ..utils.quality_assessor import QualityAssessor, AdvancedQualityAssessor
from ..core.metrics import PerformanceMetrics, MetricsBenchmarker, ModelMetrics, MetricCategory
from ..core.comparator import BatchBaselineComparator, BaselineComparison
from ..reporters.markdown import MarkdownReporter, QuickReporter
from ..configs.settings import (
    OptimizationConfig, ConfigurationManager, PresetConfigs, TemplateConfigs
)


class LLMOptimizationFramework:
    """
    Main framework class that orchestrates the complete LLM optimization pipeline
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize the optimization framework
        
        Args:
            config: Configuration object, uses default if None
        """
        self.config = config or ConfigurationManager().get_default_config()
        
        # Initialize components
        self.parser = DialogueParser()
        self.quality_assessor = AdvancedQualityAssessor()
        self.metrics_calculator = PerformanceMetrics(
            custom_weights=self._get_category_weights_dict()
        )
        self.benchmarker = MetricsBenchmarker()
        
        # Initialize reporters
        self.markdown_reporter = MarkdownReporter(
            project_name=self.config.project_name,
            baseline_model=self.config.baseline_model
        )
        self.quick_reporter = QuickReporter()
        
        # Storage for results
        self.dialogue_entries: Dict[str, List[DialogueEntry]] = {}
        self.model_metrics: Dict[str, ModelMetrics] = {}
        self.baseline_comparisons: Optional[Dict[str, List[BaselineComparison]]] = None
        
        # Validation
        issues = ConfigurationManager().validate_config(self.config)
        if issues:
            print("⚠️ Configuration issues detected:")
            for issue in issues:
                print(f"   - {issue}")
    
    def load_dialogue_data(self, data_source: str) -> Dict[str, int]:
        """
        Load dialogue data from various sources
        
        Args:
            data_source: Path to directory containing dialogue logs
            
        Returns:
            Dictionary with model names and entry counts
        """
        print(f"📂 Loading dialogue data from: {data_source}")
        
        if os.path.isdir(data_source):
            entries = self.parser.parse_directory(Path(data_source))
            # Group entries by model name
            self.dialogue_entries = {}
            for entry in entries:
                if entry.model_name not in self.dialogue_entries:
                    self.dialogue_entries[entry.model_name] = []
                self.dialogue_entries[entry.model_name].append(entry)
        elif os.path.isfile(data_source):
            # Single file - determine format and parse
            entry = self.parser.parse_dialogue_file(Path(data_source))
            if entry:
                self.dialogue_entries = {entry.model_name: [entry]}
            else:
                self.dialogue_entries = {}
        else:
            raise ValueError(f"Invalid data source: {data_source}")
        
        # Summary
        summary = {model: len(entries) for model, entries in self.dialogue_entries.items()}
        print(f"   Loaded {len(self.dialogue_entries)} models")
        for model, count in summary.items():
            print(f"   - {model}: {count} entries")
        
        return summary
    
    def run_quality_assessment(self) -> Dict[str, Dict[str, float]]:
        """
        Run quality assessment on all loaded dialogue entries
        
        Returns:
            Dictionary with quality scores by model and test type
        """
        print("🔍 Running quality assessment...")
        
        quality_results = {}
        
        for model_name, entries in self.dialogue_entries.items():
            print(f"   Assessing {model_name}...")
            model_quality: Dict[str, List[float]] = {}
            
            for entry in entries:
                quality_score = self.quality_assessor.assess_quality(
                    entry.response_text, entry.test_id
                )
                
                if entry.test_id not in model_quality:
                    model_quality[entry.test_id] = []
                model_quality[entry.test_id].append(quality_score.overall_score)
            
            # Calculate averages
            quality_averages = {
                test_id: sum(scores) / len(scores)
                for test_id, scores in model_quality.items()
            }
            
            quality_results[model_name] = quality_averages
            
            avg_quality = sum(quality_averages.values()) / len(quality_averages)
            print(f"     Average quality: {avg_quality:.3f}")
        
        return quality_results
    
    def calculate_performance_metrics(self) -> Dict[str, ModelMetrics]:
        """
        Calculate comprehensive performance metrics for all models
        
        Returns:
            Dictionary of model metrics
        """
        print("📊 Calculating performance metrics...")
        
        for model_name, entries in self.dialogue_entries.items():
            print(f"   Processing {model_name}...")
            
            metrics = self.metrics_calculator.calculate_model_metrics(entries, model_name)
            self.model_metrics[model_name] = metrics
            self.benchmarker.add_model_metrics(metrics)
            
            print(f"     Overall score: {metrics.overall_score:.3f}")
            print(f"     Performance tier: {metrics.performance_tier}")
        
        # Generate rankings
        rankings = self.benchmarker.generate_rankings()
        print(f"\n   🏆 Top performers:")
        for i, (model, score) in enumerate(rankings.get("overall", [])[:3]):
            print(f"     {i+1}. {model}: {score:.3f}")
        
        return self.model_metrics
    
    def run_baseline_comparison(self) -> Optional[Dict[str, List[BaselineComparison]]]:
        """
        Run baseline comparison if baseline model is configured
        
        Returns:
            Baseline comparison results or None
        """
        if not self.config.baseline_model:
            print("⏭️ Skipping baseline comparison (no baseline configured)")
            return None
        
        if self.config.baseline_model not in self.dialogue_entries:
            print(f"⚠️ Baseline model '{self.config.baseline_model}' not found in data")
            return None
        
        print(f"🎯 Running baseline comparison against {self.config.baseline_model}...")
        
        baseline_comparator = BatchBaselineComparator(self.config.baseline_model)
        self.baseline_comparisons = baseline_comparator.compare_all_models(self.dialogue_entries)
        
        for model_name, comparisons in self.baseline_comparisons.items():
            if comparisons:
                avg_similarity = sum(comp.similarity_score.overall_similarity for comp in comparisons) / len(comparisons)
                print(f"   {model_name}: {avg_similarity:.3f} avg similarity")
        
        return self.baseline_comparisons
    
    def generate_reports(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Generate comprehensive reports
        
        Args:
            output_dir: Output directory for reports
            
        Returns:
            Dictionary with report types and file paths
        """
        output_dir = output_dir or self.config.output_directory
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"📄 Generating reports in {output_dir}...")
        
        generated_reports = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Quick summary report
        if self.model_metrics:
            quick_summary = self.quick_reporter.generate_quick_summary(self.model_metrics)
            quick_path = os.path.join(output_dir, f"quick_summary_{timestamp}.md")
            
            with open(quick_path, 'w', encoding='utf-8') as f:
                f.write(quick_summary)
            
            generated_reports["quick_summary"] = quick_path
            print(f"   ✅ Quick summary: {quick_path}")
        
        # Comprehensive report
        if self.model_metrics:
            comprehensive_report = self.markdown_reporter.generate_comprehensive_report(
                model_metrics=self.model_metrics,
                baseline_comparisons=self.baseline_comparisons,
                test_details=self._get_test_details()
            )
            
            comprehensive_path = os.path.join(output_dir, f"comprehensive_report_{timestamp}.md")
            self.markdown_reporter.save_report(comprehensive_report, comprehensive_path)
            
            generated_reports["comprehensive"] = comprehensive_path
            print(f"   ✅ Comprehensive report: {comprehensive_path}")
        
        # JSON export
        if self.config.generate_json:
            json_data = self._export_to_json()
            json_path = os.path.join(output_dir, f"optimization_results_{timestamp}.json")
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)
            
            generated_reports["json"] = json_path
            print(f"   ✅ JSON export: {json_path}")
        
        return generated_reports
    
    def run_complete_optimization(self, data_source: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the complete optimization pipeline
        
        Args:
            data_source: Path to dialogue data
            output_dir: Output directory for reports
            
        Returns:
            Complete optimization results
        """
        print("🚀 Starting complete LLM optimization pipeline...")
        print("=" * 60)
        
        results = {
            "config": self.config,
            "start_time": datetime.now().isoformat(),
            "data_summary": {},
            "quality_results": {},
            "model_metrics": {},
            "baseline_comparisons": None,
            "reports": {},
            "success": False
        }
        
        try:
            # Step 1: Load data
            results["data_summary"] = self.load_dialogue_data(data_source)
            
            # Step 2: Quality assessment
            results["quality_results"] = self.run_quality_assessment()
            
            # Step 3: Performance metrics
            results["model_metrics"] = self.calculate_performance_metrics()
            
            # Step 4: Baseline comparison
            results["baseline_comparisons"] = self.run_baseline_comparison()
            
            # Step 5: Generate reports
            results["reports"] = self.generate_reports(output_dir)
            
            results["success"] = True
            results["end_time"] = datetime.now().isoformat()
            
            print("\n🎉 Optimization pipeline completed successfully!")
            print(f"   Models evaluated: {len(self.model_metrics)}")
            if isinstance(results["reports"], dict):
                print(f"   Reports generated: {len(results['reports'])}")
            else:
                print(f"   Reports generated: 0")
            
            # Print top performers
            if self.model_metrics:
                rankings = self.benchmarker.generate_rankings()
                top_performer = rankings.get("overall", [None])[0]
                if top_performer:
                    print(f"   Top performer: {top_performer[0]} ({top_performer[1]:.3f})")
            
        except Exception as e:
            print(f"❌ Pipeline failed: {str(e)}")
            results["error"] = str(e)
            results["end_time"] = datetime.now().isoformat()
            raise
        
        return results
    
    def _get_category_weights_dict(self) -> Dict[MetricCategory, float]:
        """Convert category weights to dictionary"""
        return {
            MetricCategory.QUALITY: self.config.category_weights.quality,
            MetricCategory.PERFORMANCE: self.config.category_weights.performance,
            MetricCategory.CONSISTENCY: self.config.category_weights.consistency,
            MetricCategory.EFFICIENCY: self.config.category_weights.efficiency,
            MetricCategory.RELIABILITY: self.config.category_weights.reliability
        }
    
    def _get_test_details(self) -> Dict[str, Any]:
        """Get test configuration details for reporting"""
        return {
            "test_types": list(self.config.test_configs.keys()),
            "sample_count": len(self.dialogue_entries.get(list(self.dialogue_entries.keys())[0], [])) if self.dialogue_entries else 0,
            "evaluation_date": datetime.now().strftime("%Y-%m-%d"),
            "framework_version": "1.0.0"
        }
    
    def _export_to_json(self) -> Dict[str, Any]:
        """Export optimization results to JSON format"""
        json_data: Dict[str, Any] = {
            "project_name": self.config.project_name,
            "baseline_model": self.config.baseline_model,
            "evaluation_timestamp": datetime.now().isoformat(),
            "models": {}
        }
        
        for model_name, metrics in self.model_metrics.items():
            if not isinstance(json_data["models"], dict):
                json_data["models"] = {}
            json_data["models"][model_name] = {
                "overall_score": metrics.overall_score,
                "performance_tier": metrics.performance_tier,
                "benchmark_rank": metrics.benchmark_rank,
                "category_scores": {
                    category.value: score 
                    for category, score in metrics.category_scores.items()
                },
                "recommendations": metrics.recommendations,
                "individual_metrics": [
                    {
                        "name": metric.name,
                        "category": metric.category.value,
                        "value": metric.value,
                        "interpretation": metric.interpretation,
                        "confidence": metric.confidence
                    }
                    for metric in metrics.individual_metrics
                ]
            }
        
        return json_data


# Convenience functions for quick framework usage
def quick_optimization(data_source: str, 
                      baseline_model: Optional[str] = None,
                      output_dir: str = "optimization_results") -> Dict[str, Any]:
    """
    Run a quick optimization with default settings
    
    Args:
        data_source: Path to dialogue data
        baseline_model: Optional baseline model name
        output_dir: Output directory for results
        
    Returns:
        Optimization results
    """
    config = TemplateConfigs.general_purpose()
    config.baseline_model = baseline_model
    config.output_directory = output_dir
    
    framework = LLMOptimizationFramework(config)
    return framework.run_complete_optimization(data_source, output_dir)


def quality_focused_optimization(data_source: str,
                                baseline_model: Optional[str] = None,
                                output_dir: str = "quality_optimization_results") -> Dict[str, Any]:
    """
    Run optimization focused on quality metrics
    
    Args:
        data_source: Path to dialogue data
        baseline_model: Optional baseline model name
        output_dir: Output directory for results
        
    Returns:
        Optimization results
    """
    config = PresetConfigs.quality_focused()
    config.baseline_model = baseline_model
    config.output_directory = output_dir
    
    framework = LLMOptimizationFramework(config)
    return framework.run_complete_optimization(data_source, output_dir)
