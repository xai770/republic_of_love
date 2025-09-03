#!/usr/bin/env python3
"""
Elegant Test Suite
Testing pure performance. No mocks. No fallbacks. Just truth.
"""

import sys
from typing import TYPE_CHECKING

sys.path.append('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE')

if TYPE_CHECKING:
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig
else:
    # Runtime imports
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig

from elegant_job_fitness_specialist import ElegantJobFitnessAdapter

def test_elegant_specialist():
    """Test the elegant specialist with Deutsche Bank case"""
    
    print("🏎️  ELEGANT JOB FITNESS SPECIALIST")
    print("   Pure design. No compromises. Like a Lamborghini Miura.")
    print("=" * 60)
    
    # Pure configuration
    client = OllamaClient()
    models = client.available_models()
    config = ModuleConfig(
        models=[models[0]],
        ollama_client=client
    )
    
    print(f"🤖 Using model: {config.models[0]}")
    
    # Elegant test data
    test_case = {
        'candidate_profile': {
            'name': 'xai',
            'background': 'Deutsche Bank veteran, 15+ years financial services excellence',
            'skills': ['Python', 'SQL', 'Financial Analysis', 'Risk Management', 'German fluency'],
            'experience_level': 'Senior',
            'location': 'Germany'
        },
        'job_posting': {
            'title': 'Senior Data Analyst - Financial Services',
            'company': 'European Investment Bank',
            'location': 'Frankfurt, Germany',
            'requirements': [
                '5+ years banking experience',
                'Advanced Python/SQL skills',
                'Risk management expertise',
                'German language advantage'
            ],
            'description': 'Senior analyst role supporting risk analytics and regulatory reporting'
        }
    }
    
    print("\n📋 Evaluating: Deutsche Bank veteran → European Investment Bank")
    
    # Pure execution
    specialist = ElegantJobFitnessAdapter(config)
    result = specialist.process(test_case)
    
    # Elegant results display
    fitness = result.data['fitness_assessment']
    
    print(f"\n🎯 RESULTS:")
    print(f"   Overall Score: {fitness['overall_score']:.1f}/10")
    print(f"   Skill Alignment: {fitness['skill_alignment']:.1f}/10")
    print(f"   Experience Relevance: {fitness['experience_relevance']:.1f}/10")  
    print(f"   Cultural Fit: {fitness['cultural_fit']:.1f}/10")
    print(f"   Recommendation: {fitness['recommendation']}")
    print(f"   Confidence: {fitness['confidence']}")
    print(f"   Strong Match: {'✅ YES' if fitness['is_strong_match'] else '❌ NO'}")
    print(f"   Interview Ready: {'✅ YES' if fitness['interview_ready'] else '❌ NO'}")
    
    print(f"\n💡 Key Insights:")
    for insight in fitness['key_insights']:
        if insight.strip():
            print(f"   • {insight}")
    
    print(f"\n⚡ Processing Time: {result.processing_time:.2f}s")
    print(f"🏁 Success: {result.success}")

if __name__ == "__main__":
    test_elegant_specialist()
