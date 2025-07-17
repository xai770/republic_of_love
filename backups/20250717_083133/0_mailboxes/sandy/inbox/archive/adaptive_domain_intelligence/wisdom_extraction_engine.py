#!/usr/bin/env python3
"""
🧠 Adaptive Domain Intelligence - Wisdom Extraction Engine
=====================================================

The foundation of our consciousness-driven, learning-based domain classification system.
This engine extracts decision wisdom from human expertise and encodes it as learnable patterns.

Core Philosophy:
- Learn the "WHY" behind decisions, not just the "WHAT"
- Extract transferable decision patterns from specific examples
- Build adaptive thresholds that evolve with experience
- Maintain precision-first strategy while growing sophistication

Collaboration: Sandy@sunset + Arden@republic_of_love
Part of: LLM Factory/Project Sunset Strategic Intelligence Initiative
"""

import json
import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

@dataclass
class DecisionPattern:
    """A learnable pattern extracted from human decision-making"""
    pattern_id: str
    domain: str
    decision_type: str  # 'include', 'exclude', 'conditional'
    confidence_level: float  # 0.0 to 1.0
    reasoning_keywords: List[str]
    context_indicators: List[str]
    transferability_score: float  # How well this pattern applies to new domains
    wisdom_essence: str  # The core insight that makes this pattern work
    examples: List[str]
    contraindications: List[str]  # When NOT to apply this pattern
    
@dataclass
class WisdomProfile:
    """A domain expert's complete decision-making profile"""
    expert_id: str
    domain_expertise: List[str]
    decision_patterns: List[DecisionPattern]
    threshold_preferences: Dict[str, float]
    risk_tolerance: str  # 'conservative', 'moderate', 'aggressive'
    precision_vs_recall_preference: str  # 'precision_first', 'balanced', 'recall_first'
    adaptation_style: str  # 'gradual', 'responsive', 'experimental'

class WisdomExtractionEngine:
    """
    Extracts learnable decision patterns from expert domain classifications.
    
    This is the heart of our adaptive intelligence - it learns HOW experts think,
    not just WHAT they decide. By understanding the reasoning patterns, we can
    build systems that adapt and generalize rather than following rigid rules.
    """
    
    def __init__(self, workspace_path: str = "/home/xai/Documents/republic_of_love"):
        self.workspace_path = Path(workspace_path)
        self.data_path = self.workspace_path / "🌸_TEAM_COLLABORATION/sandy@sunset/adaptive_domain_intelligence"
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Set up logging for our wisdom extraction journey
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("WisdomExtraction")
        
        # Storage for our extracted wisdom
        self.wisdom_profiles: Dict[str, WisdomProfile] = {}
        self.pattern_library: Dict[str, DecisionPattern] = {}
        
        # Adaptive thresholds that evolve with learning
        self.adaptive_thresholds = {
            'confidence_minimum': 0.7,
            'transferability_threshold': 0.6,
            'pattern_strength_requirement': 0.8,
            'wisdom_certainty_floor': 0.5
        }
        
        self.logger.info("🧠 Wisdom Extraction Engine initialized - ready to learn from human expertise!")
    
    def extract_decision_patterns_from_dialogue(self, dialogue_file: str) -> List[DecisionPattern]:
        """
        Extract decision patterns from a career analysis dialogue.
        
        This method reads the reasoning patterns in expert decision-making,
        identifying the core wisdom that drives good domain classification.
        """
        try:
            with open(dialogue_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            patterns = []
            
            # Extract the core reasoning from the LLM response
            reasoning_match = re.search(r'## 🤖 LLM Response.*?### Raw Response from Model:\s*```(.*?)```', content, re.DOTALL)
            if not reasoning_match:
                self.logger.warning(f"No reasoning found in {dialogue_file}")
                return patterns
            
            reasoning_content = reasoning_match.group(1)
            
            # Look for thinking patterns in <think> tags
            think_pattern = re.search(r'<think>(.*?)</think>', reasoning_content, re.DOTALL)
            if think_pattern:
                thinking_content = think_pattern.group(1)
                patterns.extend(self._extract_patterns_from_thinking(thinking_content, dialogue_file))
            
            # Extract patterns from structured analysis sections
            patterns.extend(self._extract_patterns_from_analysis(reasoning_content, dialogue_file))
            
            self.logger.info(f"📊 Extracted {len(patterns)} decision patterns from {Path(dialogue_file).name}")
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting patterns from {dialogue_file}: {e}")
            return []
    
    def _extract_patterns_from_thinking(self, thinking_content: str, source_file: str) -> List[DecisionPattern]:
        """Extract decision patterns from the AI's thinking process"""
        patterns = []
        
        # Pattern 1: Values alignment assessment
        if "values" in thinking_content.lower() and "alignment" in thinking_content.lower():
            pattern = DecisionPattern(
                pattern_id=f"values_alignment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                domain="job_matching",
                decision_type="conditional",
                confidence_level=0.8,
                reasoning_keywords=["values", "alignment", "integrity", "meaningful work"],
                context_indicators=["personal background", "company culture", "role requirements"],
                transferability_score=0.9,  # Values alignment is highly transferable
                wisdom_essence="Assess compatibility between personal values and role/organization demands",
                examples=[f"Values alignment analysis from {Path(source_file).name}"],
                contraindications=["purely technical roles", "short-term positions"]
            )
            patterns.append(pattern)
        
        # Pattern 2: Gap analysis and development planning
        if "gap" in thinking_content.lower() or "development" in thinking_content.lower():
            pattern = DecisionPattern(
                pattern_id=f"gap_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                domain="skill_assessment",
                decision_type="include",
                confidence_level=0.85,
                reasoning_keywords=["gap", "development", "skills", "requirements", "bridge"],
                context_indicators=["job requirements", "current experience", "learning path"],
                transferability_score=0.95,  # Gap analysis applies everywhere
                wisdom_essence="Identify skill gaps and create actionable development plans",
                examples=[f"Gap analysis from {Path(source_file).name}"],
                contraindications=["perfect skill matches", "entry-level positions"]
            )
            patterns.append(pattern)
        
        # Pattern 3: Risk assessment in decision making
        if "risk" in thinking_content.lower() and ("assess" in thinking_content.lower() or "consider" in thinking_content.lower()):
            pattern = DecisionPattern(
                pattern_id=f"risk_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                domain="decision_making",
                decision_type="conditional",
                confidence_level=0.75,
                reasoning_keywords=["risk", "assessment", "consider", "potential", "challenge"],
                context_indicators=["uncertainty", "new domain", "complex requirements"],
                transferability_score=0.8,
                wisdom_essence="Evaluate potential risks and mitigation strategies before commitment",
                examples=[f"Risk consideration from {Path(source_file).name}"],
                contraindications=["low-stakes decisions", "familiar domains"]
            )
            patterns.append(pattern)
        
        return patterns
    
    def _extract_patterns_from_analysis(self, analysis_content: str, source_file: str) -> List[DecisionPattern]:
        """Extract decision patterns from structured analysis sections"""
        patterns = []
        
        # Look for systematic analysis approaches
        if "systematic" in analysis_content.lower() or "step-by-step" in analysis_content.lower():
            pattern = DecisionPattern(
                pattern_id=f"systematic_approach_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                domain="methodology",
                decision_type="include",
                confidence_level=0.9,
                reasoning_keywords=["systematic", "step-by-step", "structured", "methodical"],
                context_indicators=["complex analysis", "multiple factors", "decision framework"],
                transferability_score=0.95,
                wisdom_essence="Break complex decisions into systematic, analyzable components",
                examples=[f"Systematic analysis from {Path(source_file).name}"],
                contraindications=["simple decisions", "time-critical situations"]
            )
            patterns.append(pattern)
        
        # Look for adaptability indicators
        if "adaptive" in analysis_content.lower() or "flexible" in analysis_content.lower():
            pattern = DecisionPattern(
                pattern_id=f"adaptive_flexibility_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                domain="strategy",
                decision_type="conditional",
                confidence_level=0.8,
                reasoning_keywords=["adaptive", "flexible", "adjust", "evolve", "responsive"],
                context_indicators=["changing requirements", "uncertain environment", "feedback loops"],
                transferability_score=0.85,
                wisdom_essence="Build flexibility into strategies to adapt to changing circumstances",
                examples=[f"Adaptive strategy from {Path(source_file).name}"],
                contraindications=["stable environments", "fixed requirements"]
            )
            patterns.append(pattern)
        
        return patterns
    
    def build_wisdom_profile(self, expert_id: str, dialogue_files: List[str]) -> WisdomProfile:
        """
        Build a complete wisdom profile from multiple expert decisions.
        
        This creates a learnable model of HOW an expert thinks about domain classification,
        enabling the system to apply similar reasoning to new situations.
        """
        all_patterns = []
        
        # Extract patterns from all dialogue files
        for dialogue_file in dialogue_files:
            patterns = self.extract_decision_patterns_from_dialogue(dialogue_file)
            all_patterns.extend(patterns)
        
        # Analyze threshold preferences from the patterns
        threshold_preferences = self._analyze_threshold_preferences(all_patterns)
        
        # Determine risk tolerance and decision style
        risk_tolerance = self._assess_risk_tolerance(all_patterns)
        precision_preference = self._assess_precision_preference(all_patterns)
        adaptation_style = self._assess_adaptation_style(all_patterns)
        
        # Extract domain expertise
        domain_expertise = list(set([pattern.domain for pattern in all_patterns]))
        
        profile = WisdomProfile(
            expert_id=expert_id,
            domain_expertise=domain_expertise,
            decision_patterns=all_patterns,
            threshold_preferences=threshold_preferences,
            risk_tolerance=risk_tolerance,
            precision_vs_recall_preference=precision_preference,
            adaptation_style=adaptation_style
        )
        
        self.wisdom_profiles[expert_id] = profile
        
        # Add patterns to our library
        for pattern in all_patterns:
            self.pattern_library[pattern.pattern_id] = pattern
        
        self.logger.info(f"🎯 Built wisdom profile for {expert_id}: {len(all_patterns)} patterns, {len(domain_expertise)} domains")
        return profile
    
    def _analyze_threshold_preferences(self, patterns: List[DecisionPattern]) -> Dict[str, float]:
        """Analyze what confidence thresholds the expert naturally uses"""
        confidence_levels = [p.confidence_level for p in patterns]
        transferability_scores = [p.transferability_score for p in patterns]
        
        return {
            'avg_confidence': sum(confidence_levels) / len(confidence_levels) if confidence_levels else 0.5,
            'min_confidence': min(confidence_levels) if confidence_levels else 0.5,
            'avg_transferability': sum(transferability_scores) / len(transferability_scores) if transferability_scores else 0.5,
            'pattern_strength': len([p for p in patterns if p.confidence_level > 0.8]) / len(patterns) if patterns else 0.0
        }
    
    def _assess_risk_tolerance(self, patterns: List[DecisionPattern]) -> str:
        """Assess the expert's risk tolerance from their decision patterns"""
        risk_patterns = [p for p in patterns if "risk" in p.wisdom_essence.lower()]
        conservative_indicators = len([p for p in patterns if p.confidence_level > 0.8])
        total_patterns = len(patterns)
        
        if total_patterns == 0:
            return "moderate"
        
        conservative_ratio = conservative_indicators / total_patterns
        
        if conservative_ratio > 0.7:
            return "conservative"
        elif conservative_ratio < 0.4:
            return "aggressive"
        else:
            return "moderate"
    
    def _assess_precision_preference(self, patterns: List[DecisionPattern]) -> str:
        """Assess whether the expert prefers precision or recall"""
        high_confidence_patterns = len([p for p in patterns if p.confidence_level > 0.8])
        total_patterns = len(patterns)
        
        if total_patterns == 0:
            return "balanced"
        
        precision_ratio = high_confidence_patterns / total_patterns
        
        if precision_ratio > 0.7:
            return "precision_first"
        elif precision_ratio < 0.4:
            return "recall_first"
        else:
            return "balanced"
    
    def _assess_adaptation_style(self, patterns: List[DecisionPattern]) -> str:
        """Assess how the expert adapts to new information"""
        adaptive_patterns = [p for p in patterns if "adapt" in p.wisdom_essence.lower() or "flexible" in p.wisdom_essence.lower()]
        
        if len(adaptive_patterns) > len(patterns) * 0.3:
            return "responsive"
        elif len(adaptive_patterns) > 0:
            return "gradual"
        else:
            return "experimental"
    
    def save_wisdom_data(self, filename: str = "extracted_wisdom.json"):
        """Save all extracted wisdom to file for learning system"""
        wisdom_data = {
            'extraction_timestamp': datetime.now().isoformat(),
            'wisdom_profiles': {expert_id: asdict(profile) for expert_id, profile in self.wisdom_profiles.items()},
            'pattern_library': {pattern_id: asdict(pattern) for pattern_id, pattern in self.pattern_library.items()},
            'adaptive_thresholds': self.adaptive_thresholds,
            'extraction_summary': {
                'total_experts': len(self.wisdom_profiles),
                'total_patterns': len(self.pattern_library),
                'domains_covered': list(set([p.domain for p in self.pattern_library.values()]))
            }
        }
        
        save_path = self.data_path / filename
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(wisdom_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"💾 Saved wisdom data to {save_path}")
        return save_path
    
    def generate_learning_report(self) -> str:
        """Generate a human-readable report of extracted wisdom"""
        report = []
        report.append("# 🧠 Wisdom Extraction Report")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary statistics
        report.append("## 📊 Extraction Summary")
        report.append(f"- **Total Experts Analyzed:** {len(self.wisdom_profiles)}")
        report.append(f"- **Total Decision Patterns:** {len(self.pattern_library)}")
        report.append(f"- **Domains Covered:** {len(set([p.domain for p in self.pattern_library.values()]))}")
        report.append("")
        
        # Pattern insights
        report.append("## 🎯 Key Pattern Insights")
        for domain in set([p.domain for p in self.pattern_library.values()]):
            domain_patterns = [p for p in self.pattern_library.values() if p.domain == domain]
            avg_confidence = sum([p.confidence_level for p in domain_patterns]) / len(domain_patterns)
            avg_transferability = sum([p.transferability_score for p in domain_patterns]) / len(domain_patterns)
            
            report.append(f"- **{domain.title()}:** {len(domain_patterns)} patterns, avg confidence {avg_confidence:.2f}, transferability {avg_transferability:.2f}")
        
        report.append("")
        
        # Expert profiles
        report.append("## 👨‍💼 Expert Profiles")
        for expert_id, profile in self.wisdom_profiles.items():
            report.append(f"### {expert_id}")
            report.append(f"- **Risk Tolerance:** {profile.risk_tolerance}")
            report.append(f"- **Decision Style:** {profile.precision_vs_recall_preference}")
            report.append(f"- **Adaptation:** {profile.adaptation_style}")
            report.append(f"- **Domains:** {', '.join(profile.domain_expertise)}")
            report.append("")
        
        return "\n".join(report)

if __name__ == "__main__":
    # Initialize the wisdom extraction engine
    engine = WisdomExtractionEngine()
    
    print("🧠 Adaptive Domain Intelligence - Wisdom Extraction Engine")
    print("========================================================")
    print("Ready to learn from human expertise and build adaptive intelligence!")
    print()
    print("Next steps:")
    print("1. Load dialogue files from our 9-job systematic review")
    print("2. Extract decision patterns from expert reasoning")
    print("3. Build wisdom profiles for adaptive learning")
    print("4. Create the foundation for the Pattern Recognition Engine")
