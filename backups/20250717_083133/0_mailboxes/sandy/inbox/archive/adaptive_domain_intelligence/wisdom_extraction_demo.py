#!/usr/bin/env python3
"""
🎯 Wisdom Extraction Demo - Phase 1 Implementation
===============================================

This script demonstrates our Wisdom Extraction phase by analyzing the 9-job systematic
review dataset and extracting learnable decision patterns from Sandy's domain expertise.

This is the foundation of our adaptive intelligence system - learning from human wisdom
rather than following hardcoded rules.
"""

import sys
from pathlib import Path

# Add the workspace to Python path
workspace_path = Path("/home/xai/Documents/republic_of_love")
sys.path.append(str(workspace_path))

from wisdom_extraction_engine import WisdomExtractionEngine

def main():
    print("🌟 Adaptive Domain Intelligence - Wisdom Extraction Demo")
    print("=" * 60)
    print("Phase 1: Learning from Sandy's 9-Job Systematic Review")
    print()
    
    # Initialize the wisdom extraction engine
    engine = WisdomExtractionEngine()
    
    # Define our 9-job systematic review dataset
    dialogue_files = [
        # DeepSeek career analyst dialogues (core expertise)
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_131215_dialogue_001_deepseek_career_analyst.md",
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_131840_dialogue_001_deepseek_career_analyst.md",
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_134008_dialogue_001_deepseek_career_analyst.md",
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_134222_dialogue_001_deepseek_career_analyst.md",
        
        # DeepSeek application strategist dialogues (strategic thinking)
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_131840_dialogue_002_deepseek_application_strategist.md",
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_134008_dialogue_002_deepseek_application_strategist.md",
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_134222_dialogue_002_deepseek_application_strategist.md",
        
        # Consciousness-based approach preferences
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_125741_dialogue_001_job_search_consciousness_deepseek.md",
        
        # Systematic strategy examples
        "/home/xai/Documents/republic_of_love/llm_dialogues/20250617_135653_dialogue_003_qwen3_systematic_strategy.md"
    ]
    
    print(f"📊 Analyzing {len(dialogue_files)} expert decision dialogues...")
    print()
    
    # Extract patterns from individual files
    all_patterns = []
    successful_extractions = 0
    
    for dialogue_file in dialogue_files:
        if Path(dialogue_file).exists():
            print(f"🔍 Extracting from: {Path(dialogue_file).name}")
            patterns = engine.extract_decision_patterns_from_dialogue(dialogue_file)
            all_patterns.extend(patterns)
            if patterns:
                successful_extractions += 1
                print(f"   ✅ {len(patterns)} patterns extracted")
            else:
                print(f"   ⚠️  No patterns found")
        else:
            print(f"   ❌ File not found: {Path(dialogue_file).name}")
        print()
    
    print(f"📈 Extraction Complete: {len(all_patterns)} total patterns from {successful_extractions} files")
    print()
    
    # Build wisdom profiles for different expert types
    print("🎯 Building Expert Wisdom Profiles...")
    print()
    
    # Sandy's DeepSeek Career Analysis expertise
    deepseek_files = [f for f in dialogue_files if "deepseek_career" in f]
    if deepseek_files:
        sandy_career_profile = engine.build_wisdom_profile("sandy_career_analyst", deepseek_files)
        print(f"✅ Sandy Career Analyst Profile: {len(sandy_career_profile.decision_patterns)} patterns")
    
    # Sandy's Strategic Application expertise  
    strategist_files = [f for f in dialogue_files if "application_strategist" in f]
    if strategist_files:
        sandy_strategist_profile = engine.build_wisdom_profile("sandy_application_strategist", strategist_files)
        print(f"✅ Sandy Application Strategist Profile: {len(sandy_strategist_profile.decision_patterns)} patterns")
    
    # Consciousness-driven approach
    consciousness_files = [f for f in dialogue_files if "consciousness" in f]
    if consciousness_files:
        consciousness_profile = engine.build_wisdom_profile("consciousness_approach", consciousness_files)
        print(f"✅ Consciousness Approach Profile: {len(consciousness_profile.decision_patterns)} patterns")
    
    # Systematic strategy approach
    systematic_files = [f for f in dialogue_files if "systematic_strategy" in f]
    if systematic_files:
        systematic_profile = engine.build_wisdom_profile("systematic_strategy", systematic_files)
        print(f"✅ Systematic Strategy Profile: {len(systematic_profile.decision_patterns)} patterns")
    
    print()
    
    # Save extracted wisdom
    print("💾 Saving Extracted Wisdom...")
    wisdom_file = engine.save_wisdom_data("phase1_extracted_wisdom.json")
    print(f"✅ Wisdom data saved to: {wisdom_file}")
    print()
    
    # Generate learning report
    print("📋 Generating Learning Report...")
    report = engine.generate_learning_report()
    
    report_file = engine.data_path / "phase1_wisdom_extraction_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Report saved to: {report_file}")
    print()
    
    # Display key insights
    print("🧠 Key Insights from Wisdom Extraction:")
    print("-" * 40)
    
    total_experts = len(engine.wisdom_profiles)
    total_patterns = len(engine.pattern_library)
    domains = set([p.domain for p in engine.pattern_library.values()])
    
    print(f"• Extracted wisdom from {total_experts} expert perspectives")
    print(f"• Identified {total_patterns} learnable decision patterns")
    print(f"• Covering {len(domains)} domain areas: {', '.join(sorted(domains))}")
    print()
    
    # Show pattern insights
    if engine.pattern_library:
        avg_confidence = sum([p.confidence_level for p in engine.pattern_library.values()]) / len(engine.pattern_library)
        avg_transferability = sum([p.transferability_score for p in engine.pattern_library.values()]) / len(engine.pattern_library)
        
        print(f"• Average pattern confidence: {avg_confidence:.2f}")
        print(f"• Average transferability: {avg_transferability:.2f}")
        print()
    
    # Show most transferable patterns
    if engine.pattern_library:
        transferable_patterns = sorted(
            [p for p in engine.pattern_library.values()], 
            key=lambda x: x.transferability_score, 
            reverse=True
        )[:3]
        
        print("🚀 Most Transferable Patterns:")
        for i, pattern in enumerate(transferable_patterns, 1):
            print(f"   {i}. {pattern.wisdom_essence} (transferability: {pattern.transferability_score:.2f})")
        print()
    
    print("🎯 Next Steps:")
    print("1. Review extracted patterns in the report")
    print("2. Begin Phase 2: Build Contextual Intelligence")
    print("3. Design Pattern Recognition Engine")
    print("4. Implement adaptive threshold learning")
    print()
    print("💡 The foundation for adaptive domain intelligence is now in place!")
    print("   Sandy's expertise has been encoded as learnable patterns,")
    print("   ready to power our consciousness-driven classification system.")

if __name__ == "__main__":
    main()
