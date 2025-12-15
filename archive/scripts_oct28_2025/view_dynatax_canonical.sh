#!/bin/bash
# View complete DynaTax canonical prompt script
# Created: 2025-10-23 17:12

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 DYNATAX CANONICAL: riic_dynatax_skill_matcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

sqlite3 /home/xai/Documents/ty_learn/data/llmcore.db << 'SQL'
.mode line
.headers off

SELECT '📋 CANONICAL CODE:' as field;
SELECT '  ' || canonical_code FROM canonicals WHERE canonical_code = 'dynatax_skills_categorizer';
SELECT '' as blank;

SELECT '🎯 FACET ID:' as field;
SELECT '  ' || facet_id || ' (reason → induce → induce_implicit → competencies)' FROM canonicals WHERE canonical_code = 'dynatax_skills_categorizer';
SELECT '' as blank;

SELECT '💡 CAPABILITY DESCRIPTION:' as field;
SELECT '  ' || capability_description FROM canonicals WHERE canonical_code = 'dynatax_skills_categorizer';
SELECT '' as blank;

SELECT '📝 PROMPT SCRIPT:' as field;
SELECT '─────────────────────────────────────────────────────────────────────────────────' as separator;
SELECT prompt FROM canonicals WHERE canonical_code = 'dynatax_skills_categorizer';
SELECT '─────────────────────────────────────────────────────────────────────────────────' as separator;
SELECT '' as blank;

SELECT '✅ EXPECTED RESPONSE FORMAT:' as field;
SELECT '  ' || response FROM canonicals WHERE canonical_code = 'dynatax_skills_categorizer';
SELECT '' as blank;

SELECT '📌 REVIEW NOTES:' as field;
SELECT '  ' || review_notes FROM canonicals WHERE canonical_code = 'dynatax_skills_categorizer';
SELECT '' as blank;

SELECT '🔧 STATUS:' as field;
SELECT '  Enabled: ' || CASE enabled WHEN 1 THEN 'YES ✅' ELSE 'NO ❌' END FROM canonicals WHERE canonical_code = 'dynatax_skills_categorizer';

SQL

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💙 Use this prompt script to create/improve DynaTax recipes"
echo "📁 Related: Recipe 1120 (gershon_smart_matcher), dynatax_analysis.sql"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
