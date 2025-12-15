#!/usr/bin/env python3
"""Quick progress checker for TuringOrchestrator runs"""
from core.turing_orchestrator import TuringOrchestrator

orchestrator = TuringOrchestrator(verbose=False)
pending = orchestrator.discover_pending_tasks()

if pending:
    task = pending[0]
    print(f"📊 Progress Update")
    print(f"   Remaining: {task['count']} jobs")
    print(f"   Sample IDs: {task['sample_ids'][:10]}")
else:
    print("✨ ALL DONE! System is up to date!")
