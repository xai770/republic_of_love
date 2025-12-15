#!/bin/bash
# LLMCore Markdown Report Generator - Quick Script
# Usage: ./generate_md_report.sh [output_filename]

echo "🚀 LLMCore Markdown Report Generator"
echo "===================================="
echo

# Change to project directory
cd "$(dirname "$0")"

# Check if database exists
if [ ! -f "data/llmcore.db" ]; then
    echo "❌ Error: Database file 'data/llmcore.db' not found!"
    echo "   Please ensure you're in the correct directory and the database exists."
    exit 1
fi

# Run the Python report generator
echo "📊 Generating comprehensive Markdown report..."
python3 llmcore_markdown_report_generator.py

# Check if report was generated successfully
if [ $? -eq 0 ]; then
    echo
    echo "✅ Success! Report generated successfully."
    
    # Find the most recent report file
    REPORT_FILE=$(ls -t llmcore_report_*.md 2>/dev/null | head -1)
    
    if [ -n "$REPORT_FILE" ]; then
        echo "📄 Report file: $REPORT_FILE"
        echo "📁 Full path: $(pwd)/$REPORT_FILE"
        echo
        echo "🎯 Next steps:"
        echo "  1. Review the report: cat $REPORT_FILE"
        echo "  2. Share with team: Send $REPORT_FILE to Sage, Sophia, Dexi"
        echo "  3. Archive report: mv $REPORT_FILE reports/ (if you have a reports folder)"
        echo
        echo "📊 Report stats:"
        wc -l "$REPORT_FILE" | awk '{print "  Lines: " $1}'
        wc -w "$REPORT_FILE" | awk '{print "  Words: " $1}'
        wc -c "$REPORT_FILE" | awk '{print "  Characters: " $1}'
        echo
        echo "🔍 Preview first few lines:"
        echo "=========================="
        head -20 "$REPORT_FILE"
        echo "=========================="
        echo "(... full report in $REPORT_FILE)"
    else
        echo "⚠️  Warning: Could not find generated report file"
    fi
else
    echo "❌ Error: Report generation failed!"
    echo "   Check the error messages above for details."
    exit 1
fi

echo
echo "🎉 Report generation complete! Ready to share with the team!"