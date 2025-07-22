#!/usr/bin/env python3
"""
LLM Optimization Progress Monitor
================================

Monitor the progress of ongoing LLM optimization experiments.

Author: Arden
Date: 2025-07-20
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

def monitor_optimization_progress():
    """Monitor the progress of LLM optimization experiments"""
    
    results_dir = Path("llm_optimization_results")
    
    print("🔍 LLM Optimization Progress Monitor")
    print("=" * 50)
    print(f"Monitoring directory: {results_dir}")
    print(f"Started at: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    if not results_dir.exists():
        print("⏳ Waiting for optimization to start...")
        return
    
    # Find all session directories
    session_dirs = [d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith("session_")]
    
    if not session_dirs:
        print("⏳ No sessions found yet...")
        return
    
    print(f"📊 Found {len(session_dirs)} active/completed sessions:")
    print()
    
    for session_dir in sorted(session_dirs):
        model_name = session_dir.name.split("_", 2)[-1].replace("_", ":")
        print(f"🔬 Model: {model_name}")
        
        # Check session data
        session_file = session_dir / "session_data.json"
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                iterations = session_data.get("iterations", [])
                final_results = session_data.get("final_results", {})
                
                print(f"   📈 Iterations completed: {len(iterations)}")
                
                if iterations:
                    latest_score = iterations[-1].get("score", 0)
                    print(f"   🎯 Latest score: {latest_score:.2f}")
                
                if final_results:
                    best_score = final_results.get("best_score", 0)
                    total_iterations = final_results.get("total_iterations", 0)
                    successful = final_results.get("optimization_successful", False)
                    
                    print(f"   🏆 Best score: {best_score:.2f}")
                    print(f"   ✅ Completed: {total_iterations} iterations")
                    print(f"   🎉 Success: {successful}")
                else:
                    print(f"   ⏳ Status: In progress...")
                
            except Exception as e:
                print(f"   ❌ Error reading session data: {e}")
        else:
            print(f"   ⏳ Status: Starting...")
        
        print()
    
    # Check for suite results
    suite_files = list(results_dir.glob("optimization_suite_*.json"))
    if suite_files:
        latest_suite = max(suite_files, key=lambda x: x.stat().st_mtime)
        print("🏆 SUITE RESULTS AVAILABLE!")
        print(f"📄 File: {latest_suite.name}")
        
        try:
            with open(latest_suite, 'r') as f:
                suite_data = json.load(f)
            
            summary = suite_data.get("summary", {})
            best_model = summary.get("best_model")
            best_score = summary.get("best_average_score", 0)
            
            if best_model:
                print(f"🥇 Best Model: {best_model}")
                print(f"📊 Best Average Score: {best_score:.2f}")
                
                rankings = summary.get("model_rankings", [])
                if rankings:
                    print("\n📈 Model Rankings:")
                    for i, ranking in enumerate(rankings, 1):
                        model = ranking.get("model", "Unknown")
                        score = ranking.get("average_score", 0)
                        successful = ranking.get("successful_optimizations", 0)
                        print(f"   {i}. {model}: {score:.2f} avg ({successful} successful)")
        
        except Exception as e:
            print(f"❌ Error reading suite results: {e}")

if