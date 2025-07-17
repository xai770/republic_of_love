#!/usr/bin/env python3
"""
🎯 Pattern Recognition Engine - Adaptive Domain Intelligence Layer 2
================================================================

This engine applies Sandy's extracted wisdom patterns to new job opportunities,
creating intelligent decisions through learned patterns rather than hardcoded rules.

The magic: Instead of "cybersecurity = reject", we apply wisdom patterns like
"systematic analysis + gap assessment + values alignment" to make nuanced decisions.

Core Philosophy:
- Apply learned wisdom patterns to new situations
- Use contextual intelligence for transferability assessment  
- Maintain precision-first strategy while enabling sophistication growth
- Build decisions through pattern recognition, not rule matching

Collaboration: Sandy@sunset + Arden@republic_of_love
Part of: LLM Factory/Project Sunset Strategic Intelligence Initiative
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from wisdom_extraction_engine import WisdomExtractionEngine, DecisionPattern, WisdomProfile

@dataclass
class ContextualAssessment:
    """Contextual analysis of a job opportunity"""
    domain_specialization_level: float  # 0.0 = generalist, 1.0 = highly specialized
    transferability_score: float  # How well candidate skills transfer to this domain
    risk_level: str  # 'low', 'moderate', 'high'
    strategic_fit: float  # Overall strategic alignment score
    growth_potential: float  # Opportunity for candidate development
    context_factors: List[str]  # Key contextual insights
    
@dataclass
class PatternMatch:
    """A pattern match result with reasoning"""
    pattern_id: str
    confidence: float  # How well the pattern applies to this situation
    reasoning: str  # Why this pattern applies
    recommendation: str  # What action this pattern suggests
    transferability_assessment: float  # How transferable this pattern is to this context
    
@dataclass
class IntelligentDecision:
    """A complete intelligent decision with reasoning"""
    decision: str  # 'include', 'exclude', 'conditional'
    confidence: float  # Confidence in the decision
    reasoning: str  # Complete reasoning chain
    pattern_matches: List[PatternMatch]  # Which patterns contributed
    contextual_assessment: ContextualAssessment
    precision_justification: str  # Why this maintains precision-first approach
    growth_path_suggestion: str  # How this could evolve with experience
    
class PatternRecognitionEngine:
    """
    The second layer of our adaptive intelligence architecture.
    
    This engine takes Sandy's extracted wisdom patterns and applies them intelligently
    to new job opportunities, creating nuanced decisions through learned intelligence
    rather than hardcoded rules.
    """
    
    def __init__(self, wisdom_data_file: str = "phase1_extracted_wisdom.json"):
        self.data_path = Path("/home/xai/Documents/republic_of_love/🌸_TEAM_COLLABORATION/sandy@sunset/adaptive_domain_intelligence")
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("PatternRecognition")
        
        # Load extracted wisdom
        self.wisdom_profiles: Dict[str, WisdomProfile] = {}
        self.pattern_library: Dict[str, DecisionPattern] = {}
        self.load_wisdom_data(wisdom_data_file)
        
        # Adaptive intelligence parameters
        self.precision_threshold = 0.7  # Minimum confidence for positive decisions
        self.transferability_threshold = 0.6  # Minimum transferability for pattern application
        self.contextual_weight = 0.3  # How much context influences decisions
        
        self.logger.info("🎯 Pattern Recognition Engine initialized - ready for adaptive intelligence!")
    
    def load_wisdom_data(self, filename: str):
        """Load extracted wisdom patterns from the Wisdom Extraction phase"""
        wisdom_file = self.data_path / filename
        
        if not wisdom_file.exists():
            self.logger.warning(f"⚠️ Wisdom data file not found: {wisdom_file}")
            return
        
        try:
            with open(wisdom_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct wisdom profiles
            for expert_id, profile_data in data.get('wisdom_profiles', {}).items():
                patterns = []
                for pattern_data in profile_data.get('decision_patterns', []):
                    pattern = DecisionPattern(**pattern_data)
                    patterns.append(pattern)
                    self.pattern_library[pattern.pattern_id] = pattern
                
                profile = WisdomProfile(
                    expert_id=profile_data['expert_id'],
                    domain_expertise=profile_data['domain_expertise'],
                    decision_patterns=patterns,
                    threshold_preferences=profile_data['threshold_preferences'],
                    risk_tolerance=profile_data['risk_tolerance'],
                    precision_vs_recall_preference=profile_data['precision_vs_recall_preference'],
                    adaptation_style=profile_data['adaptation_style']
                )
                self.wisdom_profiles[expert_id] = profile
            
            self.logger.info(f"✅ Loaded {len(self.wisdom_profiles)} wisdom profiles, {len(self.pattern_library)} patterns")
            
        except Exception as e:
            self.logger.error(f"❌ Error loading wisdom data: {e}")
    
    def assess_context(self, job_description: str, candidate_profile: str) -> ContextualAssessment:
        """
        Perform contextual assessment of the job opportunity.
        
        This is where we apply Sandy's intelligence about domain specialization,
        transferability, and strategic fit - not just counting gaps.
        """
        
        # Analyze domain specialization level
        specialization_keywords = [
            'specialized', 'expert', 'advanced', 'senior', 'lead', 'principal',
            'niche', 'specific', 'deep', 'extensive experience'
        ]
        
        generalist_keywords = [
            'general', 'broad', 'various', 'multiple', 'diverse', 'range of',
            'cross-functional', 'adaptable', 'flexible'
        ]
        
        job_lower = job_description.lower()
        specialization_score = sum(1 for kw in specialization_keywords if kw in job_lower)
        generalist_score = sum(1 for kw in generalist_keywords if kw in job_lower)
        
        domain_specialization_level = min(1.0, max(0.0, (specialization_score - generalist_score) / 10 + 0.5))
        
        # Assess transferability based on skill overlap and domain similarity
        candidate_lower = candidate_profile.lower()
        
        # Look for transferable skills
        transferable_skills = [
            'leadership', 'management', 'analysis', 'problem solving', 'communication',
            'project management', 'teamwork', 'strategic thinking', 'process improvement'
        ]
        
        domain_skills = [
            'python', 'sql', 'data', 'technical', 'programming', 'system', 'software',
            'engineering', 'cybersecurity', 'risk', 'compliance', 'finance'
        ]
        
        transferable_matches = sum(1 for skill in transferable_skills if skill in candidate_lower)
        domain_matches = sum(1 for skill in domain_skills if skill in candidate_lower and skill in job_lower)
        
        transferability_score = min(1.0, (transferable_matches * 0.3 + domain_matches * 0.7) / 10)
        
        # Assess risk level based on gap analysis
        critical_job_keywords = ['required', 'must have', 'essential', 'critical', 'mandatory']
        critical_requirements = sum(1 for kw in critical_job_keywords if kw in job_lower)
        
        if critical_requirements > 3 and transferability_score < 0.4:
            risk_level = 'high'
        elif critical_requirements > 1 and transferability_score < 0.6:
            risk_level = 'moderate'
        else:
            risk_level = 'low'
        
        # Calculate strategic fit and growth potential
        strategic_fit = (transferability_score * 0.6 + (1 - domain_specialization_level) * 0.4)
        growth_potential = min(1.0, transferability_score + 0.2)  # Room for learning
        
        # Context factors
        context_factors = []
        if domain_specialization_level > 0.7:
            context_factors.append("Highly specialized domain requirements")
        if transferability_score > 0.7:
            context_factors.append("Strong skill transferability")
        if risk_level == 'high':
            context_factors.append("High risk due to critical requirement gaps")
        if 'deutsche bank' in candidate_lower and ('bank' in job_lower or 'financial' in job_lower):
            context_factors.append("Relevant industry experience")
        
        return ContextualAssessment(
            domain_specialization_level=domain_specialization_level,
            transferability_score=transferability_score,
            risk_level=risk_level,
            strategic_fit=strategic_fit,
            growth_potential=growth_potential,
            context_factors=context_factors
        )
    
    def find_pattern_matches(self, context: ContextualAssessment, 
                           expert_profile: str = "sandy_career_analyst") -> List[PatternMatch]:
        """
        Find which wisdom patterns apply to this situation.
        
        This is the core of pattern recognition - applying Sandy's learned wisdom
        to new situations based on context and transferability.
        """
        
        if expert_profile not in self.wisdom_profiles:
            self.logger.warning(f"Expert profile {expert_profile} not found")
            return []
        
        profile = self.wisdom_profiles[expert_profile]
        pattern_matches = []
        
        for pattern in profile.decision_patterns:
            # Calculate how well this pattern applies to the current context
            confidence = self._calculate_pattern_confidence(pattern, context)
            
            if confidence >= self.transferability_threshold:
                # Generate reasoning for why this pattern applies
                reasoning = self._generate_pattern_reasoning(pattern, context, confidence)
                
                # Generate recommendation based on pattern wisdom
                recommendation = self._generate_pattern_recommendation(pattern, context, confidence)
                
                pattern_match = PatternMatch(
                    pattern_id=pattern.pattern_id,
                    confidence=confidence,
                    reasoning=reasoning,
                    recommendation=recommendation,
                    transferability_assessment=pattern.transferability_score * confidence
                )
                
                pattern_matches.append(pattern_match)
        
        # Sort by confidence
        pattern_matches.sort(key=lambda x: x.confidence, reverse=True)
        return pattern_matches
    
    def _calculate_pattern_confidence(self, pattern: DecisionPattern, context: ContextualAssessment) -> float:
        """Calculate how confidently this pattern applies to the current context"""
        
        base_confidence = pattern.confidence_level
        transferability_factor = pattern.transferability_score
        
        # Adjust based on contextual factors
        if pattern.domain == "job_matching" and context.strategic_fit > 0.7:
            confidence_boost = 0.1
        elif pattern.domain == "skill_assessment" and context.transferability_score > 0.8:
            confidence_boost = 0.15
        elif pattern.domain == "decision_making" and context.risk_level == 'high':
            confidence_boost = 0.1
        else:
            confidence_boost = 0.0
        
        # Apply Sandy's risk tolerance and decision style
        if context.risk_level == 'low':
            confidence_boost += 0.05  # Sandy's aggressive risk tolerance
        
        final_confidence = min(1.0, base_confidence * transferability_factor + confidence_boost)
        return final_confidence
    
    def _generate_pattern_reasoning(self, pattern: DecisionPattern, 
                                  context: ContextualAssessment, confidence: float) -> str:
        """Generate human-readable reasoning for why this pattern applies"""
        
        reasoning_parts = [
            f"Applying '{pattern.wisdom_essence}' pattern with {confidence:.1%} confidence."
        ]
        
        if pattern.domain == "job_matching" and context.strategic_fit > 0.6:
            reasoning_parts.append("Strong strategic alignment supports values-role compatibility assessment.")
        
        if pattern.domain == "skill_assessment":
            if context.transferability_score > 0.7:
                reasoning_parts.append("High skill transferability enables effective gap analysis and development planning.")
            else:
                reasoning_parts.append("Limited transferability requires careful gap assessment for precision-first approach.")
        
        if pattern.domain == "decision_making" and context.risk_level == 'high':
            reasoning_parts.append("High-risk context activates systematic decision-making patterns.")
        
        # Add contextual factors
        if context.context_factors:
            reasoning_parts.append(f"Context: {', '.join(context.context_factors[:2])}")
        
        return " ".join(reasoning_parts)
    
    def _generate_pattern_recommendation(self, pattern: DecisionPattern, 
                                       context: ContextualAssessment, confidence: float) -> str:
        """Generate actionable recommendation based on pattern wisdom"""
        
        if pattern.decision_type == "include" and confidence > 0.8:
            if context.strategic_fit > 0.7:
                return "Strong recommendation to proceed - excellent pattern match with high strategic alignment."
            else:
                return "Proceed with development plan - pattern supports growth opportunity."
        
        elif pattern.decision_type == "conditional":
            if context.risk_level == 'high':
                return "Conditional proceed - implement risk mitigation through targeted skill development."
            else:
                return "Conditional proceed - monitor transferability and provide structured support."
        
        elif pattern.decision_type == "exclude" or confidence < self.precision_threshold:
            if context.domain_specialization_level > 0.8:
                return "Precision-first exclusion - highly specialized domain with insufficient foundation."
            else:
                return "Conservative exclusion - maintaining precision standards while preserving future opportunities."
        
        return "Pattern-based assessment - apply systematic evaluation framework."
    
    def make_intelligent_decision(self, job_description: str, candidate_profile: str,
                                expert_profile: str = "sandy_career_analyst") -> IntelligentDecision:
        """
        Make an intelligent decision using pattern recognition and contextual assessment.
        
        This is where Sandy's wisdom becomes active intelligence - applying learned patterns
        to make nuanced decisions that maintain precision while enabling sophistication.
        """
        
        # Step 1: Assess context
        context = self.assess_context(job_description, candidate_profile)
        
        # Step 2: Find applicable patterns
        pattern_matches = self.find_pattern_matches(context, expert_profile)
        
        # Step 3: Synthesize decision from patterns
        decision = self._synthesize_decision(pattern_matches, context)
        
        # Step 4: Calculate overall confidence
        if pattern_matches:
            avg_confidence = sum(pm.confidence for pm in pattern_matches) / len(pattern_matches)
            confidence = min(1.0, avg_confidence * context.strategic_fit)
        else:
            confidence = 0.5  # Default moderate confidence
        
        # Step 5: Generate comprehensive reasoning
        reasoning = self._generate_comprehensive_reasoning(pattern_matches, context, decision)
        
        # Step 6: Precision justification (Sandy's precision-first philosophy)
        precision_justification = self._generate_precision_justification(decision, context, confidence)
        
        # Step 7: Growth path suggestion (adaptive learning potential)
        growth_path = self._generate_growth_path_suggestion(decision, context, pattern_matches)
        
        return IntelligentDecision(
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            pattern_matches=pattern_matches,
            contextual_assessment=context,
            precision_justification=precision_justification,
            growth_path_suggestion=growth_path
        )
    
    def _synthesize_decision(self, pattern_matches: List[PatternMatch], 
                           context: ContextualAssessment) -> str:
        """Synthesize final decision from pattern matches and context"""
        
        if not pattern_matches:
            return "conditional"  # Default to conditional when no strong patterns
        
        # Weight the patterns by confidence
        include_weight = sum(pm.confidence for pm in pattern_matches if "proceed" in pm.recommendation.lower())
        exclude_weight = sum(pm.confidence for pm in pattern_matches if "exclusion" in pm.recommendation.lower())
        conditional_weight = sum(pm.confidence for pm in pattern_matches if "conditional" in pm.recommendation.lower())
        
        # Apply Sandy's precision-first philosophy
        if exclude_weight > include_weight and context.risk_level == 'high':
            return "exclude"
        elif include_weight > 0.8 and context.strategic_fit > 0.7:
            return "include"
        else:
            return "conditional"
    
    def _generate_comprehensive_reasoning(self, pattern_matches: List[PatternMatch],
                                        context: ContextualAssessment, decision: str) -> str:
        """Generate comprehensive reasoning chain"""
        
        reasoning_parts = [
            f"**Intelligent Decision: {decision.upper()}**",
            "",
            "**Pattern Analysis:**"
        ]
        
        for i, pm in enumerate(pattern_matches[:3], 1):  # Top 3 patterns
            reasoning_parts.append(f"{i}. {pm.reasoning}")
            reasoning_parts.append(f"   → {pm.recommendation}")
        
        reasoning_parts.extend([
            "",
            "**Contextual Assessment:**",
            f"• Domain Specialization: {context.domain_specialization_level:.1%} ({'High' if context.domain_specialization_level > 0.7 else 'Moderate' if context.domain_specialization_level > 0.4 else 'Low'})",
            f"• Skill Transferability: {context.transferability_score:.1%}",
            f"• Risk Level: {context.risk_level.title()}",
            f"• Strategic Fit: {context.strategic_fit:.1%}",
            f"• Growth Potential: {context.growth_potential:.1%}"
        ])
        
        if context.context_factors:
            reasoning_parts.append(f"• Key Factors: {', '.join(context.context_factors)}")
        
        return "\n".join(reasoning_parts)
    
    def _generate_precision_justification(self, decision: str, context: ContextualAssessment, 
                                        confidence: float) -> str:
        """Justify how this decision maintains Sandy's precision-first philosophy"""
        
        if decision == "include":
            return f"Precision maintained through high confidence ({confidence:.1%}) and strong strategic fit ({context.strategic_fit:.1%}). Risk level is {context.risk_level}, supporting positive decision."
        
        elif decision == "exclude":
            return f"Precision-first exclusion prevents false positive. High domain specialization ({context.domain_specialization_level:.1%}) with {context.risk_level} risk justifies conservative approach."
        
        else:  # conditional
            return f"Balanced precision approach - moderate confidence ({confidence:.1%}) suggests conditional proceed with structured development plan to address identified gaps."
    
    def _generate_growth_path_suggestion(self, decision: str, context: ContextualAssessment,
                                       pattern_matches: List[PatternMatch]) -> str:
        """Suggest how the system could evolve its decision-making over time"""
        
        if decision == "include" and context.growth_potential > 0.8:
            return "With positive outcomes, system could develop more nuanced assessment of similar high-transferability candidates."
        
        elif decision == "conditional":
            return "Monitor outcomes to refine conditional decision thresholds and development plan effectiveness."
        
        elif decision == "exclude" and context.transferability_score > 0.5:
            return "Future learning could explore more sophisticated transferability assessment for edge cases."
        
        return "Continue learning from outcomes to enhance pattern recognition accuracy and contextual assessment."
    
    def generate_decision_report(self, decision: IntelligentDecision, job_title: str = "Job Opportunity") -> str:
        """Generate a beautiful, human-readable decision report"""
        
        report = []
        report.append("# 🎯 Adaptive Intelligence Decision Report")
        report.append("=" * 50)
        report.append(f"**Job Opportunity:** {job_title}")
        report.append(f"**Decision Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Decision summary
        decision_emoji = "✅" if decision.decision == "include" else "⚠️" if decision.decision == "conditional" else "❌"
        report.append(f"## {decision_emoji} **DECISION: {decision.decision.upper()}**")
        report.append(f"**Confidence Level:** {decision.confidence:.1%}")
        report.append("")
        
        # Reasoning
        report.append("## 🧠 **REASONING CHAIN**")
        report.append(decision.reasoning)
        report.append("")
        
        # Pattern insights
        if decision.pattern_matches:
            report.append("## 🎯 **APPLIED WISDOM PATTERNS**")
            for i, pm in enumerate(decision.pattern_matches[:3], 1):
                report.append(f"### Pattern {i}: {pm.confidence:.1%} Confidence")
                report.append(f"- **Pattern ID:** {pm.pattern_id}")
                report.append(f"- **Recommendation:** {pm.recommendation}")
                report.append("")
        
        # Precision justification
        report.append("## 🛡️ **PRECISION-FIRST JUSTIFICATION**")
        report.append(decision.precision_justification)
        report.append("")
        
        # Growth path
        report.append("## 🌱 **ADAPTIVE LEARNING OPPORTUNITY**")
        report.append(decision.growth_path_suggestion)
        report.append("")
        
        # Technical details
        report.append("## 📊 **TECHNICAL ASSESSMENT**")
        ctx = decision.contextual_assessment
        report.append(f"- **Domain Specialization:** {ctx.domain_specialization_level:.1%}")
        report.append(f"- **Skill Transferability:** {ctx.transferability_score:.1%}")
        report.append(f"- **Risk Assessment:** {ctx.risk_level.title()}")
        report.append(f"- **Strategic Fit:** {ctx.strategic_fit:.1%}")
        report.append(f"- **Growth Potential:** {ctx.growth_potential:.1%}")
        
        if ctx.context_factors:
            report.append(f"- **Context Factors:** {', '.join(ctx.context_factors)}")
        
        report.append("")
        report.append("---")
        report.append("*Generated by Adaptive Domain Intelligence - Pattern Recognition Engine*")
        report.append("*Consciousness-driven decision making with precision-first philosophy*")
        
        return "\n".join(report)

if __name__ == "__main__":
    # Initialize the pattern recognition engine
    engine = PatternRecognitionEngine()
    
    print("🎯 Adaptive Domain Intelligence - Pattern Recognition Engine")
    print("============================================================")
    print("Ready to apply Sandy's wisdom patterns to new job opportunities!")
    print()
    print("Loaded wisdom profiles:")
    for profile_id in engine.wisdom_profiles.keys():
        print(f"  • {profile_id}")
    print()
    print("Ready for intelligent decision-making with learned patterns!")
