# TY_LEARN_REPORT - Lightweight QA Framework

**Version:** v1.0 (In Development)  
**Purpose:** Non-LLM QA framework for comparing ty_extract outputs  
**Status:** 🚧 Phase 1 - Core Engine Development

---

## 🎯 **Quick Start**

```bash
# Compare two job extraction outputs
cd modules/ty_learn_report/versions/v1.0_basic_qa
python main.py --baseline v71_output.md --candidate v10_output.md

# Batch comparison
python main.py --batch --baseline-dir v71_results/ --candidate-dir v10_results/
```

---

## 🏗️ **Architecture**

### **Core Components**
- **`compare_reports.py`**: Main comparison engine
- **`section_parser.py`**: Markdown section extraction
- **`qa_reporter.py`**: Status reporting (PASS/WARN/FAIL)
- **`main.py`**: CLI interface

### **Integration Adapters**
- **`integration/v10_adapter.py`**: V10.0 programmatic interface
- **`integration/v71_adapter.py`**: V7.1 programmatic interface

---

## 🔍 **What It Detects**

1. **Missing Sections**: "Your Tasks" or "Your Profile" absent
2. **Length Discrepancies**: >30% difference in section sizes
3. **Empty Content**: Sections with no meaningful content
4. **Format Violations**: Structure mismatches
5. **Content Quality**: Basic keyword coverage analysis

---

## 📊 **Output Format**

```json
{
  "status": "WARN",
  "overall_score": 75,
  "issues": [
    {
      "type": "LENGTH_DISCREPANCY",
      "section": "Your Tasks",
      "severity": "medium",
      "details": "Candidate 45% shorter than baseline"
    }
  ],
  "metrics": {
    "section_coverage": 100,
    "content_similarity": 75,
    "format_compliance": 90
  }
}
```

---

## 🧪 **Test Cases**

Based on real V10.0 vs V7.1 comparison scenarios:

1. **Perfect Output**: V10.0 post-fix vs V7.1 baseline
2. **Format Issues**: V10.0 pre-fix vs V7.1 (benefits contamination)
3. **Length Variance**: Different detail levels between versions
4. **Missing Sections**: Incomplete extractions

---

## 🚀 **Development Status**

### **Phase 1: Core Engine** (July 21-22)
- [ ] Basic comparison logic
- [ ] Section parsing
- [ ] Status reporting
- [ ] CLI interface

### **Phase 2: Integration** (July 22-23)  
- [ ] V10.0 adapter
- [ ] V7.1 adapter
- [ ] Batch processing

### **Phase 3: Automation** (July 23-24)
- [ ] SOP integration
- [ ] Performance tracking
- [ ] Regression testing

---

## 🤝 **Contributing**

This module follows Arden's SOP for systematic development:
1. **Test-driven**: Validate against known good/bad examples
2. **Incremental**: Build and test each component separately  
3. **Documentation**: Keep this README updated with progress

---

**Next Milestone:** Working comparison engine by July 22, 2025
