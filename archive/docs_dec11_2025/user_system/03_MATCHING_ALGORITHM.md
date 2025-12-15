# Matching Algorithm: Profile vs Posting

**Author:** Arden  
**Date:** 2025-11-30  
**Status:** Draft Proposal

---

## Goal

Given:
- 1 user profile (anonymized skills, experience, preferences)
- 847+ postings (with summaries, skills, IHL scores)

Produce:
- Top 20 postings, ranked by fit
- Explanation of why each posting matches

---

## Matching Dimensions

We score on multiple dimensions, then combine:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| **Skills Match** | 35% | Do they have the required skills? |
| **Experience Fit** | 20% | Right career level for the role? |
| **Industry Alignment** | 15% | Familiar with the domain? |
| **Location Match** | 15% | Can they work there? |
| **Preference Alignment** | 10% | Does it match their stated wants? |
| **IHL Score** | 5% | Red flags from our analysis |

---

## Dimension 1: Skills Match (35%)

### Data Available

**From posting (via workflow 3001):**
```json
{
  "skills": [
    {"skill_id": 123, "skill_name": "risk management", "importance": "required"},
    {"skill_id": 456, "skill_name": "python", "importance": "preferred"},
    {"skill_id": 789, "skill_name": "sql", "importance": "nice_to_have"}
  ]
}
```

**From user profile:**
```json
{
  "skills": [
    {"skill_id": 123, "proficiency": "expert", "years": 8},
    {"skill_id": 456, "proficiency": "intermediate", "years": 3}
  ]
}
```

### Scoring Logic

```python
def score_skills(posting_skills: list, user_skills: list) -> float:
    """
    Returns 0.0 to 1.0 skill match score.
    """
    user_skill_ids = {s["skill_id"] for s in user_skills}
    user_skill_proficiency = {s["skill_id"]: s["proficiency"] for s in user_skills}
    
    # Weights by importance
    importance_weights = {
        "required": 1.0,
        "preferred": 0.5,
        "nice_to_have": 0.2
    }
    
    # Proficiency multipliers
    proficiency_multiplier = {
        "beginner": 0.5,
        "intermediate": 0.8,
        "expert": 1.0
    }
    
    total_weight = 0
    earned_score = 0
    
    for ps in posting_skills:
        weight = importance_weights.get(ps["importance"], 0.3)
        total_weight += weight
        
        if ps["skill_id"] in user_skill_ids:
            # They have the skill
            prof = user_skill_proficiency.get(ps["skill_id"], "intermediate")
            multiplier = proficiency_multiplier.get(prof, 0.7)
            earned_score += weight * multiplier
    
    if total_weight == 0:
        return 0.5  # No skill requirements = neutral match
    
    return earned_score / total_weight
```

### Missing Required Skills = Penalty

If user is missing ANY required skill, apply penalty:

```python
def required_skills_penalty(posting_skills, user_skills) -> float:
    """Returns 0.0 to 1.0 penalty multiplier."""
    user_skill_ids = {s["skill_id"] for s in user_skills}
    required = [s for s in posting_skills if s["importance"] == "required"]
    
    if not required:
        return 1.0  # No penalty
    
    missing = [s for s in required if s["skill_id"] not in user_skill_ids]
    missing_ratio = len(missing) / len(required)
    
    # Missing 1 required skill = 0.7 multiplier
    # Missing 50% = 0.5 multiplier
    # Missing all = 0.3 multiplier
    return max(0.3, 1.0 - (missing_ratio * 0.7))
```

---

## Dimension 2: Experience Fit (20%)

### Career Level Mapping

| Posting Level | User Level | Score |
|---------------|------------|-------|
| Junior | Junior | 1.0 |
| Junior | Mid | 0.7 (overqualified) |
| Junior | Senior | 0.3 (way overqualified) |
| Mid | Junior | 0.5 (stretch) |
| Mid | Mid | 1.0 |
| Mid | Senior | 0.8 (slight overqualified) |
| Senior | Junior | 0.2 (too junior) |
| Senior | Mid | 0.7 (stretch) |
| Senior | Senior | 1.0 |
| Executive | Senior | 0.8 (stretch) |
| Executive | Executive | 1.0 |

```python
EXPERIENCE_MATRIX = {
    ("junior", "junior"): 1.0,
    ("junior", "mid"): 0.7,
    ("junior", "senior"): 0.3,
    ("junior", "executive"): 0.1,
    ("mid", "junior"): 0.5,
    ("mid", "mid"): 1.0,
    ("mid", "senior"): 0.8,
    ("mid", "executive"): 0.5,
    ("senior", "junior"): 0.2,
    ("senior", "mid"): 0.7,
    ("senior", "senior"): 1.0,
    ("senior", "executive"): 0.9,
    ("executive", "junior"): 0.0,
    ("executive", "mid"): 0.3,
    ("executive", "senior"): 0.8,
    ("executive", "executive"): 1.0,
}

def score_experience(posting_level: str, user_level: str) -> float:
    return EXPERIENCE_MATRIX.get(
        (posting_level.lower(), user_level.lower()), 
        0.5  # Unknown = neutral
    )
```

---

## Dimension 3: Industry Alignment (15%)

### Industry Similarity

Some industries transfer well, others don't:

```python
# Industry similarity matrix (0.0 to 1.0)
INDUSTRY_SIMILARITY = {
    ("banking", "banking"): 1.0,
    ("banking", "fintech"): 0.8,
    ("banking", "insurance"): 0.7,
    ("banking", "consulting"): 0.6,
    ("banking", "tech"): 0.4,
    ("fintech", "tech"): 0.8,
    ("consulting", "banking"): 0.7,
    ("consulting", "tech"): 0.6,
    # ... more pairs
}

def score_industry(posting_industry: str, user_industries: list) -> float:
    """Best match among user's industry experience."""
    if not user_industries:
        return 0.5  # No industry experience = neutral
    
    best_match = 0.0
    for user_ind in user_industries:
        key = (posting_industry.lower(), user_ind.lower())
        reverse_key = (user_ind.lower(), posting_industry.lower())
        
        similarity = INDUSTRY_SIMILARITY.get(key, 
                     INDUSTRY_SIMILARITY.get(reverse_key, 0.3))
        best_match = max(best_match, similarity)
    
    return best_match
```

---

## Dimension 4: Location Match (15%)

### Location Logic

```python
def score_location(posting_location: str, user_preferences: dict) -> float:
    """
    Check if posting location matches user's location preferences.
    """
    target_locations = user_preferences.get("target_locations", [])
    accepts_remote = "remote" in [l.lower() for l in target_locations]
    
    posting_loc = posting_location.lower()
    
    # Remote posting
    if "remote" in posting_loc:
        return 1.0 if accepts_remote else 0.7  # Remote is often okay
    
    # Check direct match
    for target in target_locations:
        if target.lower() in posting_loc or posting_loc in target.lower():
            return 1.0
    
    # No match
    return 0.3 if target_locations else 0.5  # Penalty if they specified locations
```

---

## Dimension 5: Preference Alignment (10%)

User preferences from `user_preferences` table:

```python
def score_preferences(posting: dict, preferences: list) -> float:
    """
    Check posting against user's explicit preferences.
    Returns 0.0 to 1.0, where:
    - 1.0 = no violations, all positives match
    - 0.0 = hard exclude triggered
    """
    score = 0.5  # Start neutral
    
    for pref in preferences:
        if not pref["is_active"]:
            continue
            
        match = check_preference_match(posting, pref)
        
        if pref["weight"] < -0.5 and match:
            # Hard exclude triggered (e.g., "no tax jobs")
            return 0.0  # Dealbreaker
        
        if pref["weight"] > 0.5 and match:
            # Hard include matched (e.g., "must have remote")
            score += 0.2
        
        if pref["weight"] < 0 and match:
            # Soft exclude
            score -= abs(pref["weight"]) * 0.2
        
        if pref["weight"] > 0 and match:
            # Soft include
            score += pref["weight"] * 0.2
    
    return max(0.0, min(1.0, score))

def check_preference_match(posting: dict, preference: dict) -> bool:
    """Does this posting trigger this preference?"""
    ptype = preference["preference_type"]
    pkey = preference["preference_key"]
    pval = preference["preference_value"]
    
    if ptype == "exclude_skill":
        return pval in [s["skill_name"].lower() for s in posting.get("skills", [])]
    
    if ptype == "exclude_company":
        return str(posting.get("company_id")) == pval
    
    if ptype == "exclude_industry":
        return pval.lower() in posting.get("industry", "").lower()
    
    if ptype == "min_salary":
        posting_salary = posting.get("salary_max", 0)
        return posting_salary >= int(pval)
    
    # ... more preference types
    
    return False
```

---

## Dimension 6: IHL Score (5%)

Our "Is it Hype or Legit?" analysis from workflow 3001:

```python
def score_ihl(posting: dict) -> float:
    """
    Convert IHL category to match score.
    We slightly prefer "legit" postings but don't penalize heavily.
    """
    ihl_category = posting.get("ihl_category", "unknown")
    
    IHL_SCORES = {
        "legit": 1.0,
        "mostly_legit": 0.9,
        "mixed": 0.7,
        "concerning": 0.5,
        "avoid": 0.2,
        "unknown": 0.7
    }
    
    return IHL_SCORES.get(ihl_category, 0.7)
```

---

## Combined Score

```python
def calculate_match_score(posting: dict, user_profile: dict, user_preferences: list) -> dict:
    """
    Calculate overall match score with breakdown.
    """
    # Individual dimension scores
    skills_score = score_skills(
        posting.get("skills", []), 
        user_profile.get("skills", [])
    )
    skills_penalty = required_skills_penalty(
        posting.get("skills", []),
        user_profile.get("skills", [])
    )
    
    experience_score = score_experience(
        posting.get("career_level", "mid"),
        user_profile.get("career_level", "mid")
    )
    
    industry_score = score_industry(
        posting.get("industry", ""),
        user_profile.get("industries", [])
    )
    
    location_score = score_location(
        posting.get("location", ""),
        user_profile
    )
    
    preference_score = score_preferences(posting, user_preferences)
    
    ihl_score = score_ihl(posting)
    
    # Weighted combination
    raw_score = (
        skills_score * 0.35 +
        experience_score * 0.20 +
        industry_score * 0.15 +
        location_score * 0.15 +
        preference_score * 0.10 +
        ihl_score * 0.05
    )
    
    # Apply skills penalty
    final_score = raw_score * skills_penalty
    
    # Preference dealbreaker override
    if preference_score == 0.0:
        final_score = 0.0
    
    return {
        "score": round(final_score, 3),
        "breakdown": {
            "skills": round(skills_score * skills_penalty, 3),
            "experience": round(experience_score, 3),
            "industry": round(industry_score, 3),
            "location": round(location_score, 3),
            "preferences": round(preference_score, 3),
            "ihl": round(ihl_score, 3)
        },
        "penalties": {
            "missing_required_skills": round(1 - skills_penalty, 3)
        }
    }
```

---

## Example Output

```json
{
  "posting_id": 123,
  "job_title": "Senior Risk Manager",
  "company": "Large German Bank",
  "score": 0.847,
  "breakdown": {
    "skills": 0.92,
    "experience": 1.0,
    "industry": 0.85,
    "location": 1.0,
    "preferences": 0.7,
    "ihl": 0.9
  },
  "match_reasons": [
    "Strong skill match: risk management (expert), python (intermediate)",
    "Experience level: senior → senior (perfect fit)",
    "Industry: banking experience directly applicable",
    "Location: Frankfurt matches your preference"
  ],
  "concerns": [
    "Missing preferred skill: tableau",
    "Below your salary minimum by ~10%"
  ]
}
```

---

## Batch Matching Process

For weekly reports:

```python
def generate_weekly_matches(user_id: int, limit: int = 20) -> list:
    """
    Generate top N matches for a user's weekly report.
    """
    # 1. Load user profile and preferences
    profile = db.get_user_profile(user_id)
    preferences = db.get_user_preferences(user_id, active_only=True)
    
    # 2. Get all active postings
    postings = db.get_active_postings()
    
    # 3. Score each posting
    scored = []
    for posting in postings:
        result = calculate_match_score(posting, profile, preferences)
        
        # Skip dealbreakers
        if result["score"] == 0.0:
            continue
        
        scored.append({
            "posting_id": posting["posting_id"],
            "score": result["score"],
            "breakdown": result["breakdown"],
            "posting": posting
        })
    
    # 4. Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    # 5. Take top N
    top_matches = scored[:limit]
    
    # 6. Generate explanations
    for match in top_matches:
        match["reasons"] = generate_match_explanation(match, profile)
    
    return top_matches
```

---

## Future Enhancements

### 1. ML-Based Scoring
- Train on user feedback (what they clicked, applied to)
- Learn personalized weights per user
- Collaborative filtering (users like you also liked...)

### 2. Semantic Skill Matching
- "Python" ≈ "Python programming" ≈ "Python development"
- Use embeddings for fuzzy skill matching
- Handle skill synonyms and variations

### 3. Temporal Factors
- New postings get boost (freshness)
- Closing-soon postings get boost (urgency)
- Stale postings get penalty

### 4. Diversity
- Don't show 20 nearly-identical jobs
- Spread across companies/industries
- Include some "stretch" opportunities

---

## Open Questions

1. **How do we handle postings with incomplete data?**
   - Missing salary → assume average?
   - Missing skills → lower confidence?

2. **Should overqualification be penalized more?**
   - VP applying for analyst role = bad match?
   - Or opportunity for career pivot?

3. **How do we calibrate weights?**
   - A/B testing with real users?
   - Feedback-based adjustment?

4. **What about "hidden gems"?**
   - Low-scoring posting that user would love
   - How do we surface serendipitous matches?

---

*Next: [04_FEEDBACK_LOOP.md](04_FEEDBACK_LOOP.md) - How does "no tax jobs" become a preference?*
