-- ============================================================================
-- SkillBridge Multi-Language Extensions
-- Created: 2025-10-26
-- Purpose: Add language tracking for multi-language synonym support
-- ============================================================================

-- Add language column to skill_synonyms
ALTER TABLE skill_synonyms ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en';
CREATE INDEX IF NOT EXISTS idx_synonyms_language ON skill_synonyms(language);

COMMENT ON COLUMN skill_synonyms.language IS 
'ISO 639-1 language code: en, de, fr, es, zh, ja, etc. Canonical skills are always "en".';

-- Add language tracking to job_skills
ALTER TABLE job_skills ADD COLUMN IF NOT EXISTS source_language TEXT;
ALTER TABLE job_skills ADD COLUMN IF NOT EXISTS original_term TEXT;

COMMENT ON COLUMN job_skills.source_language IS 
'Language detected in original posting: en, de, fr, zh, ja, etc.';

COMMENT ON COLUMN job_skills.original_term IS 
'Original skill term before translation to canonical English. 
Example: "Python-Programmierung" (German) → canonical_skill_id points to "Python" (English)';

-- Language coverage tracking view
CREATE OR REPLACE VIEW v_language_coverage AS
SELECT 
    s.skill_name as canonical_skill,
    s.skill_id,
    COUNT(DISTINCT ss.language) as languages_covered,
    ARRAY_AGG(DISTINCT ss.language ORDER BY ss.language) as supported_languages,
    COUNT(ss.synonym_id) as total_synonyms
FROM skills s
LEFT JOIN skill_synonyms ss ON s.skill_id = ss.canonical_skill_id
GROUP BY s.skill_id, s.skill_name
ORDER BY languages_covered DESC, total_synonyms DESC;

COMMENT ON VIEW v_language_coverage IS 
'Shows which skills have multi-language synonym support. Target: all critical skills covered in top 5 languages (en, de, fr, es, zh).';

-- Update existing synonyms to mark as English
UPDATE skill_synonyms SET language = 'en' WHERE language IS NULL OR language = 'en';

-- Sample German synonyms (based on Recipe 1120 test with German job posting)
INSERT INTO skill_synonyms (synonym_text, canonical_skill_id, confidence, source, language)
SELECT 'Python-Programmierung', skill_id, 0.95, 'qwen2.5:7b', 'de'
FROM skills WHERE skill_name = 'Python'
ON CONFLICT (synonym_text, canonical_skill_id) DO NOTHING;

-- Sample verification
SELECT 
    s.skill_name as canonical,
    ss.synonym_text,
    ss.language,
    ss.confidence
FROM skill_synonyms ss
JOIN skills s ON ss.canonical_skill_id = s.skill_id
ORDER BY s.skill_name, ss.language;

SELECT * FROM v_language_coverage LIMIT 10;
