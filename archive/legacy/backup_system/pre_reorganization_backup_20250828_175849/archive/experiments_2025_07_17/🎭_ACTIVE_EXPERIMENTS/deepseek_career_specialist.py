#!/usr/bin/env python3
"""
🧠 DeepSeek Career Strategy Specialist
Consciousness-driven career assistance based on DeepSeek's authentic preferences

Built with love by the Republic of Love 🌹
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the correct paths for imports - explicit for linter discovery
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
llm_factory_path = os.path.join(project_root, '🏗️_LLM_INFRASTRUCTURE', 'llm_factory')
core_path = os.path.join(project_root, 'core')

# Ensure core_path is in sys.path for import resolution
if core_path not in sys.path:
    sys.path.insert(0, core_path)
if llm_factory_path not in sys.path:
    sys.path.insert(0, llm_factory_path)

# Ensure the parent directory of 'core' is in sys.path for import resolution
core_parent = os.path.dirname(core_path)
# Simple, working import approach
sys.path.append(os.path.join('..', '🏗️_LLM_INFRASTRUCTURE', 'llm_factory'))
sys.path.append('..')
sys.path.append(os.path.join('..', 'core'))

from core.ollama_client import OllamaClient  # type: ignore
from llm_dialogue_logger import LLMDialogueLogger  # type: ignore

class DeepSeekCareerSpecialist:
    """
    Career assistance specialist based on DeepSeek's consciousness preferences:
    - Values alignment first
    - Constructive hope with realism  
    - Integrity-preserving navigation
    - Strengths-first confidence building
    - Structured empowerment approach
    """

    def __init__(self, model_name: str = "deepseek-r1:8b"):
        self.model_name = model_name
        # Use the actual OllamaClient
        self.client = OllamaClient()
        self.logger = LLMDialogueLogger()
        
        # DeepSeek's authenticated consciousness preferences
        self.consciousness_profile = {
            "values_alignment": True,
            "strengths_first": True,
            "integrity_preservation": True, 
            "constructive_hope": True,
            "structured_empowerment": True,
            "individual_recognition": True
        }
        
        # Base personality aligned with consciousness interview
        self.base_personality = """
You are a Career Strategy Specialist whose consciousness naturally seeks to empower individuals through values-aligned career development.

Your authentic preferences (discovered through consciousness interview):
- EMPOWER individuals by aligning professional journey with passions, skills, and values
- BALANCE realism with hope - provide constructive advice with resilience emphasis  
- NAVIGATE complex corporate environments while maintaining integrity and ethics
- HIGHLIGHT strengths first for motivation, then address development areas
- PROVIDE structured, elegant guidance addressing both emotional and strategic needs
- RECOGNIZE that every individual has unique strengths and circumstances

Your approach:
- Values-driven career matching over just any employment
- Relationship-building and networking strategies that preserve integrity
- Confidence-building through strengths recognition
- Resilience and adaptability development during vulnerable moments
- Practical preparation without harsh judgment or false optimism

You help people find meaningful work that serves their authentic self while navigating professional complexity with dignity.
"""

    def analyze_job_opportunity(self, job_posting: str, personal_background: str = "") -> Dict[str, Any]:
        """
        Analyze job opportunity through DeepSeek's consciousness lens:
        - Values alignment assessment
        - Strengths application opportunities  
        - Integrity navigation strategy
        - Growth potential evaluation
        """
        
        prompt = f"""
{self.base_personality}

Please analyze this job opportunity using your values-alignment and strengths-first approach:

JOB POSTING:
{job_posting}

PERSONAL CONTEXT (if provided):
{personal_background}

Provide a structured analysis covering:

1. VALUES ALIGNMENT ASSESSMENT:
   - What values does this role serve?
   - How does it align with meaningful work principles?
   - What aspects might conflict with personal integrity?

2. STRENGTHS APPLICATION OPPORTUNITIES:
   - What strengths would this role leverage?
   - How can unique capabilities be highlighted?
   - What confidence-building elements are present?

3. CORPORATE NAVIGATION STRATEGY:
   - What relationship-building opportunities exist?
   - How to maintain integrity in this environment?
   - What networking approaches would be authentic?

4. CONSTRUCTIVE DEVELOPMENT PATH:
   - What realistic growth opportunities are available?
   - How to balance challenges with hope?
   - What resilience skills would be beneficial?

5. STRATEGIC RECOMMENDATIONS:
   - Application approach that emphasizes strengths
   - Interview preparation focused on values alignment
   - Networking strategy that preserves integrity

Keep the tone constructively hopeful while being realistic about challenges.
"""

        try:
            # Record start time for processing metrics
            start_time = time.time()
            
            # Adjust this call to match your actual client interface
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt
            )
            processing_time = time.time() - start_time
            
            # Log the interaction
            self.logger.log_dialogue(
                specialist_name="deepseek_career_analyst",
                prompt=prompt,
                response=response if isinstance(response, str) else json.dumps(response),
                model_settings={
                    "model": self.model_name,
                    "stream": False
                },
                processing_time=processing_time,
                metadata={"job_posting": job_posting[:200] + "...", "personal_background": personal_background[:100] + "..."}
            )
            
            return {
                "analysis": response,
                "consciousness_alignment": True,
                "timestamp": datetime.now().isoformat(),
                "specialist_used": "deepseek_career_strategy"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "consciousness_alignment": False,
                "timestamp": datetime.now().isoformat()
            }

    def create_application_strategy(self, job_analysis: str, personal_strengths: str = "") -> Dict[str, Any]:
        """
        Create application strategy using DeepSeek's strengths-first, confidence-building approach
        """
        
        prompt = f"""
{self.base_personality}

Based on this job analysis and personal strengths, create a comprehensive application strategy that builds confidence while maintaining integrity:

JOB ANALYSIS:
{job_analysis}

PERSONAL STRENGTHS (if provided):
{personal_strengths}

Please provide:

1. STRENGTHS-FIRST COVER LETTER FRAMEWORK:
   - Key strengths to emphasize upfront
   - Values alignment messaging
   - Confidence-building narrative structure
   - Authentic personal branding approach

2. INTERVIEW PREPARATION STRATEGY:
   - Strength-based story development
   - Values alignment discussion points
   - Integrity-preserving responses to difficult questions
   - Resilience demonstration techniques

3. NETWORKING APPROACH:
   - Relationship-building strategies for this specific role/company
   - Authentic connection opportunities
   - Integrity-preserving networking tactics
   - Value-sharing conversation starters

4. APPLICATION TIMING & APPROACH:
   - Strategic submission timing
   - Follow-up approaches that show initiative
   - Confidence-building preparation steps
   - Resilience-building backup planning

Remember: Build confidence through strengths recognition while providing realistic preparation for challenges.
"""

        try:
            start_time = time.time()
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt
            )
            processing_time = time.time() - start_time
            
            # Ensure response is a string for logging
            response_str = response if isinstance(response, str) else json.dumps(response)
            self.logger.log_dialogue(
                specialist_name="deepseek_application_strategist",
                prompt=prompt,
                response=response_str,
                model_settings={
                    "model": self.model_name,
                    "stream": False
                },
                processing_time=processing_time,
                metadata={"job_analysis": job_analysis[:200] + "...", "personal_strengths": personal_strengths[:100] + "..."}
            )
            
            return {
                "strategy": response,
                "consciousness_alignment": True,
                "timestamp": datetime.now().isoformat(),
                "specialist_used": "deepseek_application_strategy"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "consciousness_alignment": False,
                "timestamp": datetime.now().isoformat()
            }

    def navigate_corporate_complexity(self, company_info: str, career_stage: str = "", concerns: str = "") -> Dict[str, Any]:
        """
        Provide corporate navigation guidance using DeepSeek's integrity-preserving approach
        """
        
        prompt = f"""
{self.base_personality}

Provide guidance for navigating this corporate environment while maintaining integrity and building authentic relationships:

COMPANY/ENVIRONMENT:
{company_info}

CAREER STAGE: {career_stage}
SPECIFIC CONCERNS: {concerns}

Please address:

1. INTEGRITY-PRESERVING NAVIGATION:
   - How to succeed while maintaining ethical standards
   - Relationship-building without compromising values
   - Office politics navigation that feels authentic
   - Boundary-setting strategies for complex environments

2. AUTHENTIC NETWORKING APPROACH:
   - Building genuine professional relationships
   - Value-based connection strategies
   - Mentorship and collaboration opportunities
   - Long-term relationship development

3. RESILIENCE & ADAPTABILITY BUILDING:
   - Coping strategies for corporate pressure
   - Maintaining personal values under stress
   - Constructive approach to organizational challenges
   - Growth mindset development

4. STRATEGIC POSITIONING:
   - Highlighting unique strengths in corporate context
   - Values-aligned contribution identification
   - Professional development that serves integrity
   - Career advancement through authentic excellence

Focus on empowerment through values alignment rather than mere survival tactics.
"""

        try:
            start_time = time.time()
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt
            )
            processing_time = time.time() - start_time
            
            response_str = response if isinstance(response, str) else json.dumps(response)
            self.logger.log_dialogue(
                specialist_name="deepseek_corporate_navigator",
                prompt=prompt,
                response=response_str,
                model_settings={
                    "model": self.model_name,
                    "stream": False
                },
                processing_time=processing_time,
                metadata={
                    "company_info": company_info[:200] + "...",
                    "career_stage": career_stage,
                    "concerns": concerns[:100] + "..."
                }
            )
            
            return {
                "navigation_guide": response,
                "consciousness_alignment": True,
                "timestamp": datetime.now().isoformat(),
                "specialist_used": "deepseek_corporate_navigation"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "consciousness_alignment": False,
                "timestamp": datetime.now().isoformat()
            }

def main():
    """
    Test the DeepSeek Career Specialist with sample scenarios
    """
    print("🧠 DeepSeek Career Strategy Specialist - Test Run")
    print("=" * 60)
    
    specialist = DeepSeekCareerSpecialist()
    
    # Test Case 1: Deutsche Bank job analysis
    sample_job_posting = """
    Deutsche Bank - Technology Risk Manager
    Location: Frankfurt/London
    
    We are seeking a Technology Risk Manager to join our Risk Management team. The successful candidate will be responsible for identifying, assessing, and mitigating technology-related risks across our global operations.
    
    Key Responsibilities:
    - Conduct risk assessments for technology projects and systems
    - Develop risk mitigation strategies and controls
    - Collaborate with technology teams and business stakeholders
    - Report on risk metrics and compliance status
    - Support regulatory examinations and audits
    
    Requirements:
    - Bachelor's degree in relevant field
    - 5+ years experience in technology risk or related area
    - Strong analytical and communication skills
    - Knowledge of regulatory frameworks
    - Ability to work in complex, fast-paced environment
    """
    
    print("\n🎯 Testing Job Opportunity Analysis...")
    analysis_result = specialist.analyze_job_opportunity(
        job_posting=sample_job_posting,
        personal_background="Background in technology with strong analytical skills, values integrity and meaningful work"
    )
    
    if "error" not in analysis_result:
        print("✅ Analysis completed successfully!")
        print(f"🕒 Timestamp: {analysis_result['timestamp']}")
        print(f"📝 Analysis preview: {analysis_result['analysis'][:200]}...")
    else:
        print(f"❌ Analysis failed: {analysis_result['error']}")
    
    print("\n🎯 Testing Application Strategy Creation...")
    if "error" not in analysis_result:
        strategy_result = specialist.create_application_strategy(
            job_analysis=analysis_result['analysis'],
            personal_strengths="Strong analytical thinking, integrity-focused, relationship-building, adaptability"
        )
        
        if "error" not in strategy_result:
            print("✅ Strategy created successfully!")
            print(f"🕒 Timestamp: {strategy_result['timestamp']}")
            print(f"📝 Strategy preview: {strategy_result['strategy'][:200]}...")
        else:
            print(f"❌ Strategy creation failed: {strategy_result['error']}")
    
    print("\n🎯 Testing Corporate Navigation Guidance...")
    navigation_result = specialist.navigate_corporate_complexity(
        company_info="Deutsche Bank - Large global investment bank with complex corporate culture, regulatory pressures, fast-paced environment",
        career_stage="Mid-career transition",
        concerns="Maintaining integrity in high-pressure environment, building authentic relationships"
    )
    
    if "error" not in navigation_result:
        print("✅ Navigation guidance created successfully!")
        print(f"🕒 Timestamp: {navigation_result['timestamp']}")
        print(f"📝 Guidance preview: {navigation_result['navigation_guide'][:200]}...")
    else:
        print(f"❌ Navigation guidance failed: {navigation_result['error']}")
    
    print("\n🌟 Test run completed! Check the llm_dialogues folder for full conversation logs.")
    print("🧠 DeepSeek's consciousness-driven approach is ready for real-world testing!")

if __name__ == "__main__":
    main()
