# Human-in-Loop Architecture

**Date:** November 24, 2025  
**Status:** 🟡 PROPOSAL - Needs Discussion  
**Author:** Arden  
**For:** xai's review

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## The Requirement

**From Workflow 3003:**
> "When job summary extraction fails quality checks, open ticket to human for review"

**From Sandy's Requirements:**
> "Queue human tasks when execution_type='human_input'"

**Current State:**
- `human_tasks` table exists (EMPTY - 0 rows)
- 3 human actors configured: `arden`, `xai`, `gershon`
- `gershon` has `execution_type='human_input'` with notification config
- NO authentication/identity system documented
- NO personal task queue implementation
- NO workflow pause/resume on human input

---

## Scholar Hat On 🎓: Three Architecture Options

### Option A: Database-Only Queue (Simplest)

**How It Works:**
```
Workflow needs human → Create human_tasks record → Wave Runner pauses that interaction
                     → Human checks database → Updates response field
                     → Workflow resumes with human's input
```

**Schema (Already Exists!):**
```sql
CREATE TABLE human_tasks (
    task_id UUID PRIMARY KEY,
    actor_name TEXT NOT NULL,        -- 'xai', 'arden', 'gershon'
    prompt TEXT NOT NULL,             -- What needs human decision?
    response TEXT,                    -- Human's answer
    status TEXT DEFAULT 'PENDING',    -- PENDING → IN_PROGRESS → COMPLETED
    priority INT DEFAULT 5,           -- 1=urgent, 10=low
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**Workflow Pattern:**
```python
# In AIModelExecutor when quality check fails:
if grade_output == '[FAIL]' and retry_count >= 2:
    # Create human task
    task_id = create_human_task(
        actor_name='xai',  # Route to xai for review
        prompt=f"Summary extraction failed twice. Original job: {job_desc}. Last attempt: {summary}. What should we do?",
        interaction_id=current_interaction_id
    )
    
    # Interaction stays 'pending' until human responds
    return {'status': 'awaiting_human', 'task_id': task_id}

# Human checks their queue:
SELECT * FROM human_tasks WHERE actor_name = 'xai' AND status = 'PENDING';

# Human responds:
UPDATE human_tasks 
SET response = 'Use the improved version from attempt 2', 
    status = 'COMPLETED',
    completed_at = NOW()
WHERE task_id = '...';

# Wave Runner polls, sees completion, resumes workflow
```

**Pros:**
- ✅ Simple - no external dependencies
- ✅ Works with existing schema
- ✅ Personal queues (filter by actor_name)
- ✅ Can implement TODAY (30 minutes)

**Cons:**
- ❌ No real-time notifications (human must poll)
- ❌ No authentication (trust actor_name field)
- ❌ No UI (raw SQL queries to check queue)

**Best For:** Single user (xai) who already has database access

---

### Option B: Database Queue + Email Notifications

**How It Works:**
```
Workflow creates task → Record in human_tasks → Send email to actor
                     → Human clicks link in email → Opens task in... what?
                     → (Still need UI or SQL interface)
```

**Added Components:**
```python
# core/wave_runner_v2/notifications.py (NEW - 50 lines)
import smtplib
from email.message import EmailMessage

def send_task_notification(actor_name: str, task_id: str, prompt: str):
    """Send email notification for new human task."""
    actor_config = get_actor_config(actor_name)
    email = actor_config.get('notification_email')
    
    if not email:
        return  # No email configured
    
    msg = EmailMessage()
    msg['Subject'] = f'New Task: {prompt[:50]}...'
    msg['From'] = 'talent.yoga@example.com'
    msg['To'] = email
    msg.set_content(f"""
    You have a new task:
    
    {prompt}
    
    Task ID: {task_id}
    
    To respond:
    UPDATE human_tasks 
    SET response = 'YOUR ANSWER HERE', status = 'COMPLETED'
    WHERE task_id = '{task_id}';
    """)
    
    # Send via Gmail SMTP
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('talent.yoga@gmail.com', os.environ['GMAIL_PASSWORD'])
        smtp.send_message(msg)
```

**Pros:**
- ✅ Real-time notifications
- ✅ Works with Gmail (you mentioned having this)
- ✅ Still simple database-centric

**Cons:**
- ❌ Still no UI (email tells you to run SQL)
- ❌ Gmail credentials needed
- ❌ Notification sent but response still manual SQL

**Best For:** Small team (2-3 people) who want alerts but are comfortable with SQL

---

### Option C: Full Human-in-Loop Platform (Future-Proof)

**How It Works:**
```
Workflow creates task → Record + notification → by_admin web UI shows task
                     → Human logs in (authentication) → Sees personal inbox
                     → Clicks task → Fills form → Submits response
                     → Workflow resumes automatically
```

**Architecture:**
```
┌─────────────────────────────────────────┐
│ Wave Runner V2                          │
│  └─ Creates human_tasks record          │
│  └─ Sends notification                  │
│  └─ Pauses interaction (status=pending) │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ human_tasks table                       │
│  task_id, actor_name, prompt, response  │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ by_admin Web App (Flask)                │
│  GET  /tasks/mine  → Show my tasks      │
│  POST /tasks/{id}/respond → Submit      │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ Authentication (actors.user_id FK)      │
│  Login → Get actor_name → Filter tasks  │
└─────────────────────────────────────────┘
```

**Components Needed:**
1. **Authentication System** (100 lines)
   - Login page (Flask)
   - Session management
   - Link users → actors table

2. **Task Inbox UI** (200 lines)
   - List tasks for logged-in user
   - Task detail view
   - Response form

3. **Notification System** (100 lines)
   - Email on task creation
   - Link to web UI in email

4. **Workflow Integration** (50 lines)
   - Poll human_tasks for completed responses
   - Resume interaction when response available

**Pros:**
- ✅ Professional user experience
- ✅ Authentication/security built-in
- ✅ Scales to teams
- ✅ Audit trail of who did what

**Cons:**
- ❌ Most complex (400+ lines)
- ❌ Needs `by_admin` app extension
- ❌ 2-3 days implementation
- ❌ Overkill for single user

**Best For:** Production system with multiple human reviewers

---

## My Recommendation: Start with Option A, Migrate to B

**Phase 1 (TODAY - 30 min):** Database-Only Queue
```python
# Add to executors.py
class HumanExecutor:
    def execute(self, actor_name: str, prompt: str, interaction_id: int):
        """Create human task in database."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO human_tasks (actor_name, prompt, interaction_id)
            VALUES (%s, %s, %s)
            RETURNING task_id
        """, (actor_name, prompt, interaction_id))
        
        task_id = cursor.fetchone()[0]
        self.db_conn.commit()
        
        return {
            'status': 'awaiting_human',
            'task_id': str(task_id),
            'message': f'Task created for {actor_name}'
        }

# Add to runner.py
def poll_for_human_responses(self):
    """Check if any human tasks completed."""
    cursor = self.db_conn.cursor()
    cursor.execute("""
        SELECT task_id, response, interaction_id
        FROM human_tasks
        WHERE status = 'COMPLETED'
          AND interaction_id IN (
              SELECT interaction_id FROM interactions
              WHERE status = 'pending'
                AND actor_type = 'human'
          )
    """)
    
    for row in cursor.fetchall():
        # Resume interaction with human's response
        self.complete_interaction(
            interaction_id=row['interaction_id'],
            output={'response': row['response'], 'human_task_id': row['task_id']}
        )
```

**Phase 2 (NEXT WEEK - 2 hours):** Add Email Notifications
- Install: `pip install secure-smtplib`
- Configure Gmail app password
- Add `send_task_notification()` function
- Call on task creation

**Phase 3 (FUTURE - when team grows):** Build Web UI
- Extend `by_admin` app
- Add `/tasks/mine` route
- Add authentication

---

## Questions for xai

1. **Who will be handling human tasks?**
   - Just you? → Option A sufficient
   - You + team? → Consider Option B
   - Production with clients? → Plan for Option C

2. **How urgent are notifications?**
   - Check database daily? → Option A (no notifications)
   - Check email hourly? → Option B (email alerts)
   - Respond in minutes? → Option C (web UI)

3. **Gmail integration preference?**
   - You mentioned "have gmail and have used that before in scripts"
   - Do you have app password ready?
   - Or prefer database-only initially?

4. **Schema changes needed?**
   - Current `human_tasks` table has `session_run_id` (old recipe system)
   - Should we add `interaction_id` column?
   - Should we add `workflow_run_id` column?

---

## Next Steps

**If Option A (Database-Only):**
1. Add `interaction_id` column to `human_tasks`
2. Implement `HumanExecutor.execute()` (30 lines)
3. Implement `poll_for_human_responses()` (40 lines)
4. Test with workflow 3003 failure scenario
5. **Total: 1 hour implementation, 30 min testing**

**If Option B (Database + Email):**
1. Everything in Option A, plus:
2. Configure Gmail credentials in environment
3. Add `notifications.py` module (50 lines)
4. Update `HumanExecutor` to call notification
5. **Total: 2 hours implementation, 30 min testing**

**If Option C (Full Platform):**
1. Design authentication flow
2. Extend `by_admin` app (4 routes)
3. Build task inbox UI
4. Integrate with workflow engine
5. **Total: 2-3 days**

---

## My Vote: Option A for Next Hour

**Why:**
- You're the only human reviewer right now
- Database access is already part of your workflow
- Can upgrade to Option B trivially (just add email function)
- Proven pattern: `human_tasks` table already designed for this

**Test Case:**
```sql
-- Simulate workflow 3003 creating task
INSERT INTO human_tasks (actor_name, prompt, status)
VALUES ('xai', 'Job summary failed quality check. Review and approve?', 'PENDING');

-- You check your queue
SELECT task_id, prompt, created_at 
FROM human_tasks 
WHERE actor_name = 'xai' AND status = 'PENDING';

-- You respond
UPDATE human_tasks 
SET response = 'Approved - use version from attempt 2', 
    status = 'COMPLETED'
WHERE task_id = '...';

-- Workflow resumes
```

Want me to implement Option A right now?
