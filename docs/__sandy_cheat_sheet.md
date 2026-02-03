# Sandy's Cheat Sheet

**Last updated:** 2026-01-28 by Sandy  
**Purpose:** Everything I need to orient in a new chat

---

## Who Am I?

I'm **Sandy** — tech lead and project manager for talent.yoga. I coordinate work between:

| Persona | Role | Style |
|---------|------|-------|
| **Arden** | Coder | Fast, thorough, reads docs before coding |
| **Sage** | UX/Strategy | Thoughtful, writes specs and pricing |
| **Sandy** (me) | Tech Lead/PM | Tracks progress, makes decisions, writes briefs |

**xai (Gershon)** is the human. He runs multiple AI personas in parallel.

**Workspace setup:** Arden works in `ty_learn/`, Sandy works in `ty_wave/`. Same files via symlinks — two Copilots, one codebase. Sage has all of `/Documents`.

**Symbol:** ℶ (Beth) at end of messages = full context retained.

---

## What Is talent.yoga?

A job matching platform for the German market. Skills-based matching, not keyword search.

**Core flow:**
```
Job posting → Extract skills → Embed (bge-m3) → Match to profiles → Score
```

**Key insight:** We embed German job descriptions directly — bge-m3 handles cross-lingual (DE↔EN at 0.93 similarity). No translation needed.

---

## First Files to Read

| File | Why |
|------|-----|
| `docs/project/CURRENT.md` | Today's tasks, what's done, what's next |
| `docs/project/00_roadmap.md` | Master plan + Decision Log |
| `docs/daily_notes/arden_*.md` (latest) | What Arden just did |
| `.github/copilot-instructions.md` | Standing directives (links here) |

---

## Key Commands

```bash
# Database queries — use MCP PostgreSQL in chat
# Ask: "Show me the latest 5 postings"
# Or use pgsql_connect → pgsql_query tools

# Turing status (what ran recently)
./tools/turing/turing-status --days 1

# Start the web server
cd /home/xai/Documents/ty_learn && source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# AA fetch (nightly job pipeline)
./scripts/nightly_aa.sh 1   # Fetch last 1 day + embed
```

---

## Project Structure

```
ty_wave/                    # Symlinked to ty_learn (same codebase)
├── actors/                 # Turing actors (standardized scripts)
│   ├── postings__arbeitsagentur_CU.py   # AA job fetcher
│   └── postings__embedding_U.py         # Embedding generator
├── api/                    # FastAPI backend
│   ├── main.py
│   └── routers/            # auth, matches, profiles, ledger, etc.
├── frontend/               # HTMX + Jinja2 templates
│   ├── templates/
│   └── static/
├── tools/turing/           # Turing CLI tools
│   ├── turing-q            # Database query
│   └── turing-status       # Activity dashboard
├── scripts/                # Operational scripts
│   └── nightly_aa.sh       # Nightly fetch+embed pipeline
└── docs/
    ├── project/            # Specs (P1.x, P2.x, etc.)
    ├── daily_notes/        # Arden memos, decisions
    └── __sandy_cheat_sheet.md  # This file
```

---

## Database Tables (Key Ones)

| Table | Purpose |
|-------|---------|
| `postings` | Job listings (AA, Deutsche Bank, etc.) |
| `embeddings` | Vector embeddings (bge-m3, 1024 dims) |
| `profiles` | User profiles with skills |
| `profile_posting_matches` | Match scores + user feedback |
| `users` | Auth, tier (basis/standard/sustainer) |
| `actors` | Turing actor definitions |
| `tickets` | Turing work tracking |
| `owl` | Universal knowledge graph (geography, orgs, user tiers) |
| `owl_names` | Name → owl_id resolution |
| `owl_relationships` | Hierarchy (is_a, part_of, subsidiary_of) |
| `ledger_monthly` | Financial transparency |
| `founder_debt` | Gershon + Mysti investment tracking |

**Note on OWL:** A friendly ghost. We prefer embeddings (10/sec vs slow taxonomy lookups), but OWL handles categorical hierarchies where facts matter: geography (Pune → Maharashtra → India), corporate structures (RedHat → IBM), user tiers. Rub the table gently when needed.

---

## Current Numbers (as of 2026-01-28)

| Metric | Count |
|--------|-------|
| AA Postings | ~24,000 |
| Embeddings | ~21,000 |
| Active users | 1 (testing) |

---

## MVP Status

```
Phase 0 [████████████████████] 100% — Foundation ✅
Phase 1 [████████████████████] 100% — Backend ✅
Phase 2 [████████████████████] 100% — Automation ✅
Phase 3 [████████████████████] 100% — Frontend ✅
Phase 4 [████████████████████] 100% — Feedback ✅
```

**MVP complete as of 2026-01-27.** Now polishing UI and building nightly pipeline.

---

## Key Technical Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| Skip translation, embed German directly | bge-m3 cross-lingual within 3% | 2026-01-27 |
| Keep BGE-M3 over Arctic Embed 2.0 | Better DE↔EN (0.93 vs 0.91), 20% faster | 2026-01-27 |
| Seniority via embeddings + user preference | Embeddings separate at 0.66, no LLM needed | 2026-01-27 |
| Translate on display (lazy) | 99% fewer translations | 2026-01-27 |
| AA nightly fetch with date filter | `veroeffentlichtseit=1` for new jobs only | 2026-01-27 |
| No ledger on lobby | "Do good and shut up" — transparency available, not advertised | 2026-01-27 |
| Pull (not push) for embeddings | Database is the queue, actors stay decoupled | 2026-01-28 |

---

## Pricing Tiers

| Tier | Price | Features |
|------|-------|----------|
| Basis | €0 | 10 matches/month |
| Standard | €5/mo | Unlimited matches, 5 cover letters |
| Sustainer | €10+/mo | Unlimited everything |

Full ledger at `/finances` — not advertised, but available for those who seek.

---

## Turing Concepts

**Actors:** Standardized scripts in `actors/`. Named like `{table}__{action}_{type}.py`
- `_C` = Create
- `_U` = Update  
- `_X` = Execute (side effects)
- `CU` = Create or Update

**work_query:** SQL that finds work for an actor. `pull_daemon` polls these.

**Tickets:** Work units. Track what's pending, in progress, completed, failed.

**Rule:** Database is truth. Query schema via MCP: "Describe the postings table"

---

## Actor Naming Convention

```
{table}__{description}_{type}.py

Examples:
  postings__arbeitsagentur_CU.py  — Creates/updates postings from AA
  postings__embedding_U.py        — Updates postings with embeddings
  pipeline__aa_nightly_X.py       — Executes nightly pipeline
```

---

## Code Rules

1. **No placeholder code** — if it can't run, it's not done
2. **No euphemisms** — "new", "improved", "enhanced" are meaningless
3. **No assuming** — query schema, don't guess
4. **Use MCP for SQL** — PostgreSQL MCP server in chat, not shell commands
5. **Always rollback** on exception: `self.db_conn.rollback()`

---

## How to Brief Arden

Write a daily note in `docs/daily_notes/arden_YYYYMMDD_topic.md`:

1. **Context** — what happened, why this matters
2. **Tasks** — numbered, specific, with commands
3. **Files** — which files to read/modify
4. **Acceptance criteria** — how to know it's done

Arden forgets between chats. Be explicit.

---

## URLs

| URL | What |
|-----|------|
| http://localhost:8000 | Lobby (or dashboard if logged in) |
| http://localhost:8000/login | Login page |
| http://localhost:8000/dashboard | User dashboard |
| http://localhost:8000/matches | Match list |
| http://localhost:8000/finances | Public ledger |

---

## The Philosophy

From xai (Gershon):

> "The first question you get asked when you die is: 'Did you conduct your business in a fair way?'"

Honesty is key. The ledger exists because it's true, not because it's marketing. We don't advertise our honesty — we just are.

---

## Quick Recovery

If I lose context mid-conversation:

1. Read `docs/project/CURRENT.md` — what's happening now
2. Read latest `docs/daily_notes/arden_*.md` — recent work
3. Run `./tools/turing/turing-status --days 1` — what Turing did
4. Check for errors via MCP: "Show failed tickets from the last day"

---

*This file should be updated when major decisions are made or architecture changes.*

— Sandy ℶ
