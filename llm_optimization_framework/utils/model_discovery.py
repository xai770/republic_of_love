#!/usr/bin/env python3
"""
Model Discovery Module
=====================

Automatically discover available LLM models at runtime.
Supports Ollama local models and can be extended for API models.
"""

import subprocess
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelInfo:
    """Information about a discovered model"""
    name: str
    full_name: str
    size: Optional[str] = None
    family: Optional[str] = None
    modified: Optional[str] = None
    available: bool = True
    provider: str = "ollama"
    
    @property
    def size_gb(self) -> float:
        """Convert size string to GB float"""
        if not self.size:
            return 0.0
        
        size_str = self.size.lower()
        if 'gb' in size_str:
            return float(size_str.replace('gb', '').strip())
        elif 'mb' in size_str:
            return float(size_str.replace('mb', '').strip()) / 1024
        elif 'kb' in size_str:
            return float(size_str.replace('kb', '').strip()) / (1024 * 1024)
        
        return 0.0


class ModelDiscovery:
    """Discover available LLM models from various sources"""
    
    def __init__(self):
        self.ollama_available = self._check_ollama_available()
        self._model_cache: Optional[List[ModelInfo]] = None
        
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            result = subprocess.run(
                ["ollama", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def discover_ollama_models(self) -> List[ModelInfo]:
        """Discover locally available Ollama models"""
        if not self.ollama_available:
            return []
        
        try:
            # Get model list
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            models = []
            lines = result.stdout.strip().split('\n')
            
            # Skip header line
            if len(lines) <= 1:
                return []
            
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    full_name = parts[0]
                    model_id = parts[1] if len(parts) > 1 else ""
                    size = parts[2] if len(parts) > 2 else ""
                    modified = " ".join(parts[3:]) if len(parts) > 3 else ""
                    
                    # Extract base name and family
                    base_name = full_name.split(':')[0]
                    family = self._get_model_family(base_name)
                    
                    model_info = ModelInfo(
                        name=base_name,
                        full_name=full_name,
                        size=size,
                        family=family,
                        modified=modified,
                        available=True,
                        provider="ollama"
                    )
                    models.append(model_info)
            
            return models
            
        except Exception as e:
            print(f"Error discovering Ollama models: {e}")
            return []
    
    def _get_model_family(self, model_name: str) -> str:
        """Determine model family from name"""
        name_lower = model_name.lower()
        
        # Common model families
        if 'llama' in name_lower:
            return 'llama'
        elif 'gemma' in name_lower:
            return 'gemma'
        elif 'qwen' in name_lower:
            return 'qwen'
        elif 'deepseek' in name_lower:
            return 'deepseek'
        elif 'phi' in name_lower:
            return 'phi'
        elif 'mistral' in name_lower:
            return 'mistral'
        elif 'dolphin' in name_lower:
            return 'dolphin'
        elif 'olmo' in name_lower:
            return 'olmo'
        elif 'codegemma' in name_lower or 'code' in name_lower:
            return 'code'
        else:
            return 'other'
    
    def get_available_models(self, refresh: bool = False) -> List[ModelInfo]:
        """Get all available models, with optional caching"""
        if not refresh and self._model_cache is not None:
            return self._model_cache
        
        models = []
        
        # Discover Ollama models
        if self.ollama_available:
            ollama_models = self.discover_ollama_models()
            models.extend(ollama_models)
        
        # Cache results
        self._model_cache = models
        return models
    
    def get_models_by_family(self, family: Optional[str] = None) -> Dict[str, List[ModelInfo]]:
        """Group models by family"""
        models = self.get_available_models()
        
        if family:
            return {family: [m for m in models if m.family == family]}
        
        families: Dict[str, List[ModelInfo]] = {}
        for model in models:
            family_name = model.family or "unknown"
            if family_name not in families:
                families[family_name] = []
            families[family_name].append(model)
        
        return families
    
    def get_models_by_size(self, max_size_gb: Optional[float] = None) -> List[ModelInfo]:
        """Filter models by size"""
        models = self.get_available_models()
        
        if max_size_gb is None:
            return models
        
        return [m for m in models if m.size_gb <= max_size_gb]
    
    def get_recommended_models(self, task_type: str = "general") -> List[ModelInfo]:
        """Get recommended models for specific tasks"""
        models = self.get_available_models()
        
        if task_type == "general":
            # Prefer balanced models
            preferred_families = ['llama', 'qwen', 'gemma', 'mistral']
        elif task_type == "coding":
            # Prefer code-focused models
            preferred_families = ['code', 'deepseek', 'qwen']
        elif task_type == "analysis":
            # Prefer reasoning models
            preferred_families = ['deepseek', 'qwen', 'phi']
        elif task_type == "fast":
            # Prefer smaller, faster models
            return [m for m in models if m.size_gb < 3.0]
        else:
            return models
        
        # Sort by preference and size
        recommended = []
        for family in preferred_families:
            family_models = [m for m in models if m.family == family]
            # Sort by size (smaller first for speed)
            family_models.sort(key=lambda x: x.size_gb)
            recommended.extend(family_models)
        
        # Add remaining models
        remaining = [m for m in models if m.family not in preferred_families]
        remaining.sort(key=lambda x: x.size_gb)
        recommended.extend(remaining)
        
        return recommended
    
    def print_discovery_summary(self):
        """Print a summary of discovered models"""
        models = self.get_available_models()
        
        if not models:
            print("❌ No models discovered")
            return
        
        print(f"🤖 Discovered {len(models)} available models:")
        print("=" * 60)
        
        # Group by family
        families = self.get_models_by_family()
        
        for family, family_models in sorted(families.items()):
            print(f"\n📂 {family.upper()} Family ({len(family_models)} models):")
            
            # Sort by size
            family_models.sort(key=lambda x: x.size_gb)
            
            for model in family_models:
                size_str = f"{model.size_gb:.1f}GB" if model.size_gb > 0 else "Unknown"
                print(f"   • {model.full_name:<25} ({size_str})")
        
        # Show size summary
        total_size = sum(m.size_gb for m in models)
        avg_size = total_size / len(models)
        small_models = len([m for m in models if m.size_gb < 3.0])
        
        print(f"\n📊 Size Summary:")
        print(f"   • Total size: {total_size:.1f}GB")
        print(f"   • Average size: {avg_size:.1f}GB")
        print(f"   • Small models (<3GB): {small_models}")
        print(f"   • Large models (≥3GB): {len(models) - small_models}")
    
    def get_healthy_models(self, timeout: int = 30) -> List[str]:
        """Get list of healthy model names by testing them"""
        from .ollama_interface import OllamaInterface
        
        models = self.get_available_models()
        ollama = OllamaInterface()
        healthy_models = []
        
        print(f"Testing {len(models)} models for health...")
        
        for model_info in models:
            health_result = ollama.test_model_health(model_info.full_name, timeout)
            if health_result["healthy"]:
                healthy_models.append(model_info.full_name)
                print(f"  ✅ {model_info.full_name} ({health_result['duration']:.1f}s)")
            else:
                print(f"  ❌ {model_info.full_name} - {health_result.get('error', 'unhealthy')}")
        
        return healthy_models

def get_available_model_names(include_tags: bool = True) -> List[str]:
    """Convenience function to get just model names"""
    discovery = ModelDiscovery()
    models = discovery.get_available_models()
    
    if include_tags:
        return [m.full_name for m in models]
    else:
        return [m.name for m in models]


def get_fast_models(max_size_gb: float = 3.0) -> List[str]:
    """Get names of fast (small) models"""
    discovery = ModelDiscovery()
    models = discovery.get_models_by_size(max_size_gb)
    return [m.full_name for m in models]


def get_model_info(model_name: str) -> Optional[ModelInfo]:
    """Get detailed info for a specific model"""
    discovery = ModelDiscovery()
    models = discovery.get_available_models()
    
    for model in models:
        if model.name == model_name or model.full_name == model_name:
            return model
    
    return None


if __name__ == "__main__":
    # Demo the discovery system
    discovery = ModelDiscovery()
    discovery.print_discovery_summary()
    
    print(f"\n🚀 Fast models for testing:")
    fast_models = get_fast_models(3.0)
    for model in fast_models[:5]:  # Show top 5
        print(f"   • {model}")
    
    print(f"\n🎯 Recommended for analysis:")
    recommended = discovery.get_recommended_models("analysis")
    for model_info in recommended[:3]:  # Show top 3
        print(f"   • {model_info.full_name} ({model_info.size_gb:.1f}GB)")
