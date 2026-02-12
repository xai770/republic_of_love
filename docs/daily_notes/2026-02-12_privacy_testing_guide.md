# Privacy Feature Testing Guide
**To:** xai  
**From:** Your coding companion  
**Date:** 2026-02-12 (evening)  
**Re:** Manual testing of onboarding + CV anonymization features shipped today

---

## Overview

Today we shipped a 2-step onboarding flow (yogi name → notification email) and a
privacy-first CV anonymizer. Everything passed 55 unit tests + 3 E2E curl tests,
but nothing beats a real human clicking through the browser. Below is exactly
what to test and what to look for.

---

## Prerequisites

```bash
# 1. Make sure the server is running
cd ~/Documents/ty_learn
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 2. Make sure Ollama is up with both models
ollama list  # should show gemma3:4b and qwen2.5:7b

# 3. Quick health check
curl -s http://localhost:8000/health
```

---

## TEST 1: Fresh User Onboarding (Browser)

### Goal
Verify the full onboarding conversation in the actual Mira chat UI.

### Setup — Create a fresh test user

We need a user with no yogi_name and no onboarding_completed_at.

```sql
-- Connect to DB
psql -U base_admin -d turing -h localhost

-- Create a totally fresh user for browser testing
INSERT INTO users (email, google_id, full_name)
VALUES ('test-browser@example.com', 'test-browser-sub-001', 'Browser Test User')
RETURNING user_id;
-- Note the user_id (probably 7)
```

### Steps

1. **Open browser** → `http://localhost:8000/auth/test-login/<user_id>`
   - This sets a session cookie and redirects to /dashboard
   - (Only works because we're in DEBUG mode)

2. **Open Mira chat** (the chat bubble / button in the bottom-right)

3. **Test: Greeting is NOT treated as a name**
   - Type: `Hallo!`
   - **Expected:** Mira should ask for your name (something like "Wie soll ich dich nennen?" or English equivalent)
   - She should NOT set "Hallo" as your yogi_name
   - Try other greetings too: `Hi there`, `Hey Mira`, `Hallo du`

4. **Test: Name setting**
   - Type: `Call me Phoenix` (or any name you like)
   - **Expected:** Mira acknowledges the name AND immediately asks about notification email
   - Something like: "Schön, Phoenix! Möchtest du eine E-Mail-Adresse hinterlegen für Benachrichtigungen?"

5. **Test: Verify name in DB**
   ```sql
   SELECT user_id, yogi_name, notification_email, onboarding_completed_at
   FROM users WHERE email = 'test-browser@example.com';
   ```
   - `yogi_name` should be `Phoenix`
   - `notification_email` should still be NULL
   - `onboarding_completed_at` should still be NULL (not done until email step)

6. **Test: Email consent — happy path**
   - Type: `phoenix@proton.me`
   - **Expected:** Mira thanks you, confirms the email, and switches to normal chat mode
   - Verify in DB:
     ```sql
     SELECT yogi_name, notification_email, notification_consent_at, onboarding_completed_at
     FROM users WHERE email = 'test-browser@example.com';
     ```
   - `notification_email` = `phoenix@proton.me`
   - `notification_consent_at` = not null
   - `onboarding_completed_at` = not null

7. **Test: Normal chat after onboarding**
   - Type: `What is talent.yoga?`
   - **Expected:** Normal Mira FAQ response (not onboarding prompts)

### Variations to test with additional fresh users

Create more users as needed:
```sql
INSERT INTO users (email, google_id, full_name)
VALUES ('test-decline@example.com', 'test-decline-sub-001', 'Decline Test')
RETURNING user_id;
```

- **Decline email path**: After name is set, type `Nein danke` or `no thanks` or `I'd rather not`
  - **Expected:** Mira says that's fine, onboarding completes, no email saved
  - `notification_email` = NULL, `onboarding_completed_at` = not null

- **Unrelated message path**: After name is set and Mira asks about email, type something
  totally unrelated like `What jobs do you have in Berlin?`
  - **Expected:** Mira should complete onboarding silently and answer the question
  - This is the "graceful exit" — user didn't engage with email, we don't nag

---

## TEST 2: Name Validation Edge Cases

### Goal
Verify the name validation rules work in the live chat.

Create fresh users for each test (or reset via SQL):
```sql
-- Reset a user to re-test onboarding
UPDATE users SET yogi_name = NULL, onboarding_completed_at = NULL,
  notification_email = NULL, notification_consent_at = NULL
WHERE user_id = <id>;
```

### Cases to try

| You type | Expected behavior |
|---|---|
| `A` | Rejected — too short (min 2 chars). Mira asks again. |
| `ThisNameIsWayTooLongForAnything` | Rejected — too long (max 20 chars). Mira asks again. |
| `admin` | Rejected — reserved name. Mira asks again. |
| `mira` | Rejected — reserved name. Mira asks again. |
| `system` | Rejected — reserved name. Mira asks again. |
| `xai` | Rejected — already taken by user 1. Mira says it's taken. |
| `Luna` | Rejected — already taken by user 4 (case-insensitive). |
| `  Sage  ` | Accepted — whitespace trimmed. |
| `O'Brien` | Rejected — apostrophe not allowed (only letters, hyphens, spaces). |
| `Anna-Lena` | Accepted — hyphens OK. |
| `Hi there` | NOT treated as a name — greeting filter catches it. |
| `Hey` | NOT treated as a name — greeting filter catches it. |

---

## TEST 3: CV Upload + Anonymization

### Goal
Verify the parse-cv endpoint anonymizes real data correctly.

### Prerequisite
- The user MUST have a yogi_name set (onboarding completed)
- You need a CV file (PDF, DOCX, or TXT)

### Option A: curl test with a sample TXT CV

```bash
# Create a test CV file
cat > /tmp/test_cv.txt << 'EOF'
Gershon Pollatschek
Senior SAP Consultant
Email: gershon.pollatschek@gmail.com
Phone: +49 176 12345678
LinkedIn: linkedin.com/in/gershon-pollatschek

WORK EXPERIENCE

2020-Present: Senior SAP S/4HANA Consultant at Deutsche Bank AG, Frankfurt
- Led migration from SAP ECC to S/4HANA
- Managed team of 5 developers

2017-2020: SAP Consultant at Siemens AG, Munich
- ABAP development for logistics module
- Integration with SAP BW

2015-2017: Junior Developer at BMW Group, Munich
- Java backend development
- REST API design

EDUCATION
2013-2015: M.Sc. Computer Science, TU Munich
2010-2013: B.Sc. Computer Science, Hebrew University Jerusalem

SKILLS
SAP S/4HANA, ABAP, Java, Python, REST APIs, Docker, Kubernetes

CERTIFICATIONS
SAP Certified Application Associate - SAP S/4HANA
AWS Solutions Architect
EOF

# Upload as the test user (use the cookie file from test-login)
# First, log in to get a cookie
curl -s -c /tmp/test_cv_cookies.txt -L http://localhost:8000/auth/test-login/<user_id>

# Then upload
curl -s -b /tmp/test_cv_cookies.txt \
  -X POST http://localhost:8000/profiles/me/parse-cv \
  -F "file=@/tmp/test_cv.txt" | python3 -m json.tool
```

### What to check in the response

1. **Name replacement**: `Gershon Pollatschek` should be replaced with the user's yogi_name (e.g., `Phoenix`)
2. **Company generalization**: 
   - `Deutsche Bank AG` → something like `Major German Bank` or `Large Financial Institution`
   - `Siemens AG` → something like `Major German Industrial Company`
   - `BMW Group` → something like `Major German Automotive Company`
3. **Skills preserved**: `SAP S/4HANA`, `ABAP`, `Java`, `Python` should remain as-is
   - This was a bug we fixed today! SAP was being flagged as a 3-letter company name
4. **PII stripped**:
   - No email address in output
   - No phone number in output
   - No LinkedIn URL in output
5. **Education**: University names should remain (they're not PII in this context)
6. **Certifications**: `SAP Certified...` should be preserved (product/cert names, not company PII)

### Option B: Browser upload

1. Navigate to your profile page
2. Look for the CV upload section
3. Upload a real or test CV
4. Check the returned anonymous profile data

### Known edge cases

- **Role titles**: The LLM sometimes puts company names in the `role` field (e.g., "SAP Consultant at Deutsche Bank"). The scrubber catches this but may leave `[REDACTED]` in odd places. This is a known refinement area — not a blocker.
- **Product names that match companies**: "SAP S/4HANA" in a skills field is a product, not a company. We now handle this with `skip_companies=True` for skill fields.

---

## TEST 4: Onboarding State Persistence

### Goal
Verify that onboarding state survives page refreshes and browser restarts.

### Steps

1. Create a fresh user and log in via test-login
2. Open Mira, greet her, she asks for name
3. **Close the browser tab entirely** (or hard refresh)
4. Open `http://localhost:8000/dashboard` again
5. Open Mira, type something
6. **Expected:** Mira should still ask for your name (she knows you haven't set one yet)
7. Set your name → she asks for email
8. **Close the tab again**
9. Re-open dashboard, open Mira, type something
10. **Expected:** Mira should ask for email (she knows name is set but email step not done)

This tests that `get_onboarding_state()` reads from DB, not from session.

---

## TEST 5: DB State Audit

### Goal
Verify the database looks correct after all the testing.

```sql
-- Check all users and their onboarding state
SELECT user_id, email, yogi_name, notification_email,
       notification_consent_at IS NOT NULL AS has_consent,
       onboarding_completed_at IS NOT NULL AS onboarded
FROM users
ORDER BY user_id;

-- Verify unique constraint: try to create a duplicate yogi_name
UPDATE users SET yogi_name = 'Phoenix' WHERE user_id = 1;
-- Should fail with unique constraint violation (if Phoenix is already taken)

-- Check the yogi_messages table for onboarding conversations
SELECT user_id, sender_type, body, created_at
FROM yogi_messages
WHERE user_id = <test_user_id>
ORDER BY created_at;
-- Should show the full conversation: greeting, name prompt, name set, email prompt, etc.
```

---

## TEST 6: Protection Against Regression

Run the full test suite to make sure nothing broke:

```bash
cd ~/Documents/ty_learn
python3 -m pytest tests/ -q
```

Expected: 304 passed, 0 failed.

If you want just the onboarding/privacy tests:
```bash
python3 -m pytest tests/test_onboarding.py -v
```

Expected: 55 passed.

---

## Cleanup After Testing

```sql
-- Remove test users when done (keep Luna=4, Kai=5, Rio=6 for our records)
DELETE FROM yogi_messages WHERE user_id IN (SELECT user_id FROM users WHERE email LIKE 'test-%@example.com');
DELETE FROM users WHERE email LIKE 'test-%@example.com';
```

---

## Summary Checklist

| # | Test | What to look for |
|---|------|-------------------|
| 1 | Fresh onboarding (happy) | Name → email → normal chat |
| 1b | Onboarding (decline email) | Name → "no thanks" → normal chat, no email saved |
| 1c | Onboarding (ignore email) | Name → unrelated message → answers question, onboarding done |
| 2 | Name validation | Rejects short/long/reserved/taken, accepts valid names |
| 3 | CV anonymization | Name replaced, companies generalized, skills preserved, PII stripped |
| 4 | State persistence | Onboarding survives page refresh |
| 5 | DB audit | Correct flags, unique constraints, message history |
| 6 | Regression | 304 tests pass |

---

*Take your time with this. The code isn't going anywhere. Enjoy the swim in the morning if that's what happens first.*
