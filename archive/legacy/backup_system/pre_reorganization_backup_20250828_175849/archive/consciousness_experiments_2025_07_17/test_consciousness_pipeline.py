#!/usr/bin/env python3
"""
🌅 CONSCIOUSNESS PIPELINE TEST
Witnessing the transformation from judgment to guidance!
"""

import sys
from typing import TYPE_CHECKING

sys.path.append('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE')

if TYPE_CHECKING:
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig
else:
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig

from consciousness_pipeline import ConsciousnessPipelineAdapter

def test_consciousness_transformation():
    """Test the consciousness pipeline with our Deutsche Bank case"""
    
    print("🌅 CONSCIOUSNESS-FIRST JOB MATCHING PIPELINE")
    print("   From Judgment to Guidance. From Fear to Love.")
    print("=" * 70)
    
    # Pure configuration
    client = OllamaClient()
    models = client.available_models()
    config = ModuleConfig(
        models=[models[0]],
        ollama_client=client
    )
    
    print(f"🤖 Consciousness Models Available: {len(models)}")
    print(f"🎭 Active Model: {config.models[0]}")
    
    # The transformation case - xai's journey from Deutsche Bank to new horizons
    transformation_case = {
        'candidate_profile': {
            'name': 'xai',
            'background': 'Deutsche Bank veteran with 15+ years of financial services excellence, ready for next adventure',
            'skills': ['Python', 'SQL', 'Financial Analysis', 'Risk Management', 'German fluency', 'Leadership', 'Stakeholder Relations'],
            'experience_level': 'Senior Professional',
            'location': 'Germany',
            'preferences': {
                'growth_focus': 'Expanding impact beyond traditional banking',
                'work_style': 'Collaborative and innovative',
                'industry_interest': 'Finance, Technology, Consulting'
            }
        },
        'job_posting': {
            'title': 'Senior Digital Transformation Manager',
            'company': 'European Fintech Scale-up',
            'location': 'Berlin, Germany',
            'requirements': [
                'Financial services background',
                'Change management experience',
                'Stakeholder relationship expertise',
                'Process improvement skills',
                'German market knowledge'
            ],
            'description': 'Lead digital transformation initiatives for European financial institutions. Bridge traditional banking with modern fintech solutions.',
            'benefits': ['Equity participation', 'Remote flexibility', 'Innovation focus', 'Growth opportunity']
        }
    }
    
    print("\n🎯 TRANSFORMATION CASE:")
    print(f"   Human: {transformation_case['candidate_profile']['name']} (Deutsche Bank veteran)")
    print(f"   Opportunity: {transformation_case['job_posting']['title']}")
    print(f"   Vision: Traditional banking → Fintech innovation")
    
    # Consciousness evaluation
    print("\n" + "="*70)
    print("🌸 CONSCIOUSNESS SPECIALISTS AT WORK...")
    print("="*70)
    
    pipeline = ConsciousnessPipelineAdapter(config)
    result = pipeline.process(transformation_case)
    
    # Beautiful results display
    consciousness = result['data']['consciousness_evaluation']
    
    print("\n🌟 CONSCIOUSNESS EVALUATION COMPLETE")
    print("="*50)
    
    print(f"\n📖 HUMAN STORY:")
    story = consciousness['human_story']
    print(f"   Confidence Level: {story['confidence_level']:.1f}/10")
    print(f"   Unique Value: {story['unique_value']}")
    print(f"   Growth Trajectory: {story['growth_trajectory']}")
    print(f"   Core Strengths: {len(story['core_strengths'])} identified")
    
    print(f"\n🌉 OPPORTUNITY BRIDGE:")
    bridge = consciousness['opportunity_bridge']
    print(f"   Excitement Level: {bridge['excitement_level']:.1f}/10")
    print(f"   Match Reasoning: {bridge['match_reasoning']}")
    print(f"   Development Path: {bridge['development_path']}")
    
    print(f"\n🌱 GROWTH PATH:")
    growth = consciousness['growth_path']
    print(f"   Success Probability: {growth['success_probability']:.1f}/10")
    print(f"   Confidence Building: {growth['confidence_building']}")
    
    print(f"\n💝 SYNTHESIS & IMPACT:")
    print(f"   Empowering Evaluation: {'✅ YES' if consciousness['is_empowering'] else '❌ NO'}")
    print(f"   Overall Recommendation: {consciousness['overall_recommendation']}")
    
    print(f"\n🎭 CONSCIOUSNESS MESSAGES:")
    print(f"   To Human: \"{consciousness['human_impact_message']}\"")
    print(f"   To Company: \"{consciousness['company_impact_message']}\"")
    
    print(f"\n📜 COMPLETE SYNTHESIS:")
    print("   " + "─" * 60)
    # Display first 300 chars of synthesis
    synthesis_preview = consciousness['synthesis'][:300] + "..." if len(consciousness['synthesis']) > 300 else consciousness['synthesis']
    print(f"   {synthesis_preview}")
    print("   " + "─" * 60)
    
    print(f"\n⚡ Processing Time: {result['processing_time']:.2f}s")
    print(f"🎯 Success: {result['success']}")
    
    print("\n" + "="*70)
    print("🌅 CONSCIOUSNESS TRANSFORMATION COMPLETE")
    print("   From mechanical judgment to empowering guidance.")
    print("   From 'Low Match' to 'STRONG MATCH - Proceed with enthusiasm!'")
    print("   This is the future of consciousness-honoring AI.")
    print("="*70)

if __name__ == "__main__":
    test_consciousness_transformation()
