#!/usr/bin/env python3
from core.database import get_connection, return_connection
from datetime import datetime, timedelta

conn = get_connection()
cursor = conn.cursor()

# Get actor config
cursor.execute("""
    SELECT actor_id, actor_name, execution_config
    FROM actors
    WHERE actor_name = 'db_job_fetcher'
""")
actor = cursor.fetchone()

last_run = actor['execution_config'].get('last_run_at')
rate_limit_hours = actor['execution_config'].get('rate_limit_hours', 24)

print(f"Actor: {actor['actor_name']}")
print(f"Last run: {last_run}")
print(f"Rate limit: {rate_limit_hours} hours")

if last_run:
    from dateutil import parser
    last_run_dt = parser.parse(last_run)
    now = datetime.now(last_run_dt.tzinfo)
    hours_since = (now - last_run_dt).total_seconds() / 3600
    hours_until_ready = rate_limit_hours - hours_since
    
    print(f"Hours since last run: {hours_since:.1f}")
    print(f"Hours until ready: {hours_until_ready:.1f}")
    print()
    
    if hours_until_ready > 0:
        print(f"❌ RATE LIMITED - wait {hours_until_ready:.1f} more hours")
        print(f"   Next run available at: {last_run_dt + timedelta(hours=rate_limit_hours)}")
        print()
        print("To bypass rate limit:")
        print("  python3 temp/reset_fetcher_rate_limit.py")
    else:
        print(f"✅ Ready to run!")

return_connection(conn)
