#!/usr/bin/env python3
"""
Minimal headless test for CV extraction — no HTTP, no FastAPI, no browser.

Usage:
    cd /home/xai/Documents/ty_learn
    source venv/bin/activate
    python scripts/test_cv_extraction.py [path/to/cv.md]

If no path given, uses the built-in sample CV (short, ~2 chunks).
"""
import asyncio
import sys
import time
from pathlib import Path

# ── Make sure project root is on PYTHONPATH ────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.cv_anonymizer import extract_and_anonymize  # noqa: E402

SAMPLE_CV = """
# Gershon Sample — Condensed CV

## Work Experience

**Senior Software Engineer** at TechCorp (2019–2024)
- Led migration of monolithic Java app to microservices
- Reduced deployment time from 2h to 15min via CI/CD pipeline
- Technologies: Java, Kubernetes, Terraform, PostgreSQL

**Software Engineer** at FinanceBank AG (2015–2019)
- Built real-time fraud detection pipeline processing 50k tx/min
- Reduced false-positive rate by 40%
- Technologies: Python, Apache Kafka, Spark, Redis

**Junior Developer** at StartupXYZ (2013–2015)
- Full-stack web development for e-commerce platform
- Technologies: PHP, MySQL, JavaScript, jQuery

## Education
BSc Computer Science, FU Berlin, 2013

## Skills
Python, Java, Kubernetes, Terraform, PostgreSQL, Kafka, Spark, Redis
"""


def on_partial(data: dict):
    kind = data.get("type", "")
    if kind == "pass1_chunk":
        print(f"  [Pass 1] chunk {data['chunk']}/{data['total_chunks']} done "
              f"— {data['roles_found']} roles so far")
    elif kind == "pass2_role":
        print(f"  [Pass 2] {data['completed']}/{data['total']} roles anonymized")


async def main():
    cv_path = sys.argv[1] if len(sys.argv) > 1 else None
    yogi_name = "TestPhoenix"

    if cv_path:
        path = Path(cv_path)
        if not path.exists():
            print(f"Error: file not found: {cv_path}")
            sys.exit(1)
        cv_text = path.read_text(encoding="utf-8")
        print(f"CV file: {path.name} ({len(cv_text):,} chars)")
    else:
        cv_text = SAMPLE_CV
        print(f"Using built-in sample CV ({len(cv_text):,} chars)")

    print(f"yogi_name: {yogi_name}")
    print("─" * 60)

    t0 = time.monotonic()

    try:
        result = await extract_and_anonymize(
            cv_text=cv_text,
            yogi_name=yogi_name,
            on_partial=on_partial,
        )
        elapsed = time.monotonic() - t0

        print("─" * 60)
        print(f"✅ Done in {elapsed:.1f}s")
        print()
        print(f"  current_title:    {result.get('current_title')}")
        print(f"  career_level:     {result.get('career_level')}")
        print(f"  years_experience: {result.get('years_experience')}")
        print(f"  work_history:     {len(result.get('work_history', []))} roles")
        print(f"  skills:           {len(result.get('skills', []))} items")
        print(f"  languages:        {result.get('languages', [])}")
        print(f"  education:        {len(result.get('education', []))} entries")
        print()
        print("Work history:")
        for r in result.get("work_history", []):
            yr = f"{r.get('start_year','?')}–{r.get('end_year') or ('now' if r.get('is_current') else '?')}"
            print(f"  {yr}  {r.get('role')} @ {r.get('employer_description')}")
        print()
        print("Top skills:", ", ".join(result.get("skills", [])[:10]))

    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"❌ Failed after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
