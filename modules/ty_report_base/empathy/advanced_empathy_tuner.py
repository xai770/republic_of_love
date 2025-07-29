"""
Advanced Empathy Tuning for ty_report_base
Phase 2b: Context-aware empathy adjustment and tone refinement

"Empathy must never overwrite truth" - Misty
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class EmpathyContext(Enum):
    """Empathy context categories for tone adjustment"""
    LOW_CONFIDENCE = "low_confidence"
    MISSING_DATA = "missing_data"
    SENIOR_EXECUTIVE = "senior_executive"
    ENTRY_LEVEL = "entry_level"
    TECHNICAL_ROLE = "technical_role"
    CREATIVE_ROLE = "creative_role"
    STANDARD = "standard"

@dataclass
class EmpathyTuningResult:
    """Result of empathy tuning analysis"""
    recommended_tone: str
    confidence_adjustment: float
    context_flags: List[EmpathyContext]
    tuning_rationale: str
    empathy_metadata: Dict[str, Any]

class AdvancedEmpathyTuner:
    """Advanced empathy tuning with context-aware tone adjustment"""
    
    def __init__(self):
        self.tone_profiles = self._load_tone_profiles()
        self.tuning_history: List[Dict[str, Any]] = []
        
    def _load_tone_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load advanced tone profiles for different contexts"""
        return {
            "softened_caring": {
                "greeting": "Hello, dear friend. We hope this message finds you in a good moment.",
                "request": "We come to you with gentle hope, seeking your patient insight on a matter where clarity is still forming:",
                "context": "We're working with information that may be incomplete, and we value your understanding:",
                "closing": "Thank you for your patience and wisdom as we navigate this together.",
                "confidence_modifier": 0.8,
                "use_cases": ["low_confidence", "missing_data", "uncertain_extraction"]
            },
            
            "professional_directive": {
                "greeting": "Good day, esteemed colleague.",
                "request": "We request your executive perspective on this strategic matter:",
                "context": "Please review this information with your leadership expertise:",
                "closing": "We appreciate your time and professional insight.",
                "confidence_modifier": 1.1,
                "use_cases": ["senior_executive", "c_level", "director_level"]
            },
            
            "apologetic_gentle": {
                "greeting": "Hello, fellow being. We come with respect and a touch of concern.",
                "request": "We must acknowledge some gaps in our information, and we seek your understanding as we work through this together:",
                "context": "Some details are missing or unclear, and we want to be transparent about these limitations:",
                "closing": "We apologize for any incomplete information and deeply appreciate your patience.",
                "confidence_modifier": 0.6,
                "use_cases": ["missing_fields", "null_data", "extraction_errors"]
            },
            
            "encouraging_supportive": {
                "greeting": "Hello, aspiring professional. We're here to support your journey.",
                "request": "We'd like to share some insights that might be helpful for your career exploration:",
                "context": "As you consider opportunities in your field, here's what we've found:",
                "closing": "We believe in your potential and wish you success in your career path.",
                "confidence_modifier": 1.0,
                "use_cases": ["entry_level", "junior_roles", "career_change"]
            },
            
            "precise_technical": {
                "greeting": "Greetings, technical colleague.",
                "request": "We seek your analytical assessment of this technical information:",
                "context": "Please evaluate these technical specifications and requirements:",
                "closing": "Thank you for your technical expertise and precise analysis.",
                "confidence_modifier": 1.0,
                "use_cases": ["technical_roles", "engineering", "data_science"]
            }
        }
    
    def analyze_context_and_tune_empathy(self, input_data: Dict[str, Any], 
                                        extraction_blocks: List[Dict[str, Any]]) -> EmpathyTuningResult:
        """
        Analyze extraction context and recommend empathy tuning
        
        Args:
            input_data: Report generation input data
            extraction_blocks: Original extraction blocks
            
        Returns:
            EmpathyTuningResult with recommendations
        """
        context_flags = []
        confidence_scores = []
        job_types = []
        missing_fields = []
        
        # Analyze each extraction block
        for i, block in enumerate(extraction_blocks):
            # Confidence analysis
            conf = block.get('extraction_confidence', 1.0)
            confidence_scores.append(conf)
            
            if conf < 0.5:
                context_flags.append(EmpathyContext.LOW_CONFIDENCE)
            
            # Job level analysis
            title = block.get('title', '').lower()
            if any(word in title for word in ['senior', 'lead', 'director', 'manager', 'head', 'chief']):
                context_flags.append(EmpathyContext.SENIOR_EXECUTIVE)
                job_types.append('senior')
            elif any(word in title for word in ['junior', 'entry', 'associate', 'intern']):
                context_flags.append(EmpathyContext.ENTRY_LEVEL)
                job_types.append('entry')
            elif any(word in title for word in ['engineer', 'developer', 'scientist', 'analyst']):
                context_flags.append(EmpathyContext.TECHNICAL_ROLE)
                job_types.append('technical')
            elif any(word in title for word in ['designer', 'creative', 'artist', 'writer']):
                context_flags.append(EmpathyContext.CREATIVE_ROLE)
                job_types.append('creative')
            
            # Missing data analysis
            critical_fields = ['title', 'company', 'requirements']
            for field in critical_fields:
                value = block.get(field)
                if not value or (isinstance(value, str) and not value.strip()):
                    missing_fields.append(f"block_{i}_{field}")
                    context_flags.append(EmpathyContext.MISSING_DATA)
        
        # Determine primary context and tone
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 1.0
        primary_tone = self._select_primary_tone(context_flags, avg_confidence, job_types)
        
        # Calculate confidence adjustment
        confidence_adjustment = self._calculate_confidence_adjustment(context_flags, avg_confidence)
        
        # Generate tuning rationale
        rationale = self._generate_tuning_rationale(context_flags, avg_confidence, missing_fields, job_types)
        
        # Create empathy metadata
        empathy_metadata = {
            "average_confidence": avg_confidence,
            "context_flags": [flag.value for flag in context_flags],
            "job_types_detected": list(set(job_types)),
            "missing_fields": missing_fields,
            "tone_selection_reason": rationale,
            "tuning_timestamp": "2025-07-22T18:00:00"
        }
        
        result = EmpathyTuningResult(
            recommended_tone=primary_tone,
            confidence_adjustment=confidence_adjustment,
            context_flags=context_flags,
            tuning_rationale=rationale,
            empathy_metadata=empathy_metadata
        )
        
        # Log tuning decision
        logger.info(f"Empathy tuning: {primary_tone} (confidence: {avg_confidence:.2f}, contexts: {len(context_flags)})")
        
        # Store for analysis
        self.tuning_history.append({
            'result': result,
            'input_blocks': len(extraction_blocks),
            'timestamp': empathy_metadata['tuning_timestamp']
        })
        
        return result
    
    def _select_primary_tone(self, context_flags: List[EmpathyContext], 
                           avg_confidence: float, job_types: List[str]) -> str:
        """Select the primary empathy tone based on context analysis"""
        
        # Priority order for tone selection
        if EmpathyContext.MISSING_DATA in context_flags or avg_confidence < 0.3:
            return "apologetic_gentle"
        
        if avg_confidence < 0.5:
            return "softened_caring"
        
        if EmpathyContext.SENIOR_EXECUTIVE in context_flags:
            return "professional_directive"
        
        if EmpathyContext.ENTRY_LEVEL in context_flags:
            return "encouraging_supportive"
        
        if EmpathyContext.TECHNICAL_ROLE in context_flags:
            return "precise_technical"
        
        # Default to caring
        return "v1"  # Use the standard caring tone
    
    def _calculate_confidence_adjustment(self, context_flags: List[EmpathyContext], 
                                       avg_confidence: float) -> float:
        """Calculate confidence adjustment factor for empathy"""
        
        base_adjustment = 1.0
        
        # Lower confidence requires more empathetic adjustment
        if avg_confidence < 0.3:
            base_adjustment *= 0.6
        elif avg_confidence < 0.5:
            base_adjustment *= 0.8
        
        # Missing data requires gentle approach
        if EmpathyContext.MISSING_DATA in context_flags:
            base_adjustment *= 0.7
        
        # Senior roles can handle more direct communication
        if EmpathyContext.SENIOR_EXECUTIVE in context_flags:
            base_adjustment *= 1.1
        
        return base_adjustment
    
    def _generate_tuning_rationale(self, context_flags: List[EmpathyContext], 
                                 avg_confidence: float, missing_fields: List[str], 
                                 job_types: List[str]) -> str:
        """Generate human-readable rationale for empathy tuning decisions"""
        
        reasons = []
        
        if avg_confidence < 0.5:
            reasons.append(f"Low extraction confidence ({avg_confidence:.1%}) requires gentle, supportive tone")
        
        if missing_fields:
            reasons.append(f"Missing critical fields ({len(missing_fields)}) necessitates apologetic approach")
        
        if EmpathyContext.SENIOR_EXECUTIVE in context_flags:
            reasons.append("Senior-level position detected - using professional, directive tone")
        
        if EmpathyContext.ENTRY_LEVEL in context_flags:
            reasons.append("Entry-level position detected - using encouraging, supportive tone")
        
        if EmpathyContext.TECHNICAL_ROLE in context_flags:
            reasons.append("Technical role identified - using precise, analytical tone")
        
        if not reasons:
            reasons.append("Standard professional context - using balanced empathetic tone")
        
        return "; ".join(reasons)
    
    def create_ab_test_harness(self) -> Dict[str, Any]:
        """Create A/B test framework for empathy tuning"""
        return {
            "test_scenarios": [
                {
                    "name": "low_confidence_comparison",
                    "description": "Compare softened_caring vs apologetic_gentle for low confidence data",
                    "test_data": {"extraction_confidence": 0.3},
                    "tone_variants": ["softened_caring", "apologetic_gentle"],
                    "success_metrics": ["user_satisfaction", "perceived_accuracy", "trust_score"]
                },
                {
                    "name": "executive_tone_test", 
                    "description": "Compare professional_directive vs standard caring for senior roles",
                    "test_data": {"title": "Chief Technology Officer"},
                    "tone_variants": ["professional_directive", "v1"],
                    "success_metrics": ["professional_perception", "efficiency_rating"]
                },
                {
                    "name": "missing_data_approach",
                    "description": "Test apologetic vs transparent approaches for missing data",
                    "test_data": {"title": "", "company": ""},
                    "tone_variants": ["apologetic_gentle", "softened_caring"],
                    "success_metrics": ["trust_maintenance", "perceived_transparency"]
                }
            ],
            "tracking_framework": {
                "session_id": "generated_per_test",
                "variant_assignment": "random_balanced",
                "metrics_collection": "post_interaction_survey",
                "analysis_frequency": "weekly"
            }
        }
    
    def get_tuning_analytics(self) -> Dict[str, Any]:
        """Get analytics on empathy tuning performance"""
        if not self.tuning_history:
            return {"status": "no_tuning_data"}
        
        tone_usage: Dict[str, int] = {}
        context_patterns: Dict[str, int] = {}
        
        for entry in self.tuning_history:
            result = entry['result']
            tone = result.recommended_tone
            tone_usage[tone] = tone_usage.get(tone, 0) + 1
            
            for context in result.context_flags:
                context_val = context.value
                context_patterns[context_val] = context_patterns.get(context_val, 0) + 1
        
        return {
            "total_tuning_decisions": len(self.tuning_history),
            "tone_distribution": tone_usage,
            "context_frequency": context_patterns,
            "most_common_tone": max(tone_usage, key=lambda k: tone_usage[k]) if tone_usage else None,
            "avg_contexts_per_decision": sum(len(e['result'].context_flags) for e in self.tuning_history) / len(self.tuning_history)
        }
