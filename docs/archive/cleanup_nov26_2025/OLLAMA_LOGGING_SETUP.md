# Ollama Logging Configuration - Quick Reference
**Date:** November 19, 2025  
**Status:** ✅ Enabled and Active

---

## Configuration Applied

**File:** `~/.ollama/config.yaml`

```yaml
log: true
log-requests: true
log-responses: true
```

**Service Status:** Running as `ollama.service` (systemd)

---

## Viewing Logs

### Real-time monitoring (tail mode)
```bash
# Follow all Ollama logs
journalctl -u ollama -f

# Follow with timestamps
journalctl -u ollama -f --since "1 minute ago"
```

### View recent logs
```bash
# Last 100 lines
journalctl -u ollama -n 100 --no-pager

# Last hour
journalctl -u ollama --since "1 hour ago" --no-pager

# Last 10 minutes
journalctl -u ollama --since "10 minutes ago" --no-pager
```

### Search logs for specific patterns
```bash
# Find all API requests
journalctl -u ollama | grep "POST"

# Find model loading events
journalctl -u ollama | grep "loading model"

# Find GPU memory usage
journalctl -u ollama | grep "gpu memory"

# Find errors
journalctl -u ollama | grep "level=ERROR"
```

### Export logs to file
```bash
# Export today's logs
journalctl -u ollama --since today > ollama_logs_$(date +%Y%m%d).log

# Export last hour
journalctl -u ollama --since "1 hour ago" > ollama_debug.log
```

---

## What You'll See Now

### 1. HTTP Request Logs (GIN framework)
```
[GIN] 2025/11/19 - 12:12:02 | 200 |  2.040907755s | 127.0.0.1 | POST "/api/generate"
[GIN] 2025/11/19 - 12:12:02 | 200 |    27.137µs | 127.0.0.1 | HEAD "/"
[GIN] 2025/11/19 - 12:12:02 | 200 | 101.577193ms | 127.0.0.1 | POST "/api/show"
```

### 2. Model Loading Details
```
level=INFO source=server.go:653 msg="loading model" "model layers"=27
level=INFO source=ggml.go:494 msg="offloaded 27/27 layers to GPU"
level=INFO source=device.go:212 msg="model weights" device=CUDA0 size="762.5 MiB"
```

### 3. GPU Memory Allocation
```
level=INFO source=server.go:665 msg="gpu memory" id=GPU-ed529af1-8d3d-581f-81f1-178ec71b0054 
  library=CUDA available="5.2 GiB" free="5.7 GiB"
```

### 4. Performance Metrics
```
level=INFO source=device.go:223 msg="kv cache" device=CUDA0 size="38.0 MiB"
level=INFO source=device.go:234 msg="compute graph" device=CUDA0 size="80.0 MiB"
level=INFO source=device.go:244 msg="total memory" size="1.2 GiB"
```

---

## Advanced Logging Options

### Enable DEBUG level (very verbose)
Edit `~/.ollama/config.yaml`:
```yaml
log: true
log-requests: true
log-responses: true
log-level: debug  # ← Add this for detailed debugging
```

Then restart: `sudo systemctl restart ollama`

### Save logs to custom file
Edit `~/.ollama/config.yaml`:
```yaml
log: true
log-requests: true
log-responses: true
log-file: /home/xai/.ollama/ollama.log  # ← Custom log file
```

**Note:** When using `log-file`, logs write to BOTH systemd journal AND the file.

---

## Integration with Workflow Debugging

### Track model switches in your workflow
```bash
# Monitor when models load/unload
journalctl -u ollama -f | grep -E "(loading model|offloaded.*layers)"
```

### Measure API latency
```bash
# See actual request times
journalctl -u ollama --since "1 hour ago" | grep "POST.*api/generate" | \
  awk '{print $(NF-3)}' | sort -n
```

### Debug GPU sawtooth pattern
```bash
# Watch GPU memory changes in real-time
watch -n 1 'journalctl -u ollama -n 5 | grep "gpu memory"'
```

---

## Troubleshooting

### Logs not showing up?
```bash
# 1. Verify config is loaded
cat ~/.ollama/config.yaml

# 2. Restart Ollama
sudo systemctl restart ollama

# 3. Check service status
systemctl status ollama

# 4. View startup logs
journalctl -u ollama --since "5 minutes ago"
```

### Too much logging? Reduce verbosity
Edit `~/.ollama/config.yaml`:
```yaml
log: true
log-requests: false   # ← Disable HTTP request logs
log-responses: false  # ← Disable response logs
```

### Clean up old logs
```bash
# Clear logs older than 7 days
sudo journalctl --vacuum-time=7d

# Limit journal size to 500MB
sudo journalctl --vacuum-size=500M
```

---

## Quick Commands Cheat Sheet

```bash
# Real-time monitoring
journalctl -u ollama -f

# Last 50 lines
journalctl -u ollama -n 50

# Search for errors
journalctl -u ollama | grep ERROR

# Export today's logs
journalctl -u ollama --since today > ollama_$(date +%Y%m%d).log

# Restart Ollama
sudo systemctl restart ollama

# Check config
cat ~/.ollama/config.yaml
```

---

## Next Steps

1. **Monitor one workflow run** to see logging in action
2. **Correlate Ollama logs** with your workflow_executor logs
3. **Track GPU usage** during model-first batching
4. **Validate model switching** happens at expected times

---

**Status:** Logging configured and validated ✅  
**Config file:** `~/.ollama/config.yaml`  
**Service:** `ollama.service` (active)  
**Log viewer:** `journalctl -u ollama -f`
