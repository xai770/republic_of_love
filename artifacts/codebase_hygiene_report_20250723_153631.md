# 🧹 CODEBASE HYGIENE REPORT

**Scan Root**: `modules/ty_extract_versions/ty_extract_v14`
**Scan Date**: 2025-07-23 15:36:31

## 📊 SUMMARY
- **Total Issues Found**: 3

## 📄 Zero-Size Files (1 found)

### 1. `modules/ty_extract_versions/ty_extract_v14/config_clean.py`

## 🗑️ Cache Directories (1 found)

### 1. `modules/ty_extract_versions/ty_extract_v14/__pycache__` (0.0 MB)

## ⚠️ Suspicious Patterns (1 found)

### 1. `modules/ty_extract_versions/ty_extract_v14/config_backup.py`
   - **Issue**: Backup-like filename pattern

## 💡 RECOMMENDATIONS

### 🗑️ Cache Cleanup
- Run with `--fix-auto` to automatically remove cache directories
- Add cache directories to `.gitignore`
