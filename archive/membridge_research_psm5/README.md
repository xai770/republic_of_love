# MemBridge Research Files - PSM Round 5.2
**Archived:** 2025-10-20  
**Reason:** Cleanup - Production uses registry.py and models.py only

## Archived Files

### converged_membridge.py (36K)
**PSM Round 5.2 Implementation**  
Value-weighted LLM interaction storage system with intelligent caching decisions.

**Key Features:**
- Environmental context tracking and drift detection
- Value-weighted storage (failures > firsts > outliers > samples)
- Template lifecycle management (learning → verified → stable)
- SQLite-based persistence with performance optimization
- Fallback modes for error resilience

**Author:** Arden  
**Date:** 2025-09-02  

### origin_tracking.py (12K)
**Drift Detection & Origin Tracking**  
Tracks interaction origins and detects environmental drift for cache invalidation.

**Key Features:**
- Origin tracking for LLM interactions
- Environmental context monitoring
- Drift detection algorithms

### environmental.py (12K)
**Environmental Context Tracking**  
Collects and manages environmental context for LLM interactions.

**Key Features:**
- Context collection from system environment
- Environmental state management
- Integration with drift detection

## Production Usage

**Current Production (production/v17/)** uses:
- `membridge.registry` (registry.py) - Config-driven LLM call system
- `membridge.models` (models.py) - Data models and configuration

**These research files were NOT in active use** but represent interesting exploratory work on:
- Intelligent caching strategies
- Value-weighted storage decisions
- Environmental drift detection
- Template lifecycle management

## Recovery

If needed, these files can be restored from:
1. This archive directory: `/home/xai/Documents/ty_learn/archive/membridge_research_psm5/`
2. Documents backup system: `~/Documents_Versions/`
3. Git history (if committed)

## Deleted Files (Not Archived)

**Not Worth Keeping:**
- `registry_v2.py` (24K) - Old version replaced by registry.py
- `registry_v2.py.zeroed_20250908_071814` - Old backup/zero file
- `converged_membridge_new.py` (24K) - Experimental "new" version
- `tests/` (212K) - Test files (covered by backups)
- `__pycache__/` (120K) - Python cache files

**Total Cleanup:** ~380K deleted, ~60K archived, ~100K production code retained
