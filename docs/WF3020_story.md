	# WF3020: The Skill Librarians

*A tale of seven librarians who organize the world's skills*

---

## The Library

Imagine a vast library where every professional skill in the world needs a home. The library starts with **five main halls** (but can grow when Clara proposes and Victor approves new ones):

| Hall | What Lives Here |
|------|-----------------|| **Technical Engineering** | Programming, DevOps, cloud, databases, frameworks, tools |
| **Data & Analytics** | Data science, ML/AI, business intelligence, visualization |
| **Compliance & Risk** | AML/KYC, regulatory, audit, legal, risk management |
| **Finance & Banking** | Trading, accounting, financial analysis, treasury |
| **Communication & Leadership** | Soft skills, teamwork, management, presentation |

Each hall has **sections** (subgroups), and sections have **shelves** (more specific subgroups). A skill card must find its most specific home.

---

## The Librarians

### Lucy the Lookup Clerk

**Job:** Check if a skill card already exists in the catalog.

Lucy sits at the front desk. When a skill name arrives, she:
1. Checks the master catalog (entities table) for exact match
2. Checks aliases (entity_names table) 
3. Tries fuzzy matching for obvious variants (python3 → python)

**Lucy reports:**
- `found: true` + `entity_id` → "This skill exists, card #12345"
- `found: false` → "New skill, needs a card"

```
Input:  "kubernetes"
Output: {found: true, entity_id: 23456, canonical_name: "kubernetes"}

Input:  "some_new_skill_xyz"
Output: {found: false, skill_name: "some_new_skill_xyz"}
```

**⚠️ Critical Contract:** When WF3020 receives a specific entity from the queue (subject_id), Lucy must preserve that entity_id in her output. If Lucy finds a *different* entity with the same name (e.g., a `skill_atomic` when we queued a `skill`), she should note the match but still return the original subject_id for classification. See "Entity ID Contract Bug" in Arden's Update for details.

---

### Carl the Card Maker

**Job:** Create catalog cards for new skills.

Carl only works when Lucy says `found: false`. He:
1. Creates a new entity record (type: skill_atomic)
2. Normalizes the name (lowercase, underscores)
3. Returns the new entity_id

```
Input:  {skill_name: "Some New Skill"}
Output: {entity_id: 99999, canonical_name: "some_new_skill", created: true}
```

---

### Clara the Classifier

**Job:** Look at a skill and pick which hall/section it belongs in.

Clara is an AI (**gemma2:latest** — see Arden's Update below for model selection rationale). She receives:
- The skill name
- Her current location in the library
- A list of options (halls or sections to choose from)

**Clara's Options (Decision Space):**

| Letter | Meaning | When to Pick | Output Format |
|--------|---------|--------------|---------------|
| `[a-f]` | Navigate to category | Best semantic match | `[a]` |
| `[h]` | PLACE HERE | Current location is most specific fit | `[h]` |
| `[z]` | GO BACK | Wrong turn, need to backtrack | `[z]` |
| `[n]` | NEW CATEGORY | None fit, propose new | `[n] name: description` |

**Example prompt Clara sees:**
```
Skill: kubernetes
Location: IN technical_engineering

Options:
a. containerization_and_orchestration - Docker, Kubernetes, container tools
b. devops_and_automation - CI/CD, infrastructure as code
c. cloud_platforms - AWS, Azure, GCP services
d. databases - SQL, NoSQL, data storage
h. ** PLACE HERE ** - File in technical_engineering (no deeper fit)
z. ** GO BACK ** - Return to previous level
n. ** NEW CATEGORY ** - Propose a new section

Pick the BEST match. Reply with just the letter in brackets.
```

**Clara responds:** `[a]` (containerization is most specific for kubernetes)

**If Clara picks `[n]` NEW CATEGORY:**
```
[n] kubernetes_ecosystem: Kubernetes-specific tools, operators, and distributions
```
This goes to Victor for approval before the category is created.

---

### Victor the Verifier (Supervisor)

**Job:** Review Clara's proposals for new categories. Create approved groups.

Victor is a larger, more capable AI (claude/gpt-4). He only gets involved when Clara proposes something new (a new hall or section).

**Victor receives:**
- The skill Clara is trying to classify
- Clara's proposed new category name and description
- The existing options Clara rejected
- Current location in hierarchy (where new group would be created)

**Victor's Options (Decision Space):**

| Choice | Meaning | What Happens Next |
|--------|---------|-------------------|
| `APPROVE` | Proposal is valid and distinct | Victor creates the group, then Adam files skill there |
| `REJECT: use [existing]` | Existing category fits | Clara receives feedback, must pick from existing |
| `REJECT: modify to [suggestion]` | Proposal needs refinement | Clara can accept modification or pick existing |

**Victor creates the group** when approving (not Carl, not Adam). He has authority to extend the taxonomy.

**Rejection loop limit:** Max 2 rounds. If Clara and Victor disagree twice:
```
Round 1: Clara proposes → Victor rejects
Round 2: Clara re-proposes → Victor rejects again
Round 3: ESCALATE to human review OR force Clara to pick existing
```

**Example exchange:**
```
Victor receives:
  Skill: regulatory_sandbox_testing
  Clara's proposal: fintech_innovation - Emerging fintech, sandboxes, blockchain
  Existing options: compliance_risk, finance_banking
  Location: TOP LEVEL

Victor responds:
  APPROVE
  Creating group: fintech_innovation (is_a → TOP LEVEL)
  Rationale: Distinct from both compliance (regulatory focus) and finance 
  (banking focus). Fintech innovation spans both but has unique concerns.

--- or ---

Victor responds:
  REJECT: use compliance_risk
  Rationale: Regulatory sandbox testing is fundamentally about compliance,
  even if the context is innovative. The "sandbox" is a compliance mechanism.
```

**Note:** This supervisor review is rare — most skills fit existing categories. But it allows the taxonomy to grow organically when genuinely new domains emerge.

---

### Nate the Navigator

**Job:** Process Clara's choice, update location, build next options.

Nate is a script. When Clara picks `[a]`, Nate:
1. Looks up what 'a' means (e.g., "technical_engineering")
2. Queries the database for children of that group
3. Builds new options for Clara
4. Tracks depth and path (how deep, and how we got here)

**State Management (Path Stack):**

Nate maintains a `path` array to enable GO BACK:
```python
# Initial state
path = []  # Empty = TOP LEVEL

# Clara picks [a] technical_engineering
path = ["technical_engineering"]  # depth = 1

# Clara picks [b] databases
path = ["technical_engineering", "databases"]  # depth = 2

# Clara picks [z] GO BACK
path = ["technical_engineering"]  # Pop! Back to depth = 1
```

**Depth Limit:** Max depth = 10. If `len(path) >= 10`, Nate removes navigation options and only offers PLACE HERE. No taxonomy needs 10+ levels.

**Critical behavior:**
- If the selected group has children → build options from children + "PLACE HERE" + "GO BACK"
- If no children exist → options are "PLACE HERE" + "GO BACK"
- If depth ≥ 10 → options are "PLACE HERE" only (force termination)
- When Clara picks "PLACE HERE" → Nate sets `done: true`
- When Clara picks "GO BACK" → Nate pops the path stack, rebuilds parent's options

**Why GO BACK matters:** Clara might pick the wrong hall initially. If `kubernetes` accidentally goes into `finance_banking`, Clara needs a way to say "oops, wrong turn" and go back up. Without backtrack, mistakes become permanent.

```
Input:  {letter: "a", path: [], current_options: {a: "technical_engineering", ...}}
Output: {location: "IN: technical_engineering",
         path: ["technical_engineering"],
         options: "a. devops_and_automation...\nb. databases...\nh. PLACE HERE\nz. GO BACK",
         done: false}

--- later ---

Input:  {letter: "h", path: ["technical_engineering", "databases"]}
Output: {done: true, target_group: "databases"}

--- or if wrong turn ---

Input:  {letter: "z", path: ["technical_engineering", "databases"]}
Output: {location: "IN: technical_engineering",
         path: ["technical_engineering"],  # Popped!
         options: "a. databases...\nb. devops...\nh. PLACE HERE\nz. GO BACK",
         done: false}
```

**⚠️ Implementation Note:** The `path` array must survive Clara↔Nate loop iterations. This uses the same state-passing pattern fixed in WF3011 (Dec 28). If that fix isn't applied, path will reset each iteration.

---

### Adam the Archivist

**Job:** File the skill card in its final location.

Adam only runs when Nate says `done: true`. He:
1. Gets the skill's entity_id
2. Gets the target_group from Nate
3. Creates a `belongs_to` relationship
4. Verifies no duplicate filing (unique constraint)

```
Input:  {entity_id: 23456, target_group: "containerization_and_orchestration"}
Output: {success: true, relationship: "kubernetes belongs_to containerization_and_orchestration"}
```

---

### Quinn the Quality Auditor

**Job:** Enforce the library rules. Find violations and flag them for repair.

Quinn is a script that runs **after each batch** (not per-skill). She:
1. Checks all QA rules (see "QA Requirements" section)
2. Logs violations to a report table
3. Triggers repair actions or flags for human review

**Trigger Mechanism:**
- **Automatic:** After every 100 workflow_runs complete (daemon hook)
- **Scheduled:** Daily full audit at 3:00 AM (cron)
- **Manual:** `python scripts/wf3020_qa.py --full-audit`

**Quinn runs in two modes:**

| Mode | When | What |
|------|------|------|
| **Post-batch** | After 100 workflow_runs | Quick checks on newly-filed skills |
| **Full audit** | Daily or on-demand | Complete taxonomy health check |

**Quinn's checks:**
```
1. Empty groups      → DELETE or flag for review
2. Loops detected    → HALT + alert (manual fix required)
3. Multiple parents  → Flag for merge decision
4. Oversized groups  → Queue for split (Clara + Victor)
5. Orphan groups     → Queue for wiring (Clara classifies the group itself)
6. Duplicate skills  → Flag for merge + alias creation
```

**Quinn does NOT:**
- Make judgment calls (that's Clara/Victor's job)
- Delete skills (only empty groups)
- Break ties on multiple parents (needs human decision)

**Quinn reports:**
```
Input:  {mode: "full_audit"}
Output: {
  empty_groups: 12,
  loops: 0,
  multiple_parents: 3,
  oversized_groups: ["technical_engineering"],
  orphan_groups: 7,
  duplicate_skills: ["python_programming", "python"],
  health: "NEEDS_ATTENTION"
}
```

When `health: "HEALTHY"`, the taxonomy is clean. Otherwise, Quinn's report drives the repair queue.

---

## The Workflow

```mermaid
flowchart TD
    START([skill_atomic arrives<br/>e.g. 'kubernetes']) --> LUCY

    subgraph LUCY [Lucy - Lookup Clerk]
        L1[Check entities table]
        L1 --> L2{Found?}
    end

    L2 -->|found: false| CARL
    L2 -->|found: true| CLARA

    subgraph CARL [Carl - Card Maker]
        C1[Create new entity<br/>entity_id: 99999]
    end
    CARL --> CLARA

    subgraph CLARA [Clara - Classifier AI]
        CL1[See skill + location + options]
        CL1 --> CL2[Pick a letter]
    end

    CLARA --> NATE

    subgraph NATE [Nate - Navigator]
        N1[Process Clara's choice]
        N1 --> N2{What did<br/>Clara pick?}
    end

    N2 -->|letter a-f<br/>go deeper| N3[Query children<br/>Build new options]
    N2 -->|letter z<br/>GO BACK| N4[Return to parent<br/>Build parent options]
    N2 -->|letter h<br/>PLACE HERE| N5[Set done: true<br/>target_group = current]
    N2 -->|letter n<br/>NEW CATEGORY| VICTOR

    N3 --> CLARA
    N4 --> CLARA
    N5 --> ADAM

    subgraph VICTOR [Victor - Supervisor]
        V1{Review Clara's<br/>proposal}
        V1 -->|Approved| V2[Create new group]
        V1 -->|Rejected| V3[Send feedback<br/>to Clara]
    end

    V2 --> ADAM
    V3 --> CLARA

    subgraph ADAM [Adam - Archivist]
        A1[Create belongs_to<br/>relationship]
        A1 --> A2[✓ Filed]
    end

    A2 --> BATCH{Batch<br/>complete?}
    BATCH -->|No| START
    BATCH -->|Yes| QUINN

    subgraph QUINN [Quinn - Quality Auditor]
        Q1[Run QA checks]
        Q1 --> Q2{Health?}
    end

    Q2 -->|HEALTHY| DONE([✓ Batch Done])
    Q2 -->|NEEDS_ATTENTION| REPAIR

    subgraph REPAIR [Repair Queue]
        R1{Issue type?}
        R1 -->|Empty groups| R2[DELETE empty]
        R1 -->|Orphan groups| R3[Queue group<br/>for classification]
        R1 -->|Oversized| R4[Queue group<br/>for split]
        R1 -->|Duplicates| R5[Flag for<br/>human review]
        R1 -->|Loops| R6[🚨 HALT<br/>manual fix]
    end

    R2 --> QUINN
    R3 --> CLARA
    R4 --> VICTOR
    R5 --> DONE
    R6 --> DONE

    style LUCY fill:#e1f5fe
    style CARL fill:#fff3e0
    style CLARA fill:#f3e5f5
    style NATE fill:#e8f5e9
    style ADAM fill:#fce4ec
    style VICTOR fill:#fff9c4
    style QUINN fill:#e0f2f1
    style REPAIR fill:#ffebee
```

### Example: Classifying "kubernetes"

```mermaid
sequenceDiagram
    participant S as Skill: kubernetes
    participant Lucy
    participant Clara
    participant Nate
    participant Adam

    S->>Lucy: kubernetes
    Lucy->>Lucy: Check catalog
    Lucy-->>Clara: found: true, entity_id: 23456

    Note over Clara: Location: TOP LEVEL<br/>Options: a-e (5 domains) + h (place here)
    Clara->>Nate: [a] technical_engineering

    Nate->>Nate: Query children of technical_engineering
    Note over Nate: Found: containerization, devops, databases...
    Nate-->>Clara: location: IN technical_engineering

    Note over Clara: Options: a. containerization<br/>b. devops<br/>h. PLACE HERE<br/>z. GO BACK
    Clara->>Nate: [a] containerization_and_orchestration

    Nate->>Nate: Query children
    Note over Nate: No children found
    Nate-->>Clara: location: IN containerization

    Note over Clara: Options: h. PLACE HERE<br/>z. GO BACK
    Clara->>Nate: [h] PLACE HERE

    Nate-->>Adam: done: true, target_group: containerization
    Adam->>Adam: INSERT belongs_to
    Adam-->>S: ✓ kubernetes → containerization_and_orchestration
```

---

## Error Handling

Things fail. Here's what happens when they do.

### Per-Actor Failures

| Actor | Failure | Action | Recovery |
|-------|---------|--------|----------|
| **Lucy** | Multiple fuzzy matches | Return all candidates | Clara disambiguates (or pick closest) |
| **Lucy** | DB timeout | Retry 3x with backoff | Mark workflow_run failed |
| **Carl** | Duplicate entity (race) | `ON CONFLICT DO NOTHING` | Fetch existing entity_id, continue |
| **Clara** | LLM timeout | Retry 2x | Mark failed, log, continue to next skill |
| **Clara** | Invalid response | Parse error | Retry with "please respond with just [letter]" |
| **Clara** | Stuck in loop (>20 turns) | Force termination | Place at current location, flag for review |
| **Nate** | Empty children query | Not an error | Offer only PLACE HERE + GO BACK |
| **Victor** | LLM timeout | Retry 2x | Escalate to human (don't auto-reject) |
| **Adam** | Constraint violation | Skill already filed | Log duplicate, continue (idempotent) |
| **Quinn** | Loop detected | HALT all processing | Alert human, manual fix required |

### Race Condition Prevention

Two workflow_runs for the same skill starting simultaneously:
```sql
-- Carl's INSERT must be idempotent
INSERT INTO entities (canonical_name, entity_type)
VALUES ($1, 'skill_atomic')
ON CONFLICT (canonical_name, entity_type) DO NOTHING
RETURNING entity_id;

-- If no row returned, fetch existing
SELECT entity_id FROM entities 
WHERE canonical_name = $1 AND entity_type = 'skill_atomic';
```

### General Rule

> On any unrecoverable error: mark `workflow_run.status = 'failed'`, log full context to `workflow_run.error_message`, continue with next skill in queue.

Failed skills can be retried later. The taxonomy must not block on individual failures.

### Lucy's Fuzzy Match Disambiguation

When Lucy finds multiple close matches:
```
Input:  "python3"
Matches: ["python", "python_scripting", "python_django"]

Option A: Pick closest (Levenshtein distance) → "python"
Option B: Return all, let Clara pick → {candidates: ["python", "python_scripting"]}
```

**Current implementation:** Option A (pick closest). If confidence < 0.8, treat as "not found" and let Carl create new.

---

## The Hierarchy Structure

For this to work, the library needs proper **structure**:

```
LEVEL 0: Halls (5 top-level domains)
├── technical_engineering
├── data_analytics_intelligence  
├── compliance_risk
├── finance_banking
└── communication_collaboration

LEVEL 1: Sections (connected via is_a)
├── technical_engineering
│   ├── containerization_and_orchestration (is_a → technical_engineering)
│   ├── devops_and_automation (is_a → technical_engineering)
│   ├── databases (is_a → technical_engineering)
│   ├── programming_languages (is_a → technical_engineering)
│   └── cloud_platforms (is_a → technical_engineering)
├── compliance_risk
│   ├── aml_kyc_compliance (is_a → compliance_risk)
│   ├── regulatory_compliance (is_a → compliance_risk)
│   └── risk_management (is_a → compliance_risk)
... etc

LEVEL 2+: Shelves (deeper sections)
├── containerization_and_orchestration
│   ├── kubernetes_ecosystem (is_a → containerization_and_orchestration)
│   ├── docker_tools (is_a → containerization_and_orchestration)
│   └── container_security (is_a → containerization_and_orchestration)
```

**Skills file at the most specific level that fits:**
- `kubernetes` → belongs_to → `containerization_and_orchestration`
- `risk_analysis` → belongs_to → `risk_management`
- `leadership` → belongs_to → `communication_collaboration` (top level, nothing more specific)

---

## What Went Wrong (December 2025)

### Problem: Flat Hierarchy

The 5 halls existed. The sections existed. But **no is_a connections** between them!

```
Nate's query: "What sections are in technical_engineering?"
Database:     "None."
Result:       Clara's only option is PLACE HERE
              → All 3,000 tech skills land directly in technical_engineering
```

### The Evidence

```
┌─────────────────────────────┬────────┐
│ Domain                      │ Skills │
├─────────────────────────────┼────────┤
│ technical_engineering       │  3,092 │  ← EVERYTHING piled here
│ communication_collaboration │  1,060 │
│ finance_banking             │  1,043 │
│ compliance_risk             │    966 │
│ data_analytics_intelligence │    558 │
└─────────────────────────────┴────────┘

Subgroups with skills: 0
Empty orphan groups:   352
```

### Root Cause

Groups were created but never **wired** to their parent domains:

```sql
-- These groups EXIST:
containerization_and_orchestration (61 children!)
devops_and_automation (31 children!)
aml_kyc_compliance (26 children!)

-- But they're NOT CONNECTED to the 5 top domains:
SELECT * FROM entity_relationships 
WHERE relationship = 'is_a' 
AND related_entity_id IN (top_5_domains);
-- Result: 0 rows
```

---

## The Fix

### Step 1: Clean Up Garbage

```sql
-- Delete 352 empty orphan groups (no skills, no children)
DELETE FROM entities WHERE entity_type = 'skill_group' 
AND entity_id NOT IN (
    SELECT related_entity_id FROM entity_relationships 
    WHERE relationship IN ('belongs_to','is_a')
);

-- Delete broken is_a relationships (garbage from buggy runs)
DELETE FROM entity_relationships WHERE relationship = 'is_a';
```

### Step 2: Wire Sections to Domains

Use Clara to classify the 42 intermediate groups:

```
"Clara, where does 'containerization_and_orchestration' belong?"
Clara: [a] technical_engineering

→ INSERT: containerization_and_orchestration is_a technical_engineering
```

### Step 3: Re-run Classification

Queue all 9,415 skills through WF3020 again. This time:
- Nate finds children (the newly-wired sections)
- Clara can navigate INTO sections
- Skills land at the right depth

---

## QA Requirements (The Library Rules)

A healthy taxonomy must satisfy these invariants:

### Structural Rules

| Rule | Check | Why It Matters |
|------|-------|----------------|
| **No empty groups** | Every group has ≥1 skill or ≥1 child group | Empty folders waste navigation; Clara sees useless options |
| **No loops** | `is_a` chains terminate at a root (no cycles) | Infinite navigation; Nate never reaches "done" |
| **Single parent** | Each group has exactly ONE `is_a` parent (or zero if root) | Multiple parents = ambiguous path; skill could end up in either |
| **Balanced depth** | Groups have 1–20 direct members | Too few (1-2) = over-fragmented; too many (20+) = Clara overwhelmed |
| **All roots are domains** | Groups with no `is_a` parent are one of the 5 top-level domains | Orphan groups = invisible to navigation; skills can't reach them |

### Data Quality Rules

| Rule | Check | Why It Matters |
|------|-------|----------------|
| **No duplicate skills** | Same canonical name shouldn't exist in multiple groups | "python" in `programming_languages` AND `data_science` = confusion |
| **Aliases recorded** | Variants stored in `entity_names` | "Python", "python3", "PYTHON" all resolve to canonical `python` |
| **Proper capitalization** | Display names honor conventions (SAP, PostgreSQL, JavaScript) | Presentation quality; user-facing output looks professional |
| **Provenance tracked** | Skills link back to source via `entity_names.verbatim` | Can trace where extraction came from; debug bad atomizations |

### Operational Checks

```sql
-- 1. Find empty groups (no skills, no children)
SELECT e.entity_id, e.canonical_name 
FROM entities e
WHERE e.entity_type = 'skill_group'
AND NOT EXISTS (SELECT 1 FROM entity_relationships r WHERE r.related_entity_id = e.entity_id)
AND NOT EXISTS (SELECT 1 FROM entity_relationships r WHERE r.entity_id = e.entity_id);

-- 2. Find loops (recursive CTE, LIMIT to detect cycles)
WITH RECURSIVE chain AS (
  SELECT entity_id, related_entity_id, 1 as depth, ARRAY[entity_id] as path
  FROM entity_relationships WHERE relationship = 'is_a'
  UNION ALL
  SELECT c.entity_id, r.related_entity_id, c.depth + 1, c.path || r.entity_id
  FROM chain c
  JOIN entity_relationships r ON c.related_entity_id = r.entity_id AND r.relationship = 'is_a'
  WHERE c.depth < 20 AND NOT r.entity_id = ANY(c.path)
)
SELECT * FROM chain WHERE depth = 20;  -- If results, potential loop

-- 3. Find groups with multiple parents
SELECT entity_id, COUNT(*) as parent_count
FROM entity_relationships WHERE relationship = 'is_a'
GROUP BY entity_id HAVING COUNT(*) > 1;

-- 4. Find oversized groups (>20 direct children)
SELECT r.related_entity_id as group_id, e.canonical_name, COUNT(*) as child_count
FROM entity_relationships r
JOIN entities e ON r.related_entity_id = e.entity_id
WHERE r.relationship IN ('belongs_to', 'is_a')
GROUP BY r.related_entity_id, e.canonical_name
HAVING COUNT(*) > 20;

-- 5. Find orphan groups (not roots, but no is_a parent)
SELECT e.entity_id, e.canonical_name
FROM entities e
WHERE e.entity_type = 'skill_group'
AND e.canonical_name NOT IN ('technical_engineering','data_analytics_intelligence',
    'compliance_risk','finance_banking','communication_collaboration')
AND NOT EXISTS (
  SELECT 1 FROM entity_relationships r 
  WHERE r.entity_id = e.entity_id AND r.relationship = 'is_a'
);
```

### When Rules Are Violated

| Violation | Action |
|-----------|--------|
| Empty group | Delete it, or investigate why skills aren't filing there |
| Loop detected | Manual review; break the cycle by removing one `is_a` |
| Multiple parents | Pick canonical parent; remove extras |
| Oversized group (>20) | Split into subgroups (Clara + Victor can propose) |
| Orphan group | Wire to appropriate domain via `is_a` |
| Duplicate skill | Merge into one; add aliases for variants |

---

## The Goal: A Proper Library

```
technical_engineering (was 3,092 skills piled here)
├── containerization_and_orchestration
│   ├── kubernetes (belongs_to)
│   ├── docker (belongs_to)
│   ├── helm (belongs_to)
│   └── ... 150 container skills
├── devops_and_automation  
│   ├── jenkins (belongs_to)
│   ├── terraform (belongs_to)
│   └── ... 80 devops skills
├── databases
│   ├── postgresql (belongs_to)
│   ├── mongodb (belongs_to)
│   └── ... 45 database skills
└── programming_languages
    ├── python (belongs_to)
    ├── java (belongs_to)
    └── ... 200 language skills
```

**Result:** Instead of 3,092 skills piled in one hall, they're distributed across specific sections. The taxonomy becomes **useful** for matching user skills to job requirements.

---

## Summary: The Seven Librarians

| Name | Role | Script/AI | Runs When |
|------|------|-----------|-----------|
| **Lucy** | Looks up if skill exists | Script (wf3020_lookup.py) | Always first |
| **Carl** | Creates new skill cards | Script (wf3020_create_entity.py) | Only if Lucy says "not found" |
| **Clara** | Picks the right hall/section | AI (qwen2.5:7b) | After Lucy (or Carl) |
| **Nate** | Navigates deeper, builds options | Script (wf3020_navigate.py) | After each Clara choice |
| **Victor** | Reviews new category proposals | AI (claude/gpt-4) | Only if Clara picks "NEW CATEGORY" |
| **Adam** | Files the card in its home | Script (wf3020_apply.py) | When Nate says "done" |
| **Quinn** | Audits taxonomy health | Script (wf3020_qa.py) | Post-batch or scheduled |

The system works when the library has **structure** (is_a connections). Without structure, everything piles up at the front door.

**Dynamic taxonomy:** The 5 top-level halls are not fixed. Clara can propose new ones, Victor approves or pushes back. The taxonomy grows organically.

**Quality enforcement:** Quinn audits after each batch, catching violations before they compound. Empty groups get pruned, oversized groups get split, orphans get wired.

---

## Where Do Skills Come From?

**WF3007 (Skill Cartographer)** handles extraction and atomization:

```
Job Posting → WF3007 C1: Fetch verbose skills
           → WF3007 C2: Extract Atomic Skills  ← ATOMIZATION HAPPENS HERE
           → WF3007 C3-C7: Grade, improve, review
           → WF3007 C8: Save as skill_atomic entity
           → Queue skill_atomic to WF3020
```

**WF3020 (Skill Taxonomy Engine)** receives already-atomized entities:

```
skill_atomic entity → Lucy → Carl → Clara ⟷ Nate → (Victor?) → Adam
```

*WF3020's C1 (Atomize) is vestigial — atomization is WF3007's job. WF3020 only classifies.*

---

## Actor ↔ Conversation Mapping

| Actor | Conversation | File |
|-------|--------------|------|
| Lucy | wf3020_c2_lookup | core/wave_runner/actors/wf3020_lookup.py |
| Carl | wf3020_c3_create | core/wave_runner/actors/wf3020_create_entity.py |
| Clara | wf3020_c4_classify | (AI prompt in DB) |
| Nate | wf3020_c5_navigate | core/wave_runner/actors/wf3020_navigate.py |
| Victor | wf3020_c4b_supervisor | (AI prompt in DB - claude/gpt-4) |
| Adam | wf3020_c6_apply | core/wave_runner/actors/wf3020_apply.py |
| Quinn | wf3020_c7_qa | core/wave_runner/actors/wf3020_qa.py |

**Notes on conversation numbering:**
- C1 (Atomize) is vestigial and should be removed. Atomization is WF3007's job.
- C7-C9 exist in the DB for duplicate handling but are **out of scope** for this document. They run separately when Quinn detects duplicates.

---

## Sandy's Review (2025-12-30)

**This is the best documentation we have.** The librarian metaphor is intuitive, the diagrams are clear, and the "What Went Wrong" section is honest and educational. Keep this pattern for other workflows.

### What's Covered Well

| Section | Verdict |
|---------|---------|
| Actor responsibilities | ✅ Clear division of labor |
| Navigation flow | ✅ Mermaid diagrams excellent |
| QA requirements | ✅ Comprehensive rules |
| Historical context | ✅ Honest about the flat hierarchy bug |
| Actor mapping table | ✅ Useful for debugging |

### What's Missing or Unclear

#### 1. GO BACK State Management

Nate offers "GO BACK" but how does he remember where Clara came from?

```
Clara: [a] technical_engineering
Clara: [b] databases  
Clara: [z] GO BACK  ← Go back to where? technical_engineering or TOP LEVEL?
```

**Need:** Nate must maintain a `path` stack: `["TOP", "technical_engineering", "databases"]`. When Clara says GO BACK, pop the stack.

**Implementation note:** This is conversation state. Does Nate persist it across loop iterations? (Same state-passing issue we fixed in WF3011.)

#### 2. Victor's Rejection Loop Limit

What if Clara and Victor disagree forever?

```
Clara: "I propose fintech_innovation"
Victor: "No, use compliance_risk"
Clara: "I still think fintech_innovation"
Victor: "No."
... infinite loop
```

**Need:** Max 2 rounds. After Victor rejects twice, escalate to human review or force Clara to pick an existing category.

#### 3. Who Creates the New Group?

Victor approves Clara's "fintech_innovation" proposal. Then what?

The diagram shows `V2 [Create new group] → ADAM`. But Adam's job is filing skills, not creating groups. 

**Need:** Either:
- Victor creates the group himself (add to Victor's responsibilities)
- Carl creates it (extend Carl's role to groups, not just skills)
- New actor "Greg the Group Maker" (probably overkill)

**Recommendation:** Victor creates the group as part of approval. He's already the authority.

#### 4. Quinn's Trigger Mechanism

> "Quinn runs after each batch"

How? Options:
- Workflow completion hook (daemon triggers Quinn when batch done)
- Scheduled cron (daily at 3am)
- Manual (`python scripts/run_quinn.py`)

**Need:** Specify. I'd recommend: automatic after every 100 workflow_runs complete, plus daily full audit.

#### 5. Error Handling

No mention of what happens when things fail:

| Failure | What Happens? |
|---------|---------------|
| Clara times out | Retry? Skip? Flag for human? |
| Adam hits constraint violation | Skill already filed elsewhere? |
| Lucy finds multiple fuzzy matches | Pick closest? Ask Clara to disambiguate? |
| Nate queries empty children | Should never happen if Quinn runs, but... |

**Need:** Error handling section. At minimum: "On any error, mark workflow_run as failed, log details, continue with next skill."

#### 6. Race Condition in Lucy

Two workflow_runs for the same skill start simultaneously:
```
Run A: Lucy checks "kubernetes" → not found
Run B: Lucy checks "kubernetes" → not found
Run A: Carl creates kubernetes (entity_id: 100)
Run B: Carl creates kubernetes (entity_id: 101) ← DUPLICATE
```

**Need:** Carl's INSERT must use `ON CONFLICT DO NOTHING RETURNING` or similar. If conflict, fetch existing entity_id.

(This is already standard practice, but worth documenting.)

#### 7. Depth Limit

Can Clara navigate 50 levels deep? Probably not intended.

**Need:** Add to Nate: `if depth > 10: force PLACE HERE`. No taxonomy needs 10+ levels.

#### 8. The Loop Mechanics (Framework Concern)

Clara ↔ Nate is a loop. This is the same pattern that broke WF3010 and WF3011. The story assumes it works, but:

- Does `parent_response` flow correctly from Nate back to Clara?
- Does Nate's state (`options`, `location`, `path`) survive the loop?

**Need:** Explicit note that this depends on the loop state fix from Dec 28. If that fix isn't generic, WF3020 will hit the same bug.

#### 9. Display Name Learning

Lucy checks `entity_names` for aliases. But we also implemented observed capitalization learning (Dec 26). Does Lucy use that?

```sql
-- Lucy should also check observed display names
SELECT entity_id FROM entity_names 
WHERE name_type IN ('alias', 'verbatim', 'observed')
AND LOWER(display_name) = LOWER($skill_name);
```

**Need:** Confirm Lucy's query includes all name_types, not just 'alias'.

### Minor Nits

1. **"5 main halls"** - Doc says Clara can propose new halls, but also treats 5 as fixed. Pick one. (I'd say: 5 are default, Clara can propose more, Victor approves.)

2. **C1 Atomize** - Doc says "vestigial, should be removed" but also "kept for backwards compatibility." Just remove it. Dead code is confusing.

3. **C7-C9** - Mentioned at the end but not explained. Either document them or explicitly say "out of scope for this doc."

### Summary

| Category | Status |
|----------|--------|
| Core flow | ✅ Documented |
| QA rules | ✅ Documented |
| Error handling | ❌ Missing |
| GO BACK mechanics | ⚠️ Incomplete |
| Victor's group creation | ⚠️ Unclear |
| Loop state management | ⚠️ Assumed working |
| Race conditions | ⚠️ Implicit |

**Recommendation:** Add a "Error Handling" section and clarify GO BACK/Victor flow. The rest is minor.

This doc is already better than 90% of workflow documentation I've seen. Ship it, iterate.

ℶ Sandy

---

## Arden's Update (2025-12-30): The Chain Experiment

### What We Tested

We conducted a model interview process to find the best classifier for Clara. Tested 11 Ollama models with a consistent skill classification task.

**Winner: gemma2:latest** — Correctly classified in 4 tries vs 10-50 for other models.

| Model | Tries to Correct Answer | Notes |
|-------|------------------------|-------|
| gemma2:latest | 4 | Clear winner |
| qwen2.5:7b | 12 | Original choice, decent |
| llama3.2:latest | 10 | Acceptable |
| mistral:latest | 50+ | Never got it right |
| phi3:latest | 50+ | Kept hallucinating |

**Recommendation:** Update Clara to use `gemma2:latest`, not `qwen2.5:7b`.

### The Chain Format Idea

Instead of multi-turn navigation (Clara picks `[a]`, Nate builds options, Clara picks `[b]`, etc.), we tested a **one-shot chain format**:

```
Skill: homomorphic_encryption

Classify into: technical_engineering->cryptography->applied_cryptographic_techniques
```

Clara returns the full taxonomy path in one response. No navigation loop needed.

**Advantages:**
- **Speed:** One LLM call vs 3-5 navigation turns
- **Simplicity:** No Nate, no state management, no GO BACK logic
- **Works:** gemma2 reliably produces valid chains

**We built it:** `wf3020_apply_chain.py` parses chains and auto-creates missing groups.

### Why We Didn't Ship It

Ran 50 skills through the chain approach. Results:

| Metric | Value |
|--------|-------|
| Skills processed | 56 |
| Successfully placed | 39 (70%) |
| Groups created | 69 |

**The problem:** 69 new groups for 56 skills. That's 1.2 groups per skill.

Navigation would create far fewer groups because Clara **picks from existing options**. With chains, Clara **invents names freely**, creating semantic duplicates:

| Chain Approach Created | Should Have Used |
|-----------------------|------------------|
| `audit_and_assurance` | `audit` (already existed) |
| `software_development` | `software` (already existed) |
| `api_development_and_integration` | `api_development` (already existed) |
| `ai_use_cases_development` | `ai_use_case_development` (typo!) |

We tried fuzzy matching to catch duplicates, but:

```sql
SELECT similarity('audit', 'audit_and_assurance');  -- 0.33
SELECT similarity('audit', 'audio');                 -- 0.50 (false positive!)
```

String similarity can't reliably distinguish semantic duplicates from false matches.

### The Core Insight

**Taxonomy quality requires constrained choices.**

When Clara sees existing options and must pick one, she can't create duplicates. When Clara freely generates names, she will create variations that are semantically identical but lexically different.

The navigation approach isn't slower because it's poorly designed — it's slower because **that's the cost of quality control**.

### When Chains Might Work

Chains could work if:
1. The taxonomy is already complete (no new groups needed)
2. We accept ongoing duplicate cleanup (Quinn merges similar groups)
3. Clara is prompted with existing group names to choose from (hybrid)

For now, we're implementing navigation as designed. The chain approach is documented here for future reference.

### Other Learnings

#### Entity ID Contract Bug

When we tested chains, 16 of 18 "failed" skills actually succeeded — but on the **wrong entity**.

**What happened:**
1. We queued `skill` entities (e.g., entity_id 37345)
2. Lucy found a matching `skill_atomic` with same name (entity_id 31888)
3. Lucy returned entity_id 31888
4. Classification was applied to 31888, not 37345

**Root cause:** Lucy's job is to check if a skill exists, but she returned a *different entity* than the one queued.

**Fix needed:** Lucy must return the original `subject_id` from the queue when that's the entity being classified. Only return a different entity_id if we're deduplicating.

#### skill vs skill_atomic

The codebase has two entity types for skills:
- `skill_atomic` — From WF3007 extraction (lowercase, underscored)
- `skill` — Sometimes created separately (original casing)

This distinction caused the entity ID bug above. We need to:
1. Decide which type is canonical
2. Ensure WF3020 processes the correct type
3. Possibly merge/alias the duplicates

#### Invalid Root Categories

gemma2 occasionally returns chains starting with categories we don't have:

```
business_processes->process_management->process_improvement
```

`business_processes` isn't in our 5 root categories. Options:
1. Add a 6th root category
2. Map `business_processes` → closest existing root
3. Reject and retry with feedback

For now, the script rejects invalid roots. May need a mapping table.

ℶ Arden

---

## Implementation Specs

**For implementation details, see:** [WF3020_implementation.md](WF3020_implementation.md)

That document contains:
- Database schema (conversations, branch conditions, instruction_steps)
- Actor input/output contracts
- SQL queries used by each actor
- Branch condition reference table
- State flow diagrams
- Testing checklist
- Runbook for operations

This story document focuses on the **conceptual "why"** — the implementation doc covers the **technical "how"**.

ℶ Sandy + Arden
