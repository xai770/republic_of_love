#!/usr/bin/env python3
"""
Test Recipe 1114 with a real job posting from the database
"""
import psycopg2
import psycopg2.extras
import subprocess
import sys

DB_CONFIG = {
    'host': 'localhost',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'database': 'base_yoga'
}

def get_real_posting(posting_id=None):
    """Fetch a real job posting from the database"""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()
    
    if posting_id:
        cursor.execute("""
            SELECT job_id, job_title, job_description, organization_name, 
                   location_city, location_state
            FROM postings 
            WHERE job_id = %s AND enabled = TRUE
        """, (str(posting_id),))
    else:
        # Get a random posting
        cursor.execute("""
            SELECT job_id, job_title, job_description, organization_name,
                   location_city, location_state
            FROM postings 
            WHERE enabled = TRUE 
              AND job_description IS NOT NULL
              AND LENGTH(job_description) > 500
            ORDER BY RANDOM()
            LIMIT 1
        """)
    
    posting = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return posting

def run_recipe_with_posting(posting):
    """Run Recipe 1114 with the posting data"""
    print("=" * 80)
    print("🎯 TESTING RECIPE 1114 WITH REAL JOB POSTING")
    print("=" * 80)
    print(f"Job ID: {posting['job_id']}")
    print(f"Title: {posting['job_title']}")
    print(f"Organization: {posting['organization_name']}")
    print(f"Location: {posting['location_city']}, {posting['location_state']}")
    print(f"Description Length: {len(posting['job_description'])} characters")
    print("=" * 80)
    print()
    
    # Run the recipe
    result = subprocess.run(
        [
            'python3', 
            'scripts/by_recipe_runner.py',
            '--recipe-id', '1114',
            '--job-id', posting['job_id'],  # Pass job_id so it saves to postings table
            '--test-data', posting['job_description'],
            '--execution-mode', 'testing',  # Use testing mode to allow re-runs
            '--target-batch-count', '5'  # Required for testing mode
        ],
        capture_output=False,
        text=True
    )
    
    return result.returncode == 0

def main():
    posting_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    posting = get_real_posting(posting_id)
    
    if not posting:
        print("❌ No posting found!")
        sys.exit(1)
    
    success = run_recipe_with_posting(posting)
    
    if success:
        print("\n✅ Recipe completed successfully!")
    else:
        print("\n❌ Recipe execution failed")
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
