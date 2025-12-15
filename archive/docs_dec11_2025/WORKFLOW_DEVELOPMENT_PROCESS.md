# Workflow Development Process

**Author:** Sandy (with xai)  
**Date:** December 4, 2025  
**Status:** Living document

---

## The Three-Step Workflow Development Cycle

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. SCRIPT         →    2. TEST           →    3. FORMALIZE          │
│  (Markdown doc)         (llm_chat.py)          (database workflow)   │
└──────────────────────────────────────────────────────────────────────┘
```

### Step 1: Script (Write the Conversation)

**Tool:** Markdown document in `scripts/draft/`

**Purpose:** 
- Design the conversation as if you're having it with an LLM
- Define who the LLM should be (system prompt)
- Define what you're asking (user prompt with `{placeholders}`)
- Imagine what a GOOD response looks like (expected output pattern)

**Output:** A Markdown file that IS the prototype - a scripted conversation

**Example structure:**
```markdown
## Agent: Technical Analyst

### System Prompt
You are a Technical Analyst specializing in IT skills assessment...

### User Prompt
Analyze this career profile for TECHNICAL SKILLS ONLY.

PROFILE:
---
{profile_raw_text}
---

Return ONLY a JSON array...

### Expected Response Pattern
[
  {"skill": "Oracle", "category": "database", "proficiency": "advanced", ...},
  ...
]
```

**Why Markdown, not Python?**
- The conversation IS the artifact - no code to distract
- Can be reviewed, discussed, iterated without technical overhead
- Can be fed directly to llm_chat.py for testing
- Documents intent, not just implementation

### Step 2: Test (Run It for Real)

**Tool:** `python3 tools/llm_chat.py`

**Purpose:**
- Execute your scripted conversation with a real local LLM
- Compare models (qwen2.5:7b vs gemma3:4b vs mistral)
- Tune prompts based on actual output
- Iterate until: right approach, perfect prompt, great responses, easy QA

**Command patterns:**
```bash
# Test with system prompt from your script
python3 tools/llm_chat.py --model qwen2.5:7b \
    --system "You are a Technical Analyst..." \
    --file docs/profile.md

# Interactive mode for iteration
python3 tools/llm_chat.py --model qwen2.5:7b
```

**Output:** Refined prompts, model selection, validated conversation flow

### Step 3: Formalize (Create Database Workflow)

**Tool:** SQL scripts or direct database inserts

**When to formalize:**
- Prompts are nailed
- Model selection confirmed
- Output format validated
- Ready for production use

**Steps:**
1. Create conversation(s) in `conversations` table
2. Create instruction(s) with `prompt_template` in `instructions` table
3. Create workflow in `workflows` table  
4. Link steps via `instruction_steps` table
5. Create/update actors if needed

**Output:** Workflow definition in database, ready for wave_runner execution

---

## Why This Works

1. **Low friction start** - No database, no code, just write what you want
2. **Real testing** - llm_chat.py uses actual local models, not imagination
3. **Iterate fast** - Change the MD file, re-run, see results
4. **Documentation built-in** - The scripted conversation IS the spec
5. **QA by pattern recognition** - Expected output makes validation obvious

---

## Example: Multi-Agent Skill Extraction

**Script location:** `scripts/draft/multi_agent_skill_extraction_conversation.md`

6 agents, each with their own conversation:
- Technical Analyst (tools, platforms, versions)
- Domain Expert (industry knowledge, functional skills)
- Leadership Coach (soft skills, influence patterns)
- Creative Director (media, communication, storytelling)
- Business Analyst (commercial acumen, achievements)
- Synthesizer (merge, deduplicate, resolve conflicts)

Each agent has: System Prompt → User Prompt → Expected Response Pattern

Test each with llm_chat.py, tune until great, then formalize as WF1125.

---

**Next step:** Test Agent 1 (Technical Analyst) with `llm_chat.py`
