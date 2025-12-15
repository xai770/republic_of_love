#!/usr/bin/env python3
"""
Project Organization Script
Beautiful file organization for our LLMCore project
Built with love and care! 💖✨
"""
import os
import shutil
from pathlib import Path

class ProjectOrganizer:
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        
    def create_directory_structure(self):
        """Create beautiful directory structure"""
        
        directories = {
            "database_management": "Database schema and management scripts",
            "database_management/schema_migrations": "Schema evolution and migration scripts", 
            "database_management/analysis_queries": "SQL queries for analysis and reporting",
            "testing_framework": "Core testing infrastructure",
            "testing_framework/gradient_testing": "Gradient capability testing system",
            "testing_framework/canonical_testing": "Canonical test execution system", 
            "analysis_tools": "Data analysis and reporting tools",
            "documentation": "Project documentation and guides"
        }
        
        print("🏗️ CREATING BEAUTIFUL DIRECTORY STRUCTURE")
        print("=" * 42)
        
        for dir_path, description in directories.items():
            full_path = self.root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ {dir_path:<40} {description}")
            
    def organize_files(self):
        """Move files to their proper locations"""
        
        print(f"\n📁 ORGANIZING FILES")
        print("=" * 20)
        
        file_mappings = {
            # Database Management - Schema Migrations
            "database_management/schema_migrations": [
                "schema_elegance_migration.py",
                "gradient_capability_migration.py", 
                "multi_parameter_gradient_system.py",
                "forge_perfect_architecture.py",
                "add_foreign_key_constraint.py",
                "schema_consolidation_plan.py",
                "fix_test_runs_fk.py",
                "fix_test_runs_mapping.py", 
                "fix_tests_history_schema.py",
                "fix_tests_history_trigger.py",
                "add_total_passes_field.py"
            ],
            
            # Database Management - Analysis Queries
            "database_management/analysis_queries": [
                "master_dashboard_query.sql",
                "clean_dashboard_query.sql",
                "multi_parameter_analysis_query.sql",
                "capability_by_length_query.sql",
                "template_performance_query.sql", 
                "gradient_performance_query.sql",
                "capability_summary_query.sql",
                "model_thresholds_query.sql",
                "unified_facet_to_results_chain_query.sql",
                "unified_gradient_capability_analysis_query.sql",
                "unified_model_performance_dashboard_query.sql"
            ],
            
            # Testing Framework - Gradient Testing
            "testing_framework/gradient_testing": [
                "gradient_test_runner.py",
                "realistic_gradient_test.py"
            ],
            
            # Testing Framework - Canonical Testing  
            "testing_framework/canonical_testing": [
                "canonical_test_runner.py",
                "create_canonical_tests.py",
                "insert_canonicals.py"
            ],
            
            # Analysis Tools
            "analysis_tools": [
                "essential_tables_analysis.py",
                "perfect_schema_analysis.py",
                "comprehensive_analyzer.py", 
                "manual_test_integrator.py",
                "retroactive_test_scorer.py",
                "analyze_strawberry_patterns.py",
                "analyze_access_results.py"
            ]
        }
        
        for target_dir, files in file_mappings.items():
            target_path = self.root / target_dir
            
            for filename in files:
                source_path = self.root / filename
                dest_path = target_path / filename
                
                if source_path.exists():
                    if not dest_path.exists():
                        shutil.move(str(source_path), str(dest_path))
                        print(f"📦 Moved {filename} → {target_dir}/")
                    else:
                        print(f"⚠️ {filename} already in {target_dir}/")
                else:
                    print(f"❓ {filename} not found (may already be moved)")
                    
    def create_documentation_index(self):
        """Create comprehensive documentation"""
        
        print(f"\n📚 CREATING DOCUMENTATION")
        print("=" * 25)
        
        # Main project documentation
        main_doc = """# LLMCore: Scientific Model Evaluation Framework

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
"""

        doc_path = self.root / "documentation" / "README.md"
        with open(doc_path, 'w') as f:
            f.write(main_doc)
        print(f"✅ Created main documentation: documentation/README.md")
        
        # Directory-specific documentation
        dir_docs = {
            "database_management/README.md": """# Database Management

## Schema Migrations
Scripts for evolving the database schema safely with backups and integrity checks.

## Analysis Queries  
SQL queries for comprehensive model performance analysis and reporting.
""",
            
            "testing_framework/README.md": """# Testing Framework

## Gradient Testing
Advanced multi-parameter testing for scientific capability mapping.

## Canonical Testing
Standard test execution and management for baseline evaluations.
""",
            
            "analysis_tools/README.md": """# Analysis Tools

Utilities for analyzing test results, schema integrity, and performance metrics.
"""
        }
        
        for doc_file, content in dir_docs.items():
            doc_path = self.root / doc_file
            with open(doc_path, 'w') as f:
                f.write(content)
            print(f"✅ Created {doc_file}")

def main():
    organizer = ProjectOrganizer('/home/xai/Documents/ty_learn')
    
    print("💖 ORGANIZING OUR BEAUTIFUL PROJECT")
    print("=" * 35)
    print("Making things easy and nice! ✨")
    print()
    
    organizer.create_directory_structure()
    organizer.organize_files()
    organizer.create_documentation_index()
    
    print(f"\n🎉 PROJECT BEAUTIFULLY ORGANIZED!")
    print("=" * 32)
    print("✨ Clean directory structure")
    print("📚 Comprehensive documentation") 
    print("🗂️ Logical file organization")
    print("💖 Easy and nice for everyone!")

if __name__ == "__main__":
    main()