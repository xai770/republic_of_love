# Workflow Execution Trace

**Generated:** 2025-12-01 03:48:33

## Workflow Context

**Workflow ID:** 3001
**Workflow Name:** Complete Job Processing Pipeline
**Started:** 2025-12-01 03:48:29
**Completed:** 2025-12-01 03:48:33
**Duration:** 4.0 seconds
**Interactions:** 1 completed, 0 failed

---

## ✅ Interaction 1: Fetch Jobs from Deutsche Bank API

**Interaction ID:** 37137
**Duration:** 3.05s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 9144
**Name:** Fetch Jobs from Deutsche Bank API
**Description:** Fetches job postings from Deutsche Bank API, checks for duplicates, parses locations, stores in postings table
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 56
**Name:** db_job_fetcher
**Type:** script
**Script:** core/wave_runner/actors/db_job_fetcher.py

### Prompt Template

````
{
  "user_id": 1,
  "max_jobs": 50,
  "source_id": 1,
  "skip_rate_limit": true
}
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**skip_if_rate_limited** (Priority: 100)
- **Condition:** `[RATE_LIMITED]`
- **Description:** Skip to extraction if fetcher is rate-limited (already ran today)
- **Next:** Conversation 9193

**API failure - terminate** (Priority: 50)
- **Condition:** `[FAILED]`
- **Description:** Job fetcher API failed - cannot proceed, terminate workflow
- **Next:** END (terminal)

**Route to check summary (success path)** (Priority: 50)
- **Condition:** `success`
- **Description:** Jobs fetched successfully - proceed to check summary
- **Next:** Conversation 9193

**API timeout - terminate** (Priority: 49)
- **Condition:** `[TIMEOUT]`
- **Description:** Job fetcher timed out - cannot proceed, terminate workflow
- **Next:** END (terminal)

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````json
{
  "max_jobs": 10,
  "search_text": "",
  "skip_rate_limit": true
}
````

### Actual Output

````json
{
  "data": {
    "status": "success",
    "staging_ids": [
      2187
    ],
    "jobs_fetched": 1,
    "jobs_updated": 0,
    "jobs_full_data": [
      {
        "location": "Luxembourg 2 Blvd K. Adenauer",
        "raw_data": {
          "posted_on": "Posted Today",
          "external_id": "R0411244",
          "api_response": {
            "title": "Internship PB - Business Service Team",
            "postedOn": "Posted Today",
            "bulletFields": [
              "R0411244"
            ],
            "externalPath": "/job/Luxembourg-2-Blvd-K-Adenauer/Internship-PB---Business-Service-Team_R0411244",
            "locationsText": "Luxembourg 2 Blvd K. Adenauer"
          },
          "external_path": "/job/Luxembourg-2-Blvd-K-Adenauer/Internship-PB---Business-Service-Team_R0411244",
          "job_description": "Job Description: We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Internship PB - Business Service Team",
        "created_at": "2025-12-01T03:48:30.331455+01:00",
        "staging_id": 2187,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Luxembourg-2-Blvd-K-Adenauer/Internship-PB---Business-Service-Team_R0411244",
        "company_name": "Deutsche Bank"
      }
    ],
    "batches_fetched": 2,
    "total_available": 1596,
    "jobs_invalidated": 2059,
    "jobs_skipped_no_title": 0,
    "jobs_skipped_no_description": 0,
    "jobs_skipped_short_description": 0
  },
  "status": "success"
}
````

---

## Summary

- **Total interactions:** 1
- **Completed:** 1
- **Failed:** 0
- **Total duration:** 4.0s
- **Avg per interaction:** 4.01s
