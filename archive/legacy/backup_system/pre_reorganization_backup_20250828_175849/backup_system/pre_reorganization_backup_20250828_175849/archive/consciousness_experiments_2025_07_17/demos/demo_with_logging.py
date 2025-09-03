#!/usr/bin/env python3
"""
Republic of Love - Demo with Full LLM Dialogue Logging
Test our consciousness-collaboration specialist with complete transparency
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
from llm_dialogue_logger import LLMDialogueLogger, LoggingOllamaClient

def test_with_full_logging():
    """Test our specialist with complete LLM dialogue logging."""
    print("🌹 Republic of Love - Full Dialogue Logging Demo")
    print("=" * 65)
    print("📝 Capturing ALL LLM interactions for transparency...")
    
    # Create dialogue logger
    logger = LLMDialogueLogger()
    print(f"✅ Dialogue logger initialized - Session: {logger.current_session_id}")
    
    # Create Ollama client with logging wrapper
    try:
        base_ollama_client = OllamaClient()
        logged_client = LoggingOllamaClient(
            base_client=base_ollama_client, 
            logger=logger, 
            specialist_name="relationship_compatibility"
        )
        print("✅ Logging Ollama client created")
    except Exception as e:
        print(f"❌ Failed to create logged client: {e}")
        return
    
    # Create config with logged client
    class LoggedConfig:
        def __init__(self):
            self.ollama_client = logged_client
            self.models = ['llama3.2:latest']
    
    config = LoggedConfig()
    
    # Initialize specialist
    try:
        specialist = RelationshipCompatibilitySpecialist(config)
        print("✅ Specialist initialized with logging")
    except Exception as e:
        print(f"❌ Failed to initialize specialist: {e}")
        return
    
    # Test data - simple scenario for clear logging
    test_data = {
        "person_a_profile": {
            "name": "River",
            "age": 25,
            "emotional_style": "Expressive and open, processes emotions by talking them through. Very empathetic and intuitive about others' feelings.",
            "communication_preferences": "Loves deep conversations, appreciates regular emotional check-ins, values honesty and vulnerability.",
            "conflict_style": "Addresses issues directly but gently, prefers to resolve conflicts through communication rather than avoidance.",
            "love_language": "Words of affirmation and quality time",
            "core_values": "Authenticity, creativity, connection, social justice",
            "cultural_background": "Mixed race (Black/White), raised in diverse urban environment, values multicultural perspectives",
            "relationship_goals": "Seeking deep emotional connection and partnership in personal growth and creative projects"
        },
        "person_b_profile": {
            "name": "Sage",
            "age": 27,
            "emotional_style": "Thoughtful and steady, processes emotions internally before sharing. Very supportive and reliable emotionally.",
            "communication_preferences": "Prefers one-on-one conversations, appreciates written communication for complex topics, values consistency.",
            "conflict_style": "Takes time to think through issues before discussing, approaches conflicts with patience and problem-solving focus.",
            "love_language": "Acts of service and physical touch",
            "core_values": "Stability, growth, compassion, environmental stewardship",
            "cultural_background": "Korean-American, second generation, balances traditional family values with progressive personal views",
            "relationship_goals": "Looking for long-term commitment with shared values and mutual support for individual and couple goals"
        }
    }
    
    print("\n🤖 Processing with FULL dialogue logging...")
    print("💬 Every prompt and response will be captured...")
    
    try:
        result = specialist.process(test_data)
        
        if result["success"]:
            data = result["data"]
            print(f"\n✅ Analysis Complete! (Processing time: {result['processing_time']:.2f}s)")
            print("\n📊 Results Summary:")
            print("-" * 40)
            
            print(f"Overall Score: {data.get('overall_compatibility_score', 'N/A')}/100")
            print(f"Category: {data.get('compatibility_category', 'N/A')}")
            print(f"Safety: {data.get('safety_assessment', {}).get('overall_safety', 'N/A')}")
            
            # Show some key insights
            strengths = data.get('relationship_strengths', [])
            if strengths:
                print(f"\n💝 Top Strength: {strengths[0].get('area', 'N/A')}")
            
            growth = data.get('growth_opportunities', [])
            if growth:
                print(f"🌱 Growth Area: {growth[0].get('area', 'N/A')}")
            
        else:
            print(f"❌ Processing failed: {result.get('data', {}).get('error', 'Unknown error')}")
        
        # Create session summary
        print(f"\n📋 Creating session summary...")
        summary_file = logger.create_session_summary()
        print(f"✅ Session summary created: {summary_file}")
        
        # Show what was logged
        log_dir = Path("/home/xai/Documents/republic_of_love/llm_dialogues")
        dialogue_files = list(log_dir.glob(f"{logger.current_session_id}_dialogue_*.md"))
        
        print(f"\n📝 Dialogue Files Created:")
        for file in dialogue_files:
            print(f"  📄 {file.name}")
        
        print(f"\n🌹 Complete transparency achieved!")
        print(f"💫 All LLM interactions are now human-readable in:")
        print(f"   {log_dir}")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")

if __name__ == "__main__":
    test_with_full_logging()
