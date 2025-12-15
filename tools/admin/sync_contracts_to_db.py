#!/usr/bin/env python3
"""
Sync Workflow Contracts to Database
===================================

Reads Python dataclass contracts and syncs them to workflow_variables table.
This keeps the database registry in sync with code contracts.

Usage:
    python tools/sync_contracts_to_db.py [--dry-run]

Author: Arden & xai
Date: 2025-11-06
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts import list_all_contracts
from core.database import get_connection
import argparse
import psycopg2.extras


def sync_contracts(dry_run: bool = False):
    """Sync all registered contracts to database"""
    
    print('\n🔄 SYNCING WORKFLOW CONTRACTS TO DATABASE')
    print('=' * 80)
    
    contracts = list_all_contracts()
    
    if not contracts:
        print('\n⚠️  No contracts registered!')
        print('   Make sure contracts/__init__.py has @register_workflow_contract decorators')
        return
    
    print(f'\n📋 Found {len(contracts)} registered contracts:')
    for workflow_id, contract in contracts.items():
        print(f'   - Workflow {workflow_id}: {contract.workflow_name}')
    
    if dry_run:
        print('\n🔍 DRY RUN MODE - No database changes will be made')
    
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    total_synced = 0
    
    try:
        # Process each contract
        for workflow_id, contract in contracts.items():
            print(f'\n📝 Processing Workflow {workflow_id}: {contract.workflow_name}')
            
            # Get registry rows
            rows = contract.to_registry_rows()
            print(f'   Found {len(rows)} variables to sync')
            
            for row in rows:
                variable_name = row['variable_name']
                scope = row['scope']
                
                # Check if already exists
                cursor.execute("""
                    SELECT variable_id, version, is_current
                    FROM workflow_variables
                    WHERE workflow_id = %s AND variable_name = %s AND scope = %s
                    ORDER BY version DESC
                    LIMIT 1
                """, (workflow_id, variable_name, scope))
                
                existing = cursor.fetchone()
                
                if existing:
                    if dry_run:
                        print(f'   Would update: {scope}.{variable_name} (version {existing["version"]} → {existing["version"] + 1})')
                    else:
                        # Mark old version as not current
                        cursor.execute("""
                            UPDATE workflow_variables
                            SET is_current = false
                            WHERE variable_id = %s
                        """, (existing['variable_id'],))
                        
                        # Insert new version
                        cursor.execute("""
                            INSERT INTO workflow_variables (
                                variable_name, workflow_id, scope, data_type,
                                json_schema, is_required, python_type, description,
                                version, is_current
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true)
                        """, (
                            variable_name, workflow_id, scope, row['data_type'],
                            row['json_schema'], row['is_required'], row['python_type'],
                            row['description'], existing['version'] + 1
                        ))
                        
                        print(f'   ✅ Updated: {scope}.{variable_name} (v{existing["version"] + 1})')
                        total_synced += 1
                else:
                    if dry_run:
                        print(f'   Would create: {scope}.{variable_name}')
                    else:
                        # Insert new variable
                        cursor.execute("""
                            INSERT INTO workflow_variables (
                                variable_name, workflow_id, scope, data_type,
                                json_schema, is_required, python_type, description,
                                version, is_current
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, true)
                        """, (
                            variable_name, workflow_id, scope, row['data_type'],
                            row['json_schema'], row['is_required'], row['python_type'],
                            row['description']
                        ))
                        
                        print(f'   ✅ Created: {scope}.{variable_name}')
                        total_synced += 1
        
        if not dry_run:
            conn.commit()
            print(f'\n✅ Synced {total_synced} variables to database')
        else:
            print(f'\n🔍 Dry run complete - would sync {total_synced} variables')
        
        # Show contract summary
        print(f'\n📊 CONTRACT SUMMARY:')
        print('=' * 80)
        
        for workflow_id, contract in contracts.items():
            cursor.execute("""
                SELECT scope, COUNT(*) as count
                FROM workflow_variables
                WHERE workflow_id = %s AND is_current = true
                GROUP BY scope
                ORDER BY scope
            """, (workflow_id,))
            
            counts = {row['scope']: row['count'] for row in cursor.fetchall()}
            
            print(f'\nWorkflow {workflow_id}: {contract.workflow_name}')
            print(f'   Input variables:  {counts.get("input", 0)}')
            print(f'   Output variables: {counts.get("output", 0)}')
    
    except Exception as e:
        print(f'\n❌ ERROR: {e}')
        if not dry_run:
            conn.rollback()
            print('   Transaction rolled back')
        raise
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Sync workflow contracts to database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()
    
    sync_contracts(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
