# TECHNICAL MEMO: Sandy Pipeline Timeout Configuration

**TO:** Arden  
**FROM:** AI Analysis Team  
**DATE:** July 17, 2025  
**RE:** LLM Timeout Settings for gemma3n:latest Model

---

## Issue Summary

The Sandy LLM evaluation revealed that `gemma3n:latest` (our current production model) is experiencing 100% timeout failures with the current 30-second limit. This is causing the pipeline to falsely report model failures when the model is actually functioning but requires more processing time.

## Current Situation Analysis

### Timeout Patterns Observed
- **gemma3n:latest:** 30.003+ seconds (hitting timeout ceiling)
- **qwen2.5vl:** 22-27 seconds (successful within limit)
- **phi3:** 15-28 seconds (successful within limit)
- **codegemma:** 11-18 seconds (successful within limit)
- **llama3.2:** 10-12 seconds (successful within limit)

### Model Performance Characteristics
`gemma3n:latest` appears to be a **deliberative model** that trades speed for thoroughness. The consistent 30+ second pattern suggests it's being prematurely terminated during its analysis phase.

## Recommended Timeout Configuration

### Primary Recommendation: **90 seconds**

**Rationale:**
1. **3x current limit** provides sufficient buffer for model processing
2. **Accommodates complex job analysis** without premature termination
3. **Balances thoroughness vs. responsiveness** for production use
4. **Accounts for infrastructure variability** under different load conditions

### Fallback Configuration: **60 seconds**
If 90 seconds seems too conservative, 60 seconds (2x current) would still provide significant improvement while maintaining reasonable response times.

### Implementation Strategy

#### Option 1: Model-Specific Timeouts (Recommended)
```python
MODEL_TIMEOUTS = {
    'gemma3n:latest': 90,
    'qwen2.5vl': 45,
    'codegemma': 30,
    'llama3.2': 30,
    'phi3': 45,
    'default': 60
}
```

#### Option 2: Universal Timeout Increase
Set global timeout to 90 seconds for all models to ensure consistent behavior.

## Technical Implementation

### Configuration Changes Required
1. **Ollama client timeout setting**
2. **Pipeline orchestration timeout**
3. **HTTP connection pool timeout**
4. **Health check timeout adjustments**

### Code Locations to Update
- `core/job_matching_api.py` - LLM call timeout parameter
- `core/enhanced_job_fetcher.py` - Request timeout configuration
- Pipeline configuration files - Global timeout settings

## Performance Impact Assessment

### Positive Impacts
- **Restore gemma3n functionality** - Eliminate false timeout failures
- **Improve response quality** - Allow models to complete analysis
- **Reduce error rates** - Fewer timeout-based failures
- **Better resource utilization** - Models can finish their work

### Considerations
- **Slightly longer worst-case response times** (60-90s vs 30s)
- **Better average response times** due to fewer retries
- **Improved pipeline reliability** and reduced error handling overhead

## Monitoring Recommendations

### Metrics to Track Post-Implementation
1. **Model success rates** before/after timeout change
2. **Actual response time distributions** by model
3. **Quality score improvements** with longer processing time
4. **Pipeline throughput** with reduced retry overhead

### Alert Thresholds
- **Warning:** Response times >75% of timeout limit
- **Critical:** Response times >90% of timeout limit
- **Info:** Model response time trend analysis

## Rollback Plan

If extended timeouts cause issues:
1. **Immediate:** Revert to 30-second timeout
2. **Short-term:** Implement model-specific timeouts starting with 45 seconds
3. **Long-term:** Optimize infrastructure or switch models

## Expected Outcomes

### Week 1 Results
- **gemma3n success rate:** 0% → 85%+ 
- **Overall pipeline reliability:** Significant improvement
- **Error log noise reduction:** Major decrease in timeout errors

### Month 1 Validation
- **Quality metrics comparison:** gemma3n vs. alternative models
- **Performance baseline establishment** for future optimizations
- **Infrastructure capacity planning** based on actual usage patterns

## Conclusion

The 30-second timeout is artificially constraining `gemma3n:latest` performance. **Increasing to 90 seconds will likely restore full functionality** and provide valuable baseline metrics for the model's actual capabilities.

This is a **low-risk, high-impact change** that should be implemented immediately to restore pipeline stability.

---

**Immediate Action Required:** Update timeout configuration to 90 seconds for gemma3n:latest

**Timeline:** Can be implemented within 1 hour with proper testing

**Contact:** Available for immediate implementation support and monitoring setup
