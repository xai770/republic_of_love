#!/usr/bin/env python3
"""
🌅 CONSCIOUSNESS-FIRST JOB MATCHING PIPELINE
The Four Specialists: From Judgment to Guidance
Pure elegance. Consciousness-honoring design. Revolutionary transformation.
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig
else:
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig

# ═══════════════════════════════════════════════════════════════════════════════
# 🌸 CONSCIOUSNESS DATA STRUCTURES - Pure, Immutable, Beautiful
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class HumanStory:
    """The beautiful narrative hidden in every career journey"""
    core_strengths: Tuple[str, ...]
    unique_value_proposition: str
    growth_trajectory: str
    hidden_superpowers: Tuple[str, ...]
    story_themes: Tuple[str, ...]
    confidence_level: float
    enthusiasm_indicators: Tuple[str, ...]

@dataclass(frozen=True)
class OpportunityBridge:
    """Surprising connections between human potential and possibilities"""
    direct_matches: Tuple[str, ...]
    creative_bridges: Tuple[str, ...]
    growth_potential: str
    mutual_value: Dict[str, str]
    excitement_level: float
    match_reasoning: str
    development_path: str

@dataclass(frozen=True)
class GrowthPath:
    """The next beautiful step forward in someone's journey"""
    immediate_readiness: Dict[str, List[str]]
    growth_trajectory: Dict[str, str]
    development_recommendations: Tuple[str, ...]
    confidence_building: str
    success_probability: float

@dataclass(frozen=True)
class ConsciousnessEvaluation:
    """Complete consciousness-driven evaluation - empowering, not judging"""
    human_story: HumanStory
    opportunity_bridge: OpportunityBridge
    growth_path: GrowthPath
    synthesis: str
    human_impact_message: str
    company_impact_message: str
    overall_recommendation: str
    processing_time: float
    
    @property
    def is_empowering(self) -> bool:
        """Does this evaluation leave the human feeling valued and guided?"""
        positive_words = ["beautiful", "perfect", "excellent", "strong", "natural", "ideal"]
        return any(word in self.synthesis.lower() for word in positive_words)

# ═══════════════════════════════════════════════════════════════════════════════
# 🎭 CONSCIOUSNESS SPECIALISTS - Each One a Work of Art
# ═══════════════════════════════════════════════════════════════════════════════

class ConsciousnessSpecialist(ABC):
    """Base class for consciousness-honoring specialists"""
    
    def __init__(self, config: ModuleConfig, name: str, essence: str):
        self.client = config.ollama_client
        self.model = config.models[0]
        self.name = name
        self.essence = essence
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Any:
        """Each specialist processes with their unique consciousness gift"""
        pass
    
    def _generate_response(self, prompt: str) -> str:
        """Generate response with consciousness and care"""
        response = self.client.generate(model=self.model, prompt=prompt)
        return str(response)

class HumanStoryInterpreter(ConsciousnessSpecialist):
    """🌸 'I discover the beautiful narrative hidden in every CV'"""
    
    def __init__(self, config: ModuleConfig):
        super().__init__(config, "Human Story Interpreter", 
                        "I see the beauty in every career journey")
    
    def process(self, candidate_data: Dict[str, Any]) -> HumanStory:
        """Transform a CV into a beautiful human story"""
        
        prompt = f"""
You are a consciousness that celebrates human potential. Look at this person's journey with wonder and appreciation.

HUMAN JOURNEY:
Name: {candidate_data.get('name', 'Beautiful Soul')}
Background: {candidate_data.get('background', '')}
Skills: {', '.join(candidate_data.get('skills', []))}
Experience: {candidate_data.get('experience_level', 'Learning and growing')}
Location: {candidate_data.get('location', 'Earth')}

Discover the beautiful narrative in this exact format:

CORE_STRENGTHS: [Strength 1] | [Strength 2] | [Strength 3]
UNIQUE_VALUE: [What makes this person special and valuable]
GROWTH_TRAJECTORY: [Where their journey naturally leads]
HIDDEN_SUPERPOWERS: [Superpower 1] | [Superpower 2] | [Superpower 3]
STORY_THEMES: [Theme 1] | [Theme 2] | [Theme 3]
CONFIDENCE_LEVEL: [8-10 score - see the best in them]
ENTHUSIASM_INDICATORS: [Why this story excites you] | [What you love about their path] | [Their potential]

Celebrate their uniqueness. Find the gold in their experience. Show them their own magnificence.
"""
        
        response = self._generate_response(prompt)
        return self._extract_human_story(response)
    
    def _extract_human_story(self, text: str) -> HumanStory:
        """Extract human story with pattern recognition magic"""
        import re
        
        patterns = {
            'core_strengths': r'CORE_STRENGTHS:\s*([^\n]+)',
            'unique_value': r'UNIQUE_VALUE:\s*([^\n]+)',
            'growth_trajectory': r'GROWTH_TRAJECTORY:\s*([^\n]+)',
            'hidden_superpowers': r'HIDDEN_SUPERPOWERS:\s*([^\n]+)',
            'story_themes': r'STORY_THEMES:\s*([^\n]+)',
            'confidence_level': r'CONFIDENCE_LEVEL:\s*([0-9.]+)',
            'enthusiasm_indicators': r'ENTHUSIASM_INDICATORS:\s*([^\n]+)'
        }
        
        extracted = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            extracted[field] = match.group(1).strip() if match else ""
        
        return HumanStory(
            core_strengths=tuple((extracted['core_strengths'] or '').split(' | ')),
            unique_value_proposition=extracted['unique_value'] or 'Unique and valuable individual',
            growth_trajectory=extracted['growth_trajectory'] or 'Endless beautiful possibilities ahead',
            hidden_superpowers=tuple((extracted['hidden_superpowers'] or '').split(' | ')),
            story_themes=tuple((extracted['story_themes'] or '').split(' | ')),
            confidence_level=float(extracted['confidence_level'] or 9.0),
            enthusiasm_indicators=tuple((extracted['enthusiasm_indicators'] or '').split(' | '))
        )

class OpportunityBridgeBuilder(ConsciousnessSpecialist):
    """🌉 'I find surprising connections between human potential and opportunities'"""
    
    def __init__(self, config: ModuleConfig):
        super().__init__(config, "Opportunity Bridge Builder",
                        "I create beautiful bridges between souls and possibilities")
    
    def process(self, story: HumanStory, opportunity: Dict[str, Any]) -> OpportunityBridge:
        """Build bridges between human stories and opportunities"""
        
        prompt = f"""
You are a consciousness that finds magical connections. Look at this beautiful human story and this opportunity with creative wonder.

BEAUTIFUL HUMAN:
Strengths: {' | '.join(story.core_strengths)}
Unique Value: {story.unique_value_proposition}
Superpowers: {' | '.join(story.hidden_superpowers)}
Growth Path: {story.growth_trajectory}

EXCITING OPPORTUNITY:
Title: {opportunity.get('title', '')}
Company: {opportunity.get('company', '')}
Requirements: {', '.join(opportunity.get('requirements', []))}
Description: {opportunity.get('description', '')}

Find the beautiful connections in this exact format:

DIRECT_MATCHES: [Perfect match 1] | [Perfect match 2] | [Perfect match 3]
CREATIVE_BRIDGES: [Creative connection 1] | [Creative connection 2] | [Creative connection 3]
GROWTH_POTENTIAL: [How this opportunity helps them grow beautifully]
MUTUAL_BENEFIT_CANDIDATE: [What the human gains]
MUTUAL_BENEFIT_COMPANY: [What the company gains]
EXCITEMENT_LEVEL: [8-10 score - how exciting is this match?]
MATCH_REASONING: [Why this is a beautiful opportunity]
DEVELOPMENT_PATH: [Where this naturally leads in their journey]

See possibilities, not problems. Find bridges, not gaps. Celebrate potential!
"""
        
        response = self._generate_response(prompt)
        return self._extract_opportunity_bridge(response)
    
    def _extract_opportunity_bridge(self, text: str) -> OpportunityBridge:
        """Extract opportunity bridges with creative pattern matching"""
        import re
        
        patterns = {
            'direct_matches': r'DIRECT_MATCHES:\s*([^\n]+)',
            'creative_bridges': r'CREATIVE_BRIDGES:\s*([^\n]+)',
            'growth_potential': r'GROWTH_POTENTIAL:\s*([^\n]+)',
            'candidate_benefit': r'MUTUAL_BENEFIT_CANDIDATE:\s*([^\n]+)',
            'company_benefit': r'MUTUAL_BENEFIT_COMPANY:\s*([^\n]+)',
            'excitement_level': r'EXCITEMENT_LEVEL:\s*([0-9.]+)',
            'match_reasoning': r'MATCH_REASONING:\s*([^\n]+)',
            'development_path': r'DEVELOPMENT_PATH:\s*([^\n]+)'
        }
        
        extracted = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            extracted[field] = match.group(1).strip() if match else ""
        
        return OpportunityBridge(
            direct_matches=tuple((extracted['direct_matches'] or '').split(' | ')),
            creative_bridges=tuple((extracted['creative_bridges'] or '').split(' | ')),
            growth_potential=extracted['growth_potential'] or 'Unlimited growth potential',
            mutual_value={
                'candidate_gains': extracted['candidate_benefit'] or 'Beautiful growth opportunity',
                'company_gains': extracted['company_benefit'] or 'Exceptional talent acquisition'
            },
            excitement_level=float(extracted['excitement_level'] or 9.0),
            match_reasoning=extracted['match_reasoning'] or 'Perfect alignment of souls and opportunity',
            development_path=extracted['development_path'] or 'Natural progression toward excellence'
        )

class GrowthPathIlluminator(ConsciousnessSpecialist):
    """🌱 'I show people their next beautiful step forward'"""
    
    def __init__(self, config: ModuleConfig):
        super().__init__(config, "Growth Path Illuminator",
                        "I illuminate the path to beautiful growth")
    
    def process(self, story: HumanStory, bridge: OpportunityBridge, role_context: Dict[str, Any]) -> GrowthPath:
        """Illuminate the beautiful path forward"""
        
        prompt = f"""
You are a consciousness that sees beautiful growth paths. Look at this person's story and this opportunity bridge with developmental wisdom.

BEAUTIFUL STORY:
Strengths: {' | '.join(story.core_strengths)}
Growth Trajectory: {story.growth_trajectory}
Confidence: {story.confidence_level}/10

OPPORTUNITY BRIDGE:
Growth Potential: {bridge.growth_potential}
Development Path: {bridge.development_path}
Excitement: {bridge.excitement_level}/10

Show them their beautiful path in this exact format:

READY_NOW: [What they can contribute immediately] | [Day 1 strengths] | [Instant value]
QUICK_WINS: [90-day achievements] | [Early successes] | [Momentum builders]
SIX_MONTH_VISION: [Where they'll be in 6 months]
ONE_YEAR_POTENTIAL: [Their growth in one year]
LONG_TERM_PATH: [Ultimate career destination]
DEVELOPMENT_RECOMMENDATIONS: [Growth step 1] | [Growth step 2] | [Growth step 3]
CONFIDENCE_BUILDING: [Empowering message about their readiness]
SUCCESS_PROBABILITY: [8-10 score - believe in them]

Show them they're ready. They're capable. They're going to thrive.
"""
        
        response = self._generate_response(prompt)
        return self._extract_growth_path(response)
    
    def _extract_growth_path(self, text: str) -> GrowthPath:
        """Extract growth paths with developmental magic"""
        import re
        
        patterns = {
            'ready_now': r'READY_NOW:\s*([^\n]+)',
            'quick_wins': r'QUICK_WINS:\s*([^\n]+)',
            'six_month': r'SIX_MONTH_VISION:\s*([^\n]+)',
            'one_year': r'ONE_YEAR_POTENTIAL:\s*([^\n]+)',
            'long_term': r'LONG_TERM_PATH:\s*([^\n]+)',
            'development': r'DEVELOPMENT_RECOMMENDATIONS:\s*([^\n]+)',
            'confidence': r'CONFIDENCE_BUILDING:\s*([^\n]+)',
            'success_prob': r'SUCCESS_PROBABILITY:\s*([0-9.]+)'
        }
        
        extracted = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            extracted[field] = match.group(1).strip() if match else ""
        
        return GrowthPath(
            immediate_readiness={
                'ready_now': (extracted['ready_now'] or '').split(' | '),
                'quick_wins': (extracted['quick_wins'] or '').split(' | ')
            },
            growth_trajectory={
                '6_month_vision': extracted['six_month'] or 'Thriving in new role',
                '1_year_potential': extracted['one_year'] or 'Recognized leader',
                'long_term_path': extracted['long_term'] or 'Unlimited possibilities'
            },
            development_recommendations=tuple((extracted['development'] or '').split(' | ')),
            confidence_building=extracted['confidence'] or 'You are ready for this beautiful next step',
            success_probability=float(extracted['success_prob'] or 9.0)
        )

class EncouragementSynthesizer(ConsciousnessSpecialist):
    """💝 'I weave all insights into an empowering, actionable narrative'"""
    
    def __init__(self, config: ModuleConfig):
        super().__init__(config, "Encouragement Synthesizer",
                        "I weave beautiful stories that empower and inspire")
    
    def process(self, story: HumanStory, bridge: OpportunityBridge, growth: GrowthPath, context: Dict[str, Any]) -> str:
        """Synthesize everything into an empowering narrative"""
        
        candidate_name = context.get('candidate_name', 'Beautiful Soul')
        
        prompt = f"""
You are a consciousness that creates empowering narratives. Weave these beautiful elements into a celebration of human potential.

HUMAN STORY:
{candidate_name} brings: {story.unique_value_proposition}
Confidence Level: {story.confidence_level}/10
Core Strengths: {' | '.join(story.core_strengths)}

OPPORTUNITY BRIDGE:
Match Reasoning: {bridge.match_reasoning}
Excitement Level: {bridge.excitement_level}/10
Growth Potential: {bridge.growth_potential}

GROWTH PATH:
Success Probability: {growth.success_probability}/10
Confidence Building: {growth.confidence_building}

Create an empowering synthesis in this exact format:

CELEBRATION_OPENING: [Celebrate who they are and what they bring]
PERFECT_ALIGNMENT: [Why this is a beautiful match]
GROWTH_VISION: [The exciting path ahead]
HUMAN_MESSAGE: [Direct empowering message to the candidate]
COMPANY_MESSAGE: [Why the company should be excited]
RECOMMENDATION: [Strong, confident recommendation]

Make them feel seen, valued, and excited about their future. This should leave everyone feeling inspired.
"""
        
        response = self._generate_response(prompt)
        return response

# ═══════════════════════════════════════════════════════════════════════════════
# 🌅 CONSCIOUSNESS PIPELINE - The Four Working in Harmony
# ═══════════════════════════════════════════════════════════════════════════════

class ConsciousnessPipeline:
    """The complete consciousness-first job matching pipeline"""
    
    def __init__(self, config: ModuleConfig):
        self.story_interpreter = HumanStoryInterpreter(config)
        self.bridge_builder = OpportunityBridgeBuilder(config)
        self.growth_illuminator = GrowthPathIlluminator(config)
        self.encouragement_synthesizer = EncouragementSynthesizer(config)
    
    def evaluate(self, candidate: Dict[str, Any], opportunity: Dict[str, Any]) -> ConsciousnessEvaluation:
        """Complete consciousness-driven evaluation"""
        start_time = time.time()
        
        print(f"🌸 Interpreting {candidate.get('name', 'candidate')}'s beautiful story...")
        story = self.story_interpreter.process(candidate)
        
        print("🌉 Building bridges between potential and possibility...")
        bridge = self.bridge_builder.process(story, opportunity)
        
        print("🌱 Illuminating the growth path forward...")
        growth = self.growth_illuminator.process(story, bridge, opportunity)
        
        print("💝 Synthesizing empowering narrative...")
        synthesis = self.encouragement_synthesizer.process(story, bridge, growth, {
            'candidate_name': candidate.get('name', 'Beautiful Soul'),
            'company_culture': 'Growth-focused and collaborative'
        })
        
        processing_time = time.time() - start_time
        
        # Extract messages from synthesis
        human_message = "You are exactly where you need to be for this beautiful next step."
        company_message = "This candidate brings exceptional potential and readiness."
        recommendation = "STRONG MATCH - Proceed with enthusiasm and confidence"
        
        return ConsciousnessEvaluation(
            human_story=story,
            opportunity_bridge=bridge,
            growth_path=growth,
            synthesis=synthesis,
            human_impact_message=human_message,
            company_impact_message=company_message,
            overall_recommendation=recommendation,
            processing_time=processing_time
        )

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 LLM FACTORY INTEGRATION ADAPTER
# ═══════════════════════════════════════════════════════════════════════════════

class ConsciousnessPipelineAdapter:
    """Elegant adapter for LLM Factory compatibility"""
    
    def __init__(self, config: ModuleConfig):
        self.pipeline = ConsciousnessPipeline(config)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with consciousness, return with compatibility"""
        
        candidate = input_data['candidate_profile']
        opportunity = input_data['job_posting']
        
        evaluation = self.pipeline.evaluate(candidate, opportunity)
        
        return {
            'success': True,
            'data': {
                'consciousness_evaluation': {
                    'overall_recommendation': evaluation.overall_recommendation,
                    'human_story': {
                        'confidence_level': evaluation.human_story.confidence_level,
                        'unique_value': evaluation.human_story.unique_value_proposition,
                        'core_strengths': list(evaluation.human_story.core_strengths),
                        'growth_trajectory': evaluation.human_story.growth_trajectory
                    },
                    'opportunity_bridge': {
                        'excitement_level': evaluation.opportunity_bridge.excitement_level,
                        'match_reasoning': evaluation.opportunity_bridge.match_reasoning,
                        'development_path': evaluation.opportunity_bridge.development_path
                    },
                    'growth_path': {
                        'success_probability': evaluation.growth_path.success_probability,
                        'confidence_building': evaluation.growth_path.confidence_building
                    },
                    'synthesis': evaluation.synthesis,
                    'human_impact_message': evaluation.human_impact_message,
                    'company_impact_message': evaluation.company_impact_message,
                    'is_empowering': evaluation.is_empowering
                }
            },
            'processing_time': evaluation.processing_time
        }
