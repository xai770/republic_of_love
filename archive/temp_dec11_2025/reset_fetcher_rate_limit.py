#!/usr/bin/env python3
from core.database import get_connection, return_connection

conn = get_connection()
cursor = conn.cursor()

# Reset last_run_at to 25 hours ago (bypasses 24-hour rate limit)
cursor.execute("""
    UPDATE actors
    SET execution_config = jsonb_set(
        execution_config,
        '{last_run_at}',
        to_jsonb(NOW() - INTERVAL '25 hours')
    )
    WHERE actor_name = 'db_job_fetcher'
    RETURNING actor_name, execution_config->'last_run_at' as new_last_run
""")

result = cursor.fetchone()
conn.commit()

print(f"✅ Reset {result['actor_name']} rate limit")
print(f"   New last_run_at: {result['new_last_run']} (25 hours ago)")
print()
print("Fetcher ready to run on next workflow execution!")

return_connection(conn)
