# V16 Model Health Tracking & Blacklisting System

## Overview

The V16 batch testing framework includes an intelligent model health tracking system that automatically identifies and blacklists poorly performing models during testing. This ensures efficient resource utilization and prevents wasted time on consistently failing models.

## Blacklisting Criteria

### Automatic Blacklisting Triggers

1. **Consecutive Failures**: Models are blacklisted after **3 consecutive failures**
   - Prevents endless retry loops with broken models
   - Quickly identifies models that are completely non-responsive

2. **Low Success Rate**: Models with < **20% success rate** after 5+ attempts are blacklisted
   - Identifies models with consistently poor performance
   - Allows some initial failures but blacklists persistently problematic models

### Health Metrics Tracked

For each model, the system tracks:
- **Total attempts** and **successes/failures**
- **Consecutive failure count** (resets on success)
- **Average response time** for successful calls
- **Error type distribution** (timeout, connection, parsing, etc.)
- **Last success/failure timestamps**

## Blacklisting Process

1. **Real-time Monitoring**: Health metrics update after each model call
2. **Immediate Blacklisting**: Models are blacklisted as soon as criteria are met
3. **Skip Future Tests**: Blacklisted models are skipped in subsequent job tests
4. **Detailed Logging**: All blacklisting events are logged with reasons

## Benefits

### Efficiency Gains
- **Faster Testing**: Skip known problematic models
- **Resource Conservation**: Don't waste compute on failing models  
- **Better Results**: Focus on models that actually work

### Intelligent Adaptation
- **Dynamic Learning**: System learns which models work in your environment
- **Automatic Recovery**: Models can be un-blacklisted if manually tested later
- **Pattern Recognition**: Identifies systematic issues (e.g., all large models failing due to memory)

## Output Files

### Model Health Report (`model_health_report.json`)
```json
{
  "blacklisted_models": ["model1", "model2"],
  "blacklist_thresholds": {
    "max_consecutive_failures": 3,
    "min_success_rate_threshold": 0.2
  },
  "model_health_details": {
    "model_name": {
      "total_attempts": 10,
      "successes": 2,
      "failures": 8,
      "consecutive_failures": 3,
      "avg_response_time": 1.5,
      "error_types": {
        "timeout": 5,
        "connection_error": 3
      },
      "last_success": "2025-07-31T10:15:30",
      "last_failure": "2025-07-31T10:20:45"
    }
  }
}
```

### Enhanced Summary Report
- Shows healthy vs. blacklisted model counts
- Individual model status (✅ Active / 🚫 Blacklisted)
- Performance metrics for all models
- Blacklisting reasons and failure patterns

## Example Blacklisting Scenarios

### Scenario 1: Broken Model
```
Model: qwen3:0.6b
- Attempt 1: Connection timeout ❌
- Attempt 2: Connection timeout ❌  
- Attempt 3: Connection timeout ❌
- Result: 🚫 BLACKLISTED (3 consecutive failures)
```

### Scenario 2: Inconsistent Model
```
Model: phi3:3.8b
- Tests: 8 attempts, 1 success, 7 failures
- Success Rate: 12.5% (< 20% threshold)
- Result: 🚫 BLACKLISTED (low success rate)
```

### Scenario 3: Healthy Model
```
Model: deepseek-r1:8b
- Tests: 10 attempts, 9 successes, 1 failure
- Success Rate: 90%
- Status: ✅ Active (continues testing)
```

## Configuration

### Adjustable Thresholds
- `max_consecutive_failures`: Default 3, can be adjusted for stricter/looser criteria
- `min_success_rate_threshold`: Default 0.2 (20%), can be tuned based on requirements

### Manual Override
- Blacklists can be cleared between test runs
- Individual models can be manually excluded/included
- Thresholds can be adjusted for different testing phases

## Best Practices

1. **Start with Quick Validation**: Use small test sets to identify problematic models early
2. **Review Health Reports**: Analyze blacklisting patterns to identify systemic issues
3. **Adjust Thresholds**: Fine-tune based on your model environment and requirements
4. **Monitor Logs**: Watch for blacklisting events during testing
5. **Clean Slate Testing**: Periodically clear blacklists to test model recovery

## Integration with Testing Workflow

The blacklisting system integrates seamlessly with all testing modes:
- **Quick Validation**: Rapidly identifies major issues
- **Medium Validation**: Balances discovery with efficiency  
- **Comprehensive Testing**: Maximizes model coverage while avoiding waste
- **Full Production**: Scales efficiently across large test matrices

This intelligent system ensures your V16 testing is both comprehensive and efficient, automatically adapting to your specific model environment and performance characteristics.
