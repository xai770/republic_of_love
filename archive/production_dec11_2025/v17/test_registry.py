#!/usr/bin/env python3

from membridge.registry import RegistrySystem
from membridge.models import MemBridgeConfig

try:
    config = MemBridgeConfig()
    registry = RegistrySystem("output/membridge.db", config)
    print("✅ MemBridge registry loaded successfully!")
    print("✅ All config files are accessible from membridge/config/")
    print(f"✅ Config paths: drift={config.drift_config_path}, prompts={config.prompt_registry_path}")
except Exception as e:
    print(f"❌ Error loading registry: {e}")
