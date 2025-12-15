# 📜 Script Index & Documentation

## 🗄️ Database Management

### Schema Migrations
| Script | Purpose | Usage |
|--------|---------|-------|
| `schema_elegance_migration.py` | Initial elegant schema design | Run once for base setup |
| `gradient_capability_migration.py` | Add gradient testing capabilities | Run to enable gradient tests |
| `multi_parameter_gradient_system.py` | Multi-parameter gradient support | Run for p1,p2,p3 parameter testing |
| `forge_perfect_architecture.py` | Consolidate schema to perfect design | Run to unify tables |
| `add_foreign_key_constraint.py` | Add proper foreign key constraints | Run for referential integrity |
| `add_total_passes_field.py` | Add aggregated success metrics | Run for summary statistics |

### Analysis Queries
| Query | Purpose | Returns |
|-------|---------|---------|
| `unified_facet_to_results_chain_query.sql` | Complete hierarchy analysis | Facet→canonical→test→results chain |
| `unified_gradient_capability_analysis_query.sql` | Gradient performance analysis | Difficulty-based capability mapping |
| `unified_model_performance_dashboard_query.sql` | Model comparison dashboard | Cross-model performance metrics |
| `master_dashboard_query.sql` | Legacy comprehensive dashboard | All test results and analytics |

## 🧪 Testing Framework

### Gradient Testing
| Script | Purpose | Usage |
|--------|---------|-------|
| `gradient_test_runner.py` | Run gradient capability tests | Execute gradient test suite |
| `realistic_gradient_test.py` | Simulate realistic model performance | Generate test data with realistic curves |

### Canonical Testing  
| Script | Purpose | Usage |
|--------|---------|-------|
| `canonical_test_runner.py` | Execute canonical tests | Run standard baseline tests |
| `create_canonical_tests.py` | Create new canonical tests | Add test definitions |
| `insert_canonicals.py` | Import canonical test data | Load test data into database |

## 📊 Analysis Tools
| Tool | Purpose | Usage |
|------|---------|-------|
| `essential_tables_analysis.py` | Identify essential vs redundant tables | Database cleanup analysis |
| `perfect_schema_analysis.py` | Analyze current vs ideal schema | Schema validation |
| `comprehensive_analyzer.py` | Comprehensive test result analysis | Full result processing |
| `manual_test_integrator.py` | Integrate manual test results | Merge manual scores |
| `retroactive_test_scorer.py` | Score existing test results | Backfill scoring data |

## 🚀 Quick Start Guide

### 1. Database Setup
```bash
# Run migrations in order:
python database_management/schema_migrations/schema_elegance_migration.py
python database_management/schema_migrations/gradient_capability_migration.py  
python database_management/schema_migrations/multi_parameter_gradient_system.py
python database_management/schema_migrations/forge_perfect_architecture.py
python database_management/schema_migrations/add_foreign_key_constraint.py
```

### 2. Load Test Data
```bash
python testing_framework/canonical_testing/create_canonical_tests.py
python testing_framework/canonical_testing/insert_canonicals.py
```

### 3. Run Gradient Tests  
```bash
python testing_framework/gradient_testing/gradient_test_runner.py
```

### 4. Analyze Results
```bash
# Run analysis queries:
sqlite3 data/llmcore.db < database_management/analysis_queries/unified_gradient_capability_analysis_query.sql

# Or use analysis tools:
python analysis_tools/comprehensive_analyzer.py
```

## 💖 Architecture Overview

```
📁 LLMCore Project Structure
├── 🗄️ database_management/
│   ├── schema_migrations/     (11 scripts)
│   └── analysis_queries/      (11 queries)
├── 🧪 testing_framework/
│   ├── gradient_testing/      (2 scripts)  
│   └── canonical_testing/     (3 scripts)
├── 📊 analysis_tools/         (6 tools)
├── 📚 documentation/          (guides & docs)
└── 🗂️ data/                  (database & results)
```

**Beautiful, organized, and easy to navigate! Every script has a purpose and place.** ✨💎