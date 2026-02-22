#!/usr/bin/env python3
"""
generate_fetch_docs.py — Auto-generate turing_fetch pipeline documentation.

Introspects:
  1. scripts/turing_fetch.sh   — step ordering, cron schedule, CLI args
  2. actors DB table           — work_query, batch_size, scale_limit, priority
  3. Python actor files        — docstrings, SQL queries, imports
  4. DB views / postings_for_matching — schema dependencies

Output: docs/workflows/turing_fetch_pipeline.md

Usage:
    python3 scripts/generate_fetch_docs.py          # generate docs
    python3 scripts/generate_fetch_docs.py --check   # exit 1 if docs are stale
"""
import ast
import datetime
import hashlib
import os
import re
import sys
import textwrap

# ── Project root ──────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

OUTPUT_PATH = os.path.join(ROOT, "docs", "workflows", "turing_fetch_pipeline.md")
FETCH_SCRIPT = os.path.join(ROOT, "scripts", "turing_fetch.sh")

# ── DB helper ─────────────────────────────────────────────────

def get_db():
    """Return a psycopg2 connection (dict cursor)."""
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(
        host="localhost",
        dbname="turing",
        user="base_admin",
        password="A40ytN2UEGc_tDliTLtMF-WyKOV_VslrULoLxmUZl38",
    )
    conn.autocommit = True
    return conn


# ╔════════════════════════════════════════════════════════════════════╗
# ║  1. PARSE turing_fetch.sh                                        ║
# ╚════════════════════════════════════════════════════════════════════╝

def parse_fetch_script():
    """Extract metadata from turing_fetch.sh."""
    with open(FETCH_SCRIPT) as f:
        text = f.read()
    lines = text.split("\n")
    info = {
        "total_lines": len(lines),
        "cron": "",
        "mermaid": "",
        "steps": [],
    }

    # Cron line
    for line in lines:
        if line.startswith("# Cron:"):
            info["cron"] = line.replace("# Cron:", "").strip()
            break

    # Embedded mermaid chart
    m = re.search(r"```mermaid\n(.*?)```", text, re.DOTALL)
    if m:
        info["mermaid"] = m.group(1).strip()

    # Extract step markers:  ts "[1/5] ..." or ts "[3b/5] ..." or ts "[post] ..."
    step_pat = re.compile(
        r'ts\s+"'                           # ts "
        r'\[(\w+(?:/\d+)?)\]\s*'            # [1/5] or [post]
        r'(.*?)"',                           # description"
        re.DOTALL,
    )
    for m in step_pat.finditer(text):
        label = m.group(1).strip()
        desc = m.group(2).strip().rstrip(".")
        info["steps"].append((label, desc))

    return info


# ╔════════════════════════════════════════════════════════════════════╗
# ║  2. QUERY DB FOR ACTOR / TASK_TYPE CONFIG                        ║
# ╚════════════════════════════════════════════════════════════════════╝

def query_actor_configs():
    """Return list of dicts for all enabled pull/bulk actors."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            t.task_type_id,
            t.task_type_name,
            t.script_path,
            t.work_query,
            t.batch_size,
            t.scale_limit,
            t.priority,
            t.execution_type,
            t.enabled
        FROM task_types t
        WHERE t.enabled = true
          AND t.work_query IS NOT NULL
        ORDER BY t.priority DESC
    """)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def query_view_definition(view_name):
    """Return the CREATE VIEW SQL for a given view."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT pg_get_viewdef(%s, true)", (view_name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else "(view not found)"


def query_db_stats():
    """Return key counts for the pipeline overview section."""
    conn = get_db()
    cur = conn.cursor()
    stats = {}

    queries = {
        "total_postings": "SELECT COUNT(*) FROM postings",
        "active_postings": "SELECT COUNT(*) FROM postings WHERE COALESCE(invalidated, false) = false",
        "with_description": "SELECT COUNT(*) FROM postings WHERE job_description IS NOT NULL AND LENGTH(job_description) > 150",
        "with_summary": "SELECT COUNT(*) FROM postings WHERE extracted_summary IS NOT NULL",
        "embeddable": "SELECT COUNT(*) FROM postings_for_matching",
        "total_embeddings": "SELECT COUNT(*) FROM embeddings",
        "berufenet_classified": "SELECT COUNT(*) FROM postings WHERE berufenet_id IS NOT NULL AND COALESCE(invalidated, false) = false",
        "owl_names_count": "SELECT COUNT(*) FROM owl_names WHERE confidence_source IN ('human','import','llm_confirmed')",
        "owl_pending_count": "SELECT COUNT(*) FROM owl_pending WHERE status = 'pending'",
        "source_aa": "SELECT COUNT(*) FROM postings WHERE source = 'arbeitsagentur' AND COALESCE(invalidated, false) = false",
        "source_db": "SELECT COUNT(*) FROM postings WHERE source = 'deutsche_bank' AND COALESCE(invalidated, false) = false",
    }
    for key, sql in queries.items():
        try:
            cur.execute(sql)
            stats[key] = cur.fetchone()[0]
        except Exception:
            stats[key] = "?"
            conn.rollback()

    conn.close()
    return stats


# ╔════════════════════════════════════════════════════════════════════╗
# ║  3. INTROSPECT PYTHON ACTOR FILES                                ║
# ╚════════════════════════════════════════════════════════════════════╝

# Mapping of pipeline component → source file(s) for introspection
ACTOR_FILES = {
    "AA Fetch": "actors/postings__arbeitsagentur_CU.py",
    "DB Fetch": "actors/postings__deutsche_bank_CU.py",
    "Berufenet Classification": "actors/postings__berufenet_U.py",
    "Geo State Resolution": "actors/postings__geo_state_U.py",
    "Embedding Generation": "actors/postings__embedding_U.py",
    "Description Backfill": "actors/postings__job_description_U.py",
    "External Partners": "actors/postings__external_partners_U.py",
    "Extracted Summary": "actors/postings__extracted_summary_U.py",
    "Turing Daemon": "core/turing_daemon.py",
    "Description Retry": "scripts/berufenet_description_retry.py",
    "Auto-Triage": "scripts/bulk_auto_triage.py",
    "Domain Gate": "tools/populate_domain_gate.py",
    "Pipeline Report": "scripts/pipeline_report.py",
    "Demand Snapshot": "scripts/compute_demand_snapshot.py",
    "Profession Similarity": "scripts/compute_profession_similarity.py",
}


def introspect_python_file(filepath):
    """Extract docstring, key SQL, imports, classes from a Python file."""
    if not os.path.exists(filepath):
        return {"docstring": f"(file not found: {filepath})", "sql": [], "imports": [], "classes": []}

    with open(filepath) as f:
        source = f.read()

    result = {
        "docstring": "",
        "sql": [],
        "imports": [],
        "classes": [],
        "line_count": source.count("\n") + 1,
    }

    # AST parse for docstring + imports + class names
    try:
        tree = ast.parse(source)
        result["docstring"] = ast.get_docstring(tree) or ""
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    result["imports"].append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
            elif isinstance(node, ast.ClassDef):
                result["classes"].append(node.name)
    except SyntaxError:
        pass

    # Extract SQL patterns (triple-quoted strings containing SQL keywords)
    sql_pat = re.compile(
        r"(?:'''|\"\"\")(.*?)(?:'''|\"\"\")",
        re.DOTALL,
    )
    for m in sql_pat.finditer(source):
        block = m.group(1).strip()
        # Only include if it looks like SQL
        sql_keywords = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "WITH ")
        if any(block.upper().startswith(kw) for kw in sql_keywords):
            # Truncate very long queries
            if len(block) > 500:
                block = block[:500] + "\n-- ... (truncated)"
            result["sql"].append(block)

    return result


# ╔════════════════════════════════════════════════════════════════════╗
# ║  4. GENERATE MARKDOWN                                            ║
# ╚════════════════════════════════════════════════════════════════════╝

def fmt_num(n):
    """Format a number with comma separators, or return '?' for non-integers."""
    if isinstance(n, int):
        return f"{n:,}"
    return str(n)


def generate_docs():
    """Build the full markdown documentation string."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    script_info = parse_fetch_script()
    actor_configs = query_actor_configs()
    view_def = query_view_definition("postings_for_matching")
    stats = query_db_stats()

    sections = []

    # ── Header ────────────────────────────────────────────────
    sections.append(textwrap.dedent(f"""\
        # Turing Fetch Pipeline — Technical Reference

        > **Auto-generated** by `scripts/generate_fetch_docs.py` — do not edit by hand.
        > Regenerated on every git commit via `.git/hooks/post-commit`.

        **Generated:** {now}
        **Script:** `scripts/turing_fetch.sh` ({script_info['total_lines']} lines)
        **Schedule:** `{script_info['cron']}`
        **Log:** `logs/turing_fetch.log`

        ---
    """))

    # ── Quick Stats ───────────────────────────────────────────
    sections.append(textwrap.dedent(f"""\
        ## Quick Stats (at generation time)

        | Metric | Count |
        |--------|------:|
        | Total postings | {fmt_num(stats.get('total_postings'))} |
        | Active postings | {fmt_num(stats.get('active_postings'))} |
        | — Arbeitsagentur | {fmt_num(stats.get('source_aa'))} |
        | — Deutsche Bank | {fmt_num(stats.get('source_db'))} |
        | With description (>150 chars) | {fmt_num(stats.get('with_description'))} |
        | With extracted summary | {fmt_num(stats.get('with_summary'))} |
        | Embeddable (postings_for_matching) | {fmt_num(stats.get('embeddable'))} |
        | Total embeddings | {fmt_num(stats.get('total_embeddings'))} |
        | Berufenet classified | {fmt_num(stats.get('berufenet_classified'))} |
        | OWL vocabulary (confirmed) | {fmt_num(stats.get('owl_names_count'))} |
        | OWL pending triage | {fmt_num(stats.get('owl_pending_count'))} |

        ---
    """))

    # ── Table of Contents ─────────────────────────────────────
    toc_lines = ["## Table of Contents\n"]
    toc_entries = [
        ("Pipeline Overview", "pipeline-overview"),
        ("Master Flowchart", "master-flowchart"),
        ("Pipeline Steps", "pipeline-steps"),
        ("Actor Configuration (DB)", "actor-configuration-db"),
        ("Key Views & Functions", "key-views--functions"),
        ("Troubleshooting", "troubleshooting"),
    ]
    # Add actor deep dives
    for name in ACTOR_FILES:
        anchor = name.lower().replace(" ", "-").replace("(", "").replace(")", "")
        toc_entries.append((name, anchor))

    for i, (title, anchor) in enumerate(toc_entries, 1):
        toc_lines.append(f"{i}. [{title}](#{anchor})")
    toc_lines.append("\n---\n")
    sections.append("\n".join(toc_lines))

    # ── Pipeline Overview ─────────────────────────────────────
    sections.append(textwrap.dedent("""\
        ## Pipeline Overview

        The `turing_fetch` pipeline is the nightly batch orchestrator that:

        1. **Fetches** job postings from external sources (Arbeitsagentur API, Deutsche Bank API)
        2. **Classifies** each posting with Berufenet occupation codes (OWL lookup → embedding → LLM)
        3. **Enriches** with domain categories, geo state, qualification levels
        4. **Backfills** missing job descriptions via web scraping (VPN-rotated)
        5. **Embeds** posting text for semantic matching (bge-m3 via Ollama)
        6. **Certifies** data integrity (100% embedding coverage, zero hash corruption)
        7. **Computes** market intelligence (demand snapshots, profession similarity)

        ### CLI Usage

        ```bash
        # Standard nightly run (cron)
        ./scripts/turing_fetch.sh 1 25000 force

        # Manual: last 7 days, max 5000 per source
        ./scripts/turing_fetch.sh 7 5000

        # Status check (no pipeline run)
        ./scripts/turing_fetch.sh status

        # Debug mode (process info, connections, resources)
        ./scripts/turing_fetch.sh debug

        # Tail latest backfill log
        ./scripts/turing_fetch.sh tail
        ```

        | Argument | Default | Description |
        |----------|---------|-------------|
        | `$1` (since) | `1` | Fetch postings from the last N days |
        | `$2` (max_jobs) | `1000` | Max postings per source/city |
        | `$3` (force) | _(none)_ | Pass `force` to skip preflight checks |

        ---
    """))

    # ── Master Flowchart ──────────────────────────────────────
    sections.append("## Master Flowchart\n\n")
    sections.append("```mermaid\n")
    sections.append(textwrap.dedent("""\
        flowchart TD
            subgraph "Step 0: PREFLIGHT"
                P0[Import smoke tests]
            end

            subgraph "Step 1: FETCH"
                S1A["🇩🇪 AA API\\n16 Bundesländer\\n--no-descriptions"]
                S1B["💼 Deutsche Bank API"]
            end

            subgraph "Step 3: BERUFENET"
                S3A["🦉 Phase 1: OWL lookup\\n(instant, vocabulary match)"]
                S3B["📐 Phase 2: Embed + LLM\\n(~14/sec, GPU-bound)"]
                S3C["🤖 Phase 3: Auto-triage\\n(LLM picks best candidate)"]
                S3A --> S3B --> S3C
            end

            subgraph "Step 3b-d: CLASSIFY"
                S3b["🗺️ Domain gate cascade\\n(KldB → keyword → LLM)"]
                S3c["📍 Geo state resolution\\n(city → OWL → Bundesland)"]
                S3d["🎓 Qualification backfill\\n(beruf → KldB → qual level)"]
                S3b --> S3c --> S3d
            end

            subgraph "Step 4: ENRICH"
                S4["⚙️ Turing daemon\\n(parallel bulk actors)"]
                S4a["job_description_backfill\\nprio:60, scale:20"]
                S4b["external_partner_scraper\\nprio:55"]
                S4c["extracted_summary\\nprio:50, LLM"]
                S4d["embedding_generator\\nprio:30, scale:20"]
                S4e["owl_pending_auto_triage\\nprio:10"]
                S4f["domain_gate_classifier\\nprio:0"]
                S4 --> S4a & S4b & S4c & S4d & S4e & S4f
            end

            subgraph "Step 5: SECOND PASS"
                S5["🔄 Berufenet description retry\\n(title+desc → LLM → ~25% yield)"]
            end

            subgraph "Post-Pipeline"
                PP1["Embedding sweep\\n(catch stale from enrichment)"]
                PP2["📊 Data certification\\n(pipeline_report.py)"]
                PP3["📈 Demand snapshot"]
                PP4["🔗 Profession similarity"]
                PP5["📲 Notifications\\n(ntfy + Signal + pipeline_health)"]
                PP1 --> PP2 --> PP3 --> PP4 --> PP5
            end

            P0 --> S1A --> S1B --> S3A
            S3C --> S3b
            S3d --> S4
            S4 --> S5
            S5 --> PP1
    """))
    sections.append("```\n\n---\n")

    # ── Pipeline Steps ────────────────────────────────────────
    sections.append("## Pipeline Steps\n\n")
    sections.append("Extracted from `scripts/turing_fetch.sh` step markers:\n\n")
    sections.append("| Step | Description |\n|------|-------------|\n")
    for label, desc in script_info["steps"]:
        sections.append(f"| `[{label}]` | {desc} |\n")
    sections.append("\n---\n")

    # ── Actor Configuration ───────────────────────────────────
    sections.append("## Actor Configuration (DB)\n\n")
    sections.append("Live configuration from `task_types` table (enabled, with work_query):\n\n")
    sections.append("| TT# | Name | Script | Prio | Batch | Scale | Exec Type |\n")
    sections.append("|-----|------|--------|-----:|------:|------:|-----------|\n")
    for ac in actor_configs:
        tt = ac.get("task_type_id", "?")
        name = ac.get("task_type_name", "?")
        script = ac.get("script_path", "?") or "—"
        prio = ac.get("priority", "?")
        batch = ac.get("batch_size", "?")
        scale = ac.get("scale_limit", "?") or "—"
        exec_type = ac.get("execution_type", "?")
        sections.append(f"| {tt} | {name} | `{script}` | {prio} | {batch} | {scale} | {exec_type} |\n")

    sections.append("\n<details><summary>Work queries (click to expand)</summary>\n\n")
    for ac in actor_configs:
        wq = ac.get("work_query", "") or ""
        if wq.strip():
            name = ac.get("task_type_name", "?")
            sections.append(f"**{name}** (TT#{ac.get('task_type_id', '?')}):\n```sql\n{wq.strip()}\n```\n\n")
    sections.append("</details>\n\n---\n")

    # ── Key Views & Functions ─────────────────────────────────
    sections.append("## Key Views & Functions\n\n")
    sections.append("### `postings_for_matching` (view)\n\n")
    sections.append("The canonical view for matching-eligible postings. "
                     "Embeddings are generated from `match_text`.\n\n")
    sections.append(f"```sql\n{view_def}\n```\n\n")
    sections.append("**Key field:** `match_text = COALESCE(extracted_summary, job_description)` — "
                     "prefers LLM summary (Deutsche Bank) but falls back to raw description (AA).\n\n")

    sections.append("### `normalize_text_python()` (PL/pgSQL)\n\n")
    sections.append(textwrap.dedent("""\
        Server-side text normalization used for content-addressed embedding storage.
        Strips 29 unicode whitespace characters (broader than Python's `.strip()`) + lowercases.

        The text hash formula:
        ```sql
        LEFT(ENCODE(SHA256(CONVERT_TO(normalize_text_python(text), 'UTF8')), 'hex'), 32)
        ```

        This eliminates Python/PostgreSQL normalization drift that previously caused
        duplicate embeddings and false "stale" reports.

    """))

    sections.append("### Tables & Dependencies\n\n")
    sections.append(textwrap.dedent("""\
        | Table/View | Read by | Written by |
        |-----------|---------|------------|
        | `postings` | All actors | AA fetch, DB fetch, berufenet, geo_state, job_desc, external_partners, extracted_summary, domain_gate, auto_triage, description_retry, qual backfill |
        | `postings_for_matching` (view) | embedding, pipeline_report | _(derived from postings)_ |
        | `embeddings` | embedding (conflict), pipeline_report, profession_similarity | embedding |
        | `owl_names` | berufenet (lookup), geo_state (geo) | berufenet (synonyms), auto_triage, description_retry |
        | `owl` | berufenet (entity), external_partners (prefix map) | — |
        | `owl_pending` | auto_triage, description_retry | berufenet (escalation) |
        | `berufenet` | domain_gate, demand_snapshot, profession_similarity, qual backfill | — |
        | `berufenet_synonyms` | domain_gate, qual backfill | — |
        | `demand_snapshot` | — | compute_demand_snapshot |
        | `profession_similarity` | — | compute_profession_similarity |
        | `tickets` | — | AA fetch, DB fetch, turing_daemon |

    """))
    sections.append("---\n")

    # ── Per-Actor Deep Dives ──────────────────────────────────
    # Static knowledge enriched by introspection
    ACTOR_DETAILS = {
        "AA Fetch": {
            "purpose": "Fetches job postings from the Arbeitsagentur (German federal job board) REST API. "
                       "Covers 16 Bundesländer. Source actor — creates subjects, not triggered by work_query.",
            "reads": "`arbeitsagentur REST API`, `postings` (conflict check on `external_job_id`)",
            "writes": "`postings` (INSERT/UPSERT), `tickets` (audit)",
            "normalization": "None — raw API data inserted as-is.",
            "dependencies": "Arbeitsagentur REST API (public key `jobboerse-jobsuche`), `requests`, `BeautifulSoup`",
            "failure_mode": "API rate limits → exponential backoff. Partial results committed (per-state batches).",
            "data_contract": "`external_job_id` unique per active posting. `last_seen_at` refreshed on every fetch.",
        },
        "DB Fetch": {
            "purpose": "Fetches job postings from the Deutsche Bank careers API (Beesite/Workday). "
                       "Source actor — triggered by cron, not work_query. Auto-invalidates postings not seen for 2+ days.",
            "reads": "`Deutsche Bank API`, `postings` (existing check by `external_job_id`)",
            "writes": "`postings` (INSERT/UPDATE/invalidate), `tickets` (audit)",
            "normalization": "`sanitize_for_storage()` from `core.text_utils` applied to descriptions.",
            "dependencies": "Deutsche Bank API (HTTP JSON), `requests`, `BeautifulSoup`, `core.text_utils`",
            "failure_mode": "Safety threshold: won't invalidate >50% of existing postings (API outage protection).",
            "data_contract": "`STALENESS_DAYS = 2`. Postings gone from API for 2+ days get `invalidated = true`.",
        },
        "Berufenet Classification": {
            "purpose": "Maps job titles to German occupational classification (Berufenet ID, KldB code, qualification level). "
                       "4-phase architecture: OWL lookup → Embedding discovery → LLM verification → Human triage.",
            "reads": "`postings` (job_title), `owl_names` + `owl` (vocabulary), `berufenet_full.parquet` + embeddings (pre-computed)",
            "writes": "`postings` (berufenet_id, berufenet_name, berufenet_kldb, qualification_level, berufenet_verified), "
                      "`owl_names` (new synonyms), `owl_pending` (escalations)",
            "normalization": "`clean_job_title()` from `lib.berufenet_matching` — strips gender markers, brackets, whitespace. "
                            "Three-tier OWL resolution: unanimous → majority → reject.",
            "dependencies": "Ollama (`bge-m3:567m` embeddings, LLM for verification), `numpy`, `pandas`, `lib.berufenet_matching`",
            "failure_mode": "Phase 1 (OWL) never fails. Phase 2 degrades gracefully — unmatched titles go to `owl_pending`. "
                           "GPU saturation throttles at `LLM_WORKERS` concurrent.",
            "data_contract": "`THRESHOLD_AUTO_ACCEPT = 0.85` (skip LLM). `THRESHOLD_LLM_VERIFY = 0.70` (ask LLM). "
                            "New confirmed synonyms auto-add to OWL (self-learning system).",
        },
        "Geo State Resolution": {
            "purpose": "Resolves `location_state` (Bundesland) for postings that have `location_city` but no state. "
                       "Uses OWL geography hierarchy with GeoNames fallback.",
            "reads": "`postings` (location_city), `owl_names` + `owl` (geography), `data/DE/DE.txt` (GeoNames)",
            "writes": "`postings.location_state`",
            "normalization": "Comma-stripping (\"Berlin, Mitte\" → \"Berlin\"), city-state detection (Berlin, Hamburg, Bremen).",
            "dependencies": "None external. Uses `data/DE/DE.txt` (GeoNames offline file).",
            "failure_mode": "Skips ambiguous cities. ~82% resolution rate. No API calls — safe to retry.",
            "data_contract": "Only updates postings where `location_state IS NULL AND location_city IS NOT NULL`.",
        },
        "Embedding Generation": {
            "purpose": "Computes bge-m3 embeddings for `match_text` from `postings_for_matching`. "
                       "Content-addressed storage keyed by `text_hash`. Parallel-safe, idempotent.",
            "reads": "`postings_for_matching` (match_text), `embeddings` (existence check via text_hash)",
            "writes": "`embeddings` (text_hash, text, embedding, model) — UPSERT replaces stale",
            "normalization": "`normalize_text_python()` server-side for both text and hash. "
                            "Hash = `sha256(normalize_text_python(text))[:32]`. Eliminates Python/SQL drift.",
            "dependencies": "Ollama (`bge-m3:567m`), `EMBED_WORKERS` parallel threads",
            "failure_mode": "Ollama down → skip (returns empty embedding). Individual failures don't block batch.",
            "data_contract": "`ON CONFLICT (text_hash) DO UPDATE` — stale embeddings replaced automatically. "
                            "Certified clean = 100% embeddable postings have current embeddings + zero corrupted hashes.",
        },
        "Description Backfill": {
            "purpose": "Fetches full job descriptions from source websites for AA postings that arrived with "
                       "metadata only (`--no-descriptions` in step 1). Playwright-based SPA rendering with VPN rotation.",
            "reads": "`postings` (via work_query: missing descriptions, <2 failures)",
            "writes": "`postings.job_description`",
            "normalization": "HTML → text via `ArbeitsagenturScraper` (Playwright).",
            "dependencies": "HTTP (arbeitsagentur.de), VPN rotation (`scripts/vpn.sh` — ProtonVPN German servers), "
                           "`lib/scrapers/arbeitsagentur.py` (Playwright)",
            "failure_mode": "`CONSECUTIVE_403_THRESHOLD = 3` → VPN rotate. `MAX_RATE_LIMIT_RETRIES = 10`. "
                           "Failures increment `processing_failures` — stops at 2.",
            "data_contract": "`MIN_DESCRIPTION_LENGTH = 100`. Only AA postings. TT#1299: batch=50, scale=20, prio=60.",
        },
        "External Partners": {
            "purpose": "Fetches descriptions from external partner sites (jobvector.de, etc.) for postings "
                       "where `job_description = '[EXTERNAL_PARTNER]'`. OWL-based prefix → scraper mapping.",
            "reads": "`postings` (where `job_description = '[EXTERNAL_PARTNER]'`), `owl` (external_job_site prefixes), "
                     "`postings.source_metadata->raw_api_response->externeUrl`",
            "writes": "`postings.job_description`, `postings.source_metadata`",
            "normalization": "`strip_html()` (BeautifulSoup text extraction).",
            "dependencies": "HTTP (external partner sites), `lib/scrapers` registry",
            "failure_mode": "Unknown domain → skip. `MIN_DESCRIPTION_LENGTH = 100`.",
            "data_contract": "TT#1305: batch=100, prio=55. Only processes postings with `externeUrl` in metadata.",
        },
        "Extracted Summary": {
            "purpose": "Extracts structured English summary from Deutsche Bank posting descriptions using LLM. "
                       "AA postings use raw `job_description` directly (no summary needed).",
            "reads": "`postings` (posting_id, job_title, job_description), `instructions` (prompt template #3328)",
            "writes": "`postings.extracted_summary`",
            "normalization": "LLM extracts structured summary in English. QA: bad-data patterns, length 50-5000 chars.",
            "dependencies": "Ollama (`qwen2.5-coder:7b`)",
            "failure_mode": "LLM hallucination detected → skip posting (bad-data pattern filter). "
                           "Rate limited by `scale_limit = 1` (sequential).",
            "data_contract": "TT#1300: batch=50, scale=1, prio=50. Deutsche Bank postings only.",
        },
        "Turing Daemon": {
            "purpose": "Pipeline execution engine. Discovers and runs all enabled bulk actors in priority order. "
                       "ThreadPoolExecutor with per-actor `scale_limit` workers. VPN rotation on HTTP 403s. "
                       "One ticket per batch run for tracking.",
            "reads": "`task_types` JOIN `actors` — discovers enabled bulk actors with work_queries",
            "writes": "`tickets` (batch tracking). Delegates writes to individual actors.",
            "normalization": "Normalizes result rows to have `subject_id` (tries `posting_id`, `profile_id`, `id`).",
            "dependencies": "VPN rotation, advisory lock `73573` (prevents concurrent daemon runs), "
                           "`importlib` dynamic actor loading",
            "failure_mode": "Per-actor failures isolated — other actors continue. Advisory lock prevents double-runs. "
                           "`CONSECUTIVE_403_THRESHOLD = 3` → VPN rotate.",
            "data_contract": "Executes actors in priority DESC order. Respects `batch_size` and `scale_limit` per actor.",
        },
        "Description Retry": {
            "purpose": "Re-attempts berufenet classification for rejected `owl_pending` items using job description "
                       "as additional LLM context. Expected yield: ~25% resolution.",
            "reads": "`owl_pending` (status='rejected'), `postings` (JOIN on job_title, where description available)",
            "writes": "`owl_pending` (→ 'resolved'), `postings` (berufenet fields), `owl_names` (new synonyms)",
            "normalization": "`_truncate_description()` — truncates to 800 chars at word boundary for LLM context.",
            "dependencies": "Ollama (`qwen2.5:7b`)",
            "failure_mode": "Failed LLM calls → mark `processed_by = 'description_retry_rejected'` to skip on next run.",
            "data_contract": "`BATCH_SIZE = 50`. Only processes items with matching posting that has description >50 chars.",
        },
        "Auto-Triage": {
            "purpose": "Bulk auto-triage of `owl_pending` berufenet items. Runs LLM on items escalated by "
                       "Berufenet Phase 2 that have embedding candidates attached. Resolved items become OWL synonyms.",
            "reads": "`owl_pending` (status='pending', owl_type='berufenet'), `source_context` JSON (candidates)",
            "writes": "`postings` (berufenet_id, berufenet_verified), `owl_pending` (→ 'resolved'/'rejected'), "
                      "`owl_names` (new synonyms)",
            "normalization": "None — uses existing candidates from Berufenet Phase 2.",
            "dependencies": "`lib.berufenet_matching.llm_triage_pick` (Ollama LLM)",
            "failure_mode": "LLM rejection → mark as 'rejected'. Safe to re-run.",
            "data_contract": "`BATCH_SIZE = 50`. Matches update all postings with same `LOWER(job_title)`.",
        },
        "Domain Gate": {
            "purpose": "Classifies postings into ~12 user-friendly domain categories using KldB codes. "
                       "3-step cascade: KldB Berufshauptgruppe → keyword title patterns → LLM fallback. "
                       "~95% coverage.",
            "reads": "`postings` JOIN `berufenet` (on berufenet_id), `berufenet_synonyms`",
            "writes": "`postings.domain_gate` (JSONB: primary_domain, sub_domain, kldb_hauptgruppe, color)",
            "normalization": "KldB code → 2-digit Berufshauptgruppe extraction (`SUBSTRING(kldb FROM 3 FOR 2)`).",
            "dependencies": "None external. TT#1303: batch=10, scale=10, prio=0.",
            "failure_mode": "No berufenet/KldB → fall through to keyword/LLM cascade.",
            "data_contract": "12 domain categories (IT, Healthcare, Education, Finance, etc.) with UI colors.",
        },
        "Pipeline Report": {
            "purpose": "Per-source posting pipeline summary with data quality certification. "
                       "Checks: all embeddable postings have current embeddings AND zero corrupted hashes.",
            "reads": "`postings`, `postings_for_matching`, `embeddings` (hash match via `normalize_text_python()`)",
            "writes": "stdout only (report table). No DB writes.",
            "normalization": "Uses `normalize_text_python()` inside SHA256 for hash matching (matches embedding storage).",
            "dependencies": "None external.",
            "failure_mode": "N/A — read-only report.",
            "data_contract": "Output: `✅ CERTIFIED CLEAN` or `⚠️ NOT CLEAN` with itemized issues.",
        },
        "Demand Snapshot": {
            "purpose": "Nightly market intelligence. Populates `demand_snapshot` with (state × domain) and "
                       "(state × domain × berufenet_id) counts, national averages, demand ratios.",
            "reads": "`postings` JOIN `berufenet`",
            "writes": "`demand_snapshot` (DELETE + INSERT + UPDATE for ratios)",
            "normalization": "KldB 2-digit domain codes. Minimum threshold: 20 postings nationally for profession-level.",
            "dependencies": "None external. Runtime: <5 seconds.",
            "failure_mode": "Idempotent — safe to re-run. DELETE + INSERT pattern.",
            "data_contract": "`demand_ratio = total_postings / national_avg`. Two passes: domain-level, then profession-level.",
        },
        "Profession Similarity": {
            "purpose": "Hybrid KLDB structure + embedding cosine similarity. "
                       "Populates top-N related professions per Berufenet profession. "
                       "Combined = 0.4 × kldb_score + 0.6 × embedding_score.",
            "reads": "`berufenet` (with ≥20 postings filter), `embeddings` (profession name embeddings)",
            "writes": "`profession_similarity` (DELETE + INSERT)",
            "normalization": "KLDB scoring: same 5-digit=1.0, same 3-digit=0.7, same 2-digit=0.3, different=0.0.",
            "dependencies": "`numpy` for cosine similarity. Runtime: 30-60 seconds.",
            "failure_mode": "Idempotent — safe to re-run. Minimum threshold: combined score ≥ 0.15.",
            "data_contract": "Combined weighting: 40% structural (KldB hierarchy) + 60% semantic (embedding cosine).",
        },
    }

    for name, filepath in ACTOR_FILES.items():
        details = ACTOR_DETAILS.get(name, {})
        intro = introspect_python_file(filepath)

        sections.append(f"## {name}\n\n")
        sections.append(f"**File:** `{filepath}` ({intro['line_count']} lines)\n\n")

        if intro["docstring"]:
            # First sentence only for the summary line
            first_sentence = intro["docstring"].split("\n")[0].strip()
            sections.append(f"> {first_sentence}\n\n")

        sections.append(f"**Purpose:** {details.get('purpose', intro['docstring'][:200] or '—')}\n\n")

        # I/O table
        sections.append("| | Details |\n|---|---|\n")
        sections.append(f"| **Reads from** | {details.get('reads', '—')} |\n")
        sections.append(f"| **Writes to** | {details.get('writes', '—')} |\n")
        sections.append(f"| **Normalization** | {details.get('normalization', '—')} |\n")
        sections.append(f"| **Dependencies** | {details.get('dependencies', '—')} |\n")
        sections.append(f"| **Failure mode** | {details.get('failure_mode', '—')} |\n")
        sections.append(f"| **Data contract** | {details.get('data_contract', '—')} |\n")
        sections.append("\n")

        # Classes found
        if intro["classes"]:
            sections.append(f"**Classes:** {', '.join(f'`{c}`' for c in intro['classes'])}\n\n")

        # Key SQL (collapsed)
        if intro["sql"]:
            sections.append("<details><summary>Key SQL queries (click to expand)</summary>\n\n")
            for i, sql in enumerate(intro["sql"][:5], 1):  # Max 5 queries
                sections.append(f"```sql\n{sql}\n```\n\n")
            sections.append("</details>\n\n")

        # Internal flowchart for complex actors
        if name == "Berufenet Classification":
            sections.append("### Internal Flow\n\n```mermaid\nflowchart TD\n")
            sections.append(textwrap.dedent("""\
                    A[Unclassified job_title] --> B{OWL vocabulary?}
                    B -- yes, unanimous --> C[✅ verified='owl']
                    B -- yes, multiple --> D{All agree?}
                    D -- yes --> C
                    D -- no --> E[Majority vote]
                    B -- no --> F{Phase 2 on?}
                    F -- no --> G[Skip - NULL]
                    F -- yes --> H[Compute bge-m3 embedding]
                    H --> I{cosine > 0.85?}
                    I -- yes --> J[Auto-accept + add synonym]
                    I -- 0.70-0.85 --> K[LLM verify]
                    K -- confirmed --> J
                    K -- rejected --> L[owl_pending]
                    I -- < 0.70 --> L
                    L --> M[Phase 3: Auto-triage]
                    M -- match --> J
                    M -- no match --> N[Human review]
            """))
            sections.append("```\n\n")

        elif name == "Embedding Generation":
            sections.append("### Content-Addressed Storage\n\n```mermaid\nflowchart LR\n")
            sections.append(textwrap.dedent("""\
                    A[match_text] --> B["normalize_text_python()\\n(server-side)"]
                    B --> C["SHA256 → text_hash\\n(first 32 hex chars)"]
                    B --> D["bge-m3 embedding\\n(1024-dim vector)"]
                    C --> E["embeddings table\\nKEY: text_hash"]
                    D --> E
                    E --> F{ON CONFLICT?}
                    F -- new --> G[INSERT]
                    F -- exists --> H["UPDATE\\n(replace stale)"]
            """))
            sections.append("```\n\n")

        elif name == "Turing Daemon":
            sections.append("### Execution Model\n\n```mermaid\nflowchart TD\n")
            sections.append(textwrap.dedent("""\
                    A[Daemon starts] --> B[Advisory lock 73573]
                    B --> C[Query task_types\\nORDER BY priority DESC]
                    C --> D[For each task_type]
                    D --> E[Execute work_query]
                    E --> F{work found?}
                    F -- yes --> G[ThreadPoolExecutor\\nmax_workers=scale_limit]
                    G --> H[Process batch]
                    H --> I[Log ticket]
                    F -- no --> J[Skip]
                    I --> D
                    J --> D
                    D --> K[Release lock]
            """))
            sections.append("```\n\n")

        sections.append("---\n\n")

    # ── Troubleshooting / Runbook ─────────────────────────────
    sections.append(textwrap.dedent("""\
        ## Troubleshooting

        Common failure modes and fixes, derived from production incidents.

        ### Pipeline won't start (lock file)

        ```
        ⚠️  Already running (PID 12345) - exiting
        ```

        **Cause:** Previous run crashed without cleanup, or a run is genuinely still going.

        **Fix:**
        ```bash
        # Check if process is real
        ps aux | grep turing_fetch
        # If stale:
        rm -f /tmp/turing_fetch.lock
        ```

        ### Step 4 stalls / 403 errors (description backfill)

        ```
        CONSECUTIVE 403s: 3 — rotating VPN...
        ```

        **Cause:** Arbeitsagentur rate-limited the current IP.

        **Fix:** Automatic — VPN rotates via `scripts/vpn.sh` (ProtonVPN). If all IPs exhausted:
        ```bash
        # Check VPN status
        protonvpn-cli status
        # Force reconnect to a different server
        sudo protonvpn-cli disconnect && sudo protonvpn-cli connect --cc DE
        ```
        Actor stops after `MAX_RATE_LIMIT_RETRIES = 10` rotations. Resume on next run.

        ### Certification fails (embeddings dirty)

        ```
        ⚠️  DIRTY need=42 corrupt=0
        ```

        **Cause:** Description backfill (step 4) changed `match_text` after the embedding actor ran.
        The post-step embedding sweep should catch this, but if the sweep was interrupted:

        **Fix:**
        ```bash
        # Manual embedding sweep
        python3 actors/postings__embedding_U.py --batch 50000
        # Re-certify
        python3 scripts/pipeline_report.py
        ```

        ### Certification fails (corrupted hashes)

        ```
        ⚠️  DIRTY need=0 corrupt=156
        ```

        **Cause:** Python `.strip()` vs SQL `btrim()` unicode normalization drift created
        embeddings whose stored `text` doesn't match the `text_hash`. Fixed in commit `660c9e6`
        but legacy rows may resurface if old code paths are reintroduced.

        **Fix:**
        ```sql
        -- Find and repair corrupted hashes
        UPDATE embeddings
        SET text_hash = LEFT(ENCODE(SHA256(
            CONVERT_TO(normalize_text_python(text), 'UTF8')
        ), 'hex'), 32)
        WHERE text_hash != LEFT(ENCODE(SHA256(
            CONVERT_TO(text, 'UTF8')
        ), 'hex'), 32);

        -- Delete duplicates (keep newest)
        DELETE FROM embeddings a
        USING embeddings b
        WHERE a.text_hash = b.text_hash
          AND a.created_at < b.created_at;
        ```

        ### Berufenet Phase 2 slow (>2 hours)

        **Cause:** GPU saturated or Ollama unresponsive.

        **Fix:**
        ```bash
        # Check Ollama
        curl -s http://localhost:11434/api/tags | python3 -m json.tool
        # Restart if needed
        systemctl restart ollama
        # Check GPU
        nvidia-smi
        ```
        Phase 2 batch size is 2000. Reduce to 500 if OOM.

        ### OWL lookup returns 0 hits (vocabulary stale)

        **Cause:** New job titles not yet in `owl_names`. Phase 2 auto-adds synonyms,
        so this self-heals over successive runs.

        **Check:**
        ```sql
        SELECT COUNT(*) FROM owl_names
        WHERE confidence_source IN ('human','import','llm_confirmed');
        -- Should be >100K and growing
        ```

        ### Pipeline notification not received

        **Cause:** ntfy.sh down, or Signal not configured.

        **Check:**
        ```bash
        # Test ntfy
        curl -d "test" https://ntfy.sh/ty-pipeline
        # Test Signal
        python3 -c "from lib.signal_notify import send_alert; send_alert('test')"
        ```

        ### Demand snapshot empty / profession similarity zero rows

        **Cause:** Berufenet classification coverage too low (< 20 postings per profession).

        **Check:**
        ```sql
        SELECT COUNT(DISTINCT berufenet_id)
        FROM postings
        WHERE berufenet_id IS NOT NULL AND NOT invalidated;
        -- Should be >2000
        ```

        ### Quick diagnostic commands

        ```bash
        # Full status without running pipeline
        ./scripts/turing_fetch.sh status

        # Process-level debug (PIDs, file descriptors, connections)
        ./scripts/turing_fetch.sh debug

        # Tail latest backfill log
        ./scripts/turing_fetch.sh tail

        # Pipeline report (data quality check)
        python3 scripts/pipeline_report.py

        # Check specific actor's pending work
        python3 -c "
        from core.database import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) as cnt FROM postings_for_matching p WHERE NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.text_hash = LEFT(ENCODE(SHA256(CONVERT_TO(normalize_text_python(p.match_text), \"UTF8\")), \"hex\"), 32))')
            print(f'Pending embeddings: {cur.fetchone()[\"cnt\"]}')
        "
        ```

        ---
    """))

    # ── Footer ────────────────────────────────────────────────
    sections.append(textwrap.dedent(f"""\
        ## Regeneration

        This document is auto-generated by `scripts/generate_fetch_docs.py`.

        To regenerate manually:
        ```bash
        python3 scripts/generate_fetch_docs.py
        ```

        To check if docs are stale (CI/pre-commit):
        ```bash
        python3 scripts/generate_fetch_docs.py --check
        ```

        Auto-triggered on every `git commit` via `.git/hooks/post-commit`.

        ---

        _Generated {now} by generate_fetch_docs.py_
    """))

    return "".join(sections)


# ╔════════════════════════════════════════════════════════════════════╗
# ║  MAIN                                                            ║
# ╚════════════════════════════════════════════════════════════════════╝

def _strip_volatile(text):
    """Remove sections that change every run (stats, timestamps) for --check comparison."""
    # Strip timestamps
    text = re.sub(r"\*\*Generated:\*\* .*", "", text)
    text = re.sub(r"_Generated .* by generate_fetch_docs.py_", "", text)
    # Strip entire Quick Stats table (DB counts change every pipeline run)
    text = re.sub(
        r"## Quick Stats \(at generation time\).*?(?=\n## )",
        "",
        text,
        flags=re.DOTALL,
    )
    return text


def main():
    check_mode = "--check" in sys.argv

    print("Generating turing_fetch pipeline docs...")

    doc = generate_docs()

    if check_mode:
        # Compare with existing file (structural only — ignore stats + timestamps)
        if os.path.exists(OUTPUT_PATH):
            with open(OUTPUT_PATH) as f:
                existing = f.read()
            clean_existing = _strip_volatile(existing)
            clean_new = _strip_volatile(doc)
            if clean_existing.strip() == clean_new.strip():
                print("✅ Docs are up to date")
                sys.exit(0)
            else:
                print("⚠️  Docs are stale — run: python3 scripts/generate_fetch_docs.py")
                sys.exit(1)
        else:
            print(f"⚠️  Docs missing at {OUTPUT_PATH}")
            sys.exit(1)

    # Write the docs
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(doc)

    print(f"✅ Written to {OUTPUT_PATH}")
    print(f"   {len(doc):,} chars, {doc.count(chr(10)):,} lines")


if __name__ == "__main__":
    main()
