#!/bin/bash
# 🍽️ LLMCore Restaurant Quick Check
# Convenient wrapper for the restaurant readiness checker

echo "🍽️ Welcome to LLMCore Restaurant!"
echo "Checking if our kitchen is ready for cooking..."
echo

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Change to project root
cd "$PROJECT_ROOT"

# Run the readiness checker using the virtual environment
"$PROJECT_ROOT/venv/bin/python" llmcore/restaurant_readiness_checker.py "$@"

# Store exit code
EXIT_CODE=$?

echo
if [ $EXIT_CODE -eq 0 ]; then
    echo "👨‍🍳 Bon appétit! Your kitchen is ready to serve! ✨"
else
    echo "🔧 Please resolve the issues above before cooking."
fi

exit $EXIT_CODE