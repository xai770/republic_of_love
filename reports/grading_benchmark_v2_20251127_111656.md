# Model Benchmark Report: Grading

**Generated:** 2025-11-27 11:47:35

**Task:** grading
**Test Cases:** 10
**Models Tested:** 24

---

## ❌ NO CHAMPION FOUND

No model achieved 100% correctness.

---

## 📊 Complete Results

| Rank | Model | Correctness | Avg Latency (ms) | Qualified | Score |
|------|-------|-------------|------------------|-----------|-------|
| 1 | `codegemma:2b` | 1/10 (10.0%) | 1755.2 | ❌ | 0.0 |
| 2 | `codegemma:latest` | 6/10 (60.0%) | 8689.4 | ❌ | 0.0 |
| 3 | `dolphin3:8b` | 8/10 (80.0%) | 4120.9 | ❌ | 0.0 |
| 4 | `dolphin3:latest` | 5/10 (50.0%) | 4250.0 | ❌ | 0.0 |
| 5 | `gemma2:latest` | 9/10 (90.0%) | 18961.0 | ❌ | 0.0 |
| 6 | `gemma3:1b` | 4/10 (40.0%) | 1337.8 | ❌ | 0.0 |
| 7 | `gemma3:4b` | 5/10 (50.0%) | 2884.3 | ❌ | 0.0 |
| 8 | `gemma3n:e2b` | 8/10 (80.0%) | 4749.4 | ❌ | 0.0 |
| 9 | `gemma3n:latest` | 7/10 (70.0%) | 6521.8 | ❌ | 0.0 |
| 10 | `granite3.1-moe:3b` | 5/10 (50.0%) | 2385.0 | ❌ | 0.0 |
| 11 | `llama3.2:1b` | 6/10 (60.0%) | 1739.6 | ❌ | 0.0 |
| 12 | `llama3.2:latest` | 5/10 (50.0%) | 3049.0 | ❌ | 0.0 |
| 13 | `mistral:latest` | 8/10 (80.0%) | 4074.3 | ❌ | 0.0 |
| 14 | `mistral-nemo:12b` | 4/10 (40.0%) | 22876.6 | ❌ | 0.0 |
| 15 | `olmo2:7b` | 2/10 (20.0%) | 15423.2 | ❌ | 0.0 |
| 16 | `olmo2:latest` | 3/10 (30.0%) | 12610.4 | ❌ | 0.0 |
| 17 | `phi3:3.8b` | 5/10 (50.0%) | 5031.2 | ❌ | 0.0 |
| 18 | `phi3:latest` | 5/10 (50.0%) | 5647.6 | ❌ | 0.0 |
| 19 | `phi4-mini:latest` | 6/10 (60.0%) | 5799.6 | ❌ | 0.0 |
| 20 | `qwen2.5:7b` | 8/10 (80.0%) | 6748.1 | ❌ | 0.0 |
| 21 | `qwen2.5vl:latest` | 5/10 (50.0%) | 15709.6 | ❌ | 0.0 |
| 22 | `qwen3:0.6b` | 0/10 (0.0%) | 3124.9 | ❌ | 0.0 |
| 23 | `qwen3:1.7b` | 0/10 (0.0%) | 9960.9 | ❌ | 0.0 |
| 24 | `qwen3:4b` | 0/10 (0.0%) | 16405.3 | ❌ | 0.0 |

---

## 🔍 Detailed Test Results

### codegemma:2b

**Correctness:** 1/10 (10.0%)
**Avg Latency:** 1755.2ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | UNKNOWN | ❌ | 7567.5 | - |
| GRADE_FAIL_002 | FAIL | UNKNOWN | ❌ | 180.1 | - |
| GRADE_PASS_001 | PASS | UNKNOWN | ❌ | 511.7 | - |
| GRADE_PASS_002 | PASS | UNKNOWN | ❌ | 459.1 | - |
| GRADE_PASS_003 | PASS | UNKNOWN | ❌ | 378.1 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 754.0 | - |
| GRADE_PASS_005 | PASS | UNKNOWN | ❌ | 5436.3 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 233.3 | - |
| GRADE_FAIL_004 | FAIL | UNKNOWN | ❌ | 612.1 | - |
| GRADE_FAIL_005 | FAIL | UNKNOWN | ❌ | 1420.0 | - |

### codegemma:latest

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 8689.4ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 12415.4 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 5296.8 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 9212.2 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 8492.3 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 13983.5 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 7127.1 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 9963.6 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 5830.4 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 6820.1 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 7752.8 | - |

### dolphin3:8b

**Correctness:** 8/10 (80.0%)
**Avg Latency:** 4120.9ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 8405.3 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 3880.5 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 3784.2 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 3957.4 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 3564.7 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 3824.8 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 4113.5 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 2977.5 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 3400.7 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 3300.8 | - |

### dolphin3:latest

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 4250.0ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 3269.8 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 4231.8 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 5683.6 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 5416.2 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 3047.0 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 3008.9 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 6596.9 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 3912.0 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 2566.9 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 4766.5 | - |

### gemma2:latest

**Correctness:** 9/10 (90.0%)
**Avg Latency:** 18961.0ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 29843.5 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 16076.8 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 24454.0 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 18506.9 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 20308.3 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 21412.2 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 14946.2 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 6658.0 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 18481.7 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 18922.1 | - |

### gemma3:1b

**Correctness:** 4/10 (40.0%)
**Avg Latency:** 1337.8ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 3108.0 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 911.8 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 1222.7 | - |
| GRADE_PASS_002 | PASS | FAIL | ❌ | 1217.2 | - |
| GRADE_PASS_003 | PASS | FAIL | ❌ | 1308.0 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 1056.2 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 1065.5 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 591.5 | - |
| GRADE_FAIL_004 | FAIL | FAIL | ✅ | 1462.1 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 1435.3 | - |

### gemma3:4b

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 2884.3ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 5234.7 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 1636.0 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 4402.1 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 2449.7 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 4303.7 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 1988.0 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 1543.0 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 1238.3 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 1707.8 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 4340.1 | - |

### gemma3n:e2b

**Correctness:** 8/10 (80.0%)
**Avg Latency:** 4749.4ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 8806.1 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 4335.5 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 3958.0 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 6376.4 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 7297.0 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 3129.5 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 4250.3 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 2414.8 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 3024.9 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 3901.2 | - |

### gemma3n:latest

**Correctness:** 7/10 (70.0%)
**Avg Latency:** 6521.8ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 19429.8 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 9575.0 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 5741.8 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 4663.3 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 4930.7 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 4493.5 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 4272.9 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 4370.5 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 3562.5 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 4177.5 | - |

### granite3.1-moe:3b

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 2385.0ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 3259.7 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 997.7 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 6200.1 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 3156.0 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 1491.5 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 1651.1 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 1537.8 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 909.7 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 1735.9 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 2910.1 | - |

### llama3.2:1b

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 1739.6ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 8267.9 | - |
| GRADE_FAIL_002 | FAIL | UNKNOWN | ❌ | 3001.1 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 2507.5 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 400.5 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 359.5 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 347.6 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 1641.8 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 238.4 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 315.6 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 316.1 | - |

### llama3.2:latest

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 3049.0ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 4769.3 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 2327.6 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 4249.1 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 4278.3 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 3866.6 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 2720.6 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 2180.0 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 669.2 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 2584.1 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 2844.9 | - |

### mistral:latest

**Correctness:** 8/10 (80.0%)
**Avg Latency:** 4074.3ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 9753.2 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 3826.6 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 3637.3 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 4206.1 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 3231.8 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 2470.8 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 2789.6 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 2724.3 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 3042.2 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 5060.9 | - |

### mistral-nemo:12b

**Correctness:** 4/10 (40.0%)
**Avg Latency:** 22876.6ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 22815.6 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 12372.8 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 23533.8 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 34368.5 | - |
| GRADE_PASS_003 | PASS | FAIL | ❌ | 29408.3 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 36114.6 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 12147.2 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 11754.8 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 27946.0 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 18304.3 | - |

### olmo2:7b

**Correctness:** 2/10 (20.0%)
**Avg Latency:** 15423.2ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 15239.6 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 6103.2 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 15375.4 | - |
| GRADE_PASS_002 | PASS | FAIL | ❌ | 18465.1 | - |
| GRADE_PASS_003 | PASS | FAIL | ❌ | 12959.5 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 36878.1 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 15612.8 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 8561.3 | - |
| GRADE_FAIL_004 | FAIL | FAIL | ✅ | 16189.1 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 8848.4 | - |

### olmo2:latest

**Correctness:** 3/10 (30.0%)
**Avg Latency:** 12610.4ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 8470.6 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 8074.2 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 11608.7 | - |
| GRADE_PASS_002 | PASS | FAIL | ❌ | 20990.5 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 14964.8 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 18746.6 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 10747.5 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 9716.6 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 10358.9 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 12425.2 | - |

### phi3:3.8b

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 5031.2ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 8305.0 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 3447.1 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 4448.9 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 4503.7 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 5472.6 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 5476.0 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 3824.7 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 4539.4 | - |
| GRADE_FAIL_004 | FAIL | UNKNOWN | ❌ | 6260.9 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 4034.2 | - |

### phi3:latest

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 5647.6ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 4634.2 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 4445.0 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 10277.7 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 5255.8 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 6689.5 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 6884.5 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 6168.2 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 2986.1 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 3987.5 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 5147.2 | - |

### phi4-mini:latest

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 5799.6ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 8930.6 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 6401.2 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 4659.3 | - |
| GRADE_PASS_002 | PASS | FAIL | ❌ | 5449.7 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 5986.0 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 5150.0 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 6324.4 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 2031.7 | - |
| GRADE_FAIL_004 | FAIL | FAIL | ✅ | 6343.6 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 6719.6 | - |

### qwen2.5:7b

**Correctness:** 8/10 (80.0%)
**Avg Latency:** 6748.1ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 9039.0 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 5327.3 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 6864.2 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 7333.5 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 9462.1 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 7242.7 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 5134.8 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 2719.2 | - |
| GRADE_FAIL_004 | FAIL | FAIL | ✅ | 6010.0 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 8348.3 | - |

### qwen2.5vl:latest

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 15709.6ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 22729.1 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 15886.8 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 8420.7 | - |
| GRADE_PASS_002 | PASS | FAIL | ❌ | 8169.0 | - |
| GRADE_PASS_003 | PASS | FAIL | ❌ | 23392.7 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 16058.4 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 21920.1 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 5727.2 | - |
| GRADE_FAIL_004 | FAIL | FAIL | ✅ | 17862.2 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 16930.3 | - |

### qwen3:0.6b

**Correctness:** 0/10 (0.0%)
**Avg Latency:** 3124.9ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | UNKNOWN | ❌ | 5128.9 | - |
| GRADE_FAIL_002 | FAIL | UNKNOWN | ❌ | 3012.9 | - |
| GRADE_PASS_001 | PASS | UNKNOWN | ❌ | 3041.2 | - |
| GRADE_PASS_002 | PASS | UNKNOWN | ❌ | 3349.3 | - |
| GRADE_PASS_003 | PASS | UNKNOWN | ❌ | 3470.6 | - |
| GRADE_PASS_004 | PASS | UNKNOWN | ❌ | 2515.0 | - |
| GRADE_PASS_005 | PASS | UNKNOWN | ❌ | 2409.2 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 1648.9 | - |
| GRADE_FAIL_004 | FAIL | UNKNOWN | ❌ | 3499.6 | - |
| GRADE_FAIL_005 | FAIL | UNKNOWN | ❌ | 3173.8 | - |

### qwen3:1.7b

**Correctness:** 0/10 (0.0%)
**Avg Latency:** 9960.9ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | UNKNOWN | ❌ | 10597.5 | - |
| GRADE_FAIL_002 | FAIL | UNKNOWN | ❌ | 19042.7 | - |
| GRADE_PASS_001 | PASS | UNKNOWN | ❌ | 5825.0 | - |
| GRADE_PASS_002 | PASS | UNKNOWN | ❌ | 12349.4 | - |
| GRADE_PASS_003 | PASS | UNKNOWN | ❌ | 10223.4 | - |
| GRADE_PASS_004 | PASS | UNKNOWN | ❌ | 7935.3 | - |
| GRADE_PASS_005 | PASS | UNKNOWN | ❌ | 7453.8 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 6328.6 | - |
| GRADE_FAIL_004 | FAIL | UNKNOWN | ❌ | 6914.1 | - |
| GRADE_FAIL_005 | FAIL | UNKNOWN | ❌ | 12938.7 | - |

### qwen3:4b

**Correctness:** 0/10 (0.0%)
**Avg Latency:** 16405.3ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | UNKNOWN | ❌ | 10803.6 | - |
| GRADE_FAIL_002 | FAIL | UNKNOWN | ❌ | 9231.9 | - |
| GRADE_PASS_001 | PASS | UNKNOWN | ❌ | 17381.9 | - |
| GRADE_PASS_002 | PASS | UNKNOWN | ❌ | 14621.1 | - |
| GRADE_PASS_003 | PASS | UNKNOWN | ❌ | 17278.8 | - |
| GRADE_PASS_004 | PASS | UNKNOWN | ❌ | 10220.7 | - |
| GRADE_PASS_005 | PASS | UNKNOWN | ❌ | 13627.6 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 7710.6 | - |
| GRADE_FAIL_004 | FAIL | UNKNOWN | ❌ | 51689.7 | - |
| GRADE_FAIL_005 | FAIL | UNKNOWN | ❌ | 11486.6 | - |

---

## 📈 Summary Statistics

- **Total Models Tested:** 24
- **Qualified (100% correct):** 0
- **Disqualified:** 24
- **Test Cases:** 10
- **Pass Cases:** 5
- **Fail Cases:** 5

