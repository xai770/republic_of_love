#!/usr/bin/env python3
"""
archive_tickets_to_files.py - Export old tickets to JSON files, then delete from DB

Policy: Tickets older than 30 days get exported to JSON files (one per day),
        then deleted from the database. Files can go on USB backup.

Output: backups/tickets_archive/tickets_YYYYMMDD.json.gz (gzipped JSON)

Usage:
    ./scripts/archive_tickets_to_files.py                    # Dry run
    ./scripts/archive_tickets_to_files.py --execute          # Actually archive
    ./scripts/archive_tickets_to_files.py --age-days 60      # Custom age threshold
    ./scripts/archive_tickets_to_files.py --output-dir /mnt/usb/archive  # Custom path

Author: Arden (fixing Sandy's basement-to-basement approach)
Date: 2026-02-02
"""

import argparse
import gzip
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection_raw as get_connection

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "backups" / "tickets_archive"


def json_serializer(obj):
    """Handle non-JSON-serializable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (bytes, bytearray)):
        return obj.decode('utf-8', errors='replace')
    raise TypeError(f"Type {type(obj)} not serializable")


def get_archivable_dates(conn, age_days: int):
    """Get list of dates that have archivable tickets."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE(created_at) as ticket_date, COUNT(*) as count
        FROM tickets
        WHERE created_at < NOW() - INTERVAL '%s days'
          AND status IN ('completed', 'failed', 'skipped', 'invalidated')
        GROUP BY DATE(created_at)
        ORDER BY ticket_date
    """, (age_days,))
    return cur.fetchall()


def export_day_to_file(conn, ticket_date, output_dir: Path, execute: bool) -> tuple[int, str]:
    """Export tickets from a single day to a gzipped JSON file.
    
    Returns (count, filepath) tuple.
    """
    cur = conn.cursor()
    
    # Fetch all tickets for this date
    cur.execute("""
        SELECT 
            ticket_id, subject_type, subject_id, actor_id, actor_type,
            batch_id, status, input, output, error_message,
            retry_count, max_retries, execution_order,
            parent_ticket_id, input_ticket_ids,
            enabled, invalidated,
            created_at, updated_at, started_at, completed_at
        FROM tickets
        WHERE DATE(created_at) = %s
          AND status IN ('completed', 'failed', 'skipped', 'invalidated')
        ORDER BY ticket_id
    """, (ticket_date,))
    
    rows = cur.fetchall()
    if not rows:
        return 0, None
    
    # Convert to list of dicts
    tickets = []
    for row in rows:
        tickets.append({
            'ticket_id': row['ticket_id'],
            'subject_type': row['subject_type'],
            'subject_id': row['subject_id'],
            'actor_id': row['actor_id'],
            'actor_type': row['actor_type'],
            'batch_id': row['batch_id'],
            'status': row['status'],
            'input': row['input'],
            'output': row['output'],
            'error_message': row['error_message'],
            'retry_count': row['retry_count'],
            'max_retries': row['max_retries'],
            'execution_order': row['execution_order'],
            'parent_ticket_id': row['parent_ticket_id'],
            'input_ticket_ids': row['input_ticket_ids'],
            'enabled': row['enabled'],
            'invalidated': row['invalidated'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'started_at': row['started_at'],
            'completed_at': row['completed_at'],
        })
    
    # Build archive metadata
    archive_data = {
        'archive_version': '1.0',
        'archived_at': datetime.now().isoformat(),
        'ticket_date': str(ticket_date),
        'ticket_count': len(tickets),
        'status_counts': {},
        'tickets': tickets
    }
    
    # Count by status
    for t in tickets:
        status = t['status']
        archive_data['status_counts'][status] = archive_data['status_counts'].get(status, 0) + 1
    
    # Generate filename
    date_str = ticket_date.strftime('%Y%m%d')
    filename = f"tickets_{date_str}.json.gz"
    filepath = output_dir / filename
    
    if execute:
        # Write gzipped JSON
        output_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump(archive_data, f, default=json_serializer, indent=2)
    
    return len(tickets), filepath


def delete_archived_tickets(conn, ticket_date) -> int:
    """Delete tickets for a date after successful archive."""
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM tickets
        WHERE DATE(created_at) = %s
          AND status IN ('completed', 'failed', 'skipped', 'invalidated')
    """, (ticket_date,))
    return cur.rowcount


def archive_tickets(execute: bool = False, age_days: int = 30, output_dir: Path = None):
    """Main archive function."""
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    
    conn = get_connection()
    
    # Get dates to archive
    dates = get_archivable_dates(conn, age_days)
    
    total_tickets = sum(row['count'] for row in dates)
    
    print(f"Tickets older than {age_days} days:")
    print(f"  Dates to archive: {len(dates)}")
    print(f"  Total tickets:    {total_tickets:,}")
    print(f"  Output directory: {output_dir}")
    print()
    
    if not dates:
        print("Nothing to archive!")
        conn.close()
        return
    
    # Show date range
    print(f"  Date range: {dates[0]['ticket_date']} to {dates[-1]['ticket_date']}")
    print()
    
    if not execute:
        print("DRY RUN - No changes made. Use --execute to archive.")
        print()
        print("Would create files:")
        for row in dates[:5]:
            date_str = row['ticket_date'].strftime('%Y%m%d')
            print(f"  tickets_{date_str}.json.gz ({row['count']:,} tickets)")
        if len(dates) > 5:
            print(f"  ... and {len(dates) - 5} more files")
        conn.close()
        return
    
    print("Archiving (one file per day)...")
    print()
    
    total_exported = 0
    total_deleted = 0
    files_created = []
    
    for row in dates:
        ticket_date = row['ticket_date']
        expected_count = row['count']
        date_str = ticket_date.strftime('%Y-%m-%d')
        
        try:
            # Export to file
            count, filepath = export_day_to_file(conn, ticket_date, output_dir, execute=True)
            
            if count != expected_count:
                print(f"  WARNING: {date_str} - Expected {expected_count}, got {count}")
            
            # Verify file exists and has reasonable size
            if not filepath.exists():
                raise Exception(f"File not created: {filepath}")
            
            file_size = filepath.stat().st_size
            if file_size < 100:  # Sanity check
                raise Exception(f"File too small ({file_size} bytes): {filepath}")
            
            # Delete from DB (same transaction per day for safety)
            deleted = delete_archived_tickets(conn, ticket_date)
            conn.commit()
            
            total_exported += count
            total_deleted += deleted
            files_created.append(filepath)
            
            # Progress output
            size_kb = file_size / 1024
            print(f"  {date_str}: {count:,} tickets → {filepath.name} ({size_kb:.1f} KB) ✓")
            
        except Exception as e:
            print(f"  {date_str}: ERROR - {e}")
            conn.rollback()
            # Continue with next date
    
    conn.close()
    
    print()
    print(f"Done!")
    print(f"  Files created:  {len(files_created)}")
    print(f"  Tickets saved:  {total_exported:,}")
    print(f"  Rows deleted:   {total_deleted:,}")
    print()
    
    # Show total archive size
    total_size = sum(f.stat().st_size for f in files_created)
    if total_size > 1024 * 1024 * 1024:
        size_str = f"{total_size / (1024*1024*1024):.2f} GB"
    elif total_size > 1024 * 1024:
        size_str = f"{total_size / (1024*1024):.1f} MB"
    else:
        size_str = f"{total_size / 1024:.1f} KB"
    
    print(f"  Archive size:   {size_str}")
    print(f"  Location:       {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='Archive old tickets to JSON files')
    parser.add_argument('--execute', action='store_true',
                        help='Actually archive (default is dry run)')
    parser.add_argument('--age-days', type=int, default=30,
                        help='Archive tickets older than N days (default: 30)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})')
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    archive_tickets(
        execute=args.execute,
        age_days=args.age_days,
        output_dir=output_dir
    )


if __name__ == '__main__':
    main()
