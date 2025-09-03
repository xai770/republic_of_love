# 📚 LLM Task Codex - Production Operations Runbook

**Document Version**: 1.0  
**Date**: 2025-07-27  
**Author**: Arden (Republic of Love Engineering)  
**Status**: Production Ready  

## 🎯 Overview

The LLM Task Codex system transforms mutable `ty_log` task configurations into blessed, immutable `ty_codex` configurations for production use. This runbook covers all operational procedures for production deployment and maintenance.

## 🏗️ System Architecture

### **Sacred Boundaries**
- **`ty_log`** (Mutable): Source configurations for evolution and experimentation
- **`ty_codex`** (Blessed): Immutable configurations for production execution
- **Templates**: V14 template integration for rich prompt content

### **Components**
- **Export Script**: `llm_framework/export_llm_task.py`
- **QA Integration**: `llm_framework/blessed_qa_integration.py`
- **Blessed Configs**: `output/llm_tasks/*.yaml`
- **Templates**: `modules/ty_extract_versions/ty_extract_v14/config/templates/`

## 🚀 Production Operations

### **1. Exporting New Task Configurations**

#### **Basic Export**
```bash
cd /home/xai/Documents/ty_learn
python3 llm_framework/export_llm_task.py modules/ty_extract_versions/data/ty_codex/ty_log/llm_task_[TASK_NAME].yaml
```

#### **Force Overwrite (Use with Caution)**
```bash
python3 llm_framework/export_llm_task.py [SOURCE_FILE] --overwrite
```

#### **Expected Output**
```
2025-07-27 17:36:30,916 - INFO - 🚀 Starting LLM Task Codex Export
2025-07-27 17:36:30,918 - INFO - ✅ Source validation passed
2025-07-27 17:36:30,918 - INFO - Using V14 template: [TEMPLATE_PATH]
2025-07-27 17:36:30,920 - INFO - ✅ Version incremented to [N]
2025-07-27 17:36:30,922 - INFO - ✅ Export completed successfully
```

### **2. Validating Blessed Configurations**

#### **Check Config Integrity**
```bash
python3 -c "
import yaml
from pathlib import Path

config_path = Path('output/llm_tasks/[TASK_ID].yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

print(f'Task ID: {config[\"task_id\"]}')
print(f'Version: {config[\"version\"]}')
print(f'QA Schema: {config[\"qa_schema_id\"]}')
print(f'Blessed by: {config[\"blessed_by\"]}')
print(f'Blessed on: {config[\"blessed_on\"]}')
"
```

#### **QA Compatibility Check**
```bash
python3 -c "
from llm_framework.blessed_qa_integration import BlessedConfigQALoader

qa_loader = BlessedConfigQALoader()
is_compatible = qa_loader.validate_qa_compatibility('[TASK_ID]')
print(f'QA Compatible: {\"PASS\" if is_compatible else \"FAIL\"}')
"
```

### **3. Monitoring and Alerts**

#### **Health Check Commands**
```bash
# Check blessed configs directory
ls -la output/llm_tasks/

# Count available configs
python3 -c "
from llm_framework.blessed_qa_integration import BlessedConfigQALoader
qa_loader = BlessedConfigQALoader()
configs = qa_loader.list_available_configs()
print(f'Available configs: {len(configs)}')
"
```

#### **Performance Monitoring**
- **Export time**: Should be < 0.1 seconds per operation
- **Config size**: Typically 1500-3000 bytes per blessed config
- **Version progression**: Should increment monotonically

## 🔧 Troubleshooting Guide

### **Common Issues**

#### **"Source file not found"**
```bash
❌ Export failed: Source file not found: [PATH]
```
**Solution**: Verify source file path is correct and file exists in `ty_log/`

#### **"V14 template not found"**
```bash
❌ Export failed: V14 template not found: [TEMPLATE_PATH]
```
**Solution**: Check template mapping in `extract_prompt_content()` or add `prompt_template` field to source

#### **"Missing required field"**
```bash
❌ Export failed: Missing required field: model
```
**Solution**: Validate source YAML has all required fields: `task_id`, `title`, `model`, `generation_config`

#### **"ty_learn root not found"**
```bash
❌ ty_learn root not found - ensure script runs within ty_learn workspace
```
**Solution**: Run commands from within `/home/xai/Documents/ty_learn` or subdirectories

### **Advanced Troubleshooting**

#### **Corrupted Blessed Config**
```bash
# Check file integrity
python3 -c "
import yaml
try:
    with open('output/llm_tasks/[TASK_ID].yaml', 'r') as f:
        config = yaml.safe_load(f)
    print('✅ Config is valid YAML')
except Exception as e:
    print(f'❌ Config corrupted: {e}')
"

# Re-export if needed
python3 llm_framework/export_llm_task.py [SOURCE_FILE] --overwrite
```

#### **Version Conflicts**
```bash
# Check current version
python3 -c "
import yaml
with open('output/llm_tasks/[TASK_ID].yaml', 'r') as f:
    config = yaml.safe_load(f)
print(f'Current version: {config[\"version\"]}')
"

# Force specific version (emergency only)
# Edit blessed config manually and set version field
```

## 📊 Maintenance Procedures

### **Daily Operations**
- [ ] Monitor export success rates
- [ ] Check blessed config directory disk usage
- [ ] Validate QA integration working

### **Weekly Operations**
- [ ] Review version progression patterns
- [ ] Archive old blessed config versions if needed
- [ ] Update template mappings for new tasks

### **Monthly Operations**
- [ ] Performance review of export operations
- [ ] Update documentation with new procedures
- [ ] Team training on any new features

## 🔐 Security Considerations

### **Access Control**
- **Export Operations**: Require appropriate permissions for `ty_log/` source access
- **Blessed Configs**: Protect `output/llm_tasks/` from unauthorized modification
- **Templates**: Maintain integrity of V14 template files

### **Data Integrity**
- **Atomic Writes**: System prevents partial config corruption
- **Version Control**: Track all changes through version numbers
- **Blessing Authority**: Only authorized users (Dexi) can bless configurations

## 🎯 Performance Baselines

### **Expected Performance**
- **Export Speed**: < 0.1 seconds per operation
- **Memory Usage**: < 10MB during export
- **Storage**: ~2KB per blessed config

### **Scaling Considerations**
- System tested up to 5 sequential exports
- No memory leaks detected
- Version management handles large version numbers

## 📞 Emergency Contacts

### **System Issues**
- **Engineering**: Arden (Republic of Love Engineering)
- **Architecture**: Sage (Collaborative Architecture)
- **Blessing Authority**: Dexi (Semantic Weaver)

### **Escalation Path**
1. **Level 1**: Operational issues (missing files, permissions)
2. **Level 2**: System errors (export failures, corruption)
3. **Level 3**: Architectural issues (schema changes, integration problems)

## 📝 Change Management

### **Adding New Tasks**
1. Create source configuration in `ty_log/`
2. Add template mapping if using V14 templates
3. Run export and validate blessed config
4. Update QA compatibility testing
5. Document new task in team knowledge base

### **Updating Templates**
1. Modify V14 templates in appropriate directory
2. Re-export affected tasks to pick up changes
3. Validate QA compatibility maintained
4. Update version numbers appropriately

### **Schema Changes**
1. Coordinate with Sage (Architecture) and Dexi (Blessing)
2. Update export script validation logic
3. Test with existing configurations
4. Document migration procedures
5. Plan rollout strategy

---

**🎉 Production Ready - This system is blessed for immediate deployment!**

**Last Updated**: 2025-07-27  
**Next Review**: 2025-08-27
