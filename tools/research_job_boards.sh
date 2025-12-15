#!/bin/bash
# Demo: Research Job Boards using ExecAgent
# Shows how LLMs can search the web AND consult other AI models

echo "=================================================="
echo "ExecAgent Research Demo: Job Board APIs"
echo "=================================================="
echo ""

echo "Step 1: Search the web for job board APIs"
echo "--------------------------------------------------"
python3 tools/exec_agent.py --command 'search "job board APIs for developers"'
echo ""

echo "Step 2: Ask local AI model for recommendations"
echo "--------------------------------------------------"
python3 tools/exec_agent.py --command 'ask granite3.1-moe:3b "What are the best free job board APIs? List 3 with reasons. Be concise."'
echo ""

echo "Step 3: Get details from specific API"
echo "--------------------------------------------------"
python3 tools/exec_agent.py --command 'curl "https://publicapis.dev/category/jobs"'
echo ""

echo "Step 4: Log research session"
echo "--------------------------------------------------"
python3 tools/exec_agent.py --command 'add log "Researched job board APIs - found FindWork, Greenhouse, RapidAPI as top options"'
echo ""

echo "=================================================="
echo "Research Complete!"
echo "=================================================="
echo ""
echo "This demonstrates:"
echo "  ✅ Web search with ddgr (real results from DuckDuckGo)"
echo "  ✅ AI consultation (local Ollama models)"
echo "  ✅ Direct API access (curl for structured data)"
echo "  ✅ Session logging (track research progress)"
echo ""
echo "Next steps:"
echo "  • Integrate job board APIs into Turing"
echo "  • Build skill matching against live job postings"
echo "  • Compare our extracted skills vs. job requirements"
