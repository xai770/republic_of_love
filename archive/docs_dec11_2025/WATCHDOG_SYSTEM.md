# Watchdog System - Stuck Interaction Cleanup

**Date:** November 26, 2025  
**Author:** Sandy  
**Status:** Production Ready

---

## Overview

The Watchdog system automatically cleans up interactions and workflow runs that get stuck in "running" state due to process crashes, system failures, or user interruptions.

**Problem it solves:**
- Runner process crashes before marking interaction as completed
- System runs out of memory (OOM killer)
- User interrupts with Ctrl+C
- Ollama/model processes crash
- Network timeouts cause indefinite hangs

**Without watchdog:**
- Interactions stuck in "running" forever
- Workflows appear active but aren't progressing
- Database fills with zombie processes
- Manual cleanup required

**With watchdog:**
- Automatic cleanup every 5 minutes
- Self-healing system
- Clear audit trail
- No manual intervention needed

---

## Architecture

### The Vulnerability

```python
# In core/wave_runner/runner.py - _execute_interaction()

# 1. Interaction marked as 'running'
self.db.claim_interaction(interaction_id, self.runner_id)

# 2. Execution happens (can crash/hang here)
if interaction['actor_type'] == 'ai_model':
    output = self._execute_ai_model(interaction)  # ← VULNERABLE POINT
elif interaction['actor_type'] == 'script':
    output = self._execute_script(interaction)    # ← VULNERABLE POINT

# 3. Only marked 'completed' if step 2 finishes
self.db.update_interaction_success(interaction_id, output)
```

**If the process crashes between steps 1 and 3:**
- Interaction stays in "running" status forever
- No cleanup happens automatically
- Workflow progression blocked

### Why Subprocess Timeouts Aren't Enough

Executors have built-in timeouts:
- AI models: 10 minutes
- Scripts: 5 minutes

But timeouts don't help if:
1. **Process killed externally** - OOM killer, user Ctrl+C
2. **Python process crashes** - No exception raised
3. **Database connection lost** - Can't update status
4. **System shutdown** - No cleanup

### Watchdog Solution

**Independent process that runs periodically:**
- Queries database for stuck interactions
- Marks them as failed with clear error message
- Updates workflow runs accordingly
- Logs all actions for audit trail

**Conservative timeouts:**
- Interactions: 15 minutes (3x normal 5min timeout)
- Workflows: 2 hours (way longer than any expected run)

---

## Implementation

### File: `scripts/watchdog_cleanup.py`

**Configuration:**
```python
MAX_INTERACTION_RUNTIME_MINUTES = 15  # 3x normal timeout
MAX_WORKFLOW_RUNTIME_HOURS = 2        # No workflow should run this long
DRY_RUN = False                        # Set True to test without changes
```

**Functions:**

1. **`cleanup_stuck_interactions()`**
   - Finds interactions in "running" status > 15 minutes
   - Marks as "failed" with descriptive error message
   - Returns count of cleaned interactions

2. **`cleanup_stuck_workflows()`**
   - Finds workflow runs stuck in "running" status
   - Only cleans if they have NO running interactions
   - Marks as "completed"
   - Returns count of cleaned workflows

**Output Example:**
```
================================================================================
WATCHDOG CLEANUP - 2025-11-26 18:20:00
================================================================================
Configuration:
  - Max interaction runtime: 15 minutes
  - Max workflow runtime: 2 hours
  - Dry run: False
================================================================================

[2025-11-26 18:20:00] ⚠️  Found 3 stuck interactions:
  - Interaction 683: stuck for 25.3 minutes
  - Interaction 695: stuck for 18.7 minutes
  - Interaction 701: stuck for 16.2 minutes
[2025-11-26 18:20:00] ✅ Marked 3 stuck interactions as failed

[2025-11-26 18:20:00] ⚠️  Found 2 stuck workflow runs:
  - Workflow 197 (posting 4807): stuck for 2.5 hours
  - Workflow 198 (posting 4808): stuck for 3.1 hours
[2025-11-26 18:20:00] ✅ Marked 2 stuck workflow runs as completed

================================================================================
WATCHDOG SUMMARY:
  - Interactions cleaned: 3
  - Workflows cleaned: 2
  - Total cleaned: 5
================================================================================
```

---

## Deployment

### Option 1: Cron Job (Recommended)

Add to crontab (`crontab -e`):

```bash
# Watchdog: Cleanup stuck interactions every 5 minutes
*/5 * * * * cd /home/xai/Documents/ty_wave && python3 scripts/watchdog_cleanup.py >> logs/watchdog.log 2>&1
```

**Benefits:**
- Runs automatically in background
- Logs all actions to file
- Survives system reboots
- No manual intervention needed

### Option 2: Systemd Timer

Create `/etc/systemd/system/watchdog-cleanup.service`:

```ini
[Unit]
Description=Watchdog Cleanup - Stuck Interactions
After=postgresql.service

[Service]
Type=oneshot
User=xai
WorkingDirectory=/home/xai/Documents/ty_wave
ExecStart=/usr/bin/python3 scripts/watchdog_cleanup.py
StandardOutput=append:/home/xai/Documents/ty_wave/logs/watchdog.log
StandardError=append:/home/xai/Documents/ty_wave/logs/watchdog.log
```

Create `/etc/systemd/system/watchdog-cleanup.timer`:

```ini
[Unit]
Description=Run Watchdog Cleanup every 5 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable watchdog-cleanup.timer
sudo systemctl start watchdog-cleanup.timer
```

### Option 3: Manual Execution

Run on-demand:
```bash
cd /home/xai/Documents/ty_wave
python3 scripts/watchdog_cleanup.py
```

Test with dry-run (see what would be cleaned):
```bash
# Edit script, set DRY_RUN = True, then:
python3 scripts/watchdog_cleanup.py
```

---

## Monitoring

### Log Files

Watchdog logs to: `logs/watchdog.log`

**Check recent activity:**
```bash
tail -100 logs/watchdog.log
```

**Count cleanups in last 24 hours:**
```bash
grep "WATCHDOG SUMMARY" logs/watchdog.log | tail -48
```

**Find when specific interaction was cleaned:**
```bash
grep "Interaction 683" logs/watchdog.log
```

### Database Queries

**Find interactions cleaned by watchdog:**
```sql
SELECT 
    interaction_id,
    conversation_id,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at))::int as duration_seconds,
    output->>'error' as error_message
FROM interactions
WHERE status = 'failed'
  AND output->>'error' LIKE '%watchdog%'
ORDER BY completed_at DESC
LIMIT 20;
```

**Count watchdog interventions by date:**
```sql
SELECT 
    DATE(completed_at) as cleanup_date,
    COUNT(*) as interactions_cleaned
FROM interactions
WHERE status = 'failed'
  AND output->>'error' LIKE '%watchdog%'
GROUP BY DATE(completed_at)
ORDER BY cleanup_date DESC;
```

**Most frequently stuck conversations:**
```sql
SELECT 
    c.conversation_name,
    a.actor_name,
    COUNT(*) as stuck_count
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON i.actor_id = a.actor_id
WHERE i.status = 'failed'
  AND i.output->>'error' LIKE '%watchdog%'
GROUP BY c.conversation_name, a.actor_name
ORDER BY stuck_count DESC
LIMIT 10;
```

---

## Tuning

### Adjust Timeouts

Edit `scripts/watchdog_cleanup.py`:

```python
# More aggressive (faster cleanup, riskier)
MAX_INTERACTION_RUNTIME_MINUTES = 10  # 2x normal timeout
MAX_WORKFLOW_RUNTIME_HOURS = 1        # Shorter window

# More conservative (slower cleanup, safer)
MAX_INTERACTION_RUNTIME_MINUTES = 20  # 4x normal timeout
MAX_WORKFLOW_RUNTIME_HOURS = 4        # Longer window
```

**Recommendation:** Start conservative, tighten based on observed data.

### Adjust Frequency

**More frequent (faster recovery):**
```bash
# Every 2 minutes
*/2 * * * * cd /home/xai/Documents/ty_wave && python3 scripts/watchdog_cleanup.py >> logs/watchdog.log 2>&1
```

**Less frequent (lower overhead):**
```bash
# Every 10 minutes
*/10 * * * * cd /home/xai/Documents/ty_wave && python3 scripts/watchdog_cleanup.py >> logs/watchdog.log 2>&1
```

**Recommendation:** 5 minutes is good balance for production.

---

## Testing

### Dry Run Test

```bash
# Edit watchdog_cleanup.py, set DRY_RUN = True
cd /home/xai/Documents/ty_wave
python3 scripts/watchdog_cleanup.py
```

Should show what would be cleaned without actually doing it.

### Create Test Stuck Interaction

```sql
-- Manually create a stuck interaction for testing
INSERT INTO interactions (
    conversation_id,
    actor_id,
    parent_interaction_id,
    workflow_run_id,
    status,
    started_at,
    input
) VALUES (
    3335,  -- Some conversation
    12,    -- Some actor
    NULL,
    NULL,
    'running',
    NOW() - interval '20 minutes',  -- Stuck for 20 min
    '{"test": "stuck interaction"}'::jsonb
)
RETURNING interaction_id;
```

Wait 5 minutes for cron, or run watchdog manually. Should clean it up.

### Verify Cleanup

```sql
-- Check it was marked as failed
SELECT 
    interaction_id,
    status,
    output->>'error' as error_message
FROM interactions
WHERE interaction_id = <ID_FROM_ABOVE>;
```

---

## Alerts (Optional)

### Email on Cleanup

Add to watchdog script:

```python
def send_alert(interactions_cleaned, workflows_cleaned):
    """Send email when watchdog cleans up stuck processes"""
    if interactions_cleaned + workflows_cleaned == 0:
        return  # Nothing to report
    
    import smtplib
    from email.message import EmailMessage
    
    msg = EmailMessage()
    msg['Subject'] = f'Watchdog Alert: Cleaned {interactions_cleaned + workflows_cleaned} stuck processes'
    msg['From'] = 'watchdog@tywave.com'
    msg['To'] = 'admin@tywave.com'
    msg.set_content(f"""
    Watchdog cleanup summary:
    - Interactions cleaned: {interactions_cleaned}
    - Workflows cleaned: {workflows_cleaned}
    
    Check logs/watchdog.log for details.
    """)
    
    with smtplib.SMTP('localhost') as s:
        s.send_message(msg)
```

### Slack/Discord Webhook

```python
def send_slack_alert(message):
    """Send alert to Slack channel"""
    import requests
    
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    payload = {"text": message}
    requests.post(webhook_url, json=payload)
```

---

## Troubleshooting

### Watchdog Not Running

**Check cron status:**
```bash
# See recent cron jobs
grep CRON /var/log/syslog | tail -20

# Check if watchdog job is scheduled
crontab -l | grep watchdog
```

**Check permissions:**
```bash
# Make script executable
chmod +x scripts/watchdog_cleanup.py

# Check log directory is writable
ls -la logs/
```

### Too Many False Positives

**Symptoms:** Legitimate long-running interactions getting cleaned up

**Solution:** Increase timeout:
```python
MAX_INTERACTION_RUNTIME_MINUTES = 20  # Was 15
```

### Watchdog Itself Getting Stuck

**Very rare, but possible if database is unresponsive**

Add timeout to cron:
```bash
*/5 * * * * timeout 60 python3 /path/to/watchdog_cleanup.py >> logs/watchdog.log 2>&1
```

Watchdog will be killed after 60 seconds if it hangs.

---

## Production Metrics

**From Nov 26, 2025 cleanup:**

| Metric | Value | Notes |
|--------|-------|-------|
| Stuck interactions cleaned | 12 | First cleanup |
| Oldest stuck | 31.8 hours | Job fetcher |
| Most common stuck actor | db_job_fetcher (8) | API timeout issues |
| Second most common | gemma2:latest (3) | LLM hangs |
| Workflow runs cleaned | 75 | Cascading effect |

**Recommendations based on data:**
1. Investigate db_job_fetcher timeouts (8/12 stuck interactions)
2. Review gemma2:latest stability (3/12 stuck interactions)
3. Consider adding heartbeat to long-running actors

---

## Future Enhancements

### Priority 1: Heartbeat System

**Problem:** Current system can't distinguish between:
- Legitimately long-running interaction (e.g., 12-minute model inference)
- Actually stuck interaction

**Solution:** Runner updates heartbeat every 30 seconds:

```sql
ALTER TABLE interactions ADD COLUMN last_heartbeat TIMESTAMP;

-- Watchdog checks heartbeat instead of start time
WHERE status = 'running'
  AND last_heartbeat < NOW() - interval '2 minutes'
```

**Benefit:** More accurate detection of stuck processes

### Priority 2: Graceful Shutdown

**Problem:** Ctrl+C leaves interactions in running state

**Solution:** Catch SIGTERM/SIGINT in runner:

```python
import signal

def cleanup_on_exit(signum, frame):
    """Mark all running interactions as failed on shutdown"""
    self.db.execute("""
        UPDATE interactions 
        SET status = 'failed', 
            output = '{"error": "Runner shutdown gracefully"}'
        WHERE status = 'running' 
          AND runner_id = %s
    """, (self.runner_id,))
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup_on_exit)
signal.signal(signal.SIGINT, cleanup_on_exit)
```

### Priority 3: Dead Letter Queue

**Problem:** Repeatedly failing interactions get retried forever

**Solution:** Track failure count, move to DLQ after N failures:

```sql
ALTER TABLE interactions ADD COLUMN retry_count INT DEFAULT 0;

-- In watchdog
UPDATE interactions
SET retry_count = retry_count + 1
WHERE status = 'failed' AND output->>'error' LIKE '%watchdog%';

-- Move to DLQ if too many retries
UPDATE interactions
SET status = 'dead_letter'
WHERE retry_count > 3;
```

---

## Summary

**What it does:**
- Automatically cleans up stuck interactions every 5 minutes
- Self-healing system that prevents database pollution
- Clear audit trail of all cleanup actions

**How to deploy:**
```bash
# Add to crontab
crontab -e
# Add line:
*/5 * * * * cd /home/xai/Documents/ty_wave && python3 scripts/watchdog_cleanup.py >> logs/watchdog.log 2>&1
```

**How to monitor:**
```bash
# Check logs
tail -100 logs/watchdog.log

# Query database
SELECT COUNT(*) FROM interactions 
WHERE output->>'error' LIKE '%watchdog%';
```

**When to tune:**
- Too many false positives → Increase timeout
- Too slow recovery → Decrease timeout or increase frequency
- Specific actors stuck → Investigate root cause, not just cleanup

---

**Status:** Production ready  
**Last updated:** November 26, 2025  
**Maintained by:** Sandy
