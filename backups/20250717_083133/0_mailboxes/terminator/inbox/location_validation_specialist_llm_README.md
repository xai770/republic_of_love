# Location Validation Specialist LLM Delivery

## Overview
This delivery contains the production-ready Location Validation Specialist for Sandy's Daily Report Pipeline, fully compliant with `republic_of_love_rules.md`.

- **LLM-powered specialist**: All logic is performed by an LLM (Ollama, llama3.2:latest), never hardcoded.
- **Template-based output**: The LLM is strictly instructed to output only a single template block, never JSON or extra text.
- **Zero-dependency test script**: `test_hallucination_detection.py` runs advanced edge-case tests and requires only Python and Ollama.
- **Edge-case robustness**: Handles city/country/borough ambiguity, context bleeding, and "same city, different country" cases.

## Files Delivered
- `location_validation_specialist_llm.py` (specialist implementation)
- `test_hallucination_detection.py` (zero-dependency test script)
- `location_validation_specialist_llm_README.md` (this documentation)

## How it Works
- The specialist receives a metadata location and a job description.
- It uses a strict, anti-hallucination prompt to the LLM, enforcing:
  - Only the template is output, once, with no extra text.
  - Boroughs (e.g., Manhattan) are treated as part of the city (e.g., New York).
  - "Same city, different country" is always flagged as a conflict.
  - Only the main work location is considered authoritative.
- The test script runs 6 advanced edge cases, all of which now pass.

## Usage
1. Start Ollama with the llama3.2:latest model.
2. Run `python test_hallucination_detection.py`.
3. All tests should pass with no hallucinations.

## Compliance
- All logic is LLM-based (Rule 1)
- Output is template-based, not JSON (Rule 2)
- Zero-dependency test script included (Rule 3)
- This README and test script are delivered to terminator@llm_factory (Rule 4)

---
For questions, contact Sandy or the LLM Factory team.
