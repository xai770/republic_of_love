# TY_LEARN_REPORT - QA Framework Development Plan

**Module:** `ty_learn_report`  
**Purpose:** Lightweight, non-LLM QA framework for comparing LLM outputs  
**Sponsor:** Misty (on behalf of Xai)  
**Lead Developer:** Arden  
**Start Date:** July 21, 2025

---

## 🎯 **PROJECT OVERVIEW**

### **Mission Statement**
Build a simple, reliable QA framework to compare outputs from different ty_extract versions (V10.0 vs V7.1) using structural heuristics, catching major discrepancies without LLM complexity.

### **Success Criteria**
- ✅ Detect missing sections automatically
- ✅ Flag >30% length differences between versions
- ✅ Identify empty/malformed content
- ✅ Provide clear PASS/WARN/FAIL status
- ✅ Enable programmatic access to existing modules

---

## 📋 **DEVELOPMENT PHASES**

### **🏗️ Phase 1: Core QA Engine** 
**Target:** July 21-22, 2025

#### **Deliverables:**
- [x] **Basic comparison engine** (`compare_reports.py`) ✅
- [x] **Section parser** (extract "Your Tasks"/"Your Profile" sections) ✅
- [x] **Length analyzer** (character/word count deltas) ✅
- [x] **Status reporter** (PASS/WARN/FAIL with details) ✅

#### **Test Cases:**
- [x] **V10.0 vs V7.1** comparison simulation ✅
- [x] **Format violation detection** (missing sections) ✅
- [x] **Length discrepancy flagging** (>30% difference) ✅

**STATUS: ✅ COMPLETE - All core components implemented and tested**

---

### **🔧 Phase 2: Module Integration**
**Target:** July 22-23, 2025

#### **Deliverables:**
- [ ] **Refactor V10.0 main.py** to export `generate_report()` function
- [ ] **Create V7.1 adapter** for programmatic access
- [ ] **Integration testing** with both modules
- [ ] **CLI interface** for manual QA runs

#### **API Design:**
```python
def generate_report(job_data: dict, model_version: str) -> dict:
    """Standard interface for all ty_extract modules"""
    
def compare_outputs(baseline: dict, candidate: dict) -> QAResult:
    """Core comparison logic"""
```

---

### **🚀 Phase 3: Automation & Scale**
**Target:** July 23-24, 2025

#### **Deliverables:**
- [ ] **Batch processing** for multiple jobs
- [ ] **Regression testing framework**
- [ ] **Performance metrics tracking**
- [ ] **Integration with existing SOP**

---

## 🧪 **TESTING STRATEGY**

### **Validation Data**
- **Known Good**: V7.1 outputs (gold standard)
- **Known Issues**: V10.0 pre-fix outputs (format violations)
- **Current State**: V10.0 post-fix outputs (high quality)

### **Test Scenarios**
1. **✅ Perfect Match**: Identical structure, similar content
2. **⚠️ Minor Differences**: <30% length variance, same sections
3. **❌ Major Issues**: Missing sections, >30% length difference
4. **❌ Format Violations**: Wrong structure, benefits contamination

---

## 📊 **PROGRESS TRACKING**

### **Week 1 (July 21-27, 2025)**

#### **Day 1 (July 21) - CURRENT**
- [x] **Project Setup**: Created module directory and planning doc
- [ ] **Core Engine**: Basic comparison logic
- [ ] **Test Data**: Prepare V10.0 vs V7.1 sample outputs

#### **Day 2 (July 22)**
- [ ] **Section Parser**: Extract and analyze markdown sections
- [ ] **Length Analyzer**: Implement delta calculations
- [ ] **Status Reporter**: PASS/WARN/FAIL logic

#### **Day 3 (July 23)**
- [ ] **V10.0 Refactor**: Export generate_report() function
- [ ] **Integration Test**: Full V10.0 vs V7.1 comparison
- [ ] **CLI Interface**: Manual QA tool

#### **Day 4 (July 24)**
- [ ] **Batch Processing**: Multiple job analysis
- [ ] **Documentation**: Usage guide and examples
- [ ] **SOP Integration**: Update Arden's workflow

---

## 🏗️ **ARCHITECTURE DESIGN**

### **Module Structure**
```
modules/ty_learn_report/
├── README.md                    # Usage guide
├── DEVELOPMENT_PLAN.md          # This document
├── versions/
│   └── v1.0_basic_qa/
│       ├── main.py              # CLI interface
│       ├── compare_reports.py   # Core comparison engine
│       ├── section_parser.py    # Markdown section analysis
│       ├── qa_reporter.py       # Status and reporting
│       └── tests/
│           ├── test_comparison.py
│           └── sample_data/
└── integration/
    ├── v10_adapter.py           # V10.0 programmatic interface
    └── v71_adapter.py           # V7.1 programmatic interface
```

### **Core Classes**
```python
class QAResult:
    status: str  # PASS/WARN/FAIL
    details: dict
    metrics: dict
    
class ReportComparator:
    def compare(baseline: str, candidate: str) -> QAResult
    
class SectionAnalyzer:
    def extract_sections(content: str) -> dict
    def analyze_structure(sections: dict) -> dict
```

---

## 🎯 **IMMEDIATE NEXT STEPS**

1. **Create v1.0_basic_qa directory structure**
2. **Implement basic comparison engine with V10.0 vs V7.1 test**
3. **Test against our known good/bad examples**
4. **Validate approach before Phase 2**

---

## 📝 **CHANGE LOG**

### **v0.1 - July 21, 2025**
- Initial project setup and planning
- Created module directory structure
- Defined development phases and success criteria

---

## 🤝 **STAKEHOLDER COMMUNICATION**

### **Status Updates**
- **Daily**: Progress updates in this document
- **Weekly**: Summary report to Misty/Xai
- **Milestone**: Demo and validation sessions

### **Decision Points**
- **API Design**: Final interface for programmatic access
- **Integration Strategy**: How to refactor existing modules
- **Quality Thresholds**: What constitutes PASS vs WARN vs FAIL

---

*This planning document will be updated daily to track progress and decisions.*

**Next Update:** July 22, 2025 - Phase 1 Progress Review
