# Three-Way Comparison Analysis: Manual vs HTTP API vs CLI

## Executive Summary
This analysis compares LLM performance across three different testing methods: Manual CLI testing, HTTP API scripted testing, and CLI scripted testing. **The results reveal significant interface-dependent performance differences.**

## Key Findings by Model

### **DeepSeek-R1:8b**
- **Manual CLI**: 7/8 correct (87.5% accuracy)
- **HTTP API**: 0/8 correct (0% accuracy) - responses truncated with `<think>` tags
- **CLI Scripted**: 4/8 correct (50% accuracy) - some timeouts, but correct answers when completed
- **Conclusion**: Manual > CLI Scripted > HTTP API

### **Qwen3:latest** 
- **Manual CLI**: 8/8 correct (100% accuracy) 
- **HTTP API**: 0/8 correct (0% accuracy) - same truncation issue
- **CLI Scripted**: 8/8 correct (100% accuracy) - perfect match with manual!
- **Conclusion**: Manual = CLI Scripted >> HTTP API

### **CodeGemma:latest**
- **Manual CLI**: 4/8 correct (50% accuracy)
- **HTTP API**: 4/8 correct (50% accuracy) 
- **CLI Scripted**: 5/8 correct (62.5% accuracy)
- **Conclusion**: Consistent across interfaces, slight CLI advantage

### **GPT-OSS:latest**
- **Manual CLI**: 8/8 correct (100% accuracy)
- **HTTP API**: 6/8 correct (75% accuracy) - some missing responses
- **CLI Scripted**: 8/8 correct (100% accuracy) - perfect match with manual!
- **Conclusion**: Manual = CLI Scripted > HTTP API

## Critical Insights

### **1. Interface Method Dramatically Affects Results**
- **CLI methods** (both manual and scripted) allow reasoning models to complete their thought processes
- **HTTP API** consistently truncates reasoning model responses, causing 100% failure rate for DeepSeek-R1 and Qwen3

### **2. Manual vs CLI Scripted Correlation**
- **High correlation** for models that work well (Qwen3, GPT-OSS): 100% match
- **Moderate correlation** for reasoning-heavy models (DeepSeek-R1): timeouts affect scripted version
- **Good correlation** for simpler models (CodeGemma): consistent behavior across methods

### **3. Reasoning Models Require Proper Interface**
- Models with `<think>` capabilities (DeepSeek-R1, Qwen3) **fail completely** via HTTP API
- Same models **perform excellently** via CLI interface
- This suggests **API implementation differences** in handling reasoning tokens

## Recommendations

### **For Testing Methodology**
1. **Use CLI interface** for reasoning-capable models (DeepSeek-R1, Qwen3)
2. **HTTP API acceptable** for simpler models without extensive reasoning processes
3. **Manual testing remains gold standard** for capturing true model capabilities

### **For Model Selection**
1. **Qwen3:latest** shows most consistent performance across interfaces (100% CLI accuracy)
2. **GPT-OSS:latest** reliable across methods with good performance
3. **DeepSeek-R1** powerful but interface-sensitive (manual testing reveals true capability)
4. **CodeGemma** shows consistent limitations across all interfaces

## Conclusion
This analysis validates that **testing methodology significantly impacts results**. Your manual CLI testing captured the true performance of reasoning models, while HTTP API testing severely underestimated their capabilities. CLI scripted testing provides a good middle ground, achieving high correlation with manual results while enabling systematic evaluation.

**Bottom line**: Manual testing wasn't just convenient—it was actually **more accurate** for evaluating reasoning model capabilities.