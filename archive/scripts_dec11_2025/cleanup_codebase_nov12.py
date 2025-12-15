#!/usr/bin/env python3
"""
Codebase Cleanup - November 12, 2025
====================================
Clean up obsolete files, duplicates, and cruft to keep codebase focused.

Philosophy: Clean room now = glad later!
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

DRY_RUN = False  # Set to False to actually execute

# Base directory
BASE = Path('/home/xai/Documents/ty_learn')
ARCHIVE_BASE = BASE / 'archive' / 'cleanup_nov12_2025'

def safe_delete(path, reason):
    """Delete file/dir with logging"""
    if DRY_RUN:
        print(f'  [DRY RUN] Would delete: {path.relative_to(BASE)} ({reason})')
        return False
    
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f'  ✓ Deleted: {path.relative_to(BASE)} ({reason})')
        return True
    except Exception as e:
        print(f'  ✗ Failed: {path.relative_to(BASE)} - {e}')
        return False

def safe_move(src, dst, reason):
    """Move file/dir with logging"""
    if DRY_RUN:
        print(f'  [DRY RUN] Would move: {src.relative_to(BASE)} → {dst.relative_to(BASE)} ({reason})')
        return False
    
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f'  ✓ Moved: {src.relative_to(BASE)} → {dst.relative_to(BASE)} ({reason})')
        return True
    except Exception as e:
        print(f'  ✗ Failed: {src.relative_to(BASE)} - {e}')
        return False

def cleanup_pycache():
    """Remove all __pycache__ directories and .pyc files"""
    print('\n' + '=' * 70)
    print('1. CLEANING __pycache__ AND .pyc FILES')
    print('=' * 70)
    
    pycache_dirs = list(BASE.rglob('__pycache__'))
    pyc_files = [f for f in BASE.rglob('*.pyc') if '__pycache__' not in str(f)]
    
    print(f'Found {len(pycache_dirs)} __pycache__ dirs, {len(pyc_files)} orphan .pyc files')
    print()
    
    deleted = 0
    for path in pycache_dirs:
        if safe_delete(path, 'pycache'):
            deleted += 1
    
    for path in pyc_files:
        if safe_delete(path, 'orphan pyc'):
            deleted += 1
    
    print(f'\n✅ Cleaned {deleted} cache files/dirs')

def cleanup_tools():
    """Clean up tools/ directory"""
    print('\n' + '=' * 70)
    print('2. CLEANING tools/ DIRECTORY')
    print('=' * 70)
    
    tools = BASE / 'tools'
    archive_tools = ARCHIVE_BASE / 'tools'
    
    # Files to DELETE (completely obsolete)
    delete_files = [
        # Compiled workflows (don't save to DB, misleading)
        'fake_job_detector_compiled.py',
        'complete_job_processing_pipeline_compiled.py',
        'taxonomy_maintenance_(turing_native)_compiled.py',
        
        # IHL legacy (all superseded by TuringOrchestrator + batch_ihl_scorer.py)
        'backfill_ihl_scores.py',
        'benchmark_ihl_performance.py',
        'process_ihl_partition.py',
        'process_ihl_optimized.py',
        'process_ihl_results.py',
        'rerun_failed_ihl.py',
        
        # Batch processor duplicates (keep batch_ihl_scorer.py only)
        'batch_run_ihl.py',
        'process_ihl_stage_batched.py',
        'smart_ihl_batch.py',
        'gentle_batch_processor.py',
        'batch_submit_all_postings.py',
        
        # Taxonomy legacy (old organization approaches)
        'recursive_organize_infinite.py',
        'recursive_meta_structure.py',
        'apply_meta_structure.py',
        'design_meta_structure.py',
        'deduplicate_taxonomy.py',
        'build_semantic_hierarchy.py',
        
        # Obsolete tools
        '_document_workflow.py',
        'flatten_single_child_folders.py',
        'export_skills_to_folders.py',
        'fetch_descriptions_selenium.py',
        'match_profile_to_jobs.py',
        'save_extracted_skills.py',
        'build_skill_hierarchy_variants.py',
        'generate_skills_qa_report.py',
        'save_skills.py',
        'multi_model_skill_extractor.py',
        'generate_ihl_report.py',
        'taxonomy_gopher.py',
        'recipe_report.py',
        'create_recipe_1115.py',
        'create_recipe.py',
        'parse_ticket_from_session.py',
        'sandy_submit_job.py',
        'export_recipe_to_production.py',
        'prompt_cli.py',
        'prompt_versioning.py',
    ]
    
    # Files to ARCHIVE (one-time migration helpers)
    archive_files = [
        'populate_location_from_metadata.py',
        'import_deutsche_bank_worldwide.py',
        'fetch_workday_descriptions.py',
        'update_country_data.py',
        'import_588_jobs.py',
        'import_deutsche_bank_v2.py',
        'update_external_urls.py',
        'update_workday_urls.py',
        'fetch_from_web_ui_api.py',
        'fetch_all_german_jobs.py',
        'update_runner_schema.py',
        'interrogate_job_source.py',
    ]
    
    print(f'\nDeleting {len(delete_files)} obsolete files...')
    deleted = 0
    for filename in delete_files:
        path = tools / filename
        if path.exists():
            if safe_delete(path, 'obsolete'):
                deleted += 1
    
    print(f'\nArchiving {len(archive_files)} migration helpers...')
    archived = 0
    for filename in archive_files:
        src = tools / filename
        if src.exists():
            dst = archive_tools / 'migration_helpers' / filename
            if safe_move(src, dst, 'one-time migration'):
                archived += 1
    
    print(f'\n✅ Deleted {deleted} files, Archived {archived} files')

def cleanup_scripts():
    """Clean up scripts/ directory"""
    print('\n' + '=' * 70)
    print('3. CLEANING scripts/ DIRECTORY')
    print('=' * 70)
    
    scripts = BASE / 'scripts'
    archive_scripts = ARCHIVE_BASE / 'scripts'
    
    # Archive old recipe creation scripts (superseded by TuringOrchestrator)
    archive_files = [
        'create_recipe_1118.py',
        'create_recipe_1119.py',
    ]
    
    archived = 0
    for filename in archive_files:
        src = scripts / filename
        if src.exists():
            dst = archive_scripts / 'old_recipe_creators' / filename
            if safe_move(src, dst, 'old recipe creator'):
                archived += 1
    
    print(f'✅ Archived {archived} files')
    print(f'✅ Keeping: cleanup_workspace_nov12.py (this session)')
    print(f'✅ Keeping: hybrid_skill_extraction.py (THE BRIDGE - active)')

def cleanup_empty_dirs():
    """Remove empty directories"""
    print('\n' + '=' * 70)
    print('4. CLEANING EMPTY DIRECTORIES')
    print('=' * 70)
    
    # Directories that should be removed if empty
    check_dirs = [
        BASE / 'extraction',
        BASE / 'production',
    ]
    
    removed = 0
    for dir_path in check_dirs:
        if dir_path.exists() and dir_path.is_dir():
            # Check if truly empty (no files, only maybe __pycache__)
            contents = [f for f in dir_path.rglob('*') if '__pycache__' not in str(f) and f.name != '.gitkeep']
            if not contents:
                if safe_delete(dir_path, 'empty directory'):
                    removed += 1
    
    print(f'✅ Removed {removed} empty directories')

def cleanup_monitor_scripts():
    """Clean up redundant monitoring scripts"""
    print('\n' + '=' * 70)
    print('5. CLEANING MONITOR SCRIPTS')
    print('=' * 70)
    
    tools = BASE / 'tools'
    
    # Multiple monitor scripts - consolidate
    delete_files = [
        'monitor_batch.sh',
        'monitor_ihl_batch.sh',
        'monitor_ihl_progress.sh',
        'monitor_parallel_progress.sh',
    ]
    
    deleted = 0
    for filename in delete_files:
        path = tools / filename
        if path.exists():
            if safe_delete(path, 'redundant - use check_progress.py'):
                deleted += 1
    
    print(f'✅ Deleted {deleted} redundant monitor scripts')
    print(f'   Use check_progress.py or batch_ihl_scorer.py --status instead')

def summarize_remaining():
    """Show what's left after cleanup"""
    print('\n' + '=' * 70)
    print('FINAL STRUCTURE')
    print('=' * 70)
    
    dirs_count = {
        'tools': len(list((BASE / 'tools').glob('*.py'))) if (BASE / 'tools').exists() else 0,
        'scripts': len(list((BASE / 'scripts').glob('*.py'))) if (BASE / 'scripts').exists() else 0,
        'runners': len(list((BASE / 'runners').glob('*.py'))) if (BASE / 'runners').exists() else 0,
        'matching': len(list((BASE / 'matching').glob('*.py'))) if (BASE / 'matching').exists() else 0,
        'interrogators': len(list((BASE / 'interrogators').glob('*.py'))) if (BASE / 'interrogators').exists() else 0,
        'core': len(list((BASE / 'core').glob('*.py'))) if (BASE / 'core').exists() else 0,
    }
    
    for dir_name, count in dirs_count.items():
        if count > 0:
            print(f'  {dir_name:20s} {count:3d} files')
    
    total = sum(dirs_count.values())
    print(f'\n  TOTAL: {total} Python files (focused and clean!)')

def main():
    print('=' * 70)
    print('CODEBASE CLEANUP - November 12, 2025')
    print('=' * 70)
    print(f'Mode: {"DRY RUN (no changes)" if DRY_RUN else "LIVE (will delete/move files)"}')
    print()
    
    if not DRY_RUN:
        response = input('Are you sure you want to proceed? (yes/no): ')
        if response.lower() != 'yes':
            print('Aborted.')
            return
    
    # Execute cleanup steps
    cleanup_pycache()
    cleanup_tools()
    cleanup_scripts()
    cleanup_monitor_scripts()
    cleanup_empty_dirs()
    summarize_remaining()
    
    print('\n' + '=' * 70)
    print('✅ CLEANUP COMPLETE')
    print('=' * 70)
    print(f'Archive location: {ARCHIVE_BASE.relative_to(BASE)}')
    print()
    print('Clean room = Glad later! 🎉')
    print('=' * 70)

if __name__ == '__main__':
    main()
