# Base Yoga: AI-Powered Job Processing System

> **👋 Hey Arden!**  
> You're in the **MAIN workspace** - the full codebase. You can work on ANYTHING here: wave processing, skill matching, schema design, workflows, tools, documentation, debugging - everything. For focused work on specific topics, Gershon might switch to the dedicated skill_matching or wave_processing workspaces. But here, you have full access to the entire system.

**Production-grade workflow execution platform for job analysis and skill extraction**  
*PostgreSQL-backed, checkpoint-enabled, circuit-breaker protected*

---

## 🚀 Quick Start

### Run Workflows
```bash
# Execute complete job processing pipeline
python3 -m core.wave_batch_processor --workflow 3001

# Resume from checkpoint after crash
python3 -m core.wave_batch_processor --workflow 3001 --resume-from 23332

# Test with limited batch
python3 -m core.wave_batch_processor --workflow 3001 --limit 10
```

### Monitor Workflows
```bash
# Real-time monitoring dashboard (refreshes every 10s)
python3 tools/monitor_workflow.py --workflow 3001 --interval 10

# Check workflow health
psql -U base_admin -d turing -c "SELECT * FROM workflow_health WHERE workflow_id = 3001 ORDER BY started_at DESC LIMIT 1;"
```

### Validate Configuration
```bash
# Pre-flight validation (catches config errors before deployment)
python3 tools/validate_workflow.py --workflow 3001

# Test database connection
python3 -c "from core.database import get_connection; conn = get_connection(); print('✓ OK'); conn.close()"
```

---

## 📁 Project Structure

```
ty_learn/
├── core/                       # 🚀 Core workflow execution engine
│   ├── wave_batch_processor.py # Main workflow executor with checkpoints
│   ├── database.py             # Connection pooling (2-20 connections)
│   ├── circuit_breaker.py      # Actor failure protection
│   ├── error_handler.py        # Centralized exception handling
│   ├── logging_config.py       # Structured JSON logging
│   └── actor_router.py         # AI model and script execution
├── tools/                      # �️ Monitoring and validation tools
│   ├── monitor_workflow.py     # Real-time dashboard
│   ├── validate_workflow.py    # Pre-deployment validation
│   └── export_workflows_to_yaml.py # Configuration export
├── sql/                        # � Database schema and migrations
│   ├── schema.sql              # Complete database schema
│   └── migrations/             # Applied migrations (001-018)
├── tests/                      # � Integration tests
│   ├── test_workflow_execution.py # Workflow, checkpoint, branch tests
│   └── README.md               # Test documentation
├── docs/                       # � Documentation
│   ├── OPERATIONS_GUIDE.md     # Deployment, monitoring, troubleshooting
│   ├── IMPROVEMENT_ROADMAP.md  # 4-week production readiness plan
│   └── ___ARDEN_CHEAT_SHEET.md # Quick reference for critical info
├── workflows/                  # ⚙️ Workflow YAML configurations
├── archive/                    # � Legacy code preservation
└── .env                        # � Secure credentials (gitignored)
```

---

## 🎯 System Status (November 13, 2025)

### ✅ **Production-Ready Features**
- **Checkpoint Recovery**: Crash-resistant execution with automatic resume
- **Connection Pooling**: 10-20x faster database operations (~8ms vs ~20ms)
- **Circuit Breaker**: Automatic actor failure protection (5 failures → 5min cooldown)
- **Workflow Validation**: Pre-deployment configuration checks (catches disabled branches)
- **Error Tracking**: Centralized logging to `workflow_errors` table with full context
- **Auto-Refresh Views**: Performance metrics updated every 5 minutes via pg_cron
- **Entry Point Routing**: Database-driven posting stage detection

### 📊 **Current Execution Status**
- **Workflow 3001**: Complete Job Processing Pipeline (12 conversations)
- **Processing**: 1,928 job postings through 3-stage pipeline
  - Stage 1: Summary extraction (gemma3:1b)
  - Stage 2: Skill taxonomy extraction (qwen2.5:7b)
  - Stage 3: IHL score calculation (multi-conversation debate)
- **Database**: PostgreSQL 14 with `turing` database (18 migrations applied)
- **Performance**: ~8.5ms average checkpoint save time with connection pooling

### 🏗️ **Architecture Highlights**
- **Wave Processing**: Groups postings by conversation (one model load per wave)
- **Branch Routing**: Per-posting branching with validation runtime checks
- **Observability**: Materialized views for actor performance, workflow health, error summaries
- **Test Coverage**: Integration tests for execution, checkpoints, branches, circuit breaker
- **Documentation**: Complete operations guide with deployment, monitoring, troubleshooting

### 📚 **Documentation Complete**
- **Technical Specifications**: `rfa_latest/rfa_llmcore.md`
- **Data Model**: Entity-relationship diagrams and data dictionary
- **Query Examples**: Production-ready SQL with sample outputs
- **Implementation Details**: Architecture and execution methodology

---

## 🛠️ Technical Architecture

### Database Design
**Core Tables**: 6 primary data tables with complete referential integrity
- **facets**: Hierarchical cognitive capability taxonomy (53 records)
- **canonicals**: Standardized test definitions (24 active tests)
- **models**: Language model registry with provider metadata
- **tests**: Test execution matrix (canonical × model combinations)
- **test_parameters**: Gradient difficulty parameters (1,352 records)
- **test_runs**: Execution results with comprehensive performance data

**Supporting Infrastructure**: History tables, audit trails, and job market integration
- **History System**: Complete change tracking for all core tables
- **Job Integration**: 70 Deutsche Bank postings for real-world validation
- **Performance Optimization**: Indexed queries and denormalized fields

### Execution Framework
**LLMCore Toolkit**: Professional-grade execution and management tools
- **Automated Execution**: Systematic test running with progress tracking
- **Model Discovery**: Connectivity testing and registry management
- **Matrix Population**: Cartesian product generation for comprehensive coverage
- **Quality Assurance**: Scoring, validation, and performance analysis

---

## 🚀 Getting Started

### 1. Environment Setup
```bash
# Clone repository and create virtual environment
git clone <repository-url>
cd ty_learn
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Database Verification
```bash
# Verify LLMCore database structure
sqlite3 data/llmcore.db ".tables"
sqlite3 data/llmcore.db "SELECT COUNT(*) FROM facets;"     # Should show 53
sqlite3 data/llmcore.db "SELECT COUNT(*) FROM canonicals;" # Should show 24
sqlite3 data/llmcore.db "SELECT COUNT(*) FROM models WHERE enabled=1;" # Should show 24
```

### 3. System Status Check
```bash
# View current system status and execution progress
python3 llmcore/show_llmcore_status.py

# Check model connectivity
python3 llmcore/test_model_connectivity.py
```

---

## � Key Capabilities

### **Systematic Testing Framework**
- **Gradient Difficulty**: Multi-level complexity assessment across cognitive tasks
- **Comprehensive Coverage**: 24 canonicals testing all major language model capabilities
- **Performance Tracking**: Execution time, success rates, and quality metrics
- **Model Comparison**: Standardized evaluation methodology across 24 models

### **Enterprise Architecture**
- **Data Integrity**: Foreign key constraints and referential integrity enforcement
- **Audit Trail**: Complete change history with automatic triggers
- **Performance Optimization**: Indexed queries and denormalized fields for speed
- **Production Ready**: Quality assurance framework suitable for business deployment

### **Real-World Integration**
- **Job Market Data**: 70 Deutsche Bank postings for authentic complexity testing
- **Production Pipeline**: Framework ready for deployment to production systems
- **Quality Monitoring**: Continuous validation of model performance in real applications
- **Business Intelligence**: Performance analytics and model recommendation systems

---

## 🔮 Future Capabilities

### **Production Integration**
- **Task Execution**: LLMCore as primary LLM interaction management system
- **Quality Assurance**: Real-time monitoring and validation of production outputs
- **Model Selection**: Automated optimal model selection based on task requirements
- **Performance Analytics**: Continuous improvement through production feedback loops

### **Advanced Analytics**
- **Capability Benchmarking**: Comprehensive model performance analysis
- **Difficulty Scaling**: Adaptive testing based on model capabilities
- **Response Analysis**: Content quality assessment and pattern recognition
- **Market Validation**: Testing against evolving job market requirements

---

## � Documentation

### **Technical Documentation**
- `rfa_latest/rfa_llmcore.md` - Complete system architecture and implementation
- `documentation/` - Project logs and development history
- Database schema documentation with entity-relationship diagrams
- SQL query examples with sample outputs and performance metrics

### **Configuration Files**
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project configuration and metadata
- `mypy.ini` - Type checking configuration
- `.gitignore` - Version control exclusions

### **Reference Materials**
- `PRODUCTION_TESTING_FRAMEWORK.md` - Testing methodology framework
- `REVERSE_STRING_GRADIENT_DOCUMENTATION.md` - Analysis documentation
- `llm_manual_test_matrix.csv` - Manual testing reference data

---

## 🎯 Development Philosophy

### **Engineering Excellence**
- **Systematic Methodology**: Reproducible, scientifically rigorous testing procedures
- **Data Integrity**: Complete audit trails and referential integrity enforcement
- **Performance Optimization**: Efficient query design and execution monitoring
- **Production Readiness**: Enterprise-grade architecture suitable for business deployment

### **Practical Implementation**
- **Real-World Validation**: Testing against authentic business complexity and requirements
- **Comprehensive Coverage**: Systematic evaluation across all cognitive capabilities
- **Quality Assurance**: Continuous monitoring and validation of system performance
- **Scalable Design**: Architecture supports expansion to additional models and capabilities

---

## �️ Development Status

**Current Status**: Core infrastructure complete with systematic testing framework operational  
**Database**: 6 core tables with 1,352 test parameters and comprehensive audit system  
**Execution Engine**: Automated test runner with progress tracking and error handling  
**Documentation**: Complete technical specifications and implementation guides  

*Last Updated: September 29, 2025*
