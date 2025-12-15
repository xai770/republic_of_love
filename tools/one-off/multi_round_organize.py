#!/usr/bin/env python3
"""
Multi-Round Root Organizer
===========================

When AI can't assign all root categories in one shot (working memory limits),
this runs multiple rounds until everything is organized.

Each round:
1. Count unassigned folders at root
2. If >15: run AI organization on remaining items
3. Repeat until all assigned
"""

import os
import subprocess
import time
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def count_root_folders(taxonomy_path):
    """Count folders at root (excluding organized groups and backups)"""
    count = 0
    for item in os.listdir(taxonomy_path):
        if item.startswith('.') or item.endswith('.backup') or item in ['README.md', '_README.md']:
            continue
        item_path = taxonomy_path / item
        if item_path.is_dir():
            count += 1
    return count

def run_organizer_round(round_num):
    """Run one round of organization"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}ROUND {round_num}: Organizing remaining root categories{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
    
    result = subprocess.run(
        ['python3', 'tools/recursive_organize_infinite.py',
         '--folder-threshold', '15',
         '--file-threshold', '25',
         '--max-folders', '8',
         '--max-iterations', '25'],
        capture_output=True,
        text=True,
        timeout=3600  # 1 hour max per round
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print(f"{Colors.YELLOW}⚠️  Round {round_num} had issues{Colors.END}")
        print(result.stderr)
    
    return result.returncode == 0

def main():
    taxonomy_path = Path('skills_taxonomy')
    max_rounds = 5
    
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}MULTI-ROUND ROOT ORGANIZER{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    for round_num in range(1, max_rounds + 1):
        # Count current state
        folder_count = count_root_folders(taxonomy_path)
        
        print(f"{Colors.GREEN}Current state: {folder_count} folders at root{Colors.END}")
        
        if folder_count <= 15:
            print(f"\n{Colors.GREEN}✅ Root level organized! ({folder_count} ≤ 15){Colors.END}")
            print(f"{Colors.GREEN}Now running deep organization on subfolders...{Colors.END}\n")
            # Run one final pass with skip-root to organize deeper levels
            subprocess.run([
                'python3', 'tools/recursive_organize_infinite.py',
                '--folder-threshold', '15',
                '--file-threshold', '25',
                '--max-folders', '8',
                '--max-iterations', '25',
                '--skip-root'
            ])
            break
        
        # Run organization round
        success = run_organizer_round(round_num)
        
        if not success:
            print(f"\n{Colors.YELLOW}Round {round_num} failed, stopping{Colors.END}")
            break
        
        # Check if we made progress
        new_count = count_root_folders(taxonomy_path)
        
        if new_count >= folder_count:
            print(f"\n{Colors.YELLOW}⚠️  No progress made (still {new_count} folders){Colors.END}")
            print(f"{Colors.YELLOW}Stopping to avoid infinite loop{Colors.END}")
            break
        
        print(f"\n{Colors.GREEN}Progress: {folder_count} → {new_count} folders{Colors.END}")
        
        if round_num < max_rounds:
            print(f"{Colors.CYAN}Waiting 2 seconds before next round...{Colors.END}")
            time.sleep(2)
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}MULTI-ROUND ORGANIZATION COMPLETE{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    final_count = count_root_folders(taxonomy_path)
    print(f"{Colors.GREEN}Final: {final_count} folders at root level{Colors.END}\n")

if __name__ == '__main__':
    main()
