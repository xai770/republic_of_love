#!/usr/bin/env python3
"""
Test TuringOrchestrator autonomous execution.
Process a few pending tasks to validate the full workflow.
"""
from core.turing_orchestrator import TuringOrchestrator


def main():
    print("=" * 70)
    print("TESTING AUTONOMOUS EXECUTION")
    print("=" * 70)
    print()
    
    # Initialize orchestrator
    orchestrator = TuringOrchestrator(verbose=True)
    
    # Process 3 pending tasks in dry-run mode (no database commits)
    print("\n🤖 Processing 3 pending tasks (dry-run mode)...")
    results = orchestrator.process_pending_tasks(max_tasks=3, dry_run=True)
    
    # Show summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Status: {results['status']}")
    print(f"Tasks found: {results['tasks_found']} types")
    print(f"Items processed: {results['tasks_processed']}")
    print(f"Success count: {results['success_count']}")
    print(f"Success rate: {results['success_count']}/{results['tasks_processed']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
