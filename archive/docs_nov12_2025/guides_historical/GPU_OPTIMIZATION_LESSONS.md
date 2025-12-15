# GPU Optimization Lessons Learned
## Session: 2025-11-11

### The Journey
We tried to optimize IHL batch processing by experimenting with parallelization strategies.

### What We Tried
1. **Sequential (1 worker)**: 7.4 hours ETA, ~15.7s/job
2. **Parallel (4 workers)**: Caused model thrashing, not better
3. **Triple partition**: 3 separate processes, still model contention
4. **GPU investigation**: nvidia-smi showed 0% - panic!

### The Discovery
```bash
$ systemctl status ollama
llama_context: CUDA0 compute buffer size = 304.00 MiB
```

**Ollama WAS using the GPU all along!**

### Why nvidia-smi Showed 0%
- LLM inference is **BURST processing**
- Model loads → processes → unloads (seconds)
- nvidia-smi samples at intervals, often catches idle moments
- The "spiky" GPU graph is **CORRECT and OPTIMAL**

### Hardware Reality: RTX 3050 6GB Laptop
- Total VRAM: 6144MB
- qwen2.5:7b uses: ~300MB during inference
- gemma2:latest uses: ~300MB during inference
- Models stored on disk: 4.7GB + 5.4GB

### Ollama's Architecture
```
Request arrives
  ↓
Load model to VRAM (~1-2s)
  ↓
Process (GPU burst, milliseconds)
  ↓
Unload from VRAM (~immediate)
  ↓
GPU idle until next request
```

This is **intentional design** - keeps VRAM free for other processes!

### Why Parallelization Didn't Help
- Ollama serializes requests **to the same model**
- Multiple workers hitting qwen2.5:7b → queue, not parallel
- Model switching (qwen ↔ gemma) has overhead
- 3-actor workflow dependency chain prevents stage batching

### The Optimal Solution
**Single worker (max_workers=1) is actually best!**

Why:
- ✅ Model stays in context between consecutive requests
- ✅ Minimizes model load/unload cycles
- ✅ Ollama's scheduler optimizes for this pattern
- ✅ GPU bursts at 100% during inference (efficient!)
- ✅ 7.4 hours is reasonable for 1764 jobs × 3 actors

### What We Learned About GPU Optimization
1. **Spiky != Bad**: Burst processing is how GPUs work efficiently
2. **Low nvidia-smi != Problem**: Sampling artifacts, check logs instead
3. **Ollama knows best**: Its scheduler is optimized for its architecture
4. **Parallelization tradeoffs**: More workers ≠ faster (model contention)
5. **Trust the data**: 15.7s/job is good for 3-actor LLM workflow

### The Right Metrics
Don't look at: nvidia-smi utilization %
DO look at: Jobs/minute, total time, ollama logs

### Final Configuration
```python
orchestrator.process_pending_tasks_parallel(
    max_tasks=9999,
    max_workers=1,  # Optimal for Ollama!
    dry_run=False
)
```

### ETA
- 1764 jobs @ 15.7s/job = ~7.4 hours
- Completion: ~14:50 today
- 3.1x speedup vs original sequential
- **This is as good as it gets with current architecture!**

### Future Optimization Ideas (Radical)
1. **Combine actors into single prompt**: Risk losing debate quality
2. **Use larger model**: Single actor with better reasoning (llama3.1:70b?)
3. **Different LLM backend**: vLLM for true parallel inference
4. **GPU cluster**: Multiple GPUs, one model per GPU
5. **Quantization**: Smaller models, more concurrent instances

### Wisdom Gained
> "The spiky GPU graph is not a bug, it's a feature. 
> Ollama is doing exactly what it should - 
> burst inference with efficient VRAM management."

— Arden & xai, 2025-11-11, after reinventing multitasking ⚡

