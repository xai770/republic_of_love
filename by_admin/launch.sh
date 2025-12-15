#!/bin/bash
# Quick launch script for LLMCore Admin GUI

echo "🏛️ Starting LLMCore Admin GUI..."

# Navigate to the admin directory
cd "$(dirname "$0")"

# Check if dependencies are installed
if ! python3 -c "import streamlit, pandas" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if database exists
DB_PATH="../data/llmcore.db"
if [ ! -f "$DB_PATH" ]; then
    echo "⚠️  Warning: Database not found at $DB_PATH"
    echo "   Make sure you're in the correct directory and the database exists."
    exit 1
fi

echo "🚀 Launching application..."
echo "   Database: $DB_PATH"
echo "   URL: http://localhost:8501"
echo ""
echo "💡 Use Ctrl+C to stop the server"

# Launch Streamlit
streamlit run app.py