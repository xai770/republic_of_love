# Turing Project Context

**talent.yoga** is a job matching service:
- Users upload profiles with their skills/experience
- We scan job postings from Deutsche Bank and other sources
- We match profiles to postings via a skill hierarchy (OWL taxonomy)
- Closer skills in the hierarchy = better match

## CPS: Competency Proof Stack

Every job requirement decomposes into what a candidate must PROVE:

**Proof dimensions:**
- **Skill** — Core capability (python, leadership, sql)
- **Experience** — Skill + years ("5 years python")
- **Certificate** — Credential (AWS, CPA, MBA)
- **Track Record** — Achievement ("led 50-person team")

**Context dimensions:**
- **Domain** — Industry (finance, fintech, healthcare, technology)
- **Seniority** — Level as stated (Senior, VP, Lead)
- **Setting** — Where experience gained (payment systems, trading)
- **Role** — Role context (Backend Engineer, Team Lead)

**Metadata:**
- **Importance** — critical/required/preferred/nice_to_have
- **Confidence** — Model's certainty (0.0-1.0)
- **Tags** — Lowercase semantic anchors for fuzzy matching

## Current State

- 13,713 competencies extracted from 2,010 postings
- Stored in `posting_facets` table
- Next step: link to OWL hierarchy for matching
