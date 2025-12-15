#!/bin/bash
# Quick system health check

echo "================================"
echo "Turing System Health Check"
echo "================================"
echo ""

# Load environment
export $(cat /home/xai/Documents/ty_learn/.env | grep -v '^#' | xargs)

# Database connection
echo "🔍 Testing database connection..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\pset pager off" -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database: Connected"
else
    echo "❌ Database: Connection failed"
    exit 1
fi

# Workflow doc triggers
echo ""
echo "🔍 Checking workflow doc triggers..."
TRIGGER_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE '%workflow%' AND tgrelid = 'workflow_conversations'::regclass;")
if [ "$TRIGGER_COUNT" -eq 1 ]; then
    echo "✅ Triggers: 1 trigger on workflow_conversations (correct)"
else
    echo "⚠️  Triggers: Found $TRIGGER_COUNT triggers (expected 1)"
fi

# GPU status
echo ""
echo "🔍 Checking GPU/Ollama status..."
if command -v ollama &> /dev/null; then
    MODEL_COUNT=$(ollama ps 2>/dev/null | tail -n +2 | wc -l)
    echo "✅ Ollama: Running ($MODEL_COUNT models loaded)"
else
    echo "⚠️  Ollama: Not found or not running"
fi

# Virtual environment
echo ""
echo "🔍 Checking Python environment..."
if [ -d "/home/xai/Documents/ty_learn/venv" ]; then
    echo "✅ Venv: Exists"
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "✅ Venv: Activated ($VIRTUAL_ENV)"
    else
        echo "⚠️  Venv: Not activated (run: source venv/bin/activate)"
    fi
else
    echo "❌ Venv: Not found"
fi

# Workflow status
echo ""
echo "🔍 Checking workflow 3001 status..."
PENDING=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM postings WHERE enabled = TRUE AND job_description IS NOT NULL AND extracted_summary IS NULL;")
COMPLETED=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM postings WHERE enabled = TRUE AND extracted_summary IS NOT NULL;")
echo "📊 Workflow 3001: $COMPLETED completed, $PENDING pending"

echo ""
echo "================================"
echo "Health check complete!"
echo "================================"
