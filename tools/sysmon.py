#!/usr/bin/env python3
"""
sysmon.py - System Monitor for AI assistant visibility

Usage:
    python3 tools/sysmon.py              # One-shot stats
    python3 tools/sysmon.py --watch      # Continuous (5s interval)
    python3 tools/sysmon.py --watch -i 2 # Custom interval
    python3 tools/sysmon.py --gpu        # GPU only
    python3 tools/sysmon.py --daemon     # Background mode (writes to logs/sysmon.log)
"""

import argparse
import subprocess
import time
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def get_gpu_stats():
    """Get NVIDIA GPU stats."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = [p.strip() for p in result.stdout.strip().split(',')]
            return {
                'gpu_util': f"{parts[0]}%",
                'mem_util': f"{parts[1]}%", 
                'vram_used': f"{int(float(parts[2]))}MB",
                'vram_total': f"{int(float(parts[3]))}MB",
                'temp': f"{parts[4]}°C",
                'power': f"{parts[5]}W" if len(parts) > 5 else "N/A"
            }
    except Exception as e:
        return {'error': str(e)}
    return None

def get_cpu_stats():
    """Get CPU usage."""
    try:
        # Get load average
        load = os.getloadavg()
        
        # Get CPU count
        cpu_count = os.cpu_count() or 1
        
        return {
            'load_1m': f"{load[0]:.1f}",
            'load_5m': f"{load[1]:.1f}",
            'load_15m': f"{load[2]:.1f}",
            'cores': cpu_count,
            'load_pct': f"{(load[0] / cpu_count) * 100:.0f}%"
        }
    except Exception as e:
        return {'error': str(e)}

def get_memory_stats():
    """Get RAM usage."""
    try:
        with open('/proc/meminfo') as f:
            mem = {}
            for line in f:
                parts = line.split()
                key = parts[0].rstrip(':')
                mem[key] = int(parts[1]) // 1024  # KB to MB
        
        total = mem.get('MemTotal', 0)
        available = mem.get('MemAvailable', 0)
        used = total - available
        
        return {
            'used': f"{used}MB",
            'total': f"{total}MB",
            'available': f"{available}MB",
            'pct': f"{(used / total) * 100:.0f}%" if total else "N/A"
        }
    except Exception as e:
        return {'error': str(e)}

def get_disk_stats():
    """Get disk usage for project root."""
    try:
        stat = os.statvfs(PROJECT_ROOT)
        total = (stat.f_blocks * stat.f_frsize) // (1024**3)
        free = (stat.f_bavail * stat.f_frsize) // (1024**3)
        used = total - free
        return {
            'used': f"{used}GB",
            'total': f"{total}GB",
            'free': f"{free}GB",
            'pct': f"{(used / total) * 100:.0f}%" if total else "N/A"
        }
    except Exception as e:
        return {'error': str(e)}

def get_ollama_status():
    """Check if Ollama is running and what model is loaded."""
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/tags'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            models = [m['name'] for m in data.get('models', [])]
            return {'status': 'running', 'models': len(models)}
    except:
        pass
    return {'status': 'not running'}

def get_daemon_status():
    """Check if turing-daemon is running."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'pull_daemon.py'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return {'status': 'running', 'pids': pids}
    except:
        pass
    return {'status': 'stopped'}

def format_stats(gpu=True, cpu=True, mem=True, disk=False, services=True):
    """Format all stats into a readable string."""
    lines = []
    ts = datetime.now().strftime('%H:%M:%S')
    
    if gpu:
        g = get_gpu_stats()
        if g and 'error' not in g:
            lines.append(f"GPU: {g['gpu_util']} util | {g['vram_used']}/{g['vram_total']} VRAM | {g['temp']} | {g['power']}")
        elif g:
            lines.append(f"GPU: {g.get('error', 'N/A')}")
    
    if cpu:
        c = get_cpu_stats()
        if c and 'error' not in c:
            lines.append(f"CPU: {c['load_pct']} ({c['load_1m']}/{c['load_5m']}/{c['load_15m']} load, {c['cores']} cores)")
    
    if mem:
        m = get_memory_stats()
        if m and 'error' not in m:
            lines.append(f"RAM: {m['pct']} ({m['used']}/{m['total']})")
    
    if disk:
        d = get_disk_stats()
        if d and 'error' not in d:
            lines.append(f"Disk: {d['pct']} ({d['used']}/{d['total']}, {d['free']} free)")
    
    if services:
        daemon = get_daemon_status()
        ollama = get_ollama_status()
        svc_line = f"Services: daemon={daemon['status']}"
        if daemon['status'] == 'running':
            svc_line += f"(PIDs: {','.join(daemon['pids'])})"
        svc_line += f" | ollama={ollama['status']}"
        if ollama['status'] == 'running':
            svc_line += f"({ollama['models']} models)"
        lines.append(svc_line)
    
    return f"[{ts}] " + " | ".join(lines) if len(lines) == 1 else f"[{ts}]\n  " + "\n  ".join(lines)

def main():
    parser = argparse.ArgumentParser(description='System monitor')
    parser.add_argument('--watch', '-w', action='store_true', help='Continuous monitoring')
    parser.add_argument('--interval', '-i', type=int, default=5, help='Watch interval (seconds)')
    parser.add_argument('--gpu', '-g', action='store_true', help='GPU only')
    parser.add_argument('--daemon', '-d', action='store_true', help='Background mode (log to file)')
    parser.add_argument('--compact', '-c', action='store_true', help='Single line output')
    args = parser.parse_args()
    
    log_file = None
    if args.daemon:
        log_path = PROJECT_ROOT / 'logs' / 'sysmon.log'
        log_file = open(log_path, 'a')
        print(f"Logging to {log_path}")
    
    def output(text):
        if log_file:
            log_file.write(text + '\n')
            log_file.flush()
        else:
            print(text)
    
    try:
        if args.watch or args.daemon:
            while True:
                if args.gpu:
                    g = get_gpu_stats()
                    output(f"[{datetime.now().strftime('%H:%M:%S')}] GPU: {g['gpu_util']} | {g['vram_used']}/{g['vram_total']} | {g['temp']}")
                else:
                    output(format_stats(disk=not args.compact, services=not args.compact))
                time.sleep(args.interval)
        else:
            if args.gpu:
                g = get_gpu_stats()
                print(f"GPU: {g['gpu_util']} util | {g['vram_used']}/{g['vram_total']} VRAM | {g['temp']} | {g['power']}")
            else:
                print(format_stats(disk=True))
    except KeyboardInterrupt:
        pass
    finally:
        if log_file:
            log_file.close()

if __name__ == '__main__':
    main()
