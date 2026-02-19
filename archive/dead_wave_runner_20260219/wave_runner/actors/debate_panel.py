#!/usr/bin/env python3
"""
WF3006 Debate Panel - Challenger, Defender, Judge

Implements the 3-model debate system for low-confidence classifications:
- Challenger (qwen2.5:7b): Finds flaws in initial classification
- Defender (gemma3:4b): Defends with additional evidence
- Judge (gemma3:4b): Makes final ruling

Author: Arden
Date: December 15, 2025
"""

import json
import subprocess
from typing import Optional

# Model assignments
CHALLENGER_MODEL = "qwen2.5:7b"
DEFENDER_MODEL = "gemma3:4b"
JUDGE_MODEL = "gemma3:4b"

# Timeout
LLM_TIMEOUT = 300  # 5 minutes


def call_llm(prompt: str, model: str) -> dict:
    """Call Ollama LLM."""
    try:
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=LLM_TIMEOUT
        )
        
        if result.returncode != 0:
            return {"error": result.stderr, "success": False}
        
        return {"response": result.stdout.strip(), "success": True}
        
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def challenge_classification(
    skill_name: str,
    skill_description: str,
    initial_domain: str,
    initial_reasoning: str,
    initial_confidence: float,
    available_domains: list[dict]
) -> dict:
    """
    Challenger model questions the initial classification.
    Returns alternative domain suggestions if any.
    """
    domains_text = "\n".join([
        f"  - {d['name']}: {d.get('description', '')}" 
        for d in available_domains
    ])
    
    prompt = f"""You are a skeptical classification reviewer. Your job is to find flaws in skill classifications.

## SKILL
**Name:** {skill_name}
**Description:** {skill_description or 'No description'}

## INITIAL CLASSIFICATION
**Domain:** {initial_domain}
**Confidence:** {initial_confidence}
**Reasoning:** {initial_reasoning}

## AVAILABLE DOMAINS
{domains_text}

## YOUR TASK
Challenge this classification. Look for:
1. Better-fitting domains that were overlooked
2. Ambiguities in the skill that could lead to different classifications
3. Weaknesses in the reasoning

Respond with JSON ONLY:
```json
{{
  "has_challenge": true/false,
  "alternative_domain": "domain_name or null",
  "challenge_reasoning": "Your argument against the initial classification",
  "strength": 0.0-1.0 (how strong is your challenge)
}}
```

If the classification is clearly correct, set has_challenge: false."""

    result = call_llm(prompt, CHALLENGER_MODEL)
    
    if not result.get("success"):
        return {"error": result.get("error")}
    
    # Parse response
    response_text = result.get("response", "")
    try:
        # Find JSON in response
        import re
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    return {"raw_response": response_text, "parse_error": True}


def defend_classification(
    skill_name: str,
    skill_description: str,
    initial_domain: str,
    initial_reasoning: str,
    challenge: dict,
    similar_skills: list[dict]
) -> dict:
    """
    Defender model responds to the challenge with additional evidence.
    """
    similar_text = "\n".join([
        f"  - {s['name']} → {s['domain']}" 
        for s in similar_skills
    ]) if similar_skills else "  (no similar skills found)"
    
    prompt = f"""You are defending a skill classification against a challenge.

## SKILL
**Name:** {skill_name}
**Description:** {skill_description or 'No description'}

## INITIAL CLASSIFICATION
**Domain:** {initial_domain}
**Reasoning:** {initial_reasoning}

## CHALLENGE
**Alternative proposed:** {challenge.get('alternative_domain', 'None')}
**Argument:** {challenge.get('challenge_reasoning', 'No argument provided')}

## SIMILAR SKILLS (evidence)
{similar_text}

## YOUR TASK
Defend the initial classification OR acknowledge the challenge is valid.

Respond with JSON ONLY:
```json
{{
  "defense": "Your defense of the initial classification",
  "acknowledges_challenge": true/false,
  "revised_confidence": 0.0-1.0,
  "recommendation": "original" or "alternative" or "needs_human"
}}
```"""

    result = call_llm(prompt, DEFENDER_MODEL)
    
    if not result.get("success"):
        return {"error": result.get("error")}
    
    response_text = result.get("response", "")
    try:
        import re
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    return {"raw_response": response_text, "parse_error": True}


def judge_debate(
    skill_name: str,
    skill_description: str,
    initial_domain: str,
    initial_confidence: float,
    initial_reasoning: str,
    challenge: dict,
    defense: dict
) -> dict:
    """
    Judge model makes final ruling based on debate.
    """
    prompt = f"""You are the final arbiter of a classification debate.

## SKILL
**Name:** {skill_name}
**Description:** {skill_description or 'No description'}

## ORIGINAL CLASSIFICATION
**Domain:** {initial_domain} (confidence: {initial_confidence})
**Reasoning:** {initial_reasoning}

## CHALLENGER'S ARGUMENT
**Alternative:** {challenge.get('alternative_domain', 'None')}
**Argument:** {challenge.get('challenge_reasoning', 'No argument')}
**Strength:** {challenge.get('strength', 'Unknown')}

## DEFENDER'S RESPONSE
**Defense:** {defense.get('defense', 'No defense')}
**Acknowledges challenge:** {defense.get('acknowledges_challenge', 'Unknown')}
**Recommendation:** {defense.get('recommendation', 'Unknown')}

## YOUR RULING
Make the final decision. Choose wisely.

Respond with JSON ONLY:
```json
{{
  "ruling": "original" or "alternative" or "needs_human",
  "final_domain": "the domain to use",
  "final_confidence": 0.0-1.0,
  "reasoning": "Explain your ruling",
  "overturn_original": true/false
}}
```"""

    result = call_llm(prompt, JUDGE_MODEL)
    
    if not result.get("success"):
        return {"error": result.get("error")}
    
    response_text = result.get("response", "")
    try:
        import re
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    return {"raw_response": response_text, "parse_error": True}


def run_debate(
    skill: dict,
    initial_classification: dict,
    available_domains: list[dict],
    similar_skills: list[dict] = None
) -> dict:
    """
    Run full debate pipeline for a skill classification.
    
    Args:
        skill: {'entity_id', 'name', 'description'}
        initial_classification: {'domain', 'confidence', 'reasoning'}
        available_domains: List of domain dicts
        similar_skills: Optional list of similar classified skills
        
    Returns:
        Final classification decision with debate history
    """
    skill_name = skill.get('name')
    skill_description = skill.get('description', '')
    initial_domain = initial_classification.get('domain')
    initial_confidence = initial_classification.get('confidence', 0.7)
    initial_reasoning = initial_classification.get('reasoning', '')
    
    debate_history = {
        "skill_id": skill.get('entity_id'),
        "skill_name": skill_name,
        "initial": initial_classification
    }
    
    # Step 1: Challenge
    print(f"  [Challenger] Reviewing {skill_name}...")
    challenge = challenge_classification(
        skill_name, skill_description,
        initial_domain, initial_reasoning, initial_confidence,
        available_domains
    )
    debate_history["challenge"] = challenge
    
    if challenge.get("error") or challenge.get("parse_error"):
        print(f"  [Challenger] ⚠ Failed to parse: {challenge}")
        debate_history["status"] = "challenge_failed"
        debate_history["final_domain"] = initial_domain
        debate_history["final_confidence"] = initial_confidence
        return debate_history
    
    # If no challenge, accept original
    if not challenge.get("has_challenge"):
        print(f"  [Challenger] ✓ No challenge - accepting {initial_domain}")
        debate_history["status"] = "no_challenge"
        debate_history["final_domain"] = initial_domain
        debate_history["final_confidence"] = initial_confidence
        return debate_history
    
    print(f"  [Challenger] ⚔ Challenged! Alternative: {challenge.get('alternative_domain')}")
    
    # Step 2: Defend
    print(f"  [Defender] Building defense...")
    defense = defend_classification(
        skill_name, skill_description,
        initial_domain, initial_reasoning,
        challenge, similar_skills or []
    )
    debate_history["defense"] = defense
    
    if defense.get("error") or defense.get("parse_error"):
        print(f"  [Defender] ⚠ Failed: {defense}")
        debate_history["status"] = "defense_failed"
        debate_history["final_domain"] = initial_domain
        debate_history["final_confidence"] = initial_confidence * 0.9
        return debate_history
    
    print(f"  [Defender] Recommendation: {defense.get('recommendation')}")
    
    # Step 3: Judge
    print(f"  [Judge] Making ruling...")
    ruling = judge_debate(
        skill_name, skill_description,
        initial_domain, initial_confidence, initial_reasoning,
        challenge, defense
    )
    debate_history["ruling"] = ruling
    
    if ruling.get("error") or ruling.get("parse_error"):
        print(f"  [Judge] ⚠ Failed: {ruling}")
        debate_history["status"] = "judge_failed"
        debate_history["final_domain"] = initial_domain
        debate_history["final_confidence"] = initial_confidence * 0.8
        return debate_history
    
    # Final result
    debate_history["status"] = "debated"
    debate_history["final_domain"] = ruling.get("final_domain", initial_domain)
    debate_history["final_confidence"] = ruling.get("final_confidence", initial_confidence)
    debate_history["overturned"] = ruling.get("overturn_original", False)
    
    if ruling.get("overturn_original"):
        print(f"  [Judge] ⚡ OVERTURNED → {ruling.get('final_domain')}")
    else:
        print(f"  [Judge] ✓ Upheld → {ruling.get('final_domain')}")
    
    return debate_history


# For testing
if __name__ == "__main__":
    # Test with a sample skill
    test_skill = {
        "entity_id": 9999,
        "name": "SOX Compliance Audit",
        "description": "Conducting audits for Sarbanes-Oxley compliance"
    }
    
    test_classification = {
        "domain": "data_and_analytics",
        "confidence": 0.65,
        "reasoning": "Auditing involves data analysis"
    }
    
    test_domains = [
        {"name": "technology", "description": "Software, hardware, infrastructure"},
        {"name": "data_and_analytics", "description": "Data science, BI, statistics"},
        {"name": "compliance_and_risk", "description": "Legal, audit, regulatory"},
        {"name": "business_operations", "description": "Operations, logistics"},
    ]
    
    print("=" * 60)
    print("WF3006 Debate Panel Test")
    print("=" * 60)
    
    result = run_debate(test_skill, test_classification, test_domains)
    
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2))
