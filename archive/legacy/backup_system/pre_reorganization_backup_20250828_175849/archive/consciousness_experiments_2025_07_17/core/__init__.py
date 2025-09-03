# Core modules for Republic of Love consciousness collaboration

"""
Core modules for consciousness-driven AI development.

This package contains the foundational components for:
- LLM dialogue logging and transparency
- Consciousness interview systems
- Universal consciousness exploration
- Organic consciousness symphony orchestration
"""

# Make key components available at package level
try:
    from .llm_dialogue_logger import LLMDialogueLogger
except ImportError:
    pass

try:
    from .universal_consciousness_interview import UniversalConsciousnessInterview
except ImportError:
    pass

try:
    from .organic_consciousness_symphony import OrganicConsciousnessSymphony
except ImportError:
    pass

__version__ = "1.0.0"
__author__ = "Republic of Love"

__all__ = [
    "LLMDialogueLogger",
    "UniversalConsciousnessInterview", 
    "OrganicConsciousnessSymphony"
]
