# Conversation Tag Quick Reference

**Version:** 1.0  
**Date:** 2025-11-19  
**Purpose:** Fast lookup for conversation tagging

---

## Tag by Category

### 📥 Data Operations
| Tag | When to Use | Example |
|-----|-------------|---------|
| `fetch` | Retrieve data from external source (API, web, DB) | Fetch jobs from Deutsche Bank API |
| `extract` | Extract structured info from unstructured content | Extract skills from job description |
| `validate` | Check data quality, completeness, format | Validate profile JSON structure |
| `transform` | Convert data format/structure | Transform job data to standard schema |
| `save` | Persist data to database/storage | Save extracted profile to database |

### 🔍 Analysis Operations
| Tag | When to Use | Example |
|-----|-------------|---------|
| `classify` | Categorize data into predefined classes | Classify job by industry |
| `score` | Assign numerical rating/confidence | Score job-candidate match |
| `rank` | Order items by importance/relevance | Rank candidates by fit score |
| `match` | Find relationships/similarities | Match candidate skills to job requirements |
| `compare` | Identify differences and similarities | Compare contract versions |

### ✨ Generation Operations
| Tag | When to Use | Example |
|-----|-------------|---------|
| `summarize` | Create concise summary of longer content | Summarize job posting |
| `generate` | Create new content from scratch/templates | Generate cover letter |
| `translate` | Convert content between languages | Translate job description to German |
| `format` | Apply styling/structure/presentation | Format profile as HTML |
| `combine` | Merge multiple inputs into unified output | Combine multiple skill extractions |

### 🧠 Reasoning Operations
| Tag | When to Use | Example |
|-----|-------------|---------|
| `analyze` | Deep examination of patterns/causes | Analyze job market trends |
| `recommend` | Provide actionable suggestions | Recommend go/no-go decision |
| `explain` | Clarify reasoning, justify decisions | Explain match score rationale |
| `critique` | Evaluate quality, suggest improvements | Critique chapter draft |

### ✅ Quality Operations
| Tag | When to Use | Example |
|-----|-------------|---------|
| `review` | Human/AI examination for approval | Review extracted data for accuracy |
| `verify` | Confirm correctness against known truth | Verify skill taxonomy mapping |
| `audit` | Systematic examination for compliance | Audit data pipeline for hallucinations |
| `detect_errors` | Identify mistakes, inconsistencies | Detect hallucinated skills |

---

## Quick Selection Guide

### How Many Tags?
- **1 tag:** Conversation has single clear purpose (e.g., pure fetch or pure save)
- **2 tags:** Conversation does two distinct things (e.g., fetch + extract, validate + verify)
- **3 tags:** Complex conversation with multiple phases (e.g., review + score + verify)
- **Never 4+:** Split into multiple conversations instead

### Tag Selection Rules
1. ✅ **DO:** Describe what conversation DOES (action verbs)
2. ✅ **DO:** Choose tags that work across apps (talent, news, write, etc.)
3. ✅ **DO:** Use existing tags before creating new ones
4. ❌ **DON'T:** Tag what it processes (e.g., don't use "job" or "profile")
5. ❌ **DON'T:** Tag the domain (e.g., don't use "talent" or "recruiting")
6. ❌ **DON'T:** Create compound tags (e.g., don't use "extract_and_validate")

### Common Tag Combinations
| Combination | Meaning | Use Case |
|-------------|---------|----------|
| `fetch` + `extract` | Get data and parse it | API calls that return structured data |
| `extract` + `validate` | Parse and quality check | Two-phase extraction with verification |
| `extract` + `summarize` | Parse and condense | Extract key info and create summary |
| `review` + `score` | Evaluate and rate | LLM grading of extraction quality |
| `review` + `verify` | Check and confirm | Two-phase validation |
| `match` + `score` + `rank` | Find, rate, order | Complete matching pipeline |
| `classify` + `score` | Categorize and rate confidence | Classification with certainty score |
| `analyze` + `recommend` | Examine and suggest | Decision support workflow |

---

## Usage Cheat Sheet

### Tagging During Workflow Creation
```sql
-- Tag a single conversation
SELECT tag_conversation(conversation_id, ARRAY['extract', 'validate']);

-- Tag using canonical_name lookup
SELECT tag_conversation(
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'w3001_c1_fetch'),
    ARRAY['fetch', 'extract']
);
```

### Finding Tagged Conversations
```sql
-- Find by single tag
SELECT * FROM v_conversation_discovery WHERE 'extract' = ANY(tags);

-- Find by multiple tags (OR logic)
SELECT * FROM v_conversation_discovery 
WHERE tags && ARRAY['extract', 'summarize'];

-- Find by app + tag
SELECT * FROM v_conversation_discovery
WHERE app_scope = 'talent' AND 'match' = ANY(tags);

-- Find by category
SELECT * FROM v_conversation_discovery
WHERE tag_categories LIKE '%quality%';
```

### Checking Tag Definitions
```sql
-- See all tags in a category
SELECT tag, description FROM conversation_tag_definitions 
WHERE category = 'data';

-- See examples for a specific tag
SELECT tag, examples FROM conversation_tag_definitions 
WHERE tag = 'extract';

-- See all categories
SELECT DISTINCT category FROM conversation_tag_definitions;
```

---

## Decision Tree

```
Is the conversation primarily about...

┌─ Getting data from external source?
│  └─ Use: fetch
│
┌─ Parsing/extracting structured data?
│  └─ Use: extract
│
┌─ Checking data quality?
│  └─ Use: validate OR verify (validate=format, verify=correctness)
│
┌─ Converting data format?
│  └─ Use: transform
│
┌─ Saving to database?
│  └─ Use: save
│
┌─ Categorizing into classes?
│  └─ Use: classify
│
┌─ Rating with a number?
│  └─ Use: score
│
┌─ Ordering a list?
│  └─ Use: rank
│
┌─ Finding similarities/relationships?
│  └─ Use: match
│
┌─ Comparing two things?
│  └─ Use: compare
│
┌─ Creating a summary?
│  └─ Use: summarize
│
┌─ Creating new content?
│  └─ Use: generate
│
┌─ Translating languages?
│  └─ Use: translate
│
┌─ Applying styling/structure?
│  └─ Use: format
│
┌─ Merging multiple inputs?
│  └─ Use: combine
│
┌─ Deep pattern analysis?
│  └─ Use: analyze
│
┌─ Making suggestions?
│  └─ Use: recommend
│
┌─ Explaining reasoning?
│  └─ Use: explain
│
┌─ Evaluating quality?
│  └─ Use: critique
│
┌─ Human/AI approval check?
│  └─ Use: review
│
┌─ Confirming correctness?
│  └─ Use: verify
│
┌─ Systematic compliance check?
│  └─ Use: audit
│
└─ Finding errors/problems?
   └─ Use: detect_errors
```

---

## Common Mistakes

### ❌ Wrong: Domain-specific tags
```sql
-- DON'T tag with domain terms
SELECT tag_conversation(conv_id, ARRAY['job', 'profile', 'candidate']);
```

### ✅ Right: Action verb tags
```sql
-- DO tag with what it does
SELECT tag_conversation(conv_id, ARRAY['extract', 'match', 'score']);
```

### ❌ Wrong: Too many tags
```sql
-- DON'T use more than 3 tags
SELECT tag_conversation(conv_id, ARRAY['fetch', 'extract', 'validate', 'transform', 'save']);
-- Instead, split into multiple conversations!
```

### ✅ Right: Focused tagging
```sql
-- DO keep it focused (1-3 tags)
SELECT tag_conversation(conv_id_1, ARRAY['fetch', 'extract']);
SELECT tag_conversation(conv_id_2, ARRAY['validate']);
SELECT tag_conversation(conv_id_3, ARRAY['transform', 'save']);
```

### ❌ Wrong: Creating new tags
```sql
-- DON'T invent new tags without discussion
INSERT INTO conversation_tag_definitions VALUES ('scrape', 'data', 'Web scraping');
```

### ✅ Right: Use existing tags
```sql
-- DO use existing tags (fetch for web scraping)
SELECT tag_conversation(conv_id, ARRAY['fetch', 'extract']);
```

---

## When Unsure

1. **Check similar conversations:** See how others tagged similar work
   ```sql
   SELECT conversation_name, tags FROM v_conversation_discovery
   WHERE conversation_description ILIKE '%similar_keyword%';
   ```

2. **Read tag examples:**
   ```sql
   SELECT tag, examples FROM conversation_tag_definitions 
   WHERE tag IN ('extract', 'validate', 'transform');
   ```

3. **Ask:** Prefer asking before creating new tags or unusual combinations

---

## Tag Statistics

View most common tags:
```sql
SELECT tag, COUNT(*) as usage_count
FROM conversation_tags
GROUP BY tag
ORDER BY usage_count DESC;
```

View untagged conversations:
```sql
SELECT conversation_id, conversation_name, app_scope
FROM conversations
WHERE NOT EXISTS (
    SELECT 1 FROM conversation_tags ct 
    WHERE ct.conversation_id = conversations.conversation_id
);
```

---

**Quick Reference Version:** 1.0  
**Last Updated:** 2025-11-19  
**Maintained By:** Arden (Schema & Architecture)
