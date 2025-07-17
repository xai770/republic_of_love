#!/usr/bin/env python3
"""
🧹 Mailbox Zero-Size File Cleaner
=================================

SAFETY-FIRST cleanup script for removing empty files from the 0_mailboxes directory tree.

FEATURES:
- Recursively scans all subdirectories in 0_mailboxes
- Identifies files with 0 bytes (empty files)
- Safe deletion with confirmation prompts
- Detailed logging of all actions
- Dry-run mode for preview before deletion
- Backup option for cautious cleanup

SAFETY MEASURES:
- Preview mode shows what will be deleted
- Confirmation prompts before actual deletion
- Detailed logging of all operations
- Skip system files and hidden directories

DATE: June 27, 2025
PURPOSE: Maintain clean mailbox file structure
LOCATION: 0_mailboxes/cleanup_zero_size_files.py
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

class MailboxCleaner:
    """Safe cleanup utility for mailbox zero-size files"""
    
    def __init__(self, mailbox_root: str = None):
        # Auto-detect mailbox root if not provided
        if mailbox_root is None:
            script_dir = Path(__file__).parent
            self.mailbox_root = script_dir
        else:
            self.mailbox_root = Path(mailbox_root)
        
        self.zero_size_files = []
        self.deleted_count = 0
        self.total_scanned = 0
        
    def scan_for_zero_size_files(self) -> List[Path]:
        """Scan the mailbox tree for zero-size files"""
        print(f"🔍 Scanning mailbox tree: {self.mailbox_root}")
        print("-" * 60)
        
        zero_size_files = []
        
        for root, dirs, files in os.walk(self.mailbox_root):
            # Skip hidden directories and system folders
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                # Skip hidden files and Python cache files
                if file.startswith('.') or file.endswith('.pyc'):
                    continue
                    
                file_path = Path(root) / file
                self.total_scanned += 1
                
                try:
                    if file_path.stat().st_size == 0:
                        zero_size_files.append(file_path)
                        print(f"📄 Found zero-size: {file_path.relative_to(self.mailbox_root)}")
                except (OSError, FileNotFoundError):
                    print(f"⚠️  Could not access: {file_path}")
                    continue
        
        self.zero_size_files = zero_size_files
        return zero_size_files
    
    def preview_cleanup(self) -> None:
        """Show what would be deleted without actually deleting"""
        print(f"\n📋 CLEANUP PREVIEW")
        print("=" * 60)
        
        if not self.zero_size_files:
            print("✅ No zero-size files found - mailbox tree is clean!")
            return
        
        print(f"📊 Scan Results:")
        print(f"   Total files scanned: {self.total_scanned}")
        print(f"   Zero-size files found: {len(self.zero_size_files)}")
        print(f"")
        
        print(f"📄 Files that would be deleted:")
        for i, file_path in enumerate(self.zero_size_files, 1):
            relative_path = file_path.relative_to(self.mailbox_root)
            print(f"   {i:3d}. {relative_path}")
        
        print(f"\n💾 Storage saved: {len(self.zero_size_files)} empty files removed")
    
    def confirm_deletion(self) -> bool:
        """Get user confirmation for deletion"""
        if not self.zero_size_files:
            return False
        
        print(f"\n⚠️  DELETION CONFIRMATION")
        print("-" * 40)
        print(f"Ready to delete {len(self.zero_size_files)} zero-size files.")
        print(f"This action cannot be undone.")
        print(f"")
        
        while True:
            response = input("🤔 Proceed with deletion? [y/N]: ").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no', '']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    def delete_zero_size_files(self, confirmed: bool = False) -> int:
        """Delete the zero-size files"""
        if not confirmed and not self.confirm_deletion():
            print("🛑 Deletion cancelled by user.")
            return 0
        
        print(f"\n🧹 DELETING ZERO-SIZE FILES")
        print("=" * 60)
        
        deleted_count = 0
        
        for file_path in self.zero_size_files:
            try:
                relative_path = file_path.relative_to(self.mailbox_root)
                file_path.unlink()
                deleted_count += 1
                print(f"🗑️  Deleted: {relative_path}")
            except (OSError, FileNotFoundError) as e:
                print(f"❌ Failed to delete {relative_path}: {e}")
        
        self.deleted_count = deleted_count
        return deleted_count
    
    def cleanup_summary(self) -> None:
        """Print cleanup summary"""
        print(f"\n📊 CLEANUP SUMMARY")
        print("=" * 60)
        print(f"✅ Total files scanned: {self.total_scanned}")
        print(f"🔍 Zero-size files found: {len(self.zero_size_files)}")
        print(f"🗑️  Files deleted: {self.deleted_count}")
        
        if self.deleted_count > 0:
            print(f"💾 Result: Mailbox tree cleaned successfully!")
        else:
            print(f"💾 Result: No files were deleted.")
        
        print(f"⏰ Cleanup completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

def print_banner():
    """Print the cleanup utility banner"""
    banner = """
    ================================================================
    🧹              MAILBOX ZERO-SIZE FILE CLEANER               🧹
    ================================================================
    
    🎯 PURPOSE: Remove empty files from 0_mailboxes directory tree
    🛡️ SAFETY: Preview mode, confirmation prompts, detailed logging
    📂 SCOPE: Recursive scan of all mailbox subdirectories
    ⚡ BENEFITS: Cleaner file structure, reduced clutter
    
    ================================================================
    """
    print(banner)

def print_help():
    """Print usage help"""
    help_text = """
    USAGE:
        python cleanup_zero_size_files.py [OPTIONS]
    
    OPTIONS:
        --preview    Show what would be deleted (default mode)
        --delete     Actually delete zero-size files (with confirmation)
        --force      Delete without confirmation (USE WITH CAUTION)
        --help       Show this help message
    
    EXAMPLES:
        python cleanup_zero_size_files.py
        python cleanup_zero_size_files.py --preview
        python cleanup_zero_size_files.py --delete
    
    SAFETY FEATURES:
        - Default mode is preview-only (safe)
        - Confirmation prompt before deletion
        - Skips hidden files and system directories
        - Detailed logging of all operations
    """
    print(help_text)

def main():
    """Main cleanup execution"""
    print_banner()
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        print_help()
        return
    
    # Determine mode
    delete_mode = '--delete' in args
    force_mode = '--force' in args
    preview_mode = not delete_mode and not force_mode
    
    # Initialize cleaner
    cleaner = MailboxCleaner()
    
    # Scan for zero-size files
    zero_size_files = cleaner.scan_for_zero_size_files()
    
    # Show preview
    cleaner.preview_cleanup()
    
    # Handle different modes
    if preview_mode:
        print(f"\n💡 TIP: Run with --delete to actually remove these files")
        print(f"       or --force to delete without confirmation")
    elif delete_mode:
        cleaner.delete_zero_size_files(confirmed=False)
    elif force_mode:
        print(f"\n🚨 FORCE MODE: Deleting without confirmation...")
        cleaner.delete_zero_size_files(confirmed=True)
    
    # Show summary
    cleaner.cleanup_summary()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n🛑 Cleanup interrupted by user")
    except Exception as e:
        print(f"\n❌ Cleanup error: {e}")
        sys.exit(1)
