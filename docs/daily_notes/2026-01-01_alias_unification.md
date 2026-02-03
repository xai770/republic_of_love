# Daily Note: Alias Unification Insight

**Date:** 2026-01-01  
**Topic:** How aliases should work in the skill taxonomy

---

## The Insight

A canonical name IS an alias. It's just the "primary" one that happens to match `entities.canonical_name`.

**Wrong mental model:**
```
entities.canonical_name = "kubernetes"
entity_names = ["k8s", "kube", "kubernetes platform"]  ← aliases
```

**Correct mental model:**
```
entities.canonical_name = "kubernetes"  ← for internal reference only
entity_names = [
    "kubernetes" (is_primary=true),     ← THE canonical form
    "k8s",
    "kube", 
    "kubernetes platform"
]
```

## Why This Matters

**All matching should go through `entity_names`, not `entities.canonical_name`.**

When matching:
- Job posting skill: "k8s experience"
- Profile skill: "Kubernetes"

Both should match against `entity_names.display_name` (case-insensitive), which resolves to the same `entity_id`.

## Implementation Implication

Lookup queries should be:
```sql
-- Find entity for a skill phrase
SELECT e.entity_id, e.canonical_name
FROM entity_names en
JOIN entities e ON e.entity_id = en.entity_id
WHERE LOWER(en.display_name) = LOWER(%s)
AND e.entity_type = 'skill';
```

NOT:
```sql
-- WRONG - misses aliases
SELECT entity_id FROM entities 
WHERE LOWER(canonical_name) = LOWER(%s);
```

## Validation Query

To check if all posting skills are in the hierarchy:
```sql
-- Skills from postings NOT in entity_names
SELECT DISTINCT ep.skill_phrase
FROM entities_pending ep
WHERE NOT EXISTS (
    SELECT 1 FROM entity_names en
    WHERE LOWER(en.display_name) = LOWER(ep.skill_phrase)
);
```

---

*— Arden*
