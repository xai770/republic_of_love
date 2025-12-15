#!/usr/bin/env python3
"""
Wave Runner Daemon - Persistent workflow execution service

Runs continuously, polling for pending interactions across all workflows.
Designed to run as a systemd service or via supervisor.

Features:
- Polls every 5 seconds for pending work
- Processes all workflows in global_batch mode  
- Graceful shutdown on SIGTERM/SIGINT
- Auto-reloads Python code on changes (optional)
- Health endpoint (future)

Usage:
    python3 scripts/wave_runner_daemon.py
    python3 scripts/wave_runner_daemon.py --poll-interval 10

To run as systemd service, create /etc/systemd/system/wave-runner.service:
    [Unit]
    Description=Wave Runner Daemon
    After=postgresql.service

    [Service]
    Type=simple
    User=xai
    WorkingDirectory=/home/xai/Documents/ty_learn
    ExecStart=/usr/bin/python3 scripts/wave_runner_daemon.py
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target

Author: Arden (guidance) + Sandy (implementation)
Date: December 7, 2025
"""

import sys
import os
import time
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.wave_runner.runner import WaveRunner


class WaveRunnerDaemon:
    """Persistent wave runner that polls for work."""
    
    def __init__(
        self,
        poll_interval: int = 5,
        max_batch_size: int = 50,
        idle_log_interval: int = 60
    ):
        """
        Initialize daemon.
        
        Args:
            poll_interval: Seconds between polls when no work
            max_batch_size: Max interactions per run() call
            idle_log_interval: Log "idle" message every N seconds
        """
        self.poll_interval = poll_interval
        self.max_batch_size = max_batch_size
        self.idle_log_interval = idle_log_interval
        self.running = True
        self.last_idle_log = 0
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        
        # Load environment
        load_dotenv(project_root / '.env')
        
        self.logger.info("Wave Runner Daemon initialized")
        self.logger.info(f"  Poll interval: {poll_interval}s")
        self.logger.info(f"  Max batch size: {max_batch_size}")
    
    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        log_dir = project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        logger = logging.getLogger('wave_runner_daemon')
        logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(log_dir / 'wave_runner_daemon.log')
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name}, shutting down...")
        self.running = False
    
    def _get_connection(self):
        """Create database connection."""
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', 5432),
            database=os.getenv('DB_NAME', 'turing'),
            user=os.getenv('DB_USER', 'base_admin'),
            password=os.getenv('DB_PASSWORD', '')
        )
    
    def _count_pending(self, conn) -> int:
        """Count pending interactions."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM interactions 
            WHERE status = 'pending'
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    
    def run(self):
        """Main daemon loop."""
        self.logger.info("Starting Wave Runner Daemon loop...")
        
        conn = None
        stats_total = {
            'interactions_completed': 0,
            'interactions_failed': 0,
            'runs': 0
        }
        
        while self.running:
            try:
                # Get/refresh connection
                if conn is None or conn.closed:
                    conn = self._get_connection()
                    self.logger.info("Database connection established")
                
                # Check for pending work
                pending_count = self._count_pending(conn)
                
                if pending_count == 0:
                    # No work - log idle status periodically
                    now = time.time()
                    if now - self.last_idle_log >= self.idle_log_interval:
                        self.logger.info("Idle - no pending interactions")
                        self.last_idle_log = now
                    
                    time.sleep(self.poll_interval)
                    continue
                
                # Work available - run the wave runner
                self.logger.info(f"Found {pending_count} pending interactions")
                
                runner = WaveRunner(
                    db_conn=conn,
                    runner_id=f"daemon_{int(time.time())}",
                    global_batch=True  # Process all workflows
                )
                
                result = runner.run(
                    max_iterations=100,
                    max_interactions=self.max_batch_size
                )
                
                # Update stats
                stats_total['interactions_completed'] += result.get('interactions_completed', 0)
                stats_total['interactions_failed'] += result.get('interactions_failed', 0)
                stats_total['runs'] += 1
                
                self.logger.info(
                    f"Run complete: {result.get('interactions_completed', 0)} completed, "
                    f"{result.get('interactions_failed', 0)} failed "
                    f"(total: {stats_total['interactions_completed']} completed)"
                )
                
                # Short pause before next poll
                time.sleep(1)
                
            except psycopg2.Error as e:
                self.logger.error(f"Database error: {e}")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                conn = None
                time.sleep(self.poll_interval)
                
            except Exception as e:
                self.logger.exception(f"Unexpected error: {e}")
                time.sleep(self.poll_interval)
        
        # Cleanup
        if conn:
            conn.close()
        
        self.logger.info(
            f"Daemon stopped. Total: {stats_total['interactions_completed']} completed, "
            f"{stats_total['interactions_failed']} failed over {stats_total['runs']} runs"
        )


def main():
    parser = argparse.ArgumentParser(description='Wave Runner Daemon')
    parser.add_argument('--poll-interval', type=int, default=5,
                        help='Seconds between polls (default: 5)')
    parser.add_argument('--max-batch-size', type=int, default=50,
                        help='Max interactions per run (default: 50)')
    parser.add_argument('--idle-log-interval', type=int, default=60,
                        help='Seconds between idle log messages (default: 60)')
    
    args = parser.parse_args()
    
    daemon = WaveRunnerDaemon(
        poll_interval=args.poll_interval,
        max_batch_size=args.max_batch_size,
        idle_log_interval=args.idle_log_interval
    )
    
    daemon.run()


if __name__ == '__main__':
    main()
