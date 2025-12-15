#!/bin/bash
# ExecAgent Demo - Show how LLMs can use web commands

echo "================================================================"
echo "ExecAgent Demo - LLM with Web Access"
echo "================================================================"
echo

# Show banner
python3 tools/exec_agent.py --banner

echo
echo "================================================================"
echo "Example: LLM wants to search for information"
echo "================================================================"
echo
echo "LLM Response:"
echo "Let me search for that... {ExecAgent search \"postgresql performance tuning\"}"
echo
echo "After ExecAgent processing:"
echo
echo "Let me search for that... {ExecAgent search \"postgresql performance tuning\"}" | python3 tools/exec_agent.py
echo

echo "================================================================"
echo "Example: LLM wants to check a URL"
echo "================================================================"
echo
echo "LLM Response:"
echo "I'll fetch that page: {ExecAgent curl \"https://api.github.com/zen\"}"
echo
echo "After ExecAgent processing:"
echo
echo "I'll fetch that page: {ExecAgent curl \"https://api.github.com/zen\"}" | python3 tools/exec_agent.py
echo

echo "================================================================"
echo "Example: LLM logs its work"
echo "================================================================"
echo
echo "LLM Response:"
echo "Starting task... {ExecAgent add log \"14:30 Analyzed job posting #123\"}"
echo
echo "After ExecAgent processing:"
echo
echo "Starting task... {ExecAgent add log \"14:30 Analyzed job posting #123\"}" | python3 tools/exec_agent.py
echo

echo "================================================================"
echo "Example: LLM reads its log"
echo "================================================================"
echo
echo "LLM Response:"
echo "Let me check my logs: {ExecAgent read log}"
echo
echo "After ExecAgent processing:"
echo
echo "Let me check my logs: {ExecAgent read log}" | python3 tools/exec_agent.py
echo

echo "================================================================"
echo "✅ Demo Complete!"
echo "================================================================"
