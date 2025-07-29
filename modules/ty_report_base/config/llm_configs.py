#!/usr/bin/env python3
"""
Phase 2b Configuration Examples
Authentic LLM integration configurations for production use

No stubs, no mocks, no synthetic data.
"""

import os
from pathlib import Path
from typing import Dict, Any

def get_openai_config() -> Dict[str, Any]:
    """OpenAI GPT configuration for authentic generation"""
    return {
        "provider": "openai",
        "model_name": "gpt-4",  # or gpt-3.5-turbo for cost efficiency
        "api_key": os.getenv('OPENAI_API_KEY'),  # Set in environment
        "max_tokens": 500,
        "temperature": 0.7  # Balance creativity with consistency
    }

def get_anthropic_config() -> Dict[str, Any]:
    """Anthropic Claude configuration for authentic generation"""
    return {
        "provider": "anthropic", 
        "model_name": "claude-3-sonnet-20240229",
        "api_key": os.getenv('ANTHROPIC_API_KEY'),  # Set in environment
        "max_tokens": 500,
        "temperature": 0.7
    }

def get_local_ollama_config(model: str = "qwen3:latest") -> Dict[str, Any]:
    """Local Ollama configuration (requires Ollama running locally)"""
    return {
        "provider": "local_ollama",
        "model_name": model,  # qwen3:latest, mistral:7b, llama2:13b, etc.
        "endpoint": "http://localhost:11434/api/generate",
        "max_tokens": 500,
        "temperature": 0.7
    }

def get_local_llamacpp_config() -> Dict[str, Any]:
    """Local llama.cpp server configuration"""
    return {
        "provider": "local_llamacpp",
        "model_name": "local_model",  # Descriptive name for your local model
        "endpoint": "http://localhost:8080/completion",
        "max_tokens": 500,
        "temperature": 0.7
    }

def validate_llm_config(config: Dict[str, Any]) -> bool:
    """Validate LLM configuration before use"""
    
    required_fields = ["provider", "model_name"]
    for field in required_fields:
        if field not in config:
            print(f"❌ Missing required field: {field}")
            return False
    
    provider = config["provider"]
    
    # Provider-specific validation
    if provider == "openai":
        if not config.get("api_key"):
            print("❌ OpenAI API key required (set OPENAI_API_KEY environment variable)")
            return False
            
    elif provider == "anthropic":
        if not config.get("api_key"):
            print("❌ Anthropic API key required (set ANTHROPIC_API_KEY environment variable)")
            return False
            
    elif provider == "local_ollama":
        # Could add connectivity check here
        print("ℹ️  Local Ollama - ensure Ollama is running: `ollama serve`")
        
    elif provider == "local_llamacpp":
        # Could add connectivity check here
        print("ℹ️  Local llama.cpp - ensure server is running")
        
    else:
        print(f"❌ Unsupported provider: {provider}")
        return False
    
    print(f"✅ LLM configuration validated: {provider}/{config['model_name']}")
    return True

if __name__ == "__main__":
    print("🔧 Phase 2b LLM Configuration Examples\n")
    
    print("Available configurations:")
    print("1. OpenAI GPT-4 (requires API key)")
    print("2. Anthropic Claude (requires API key)")  
    print("3. Local Ollama (requires local Ollama server)")
    print("4. Local llama.cpp (requires local server)")
    
    print(f"\n📋 Example OpenAI config:")
    openai_config = get_openai_config()
    print(f"   Provider: {openai_config['provider']}")
    print(f"   Model: {openai_config['model_name']}")
    print(f"   API Key: {'✅ Set' if openai_config['api_key'] else '❌ Missing'}")
    
    print(f"\n📋 Example Ollama config:")
    ollama_config = get_local_ollama_config()
    print(f"   Provider: {ollama_config['provider']}")
    print(f"   Model: {ollama_config['model_name']}")
    print(f"   Endpoint: {ollama_config['endpoint']}")
    
    print(f"\n🔍 Validation examples:")
    print("OpenAI config:", "✅ Valid" if validate_llm_config(openai_config) else "❌ Invalid")
    print("Ollama config:", "✅ Valid" if validate_llm_config(ollama_config) else "❌ Invalid")
