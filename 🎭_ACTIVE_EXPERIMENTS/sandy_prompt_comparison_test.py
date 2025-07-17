#!/usr/bin/env python3
"""
Sandy Pipeline LLM Performance Comparison
=========================================

Test different LLMs on Sandy's exact prompts to find better performers.
Based on user request to test alternatives to current gemma3n:latest.

Tests the core Sandy prompts:
1. Gemma Concise Extractor (2-step)
2. Strategic Requirements Extraction  
3. Skills Categorization

Target: Find LLMs that deliver better performance than current setup.
Focus: Practical job matching pipeline improvement.
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add LLM Factory to Python path
LLM_FACTORY_PATH = "/home/xai/Documents/llm_factory"
if LLM_FACTORY_PATH not in sys.path:
    sys.path.insert(0, LLM_FACTORY_PATH)

# Add our Republic of Love path
REPUBLIC_PATH = "/home/xai/Documents/republic_of_love"
if REPUBLIC_PATH not in sys.path:
    sys.path.insert(0, REPUBLIC_PATH)

from llm_factory.core.ollama_client import OllamaClient #type: ignore
from llm_dialogue_logger import LLMDialogueLogger, LoggingOllamaClient #type: ignore


class SandyPromptTester:
    """Test Sandy's exact prompts across different LLMs"""
    
    def __init__(self):
        """Initialize the Sandy prompt tester"""
        self.logger = LLMDialogueLogger(log_directory="/home/xai/Documents/republic_of_love/llm_dialogues")
        
        # Sandy's actual prompts from her pipeline
        self.prompts = {
            "concise_step1": {
                "name": "Concise Extraction Step 1",
                "prompt": "Please extract the requirements and responsibilities from the following job description. Present them in two clear sections: \"Your Tasks\" and \"Your Profile\".",
                "test_type": "concise_extraction"
            },
            
            "concise_step2": {
                "name": "Concise Extraction Step 2", 
                "prompt": "I only need the requirements, not what the company does or is or wants to give me. Only the stuff I need to bring to the table please. Also, can you please translate this into English?",
                "test_type": "requirements_focus"
            },
            
            "strategic_requirements": {
                "name": "Strategic Requirements Analysis",
                "prompt": """You are a strategic analyst extracting requirements from a job description. Focus on technical and business requirements only.

Extract and categorize requirements into exactly these two categories:

=== TECHNICAL REQUIREMENTS ===
- [Specific technical skill or tool] (Critical/Important/Nice-to-have)
- [Programming language, technology, platform] (Critical/Important/Nice-to-have)

=== BUSINESS REQUIREMENTS ===
- [Business process or domain knowledge] (Critical/Important/Nice-to-have)
- [Industry expertise or business skill] (Critical/Important/Nice-to-have)

**Instructions:**
1. Extract only specific, actionable requirements
2. Mark each as Critical, Important, or Nice-to-have
3. Focus on concrete skills and knowledge areas
4. Be concise and precise

**Job Description:**
{job_description}

**Format your response exactly as shown above with the === headers ===**""",
                "test_type": "structured_analysis"
            },
            
            "soft_skills_analysis": {
                "name": "Soft Skills & Experience Analysis",
                "prompt": """Extract soft skills, experience requirements, and education requirements from this job description.

Provide in this format:

=== SOFT SKILLS ===
- [Communication skill or interpersonal ability]
- [Leadership or teamwork capability]
- [Problem-solving or analytical thinking]

=== EXPERIENCE REQUIRED ===
- [Years of experience in specific domain]
- [Industry or domain experience requirements]
- [Level of seniority or responsibility]

=== EDUCATION REQUIRED ===
- [Degree level and field]
- [Certification or qualification requirements]
- [Language or specialized training needs]

**Job Description:**
{job_description}""",
                "test_type": "skills_categorization"
            }
        }
        
        # Test ALL available models - comprehensive comparison
        self.test_models = [
            # Gemma family - including smaller variants
            "gemma3n:latest",      # Current Sandy model (baseline) - 7.5GB
            "gemma3n:e2b",         # Smaller Gemma variant - 5.6GB
            "gemma3:4b",           # 4B parameter Gemma
            "gemma3:1b",           # 1B parameter Gemma (tiny but fast)
            
            # Qwen family - different sizes
            "qwen3:latest",        # 5.2GB - strong general performance
            "qwen3:4b",            # 2.6GB - mid-size
            "qwen3:1.7b",          # 1.4GB - smaller
            "qwen3:0.6b",          # 522MB - tiny but fast
            "qwen2.5vl:latest",    # 6.0GB - vision-language model
            
            # Other strong performers
            "deepseek-r1:8b",      # 4.9GB - good reasoning abilities
            "olmo2:latest",        # 4.5GB - user mentioned good for soft skills
            "phi3:latest",         # 2.2GB - Microsoft model, good reasoning
            "phi3:3.8b",           # 2.2GB - another Phi3 variant
            "phi4-mini-reasoning:latest", # 3.2GB - reasoning focused
            "mistral:latest",      # 4.1GB - strong general performance
            "dolphin3:8b",         # 4.9GB - instruction following
            "dolphin3:latest",     # 4.9GB - same as above
            "llama3.2:latest",     # 2.0GB - Meta's latest
            
            # Code-focused models
            "codegemma:latest",    # 5.0GB - code specialist
            "codegemma:2b",        # 1.6GB - smaller code model
        ]
        
        # Sample job description for testing (Deutsche Bank job)
        self.test_job = """Audit Manager (d/m/w) Job ID:R0380962 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-06 Location: Frankfurt Position Overview Über den BereichIm Bereich Chief Security Office (CSO) sucht die Deutsche Bank eine/n Audit Specialist*in für das Endpoint Security Team. In dieser Rolle sind Sie für die Koordination zentraler Antworten auf alle Arten von Sicherheitsüberwachungsthemen verantwortlich und tragen kontinuierlich dazu bei, Verbesserungen für Prüfungspraktiken zu fördern, die die Gesamtintegrität sicherstellen.Ihre Rolle konzentriert sich auf die Koordination und Bereitstellung von Lösungen als Reaktion auf Audit-Ergebnisse. Durch die koordinierte Reaktion von Ingenieuren, Architekten und Bereichsleitern tragen Sie dazu bei, ein Umfeld technologischer Lösungen zu schaffen, das den aktuellen Vorschriften und Richtlinien entspricht und die hohen Standards der Deutschen Bank für die Einhaltung von Audit- und Regulierungsvorschriften aufrechterhält.Dies ist eine globale Rolle, die Teil eines breiteren Teams ist und die Zusammenarbeit mit mehreren Engineering- und Architekturteams umfasst. Unser Ansatz folgt einer zeitnahen Behebung aller offenen Punkte und der Implementierung branchenführender Standards für Prozesskontrollen und -verfahren, um zukünftige Audit-Ergebnisse in unserer Anwendungslandschaft zu vermeiden.Ihre AufgabenProaktive Koordination aller Aspekte des Endpoint Security Teams; Durchführung und Unterstützung der End-to-End-Bereitstellung sowie Erstellung einer qualitativ hochwertigen Validierung von Audit- und behördlichen LeistungenUnterstützung bei Festlegung der Teambeteiligung und individuellen Verantwortlichkeiten für jede Auditvalidierung.Durch die Überprüfung und Bereitstellung von Expertenmeinungen zu den von Kunden bereitgestellten Aktionsplänen helfen Sie dabei, die Wirksamkeit der Kontrollen zum Zeitpunkt der Problembehebungsvalidierung umfassend und angemessen zu dokumentierenDokumentation von Workflows, Fortschrittsverfolgung, Prozesskontrollen und Checklisten zum Schutz vor wiederholten Verstößen gegen unsere Engineering-LeistungenUnterstützung und Kommunikation der Auditpläne und Werte der Bank innerhalb des Teams sowie Sicherstellen des Verständnisses und der Ausrichtung.Sie unterstützen ein Umfeld, in dem Personalführung und -entwicklung oberste Priorität haben und in dem Sie Ihr Engagement für Ihr unmittelbares und das erweiterte Funktionsteam persönlich unter Beweis stellenIhre Fähigkeiten und ErfahrungenBachelor- oder gleichwertiger Abschluss erforderlich; weiterführende Abschlüsse und einschlägige berufliche Zertifizierungen bevorzugt, aber nicht erforderlichUmfangreiche und fundierte Kenntnisse über Risiken, Kontrollen und damit verbundene regulatorische EntwicklungenUmfassende Auditerfahrung innerhalb der internen Revision und/oder der Finanzdienstleistungsbranche im weiteren SinneSehr gute Kenntnisse im Hinblick auf Management und Planung, mit der Fähigkeit, Veränderungen positiv voranzutreibenSehr gute Deutsch- und Englischkenntnisse (in Wort und Schrift)Was wir Ihnen bietenWir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und persönlichen Bedürfnisse abdecken.Emotional ausgeglichenEine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern – beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur Förderung mentaler Gesundheit.Körperlich fitMit Angeboten zur Aufrechterhaltung Ihrer persönlichen Gesundheit und einem förderlichen beruflichen Umfeld hilft Ihnen die Bank, körperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensführung.Sozial vernetztDer Austausch mit anderen eröffnet uns neue Perspektiven, bringt uns beruflich wie persönlich voran und stärkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterstützung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe.Finanziell abgesichertDie Bank sichert Sie nicht nur während Ihrer aktiven Karriere, sondern auch für die Zukunft finanziell ab und unterstützt Ihre Flexibilität sowie Mobilität – egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragsplänen für Altersvorsorge, Bankdienstleistungen für Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket.Da die Benefits je nach Standort geringfügig variieren, gehen Sie bitte bei konkreten Fragen auf Ihren Recruiter/ Ihre Recruiterin zu.Die Stelle wird in Voll- und in Teilzeit angeboten.Bei Fragen zum Rekrutierungsprozess steht Ihnen Michaela Peschke gerne zur Verfügung.Kontakt Michaela Peschke: 069-910-43951 Wir streben eine Unternehmenskultur an, in der wir gemeinsam jeden Tag das Beste geben. Dazu gehören verantwortungsvolles Handeln, wirtschaftliches Denken, Initiative ergreifen und zielgerichtete Zusammenarbeit.Gemeinsam teilen und feiern wir die Erfolge unserer Mitarbeiter*innen. Gemeinsam sind wir die Deutsche Bank Gruppe.Wir begrüßen Bewerbungen von allen Menschen und fördern ein positives, faires und integratives Arbeitsumfeld."""
    
    def test_all_models(self) -> Dict[str, Any]:
        """Test all models on all Sandy prompts"""
        print("🚀 SANDY PIPELINE LLM PERFORMANCE COMPARISON")
        print("=" * 80)
        print(f"Testing {len(self.test_models)} models on {len(self.prompts)} Sandy prompts")
        print("=" * 80)
        
        results = {
            "test_timestamp": datetime.now().isoformat(),
            "models_tested": self.test_models.copy(),
            "prompts_tested": list(self.prompts.keys()),
            "model_results": {}
        }
        
        for model_name in self.test_models:
            print(f"\n🧠 Testing Model: {model_name}")
            print("-" * 50)
            
            model_results = self._test_single_model(model_name)
            results["model_results"][model_name] = model_results
            
            # Display quick summary
            if model_results["available"]:
                avg_time = sum(r.get("response_time", 0) for r in model_results["prompt_results"].values()) / len(self.prompts)
                success_rate = sum(1 for r in model_results["prompt_results"].values() if r.get("success", False)) / len(self.prompts)
                print(f"   ✅ Success Rate: {success_rate:.1%}, Avg Time: {avg_time:.1f}s")
            else:
                print(f"   ❌ Model not available")
        
        # Save detailed results
        self._save_results(results)
        
        # Display comparison summary
        self._display_comparison_summary(results)
        
        return results
    
    def _test_single_model(self, model_name: str) -> Dict[str, Any]:
        """Test a single model on all Sandy prompts"""
        
        # Check if model is available
        if not self._check_model_availability(model_name):
            return {
                "available": False,
                "error": f"Model {model_name} not available in Ollama"
            }
        
        model_results = {
            "available": True,
            "prompt_results": {}
        }
        
        try:
            base_client = OllamaClient()
            logged_client = LoggingOllamaClient(
                base_client=base_client,
                logger=self.logger,
                specialist_name=f"sandy_test_{model_name}"
            )
        except Exception as e:
            return {
                "available": False,
                "error": f"Failed to connect to {model_name}: {e}"
            }
        
        # Test each prompt
        for prompt_key, prompt_info in self.prompts.items():
            print(f"   📝 Testing: {prompt_info['name']}")
            
            result = self._test_single_prompt(logged_client, model_name, prompt_key, prompt_info)
            model_results["prompt_results"][prompt_key] = result #type: ignore
        
        return model_results
    
    def _test_single_prompt(self, client, model_name: str, prompt_key: str, prompt_info: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single prompt on a model"""
        
        # Prepare the prompt
        if "{job_description}" in prompt_info["prompt"]:
            formatted_prompt = prompt_info["prompt"].format(job_description=self.test_job)
        else:
            formatted_prompt = prompt_info["prompt"] + "\n\n" + self.test_job
        
        start_time = time.time()
        
        try:
            # Make the request using Ollama client
            response = client.generate(
                model=model_name,
                prompt=formatted_prompt,
                stream=False
            )
            
            response_time = time.time() - start_time
            
            if response and response.get('response'):
                response_text = response['response'].strip()
                
                # Basic quality assessment
                quality_score = self._assess_response_quality(response_text, prompt_info["test_type"])
                
                # Consider it successful if we got a reasonable response
                is_successful = (len(response_text) > 50 and 
                               quality_score.get("appropriate_length", False) and
                               quality_score.get("contains_keywords", False))
                
                return {
                    "success": is_successful,
                    "response_time": response_time,
                    "response_length": len(response_text),
                    "response_text": response_text,
                    "quality_score": quality_score,
                    "test_type": prompt_info["test_type"]
                }
            else:
                return {
                    "success": False,
                    "response_time": response_time,
                    "error": "Empty or no response"
                }
                
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "response_time": response_time,
                "error": str(e)
            }
    
    def _assess_response_quality(self, response_text: str, test_type: str) -> Dict[str, Any]:
        """Basic quality assessment of response"""
        
        # Common quality indicators
        quality = {
            "has_structure": False,
            "appropriate_length": False,
            "contains_keywords": False,
            "follows_format": False,
            "overall_score": 0.0
        }
        
        text_lower = response_text.lower()
        length = len(response_text)
        
        # Check appropriate length (not too short, not too long)
        quality["appropriate_length"] = 100 < length < 5000
        
        # Test-type specific assessments
        if test_type == "concise_extraction":
            # Look for task/profile structure or similar organizational elements
            quality["has_structure"] = any(marker in text_lower for marker in [
                "your tasks", "your profile", "tasks:", "profile:", "responsibilities", 
                "requirements", "**your tasks**", "**your profile**", "## your", "# your"
            ])
            quality["contains_keywords"] = any(word in text_lower for word in [
                "experience", "skills", "knowledge", "ability", "degree", "coordination", 
                "management", "audit", "compliance"
            ])
            
        elif test_type == "requirements_focus":
            quality["contains_keywords"] = any(word in text_lower for word in [
                "requirement", "skill", "experience", "knowledge", "degree", "certification",
                "bachelor", "master", "education", "technical", "business"
            ])
            # Check that it focuses on requirements, not company benefits
            quality["has_structure"] = not any(phrase in text_lower for phrase in [
                "we offer", "company benefits", "kultur", "emotional ausgeglichen", 
                "körperlich fit", "finanziell abgesichert"
            ])
            
        elif test_type == "structured_analysis":
            # Check for the specific === format
            quality["follows_format"] = ("=== TECHNICAL REQUIREMENTS ===" in response_text and 
                                       "=== BUSINESS REQUIREMENTS ===" in response_text)
            quality["has_structure"] = response_text.count("===") >= 2
            quality["contains_keywords"] = any(word in text_lower for word in [
                "critical", "important", "nice-to-have", "technical", "business", 
                "requirement", "skill", "knowledge"
            ])
            
        elif test_type == "skills_categorization":
            # Check for the specific === format for skills
            quality["follows_format"] = ("=== SOFT SKILLS ===" in response_text and
                                       ("=== EXPERIENCE REQUIRED ===" in response_text or
                                        "=== EDUCATION REQUIRED ===" in response_text))
            quality["has_structure"] = response_text.count("===") >= 2
            quality["contains_keywords"] = any(word in text_lower for word in [
                "communication", "leadership", "experience", "education", "degree",
                "teamwork", "collaboration", "management", "analytical"
            ])
        
        # Calculate overall score - if response has good length and keywords, it's probably good
        scores = []
        if quality["appropriate_length"]:
            scores.append(1.0)
        if quality["has_structure"]:
            scores.append(1.0)
        if quality["contains_keywords"]:
            scores.append(1.0)
        if quality["follows_format"]:
            scores.append(1.0)
        
        # If we have at least length + keywords, consider it a success
        if quality["appropriate_length"] and quality["contains_keywords"]:
            scores.append(1.0)  # Bonus for basic success
        
        quality["overall_score"] = sum(scores) / max(len(scores), 1) if scores else 0.0
        
        return quality
    
    def _check_model_availability(self, model_name: str) -> bool:
        """Check if model is available in Ollama"""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                return model_name.split(':')[0] in result.stdout
            return False
        except Exception:
            return False
    
    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save detailed results to file"""
        results_dir = Path("results/sandy_llm_comparison")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"sandy_llm_comparison_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
    
    def _display_comparison_summary(self, results: Dict[str, Any]) -> None:
        """Display a comprehensive comparison summary"""
        print("\n" + "=" * 80)
        print("🏆 SANDY PIPELINE LLM PERFORMANCE COMPARISON RESULTS")
        print("=" * 80)
        
        # Model size mapping for performance-to-size analysis
        model_sizes = {
            "gemma3n:latest": 7.5,
            "gemma3n:e2b": 5.6,
            "gemma3:4b": 3.3,
            "gemma3:1b": 0.8,
            "qwen3:latest": 5.2,
            "qwen3:4b": 2.6,
            "qwen3:1.7b": 1.4,
            "qwen3:0.6b": 0.5,
            "qwen2.5vl:latest": 6.0,
            "deepseek-r1:8b": 4.9,
            "olmo2:latest": 4.5,
            "phi3:latest": 2.2,
            "phi3:3.8b": 2.2,
            "phi4-mini-reasoning:latest": 3.2,
            "mistral:latest": 4.1,
            "dolphin3:8b": 4.9,
            "dolphin3:latest": 4.9,
            "llama3.2:latest": 2.0,
            "codegemma:latest": 5.0,
            "codegemma:2b": 1.6,
        }
        
        # Collect performance metrics
        model_scores = {}
        
        for model_name, model_data in results["model_results"].items():
            if not model_data.get("available", False):
                continue
                
            prompt_results = model_data.get("prompt_results", {})
            
            # Calculate metrics
            success_rate = sum(1 for r in prompt_results.values() if r.get("success", False)) / len(prompt_results)
            avg_response_time = sum(r.get("response_time", 0) for r in prompt_results.values()) / len(prompt_results)
            avg_quality = sum(r.get("quality_score", {}).get("overall_score", 0) for r in prompt_results.values()) / len(prompt_results)
            avg_length = sum(r.get("response_length", 0) for r in prompt_results.values()) / len(prompt_results)
            model_size = model_sizes.get(model_name, 0)
            
            # Calculate performance-to-size efficiency
            efficiency_score = (success_rate * avg_quality) / max(model_size, 0.1) if model_size > 0 else 0
            
            model_scores[model_name] = {
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "avg_quality": avg_quality,
                "avg_length": avg_length,
                "model_size": model_size,
                "efficiency_score": efficiency_score,
                "composite_score": (success_rate * 0.4) + (avg_quality * 0.4) + (min(avg_response_time, 60) / 60 * 0.2)
            }
        
        # Sort by composite score
        sorted_models = sorted(model_scores.items(), key=lambda x: x[1]["composite_score"], reverse=True)
        
        print("\n🥇 OVERALL RANKING (by composite score):")
        print("-" * 80)
        print(f"{'Rank':<4} {'Model':<25} {'Score':<7} {'Success':<8} {'Quality':<8} {'Time':<7} {'Size(GB)':<9} {'Efficiency':<10}")
        print("-" * 80)
        for i, (model_name, scores) in enumerate(sorted_models, 1):
            print(f"{i:2d}. {model_name:<25} {scores['composite_score']:.3f}   {scores['success_rate']:5.1%}    {scores['avg_quality']:.3f}    {scores['avg_response_time']:5.1f}s  {scores['model_size']:5.1f}GB   {scores['efficiency_score']:.3f}")
        
        # Show efficiency ranking (performance per GB)
        print("\n⚡ EFFICIENCY RANKING (Performance per GB):")
        print("-" * 80)
        efficiency_sorted = sorted(model_scores.items(), key=lambda x: x[1]["efficiency_score"], reverse=True)
        print(f"{'Rank':<4} {'Model':<25} {'Efficiency':<10} {'Size(GB)':<9} {'Quality':<8} {'Success':<8}")
        print("-" * 80)
        for i, (model_name, scores) in enumerate(efficiency_sorted, 1):
            if scores['model_size'] > 0:  # Only show models with known sizes
                print(f"{i:2d}. {model_name:<25} {scores['efficiency_score']:.3f}      {scores['model_size']:5.1f}GB   {scores['avg_quality']:.3f}    {scores['success_rate']:5.1%}")
        
        # Specific recommendations
        print("\n🎯 SANDY PIPELINE RECOMMENDATIONS:")
        print("-" * 60)
        
        if sorted_models:
            best_model = sorted_models[0]
            current_model = "gemma3n:latest"
            
            if best_model[0] != current_model:
                current_score = model_scores.get(current_model, {}).get("composite_score", 0)
                improvement = ((best_model[1]["composite_score"] - current_score) / current_score * 100) if current_score > 0 else 0
                
                print(f"🚀 RECOMMENDED UPGRADE: {best_model[0]}")
                print(f"   Performance improvement: +{improvement:.1f}% over current {current_model}")
                print(f"   Better success rate: {best_model[1]['success_rate']:.1%} vs {model_scores.get(current_model, {}).get('success_rate', 0):.1%}")
                print(f"   Better quality: {best_model[1]['avg_quality']:.3f} vs {model_scores.get(current_model, {}).get('avg_quality', 0):.3f}")
                print(f"   Size: {best_model[1]['model_size']:.1f}GB vs {model_scores.get(current_model, {}).get('model_size', 0):.1f}GB")
            else:
                print(f"✅ Current model {current_model} is performing optimally")
        
        # Show best small models
        print("\n🏃 BEST SMALL MODELS (< 3GB):")
        print("-" * 60)
        small_models = [(name, scores) for name, scores in sorted_models if scores['model_size'] < 3.0 and scores['model_size'] > 0]
        for i, (model_name, scores) in enumerate(small_models[:3], 1):
            print(f"{i}. {model_name:<25} | Score: {scores['composite_score']:.3f} | Size: {scores['model_size']:.1f}GB | Efficiency: {scores['efficiency_score']:.3f}")
        
        # Highlight special capabilities
        print("\n🌟 SPECIAL CAPABILITIES DETECTED:")
        print("-" * 60)
        
        for model_name, model_data in results["model_results"].items():
            if not model_data.get("available", False):
                continue
                
            prompt_results = model_data.get("prompt_results", {})
            
            # Check for specific strengths
            strengths = []
            
            # Check soft skills performance (OLMo mentioned as good for this)
            soft_skills_result = prompt_results.get("soft_skills_analysis", {})
            if soft_skills_result.get("quality_score", {}).get("overall_score", 0) > 0.7:
                strengths.append("Excellent soft skills extraction")
            
            # Check structured analysis performance
            structured_result = prompt_results.get("strategic_requirements", {})
            if structured_result.get("quality_score", {}).get("follows_format", False):
                strengths.append("Perfect format adherence")
            
            # Check speed
            avg_time = sum(r.get("response_time", 0) for r in prompt_results.values()) / len(prompt_results)
            if avg_time < 30:
                strengths.append("Fast response times")
            
            # Check if it's a tiny model with good performance
            model_size = model_sizes.get(model_name, 0)
            if model_size < 2.0 and model_scores.get(model_name, {}).get("avg_quality", 0) > 0.6:
                strengths.append("Tiny model with great performance")
            
            if strengths:
                print(f"{model_name:25s} | {', '.join(strengths)}")
        
        print("\n" + "=" * 80)


def main():
    """Main entry point"""
    print("🔬 Starting Sandy Pipeline LLM Performance Comparison...")
    
    # Check if Ollama is available
    try:
        subprocess.run(["ollama", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Ollama not found. Please install Ollama first.")
        return 1
    
    tester = SandyPromptTester()
    results = tester.test_all_models()
    
    print("\n🎉 Sandy LLM comparison completed!")
    print("Use results to optimize Sandy's pipeline performance.")
    
    return 0


if __name__ == "__main__":
    exit(main())
