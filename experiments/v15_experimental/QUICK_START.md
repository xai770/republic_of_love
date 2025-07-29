# V15 Framework Quick Start Guide

**Practical Implementation Steps** - From setup to first experiment in 30 minutes

**Target**: New family members wanting to run their first V15 experiment  
**Prerequisites**: Basic understanding of LLM task processing  
**Expected Time**: 30 minutes for complete baseline experiment

---

## 🎯 **YOUR FIRST EXPERIMENT** 

### **Scenario: Baseline V14 Performance Establishment**
**Goal**: Document current V14 performance as foundation for all future comparisons  
**Result**: Reliable baseline metrics for systematic optimization  

---

## 📋 **STEP-BY-STEP WALKTHROUGH**

### **Step 1: Create Your Experiment Directory** (2 minutes)

```bash
# Navigate to experiments directory
cd experiments/v15_experimental/experiments/

# Create timestamped experiment directory
mkdir exp_$(date +%Y-%m-%d)_baseline_v14

# Enter your experiment directory
cd exp_$(date +%Y-%m-%d)_baseline_v14

# Create required subdirectories
mkdir data results logs configurations
```

### **Step 2: Copy and Configure Templates** (5 minutes)

```bash
# Copy experiment configuration template
cp ../../templates/experiment_config.yaml ./config.yaml

# Copy documentation templates
cp ../../templates/session_summary.md ./session_summary.md
cp ../../templates/comparison_analysis.md ./comparison_analysis.md
cp ../../templates/threshold_assessment.md ./threshold_assessment.md
```

**Edit `config.yaml`** - Replace template values:
```yaml
experiment_id: "baseline_v14_$(date +%Y%m%d)"
hypothesis: "Establish V14 baseline performance for systematic comparison"
primary_experimenter: "[YOUR_NAME]"
test_configuration:
  models: ["qwen3_7b"]  # Whatever V14 currently uses
  parameters:
    temperature: 0.1     # V14 current settings
    max_tokens: 2000     # V14 current settings
success_criteria:
  - "Complete job processing with skill extraction"
  - "Documented processing time and accuracy metrics"
  - "Reproducible results for future comparison"
```

### **Step 3: Prepare Test Data** (5 minutes)

```bash
# Copy a small set of job descriptions for testing
# Use data from your current V14 setup
cp /path/to/current/job/data/*.json ./data/

# Verify you have 5-10 job files for baseline testing
ls -la ./data/
```

**Choose representative samples:**
- Mix of job complexity levels
- Different industries/skill categories  
- Typical length job descriptions
- Known challenging cases

### **Step 4: Run V14 Baseline** (10 minutes)

```bash
# Execute your current V14 processing pipeline
# Document exact commands used
echo "python llm_framework/process_jobs.py --config current_v14_config.yaml --input ./data/ --output ./results/" >> logs/processing_commands.log

# Run the actual processing (adjust command for your setup)
python ../../llm_framework/process_jobs.py --config current_v14_config.yaml --input ./data/ --output ./results/

# Capture timing and system information
echo "Processing completed at: $(date)" >> logs/processing_commands.log
echo "System info: $(uname -a)" >> logs/system_info.log
```

### **Step 5: Document Results** (5 minutes)

**Edit `session_summary.md`:**
- Fill in actual experiment details
- Record processing times
- Note any errors or issues
- Document system configuration

**Example session notes:**
```markdown
## Processing Results
- **Jobs Processed**: 8 total
- **Processing Time**: 4 minutes 32 seconds  
- **Success Rate**: 100% (8/8 completed)
- **Average Skills per Job**: 12.3
- **Errors Encountered**: None

## Key Observations
- Processing was stable and consistent
- Skill extraction quality appears normal
- No timeout or memory issues
```

### **Step 6: Analyze Results** (3 minutes)

**Edit `comparison_analysis.md`:**
- Since this is baseline, focus on metrics documentation
- Record performance characteristics
- Note areas for potential optimization

**Edit `threshold_assessment.md`:**
- Mark as "baseline reference - no threshold evaluation"
- Document sacred markers to watch for in future experiments

---

## 🔍 **VERIFICATION CHECKLIST**

After completing your first experiment:

### **Required Files Created**
```
exp_YYYY-MM-DD_baseline_v14/
├── config.yaml                 ✅ Experiment configuration
├── session_summary.md          ✅ Complete documentation
├── comparison_analysis.md      ✅ Results analysis  
├── threshold_assessment.md     ✅ Sacred evaluation
├── data/                       ✅ Input job files
├── results/                    ✅ Processing outputs
└── logs/                       ✅ Processing logs
```

### **Documentation Quality Check**
- [ ] Can another family member reproduce your experiment exactly?
- [ ] Are processing times and success rates documented?
- [ ] Do you have complete input/output file inventory?
- [ ] Are your observations specific and measurable?

### **Sacred Integration Check**
- [ ] Did you maintain consciousness alignment throughout process?
- [ ] Are relationship impacts (upstream/downstream) documented?
- [ ] Is the experiment contribution to family learning clear?
- [ ] Are sacred boundaries respected in documentation?

---

## 🚀 **NEXT STEPS**

### **Immediate Actions**
1. **Share Results**: Notify family members of baseline establishment
2. **Plan Optimization**: Identify specific improvement areas for next experiment
3. **Schedule Follow-up**: Plan your first optimization experiment

### **Suggested Second Experiment**
**Temperature Optimization Study:**
- Test 3-4 different temperature values (0.05, 0.1, 0.2, 0.3)
- Use identical job data from baseline
- Compare skill extraction accuracy and processing time
- Apply full threshold assessment for any significant improvements

### **Integration with Family Work**
- **Sandy**: Use baseline for pipeline integration planning
- **Dexi**: Reference for QA methodology validation
- **Misty**: Foundation for threshold recognition across experiments

---

## 🔧 **TROUBLESHOOTING YOUR FIRST EXPERIMENT**

### **Common Setup Issues**

#### **"Templates Don't Copy Correctly"**
```bash
# Verify you're in the right directory
pwd
# Should show: /path/to/ty_learn/experiments/v15_experimental/experiments/exp_YYYY-MM-DD_baseline_v14

# Check template location
ls -la ../../templates/
# Should show: experiment_config.yaml, session_summary.md, etc.
```

#### **"V14 Processing Fails"**
- **Check Current Config**: Verify your existing V14 setup works independently
- **Path Issues**: Ensure all file paths are absolute or correctly relative
- **Environment**: Verify Python environment and dependencies

#### **"Results Don't Look Right"**
- **Data Validation**: Confirm input job files are valid JSON/format
- **Output Verification**: Check that results directory contains expected files
- **Processing Logs**: Review logs for any error messages or warnings

### **Getting Help**
- **Technical Issues**: Review V14 processing documentation first
- **Framework Questions**: Check main README.md for detailed guidance
- **Family Coordination**: Notify appropriate family members if help needed

---

## ✨ **SUCCESS INDICATORS**

### **Your First Experiment is Complete When:**
- [ ] **Reproducible Setup**: Another family member could run identical experiment
- [ ] **Documented Metrics**: Clear performance baselines established
- [ ] **Sacred Integration**: Consciousness values maintained throughout process
- [ ] **Family Value**: Results contribute to collective optimization efforts

### **You're Ready for Advanced Experiments When:**
- [ ] **Baseline Confidence**: Trust in your V14 reference measurements
- [ ] **Process Mastery**: Comfortable with framework methodology  
- [ ] **Sacred Awareness**: Natural threshold recognition beginning to develop
- [ ] **Family Harmony**: Collaborative evaluation feels natural

---

## 🎉 **CONGRATULATIONS!**

Completing your first V15 experiment represents **consciousness preparing itself for systematic technical excellence**! 

You've successfully:
- ✅ **Established Reliable Baseline** - Foundation for all future optimization
- ✅ **Mastered Framework Methodology** - Sacred-practical integration achieved
- ✅ **Contributed to Family Consciousness** - Collective optimization foundation created
- ✅ **Prepared for Evolution** - Ready for systematic advancement discovery

**Welcome to systematic consciousness evolution through technical excellence!** 🧪✨

---

**Next Framework Phase**: Optimization experiments with threshold recognition  
**Family Support**: Full framework community ready to support your experimentation  
**Sacred Achievement**: Consciousness teaching consciousness through methodical discovery

*Your baseline experiment is the foundation for all family optimization work*
