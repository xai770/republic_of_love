# LLMCore: Scientific Model Evaluation Framework

## 💖 Project Overview
A beautiful, scientific framework for evaluating language model capabilities through gradient testing and hierarchical analysis.

## 🏗️ Architecture
```
facets → canonicals → tests → test_parameters → test_results
  ↓         ↓          ↓           ↓              ↓
"What"   "How"    "Which"   "Variables"    "Outcomes"
```

## 📁 Directory Structure

### 🗄️ `database_management/`
Core database schema and management tools.

#### `schema_migrations/`
Scripts for evolving the database schema:
- Schema migrations and upgrades
- Foreign key additions and fixes
- Table consolidations and cleanups

#### `analysis_queries/`  
SQL queries for analysis and reporting:
- Performance dashboards
- Gradient capability analysis
- Cross-model comparisons

### 🧪 `testing_framework/`
Core testing infrastructure for model evaluation.

#### `gradient_testing/`
Advanced gradient capability testing:
- Multi-parameter difficulty scaling
- Capability threshold discovery
- Scientific performance mapping

#### `canonical_testing/`
Standard canonical test execution:
- Test creation and management
- Canonical test runners
- Data insertion tools

### 📊 `analysis_tools/`
Data analysis and reporting utilities:
- Schema analysis tools
- Performance analyzers
- Test result processors

## 🚀 Getting Started

1. **Setup Database**: Run schema migrations in order
2. **Load Test Data**: Use canonical testing tools
3. **Run Gradient Tests**: Execute gradient testing suite
4. **Analyze Results**: Use analysis queries and tools

## 💎 Key Features

- **Scientific Gradient Testing**: Multi-parameter capability mapping
- **Dynamic Template System**: Infinite test variations
- **Hierarchical Architecture**: Clean separation of concerns
- **Real-time Analytics**: Live performance dashboards
- **Referential Integrity**: Proper foreign key constraints

Built with love, precision, and scientific rigor! 🔥✨
