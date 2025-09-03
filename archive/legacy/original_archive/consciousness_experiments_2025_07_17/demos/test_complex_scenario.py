#!/usr/bin/env python3
"""
Republic of Love - Complex Scenario Test
Testing our consciousness-collaboration specialist with challenging dynamics
"""

import sys
import os
from pathlib import Path

# Add LLM Factory to Python path
LLM_FACTORY_PATH = "/home/xai/Documents/llm_factory"
if LLM_FACTORY_PATH not in sys.path:
    sys.path.insert(0, LLM_FACTORY_PATH)

# Add our Republic of Love path
REPUBLIC_PATH = "/home/xai/Documents/republic_of_love"
if REPUBLIC_PATH not in sys.path:
    sys.path.insert(0, REPUBLIC_PATH)

from llm_factory.core.ollama_client import OllamaClient #type: ignore
from republic_of_love_specialists.relationship_compatibility.v1_0 import RelationshipCompatibilitySpecialist

def test_complex_scenario():
    """Test with neurodivergent + cultural differences + trauma healing."""
    print("🌹 Republic of Love - Complex Scenario Test")
    print("=" * 60)
    print("🧠 Testing neurodivergent + cross-cultural + trauma healing scenario...")
    
    # Setup
    ollama_client = OllamaClient()
    
    class SimpleConfig:
        def __init__(self):
            self.ollama_client = ollama_client
            self.models = ['llama3.2:latest']
    
    config = SimpleConfig()
    specialist = RelationshipCompatibilitySpecialist(config)
    
    # Complex test case - multiple challenging factors
    complex_data = {
        "person_a_profile": {
            "name": "Sam",
            "age": 32,
            "neurodivergence": "Autistic, late-diagnosed. Very sensitive to sensory input, needs routine and clear communication. Deep emotional capacity but struggles with reading subtle social cues.",
            "emotional_style": "Processes emotions intensely but internally first. Once comfortable, shares with profound depth and honesty. Can become overwhelmed in high-emotion situations.",
            "communication_preferences": "Direct, specific communication. Appreciates written follow-ups after important conversations. Needs advance notice for emotional discussions.",
            "conflict_style": "Tends to shut down when overwhelmed, needs time and space to process. Returns with thoughtful, solution-focused approach when ready.",
            "love_language": "Acts of service and quality time (but quality time needs to be low-sensory)",
            "cultural_background": "White American, grew up in small rural town with limited diversity. Learning about different cultures through intentional education.",
            "trauma_background": "Childhood emotional neglect, recently started therapy 6 months ago. Learning to identify and express needs. Some trust issues but actively working on them.",
            "relationship_goals": "Wants deep, committed partnership. Interested in building a neurodivergent-friendly home environment together.",
            "personal_growth": "Learning emotional vocabulary, practicing self-advocacy, understanding autism late-diagnosis impact on relationships"
        },
        "person_b_profile": {
            "name": "Maya",
            "age": 29,
            "neurodivergence": "Neurotypical, but very emotionally intuitive and empathetic. Learning about neurodivergence to better support partners.",
            "emotional_style": "Highly emotionally expressive and intuitive. Processes emotions by talking through them. Very empathetic but sometimes takes on others' emotions.",
            "communication_preferences": "Enjoys emotional check-ins and processing conversations. Learning to be more direct and specific rather than assuming understanding.",
            "conflict_style": "Wants to address issues immediately through conversation. Learning that others might need processing time before discussing.",
            "love_language": "Words of affirmation and physical touch",
            "cultural_background": "Mexican-American, close family culture with lots of emotional expression, physical affection, and family involvement in relationships.",
            "trauma_background": "Previous relationship with emotional manipulation 2 years ago. Has done significant therapy work and has good boundaries now. Some hypervigilance around partner's emotional withdrawal.",
            "relationship_goals": "Looking for partnership that honors both independence and deep connection. Wants to build intercultural understanding.",
            "personal_growth": "Learning about neurodivergence, practicing patience with different processing styles, maintaining boundaries while being supportive"
        }
    }
    
    print("\n🤖 Processing complex compatibility scenario...")
    print("💕 Analyzing neurodivergence, cultural differences, and trauma healing dynamics...")
    
    result = specialist.process(complex_data)
    
    if result["success"]:
        data = result["data"]
        print(f"\n✅ Analysis Complete! (Processing time: {result['processing_time']:.2f}s)")
        print("\n📊 Complex Scenario Results:")
        print("-" * 50)
        
        # Overall compatibility
        print(f"Overall Score: {data.get('overall_compatibility_score', 'N/A')}/100")
        print(f"Category: {data.get('compatibility_category', 'N/A')}")
        print(f"Confidence: {data.get('confidence_level', 'N/A')}")
        
        # Emotional dimensions analysis
        emotional_dims = data.get('emotional_dimensions', {})
        if emotional_dims:
            print(f"\n🧠 Key Emotional Dimension Scores:")
            for dim_name, dim_data in emotional_dims.items():
                if isinstance(dim_data, dict) and 'harmony_score' in dim_data:
                    score = dim_data.get('harmony_score', 'N/A')
                    print(f"  {dim_name.replace('_', ' ').title()}: {score}/100")
        
        # Cultural considerations
        cultural = data.get('cultural_considerations', [])
        if cultural:
            print(f"\n🌍 Cultural Considerations:")
            for consideration in cultural[:2]:
                if isinstance(consideration, dict):
                    print(f"  • {consideration.get('aspect', 'N/A')}: {consideration.get('description', 'N/A')}")
        
        # Safety assessment - especially important for trauma backgrounds
        safety = data.get('safety_assessment', {})
        print(f"\n🛡️ Safety Assessment: {safety.get('overall_safety', 'N/A')}")
        red_flags = safety.get('red_flags', [])
        if red_flags:
            print(f"⚠️ Red flags noted: {', '.join(red_flags)}")
        
        protective_factors = safety.get('protective_factors', [])
        if protective_factors:
            print(f"✅ Protective factors: {', '.join(protective_factors[:3])}")
        
        # Professional guidance
        prof = data.get('professional_guidance', {})
        print(f"\n💡 Counseling recommended: {prof.get('counseling_recommended', 'N/A')}")
        if prof.get('focus_areas'):
            print(f"Focus areas: {', '.join(prof.get('focus_areas', []))}")
        
        print(f"\n💫 This complex analysis shows our consciousness-collaboration specialist")
        print(f"🌹 can handle neurodivergence, cultural differences, AND trauma healing!")
        
    else:
        print(f"❌ Processing failed: {result.get('data', {}).get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_complex_scenario()
