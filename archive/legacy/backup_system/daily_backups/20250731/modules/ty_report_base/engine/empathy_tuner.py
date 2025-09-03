#!/usr/bin/env python3
"""
Advanced Empathy Tuning for ty_report_base
Authentic emotional intelligence for job report generation

No synthetic emotion. Real LLM-driven empathy adaptation.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class EmpathyLevel(Enum):
    """Empathy intensity levels"""
    MINIMAL = "minimal"       # Facts only
    GENTLE = "gentle"         # Soft encouragement  
    HIGH = "high"            # Full emotional support
    ADAPTIVE = "adaptive"     # Context-aware tuning

class ToneProfile(Enum):
    """Communication tone profiles"""
    PROFESSIONAL = "professional"
    ENCOURAGING = "encouraging"
    SUPPORTIVE = "supportive"
    MOTIVATIONAL = "motivational"
    REALISTIC = "realistic"

@dataclass
class EmpathyConfig:
    """Configuration for empathy-driven content generation"""
    level: EmpathyLevel
    tone_profile: ToneProfile
    softness_factor: float  # 0.0-1.0, higher = gentler
    directive_balance: float  # 0.0-1.0, higher = more guidance
    apologetic_threshold: float  # 0.0-1.0, when to add apologetic language
    context_adaptation: bool  # Whether to adapt to job/user context
    cultural_sensitivity: bool  # Cultural awareness in communication
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "level": self.level.value,
            "tone_profile": self.tone_profile.value,
            "softness_factor": self.softness_factor,
            "directive_balance": self.directive_balance,
            "apologetic_threshold": self.apologetic_threshold,
            "context_adaptation": self.context_adaptation,
            "cultural_sensitivity": self.cultural_sensitivity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmpathyConfig':
        """Create from dictionary"""
        return cls(
            level=EmpathyLevel(data["level"]),
            tone_profile=ToneProfile(data["tone_profile"]),
            softness_factor=data["softness_factor"],
            directive_balance=data["directive_balance"],
            apologetic_threshold=data["apologetic_threshold"],
            context_adaptation=data["context_adaptation"],
            cultural_sensitivity=data["cultural_sensitivity"]
        )

class EmpathyTuner:
    """Advanced empathy tuning for authentic LLM generation"""
    
    def __init__(self):
        self.preset_configs = self._create_preset_configs()
    
    def _create_preset_configs(self) -> Dict[str, EmpathyConfig]:
        """Create preset empathy configurations"""
        return {
            "job_seeker_support": EmpathyConfig(
                level=EmpathyLevel.HIGH,
                tone_profile=ToneProfile.SUPPORTIVE,
                softness_factor=0.8,
                directive_balance=0.6,
                apologetic_threshold=0.3,
                context_adaptation=True,
                cultural_sensitivity=True
            ),
            "career_guidance": EmpathyConfig(
                level=EmpathyLevel.GENTLE,
                tone_profile=ToneProfile.ENCOURAGING,
                softness_factor=0.6,
                directive_balance=0.7,
                apologetic_threshold=0.2,
                context_adaptation=True,
                cultural_sensitivity=False
            ),
            "technical_analysis": EmpathyConfig(
                level=EmpathyLevel.MINIMAL,
                tone_profile=ToneProfile.PROFESSIONAL,
                softness_factor=0.2,
                directive_balance=0.9,
                apologetic_threshold=0.1,
                context_adaptation=False,
                cultural_sensitivity=False
            ),
            "empathetic_default": EmpathyConfig(
                level=EmpathyLevel.ADAPTIVE,
                tone_profile=ToneProfile.SUPPORTIVE,
                softness_factor=0.7,
                directive_balance=0.5,
                apologetic_threshold=0.4,
                context_adaptation=True,
                cultural_sensitivity=True
            )
        }
    
    def get_preset_config(self, preset_name: str) -> Optional[EmpathyConfig]:
        """Get a preset empathy configuration"""
        config = self.preset_configs.get(preset_name)
        return config if isinstance(config, EmpathyConfig) else None
    
    def tune_prompt_for_empathy(
        self, 
        base_prompt: str, 
        empathy_config: EmpathyConfig,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add empathy tuning instructions to an LLM prompt
        
        Args:
            base_prompt: Original prompt text
            empathy_config: Empathy configuration to apply
            context: Additional context (job data, user profile, etc.)
            
        Returns:
            Enhanced prompt with empathy instructions
        """
        
        # Build empathy instruction components
        empathy_instructions = []
        
        # Level-based instructions
        if empathy_config.level == EmpathyLevel.MINIMAL:
            empathy_instructions.append(
                "Maintain a professional, fact-based tone. Avoid emotional language."
            )
        elif empathy_config.level == EmpathyLevel.GENTLE:
            empathy_instructions.append(
                "Use gentle, encouraging language. Show understanding for job search challenges."
            )
        elif empathy_config.level == EmpathyLevel.HIGH:
            empathy_instructions.append(
                "Provide high emotional support. Acknowledge difficulties and offer reassurance. "
                "Use warmth and understanding throughout."
            )
        elif empathy_config.level == EmpathyLevel.ADAPTIVE:
            empathy_instructions.append(
                "Adapt your emotional tone based on the context. Show empathy where appropriate, "
                "professional clarity where needed."
            )
        
        # Tone profile instructions
        tone_instruction = self._get_tone_instruction(empathy_config.tone_profile)
        empathy_instructions.append(tone_instruction)
        
        # Softness factor tuning
        if empathy_config.softness_factor > 0.7:
            empathy_instructions.append(
                "Use gentle, soft language. Avoid harsh words or direct criticism. "
                "Frame challenges as opportunities."
            )
        elif empathy_config.softness_factor > 0.4:
            empathy_instructions.append(
                "Balance directness with kindness. Use moderate language."
            )
        else:
            empathy_instructions.append(
                "Be direct and clear. Focus on facts and actionable information."
            )
        
        # Directive balance
        if empathy_config.directive_balance > 0.7:
            empathy_instructions.append(
                "Provide clear guidance and specific next steps. Be directive in recommendations."
            )
        elif empathy_config.directive_balance > 0.4:
            empathy_instructions.append(
                "Offer suggestions while respecting user autonomy. Balance guidance with options."
            )
        else:
            empathy_instructions.append(
                "Present information and let the user draw their own conclusions. Minimize directives."
            )
        
        # Apologetic threshold
        if empathy_config.apologetic_threshold > 0.5:
            empathy_instructions.append(
                "When delivering potentially disappointing information, use apologetic language. "
                "Express regret for limitations or challenges."
            )
        elif empathy_config.apologetic_threshold > 0.2:
            empathy_instructions.append(
                "Use apologetic language sparingly, only for significant limitations or problems."
            )
        
        # Context adaptation
        if empathy_config.context_adaptation and context:
            context_instructions = self._generate_context_instructions(context)
            empathy_instructions.extend(context_instructions)
        
        # Cultural sensitivity
        if empathy_config.cultural_sensitivity:
            empathy_instructions.append(
                "Be culturally sensitive. Avoid assumptions about background, experience, or values. "
                "Use inclusive language."
            )
        
        # Combine instructions
        empathy_section = "\n".join([
            "",
            "EMPATHY AND COMMUNICATION GUIDELINES:",
            *[f"- {instruction}" for instruction in empathy_instructions],
            ""
        ])
        
        # Insert empathy section after base prompt
        enhanced_prompt = base_prompt + empathy_section
        
        return enhanced_prompt
    
    def _get_tone_instruction(self, tone_profile: ToneProfile) -> str:
        """Get tone-specific instruction"""
        tone_instructions = {
            ToneProfile.PROFESSIONAL: "Maintain professional tone throughout. Use clear, business-appropriate language.",
            ToneProfile.ENCOURAGING: "Be encouraging and positive. Highlight opportunities and potential.",
            ToneProfile.SUPPORTIVE: "Show support and understanding. Acknowledge challenges with empathy.",
            ToneProfile.MOTIVATIONAL: "Use motivational language. Inspire action and confidence.",
            ToneProfile.REALISTIC: "Be realistic and honest while remaining constructive."
        }
        return tone_instructions[tone_profile]
    
    def _generate_context_instructions(self, context: Dict[str, Any]) -> List[str]:
        """Generate context-specific empathy instructions"""
        instructions = []
        
        # Job difficulty context
        if context.get("extraction_confidence", 1.0) < 0.7:
            instructions.append(
                "The job data may be incomplete. Acknowledge this limitation with understanding."
            )
        
        # Salary context
        if context.get("salary_info") == "not_provided":
            instructions.append(
                "When addressing missing salary information, show understanding of this concern."
            )
        
        # Experience level context
        if "junior" in str(context.get("title", "")).lower():
            instructions.append(
                "This appears to be a junior role. Use encouraging language for early-career professionals."
            )
        elif "senior" in str(context.get("title", "")).lower():
            instructions.append(
                "This is a senior role. Acknowledge the high standards while being supportive."
            )
        
        # Location context
        if context.get("remote") == False:
            instructions.append(
                "For on-site roles, acknowledge potential relocation or commute considerations with empathy."
            )
        
        return instructions
    
    def create_custom_config(
        self,
        level: str = "high",
        tone: str = "supportive", 
        **kwargs
    ) -> EmpathyConfig:
        """Create a custom empathy configuration"""
        
        return EmpathyConfig(
            level=EmpathyLevel(level),
            tone_profile=ToneProfile(tone),
            softness_factor=kwargs.get("softness_factor", 0.7),
            directive_balance=kwargs.get("directive_balance", 0.5),
            apologetic_threshold=kwargs.get("apologetic_threshold", 0.4),
            context_adaptation=kwargs.get("context_adaptation", True),
            cultural_sensitivity=kwargs.get("cultural_sensitivity", True)
        )
    
    def validate_empathy_response(
        self,
        response: str,
        empathy_config: EmpathyConfig,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate that a response matches empathy configuration
        
        Args:
            response: Generated response text
            empathy_config: Expected empathy configuration
            context: Optional context information
            
        Returns:
            Validation results with scores and flags
        """
        
        validation_result: Dict[str, Any] = {
            "empathy_score": 0.0,
            "tone_match": False,
            "softness_appropriate": False,
            "directive_balance_correct": False,
            "flags": [],
            "recommendations": []
        }
        
        response_lower = response.lower()
        
        # Check empathy level alignment
        empathy_indicators = [
            "understand", "sorry", "acknowledge", "challenging", 
            "support", "help", "appreciate", "recognize"
        ]
        
        empathy_count = sum(1 for word in empathy_indicators if word in response_lower)
        expected_empathy = self._get_expected_empathy_count(empathy_config.level)
        
        validation_result["empathy_score"] = min(empathy_count / max(expected_empathy, 1), 1.0)
        
        # Check tone appropriateness
        tone_words = self._get_tone_words(empathy_config.tone_profile)
        tone_matches = sum(1 for word in tone_words if word in response_lower)
        validation_result["tone_match"] = tone_matches > 0
        
        # Check softness level
        harsh_words = ["must", "should", "required", "mandatory", "failed", "wrong"]
        harsh_count = sum(1 for word in harsh_words if word in response_lower)
        expected_harshness = (1.0 - empathy_config.softness_factor) * 5
        validation_result["softness_appropriate"] = harsh_count <= expected_harshness
        
        # Check directive balance
        directive_words = ["recommend", "suggest", "should", "need to", "must", "action"]
        directive_count = sum(1 for word in directive_words if word in response_lower)
        expected_directives = empathy_config.directive_balance * 8
        validation_result["directive_balance_correct"] = abs(directive_count - expected_directives) <= 3
        
        # Generate flags and recommendations
        flags: List[str] = validation_result["flags"]  # type: ignore
        recommendations: List[str] = validation_result["recommendations"]  # type: ignore
        
        if validation_result["empathy_score"] < 0.5 and empathy_config.level in [EmpathyLevel.HIGH, EmpathyLevel.GENTLE]:
            flags.append("Low empathy detected for high-empathy configuration")
            recommendations.append("Increase empathetic language and acknowledgment")
        
        if not validation_result["tone_match"]:
            flags.append(f"Response tone doesn't match {empathy_config.tone_profile.value}")
            recommendations.append(f"Adjust language to match {empathy_config.tone_profile.value} tone")
        
        if not validation_result["softness_appropriate"]:
            flags.append("Softness level doesn't match configuration")
            recommendations.append("Adjust language harshness to match softness factor")
        
        return validation_result
    
    def _get_expected_empathy_count(self, level: EmpathyLevel) -> int:
        """Get expected empathy word count for validation"""
        counts = {
            EmpathyLevel.MINIMAL: 1,
            EmpathyLevel.GENTLE: 3,
            EmpathyLevel.HIGH: 6,
            EmpathyLevel.ADAPTIVE: 4
        }
        return counts[level]
    
    def _get_tone_words(self, tone: ToneProfile) -> List[str]:
        """Get expected words for tone validation"""
        tone_words = {
            ToneProfile.PROFESSIONAL: ["professional", "business", "appropriate", "standard"],
            ToneProfile.ENCOURAGING: ["opportunity", "potential", "positive", "growth", "excellent"],
            ToneProfile.SUPPORTIVE: ["support", "understand", "help", "together", "guidance"],
            ToneProfile.MOTIVATIONAL: ["achieve", "success", "inspire", "motivate", "excel"],
            ToneProfile.REALISTIC: ["realistic", "practical", "honest", "balanced", "objective"]
        }
        return tone_words[tone]

def get_empathy_tuner() -> EmpathyTuner:
    """Get the global empathy tuner instance"""
    return EmpathyTuner()

# Example usage and presets
if __name__ == "__main__":
    tuner = get_empathy_tuner()
    
    # Demo: Create job seeker support configuration
    config = tuner.get_preset_config("job_seeker_support")
    if config is not None:
        print("Job Seeker Support Config:")
        print(json.dumps(config.to_dict(), indent=2))
        
        # Demo: Tune a prompt for empathy
        base_prompt = "Analyze this job posting and provide recommendations."
        enhanced_prompt = tuner.tune_prompt_for_empathy(
            base_prompt,
            config,
            context={"title": "Junior Developer", "salary_info": "not_provided"}
        )
        
        print(f"\nEnhanced Prompt:\n{enhanced_prompt}")
    else:
        print("Config not found")
