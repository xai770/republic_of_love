#!/usr/bin/env python3
"""
Sandy LLM Evaluation - Using New Optimization Framework
======================================================

Rerun Sandy's LLM evaluation using our professional optimization framework.
This analyzes the same models and data from the original Sandy test but with
comprehensive metrics, professional reporting, and baseline comparison.
"""

import sys
from pathlib import Path
import os

# Add the framework to path
framework_path = Path(__file__).parent / "llm_optimization_framework"
sys.path.insert(0, str(framework_path))

def main():
    """Run Sandy LLM evaluation with new framework"""
    
    print("🌸 Sandy LLM Evaluation - Professional Framework Edition")
    print("=" * 70)
    print("📊 Analyzing Sandy's test data with our new optimization framework\n")
    
    # Import framework components
    from llm_optimization_framework.configs.settings import OptimizationConfig, TemplateConfigs
    from llm_optimization_framework.utils.dialogue_parser import DialogueParser
    from llm_optimization_framework.core.metrics import PerformanceMetrics, MetricCategory
    from llm_optimization_framework.core.comparator import BatchBaselineComparator
    from llm_optimization_framework.reporters.markdown import MarkdownReporter
    from llm_optimization_framework.utils.quality_assessor import QualityAssessor
    
    # Configuration for Sandy-specific evaluation
    print("⚙️ Setting up Sandy-specific configuration...")
    config = TemplateConfigs.content_extraction()
    config.baseline_model = "gemma3n:latest"  # Sandy's reference model
    config.quality_threshold = 0.70  # Sandy's quality requirements
    config.performance_threshold = 0.75
    config.consistency_threshold = 0.65
    
    # Sandy-specific metrics weights (focused on content extraction quality)
    config.metrics_weights = {
        'quality': 0.50,      # High weight on response quality
        'performance': 0.25,  # Moderate weight on speed
        'consistency': 0.25   # Moderate weight on consistency
    }
    
    print(f"✅ Configuration: Content Extraction optimized for {config.baseline_model}")
    print(f"📊 Weights: Quality={config.metrics_weights['quality']}, Performance={config.metrics_weights['performance']}, Consistency={config.metrics_weights['consistency']}")
    
    # Parse Sandy's dialogue logs
    print("\n📂 Parsing Sandy's dialogue logs...")
    dialogue_dir = Path("/home/xai/Documents/republic_of_love/llm_dialogues")
    sandy_pattern = "*sandy_test_*.md"
    
    parser = DialogueParser()
    
    # Get all Sandy test files
    sandy_files = list(dialogue_dir.glob(sandy_pattern))
    print(f"📋 Found {len(sandy_files)} Sandy test files")
    
    if not sandy_files:
        print("❌ No Sandy test files found!")
        print(f"   Looking in: {dialogue_dir}")
        print(f"   Pattern: {sandy_pattern}")
        return
    
    # Parse dialogue entries
    print("🔍 Parsing dialogue entries...")
    dialogue_entries_list = parser.parse_directory(dialogue_dir, sandy_pattern)
    
    # Group by model name
    dialogue_entries = {}
    for entry in dialogue_entries_list:
        if entry.model_name not in dialogue_entries:
            dialogue_entries[entry.model_name] = []
        dialogue_entries[entry.model_name].append(entry)
    
    if not dialogue_entries:
        print("❌ No dialogue entries parsed!")
        return
    
    print(f"✅ Parsed {len(dialogue_entries)} model dialogues")
    for model, entries in dialogue_entries.items():
        print(f"   📱 {model}: {len(entries)} test entries")
    
    # Calculate comprehensive metrics
    print("\n📊 Calculating comprehensive performance metrics...")
    metrics_calc = PerformanceMetrics()
    assessor = QualityAssessor()
    
    model_metrics = {}
    
    for model_name, entries in dialogue_entries.items():
        print(f"   🔄 Processing {model_name}...")
        
        # Calculate metrics for this model
        try:
            metrics = metrics_calc.calculate_model_metrics(entries, model_name)
            model_metrics[model_name] = metrics
            
            print(f"      ✅ Score: {metrics.overall_score:.3f}")
            print(f"      📈 Quality: {metrics.category_scores.get(MetricCategory.QUALITY, 0.0):.3f}")
            print(f"      ⚡ Performance: {metrics.category_scores.get(MetricCategory.PERFORMANCE, 0.0):.3f}")
            print(f"      🎯 Consistency: {metrics.category_scores.get(MetricCategory.CONSISTENCY, 0.0):.3f}")
            
        except Exception as e:
            print(f"      ❌ Error calculating metrics: {e}")
            continue
    
    if not model_metrics:
        print("❌ No metrics calculated!")
        return
    
    # Baseline comparison
    print(f"\n🎯 Performing baseline comparison against {config.baseline_model}...")
    comparator = BatchBaselineComparator(config.baseline_model)
    
    try:
        # Convert dialogue_entries format for comparator
        all_entries = dialogue_entries
        baseline_results = comparator.compare_all_models(all_entries)
        
        print("📊 Baseline Comparison Results:")
        print(f"   📍 Baseline Model: {config.baseline_model}")
        
        if baseline_results:
            total_comparisons = sum(len(comparisons) for comparisons in baseline_results.values())
            print(f"   � Total comparisons: {total_comparisons}")
            
            # Calculate summary statistics
            above_baseline_count = 0
            below_baseline_count = 0
            
            for model, comparisons in baseline_results.items():
                if model != config.baseline_model:
                    avg_similarity = sum(comp.similarity_score for comp in comparisons) / len(comparisons) if comparisons else 0
                    if avg_similarity > 0.5:  # threshold for "above baseline"
                        above_baseline_count += 1
                    else:
                        below_baseline_count += 1
            
            print(f"   📈 Models performing well: {above_baseline_count}")
            print(f"   📉 Models needing improvement: {below_baseline_count}")
        
    except Exception as e:
        print(f"❌ Error in baseline comparison: {e}")
        baseline_results = None
    
    # Generate comprehensive report
    print(f"\n📄 Generating comprehensive Sandy LLM evaluation report...")
    
    try:
        reporter = MarkdownReporter(
            project_name="Sandy LLM Evaluation Report", 
            baseline_model=config.baseline_model
        )
        
        # Add Sandy-specific context
        report_metadata = {
            "evaluation_type": "Content Extraction & Job Matching",
            "test_focus": "Sandy's specialized requirements",
            "data_source": "Sandy test dialogues from July 16, 2025",
            "models_evaluated": len(model_metrics),
            "test_files": len(sandy_files)
        }
        
        # Generate the report
        report_content = reporter.generate_comprehensive_report(
            model_metrics, 
            baseline_results
        )
        
        # Save report
        report_file = Path("sandy_llm_evaluation_report.md")
        reporter.save_report(report_content, str(report_file))
        
        print(f"✅ Report saved: {report_file}")
        print(f"📊 Report includes:")
        print(f"   🏆 Model rankings and scores")
        print(f"   📈 Baseline comparison analysis")
        print(f"   📋 Executive summary")
        print(f"   🎯 Performance recommendations")
        print(f"   📊 Detailed metrics breakdown")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
    
    # Quick summary for immediate feedback
    print(f"\n🎊 Sandy LLM Evaluation Complete!")
    print("=" * 50)
    
    if model_metrics:
        # Sort models by overall score
        sorted_models = sorted(
            model_metrics.items(), 
            key=lambda x: x[1].overall_score, 
            reverse=True
        )
        
        print("🏆 Top 5 Models for Sandy:")
        for i, (model, metrics) in enumerate(sorted_models[:5], 1):
            grade = 'A' if metrics.overall_score >= 0.9 else 'A-' if metrics.overall_score >= 0.85 else 'B+' if metrics.overall_score >= 0.8 else 'B' if metrics.overall_score >= 0.75 else 'B-' if metrics.overall_score >= 0.7 else 'C+'
            print(f"   {i}. {model}")
            print(f"      Score: {metrics.overall_score:.3f} ({grade})")
            print(f"      Quality: {metrics.category_scores.get(MetricCategory.QUALITY, 0.0):.3f} | Performance: {metrics.category_scores.get(MetricCategory.PERFORMANCE, 0.0):.3f} | Consistency: {metrics.category_scores.get(MetricCategory.CONSISTENCY, 0.0):.3f}")
        
        print(f"\n📋 Key Insights:")
        best_model = sorted_models[0]
        print(f"   🥇 Best Overall: {best_model[0]} ({best_model[1].overall_score:.3f})")
        
        # Find best in each category
        best_quality = max(model_metrics.items(), key=lambda x: x[1].category_scores.get(MetricCategory.QUALITY, 0.0))
        best_performance = max(model_metrics.items(), key=lambda x: x[1].category_scores.get(MetricCategory.PERFORMANCE, 0.0))
        best_consistency = max(model_metrics.items(), key=lambda x: x[1].category_scores.get(MetricCategory.CONSISTENCY, 0.0))
        
        print(f"   🎯 Best Quality: {best_quality[0]} ({best_quality[1].category_scores.get(MetricCategory.QUALITY, 0.0):.3f})")
        print(f"   ⚡ Best Performance: {best_performance[0]} ({best_performance[1].category_scores.get(MetricCategory.PERFORMANCE, 0.0):.3f})")
        print(f"   🔄 Best Consistency: {best_consistency[0]} ({best_consistency[1].category_scores.get(MetricCategory.CONSISTENCY, 0.0):.3f})")
    
    print(f"\n📖 Full report available in: sandy_llm_evaluation_report.md")
    print("🌸 Sandy evaluation using professional framework complete! 🌸")

if __name__ == "__main__":
    main()
