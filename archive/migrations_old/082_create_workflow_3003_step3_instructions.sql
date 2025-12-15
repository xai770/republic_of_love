-- Migration 082: Workflow 3003 Step 3 - Create Instructions
-- Purpose: Create LLM prompts for Turing-native taxonomy maintenance
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

DO $$
DECLARE
    v_conv_query INTEGER;
    v_conv_analyze INTEGER;
    v_conv_organize INTEGER;
    v_conv_write INTEGER;
    v_conv_index INTEGER;
BEGIN
    -- Get conversation IDs
    SELECT conversation_id INTO v_conv_query FROM conversations WHERE canonical_name = 'w3003_c1_query';
    SELECT conversation_id INTO v_conv_analyze FROM conversations WHERE canonical_name = 'w3003_c2_analyze';
    SELECT conversation_id INTO v_conv_organize FROM conversations WHERE canonical_name = 'w3003_c3_organize';
    SELECT conversation_id INTO v_conv_write FROM conversations WHERE canonical_name = 'w3003_c4_write';
    SELECT conversation_id INTO v_conv_index FROM conversations WHERE canonical_name = 'w3003_c5_index';

    -- Instruction 1: Query skills from database
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_query,
        'Query All Skills from Database',
        1,
        'You are a database query assistant. Query the Turing database to extract ALL skills from the skill_hierarchy table.

**TASK:** Generate a SQL query to extract:
- skill_id
- skill_name
- parent_skill_id
- description (or NULL if not present)
- Any aliases from skill_aliases table

**OUTPUT FORMAT:** Return ONLY valid JSON array:
```json
[
  {
    "skill_id": 123,
    "skill_name": "Python Programming",
    "parent_skill_id": 45,
    "description": "Object-oriented programming language",
    "aliases": ["python", "py"]
  }
]
```

**IMPORTANT:**
- Include ALL skills (no LIMIT)
- Include orphan skills (parent_skill_id IS NULL)
- Group aliases by skill_id
- Output ONLY the JSON array, no explanation

BEGIN YOUR RESPONSE WITH: ```json',
        900,
        true
    );

    -- Instruction 2: Analyze taxonomy structure
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_analyze,
        'Analyze Skills and Propose Structure',
        1,
        'You are a taxonomy architect. You have received this skills data:

{{skills_json}}

**TASK:** Analyze these skills and propose a semantic organization structure.

**ANALYSIS STEPS:**
1. Identify major skill domains (e.g., Programming, Data Science, Design, Business)
2. Find natural groupings within each domain
3. Determine appropriate folder depth based on:
   - Number of skills in each category
   - Semantic relationships
   - Content-driven depth (no arbitrary limits)

**OUTPUT FORMAT:** JSON with proposed structure:
```json
{
  "top_level_categories": [
    {
      "name": "Programming Languages",
      "skill_count": 150,
      "subcategories": ["Backend", "Frontend", "Mobile", "Systems"]
    }
  ],
  "organization_strategy": "Group by paradigm first, then by technology stack",
  "max_depth": 4,
  "rationale": "Clear separation of concerns, avoids deep nesting"
}
```

BEGIN YOUR RESPONSE WITH: ```json',
        1200,
        true
    );

    -- Instruction 3: Organize skills into folder structure
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_organize,
        'Create Folder Mapping for Skills',
        1,
        'You are a file system organizer. You have:

**SKILLS DATA:**
{{skills_json}}

**TAXONOMY PLAN:**
{{taxonomy_plan}}

**TASK:** Create a mapping of each skill to its folder path in skills_taxonomy/

**RULES:**
1. Follow the taxonomy plan structure
2. Use semantic folder names (lowercase, underscores)
3. Each skill becomes a .md file: folder/path/skill_name.md
4. Respect parent-child relationships from skill_hierarchy
5. Create logical subfolder depth based on skill count

**OUTPUT FORMAT:** JSON mapping:
```json
{
  "folder_structure": {
    "programming_languages/": {
      "python/": {
        "frameworks/": ["django.md", "flask.md"],
        "libraries/": ["pandas.md", "numpy.md"]
      }
    }
  },
  "skill_paths": {
    "123": "programming_languages/python/frameworks/django.md",
    "124": "programming_languages/python/frameworks/flask.md"
  },
  "stats": {
    "total_folders": 42,
    "total_files": 543,
    "max_depth": 4
  }
}
```

BEGIN YOUR RESPONSE WITH: ```json',
        1800,
        true
    );

    -- Instruction 4: Write files to filesystem (script actor)
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_write,
        'Write Skills to Filesystem',
        1,
        'Execute file writing operation with this data:

**SKILLS DATA:**
{{skills_json}}

**FOLDER MAPPING:**
{{folder_mapping}}

**SCRIPT:** tools/taxonomy_file_writer.py

This script will:
1. Parse the folder_mapping JSON
2. Create directory structure in skills_taxonomy/
3. Write each skill as a .md file with:
   - Skill name as heading
   - Description (if present)
   - Aliases (if present)
   - Parent skill link (if present)
4. Return success/failure stats

Output the execution result.',
        600,
        true
    );

    -- Instruction 5: Generate hierarchical index
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_index,
        'Generate INDEX.md with Navigation',
        1,
        'You are a documentation generator. You have:

**FOLDER STRUCTURE:**
{{folder_mapping}}

**FILE WRITE RESULTS:**
{{write_result}}

**TASK:** Generate INDEX.md content with hierarchical navigation

**REQUIREMENTS:**
1. Create table of contents with proper indentation
2. Use markdown links to skill files
3. Show folder structure with emoji icons
4. Include stats: total skills, folders, max depth
5. Add timestamp

**OUTPUT FORMAT:** Complete INDEX.md content:
```markdown
# Skills Taxonomy - Hierarchical Index

**Generated:** 2025-11-10 10:00:00
**Total Skills:** 543
**Total Folders:** 191

---

## Navigation

📁 **Programming Languages** (150 skills)
  📁 **Python** (45 skills)
    📁 **Frameworks** (12 skills)
      - [Django](programming_languages/python/frameworks/django.md)
      - [Flask](programming_languages/python/frameworks/flask.md)
```

BEGIN YOUR RESPONSE WITH: ```markdown',
        600,
        true
    );

    RAISE NOTICE 'Created 5 instructions for Workflow 3003';
END $$;

COMMIT;

-- Verify
SELECT 
    i.instruction_id,
    i.instruction_name,
    c.canonical_name,
    LEFT(i.prompt_template, 60) as prompt_preview,
    i.timeout_seconds
FROM instructions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE c.canonical_name LIKE 'w3003_%'
ORDER BY c.canonical_name;
