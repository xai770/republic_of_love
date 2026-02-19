"""
Script Sync - Drift detection and auto-sync for script actors
Author: Sandy (GitHub Copilot)
Date: November 23, 2025
Target: <100 lines

Prevents crashes from stale/deleted scripts by detecting drift between
filesystem and database, then auto-syncing on startup.
"""

import hashlib
import logging
import psycopg2.extras
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class ScriptSyncManager:
    """Manages script actor code synchronization with drift detection."""
    
    def __init__(self, db_conn, base_dir: Path, logger=None):
        """
        Initialize script sync manager.
        
        Args:
            db_conn: Database connection
            base_dir: Base directory for script files (e.g., /home/xai/Documents/ty_wave)
            logger: Optional logger
        """
        self.conn = db_conn
        self.base_dir = Path(base_dir)
        self.logger = logger or logging.getLogger(__name__)
    
    def get_file_hash(self, filepath: Path) -> Optional[str]:
        """
        Calculate SHA256 hash of file contents.
        
        Args:
            filepath: Path to file
            
        Returns:
            Hex string of SHA256 hash, or None if file doesn't exist
        """
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except FileNotFoundError:
            return None
    
    def check_for_drift(self, actor_id: int) -> Dict[str, Any]:
        """
        Check if script file has drifted from database version.
        
        Args:
            actor_id: Actor ID to check
            
        Returns:
            {
                'has_drift': bool,
                'drift_type': 'file_modified' | 'file_missing' | 'synced',
                'db_hash': str,
                'file_hash': str | None,
                'file_path': str
            }
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT script_file_path, script_code_hash
            FROM actors
            WHERE actor_id = %s AND actor_type = 'script'
        """, (actor_id,))
        
        row = cursor.fetchone()
        if not row:
            return {'has_drift': False, 'drift_type': 'not_script_actor'}
        
        script_file_path = row['script_file_path']
        db_hash = row['script_code_hash']
        
        if not script_file_path:
            return {'has_drift': False, 'drift_type': 'no_file_path'}
        
        # Get absolute path
        abs_path = self.base_dir / script_file_path
        file_hash = self.get_file_hash(abs_path)
        
        if file_hash is None:
            return {
                'has_drift': True,
                'drift_type': 'file_missing',
                'db_hash': db_hash,
                'file_hash': None,
                'file_path': str(abs_path)
            }
        
        if file_hash != db_hash:
            return {
                'has_drift': True,
                'drift_type': 'file_modified',
                'db_hash': db_hash,
                'file_hash': file_hash,
                'file_path': str(abs_path)
            }
        
        return {
            'has_drift': False,
            'drift_type': 'synced',
            'db_hash': db_hash,
            'file_hash': file_hash,
            'file_path': str(abs_path)
        }
    
    def sync_actor_to_database(self, actor_id: int) -> bool:
        """
        Sync script actor from filesystem to database.
        
        Creates history record and updates actors table.
        
        Args:
            actor_id: Actor ID to sync
            
        Returns:
            True if synced successfully, False otherwise
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get script file path
        cursor.execute("""
            SELECT script_file_path, actor_name
            FROM actors
            WHERE actor_id = %s AND actor_type = 'script'
        """, (actor_id,))
        
        row = cursor.fetchone()
        if not row:
            self.logger.warning(f"Actor {actor_id} is not a script actor")
            return False
        
        script_file_path = row['script_file_path']
        actor_name = row['actor_name']
        
        if not script_file_path:
            self.logger.warning(f"Actor {actor_id} has no script_file_path")
            return False
        
        # Read script file
        abs_path = self.base_dir / script_file_path
        try:
            with open(abs_path, 'r') as f:
                script_code = f.read()
        except FileNotFoundError:
            self.logger.error(f"Script file not found: {abs_path}")
            # Update sync status
            cursor.execute("""
                UPDATE actors
                SET script_sync_status = 'file_missing'
                WHERE actor_id = %s
            """, (actor_id,))
            self.conn.commit()
            return False
        
        # Calculate hash
        file_hash = hashlib.sha256(script_code.encode()).hexdigest()
        
        # Create history record
        cursor.execute("""
            INSERT INTO actor_code_history (
                actor_id, script_code, script_code_hash,
                change_type, source_file_path
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING history_id
        """, (actor_id, script_code, file_hash, 'auto_sync', script_file_path))
        
        history_id = cursor.fetchone()['history_id']
        
        # Update actors table
        cursor.execute("""
            UPDATE actors
            SET script_code = %s,
                script_code_hash = %s,
                script_sync_status = 'synced',
                active_history_id = %s
            WHERE actor_id = %s
        """, (script_code, file_hash, history_id, actor_id))
        
        self.conn.commit()
        
        self.logger.info(f"Synced actor {actor_id} ({actor_name}) - hash: {file_hash[:8]}...")
        return True
    
    def sync_all_script_actors(self) -> int:
        """
        Sync all script actors on startup.
        
        Returns:
            Number of actors synced
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get all ENABLED script actors with file paths
        # Skip disabled/deprecated actors to avoid drift warnings
        cursor.execute("""
            SELECT actor_id, actor_name, script_file_path
            FROM actors
            WHERE actor_type = 'script' 
              AND script_file_path IS NOT NULL
              AND enabled = true
        """)
        
        script_actors = cursor.fetchall()
        synced_count = 0
        
        for row in script_actors:
            actor_id = row['actor_id']
            actor_name = row['actor_name']
            script_file_path = row['script_file_path']
            
            # Check for drift
            drift_info = self.check_for_drift(actor_id)
            
            if drift_info['has_drift']:
                self.logger.warning(
                    f"Drift detected for actor {actor_id} ({actor_name}): "
                    f"{drift_info['drift_type']}"
                )
                
                # Auto-sync
                if self.sync_actor_to_database(actor_id):
                    synced_count += 1
        
        if synced_count > 0:
            self.logger.info(f"Auto-synced {synced_count} script actors on startup")
        else:
            self.logger.info("All script actors in sync")
        
        return synced_count
