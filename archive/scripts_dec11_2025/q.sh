#!/bin/bash
# Quick SQL query wrapper for turing database
# Usage: ./q.sh "SELECT * FROM table_name LIMIT 10"

QUERY="$1"

if [ -z "$QUERY" ]; then
    echo "Usage: $0 \"SQL QUERY\""
    echo "Example: $0 \"SELECT * FROM workflow_triggers LIMIT 5\""
    exit 1
fi

# cd to /tmp to avoid "could not change directory" warning when run from user home
cd /tmp
sudo -u postgres psql -d turing -c "$QUERY" --pset pager=off
