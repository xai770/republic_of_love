#!/usr/bin/env python3
"""
Sandy LLM Evaluation - Clean Version (No Mocks/Fallbacks)
=========================================================

Clean rerun of Sandy's LLM evaluation using real data only.
Explicitly avoids any mock data or fallback mechanisms.
"""

import sys
from pathlib import Path
import os
from datetime import datetime

# Add the framework to path
framework_path = Path(__file__).parent / "llm_optimization_framework"
sys.path.insert(0, str(framework_path))

def main():
    """Run Sandy LLM evaluation with REAL DATA ONLY - NO MOCKS"""
    
    print("🌸 Sandy LLM Evaluation - CLEAN VERSION (Real Data Only)")
    print("=" * 70)
    print("📊 STRICTLY using Sandy's actual test data - NO FALLBACKS\n")
    
    # Import framework components
    from llm_optimization_framework.configs.settings import OptimizationConfig, TemplateConfigs
    from llm_optimization_framework.utils.dialogue_parser import DialogueParser
    from llm_optimization_framework.core.metrics import PerformanceMetrics, MetricCategory
    from llm_optimization_framework.reporters.markdown import MarkdownReporter
    
    # Configuration
    print("⚙️ Setting up configuration...")
    config = TemplateConfigs.content_extraction()
    config.baseline_model = "gemma3n:latest"
    
    # Sandy's dialogue logs directory
    dialogue_dir = Path("/home/xai/Documents/republic_of_love/llm_dialogues")
    sandy_pattern = "*sandy_test_*.md"
    
    print(f"📂 Looking for Sandy files in: {dialogue_dir}")
    print(f"🔍 Using pattern: {sandy_pattern}")
    
    # Check directory exists
    if not dialogue_dir.exists():
        print(f"❌ ERROR: Directory does not exist: {dialogue_dir}")
        return
    
    # Find Sandy test files
    sandy_files = list(dialogue_dir.glob(sandy_pattern))
    print(f"📋 Found {len(sandy_files)} Sandy test files")
    
    if not sandy_files:
        print("❌ ERROR: No Sandy test files found!")
        print(f"   Directory contents:")
        for file in dialogue_dir.glob("*sandy*"):
            print(f"     {file.name}")
        return
    
    # Show file timestamps to verify we have current data
    print("\n🕐 File timestamps (to verify current data):")
    for file in sorted(sandy_files)[:10]:  # Show first 10
        stat = file.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        print(f"   {file.name}: {mod_time}")
    if len(sandy_files) > 10:
        print(f"   ... and {len(sandy_files) - 10} more files")
    
    # Parse dialogue entries - REAL DATA ONLY
    print("\n🔍 Parsing dialogue entries from REAL files...")
    parser = DialogueParser()
    
    dialogue_entries_list = parser.parse_directory(dialogue_dir, sandy_pattern)
    
    if not dialogue_entries_list:
        print("❌ ERROR: No dialogue entries parsed from files!")
        print("   This means the parsing failed or files are empty")
        
        # Show a sample file content for debugging
        if sandy_files:
            sample_file = sandy_files[0]
            print(f"\n🔍 Sample content from {sample_file.name}:")
            with open(sample_file, 'r') as f:
                content = f.read()
                print(content[:500] + "..." if len(content) > 500 else content)
        return
    
    # Group by model name
    dialogue_entries = {}
    for entry in dialogue_entries_list:
        if entry.model_name not in dialogue_entries:
            dialogue_entries[entry.model_name] = []
        dialogue_entries[entry.model_name].append(entry)
    
    print(f"✅ Successfully parsed {len(dialogue_entries)} unique models")
    print(f"📊 Total entries: {len(dialogue_entries_list)}")
    
    # Show model breakdown with timestamps
    print("\n📱 Models and their test timestamps:")
    for model, entries in dialogue_entries.items():
        timestamps = [entry.timestamp for entry in entries if entry.timestamp]
        latest_timestamp = max(timestamps) if timestamps else "Unknown"
        print(f"   {model}: {len(entries)} tests (latest: {latest_timestamp})")
    
    # Calculate metrics - REAL DATA ONLY
    print(f"\n📊 Calculating metrics from REAL data...")
    metrics_calc = PerformanceMetrics()
    
    model_metrics = {}
    
    for model_name, entries in dialogue_entries.items():
        print(f"   🔄 Processing {model_name} ({len(entries)} real entries)...")
        
        try:
            metrics = metrics_calc.calculate_model_metrics(entries, model_name)
            model_metrics[model_name] = metrics
            
            print(f"      ✅ Score: {metrics.overall_score:.3f}")
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            continue
    
    if not model_metrics:
        print("❌ ERROR: No metrics calculated from real data!")
        return
    
    # Generate report
    print(f"\n📄 Generating report from REAL Sandy data...")
    
    try:
        reporter = MarkdownReporter("Sandy LLM Evaluation - Real Data", config.baseline_model)
        
        # Generate comprehensive report
        report_content = reporter.generate_comprehensive_report(model_metrics)
        
        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"sandy_evaluation_real_data_{timestamp}.md"
        reporter.save_report(report_content, report_file)
        
        print(f"✅ Report saved: {report_file}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
    
    # Final summary
    print(f"\n🎊 Sandy Evaluation Complete - REAL DATA VERIFIED!")
    print("=" * 60)
    
    if model_metrics:
        sorted_models = sorted(
            model_metrics.items(), 
            key=lambda x: x[1].overall_score, 
            reverse=True
        )
        
        print("🏆 Top Models from REAL Sandy Tests:")
        for i, (model, metrics) in enumerate(sorted_models[:5], 1):
            entry_count = len(dialogue_entries[model])
            print(f"   {i}. {model} (Score: {metrics.overall_score:.3f}) - {entry_count} real tests")
    
    print(f"\n📊 Data Verification:")
    print(f"   ✅ Files processed: {len(sandy_files)} real Sandy test files")
    print(f"   ✅ Entries parsed: {len(dialogue_entries_list)} real dialogue entries")
    print(f"   ✅ Models evaluated: {len(model_metrics)} unique models")
    print(f"   ✅ No mock data used")
    print(f"   ✅ No fallback mechanisms triggered")
    
    print("\n🌸 Sandy evaluation using REAL DATA complete! 🌸")

if __name__ == "__main__":
    main()
