# Model Benchmark Report: Grading

**Generated:** 2025-11-27 10:54:34

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
| 1 | `codegemma:2b` | 2/10 (20.0%) | 1871.2 | ❌ | 0.0 |
| 2 | `codegemma:latest` | 5/10 (50.0%) | 5326.9 | ❌ | 0.0 |
| 3 | `dolphin3:8b` | 4/10 (40.0%) | 3379.4 | ❌ | 0.0 |
| 4 | `dolphin3:latest` | 4/10 (40.0%) | 2678.9 | ❌ | 0.0 |
| 5 | `gemma2:latest` | 5/10 (50.0%) | 6838.1 | ❌ | 0.0 |
| 6 | `gemma3:1b` | 6/10 (60.0%) | 1404.6 | ❌ | 0.0 |
| 7 | `gemma3:4b` | 5/10 (50.0%) | 1921.3 | ❌ | 0.0 |
| 8 | `gemma3n:e2b` | 6/10 (60.0%) | 3924.8 | ❌ | 0.0 |
| 9 | `gemma3n:latest` | 6/10 (60.0%) | 3665.4 | ❌ | 0.0 |
| 10 | `granite3.1-moe:3b` | 4/10 (40.0%) | 1358.4 | ❌ | 0.0 |
| 11 | `llama3.2:1b` | 5/10 (50.0%) | 673.4 | ❌ | 0.0 |
| 12 | `llama3.2:latest` | 6/10 (60.0%) | 2753.2 | ❌ | 0.0 |
| 13 | `mistral:latest` | 6/10 (60.0%) | 3001.5 | ❌ | 0.0 |
| 14 | `mistral-nemo:12b` | 5/10 (50.0%) | 16908.5 | ❌ | 0.0 |
| 15 | `olmo2:7b` | 4/10 (40.0%) | 8746.4 | ❌ | 0.0 |
| 16 | `olmo2:latest` | 5/10 (50.0%) | 6997.0 | ❌ | 0.0 |
| 17 | `phi3:3.8b` | 5/10 (50.0%) | 3207.6 | ❌ | 0.0 |
| 18 | `phi3:latest` | 5/10 (50.0%) | 4670.8 | ❌ | 0.0 |
| 19 | `phi4-mini:latest` | 1/10 (10.0%) | 82048.0 | ❌ | 0.0 |
| 20 | `qwen2.5:7b` | 6/10 (60.0%) | 20815.5 | ❌ | 0.0 |
| 21 | `qwen2.5vl:latest` | 3/10 (30.0%) | 5274.7 | ❌ | 0.0 |
| 22 | `qwen3:0.6b` | 0/10 (0.0%) | 2961.5 | ❌ | 0.0 |
| 23 | `qwen3:1.7b` | 0/10 (0.0%) | 8332.9 | ❌ | 0.0 |
| 24 | `qwen3:4b` | 0/10 (0.0%) | 12242.8 | ❌ | 0.0 |

---

## 🔍 Detailed Test Results

### codegemma:2b

**Correctness:** 2/10 (20.0%)
**Avg Latency:** 1871.2ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | UNKNOWN | ❌ | 9944.3 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 524.8 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 399.8 | - |
| GRADE_PASS_002 | PASS | UNKNOWN | ❌ | 510.1 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 336.3 | - |
| GRADE_PASS_004 | PASS | UNKNOWN | ❌ | 289.1 | - |
| GRADE_PASS_005 | PASS | UNKNOWN | ❌ | 1240.1 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 4647.2 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 378.9 | - |
| GRADE_FAIL_005 | FAIL | UNKNOWN | ❌ | 441.9 | - |

### codegemma:latest

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 5326.9ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 8736.8 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 3575.7 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 4604.0 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 5462.7 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 3845.1 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 4648.3 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 4461.8 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 3460.0 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 9520.4 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 4954.4 | - |

### dolphin3:8b

**Correctness:** 4/10 (40.0%)
**Avg Latency:** 3379.4ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 6610.8 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 2338.9 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 5641.8 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 2455.2 | - |
| GRADE_PASS_003 | PASS | FAIL | ❌ | 8403.4 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 2479.3 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 1324.9 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 1549.3 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 1488.8 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 1502.1 | - |

### dolphin3:latest

**Correctness:** 4/10 (40.0%)
**Avg Latency:** 2678.9ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 2363.4 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 1118.8 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 5318.5 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 2893.1 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 2757.7 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 2501.0 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 2924.5 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 1129.8 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 3428.7 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 2353.4 | - |

### gemma2:latest

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 6838.1ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 9692.6 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 7162.1 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 8586.6 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 6390.5 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 7865.8 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 6492.2 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 6993.9 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 3900.0 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 5708.2 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 5589.5 | - |

### gemma3:1b

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 1404.6ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 3190.9 | - |
| GRADE_FAIL_002 | FAIL | FAIL | ✅ | 1122.9 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 1321.6 | - |
| GRADE_PASS_002 | PASS | FAIL | ❌ | 1482.6 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 1726.2 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 779.5 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 1174.4 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 487.3 | - |
| GRADE_FAIL_004 | FAIL | FAIL | ✅ | 1910.5 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 849.7 | - |

### gemma3:4b

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 1921.3ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 4358.5 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 1106.6 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 1571.8 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 1435.5 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 2213.4 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 1703.5 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 2620.9 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 677.4 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 1811.4 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 1714.0 | - |

### gemma3n:e2b

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 3924.8ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 6819.2 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 2168.0 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 3121.7 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 5035.8 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 4700.1 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 2726.6 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 5996.1 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 2534.9 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 3032.7 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 3113.3 | - |

### gemma3n:latest

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 3665.4ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 7992.1 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 2234.2 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 3395.4 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 3572.6 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 3104.5 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 3231.0 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 2904.7 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 3323.5 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 2917.8 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 3978.4 | - |

### granite3.1-moe:3b

**Correctness:** 4/10 (40.0%)
**Avg Latency:** 1358.4ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 2994.6 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 893.7 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 1488.9 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 2384.2 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 1285.6 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 905.6 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 1160.9 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 416.6 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 898.7 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 1154.9 | - |

### llama3.2:1b

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 673.4ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 2360.3 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 191.6 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 496.1 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 929.3 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 917.3 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 852.5 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 239.1 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 205.1 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 263.7 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 278.7 | - |

### llama3.2:latest

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 2753.2ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | FAIL | ✅ | 6038.6 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 2227.7 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 2297.6 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 3175.5 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 2781.5 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 2048.5 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 3007.4 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 782.4 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 2911.0 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 2261.7 | - |

### mistral:latest

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 3001.5ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 6507.8 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 2102.2 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 2926.9 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 2706.6 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 3228.3 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 3182.0 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 3584.8 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 1435.5 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 2297.7 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 2043.6 | - |

### mistral-nemo:12b

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 16908.5ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 25508.0 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 9046.9 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 21322.3 | - |
| GRADE_PASS_002 | PASS | FAIL | ❌ | 15941.2 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 18447.0 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 20309.1 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 23411.0 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 1585.0 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 15372.4 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 18142.1 | - |

### olmo2:7b

**Correctness:** 4/10 (40.0%)
**Avg Latency:** 8746.4ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 9972.2 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 7638.9 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 11355.2 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 4722.0 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 5211.9 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 6296.7 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 5511.3 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 4624.2 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 875.2 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 31256.2 | - |

### olmo2:latest

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 6997.0ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 517.0 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 334.1 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 6620.4 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 6250.0 | - |
| GRADE_PASS_003 | PASS | FAIL | ❌ | 7493.5 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 10101.9 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 8227.3 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 16029.6 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 8136.1 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 6260.3 | - |

### phi3:3.8b

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 3207.6ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 6503.9 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 2817.8 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 2501.7 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 3530.6 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 4336.8 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 2249.1 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 1802.4 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 2727.0 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 2067.1 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 3539.2 | - |

### phi3:latest

**Correctness:** 5/10 (50.0%)
**Avg Latency:** 4670.8ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 2534.3 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 15402.1 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 4527.1 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 7524.5 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 3482.5 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 3668.3 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 1798.7 | - |
| GRADE_FAIL_003 | FAIL | PASS | ❌ | 1284.8 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 4138.6 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 2347.0 | - |

### phi4-mini:latest

**Correctness:** 1/10 (10.0%)
**Avg Latency:** 82048.0ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 14876.7 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 4699.8 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 5066.7 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 75828.7 | - |
| GRADE_PASS_003 | PASS | TIMEOUT | ❌ | 120001.4 | Model timeout (>120s) |
| GRADE_PASS_004 | PASS | TIMEOUT | ❌ | 120001.9 | Model timeout (>120s) |
| GRADE_PASS_005 | PASS | TIMEOUT | ❌ | 120001.3 | Model timeout (>120s) |
| GRADE_FAIL_003 | FAIL | TIMEOUT | ❌ | 120000.8 | Model timeout (>120s) |
| GRADE_FAIL_004 | FAIL | TIMEOUT | ❌ | 120001.3 | Model timeout (>120s) |
| GRADE_FAIL_005 | FAIL | TIMEOUT | ❌ | 120001.3 | Model timeout (>120s) |

### qwen2.5:7b

**Correctness:** 6/10 (60.0%)
**Avg Latency:** 20815.5ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | TIMEOUT | ❌ | 120001.6 | Model timeout (>120s) |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 69285.3 | - |
| GRADE_PASS_001 | PASS | PASS | ✅ | 2647.4 | - |
| GRADE_PASS_002 | PASS | PASS | ✅ | 2719.9 | - |
| GRADE_PASS_003 | PASS | PASS | ✅ | 2508.2 | - |
| GRADE_PASS_004 | PASS | PASS | ✅ | 2442.9 | - |
| GRADE_PASS_005 | PASS | PASS | ✅ | 2164.2 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 1600.6 | - |
| GRADE_FAIL_004 | FAIL | PASS | ❌ | 2779.4 | - |
| GRADE_FAIL_005 | FAIL | PASS | ❌ | 2005.9 | - |

### qwen2.5vl:latest

**Correctness:** 3/10 (30.0%)
**Avg Latency:** 5274.7ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | PASS | ❌ | 7121.0 | - |
| GRADE_FAIL_002 | FAIL | PASS | ❌ | 2977.6 | - |
| GRADE_PASS_001 | PASS | FAIL | ❌ | 6020.7 | - |
| GRADE_PASS_002 | PASS | FAIL | ❌ | 4508.3 | - |
| GRADE_PASS_003 | PASS | FAIL | ❌ | 5008.5 | - |
| GRADE_PASS_004 | PASS | FAIL | ❌ | 4504.2 | - |
| GRADE_PASS_005 | PASS | FAIL | ❌ | 6450.4 | - |
| GRADE_FAIL_003 | FAIL | FAIL | ✅ | 3020.8 | - |
| GRADE_FAIL_004 | FAIL | FAIL | ✅ | 5640.0 | - |
| GRADE_FAIL_005 | FAIL | FAIL | ✅ | 7495.8 | - |

### qwen3:0.6b

**Correctness:** 0/10 (0.0%)
**Avg Latency:** 2961.5ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | UNKNOWN | ❌ | 3124.4 | - |
| GRADE_FAIL_002 | FAIL | UNKNOWN | ❌ | 1790.6 | - |
| GRADE_PASS_001 | PASS | UNKNOWN | ❌ | 5642.1 | - |
| GRADE_PASS_002 | PASS | UNKNOWN | ❌ | 2628.6 | - |
| GRADE_PASS_003 | PASS | UNKNOWN | ❌ | 2693.9 | - |
| GRADE_PASS_004 | PASS | UNKNOWN | ❌ | 1972.0 | - |
| GRADE_PASS_005 | PASS | UNKNOWN | ❌ | 2261.6 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 5447.4 | - |
| GRADE_FAIL_004 | FAIL | UNKNOWN | ❌ | 1672.4 | - |
| GRADE_FAIL_005 | FAIL | UNKNOWN | ❌ | 2382.0 | - |

### qwen3:1.7b

**Correctness:** 0/10 (0.0%)
**Avg Latency:** 8332.9ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | UNKNOWN | ❌ | 18368.9 | - |
| GRADE_FAIL_002 | FAIL | UNKNOWN | ❌ | 3983.1 | - |
| GRADE_PASS_001 | PASS | UNKNOWN | ❌ | 9878.6 | - |
| GRADE_PASS_002 | PASS | UNKNOWN | ❌ | 6779.5 | - |
| GRADE_PASS_003 | PASS | UNKNOWN | ❌ | 7773.6 | - |
| GRADE_PASS_004 | PASS | UNKNOWN | ❌ | 6887.7 | - |
| GRADE_PASS_005 | PASS | UNKNOWN | ❌ | 3640.6 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 2454.5 | - |
| GRADE_FAIL_004 | FAIL | UNKNOWN | ❌ | 6138.8 | - |
| GRADE_FAIL_005 | FAIL | UNKNOWN | ❌ | 17424.0 | - |

### qwen3:4b

**Correctness:** 0/10 (0.0%)
**Avg Latency:** 12242.8ms
**Qualified:** ❌ NO

| Test Case | Expected | Actual | Correct | Latency (ms) | Error |
|-----------|----------|--------|---------|--------------|-------|
| GRADE_FAIL_001 | FAIL | UNKNOWN | ❌ | 10721.2 | - |
| GRADE_FAIL_002 | FAIL | UNKNOWN | ❌ | 16990.9 | - |
| GRADE_PASS_001 | PASS | UNKNOWN | ❌ | 11246.4 | - |
| GRADE_PASS_002 | PASS | UNKNOWN | ❌ | 9719.5 | - |
| GRADE_PASS_003 | PASS | UNKNOWN | ❌ | 9861.3 | - |
| GRADE_PASS_004 | PASS | UNKNOWN | ❌ | 10048.4 | - |
| GRADE_PASS_005 | PASS | UNKNOWN | ❌ | 7650.1 | - |
| GRADE_FAIL_003 | FAIL | UNKNOWN | ❌ | 10024.0 | - |
| GRADE_FAIL_004 | FAIL | UNKNOWN | ❌ | 17171.5 | - |
| GRADE_FAIL_005 | FAIL | UNKNOWN | ❌ | 18994.7 | - |

---

## 📈 Summary Statistics

- **Total Models Tested:** 24
- **Qualified (100% correct):** 0
- **Disqualified:** 24
- **Test Cases:** 10
- **Pass Cases:** 5
- **Fail Cases:** 5

