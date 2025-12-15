# Extraction Model Benchmark Report

**Generated:** 2025-12-02 10:45:05

**Postings Tested:** 15
**Models Tested:** 5
**Quality Grading:** ✅ Enabled
**Grader Model:** qwen2.5:7b

## 📊 Results Summary

| Rank | Model | Clean% | Quality | Latency | Score | Recommendation |
|------|-------|--------|---------|---------|-------|----------------|
| 1 | `phi4-mini:latest` | 100% | 87/100 | 7033ms | 85 | ✅ CHAMPION |
| 2 | `gemma3:4b` | 100% | 89/100 | 8428ms | 85 | ✅ Good |
| 3 | `mistral:latest` | 100% | 89/100 | 13613ms | 80 | ✅ Good |
| 4 | `llama3.2:latest` | 100% | 84/100 | 11394ms | 79 | ✅ Good |
| 5 | `qwen2.5:7b` | 100% | 86/100 | 16154ms | 75 | ✅ Good |

### Score Formula
```
Score = (Clean% × 0.2) + (Quality × 0.6) + (Speed × 0.2)
Speed = max(0, 100 - latency_seconds × 5)
```

---

## 🔍 Detailed Results

### phi4-mini:latest

- **Clean Rate:** 100%
- **Avg Latency:** 7033ms
- **Degenerate:** 0
- **Avg Quality:** 87/100
- **Combined Score:** 85

| Posting | Status | Latency | Quality | Issues |
|---------|--------|---------|---------|--------|
| 10493 | ✅ Clean | 9872ms | 96 | - |
| 10492 | ✅ Clean | 6387ms | 85 | - |
| 10487 | ✅ Clean | 7990ms | 86 | - |
| 10477 | ✅ Clean | 6876ms | 96 | - |
| 10512 | ✅ Clean | 7756ms | 90 | - |
| 10479 | ✅ Clean | 6338ms | 80 | - |
| 10466 | ✅ Clean | 6724ms | 90 | - |
| 10502 | ✅ Clean | 8777ms | 96 | - |
| 10506 | ✅ Clean | 5563ms | 90 | - |
| 10468 | ✅ Clean | 6370ms | 80 | - |
| 10496 | ✅ Clean | 5313ms | 85 | - |
| 10509 | ✅ Clean | 7263ms | 90 | - |
| 10490 | ✅ Clean | 6876ms | 80 | - |
| 10471 | ✅ Clean | 7277ms | 80 | - |
| 10504 | ✅ Clean | 6111ms | 85 | - |

**Quality Breakdown:**

| Posting | Role | Complete | Accurate | Format | Explanation |
|---------|------|----------|----------|--------|-------------|
| 10493 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurate and complete. Key respon... |
| 10492 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurately represented, and the k... |
| 10487 | 25/25 | 38/40 | 23/25 | 9/10 | The job title is accurately represented, which sco... |
| 10477 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurate, and the summary capture... |
| 10512 | 25/25 | 30/40 | 25/25 | 10/10 | The summary accurately represents the role title a... |
| 10479 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10466 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurate, but the summary could b... |
| 10502 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. The summa... |
| 10506 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented. However, ... |
| 10468 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10496 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurately represented, and the k... |
| 10509 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the s... |
| 10490 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the s... |
| 10471 | 25/25 | 30/40 | 25/25 | 10/10 | The student accurately represented the role title ... |
| 10504 | 25/25 | 30/40 | 25/25 | 5/10 | The student's summary accurately represents the ro... |

### gemma3:4b

- **Clean Rate:** 100%
- **Avg Latency:** 8428ms
- **Degenerate:** 0
- **Avg Quality:** 89/100
- **Combined Score:** 85

| Posting | Status | Latency | Quality | Issues |
|---------|--------|---------|---------|--------|
| 10493 | ✅ Clean | 9958ms | 96 | - |
| 10492 | ✅ Clean | 7388ms | 80 | - |
| 10487 | ✅ Clean | 11659ms | 96 | - |
| 10477 | ✅ Clean | 6451ms | 85 | - |
| 10512 | ✅ Clean | 7411ms | 85 | - |
| 10479 | ✅ Clean | 7842ms | 85 | - |
| 10466 | ✅ Clean | 7872ms | 85 | - |
| 10502 | ✅ Clean | 9730ms | 96 | - |
| 10506 | ✅ Clean | 7862ms | 90 | - |
| 10468 | ✅ Clean | 8120ms | 85 | - |
| 10496 | ✅ Clean | 7465ms | 90 | - |
| 10509 | ✅ Clean | 9600ms | 90 | - |
| 10490 | ✅ Clean | 8312ms | 80 | - |
| 10471 | ✅ Clean | 7780ms | 92 | - |
| 10504 | ✅ Clean | 8968ms | 96 | - |

**Quality Breakdown:**

| Posting | Role | Complete | Accurate | Format | Explanation |
|---------|------|----------|----------|--------|-------------|
| 10493 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |
| 10492 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented. Key respo... |
| 10487 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |
| 10477 | 25/25 | 30/40 | 25/25 | 5/10 | The student accurately identified the role title a... |
| 10512 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, and the key responsibil... |
| 10479 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, but the summary could b... |
| 10466 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurately represented, which ear... |
| 10502 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |
| 10506 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented. However, ... |
| 10468 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, and the key responsibil... |
| 10496 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10509 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |
| 10490 | 25/25 | 40/40 | 25/25 | 10/10 | The job title is accurate and complete. Key respon... |
| 10471 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |
| 10504 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |

### mistral:latest

- **Clean Rate:** 100%
- **Avg Latency:** 13613ms
- **Degenerate:** 0
- **Avg Quality:** 89/100
- **Combined Score:** 80

| Posting | Status | Latency | Quality | Issues |
|---------|--------|---------|---------|--------|
| 10493 | ✅ Clean | 15364ms | 96 | - |
| 10492 | ✅ Clean | 16680ms | 80 | - |
| 10487 | ✅ Clean | 16532ms | 90 | - |
| 10477 | ✅ Clean | 10018ms | 90 | - |
| 10512 | ✅ Clean | 13023ms | 96 | - |
| 10479 | ✅ Clean | 16181ms | 96 | - |
| 10466 | ✅ Clean | 11264ms | 90 | - |
| 10502 | ✅ Clean | 16275ms | 80 | - |
| 10506 | ✅ Clean | 9565ms | 90 | - |
| 10468 | ✅ Clean | 14134ms | 80 | - |
| 10496 | ✅ Clean | 11087ms | 90 | - |
| 10509 | ✅ Clean | 14361ms | 80 | - |
| 10490 | ✅ Clean | 11634ms | 80 | - |
| 10471 | ✅ Clean | 16167ms | 96 | - |
| 10504 | ✅ Clean | 11916ms | 96 | - |

**Quality Breakdown:**

| Posting | Role | Complete | Accurate | Format | Explanation |
|---------|------|----------|----------|--------|-------------|
| 10493 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |
| 10492 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10487 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented. Key respo... |
| 10477 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10512 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurate, and the summary capture... |
| 10479 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurate, and the summary capture... |
| 10466 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the s... |
| 10502 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10506 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented. However, ... |
| 10468 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and most ... |
| 10496 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurate, and the summary capture... |
| 10509 | 25/25 | 40/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10490 | 25/25 | 40/40 | 25/25 | 10/10 | The job title is accurate, and the summary capture... |
| 10471 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |
| 10504 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurate, and the summary capture... |

### llama3.2:latest

- **Clean Rate:** 100%
- **Avg Latency:** 11394ms
- **Degenerate:** 0
- **Avg Quality:** 84/100
- **Combined Score:** 79

| Posting | Status | Latency | Quality | Issues |
|---------|--------|---------|---------|--------|
| 10493 | ✅ Clean | 9535ms | 80 | - |
| 10492 | ✅ Clean | 13198ms | 85 | - |
| 10487 | ✅ Clean | 13901ms | 85 | - |
| 10477 | ✅ Clean | 12090ms | 80 | - |
| 10512 | ✅ Clean | 12602ms | 85 | - |
| 10479 | ✅ Clean | 13676ms | 80 | - |
| 10466 | ✅ Clean | 8786ms | 85 | - |
| 10502 | ✅ Clean | 8963ms | 85 | - |
| 10506 | ✅ Clean | 7491ms | 85 | - |
| 10468 | ✅ Clean | 8121ms | 80 | - |
| 10496 | ✅ Clean | 8189ms | 85 | - |
| 10509 | ✅ Clean | 8721ms | 80 | - |
| 10490 | ✅ Clean | 7655ms | 90 | - |
| 10471 | ✅ Clean | 22127ms | 85 | - |
| 10504 | ✅ Clean | 15849ms | 90 | - |

**Quality Breakdown:**

| Posting | Role | Complete | Accurate | Format | Explanation |
|---------|------|----------|----------|--------|-------------|
| 10493 | 15/25 | 30/40 | 25/25 | 10/10 | The role title is close but lacks the "Assistant" ... |
| 10492 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurately represented. Key respo... |
| 10487 | 25/25 | 30/40 | 25/25 | 5/10 | The student accurately represented the job title a... |
| 10477 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10512 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, and the summary capture... |
| 10479 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10466 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, and the key responsibil... |
| 10502 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurately represented. However, ... |
| 10506 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, and the key responsibil... |
| 10468 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10496 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, but the summary could b... |
| 10509 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10490 | 25/25 | 30/40 | 25/25 | 10/10 | The student's summary accurately captures the role... |
| 10471 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurately represented, and the k... |
| 10504 | 25/25 | 30/40 | 25/25 | 10/10 | The student correctly identified the role title an... |

### qwen2.5:7b

- **Clean Rate:** 100%
- **Avg Latency:** 16154ms
- **Degenerate:** 0
- **Avg Quality:** 86/100
- **Combined Score:** 75

| Posting | Status | Latency | Quality | Issues |
|---------|--------|---------|---------|--------|
| 10493 | ✅ Clean | 24051ms | 80 | - |
| 10492 | ✅ Clean | 26124ms | 85 | - |
| 10487 | ✅ Clean | 32950ms | 96 | - |
| 10477 | ✅ Clean | 25434ms | 85 | - |
| 10512 | ✅ Clean | 16356ms | 85 | - |
| 10479 | ✅ Clean | 15820ms | 80 | - |
| 10466 | ✅ Clean | 14598ms | 90 | - |
| 10502 | ✅ Clean | 19124ms | 80 | - |
| 10506 | ✅ Clean | 13597ms | 80 | - |
| 10468 | ✅ Clean | 15942ms | 85 | - |
| 10496 | ✅ Clean | 6396ms | 90 | - |
| 10509 | ✅ Clean | 7121ms | 90 | - |
| 10490 | ✅ Clean | 7962ms | 96 | - |
| 10471 | ✅ Clean | 6902ms | 80 | - |
| 10504 | ✅ Clean | 9933ms | 85 | - |

**Quality Breakdown:**

| Posting | Role | Complete | Accurate | Format | Explanation |
|---------|------|----------|----------|--------|-------------|
| 10493 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10492 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurately represented. Key respo... |
| 10487 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurately represented. Key respo... |
| 10477 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurately represented, and the k... |
| 10512 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, and the key responsibil... |
| 10479 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurate, and the key responsibil... |
| 10466 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10502 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the s... |
| 10506 | 15/25 | 30/40 | 25/25 | 5/10 | The job title is close but missing the "Analyst" q... |
| 10468 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, and the key responsibil... |
| 10496 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the s... |
| 10509 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurately represented, and the k... |
| 10490 | 25/25 | 38/40 | 24/25 | 9/10 | The job title is accurate, and the summary capture... |
| 10471 | 25/25 | 30/40 | 25/25 | 10/10 | The job title is accurate, but the summary could b... |
| 10504 | 25/25 | 30/40 | 25/25 | 5/10 | The job title is accurate, but the score is slight... |

## 📝 Sample Output from Best Model (phi4-mini:latest)

### Posting 10493

**Quality Score:** 96/100

```
===OUTPUT TEMPLATE===
**Role:** Senior Management Support Specialist
**Company:** Deutsche Bank Group (DB)
**Location:** Frankfurt

**Key Responsibilities:**
- Administer complex calendars for senior management and team across different time zones.
- Coordinate business trips, including booking accommodations, travel documents preparation, full expense reimbursement according to internal guidelines.
- Process invoices internally approved by the Finance department; handle inter-departmental reque
...
```

### Posting 10492

**Quality Score:** 85/100

```
===OUTPUT TEMPLATE===
**Role:** BA Associate
**Company:** Deutsche Bank Group (DB)
**Location:** Pune, India

**Key Responsibilities:**
- Collect and define business requirements in cooperation with legal IT functions.
- Challenge existing requirements where needed; explain these to functional analysts/development teams.

**Requirements:**
- 5+ years of prior experience as a Business Analyst within an investment banking organization (with at least 3 years in legal-IT).
- Fluency in English, both
...
```

