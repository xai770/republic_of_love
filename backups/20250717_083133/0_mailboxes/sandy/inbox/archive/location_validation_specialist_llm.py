# See README for full documentation. This is the production-ready LLM-powered specialist.
# All logic is performed by the LLM (Ollama, llama3.2:latest) with strict template-based output.
# Place this file alongside the test script for zero-dependency validation.

import logging
import time
import re
import requests
from typing import Dict, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LocationValidationResult:
    metadata_location_accurate: bool
    authoritative_location: str
    conflict_detected: bool
    confidence_score: float
    analysis_details: Dict[str, Any]
    job_id: str
    processing_time: float

class LocationValidationSpecialistLLM:
    def __init__(self, model: str = "llama3.2:latest", ollama_url: str = "http://localhost:11434"):
        self.model = model
        self.ollama_url = ollama_url
        self.stats = {'jobs_processed': 0, 'conflicts_detected': 0, 'total_processing_time': 0}
        if self._verify_ollama_connection():
            logger.info(f"✅ Ollama connection verified. Using model: {self.model}")
        else:
            logger.warning("⚠️ Ollama connection failed. Check if Ollama is running.")

    def _verify_ollama_connection(self) -> bool:
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def validate_location(self, metadata_location: str, job_description: str, job_id: str = "unknown") -> LocationValidationResult:
        start_time = time.time()
        logger.info(f"🤖 Processing job {job_id} - Metadata location: {metadata_location}")
        try:
            llm_analysis = self._analyze_with_llm(metadata_location, job_description, job_id)
            analysis_results = self._parse_llm_response(llm_analysis)
            processing_time = time.time() - start_time
            self.stats['jobs_processed'] += 1
            self.stats['total_processing_time'] += processing_time
            if analysis_results['conflict_detected']:
                self.stats['conflicts_detected'] += 1
            logger.info(f"✅ Job {job_id} processed - Conflict: {analysis_results['conflict_detected']}, "
                       f"Confidence: {analysis_results['confidence_score']:.1f}%, Time: {processing_time:.3f}s")
            return LocationValidationResult(
                metadata_location_accurate=not analysis_results['conflict_detected'],
                authoritative_location=analysis_results['authoritative_location'],
                conflict_detected=analysis_results['conflict_detected'],
                confidence_score=analysis_results['confidence_score'],
                analysis_details={
                    'metadata_location': metadata_location,
                    'extracted_locations': analysis_results['extracted_locations'],
                    'conflict_type': analysis_results['conflict_type'],
                    'reasoning': analysis_results['reasoning'],
                    'risk_level': analysis_results['risk_level'],
                    'llm_model': self.model
                },
                job_id=job_id,
                processing_time=processing_time
            )
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Error processing job {job_id}: {str(e)}")
            return LocationValidationResult(
                metadata_location_accurate=True,
                authoritative_location=metadata_location,
                conflict_detected=False,
                confidence_score=0.0,
                analysis_details={
                    'error': str(e),
                    'metadata_location': metadata_location,
                    'extracted_locations': [],
                    'conflict_type': 'error',
                    'reasoning': f"Processing error: {str(e)}",
                    'risk_level': 'unknown',
                    'llm_model': self.model
                },
                job_id=job_id,
                processing_time=processing_time
            )

    def _analyze_with_llm(self, metadata_location: str, job_description: str, job_id: str) -> str:
        prompt = f"""
You are a location validation specialist. Your ONLY job is to check if the job description mentions a work location that is a different city than the metadata location.

STRICT OUTPUT INSTRUCTIONS (read carefully):
- Output ONLY the following template, ONCE. Do NOT explain, do NOT repeat, do NOT add extra text, do NOT add lists, do NOT add notes, do NOT add risk levels unless in the template. If you output anything except the template, you will be penalized.
- If the main work location in the job description matches the metadata location (even if other cities are mentioned for travel or collaboration), set CONFLICT_DETECTED: NO and AUTHORITATIVE_LOCATION to the metadata location.
- If the job description mentions a city that is not the metadata city as the main work location, set CONFLICT_DETECTED: YES and AUTHORITATIVE_LOCATION to the city or full location from the description.
- If the job description mentions only a country/region, or is ambiguous, set CONFLICT_DETECTED: NO and AUTHORITATIVE_LOCATION to the metadata location.
- IMPORTANT: If the job description mentions a city with the same name as the metadata city but in a different country or region (for example, metadata is "London" and description says "London, Ontario, Canada"), you MUST set CONFLICT_DETECTED: YES and AUTHORITATIVE_LOCATION to the full location from the description. This is a critical rule.
- If the job description mentions a borough or district (e.g., Manhattan) and the metadata city contains it (e.g., New York), treat as NO CONFLICT and AUTHORITATIVE_LOCATION as the city. Otherwise, treat as a conflict.
- AUTHORITATIVE_LOCATION must be a single city or full location, not a list. Do NOT output multiple locations as AUTHORITATIVE_LOCATION. Only one.
- If multiple locations are mentioned, select the one that is the main work location. If unclear, default to the metadata location unless a different city is clearly stated as the work location.
- If there is any ambiguity, or you are unsure, set CONFLICT_DETECTED: YES and AUTHORITATIVE_LOCATION to the most specific location from the description.
- Output the template below EXACTLY, with no extra text before or after. Do not add any explanations, markdown, or commentary.

TEMPLATE (fill in, do NOT add anything else):
CONFLICT_DETECTED: [YES or NO]
AUTHORITATIVE_LOCATION: [city or full location]
EXTRACTED_LOCATIONS: [comma-separated list of all locations found]
CONFIDENCE_SCORE: [0-100]
CONFLICT_TYPE: [critical if YES, none if NO]
REASONING: [one-line explanation]
RISK_LEVEL: [critical if YES, low if NO]

METADATA LOCATION: {metadata_location}
JOB DESCRIPTION: {job_description}
"""
        logger.info(f"🤖 Calling Ollama LLM for job {job_id}")
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "top_p": 0.9}
                },
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "")
                logger.info(f"✅ LLM analysis completed for job {job_id}")
                return llm_response
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ LLM analysis failed for job {job_id}: {str(e)}")
            raise

    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        logger.info(f"🔍 DEBUG - Raw LLM Response:")
        logger.info(f"'{llm_response}'")
        analysis = {'conflict_detected': False, 'authoritative_location': '', 'extracted_locations': [], 'confidence_score': 0.0, 'conflict_type': 'none', 'reasoning': '', 'risk_level': 'low'}
        try:
            conflict_match = re.search(r'CONFLICT_DETECTED:\s*(YES|NO)', llm_response, re.IGNORECASE)
            if conflict_match:
                analysis['conflict_detected'] = conflict_match.group(1).upper() == 'YES'
            auth_location_match = re.search(r'AUTHORITATIVE_LOCATION:\s*(.+?)(?:\n|$)', llm_response)
            if auth_location_match:
                analysis['authoritative_location'] = auth_location_match.group(1).strip()
            extracted_match = re.search(r'EXTRACTED_LOCATIONS:\s*(.+?)(?:\n|$)', llm_response)
            if extracted_match:
                locations_text = extracted_match.group(1).strip()
                analysis['extracted_locations'] = [loc.strip() for loc in locations_text.split(',') if loc.strip()]
            confidence_match = re.search(r'CONFIDENCE_SCORE:\s*(\d+)', llm_response)
            if confidence_match:
                analysis['confidence_score'] = float(confidence_match.group(1))
            conflict_type_match = re.search(r'CONFLICT_TYPE:\s*(.+?)(?:\n|$)', llm_response)
            if conflict_type_match:
                analysis['conflict_type'] = conflict_type_match.group(1).strip().lower()
            reasoning_match = re.search(r'REASONING:\s*(.+?)(?:\n|RISK_LEVEL:|$)', llm_response, re.DOTALL)
            if reasoning_match:
                analysis['reasoning'] = reasoning_match.group(1).strip()
            risk_match = re.search(r'RISK_LEVEL:\s*(.+?)(?:\n|$)', llm_response)
            if risk_match:
                analysis['risk_level'] = risk_match.group(1).strip().lower()
            logger.info(f"✅ Template parsing successful - Conflict: {analysis['conflict_detected']}, "
                       f"Confidence: {analysis['confidence_score']}")
            return analysis
        except Exception as e:
            logger.warning(f"⚠️ Template parsing failed, using defaults: {str(e)}")
            if any(keyword in llm_response.lower() for keyword in ['conflict', 'different', 'mismatch']):
                analysis['conflict_detected'] = True
                analysis['confidence_score'] = 50.0
                analysis['reasoning'] = "Fallback detection based on conflict keywords"
            return analysis
