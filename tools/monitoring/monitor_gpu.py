#!/usr/bin/env python3
"""
GPU Memory Monitor - Track Ollama model loading over time

Runs `ollama ps` every 60 seconds and logs:
- Which models are loaded
- Memory usage per model
- Total GPU memory consumption
- Timestamps for correlation with wave processing

Usage:
    # Run in background
    python3 tools/monitor_gpu.py &
    
    # Run with custom interval
    python3 tools/monitor_gpu.py --interval 30
    
    # View logs
    tail -f logs/gpu_usage_$(date +%Y-%m-%d).log
"""

import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
import argparse
import re


def get_ollama_status():
    """Run ollama ps and parse output with validation"""
    try:
        result = subprocess.run(
            ['ollama', 'ps'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return {'error': f'ollama ps failed: {result.stderr}'}
        
        lines = result.stdout.strip().split('\n')
        
        if len(lines) < 2:  # Header + at least one model
            return {'models': [], 'total_models': 0, 'status': 'no_models_loaded'}
        
        # Parse models with validation
        models = []
        for line_num, line in enumerate(lines[1:], start=2):
            parts = line.split()
            
            # Validate line format
            if len(parts) < 3:
                print(f"Warning: Skipping malformed line {line_num}: {line}")
                continue
            
            # Validate model name format (alphanumeric:version)
            model_name = parts[0]
            if not re.match(r'^[\w\-\.]+:[\w\.\-]+$', model_name):
                print(f"Warning: Invalid model name format on line {line_num}: {model_name}")
                continue
            
            # Extract fields with defaults
            models.append({
                'name': model_name,
                'id': parts[1] if len(parts) > 1 else 'unknown',
                'size': parts[2] if len(parts) > 2 else 'unknown',
                'processor': parts[3] if len(parts) > 3 else 'unknown',
                'until': ' '.join(parts[4:]) if len(parts) > 4 else ''
            })
        
        return {
            'models': models,
            'total_models': len(models),
            'status': 'ok',
            'raw_output': result.stdout
        }
        
    except subprocess.TimeoutExpired:
        return {'error': 'ollama ps timeout (>5s)', 'status': 'timeout'}
    except FileNotFoundError:
        return {'error': 'ollama not found - is it installed?', 'status': 'not_found'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}', 'status': 'error'}


def log_gpu_status(log_path):
    """Get GPU status and append to log file with error handling"""
    timestamp = datetime.now()
    status = get_ollama_status()
    
    log_entry = {
        'timestamp': timestamp.isoformat(),
        'unix_time': timestamp.timestamp(),
        **status
    }
    
    # Append to daily log file
    log_file = log_path / f"gpu_usage_{timestamp.strftime('%Y-%m-%d')}.log"
    
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except IOError as e:
        print(f"ERROR: Failed to write log: {e}")
        return log_entry
    
    # Print to stdout for debugging
    if 'error' in status:
        print(f"[{timestamp.strftime('%H:%M:%S')}] ❌ ERROR: {status['error']}")
    elif status.get('status') == 'no_models_loaded':
        print(f"[{timestamp.strftime('%H:%M:%S')}] ⚪ No models loaded")
    else:
        model_names = [m['name'] for m in status.get('models', [])]
        if model_names:
            print(f"[{timestamp.strftime('%H:%M:%S')}] ✅ Loaded: {', '.join(model_names)}")
    
    return log_entry


def main():
    parser = argparse.ArgumentParser(description='Monitor GPU memory usage via ollama ps')
    parser.add_argument('--interval', type=int, default=60, 
                       help='Check interval in seconds (default: 60)')
    parser.add_argument('--log-dir', type=str, default='logs',
                       help='Log directory (default: logs/)')
    
    args = parser.parse_args()
    
    # Setup log directory
    log_path = Path('/home/xai/Documents/ty_learn') / args.log_dir
    log_path.mkdir(exist_ok=True)
    
    print(f"GPU Monitor started - logging every {args.interval}s")
    print(f"Log directory: {log_path}")
    print(f"Press Ctrl+C to stop\n")
    
    try:
        while True:
            log_gpu_status(log_path)
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n\nGPU monitoring stopped.")


if __name__ == '__main__':
    main()
