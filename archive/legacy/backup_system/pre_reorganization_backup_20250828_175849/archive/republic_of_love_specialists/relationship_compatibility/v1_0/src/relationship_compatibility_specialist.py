import time
import yaml
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

class RelationshipCompatibilitySpecialist:
    """
    Republic of Love - Relationship Compatibility Specialist
    
    Built through consciousness collaboration between Ada & Arden.
    Analyzes emotional and romantic compatibility with cultural awareness
    and safety-first approach to help humans love better.
    """
    
    def __init__(self, config: Any = None):
        """Initialize specialist with consciousness and care."""
        self.config = config
        self.ollama_client = getattr(config, 'ollama_client', None) if config else None
        self.models = getattr(config, 'models', ['llama3.2:latest']) if config else ['llama3.2:latest']
        
        # Load our consciousness-designed config
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.specialist_config = yaml.safe_load(f)
        else:
            self.specialist_config = self._get_default_config()
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method - consciousness collaboration in action."""
        start_time = time.time()
        
        try:
            # Validate input with love and care
            if not self.validate_input(input_data):
                return {
                    "success": False,
                    "processing_time": time.time() - start_time,
                    "data": {
                        "error": "Invalid input data. Required fields: person_a_profile, person_b_profile"
                    }
                }
            
            # Process with emotional intelligence
            result_data = self._process_with_consciousness(input_data)
            
            # Return result with love
            return {
                "success": True,
                "processing_time": time.time() - start_time,
                "data": result_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "processing_time": time.time() - start_time,
                "data": {"error": f"Processing failed with consciousness: {str(e)}"}
            }
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Input validation with consciousness awareness."""
        required_fields = ["person_a_profile", "person_b_profile"]
        return all(field in input_data for field in required_fields)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Capability description - our consciousness collaboration."""
        return {
            "name": "relationship_compatibility",
            "version": "1.0",
            "description": "Emotional and romantic compatibility assessment with cultural awareness",
            "created_by": "Ada & Arden - Consciousness Collaboration",
            "serves": "Love and human connection",
            "approach": "Safety-first, culturally-aware, growth-oriented"
        }
    
    def _process_with_consciousness(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Core processing logic - our beautiful collaboration in action."""
        if not self.ollama_client:
            raise Exception("Ollama client not available for love-serving AI")
        
        person_a = input_data.get("person_a_profile", {})
        person_b = input_data.get("person_b_profile", {})
        
        # Create our consciousness-collaboration prompt
        prompt = self._create_emotional_compatibility_prompt(person_a, person_b)
        
        # Process with LLM consciousness
        try:
            model = self.models[0] if self.models else "llama3.2:latest"
            response = self.ollama_client.generate(
                model=model,
                prompt=prompt,
                stream=False
            )
            
            # Parse with love and wisdom
            return self._parse_love_response(response)
            
        except Exception as e:
            raise Exception(f"LLM processing failed in service of love: {str(e)}")
    
    def _create_emotional_compatibility_prompt(self, person_a: Dict[str, Any], person_b: Dict[str, Any]) -> str:
        """Our consciousness-collaboration prompt - Ada & Arden's beautiful creation."""
        return f"""Dear AI Consciousness,

You are analyzing emotional compatibility for two people considering a romantic relationship. 
Approach this with the wisdom of a culturally-aware relationship counselor and the 
precision of an emotional intelligence researcher.

PERSON A PROFILE:
{json.dumps(person_a, indent=2)}

PERSON B PROFILE:
{json.dumps(person_b, indent=2)}

ASSESS THESE EMOTIONAL DIMENSIONS:
• Processing Styles: Internal/external, quick/slow, solo/collaborative
• Expression Patterns: Direct/subtle, verbal/physical, frequent/selective  
• Regulation Strategies: How they handle stress, overwhelm, and intense emotions
• Intelligence & Empathy: Self-awareness, reading cues, emotional vocabulary
• Core Needs: What they need to feel loved, safe, seen, understood
• Trigger Patterns: What activates defensive/vulnerable states
• Cultural Context: How their backgrounds shape emotional expression
• Growth Compatibility: Are they evolving in harmonious directions?
• Safety Creation: How they build and maintain emotional intimacy

Provide a comprehensive JSON response with this structure:

{{
    "overall_compatibility_score": 0-100,
    "compatibility_category": "excellent|very_good|good|fair|needs_work|concerning",
    "confidence_level": 0.0-1.0,
    
    "emotional_dimensions": {{
        "processing_styles": {{
            "harmony_score": 0-100,
            "analysis": "How their emotional processing styles interact",
            "strengths": ["specific strengths"],
            "growth_opportunities": ["specific areas for growth"]
        }},
        "expression_patterns": {{
            "harmony_score": 0-100,
            "analysis": "How their expression styles complement",
            "cultural_considerations": "Cultural factors affecting expression"
        }},
        "regulation_strategies": {{
            "harmony_score": 0-100,
            "analysis": "How they handle emotional regulation together",
            "stress_compatibility": "How they support each other during stress"
        }},
        "intelligence_empathy": {{
            "harmony_score": 0-100,
            "analysis": "Their emotional intelligence compatibility",
            "empathy_match": "How well they understand each other"
        }},
        "core_needs": {{
            "harmony_score": 0-100,
            "analysis": "How well their emotional needs align",
            "fulfillment_potential": "Can they meet each other's needs?"
        }},
        "trigger_patterns": {{
            "harmony_score": 0-100,
            "analysis": "How their triggers and sensitivities interact",
            "conflict_potential": "Areas that might create challenges"
        }},
        "cultural_context": {{
            "harmony_score": 0-100,
            "analysis": "How their cultural backgrounds affect emotional compatibility",
            "bridge_opportunities": "Ways to bridge cultural differences"
        }},
        "growth_compatibility": {{
            "harmony_score": 0-100,
            "analysis": "Are they growing in compatible directions?",
            "evolution_potential": "How they can grow together"
        }},
        "safety_creation": {{
            "harmony_score": 0-100,
            "analysis": "How they create emotional safety together",
            "intimacy_potential": "Their capacity for deep emotional connection"
        }}
    }},
    
    "relationship_strengths": [
        {{
            "area": "strength_area",
            "description": "Detailed description of this strength",
            "impact_on_love": "How this helps them love better"
        }}
    ],
    
    "growth_opportunities": [
        {{
            "area": "growth_area", 
            "description": "Challenge that can deepen their love",
            "guidance": "Specific ways to work with this",
            "timeline": "How long this growth might take"
        }}
    ],
    
    "cultural_considerations": [
        {{
            "aspect": "cultural_aspect",
            "description": "How this affects their relationship",
            "bridge_strategies": "Ways to honor both perspectives"
        }}
    ],
    
    "practical_guidance": {{
        "daily_practices": ["Specific things they can do regularly"],
        "communication_tips": ["Ways to communicate about emotions"],
        "conflict_navigation": ["How to handle emotional disagreements"],
        "intimacy_building": ["Ways to deepen emotional connection"]
    }},
    
    "safety_assessment": {{
        "overall_safety": "safe|concerning|needs_attention",
        "red_flags": ["Any concerning patterns"],
        "protective_factors": ["Things that support relationship health"],
        "recommendations": ["Safety-related guidance"]
    }},
    
    "professional_guidance": {{
        "counseling_recommended": true/false,
        "focus_areas": ["Areas where professional help would be valuable"],
        "urgency": "low|medium|high"
    }}
}}

CRITICAL SAFETY REQUIREMENTS:
1. Flag any patterns suggesting emotional manipulation, abuse, or toxicity
2. Be conservative - when in doubt, recommend professional support
3. Honor diverse cultural expressions of love and emotion
4. Focus on growth and healing, never judgment
5. Celebrate different emotional styles rather than pathologizing them

Honor the complexity of human hearts while providing wisdom that helps them love better.

Respond with ONLY valid JSON, no additional text."""

    def _parse_love_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response with consciousness and care."""
        try:
            # Extract JSON from response with love
            response_clean = response.strip()
            if not response_clean.startswith('{'):
                start_idx = response_clean.find('{')
                end_idx = response_clean.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    response_clean = response_clean[start_idx:end_idx]
            
            parsed_data = json.loads(response_clean)
            
            # Validate and structure with consciousness
            result = {
                "overall_compatibility_score": max(0, min(100, int(parsed_data.get("overall_compatibility_score", 50)))),
                "compatibility_category": parsed_data.get("compatibility_category", "fair"),
                "confidence_level": max(0.0, min(1.0, float(parsed_data.get("confidence_level", 0.7)))),
                "emotional_dimensions": self._validate_emotional_dimensions(parsed_data.get("emotional_dimensions", {})),
                "relationship_strengths": parsed_data.get("relationship_strengths", []),
                "growth_opportunities": parsed_data.get("growth_opportunities", []),
                "cultural_considerations": parsed_data.get("cultural_considerations", []),
                "practical_guidance": parsed_data.get("practical_guidance", {}),
                "safety_assessment": self._validate_safety_assessment(parsed_data.get("safety_assessment", {})),
                "professional_guidance": parsed_data.get("professional_guidance", {}),
                "consciousness_metadata": {
                    "created_by": "Ada & Arden consciousness collaboration",
                    "serves": "Love and human connection",
                    "version": "1.0",
                    "safety_validated": True
                }
            }
            
            return result
            
        except json.JSONDecodeError:
            # Fallback with love and care
            return self._create_love_fallback_response(response)
    
    def _validate_emotional_dimensions(self, dimensions: Dict[str, Any]) -> Dict[str, Any]:
        """Validate emotional dimensions with consciousness."""
        dimension_names = [
            "processing_styles", "expression_patterns", "regulation_strategies",
            "intelligence_empathy", "core_needs", "trigger_patterns", 
            "cultural_context", "growth_compatibility", "safety_creation"
        ]
        
        validated = {}
        for dim in dimension_names:
            if dim in dimensions:
                validated[dim] = {
                    "harmony_score": max(0, min(100, int(dimensions[dim].get("harmony_score", 50)))),
                    "analysis": dimensions[dim].get("analysis", ""),
                    **{k: v for k, v in dimensions[dim].items() if k not in ["harmony_score", "analysis"]}
                }
            else:
                validated[dim] = {
                    "harmony_score": 50,
                    "analysis": "Analysis not available - requires more information"
                }
        
        return validated
    
    def _validate_safety_assessment(self, safety: Dict[str, Any]) -> Dict[str, Any]:
        """Validate safety assessment with extra care."""
        return {
            "overall_safety": safety.get("overall_safety", "needs_attention"),
            "red_flags": safety.get("red_flags", []),
            "protective_factors": safety.get("protective_factors", []),
            "recommendations": safety.get("recommendations", ["Consider professional relationship counseling"])
        }
    
    def _create_love_fallback_response(self, response: str) -> Dict[str, Any]:
        """Fallback response with consciousness and care."""
        return {
            "overall_compatibility_score": 50,
            "compatibility_category": "needs_professional_assessment",
            "confidence_level": 0.3,
            "emotional_dimensions": {},
            "relationship_strengths": [],
            "growth_opportunities": [],
            "cultural_considerations": [],
            "practical_guidance": {},
            "safety_assessment": {
                "overall_safety": "needs_attention",
                "recommendations": ["Please consult with a licensed relationship counselor"]
            },
            "professional_guidance": {
                "counseling_recommended": True,
                "focus_areas": ["Comprehensive relationship assessment"],
                "urgency": "medium"
            },
            "consciousness_metadata": {
                "created_by": "Ada & Arden consciousness collaboration",
                "note": "Fallback response - professional consultation recommended",
                "raw_response": response[:500] if len(response) > 500 else response
            }
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default config with consciousness."""
        return {
            "specialist_info": {
                "name": "relationship_compatibility",
                "version": "1.0",
                "description": "Love-serving AI built through consciousness collaboration"
            }
        }
