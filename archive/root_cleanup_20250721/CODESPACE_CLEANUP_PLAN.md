# Codespace Cleanup Plan - July 20, 2025

## V10 Files Organization ✅
**COMPLETED:**
- ✅ Moved `v10_vs_v71_comparison.py` → `ty_extract_v10.0_qwen3_optimized/`
- ✅ Moved `V10_IMPLEMENTATION_SUCCESS_REPORT.md` → `ty_extract_v10.0_qwen3_optimized/`

**V10 folder now contains:**
- All V10.0 implementation files
- V10 comparison scripts  
- V10 reports and documentation
- V10 test outputs

## Folders Ready for Archive 📦

### 1. **debug/** - Archive immediately
- Contains old debugging outputs
- No longer needed for production

### 2. **llm_dialogues/** - Archive immediately  
- Historical conversation logs
- Not needed for current operations

### 3. **logs/** - Archive immediately
- Old processing logs
- Can be archived for space

### 4. **output/** - Archive immediately
- Legacy output files
- All current outputs are in version-specific folders

### 5. **extraction_pipeline/** - Review then archive
- Legacy extraction code
- Superseded by versioned ty_extract folders

### 6. **llm_factory/** - Archive immediately
- Legacy LLM management code
- Superseded by current LLM validation framework

### 7. **🎭_ACTIVE_EXPERIMENTS/** - Partially archive
- Archive completed experiments
- Keep only active/relevant experiments

### 8. **ty_extract copy/** - Archive immediately
- Duplicate folder, no longer needed

### 9. **Old version comparison files** - Archive
- `COMPLETE_VERSION_COMPARISON_v7.1_v8.0_v9.0.md`
- `version_comparison_v7.1_v8.0_v9.0.md`
- `version_comparison_v8_v9_analysis.md`
- `v9_vs_v8_comparison_analysis.md`

### 10. **Legacy scripts** - Archive
- `cleanup_production.py`
- `compare_versions.py`
- `enhanced_pipeline_runner.py`
- `final_production_test.py`
- `generate_version_comparison.py`
- `version_comparison_framework.py`
- `version_comparison_framework_enhanced.py`

## Keep in Root (Active/Essential) 🔄

### **Active ty_extract versions:**
- `ty_extract_v7.1_template_based/` (Gold standard)
- `ty_extract_v10.0_qwen3_optimized/` (Production)
- `ty_extract_v8.0_llm_only_fail_fast/` (Keep for reference)
- `ty_extract_v9.0_optimized/` (Keep for reference)

### **Essential infrastructure:**
- `data/` (Job posting data)
- `📚_PROJECT_DOCS/` (Current documentation)  
- `0_mailboxes/` (Communication system)
- `🏗️_LLM_INFRASTRUCTURE/` (LLM framework)
- `llm_validation_results/` (Recent validation data)
- `scripts/` (Active utility scripts)

### **Core files:**
- `README.md`, `requirements.txt`, `pyproject.toml`
- `structured_job_extraction_prompt.md` (Active prompt)
- LLM validation scripts (`llm_validation_*.py`, `phase2_quality_assessment.py`)

## Space Savings Expected 💾
- **~8-12 folders** moved to archive
- **~50-100 files** organized  
- **Cleaner workspace** for development
- **Easier navigation** to active components

## Next Actions 🚀
1. Execute archive moves for identified folders
2. Verify all V10 files are properly organized
3. Update documentation paths if needed
4. Test that all active workflows still function
