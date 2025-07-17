# Content Extraction Specialist v3.1 Enhanced: Documentation

## Overview
This document describes the Four-Specialist Pipeline for skill extraction, achieving >90% accuracy for Deutsche Bank. It covers architecture, prompt engineering, model selection, validation, and research insights.

## Architecture
- Modular pipeline: Technical, Business, Business Process, and Soft Skill specialists
- Each specialist uses tailored prompts and model selection (empirically validated)
- Aggregation logic ensures no skill type is lost

## Prompt Design
- Each specialist prompt is optimized for its skill domain
- Iterative refinement and LLM self-reflection used for maximum accuracy
- Template-based output (no JSON)

## Model Selection
- OLMO2: Soft skills
- Mistral: Business, Business Process
- Dolphin3, Qwen3: Technical
- Model×technique matrix used for empirical selection

## Validation Results
- Golden test suite accuracy: 91.3%
- 100% on main test case
- All outputs validated for template compliance

## Research & Experimentation
- See STUDIES_IN_CONSCIOUSNESS.md for full journal
- All solution attempts, failures, and breakthroughs documented

## Usage
- See zero_dependency_demo.py for usage example
- No external dependencies required

## Contact
- For questions, contact terminator@llm_factory
