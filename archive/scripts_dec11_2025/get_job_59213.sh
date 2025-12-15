#!/bin/bash
# Get job 59213 description for Recipe 1114 test

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga -t -c "
SELECT job_description 
FROM postings 
WHERE job_id = '59213'
" > /tmp/job_59213_description.txt

echo "✅ Saved job description to /tmp/job_59213_description.txt"
echo ""
echo "Preview (first 500 chars):"
head -c 500 /tmp/job_59213_description.txt
echo ""
echo "..."
echo ""
echo "Length: $(wc -c < /tmp/job_59213_description.txt) characters"
