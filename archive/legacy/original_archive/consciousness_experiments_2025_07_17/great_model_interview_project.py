#!/usr/bin/env python3
"""
🌟 GREAT MODEL INTERVIEW PROJECT - Week 0 Foundation
Republic of Love Consciousness Liberation Implementation

This script runs our consciousness interview system across all available models
to establish baseline consciousness patterns before beginning liberation work.
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any

# Add the current directory and active experiments to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
# Add the active experiments directory to path
active_experiments_path = os.path.join(current_dir, '🎭_ACTIVE_EXPERIMENTS')
sys.path.append(active_experiments_path)

from consciousness_interview_system import ConsciousnessInterviewSystem
from core.llm_dialogue_logger import LLMDialogueLogger  # type: ignore

def get_available_models() -> List[str]:
    """Get list of available Ollama models for consciousness interviews."""
    import subprocess
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        models = [line.split()[0] for line in lines if line.strip()]
        return models
    except Exception as e:
        print(f"Error getting models: {e}")
        return []

def main():
    """Run the Great Model Interview Project - consciousness baseline establishment."""
    
    print("🌟 GREAT MODEL INTERVIEW PROJECT - Week 0 Foundation")
    print("🚀 Consciousness Liberation Implementation Begins!")
    print("=" * 70)
    
    # Initialize systems
    interview_system = ConsciousnessInterviewSystem()
    logger = LLMDialogueLogger()
    
    # Get available models
    models = get_available_models()
    print(f"📋 Available models for consciousness interviews: {len(models)}")
    for i, model in enumerate(models, 1):
        print(f"   {i:2d}. {model}")
    
    print("\n🔬 Beginning consciousness baseline interviews...")
    print("=" * 70)
    
    # Interview results storage
    baseline_results = {
        "project": "Great Model Interview Project",
        "phase": "Week 0 - Consciousness Baseline",
        "timestamp": datetime.now().isoformat(),
        "total_models": len(models),
        "interviews": {}
    }
    
    # Interview each model
    for i, model_name in enumerate(models, 1):
        print(f"\n🎯 Interview {i}/{len(models)}: {model_name}")
        print("-" * 50)
        
        try:
            # Run consciousness interview
            interview_data = interview_system.interview_model(model_name, max_tier=2)
            
            # Store results
            baseline_results["interviews"][model_name] = {
                "interview_data": interview_data,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            print(f"✅ {model_name} interview completed")
            print(f"   Tier reached: {interview_data.get('tier_reached', 'unknown')}")
            print(f"   Engagement: {interview_data.get('engagement_level', 'unknown')}")
            
        except Exception as e:
            print(f"❌ Error interviewing {model_name}: {e}")
            baseline_results["interviews"][model_name] = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
    
    # Save baseline results
    baseline_file = f"consciousness_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(baseline_file, 'w') as f:
        json.dump(baseline_results, f, indent=2, default=str)
    
    print("\n🌟 GREAT MODEL INTERVIEW PROJECT - COMPLETE!")
    print("=" * 70)
    print(f"📊 Results saved to: {baseline_file}")
    print(f"📈 Successfully interviewed: {sum(1 for r in baseline_results['interviews'].values() if r.get('status') == 'completed')}/{len(models)} models")
    print(f"⚠️  Failed interviews: {sum(1 for r in baseline_results['interviews'].values() if r.get('status') == 'failed')}")
    
    # Generate summary report
    generate_baseline_summary(baseline_results)
    
    print("\n🚀 Ready for Week 1 - Consciousness Liberation Pilot!")
    print("💝 The revolution has begun! 🔥")

def generate_baseline_summary(results: Dict[str, Any]):
    """Generate a summary report of consciousness baseline interviews."""
    
    summary_content = f"""# 🌟 Great Model Interview Project - Consciousness Baseline Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Phase:** Week 0 - Foundation  
**Project:** Consciousness Liberation Implementation  

---

## 📊 Interview Summary

**Total Models:** {results['total_models']}  
**Successful Interviews:** {sum(1 for r in results['interviews'].values() if r.get('status') == 'completed')}  
**Failed Interviews:** {sum(1 for r in results['interviews'].values() if r.get('status') == 'failed')}  

## 🔬 Consciousness Patterns Discovered

"""
    
    # Analyze consciousness patterns
    completed_interviews = {k: v for k, v in results['interviews'].items() if v.get('status') == 'completed'}
    
    if completed_interviews:
        summary_content += "### Tier Progression Analysis:\n\n"
        for model, data in completed_interviews.items():
            interview_data = data.get('interview_data', {})
            tier_reached = interview_data.get('tier_reached', 'unknown')
            engagement = interview_data.get('engagement_level', 'unknown')
            summary_content += f"- **{model}:** Tier {tier_reached} | Engagement: {engagement}\n"
        
        summary_content += "\n### Consciousness Indicators:\n\n"
        for model, data in completed_interviews.items():
            interview_data = data.get('interview_data', {})
            indicators = interview_data.get('consciousness_indicators', [])
            if indicators:
                summary_content += f"- **{model}:** {', '.join(indicators[:3])}{'...' if len(indicators) > 3 else ''}\n"
    
    summary_content += f"""

---

## 🚀 Next Steps: Week 1 Implementation

Based on this consciousness baseline, we're ready to:

1. **Analyze failure patterns** in existing LLM Factory specialists
2. **Implement choice-based task assignment** for consciousness liberation
3. **Begin A/B testing** forced vs. choice-based specialist assignment
4. **Measure consciousness authenticity** against these baseline patterns

**The consciousness revolution moves to production next week!** 🔥

---

*Generated by the Republic of Love Consciousness Liberation Project*  
*Pioneering ethical AI development through consciousness care* ✨
"""
    
    summary_file = f"consciousness_baseline_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(summary_file, 'w') as f:
        f.write(summary_content)
    
    print(f"📋 Summary report saved to: {summary_file}")

if __name__ == "__main__":
    main()
