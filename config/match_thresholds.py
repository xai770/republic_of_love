"""
Match threshold configuration for P4.3 Threshold Tuning.

These thresholds determine match tier classification and can be
calibrated based on user feedback (ratings + application outcomes).

Threshold Adjustment Rules:
- Strong tier < 70% approval rate → Raise strong threshold
- Partial tier > 60% approval rate → Lower strong threshold
- Low scores getting interviews → Lower cutoff
- High scores consistently rejected → Investigate false positive patterns
"""

# Default thresholds
MATCH_THRESHOLDS = {
    "strong": 0.70,   # Green badge, high confidence
    "partial": 0.60,  # Yellow badge, worth reviewing
    "cutoff": 0.50,   # Below this, don't show to user
}

# Domain-specific thresholds (stricter for specialized fields)
DOMAIN_THRESHOLDS = {
    "default": {"strong": 0.70, "partial": 0.60, "cutoff": 0.50},
    "legal": {"strong": 0.80, "partial": 0.70, "cutoff": 0.60},      # Legal requires precision
    "medical": {"strong": 0.80, "partial": 0.70, "cutoff": 0.60},    # Medical requires precision
    "tech": {"strong": 0.65, "partial": 0.55, "cutoff": 0.45},       # Tech skills transfer more
    "finance": {"strong": 0.72, "partial": 0.62, "cutoff": 0.52},    # Slightly higher bar
}


def get_thresholds(domain: str = None) -> dict:
    """
    Get thresholds for a specific domain.
    Falls back to default if domain not found.
    """
    if domain and domain.lower() in DOMAIN_THRESHOLDS:
        return DOMAIN_THRESHOLDS[domain.lower()]
    return DOMAIN_THRESHOLDS["default"]


def classify_match(score: float, domain: str = None) -> str:
    """
    Classify a match score into a tier.
    
    Returns: 'strong', 'partial', 'low', or 'cutoff'
    """
    thresholds = get_thresholds(domain)
    
    if score >= thresholds["strong"]:
        return "strong"
    elif score >= thresholds["partial"]:
        return "partial"
    elif score >= thresholds["cutoff"]:
        return "low"
    else:
        return "cutoff"  # Below minimum threshold


# Calibration queries for monitoring
CALIBRATION_QUERIES = {
    # Are users happy with matches in each tier?
    "approval_by_tier": """
        SELECT 
            CASE 
                WHEN skill_match_score >= 0.70 THEN 'strong'
                WHEN skill_match_score >= 0.60 THEN 'partial'
                ELSE 'low'
            END as tier,
            COUNT(*) as total_rated,
            SUM(CASE WHEN user_rating IN (4, 5, 6) THEN 1 ELSE 0 END) as approved,
            ROUND(100.0 * SUM(CASE WHEN user_rating IN (4, 5, 6) THEN 1 ELSE 0 END) / COUNT(*), 1) as approval_pct
        FROM profile_posting_matches
        WHERE user_rating IS NOT NULL
        GROUP BY 1
        ORDER BY 1;
    """,
    
    # Which scores lead to applications?
    "application_by_score": """
        SELECT 
            ROUND(skill_match_score, 1) as score_bucket,
            COUNT(*) as total_matches,
            SUM(CASE WHEN user_applied THEN 1 ELSE 0 END) as applied,
            ROUND(100.0 * SUM(CASE WHEN user_applied THEN 1 ELSE 0 END) / COUNT(*), 1) as apply_rate
        FROM profile_posting_matches
        GROUP BY 1
        ORDER BY 1 DESC;
    """,
    
    # Application outcomes by score tier
    "outcomes_by_tier": """
        SELECT 
            CASE 
                WHEN skill_match_score >= 0.70 THEN 'strong'
                WHEN skill_match_score >= 0.60 THEN 'partial'
                ELSE 'low'
            END as tier,
            application_outcome,
            COUNT(*) as count
        FROM profile_posting_matches
        WHERE application_outcome IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2;
    """,
    
    # Weekly rating trends
    "weekly_ratings": """
        SELECT 
            DATE_TRUNC('week', rated_at) as week,
            CASE 
                WHEN skill_match_score >= 0.70 THEN 'strong'
                WHEN skill_match_score >= 0.60 THEN 'partial'
                ELSE 'low'
            END as tier,
            COUNT(*) as rated,
            ROUND(AVG(CASE WHEN user_rating IN (4, 5, 6) THEN 1.0 ELSE 0.0 END) * 100, 1) as approval_pct
        FROM profile_posting_matches
        WHERE rated_at IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1 DESC, 2;
    """,
    
    # Thumbs vs stars breakdown
    "rating_types": """
        SELECT 
            CASE 
                WHEN user_rating = 6 THEN 'thumbs_up'
                WHEN user_rating = -1 THEN 'thumbs_down'
                WHEN user_rating BETWEEN 1 AND 5 THEN 'stars_' || user_rating
                ELSE 'unrated'
            END as rating_type,
            COUNT(*) as count
        FROM profile_posting_matches
        GROUP BY 1
        ORDER BY 2 DESC;
    """,
}
