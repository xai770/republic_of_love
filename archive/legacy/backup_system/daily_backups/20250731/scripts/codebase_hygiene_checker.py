#!/usr/bin/env python3
"""
Codebase Hygiene Checker for TY_Extract Versions

Detects and reports:
- Code duplication (nested directories, duplicate files)
- Zero-size files 
- Orphaned cache directories (__pycache__, .mypy_cache)
- Broken symlinks
- Suspicious file patterns
- Large files that might not belong
- Inconsistent naming patterns

Usage:
    python scripts/codebase_hygiene_checker.py
    python scripts/codebase_hygiene_checker.py --fix-auto  # Auto-fix safe issues
    python scripts/codebase_hygiene_checker.py --target modules/ty_extract_versions/ty_extract_v9.0_optimized
"""

import os
import sys
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional, Any
import json

class CodebaseHygieneChecker:
    def __init__(self, root_path: str, auto_fix: bool = False):
        self.root_path = Path(root_path)
        self.auto_fix = auto_fix
        self.issues: Dict[str, List[Dict[str, Any]]] = {
            'duplicates': [],
            'zero_files': [],
            'cache_dirs': [],
            'broken_links': [],
            'large_files': [],
            'suspicious_patterns': [],
            'nested_duplicates': []
        }
        
        # File patterns to ignore
        self.ignore_patterns = {
            '.git', '.gitignore', '__pycache__', '.mypy_cache',
            '.pytest_cache', 'node_modules', '.venv', '.env'
        }
        
        # Suspicious patterns
        self.suspicious_extensions = {'.tmp', '.bak', '.orig', '.swp', '.swo'}
        self.large_file_threshold = 10 * 1024 * 1024  # 10MB
        
    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate MD5 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (OSError, IOError):
            return None
    
    def find_duplicate_files(self) -> None:
        """Find files with identical content"""
        file_hashes = defaultdict(list)
        
        for file_path in self.root_path.rglob('*'):
            if file_path.is_file() and not any(p in str(file_path) for p in self.ignore_patterns):
                file_hash = self.get_file_hash(file_path)
                if file_hash:
                    file_hashes[file_hash].append(file_path)
        
        # Report duplicates
        for file_hash, files in file_hashes.items():
            if len(files) > 1:
                self.issues['duplicates'].append({
                    'hash': file_hash,
                    'files': [str(f) for f in files],
                    'size': files[0].stat().st_size
                })
    
    def find_nested_directory_duplicates(self) -> None:
        """Find nested directories that duplicate their parent structure"""
        for version_dir in self.root_path.glob('ty_extract_v*'):
            if not version_dir.is_dir():
                continue
                
            # Look for nested ty_extract directories
            nested_dirs = list(version_dir.rglob('ty_extract'))
            for nested in nested_dirs:
                if nested != version_dir and nested.is_dir():
                    # Compare file structures
                    parent_files = set(f.name for f in version_dir.iterdir() if f.is_file())
                    nested_files = set(f.name for f in nested.iterdir() if f.is_file())
                    
                    overlap = parent_files & nested_files
                    if len(overlap) > 3:  # Significant overlap
                        self.issues['nested_duplicates'].append({
                            'parent': str(version_dir),
                            'nested': str(nested),
                            'duplicate_files': list(overlap),
                            'overlap_ratio': len(overlap) / max(len(parent_files), 1)
                        })
    
    def find_zero_size_files(self) -> None:
        """Find zero-byte files that might be artifacts"""
        for file_path in self.root_path.rglob('*'):
            if file_path.is_file() and file_path.stat().st_size == 0:
                # Skip known zero-size files like __init__.py
                if file_path.name not in {'__init__.py', '.gitkeep', '.keep'}:
                    self.issues['zero_files'].append({
                        'path': str(file_path),
                        'parent_dir': str(file_path.parent)
                    })
    
    def find_cache_directories(self) -> None:
        """Find cache directories that should be cleaned"""
        cache_patterns = {'__pycache__', '.mypy_cache', '.pytest_cache', 'node_modules'}
        
        for cache_dir in self.root_path.rglob('*'):
            if cache_dir.is_dir() and cache_dir.name in cache_patterns:
                self.issues['cache_dirs'].append({
                    'path': str(cache_dir),
                    'size_mb': sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()) / (1024*1024)
                })
    
    def find_broken_symlinks(self) -> None:
        """Find broken symbolic links"""
        for link_path in self.root_path.rglob('*'):
            if link_path.is_symlink() and not link_path.exists():
                self.issues['broken_links'].append({
                    'path': str(link_path),
                    'target': str(link_path.readlink())
                })
    
    def find_large_files(self) -> None:
        """Find unusually large files"""
        for file_path in self.root_path.rglob('*'):
            if file_path.is_file() and file_path.stat().st_size > self.large_file_threshold:
                self.issues['large_files'].append({
                    'path': str(file_path),
                    'size_mb': file_path.stat().st_size / (1024*1024),
                    'extension': file_path.suffix
                })
    
    def find_suspicious_patterns(self) -> None:
        """Find files with suspicious patterns"""
        for file_path in self.root_path.rglob('*'):
            if file_path.is_file():
                # Check suspicious extensions
                if file_path.suffix in self.suspicious_extensions:
                    self.issues['suspicious_patterns'].append({
                        'path': str(file_path),
                        'issue': f'Suspicious extension: {file_path.suffix}',
                        'type': 'extension'
                    })
                
                # Check for backup-like patterns
                if any(pattern in file_path.name.lower() for pattern in ['backup', 'copy', 'old', 'temp']):
                    self.issues['suspicious_patterns'].append({
                        'path': str(file_path),
                        'issue': 'Backup-like filename pattern',
                        'type': 'backup_pattern'
                    })
    
    def auto_fix_safe_issues(self) -> None:
        """Auto-fix issues that are safe to fix automatically"""
        if not self.auto_fix:
            return
        
        print("🔧 AUTO-FIXING SAFE ISSUES...")
        
        # Remove cache directories
        for cache_issue in self.issues['cache_dirs']:
            cache_path = Path(cache_issue['path'])
            if cache_path.exists():
                import shutil
                shutil.rmtree(cache_path)
                print(f"   ✅ Removed cache directory: {cache_path}")
        
        # Remove zero-size non-essential files
        for zero_issue in self.issues['zero_files']:
            zero_path = Path(zero_issue['path'])
            if zero_path.exists() and zero_path.suffix in {'.log', '.tmp', '.temp'}:
                zero_path.unlink()
                print(f"   ✅ Removed zero-size file: {zero_path}")
        
        # Remove broken symlinks
        for broken_issue in self.issues['broken_links']:
            broken_path = Path(broken_issue['path'])
            if broken_path.is_symlink():
                broken_path.unlink()
                print(f"   ✅ Removed broken symlink: {broken_path}")
    
    def run_all_checks(self) -> None:
        """Run all hygiene checks"""
        print("🔍 SCANNING CODEBASE FOR HYGIENE ISSUES...")
        print(f"📁 Root path: {self.root_path}")
        print()
        
        checks = [
            ("🔍 Checking for duplicate files...", self.find_duplicate_files),
            ("🔍 Checking for nested directory duplicates...", self.find_nested_directory_duplicates),
            ("🔍 Checking for zero-size files...", self.find_zero_size_files),
            ("🔍 Checking for cache directories...", self.find_cache_directories),
            ("🔍 Checking for broken symlinks...", self.find_broken_symlinks),
            ("🔍 Checking for large files...", self.find_large_files),
            ("🔍 Checking for suspicious patterns...", self.find_suspicious_patterns),
        ]
        
        for description, check_func in checks:
            print(description)
            check_func()
        
        print("\n✅ SCAN COMPLETE!")
    
    def generate_report(self) -> str:
        """Generate a comprehensive hygiene report"""
        report = ["# 🧹 CODEBASE HYGIENE REPORT", ""]
        report.append(f"**Scan Root**: `{self.root_path}`")
        report.append(f"**Scan Date**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        total_issues = sum(len(issues) for issues in self.issues.values())
        report.append(f"## 📊 SUMMARY")
        report.append(f"- **Total Issues Found**: {total_issues}")
        report.append("")
        
        # Detailed issues
        issue_icons = {
            'duplicates': '🔄',
            'nested_duplicates': '📁',
            'zero_files': '📄',
            'cache_dirs': '🗑️',
            'broken_links': '🔗',
            'large_files': '📦',
            'suspicious_patterns': '⚠️'
        }
        
        issue_titles = {
            'duplicates': 'Duplicate Files',
            'nested_duplicates': 'Nested Directory Duplicates',
            'zero_files': 'Zero-Size Files',
            'cache_dirs': 'Cache Directories',
            'broken_links': 'Broken Symlinks',
            'large_files': 'Large Files',
            'suspicious_patterns': 'Suspicious Patterns'
        }
        
        for issue_type, issues in self.issues.items():
            if issues:
                icon = issue_icons.get(issue_type, '❓')
                title = issue_titles.get(issue_type, issue_type.title())
                report.append(f"## {icon} {title} ({len(issues)} found)")
                report.append("")
                
                for i, issue in enumerate(issues, 1):
                    if issue_type == 'duplicates':
                        report.append(f"### {i}. Duplicate Set (Size: {issue['size']} bytes)")
                        for file_path in issue['files']:
                            report.append(f"   - `{file_path}`")
                    
                    elif issue_type == 'nested_duplicates':
                        report.append(f"### {i}. Nested Duplication")
                        report.append(f"   - **Parent**: `{issue['parent']}`")
                        report.append(f"   - **Nested**: `{issue['nested']}`")
                        report.append(f"   - **Overlap**: {len(issue['duplicate_files'])} files ({issue['overlap_ratio']:.1%})")
                        report.append(f"   - **Files**: {', '.join(issue['duplicate_files'][:5])}{'...' if len(issue['duplicate_files']) > 5 else ''}")
                    
                    elif issue_type == 'cache_dirs':
                        report.append(f"### {i}. `{issue['path']}` ({issue['size_mb']:.1f} MB)")
                    
                    elif issue_type == 'large_files':
                        report.append(f"### {i}. `{issue['path']}` ({issue['size_mb']:.1f} MB)")
                    
                    else:
                        report.append(f"### {i}. `{issue['path']}`")
                        if 'issue' in issue:
                            report.append(f"   - **Issue**: {issue['issue']}")
                    
                    report.append("")
        
        if total_issues == 0:
            report.append("## 🎉 EXCELLENT!")
            report.append("No hygiene issues found! Your codebase is clean and well-organized.")
            report.append("")
        
        # Recommendations
        if total_issues > 0:
            report.append("## 💡 RECOMMENDATIONS")
            report.append("")
            
            if self.issues['nested_duplicates']:
                report.append("### 📁 Nested Duplicates")
                report.append("- Remove nested `ty_extract/` directories that duplicate parent structure")
                report.append("- Consolidate code into the main version directory")
                report.append("")
            
            if self.issues['duplicates']:
                report.append("### 🔄 Duplicate Files")
                report.append("- Review duplicate files and keep only the most recent/correct version")
                report.append("- Consider using symlinks if files need to exist in multiple locations")
                report.append("")
            
            if self.issues['cache_dirs']:
                report.append("### 🗑️ Cache Cleanup")
                report.append("- Run with `--fix-auto` to automatically remove cache directories")
                report.append("- Add cache directories to `.gitignore`")
                report.append("")
            
            if self.issues['large_files']:
                report.append("### 📦 Large Files")
                report.append("- Review large files - consider if they belong in version control")
                report.append("- Move large data files to separate storage if needed")
                report.append("")
        
        return "\n".join(report)
    
    def save_report(self, output_path: Optional[str] = None) -> str:
        """Save the hygiene report to file"""
        if output_path is None:
            timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/codebase_hygiene_report_{timestamp}.md"
        
        report_content = self.generate_report()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report_content)
        
        return output_path

def main():
    parser = argparse.ArgumentParser(description='Check codebase hygiene for TY_Extract versions')
    parser.add_argument('--target', default='modules/ty_extract_versions', 
                       help='Target directory to scan (default: modules/ty_extract_versions)')
    parser.add_argument('--fix-auto', action='store_true',
                       help='Automatically fix safe issues (cache dirs, broken links, etc.)')
    parser.add_argument('--output', help='Output report file path')
    parser.add_argument('--json', action='store_true', help='Also output JSON format')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.target):
        print(f"❌ Target directory does not exist: {args.target}")
        sys.exit(1)
    
    # Run hygiene check
    checker = CodebaseHygieneChecker(args.target, auto_fix=args.fix_auto)
    checker.run_all_checks()
    
    if args.fix_auto:
        checker.auto_fix_safe_issues()
    
    # Generate and save report
    report_path = checker.save_report(args.output)
    print(f"\n📋 Report saved to: {report_path}")
    
    # Print summary to console
    print("\n" + "="*60)
    print(checker.generate_report())
    
    # Save JSON if requested
    if args.json:
        json_path = report_path.replace('.md', '.json')
        with open(json_path, 'w') as f:
            json.dump(checker.issues, f, indent=2, default=str)
        print(f"📄 JSON data saved to: {json_path}")

if __name__ == "__main__":
    main()
