# Feedback Loop: From "No Tax Jobs" to Preference

**Author:** Arden  
**Date:** 2025-11-30  
**Status:** Draft Proposal

---

## The Problem

User says: *"I'm not a tax person, stop showing me tax jobs"*

We need to:
1. Understand what they mean
2. Create a preference that persists
3. Apply it to future matching
4. Never store the raw text (privacy)

---

## Feedback Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FEEDBACK PROCESSING FLOW                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  USER                                                               │
│    │                                                                │
│    ▼                                                                │
│  "I'm not a tax person, no tax jobs for me"                        │
│    │                                                                │
│    ▼                                                                │
│  ┌─────────────────────────────────────────┐                       │
│  │ FEEDBACK INGESTION                       │                       │
│  │ (conversation: feedback_processor)       │                       │
│  │                                          │                       │
│  │ Input:                                   │                       │
│  │   - feedback_text                        │                       │
│  │   - posting_id (if about specific post)  │                       │
│  │   - user_id                              │                       │
│  └──────────────────┬──────────────────────┘                       │
│                     │                                               │
│                     ▼                                               │
│  ┌─────────────────────────────────────────┐                       │
│  │ LOCAL LLM (mistral:7b)                  │                       │
│  │                                          │                       │
│  │ Extract:                                 │                       │
│  │   - Intent (exclude/include/info)        │                       │
│  │   - Target (skill/company/industry/etc)  │                       │
│  │   - Strength (dealbreaker vs preference) │                       │
│  │   - Duration (permanent vs temporary)    │                       │
│  │                                          │                       │
│  │ Output: Structured preference JSON       │                       │
│  └──────────────────┬──────────────────────┘                       │
│                     │                                               │
│                     ▼                                               │
│  ┌─────────────────────────────────────────┐                       │
│  │ PREFERENCE GENERATOR                     │                       │
│  │                                          │                       │
│  │ Convert LLM output to:                   │                       │
│  │   - user_preferences record              │                       │
│  │   - user_feedback record (anonymized)    │                       │
│  └──────────────────┬──────────────────────┘                       │
│                     │                                               │
│                     ▼                                               │
│  ┌─────────────────────────────────────────┐                       │
│  │ DATABASE                                 │                       │
│  │                                          │                       │
│  │ user_preferences:                        │                       │
│  │   type: exclude_skill                    │                       │
│  │   key: skill_category                    │                       │
│  │   value: tax                             │                       │
│  │   weight: -1.0 (dealbreaker)             │                       │
│  │   source: feedback_inferred              │                       │
│  └─────────────────────────────────────────┘                       │
│                                                                     │
│  RAW TEXT "I'm not a tax person" → NEVER STORED                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## LLM Prompt for Feedback Processing

```python
FEEDBACK_PROCESSING_PROMPT = """
You are a preference extractor. Analyze user feedback and extract structured preferences.

INPUT: User feedback about job recommendations
OUTPUT: JSON with extracted preferences

EXTRACT:
1. intent: What do they want?
   - "exclude" = Don't show me these
   - "include" = I want more of these
   - "info" = Just providing context, no action needed
   - "clarify" = Asking a question, needs response

2. target_type: What are they talking about?
   - "skill" = A specific skill or skill category
   - "company" = A specific company
   - "industry" = An industry sector
   - "location" = A geographic preference
   - "salary" = Compensation requirements
   - "role_type" = Type of role (management, IC, etc.)
   - "work_style" = Remote, hybrid, office
   - "posting" = This specific posting only

3. target_value: The specific thing (normalized)
   - For skills: use our skill taxonomy terms
   - For industries: use standard industry names
   - For locations: use city names

4. strength: How strong is this preference?
   - 1.0 = Dealbreaker / Must have
   - 0.7 = Strong preference
   - 0.5 = Mild preference
   - 0.3 = Slight preference

5. duration: How long should this last?
   - "permanent" = Forever (until they change it)
   - "temporary" = Just for now (maybe they're exploring)
   - "one_time" = Just this one posting

6. confidence: How confident are you in this interpretation?
   - "high" = Clear intent
   - "medium" = Reasonably sure
   - "low" = Guessing, might want to confirm

EXAMPLES:

Input: "I'm not a tax person, no tax jobs for me"
Output: {
  "intent": "exclude",
  "target_type": "skill",
  "target_value": "tax",
  "strength": 1.0,
  "duration": "permanent",
  "confidence": "high",
  "reasoning": "User explicitly states they are not a tax professional"
}

Input: "I know this company, worked there before, didn't like it"
Output: {
  "intent": "exclude",
  "target_type": "company",
  "target_value": "[company from posting]",
  "strength": 0.8,
  "duration": "permanent",
  "confidence": "high",
  "reasoning": "Negative past experience with company"
}

Input: "Interesting but the salary seems low"
Output: {
  "intent": "info",
  "target_type": "salary",
  "target_value": "below_expectations",
  "strength": 0.5,
  "duration": "temporary",
  "confidence": "medium",
  "reasoning": "User notes salary concern but doesn't rule out"
}

Input: "Can you show me more fintech roles?"
Output: {
  "intent": "include",
  "target_type": "industry",
  "target_value": "fintech",
  "strength": 0.7,
  "duration": "permanent",
  "confidence": "high",
  "reasoning": "User explicitly requests more of this industry"
}

Input: "What does 'hybrid' mean for this role?"
Output: {
  "intent": "clarify",
  "target_type": "work_style",
  "target_value": "hybrid",
  "strength": 0.0,
  "duration": "one_time",
  "confidence": "high",
  "reasoning": "User asking for clarification, not stating preference"
}

---
FEEDBACK:
{feedback_text}

POSTING CONTEXT (if provided):
{posting_context}
---

Extracted preference JSON:
"""
```

---

## Preference Creation Logic

```python
class FeedbackProcessor:
    """
    Processes user feedback into preferences.
    Uses local LLM for understanding, never stores raw text.
    """
    
    def __init__(self, llm_client, db):
        self.llm = llm_client
        self.db = db
    
    def process_feedback(
        self, 
        user_id: int, 
        feedback_text: str, 
        posting_id: int = None
    ) -> dict:
        """
        Process user feedback, create preference if applicable.
        
        Returns: {
            "understood": bool,
            "action_taken": str,
            "preference_created": dict or None,
            "needs_clarification": bool,
            "clarification_question": str or None
        }
        """
        
        # 1. Get posting context if provided
        posting_context = ""
        if posting_id:
            posting = self.db.get_posting(posting_id)
            posting_context = f"""
            Job Title: {posting['job_title']}
            Company ID: {posting['company_id']}
            Industry: {posting.get('industry', 'unknown')}
            Location: {posting.get('location', 'unknown')}
            Skills: {', '.join(s['skill_name'] for s in posting.get('skills', []))}
            """
        
        # 2. Extract preference via LLM
        extracted = self.llm.extract_preference(
            feedback_text=feedback_text,
            posting_context=posting_context
        )
        
        # 3. Handle low confidence
        if extracted["confidence"] == "low":
            return {
                "understood": False,
                "action_taken": "none",
                "preference_created": None,
                "needs_clarification": True,
                "clarification_question": self._generate_clarification(extracted)
            }
        
        # 4. Handle info/clarify intents (no preference change)
        if extracted["intent"] in ["info", "clarify"]:
            # Store anonymized feedback for analytics, no preference created
            self._store_anonymized_feedback(user_id, extracted, posting_id)
            
            return {
                "understood": True,
                "action_taken": "noted",
                "preference_created": None,
                "needs_clarification": extracted["intent"] == "clarify",
                "clarification_question": self._answer_clarification(extracted) 
                    if extracted["intent"] == "clarify" else None
            }
        
        # 5. Create preference (include or exclude)
        preference = self._create_preference(user_id, extracted, posting_id)
        
        # 6. Store anonymized feedback
        self._store_anonymized_feedback(user_id, extracted, posting_id)
        
        return {
            "understood": True,
            "action_taken": "preference_created",
            "preference_created": preference,
            "needs_clarification": False,
            "clarification_question": None
        }
    
    def _create_preference(
        self, 
        user_id: int, 
        extracted: dict, 
        posting_id: int = None
    ) -> dict:
        """Create user_preferences record from extracted data."""
        
        # Map intent to weight sign
        weight_sign = -1.0 if extracted["intent"] == "exclude" else 1.0
        weight = weight_sign * extracted["strength"]
        
        # Map target_type to preference_type
        preference_type = f"{extracted['intent']}_{extracted['target_type']}"
        
        # Resolve target value
        target_value = extracted["target_value"]
        
        # Special handling for company from posting
        if target_value == "[company from posting]" and posting_id:
            posting = self.db.get_posting(posting_id)
            target_value = str(posting["company_id"])
        
        # Map to our skill taxonomy if skill type
        if extracted["target_type"] == "skill":
            skill_id = self.db.resolve_skill(target_value)
            if skill_id:
                target_value = str(skill_id)
        
        # Calculate expiration
        expires_at = None
        if extracted["duration"] == "temporary":
            expires_at = datetime.now() + timedelta(days=30)
        elif extracted["duration"] == "one_time":
            expires_at = datetime.now() + timedelta(days=7)
        
        # Insert preference
        preference = self.db.create_preference(
            user_id=user_id,
            preference_type=preference_type,
            preference_key=extracted["target_type"],
            preference_value=target_value,
            weight=weight,
            source="feedback_inferred",
            expires_at=expires_at
        )
        
        return preference
    
    def _store_anonymized_feedback(
        self, 
        user_id: int, 
        extracted: dict, 
        posting_id: int = None
    ):
        """Store anonymized feedback record (no raw text)."""
        
        self.db.create_feedback(
            user_id=user_id,
            posting_id=posting_id,
            feedback_type=extracted["intent"],
            feedback_structured={
                "target_type": extracted["target_type"],
                "target_value": extracted["target_value"],
                "strength": extracted["strength"],
                "confidence": extracted["confidence"]
                # NOTE: No reasoning field - might contain PII
            },
            processed=True
        )
    
    def _generate_clarification(self, extracted: dict) -> str:
        """Generate a clarification question for low-confidence extraction."""
        
        templates = {
            "skill": "Just to confirm - do you want me to exclude all {value} related jobs?",
            "company": "Should I exclude this company from your recommendations going forward?",
            "industry": "Would you like to see fewer {value} industry jobs, or none at all?",
            "location": "Should I remove {value} from your preferred locations?",
        }
        
        template = templates.get(extracted["target_type"], 
                                 "I want to make sure I understand - could you clarify?")
        
        return template.format(value=extracted["target_value"])
```

---

## Feedback Types & Resulting Preferences

| User Says | Extracted | Preference Created |
|-----------|-----------|-------------------|
| "No tax jobs" | exclude + skill + tax | `exclude_skill: tax, weight: -1.0` |
| "I hate this company" | exclude + company + [id] | `exclude_company: 47, weight: -0.9` |
| "More fintech please" | include + industry + fintech | `include_industry: fintech, weight: 0.7` |
| "Too far to commute" | exclude + location + [city] | `exclude_location: munich, weight: -0.7` |
| "Salary too low" | info + salary | No preference (noted) |
| "What does hybrid mean?" | clarify + work_style | No preference (answer question) |
| "Not interested" | exclude + posting | No preference (one-time skip) |
| "Already applied" | info + posting | No preference (noted) |

---

## Confirmation Flow (Optional)

For high-impact preferences (dealbreakers), we might want to confirm:

```
User: "I will never work for this company"
System: "Got it. I'll permanently exclude [Company Name] from your recommendations. 
        This is a dealbreaker - you won't see any jobs from them. 
        Is that correct? (You can change this anytime in preferences)"
User: "Yes"
System: [Creates preference with weight -1.0]
```

```python
def needs_confirmation(extracted: dict) -> bool:
    """Determine if we should confirm before creating preference."""
    
    # Dealbreakers always confirm
    if extracted["strength"] >= 0.9:
        return True
    
    # Permanent company/industry excludes confirm
    if (extracted["duration"] == "permanent" and 
        extracted["target_type"] in ["company", "industry"]):
        return True
    
    return False
```

---

## Preference Decay (Optional)

Some preferences might weaken over time:

```python
def apply_preference_decay(preferences: list) -> list:
    """
    Apply time-based decay to preference weights.
    Old preferences become less influential.
    """
    now = datetime.now()
    
    for pref in preferences:
        age_days = (now - pref["created_at"]).days
        
        # Explicit user preferences don't decay
        if pref["source"] == "user_explicit":
            continue
        
        # Inferred preferences decay over 180 days
        if pref["source"] == "feedback_inferred":
            decay_factor = max(0.5, 1.0 - (age_days / 360))
            pref["effective_weight"] = pref["weight"] * decay_factor
    
    return preferences
```

---

## Feedback UI Patterns

### Pattern 1: Quick Reactions

```
┌─────────────────────────────────────────┐
│ Senior Risk Manager - Frankfurt         │
│ Large German Bank                        │
│ Match: 87%                               │
│                                          │
│ [👍 Interested] [👎 Not for me] [💾 Save]│
└─────────────────────────────────────────┘

User clicks "Not for me" →
Pop-up: "Why not? (helps us improve)"
- [ ] Wrong skill fit
- [ ] Don't like this company  
- [ ] Location doesn't work
- [ ] Salary too low
- [ ] Other: [___________]
```

### Pattern 2: Free Text

```
┌─────────────────────────────────────────┐
│ 💬 Feedback on this week's report       │
│                                          │
│ [                                    ]   │
│ [                                    ]   │
│                                          │
│ [Submit Feedback]                        │
└─────────────────────────────────────────┘

User types: "Stop showing me tax jobs, 
             I'm a risk person not tax"
             
→ LLM extracts: exclude_skill: tax
→ Confirmation: "I'll exclude tax-related jobs. Correct?"
→ User confirms
→ Preference created
```

### Pattern 3: Preference Management

```
┌─────────────────────────────────────────┐
│ Your Preferences                         │
│                                          │
│ ❌ Tax (skill) - Dealbreaker            │
│ ❌ Company #47 - Dealbreaker            │
│ ✓ Frankfurt - Preferred location        │
│ ✓ Fintech - Interested industry         │
│ ⚠️ Remote only - Strong preference      │
│                                          │
│ [+ Add Preference] [Edit] [Clear All]   │
└─────────────────────────────────────────┘
```

---

## Integration with Matching

When running matches, preferences are applied:

```python
def match_with_preferences(posting, user_preferences):
    """Apply preferences during matching."""
    
    for pref in user_preferences:
        if pref["preference_type"].startswith("exclude_"):
            if matches_preference(posting, pref):
                if pref["weight"] <= -0.9:
                    # Dealbreaker - score = 0
                    return {"score": 0.0, "reason": "dealbreaker"}
                else:
                    # Soft exclude - penalty
                    score_penalty = abs(pref["weight"]) * 0.3
                    
        elif pref["preference_type"].startswith("include_"):
            if matches_preference(posting, pref):
                # Boost
                score_boost = pref["weight"] * 0.2
    
    return adjusted_score
```

---

## Open Questions

1. **How do we handle contradictory feedback?**
   - User says "no tax" then later "show me tax jobs"
   - Override? Confirm change? Average?

2. **Should feedback affect global model?**
   - If 50 users exclude same company, is that signal?
   - Privacy implications of aggregation?

3. **How to handle feedback about our AI?**
   - "Your matching is terrible"
   - "Why did you recommend this?"

4. **Multi-language feedback?**
   - User types in German: "Keine Steuer-Jobs bitte"
   - LLM needs to handle

5. **Feedback frequency limits?**
   - Prevent gaming/spam
   - Rate limit preference changes?

---

*This completes the User System proposal series:*
- *01_SCHEMA_DESIGN.md - Database structure*
- *02_PRIVACY_ARCHITECTURE.md - PII stripping*
- *03_MATCHING_ALGORITHM.md - Scoring logic*
- *04_FEEDBACK_LOOP.md - Preference learning (this doc)*
