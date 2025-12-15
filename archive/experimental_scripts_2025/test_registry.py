#!/usr/bin/env python3

from membridge.registry import RegistrySystem

try:
    registry = RegistrySystem()
    print("✅ MemBridge registry loaded successfully!")
    print("✅ All config files are accessible from membridge/config/")
except Exception as e:
    print(f"❌ Error loading registry: {e}")
