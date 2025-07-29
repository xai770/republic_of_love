# 🚀 LLM Task Codex - Quick Start Guide

**For**: Republic of Love Engineering Team  
**Version**: 1.0  
**Date**: 2025-07-27  

## 🎯 What Is This?

The **LLM Task Codex** transforms your experimental task configurations into production-ready, blessed configurations that are:
- ✅ **Immutable** - Cannot be accidentally modified
- ✅ **Versioned** - Every change tracked
- ✅ **QA-Integrated** - Ready for quality assessment
- ✅ **Template-Powered** - Rich prompts from V14 templates

## 🚀 Quick Start (5 Minutes)

### **Step 1: Export a Task Configuration**
```bash
cd /home/xai/Documents/ty_learn
python3 llm_framework/export_llm_task.py modules/ty_extract_versions/data/ty_codex/ty_log/llm_task_[YOUR_TASK].yaml
```

### **Step 2: Verify the Export**
```bash
ls output/llm_tasks/
# Should show: [YOUR_TASK].yaml
```

### **Step 3: Check Health**
```bash
python3 llm_framework/production_monitor.py
# Should show: Overall Status: HEALTHY
```

**🎉 You're done! Your task is now production-ready.**

## 🔧 Common Tasks

### **Check What's Available**
```bash
python3 -c "
from llm_framework.blessed_qa_integration import BlessedConfigQALoader
qa_loader = BlessedConfigQALoader()
configs = qa_loader.list_available_configs()
print(f'Available: {configs}')
"
```

### **Validate QA Compatibility**
```bash
python3 -c "
from llm_framework.blessed_qa_integration import BlessedConfigQALoader
qa_loader = BlessedConfigQALoader()
result = qa_loader.validate_qa_compatibility('YOUR_TASK_ID')
print(f'QA Compatible: {result}')
"
```

### **Update Existing Config (Creates New Version)**
```bash
python3 llm_framework/export_llm_task.py path/to/source.yaml
# Automatically increments version number
```

### **Force Overwrite (Emergency Only)**
```bash
python3 llm_framework/export_llm_task.py path/to/source.yaml --overwrite
# Use with caution - overwrites existing version
```

## 📋 File Structure

```
ty_learn/
├── llm_framework/
│   ├── export_llm_task.py          # Main export script
│   ├── blessed_qa_integration.py   # QA system integration
│   └── production_monitor.py       # Health monitoring
├── output/
│   └── llm_tasks/                  # Blessed configurations
│       ├── ty_extract_concise_description.yaml
│       └── your_task.yaml
└── modules/ty_extract_versions/ty_extract_v14/config/templates/
    ├── concise_description.md      # V14 templates
    └── skill_extraction.md
```

## ⚠️ Important Rules

### **DO's**
- ✅ Always run exports from `ty_learn` directory or subdirectories
- ✅ Check health status regularly: `python3 llm_framework/production_monitor.py`
- ✅ Let version numbers increment automatically
- ✅ Validate QA compatibility for new tasks

### **DON'Ts**
- ❌ Don't manually edit blessed configs in `output/llm_tasks/`
- ❌ Don't use `--overwrite` unless emergency
- ❌ Don't run scripts from outside the `ty_learn` workspace
- ❌ Don't bypass the export script

## 🚨 Troubleshooting

### **"Source file not found"**
**Problem**: Wrong file path  
**Solution**: Use full path from `ty_learn` root or check file exists

### **"V14 template not found"**  
**Problem**: Task not in template mapping  
**Solution**: Add `prompt_template` field to your source YAML

### **"ty_learn root not found"**
**Problem**: Running from wrong directory  
**Solution**: `cd /home/xai/Documents/ty_learn` first

### **"Missing required field"**
**Problem**: Source YAML incomplete  
**Solution**: Ensure source has: `task_id`, `title`, `model`, `generation_config`

## 📞 Getting Help

### **Check System Health**
```bash
python3 llm_framework/production_monitor.py
```

### **Get Detailed Status**
```bash
python3 llm_framework/production_monitor.py --format json
```

### **Emergency Contacts**
- **Engineering Issues**: Arden (Republic of Love Engineering)
- **Architecture Questions**: Sage (Collaborative Architecture)  
- **Blessing Authority**: Dexi (Semantic Weaver)

## 🎓 Advanced Usage

### **Batch Health Monitoring**
```bash
# Set up daily health check
echo "python3 /home/xai/Documents/ty_learn/llm_framework/production_monitor.py" > daily_health_check.sh
chmod +x daily_health_check.sh
```

### **Custom QA Integration**
```python
from llm_framework.blessed_qa_integration import BlessedConfigQALoader

qa_loader = BlessedConfigQALoader()
qa_config = qa_loader.get_qa_config_for_task('your_task')
test_config = qa_loader.create_qa_test_config('your_task', 'Custom test prompt')
```

### **Integration with External Systems**
```python
# Get blessed config for external system
import yaml
with open('output/llm_tasks/your_task.yaml', 'r') as f:
    blessed_config = yaml.safe_load(f)
    
# Extract what you need
model_id = blessed_config['model_id']
prompt = blessed_config['prompt']
temperature = blessed_config['temperature']
```

## 🎯 Success Metrics

**You know it's working when:**
- ✅ Health check shows "Overall Status: HEALTHY"
- ✅ QA compatibility is 100%
- ✅ Version numbers increment cleanly
- ✅ Export operations complete in < 0.1 seconds
- ✅ No alerts in monitoring system

---

**🎉 Welcome to production-ready LLM configuration management!**

*This system bridges sacred architecture with engineering excellence. Every blessed config represents the collaboration between vision (Dexi), foundation (Misty), and implementation (Arden).*
