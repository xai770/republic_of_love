# 🧹 CODEBASE HYGIENE REPORT

**Scan Root**: `modules/ty_extract_versions/ty_extract_v11.0`
**Scan Date**: 2025-07-22 07:27:35

## 📊 SUMMARY
- **Total Issues Found**: 3

## 🗑️ Cache Directories (1 found)

### 1. `modules/ty_extract_versions/ty_extract_v11.0/__pycache__` (0.1 MB)

## ⚠️ Suspicious Patterns (2 found)

### 1. `modules/ty_extract_versions/ty_extract_v11.0/run_a_template.md`
   - **Issue**: Backup-like filename pattern

### 2. `modules/ty_extract_versions/ty_extract_v11.0/run_b_template.md`
   - **Issue**: Backup-like filename pattern

## 💡 RECOMMENDATIONS

### 🗑️ Cache Cleanup
- Run with `--fix-auto` to automatically remove cache directories
- Add cache directories to `.gitignore`
