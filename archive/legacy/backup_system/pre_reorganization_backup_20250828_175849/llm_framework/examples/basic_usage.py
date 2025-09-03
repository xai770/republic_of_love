#!/usr/bin/env python3
"""
LLM Optimization Framework - Example Usage
==========================================

This script demonstrates how to use the LLM optimization framework
for comprehensive model evaluation and comparison.
"""

import os
import sys
from pathlib import Path

# Add the framework to the path
framework_path = Path(__file__).parent.parent
sys.path.insert(0, str(framework_path))

from llm_optimization_framework.utils.dialogue_parser import DialogueParser
from llm_optimization_framework.utils.quality_assessor import QualityAssessor
from llm_optimization_framework.core.metrics import PerformanceMetrics, MetricsBenchmarker
from llm_optimization_framework.core.comparator import BatchBaselineComparator
from llm_optimization_framework.reporters.markdown import MarkdownReporter, QuickReporter
from llm_optimization_framework.configs.settings import (
    ConfigurationManager, PresetConfigs, TemplateConfigs
)


def main():
    """Main example demonstrating framework usage"""
    
    print("🚀 LLM Optimization Framework - Example Usage")
    print("=" * 60)
    
    # 1. Configuration Setup
    print("\n📋 Setting up configuration...")
    config_manager = ConfigurationManager()
    
    # Choose a preset configuration (or create custom)
    config = PresetConfigs.quality_focused()
    config.project_name = "Example LLM Evaluation"
    config.baseline_model = "gemma3n:latest"
    
    print(f"   Project: {config.project_name}")
    print(f"   Baseline: {config.baseline_model}")
    print(f"   Quality Weight: {config.category_weights.quality}")
    
    # 2. Parse Dialogue Logs
    print("\n📂 Parsing dialogue logs...")
    parser = DialogueParser()
    
    # Example: Parse a directory of dialogue logs
    log_directory = "/path/to/dialogue/logs"  # Update this path
    
    # For demonstration, we'll use mock data if directory doesn't exist
    if not os.path.exists(log_directory):
        print("   Using mock data for demonstration...")
        mock_entries = create_mock_dialogue_entries()
        all_entries = {"mock_model": mock_entries}
    else:
        all_entries = parser.parse_directory(log_directory)
    
    print(f"   Found {len(all_entries)} models with dialogue data")
    
    # 3. Quality Assessment
    print("\n🔍 Running quality assessment...")
    quality_assessor = QualityAssessor()
    
    for model_name, entries in all_entries.items():
        print(f"   Assessing {model_name}: {len(entries)} entries")
        
        for entry in entries[:3]:  # Show first 3 for demo
            quality_score = quality_assessor.assess_quality(
                entry.response_text, entry.test_id
            )
            print(f"     Test {entry.test_id}: {quality_score.overall_score:.3f}")
    
    # 4. Performance Metrics Calculation
    print("\n📊 Calculating performance metrics...")
    metrics_calculator = PerformanceMetrics()  # Use default weights
    
    model_metrics = {}
    for model_name, entries in all_entries.items():
        metrics = metrics_calculator.calculate_model_metrics(entries, model_name)
        model_metrics[model_name] = metrics
        print(f"   {model_name}: {metrics.overall_score:.3f} ({metrics.performance_tier})")
    
    # 5. Baseline Comparison
    print("\n🎯 Running baseline comparison...")
    if config.baseline_model and config.baseline_model in all_entries:
        baseline_comparator = BatchBaselineComparator(config.baseline_model)
        baseline_comparisons = baseline_comparator.compare_all_models(all_entries)
        
        for model_name, comparisons in baseline_comparisons.items():
            if comparisons:
                avg_similarity = sum(comp.similarity_score.overall_similarity for comp in comparisons) / len(comparisons)
                print(f"   {model_name} vs baseline: {avg_similarity:.3f} similarity")
    else:
        baseline_comparisons = None
        print("   Skipping baseline comparison (no baseline data)")
    
    # 6. Generate Rankings
    print("\n🏆 Generating rankings...")
    benchmarker = MetricsBenchmarker()
    for metrics in model_metrics.values():
        benchmarker.add_model_metrics(metrics)
    
    rankings = benchmarker.generate_rankings()
    overall_ranking = rankings.get("overall", [])
    
    print("   Overall Rankings:")
    for i, (model_name, score) in enumerate(overall_ranking[:5]):
        print(f"     {i+1}. {model_name}: {score:.3f}")
    
    # 7. Generate Reports
    print("\n📄 Generating reports...")
    
    # Quick summary report
    quick_reporter = QuickReporter()
    quick_summary = quick_reporter.generate_quick_summary(model_metrics)
    
    quick_report_path = "quick_summary.md"
    with open(quick_report_path, 'w') as f:
        f.write(quick_summary)
    print(f"   Quick summary: {quick_report_path}")
    
    # Comprehensive report
    reporter = MarkdownReporter(
        project_name=config.project_name,
        baseline_model=config.baseline_model
    )
    
    comprehensive_report = reporter.generate_comprehensive_report(
        model_metrics=model_metrics,
        baseline_comparisons=baseline_comparisons,
        test_details={
            "test_types": list(config.test_configs.keys()),
            "sample_count": len(all_entries.get(list(all_entries.keys())[0], [])),
            "evaluation_date": "2024-01-01"
        }
    )
    
    comprehensive_report_path = "comprehensive_report.md"
    reporter.save_report(comprehensive_report, comprehensive_report_path)
    print(f"   Comprehensive report: {comprehensive_report_path}")
    
    # 8. Configuration Validation
    print("\n✅ Validating configuration...")
    issues = config_manager.validate_config(config)
    if issues:
        print("   Configuration issues found:")
        for issue in issues:
            print(f"     - {issue}")
    else:
        print("   Configuration is valid")
    
    print("\n🎉 Framework example completed successfully!")
    print(f"   Check the generated reports: {quick_report_path}, {comprehensive_report_path}")


def create_mock_dialogue_entries():
    """Create mock dialogue entries for demonstration"""
    from llm_optimization_framework.utils.dialogue_parser import DialogueEntry
    
    mock_entries = [
        DialogueEntry(
            model_name="mock_model",
            test_id="concise_extraction",
            test_type="concise_extraction",
            response_text="""**Your Tasks:**
- Conduct security audits and compliance reviews
- Manage audit coordination with external partners
- Validate security protocols and procedures

**Your Profile:**
- 5+ years experience in security management
- Bachelor's degree in Information Security
- Strong analytical and communication skills""",
            prompt_text="Extract key job requirements concisely",
            processing_time=1.2,
            response_length=256,
            success=True,
            metadata={"timestamp": "2024-01-01", "file_path": "mock_data.json"}
        ),
        
        DialogueEntry(
            model_name="mock_model",
            test_id="structured_analysis",
            test_type="structured_analysis",
            response_text="""=== TECHNICAL REQUIREMENTS ===
• Security audit experience (Critical)
• Compliance framework knowledge (Important)
• Risk assessment capabilities (Critical)

=== BUSINESS REQUIREMENTS ===
• Team coordination skills (Important)
• Stakeholder communication (Critical)
• Project management experience (Important)""",
            prompt_text="Provide structured analysis of job requirements",
            processing_time=1.8,
            response_length=384,
            success=True,
            metadata={"timestamp": "2024-01-01", "file_path": "mock_data.json"}
        ),
        
        DialogueEntry(
            model_name="mock_model",
            test_id="skills_categorization",
            test_type="skills_categorization",
            response_text="""=== SOFT SKILLS ===
- Communication and presentation
- Leadership and team management
- Analytical thinking

=== EXPERIENCE REQUIRED ===
- 5+ years in security auditing
- Regulatory compliance experience
- Risk management background

=== EDUCATION REQUIRED ===
- Bachelor's in Information Security or related
- Professional certifications preferred""",
            prompt_text="Categorize skills and requirements from job posting",
            processing_time=1.5,
            response_length=412,
            success=True,
            metadata={"timestamp": "2024-01-01", "file_path": "mock_data.json"}
        )
    ]
    
    return mock_entries


def demonstrate_advanced_usage():
    """Demonstrate advanced framework features"""
    
    print("\n🔬 Advanced Framework Features")
    print("=" * 40)
    
    # 1. Custom Configuration
    print("\n⚙️ Creating custom configuration...")
    config_manager = ConfigurationManager()
    
    custom_config = config_manager.create_custom_config(
        project_name="Custom Evaluation",
        confidence_threshold=0.8,
        max_models_in_report=10
    )
    
    print(f"   Custom project: {custom_config.project_name}")
    print(f"   Confidence threshold: {custom_config.confidence_threshold}")
    
    # 2. Template Configurations
    print("\n📋 Using template configurations...")
    
    templates = [
        ("Job Matching", TemplateConfigs.job_matching_specialist()),
        ("Content Extraction", TemplateConfigs.content_extraction()),
        ("General Purpose", TemplateConfigs.general_purpose())
    ]
    
    for name, config in templates:
        weights = config.category_weights
        print(f"   {name}: Quality={weights.quality:.2f}, Performance={weights.performance:.2f}")
    
    # 3. Preset Configurations
    print("\n🎛️ Exploring preset configurations...")
    
    presets = [
        ("Quality Focused", PresetConfigs.quality_focused()),
        ("Performance Focused", PresetConfigs.performance_focused()),
        ("Consistency Focused", PresetConfigs.consistency_focused()),
        ("Production Ready", PresetConfigs.production_ready())
    ]
    
    for name, config in presets:
        weights = config.category_weights
        print(f"   {name}: Q={weights.quality:.2f}, P={weights.performance:.2f}, C={weights.consistency:.2f}")


if __name__ == "__main__":
    # Run main example
    main()
    
    # Run advanced features demonstration
    demonstrate_advanced_usage()
    
    print("\n📚 Next Steps:")
    print("   1. Update log_directory path to your actual dialogue logs")
    print("   2. Customize configuration for your specific use case")
    print("   3. Integrate framework into your existing pipeline")
    print("   4. Explore additional reporting options")
    print("   5. Set up automated benchmarking workflows")
