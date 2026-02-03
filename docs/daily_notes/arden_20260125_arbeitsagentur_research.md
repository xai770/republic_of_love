# arbeitsagentur.de API Research

**Date:** 2026-01-25 (Sunday)  
**Goal:** Figure out how to ingest job postings from arbeitsagentur.de  
**Status:** ✅ API WORKING!

---

## Discovery Summary

The Bundesagentur für Arbeit has an **unofficial but public API** that's been reverse-engineered by the [bundesAPI project](https://github.com/bundesAPI/jobsuche-api).

**Key Finding:** No OAuth needed! Just pass `X-API-Key: jobboerse-jobsuche` header.

---

## Working API

### Job Search (v4)
```bash
curl -H "X-API-Key: jobboerse-jobsuche" \
  'https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs?was=Software+Engineer&wo=Berlin&page=1&size=25'
```

### Job Search (v6 - newer, more fields)
```bash
curl -H "X-API-Key: jobboerse-jobsuche" \
  'https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs?was=Python&wo=Berlin&page=1&size=25'
```

### Search Parameters
| Parameter | Description | Example |
|-----------|-------------|---------|
| `was` | Job title/skill search | `Python`, `Software+Engineer` |
| `wo` | Location | `Berlin`, `München` |
| `page` | Page number (starts at 1) | `1` |
| `size` | Results per page | `25` |
| `angebotsart` | Job type: 1=ARBEIT, 2=SELBSTAENDIGKEIT, 4=AUSBILDUNG | `1` |
| `arbeitszeit` | vz=Vollzeit, tz=Teilzeit, ho=HomeOffice | `vz;ho` |
| `umkreis` | Radius in km from `wo` | `50` |
| `veroeffentlichtseit` | Days since posted (0-100) | `7` |

### ⚠️ Job Details API - NOT WORKING
```bash
curl -H "X-API-Key: jobboerse-jobsuche" \
  'https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails/{refnr}'
```
Returns `STELLENANGEBOT_NICHT_GEFUNDEN` - appears to require additional auth or be deprecated.

---

## Response Structure (v4)

```json
{
  "stellenangebote": [
    {
      "beruf": "Software Engineer/in",
      "titel": "Software Engineer (m/w/d)",
      "refnr": "10000-1234567890-S",
      "arbeitsort": {
        "plz": "10117",
        "ort": "Berlin",
        "strasse": "Unter den Linden 1",
        "region": "Berlin",
        "land": "Deutschland",
        "koordinaten": { "lat": 52.52, "lon": 13.38 }
      },
      "arbeitgeber": "Amazon Web Services",
      "aktuelleVeroeffentlichungsdatum": "2026-01-23",
      "eintrittsdatum": "2026-02-01",
      "externeUrl": "https://www.jobvector.de/job/..."  // External link to full description
    }
  ],
  "maxErgebnisse": 3614,
  "page": 1,
  "size": 25
}
```

---

## Data Mapping

| arbeitsagentur field | Our postings field | Notes |
|---------------------|-------------------|-------|
| `titel` | `job_title` | ✅ Direct map |
| `arbeitgeber` | `posting_name` | ✅ Company name |
| `arbeitsort.ort` | `location_city` | ✅ City |
| `externeUrl` | `external_url` | ✅ Link to full posting |
| `refnr` | `source_id` | For deduplication |
| N/A | `job_description` | ⚠️ Must fetch from externeUrl |

**Key Limitation:** Search results don't include job descriptions. Must follow `externeUrl` to get full text, OR we use the title + company + requirements inference.

---

## Integration Strategy

### Option A: Metadata Only (Fast)
- Ingest `titel`, `arbeitgeber`, `ort`, `externeUrl` directly
- Let Clara extract requirements from title + company
- Pro: Fast, no external fetching
- Con: Limited info for matching

### Option B: Full Fetch (Complete)
- Ingest search results
- Follow `externeUrl` for each job → scrape full description
- Pro: Complete job descriptions
- Con: Rate limiting, slower, external site dependencies

### Recommendation: Start with Option A
Get the pipeline working with metadata, add full fetch later.

---

## Next Steps

1. [x] ~~Find the actual job search API endpoint~~ ✅ DONE
2. [x] ~~Test with curl~~ ✅ WORKING
3. [x] ~~Map fields to our schema~~ ✅ MAPPED
4. [x] ~~Build interrogator script~~ ✅ DONE - `actors/postings__arbeitsagentur_CU.py`
5. [x] ~~Test ingestion into `postings` table~~ ✅ 85 jobs imported!
6. [ ] Add to wave-runner schedule (cron)
7. [ ] Add full description fetching (follow `externeUrl`)

---

## Implementation Summary

### Actor Created
**File:** `actors/postings__arbeitsagentur_CU.py`

**Actor ID:** 1297 (in `actors` table)

**Features:**
- Fetches from 4 default searches (Software Engineer/Berlin, Data Engineer/München, Python Developer/Hamburg, DevOps/Frankfurt)
- Pagination support (25 jobs per page)
- Deduplication by `refnr` (job reference number)
- Preflight check (prevents duplicate runs within 20 hours)
- Full audit trail via tickets table

**Usage:**
```bash
# Dry run (test API only)
python3 actors/postings__arbeitsagentur_CU.py --dry-run

# Normal run (respects preflight check)
python3 actors/postings__arbeitsagentur_CU.py

# Force run (skip preflight)
python3 actors/postings__arbeitsagentur_CU.py --force --max-jobs 50

# Custom search
python3 actors/postings__arbeitsagentur_CU.py --search "React Developer" --location München
```

### First Import Results
```
Postings by source:
  deutsche_bank: 2206
  arbeitsagentur: 85

Sample jobs:
  • DevOps Engineer im Cloud Umfeld (w/m/d) @ EMOS Software GmbH (Frankfurt am Main)
  • C2S_Platform Engineer (devops e.) (w/m/d) @ Guldberg GmbH (Frankfurt am Main)
  • Data Engineer / DevOps Engineer (w/m/d) @ Guldberg GmbH (Frankfurt am Main)
```
