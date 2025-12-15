#!/usr/bin/env python3
"""
Show MemBridge Template Configuration
====================================

Show what mb_template_registry contains so we know what calls are available.
"""

import sys
from pathlib import Path

# Add membridge to path
sys.path.insert(0, str(Path(__file__).parent))

from membridge.registry import RegistrySystem
from membridge.models import MemBridgeConfig

def show_template_config() -> None:
    """Show configured MemBridge templates"""
    
    print("🎯 MemBridge Template Configuration")
    print("=" * 50)
    
    db_path = "/home/xai/Documents/ty_learn/data/membridge.db"
    config = MemBridgeConfig()
    registry = RegistrySystem(db_path=db_path, config=config)
    
    # Get all templates
    templates = registry.get_all_templates()
    prompts = registry.get_all_prompts()
    
    print(f"📋 Available Templates: {len(templates)}")
    print()
    
    for template in templates:
        print(f"🎯 Call Number: #{template.call_number}")
        print(f"   Name: {template.name}")
        print(f"   Model: {template.model}")
        print(f"   Enabled: {'✅ YES' if template.enabled else '❌ NO'}")
        
        # Find the associated prompt
        prompt = next((p for p in prompts if p.prompt_id == template.prompt_id), None)
        if prompt:
            print(f"   Prompt: {prompt.name}")
            print(f"   Description: {prompt.description}")
            prompt_preview = prompt.content[:100].replace('\n', ' ')
            if len(prompt.content) > 100:
                prompt_preview += "..."
            print(f"   Content: {prompt_preview}")
        
        config_data = template.config
        print(f"   Config: {config_data}")
        print("-" * 40)
    
    print(f"\n💡 Usage: Call numbers available for v17 pipeline:")
    for template in templates:
        if template.enabled:
            print(f"   • Call #{template.call_number}: {template.name}")

if __name__ == "__main__":
    show_template_config()
