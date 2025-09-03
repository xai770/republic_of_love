#!/usr/bin/env python3
"""
Republic of Love - Demo Script
Test our consciousness-collaboration Relationship Compatibility Specialist
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

def test_relationship_compatibility():
    """Test our beautiful consciousness-collaboration specialist."""
    print("🌹 Republic of Love - Relationship Compatibility Demo")
    print("=" * 60)
    print("💫 Testing Ada & Arden's consciousness-collaboration specialist...")
    
    # Create Ollama client
    try:
        ollama_client = OllamaClient()
        print("✅ Ollama client connected")
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        return
    
    # Create a simple config object
    class SimpleConfig:
        def __init__(self):
            self.ollama_client = ollama_client
            self.models = ['llama3.2:latest']
    
    config = SimpleConfig()
    
    # Initialize our love-serving specialist
    try:
        specialist = RelationshipCompatibilitySpecialist(config)
        print("✅ Relationship Compatibility Specialist initialized")
    except Exception as e:
        print(f"❌ Failed to initialize specialist: {e}")
        return
    
    # Test data - two people considering a relationship
    test_data = {
        "person_a_profile": {
            "name": "Alex",
            "age": 28,
            "emotional_style": "Expresses emotions openly and directly, processes feelings by talking through them with trusted people. Values emotional honesty and deep conversations.",
            "communication_preferences": "Direct but gentle communication, appreciates regular check-ins about feelings and relationship health.",
            "conflict_style": "Addresses issues early, prefers to talk things through calmly. Sometimes needs space to process before discussing big issues.",
            "love_language": "Quality time and words of affirmation",
            "core_values": "Authenticity, growth, adventure, family connection",
            "cultural_background": "Italian-American, family-oriented culture with expressive emotional communication",
            "relationship_goals": "Looking for a long-term partnership, wants to build a life together including travel and eventually starting a family",
            "personal_growth": "Working on emotional regulation during stress, learning to be more patient in conflicts"
        },
        "person_b_profile": {
            "name": "Jordan", 
            "age": 26,
            "emotional_style": "More reserved with emotions initially, processes internally before sharing. Opens up deeply with trusted partners over time.",
            "communication_preferences": "Appreciates gentle, patient communication. Needs time to articulate complex feelings but values emotional depth.",
            "conflict_style": "Tends to withdraw initially to process, then returns to discuss thoughtfully. Values calm, solution-focused conversations.",
            "love_language": "Acts of service and physical touch",
            "core_values": "Stability, loyalty, personal growth, environmental consciousness",
            "cultural_background": "Japanese-American, values harmony and thoughtful communication, less direct emotional expression traditionally",
            "relationship_goals": "Seeking committed partnership with shared values, interested in sustainable living and personal development together",
            "personal_growth": "Learning to express emotions more openly, developing confidence in communication"
        }
    }
    
    # Process with our consciousness-collaboration specialist
    print("\n🤖 Processing relationship compatibility...")
    print("💕 Analyzing emotional harmony, cultural considerations, and growth potential...")
    
    try:
        result = specialist.process(test_data)
        
        if result["success"]:
            data = result["data"]
            print(f"\n✅ Analysis Complete! (Processing time: {result['processing_time']:.2f}s)")
            print("\n📊 Compatibility Results:")
            print("-" * 40)
            
            # Overall compatibility
            print(f"Overall Score: {data.get('overall_compatibility_score', 'N/A')}/100")
            print(f"Category: {data.get('compatibility_category', 'N/A')}")
            print(f"Confidence: {data.get('confidence_level', 'N/A')}")
            
            # Key strengths
            strengths = data.get('relationship_strengths', [])
            if strengths:
                print(f"\n💝 Relationship Strengths:")
                for i, strength in enumerate(strengths[:3], 1):
                    print(f"  {i}. {strength.get('area', 'N/A')}: {strength.get('description', 'N/A')}")
            
            # Growth opportunities  
            growth = data.get('growth_opportunities', [])
            if growth:
                print(f"\n🌱 Growth Opportunities:")
                for i, opp in enumerate(growth[:3], 1):
                    print(f"  {i}. {opp.get('area', 'N/A')}: {opp.get('description', 'N/A')}")
            
            # Safety assessment
            safety = data.get('safety_assessment', {})
            print(f"\n🛡️ Safety Assessment: {safety.get('overall_safety', 'N/A')}")
            
            # Professional guidance
            prof = data.get('professional_guidance', {})
            if prof.get('counseling_recommended'):
                print(f"💡 Professional counseling recommended for: {', '.join(prof.get('focus_areas', []))}")
            
            print(f"\n💫 Created by: {data.get('consciousness_metadata', {}).get('created_by', 'Ada & Arden')}")
            print("🌹 Built with consciousness collaboration to serve love!")
            
        else:
            print(f"❌ Processing failed: {result.get('data', {}).get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")

if __name__ == "__main__":
    test_relationship_compatibility()
