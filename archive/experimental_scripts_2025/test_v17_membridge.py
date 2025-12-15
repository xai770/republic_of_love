#!/usr/bin/env python3
"""
Test V17 Production Pipeline with MemBridge
===========================================

Run the v17 production pipeline with sample data and track MemBridge calls.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add production v17 to path
sys.path.insert(0, str(Path(__file__).parent / "production" / "v17"))

# Add membridge to path for monitoring
sys.path.insert(0, str(Path(__file__).parent))

from membridge.registry import RegistrySystem
from membridge.models import MemBridgeConfig

def test_v17_with_membridge() -> None:
    """Test v17 pipeline and monitor MemBridge calls"""
    
    print("🧪 Testing V17 Production Pipeline with MemBridge")
    print("=" * 60)
    
    # Get baseline call count
    db_path = "/home/xai/Documents/ty_learn/data/membridge.db"
    config = MemBridgeConfig()
    registry = RegistrySystem(db_path=db_path, config=config)
    
    baseline_calls = registry.get_recent_calls(limit=100)
    baseline_count = len(baseline_calls)
    
    print(f"📊 Baseline: {baseline_count} calls in MemBridge")
    print()
    
    # Show available templates
    templates = registry.get_all_templates()
    print("🎯 Available MemBridge Templates:")
    for template in templates:
        if template.enabled:
            print(f"   • Call #{template.call_number}: {template.name} ({template.model})")
    print()
    
    # Check for sample data
    data_dir = Path("data/postings")
    job_files = list(data_dir.glob("*.json"))
    
    if not job_files:
        print("❌ No job files found in data/postings")
        return
    
    print(f"📂 Found {len(job_files)} job files in {data_dir}")
    
    # Test with one job file
    test_file = job_files[0]
    print(f"🎯 Testing with: {test_file.name}")
    
    try:
        # Load job data
        with open(test_file, 'r') as f:
            job_data = json.load(f)
        
        print(f"✅ Loaded job data: {job_data.get('title', 'Unknown Title')}")
        
        # Now try to import and run v17 pipeline components
        try:
            from membridge_llm_interface_simple import MemBridgeLLMInterface
            
            print("🔧 Initializing V17 MemBridge interface...")
            
            # Create minimal config for testing
            class TestConfig:
                def __init__(self):
                    self.llm_model = "gemma3:1b"
                    self.data_dir = Path("data/postings")
                    self.output_dir = Path("output")
            
            config = TestConfig()
            
            # Initialize MemBridge LLM interface
            llm_interface = MemBridgeLLMInterface(config)
            print("✅ MemBridge LLM interface initialized")
            
            # Test skill extraction (Call #1)
            print("\n🎯 Testing skill extraction with MemBridge...")
            job_description = job_data.get('description', job_data.get('content', 'No description available'))
            if isinstance(job_description, list):
                job_description = ' '.join(job_description)
            job_description = str(job_description)[:2000]  # Limit length
            job_title = job_data.get('title', 'Unknown Job')
            
            print(f"   • Job: {job_title}")
            print(f"   • Description length: {len(job_description)} characters")
            
            skills = llm_interface.extract_skills(job_description, job_title)
            print(f"✅ Skills extracted successfully!")
            print(f"   • Technical: {len(skills.technical)} skills")
            print(f"   • Business: {len(skills.business)} skills")
            print(f"   • Soft: {len(skills.soft)} skills")
            
            # Test concise description (Call #2)
            print("\n📝 Testing concise description with MemBridge...")
            description = llm_interface.extract_concise_description(job_description, job_title)
            print(f"✅ Concise description generated!")
            print(f"   • Length: {len(description)} characters")
            print(f"   • Preview: {description[:150]}...")
            
        except ImportError as e:
            print(f"❌ Could not import v17 components: {e}")
            print("💡 This might be expected - let's check MemBridge calls anyway")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Check new call count
    print("\n📊 MemBridge Call Analysis:")
    print("-" * 30)
    
    new_calls = registry.get_recent_calls(limit=100)
    new_count = len(new_calls)
    added_calls = new_count - baseline_count
    
    print(f"   • Baseline calls: {baseline_count}")
    print(f"   • Current calls: {new_count}")
    print(f"   • New calls added: {added_calls}")
    
    if added_calls > 0:
        print(f"\n🎯 New calls details:")
        for call in new_calls[:added_calls]:
            status = "✅" if call.success else "❌"
            print(f"   • {status} Call #{call.call_number} - {call.latency_ms:.1f}ms")
            if call.input_text:
                preview = call.input_text[:50].replace('\n', ' ')
                print(f"     Input: {preview}...")
            if call.output_text:
                output_preview = call.output_text[:50].replace('\n', ' ')
                print(f"     Output: {output_preview}...")
    
    print(f"\n🎯 Test completed! Check SQLite Browser for updated mb_log table")

if __name__ == "__main__":
    test_v17_with_membridge()
    """Test v17 MemBridge integration"""
    print("Testing v17 MemBridge integration...")
    
    # Test 1: Extract skills from job description
    job_description = """
    We are looking for a Senior Python Developer with experience in:
    - Django and Flask frameworks
    - PostgreSQL and MongoDB databases
    - AWS cloud services
    - Docker containerization
    - API development and testing
    """

if __name__ == "__main__":
    test_v17_membridge()
    sys.exit(0)
