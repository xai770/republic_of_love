# Base Interrogator Class

**File:** `base.py`  
**Purpose:** Abstract base class providing common functionality for all job source interrogators

---

## Overview

The `JobSourceInterrogator` base class provides:
- Finding recording with severity levels
- Automatic timestamping
- Live feedback printing
- Report generation and grouping
- JSON export functionality
- Summary statistics

All source-specific interrogators inherit from this class.

---

## Class Structure

```python
class JobSourceInterrogator(ABC):
    def __init__(self, source_name: str)
    def add_finding(category, message, severity)
    def report()
    def generate_summary() -> Dict
    def export_report(output_file: str)
    
    @abstractmethod
    def generate_recommendations() -> List[str]
    
    @abstractmethod
    def run_full_interrogation()
```

---

## Usage Example

```python
from interrogators.base import JobSourceInterrogator

class MySourceInterrogator(JobSourceInterrogator):
    def __init__(self):
        super().__init__("My Job Board")
    
    def test_api(self):
        self.add_finding("API", "Testing endpoint...", "INFO")
        # ... do test ...
        self.add_finding("API", "✅ Endpoint works!", "SUCCESS")
    
    def generate_recommendations(self) -> List[str]:
        return [
            "Use pagination with limit=100",
            "Rate limit to 5 req/s"
        ]
    
    def run_full_interrogation(self):
        print(f"🔍 Interrogating {self.source_name}")
        self.test_api()
        self.report()

# Run it
interrogator = MySourceInterrogator()
interrogator.run_full_interrogation()
interrogator.export_report("findings.json")
```

---

## Finding Severity Levels

| Severity | Icon | Use Case | Example |
|----------|------|----------|---------|
| `INFO` | ℹ️ | Informational message | "Testing API endpoint..." |
| `SUCCESS` | ✅ | Successful test/discovery | "Found 2000 jobs" |
| `WARNING` | ⚠️ | Potential issue | "Rate limit detected at 100 req/min" |
| `ERROR` | ❌ | Failure or blocker | "403 Forbidden - Auth required" |

---

## Output Format

### Console Output (Live)
```
ℹ️ [API Limits] Testing maximum fetch size...
✅ [API Limits] CountItem=2000 → returned 2000 jobs
⚠️ [Rate Limits] Hit rate limit after 50 requests
```

### Report Format (End of Run)
```
======================================================================
📊 INTERROGATION REPORT
======================================================================

API Limits:
  • Testing maximum fetch size...
  • CountItem=2000 → returned 2000 jobs

Rate Limits:
  • Hit rate limit after 50 requests
```

### JSON Export
```json
{
  "summary": {
    "source": "My Job Board",
    "timestamp": "2025-11-07T14:30:00",
    "duration_seconds": 45.2,
    "total_findings": 15,
    "errors": 0,
    "warnings": 2,
    "successes": 10,
    "info": 3
  },
  "findings": [
    {
      "category": "API Limits",
      "message": "CountItem=2000 → returned 2000 jobs",
      "severity": "SUCCESS",
      "timestamp": "2025-11-07T14:30:15"
    }
  ],
  "recommendations": [
    "Use pagination with limit=100",
    "Rate limit to 5 req/s"
  ]
}
```

---

## Integration Points

### With Import Scripts
```python
# Import script can read findings
with open('findings.json') as f:
    findings = json.load(f)
    
# Extract recommendations
max_count = extract_max_count(findings)
rate_limit = extract_rate_limit(findings)

# Use in import logic
fetch_jobs(count=max_count, rate_limit=rate_limit)
```

### With Monitoring Systems
```python
# Check for errors
if findings['summary']['errors'] > 0:
    alert("Job board interrogation failed!")

# Track warnings over time
track_metric("warnings", findings['summary']['warnings'])
```

---

## Best Practices

1. **Category Naming**: Use consistent categories across interrogators
   - "API Limits"
   - "Geography"
   - "Data Structure"
   - "Rate Limits"
   - "Performance"
   - "Authentication"

2. **Message Format**: Be descriptive and actionable
   - ✅ "CountItem=2000 → returned 2000 jobs (total available: 2202)"
   - ❌ "Got jobs"

3. **Severity Usage**:
   - ERROR: Blocks import script execution
   - WARNING: Requires attention but not blocking
   - SUCCESS: Confirms working feature
   - INFO: Neutral observation

4. **Timestamps**: Automatically added, use for performance analysis

---

## Extension Points

Subclasses must implement:

### 1. `generate_recommendations()`
```python
def generate_recommendations(self) -> List[str]:
    """Return list of actionable recommendations"""
    recs = []
    
    # Analyze findings and generate recommendations
    if self.has_error("API Limits"):
        recs.append("Fix API access before proceeding")
    
    if self.has_warning("Rate Limits"):
        recs.append("Implement rate limiting in import script")
    
    return recs
```

### 2. `run_full_interrogation()`
```python
def run_full_interrogation(self):
    """Run all tests in logical order"""
    print(f"🔍 {self.source_name} Interrogation")
    
    self.test_authentication()
    self.test_api_limits()
    self.analyze_data_structure()
    self.benchmark_performance()
    
    self.report()
```

---

## Helper Methods (Add to Subclass)

```python
def has_error(self, category: str) -> bool:
    """Check if any errors in category"""
    return any(
        f['category'] == category and f['severity'] == 'ERROR'
        for f in self.findings
    )

def get_findings_by_category(self, category: str) -> List[Dict]:
    """Get all findings for a category"""
    return [f for f in self.findings if f['category'] == category]

def count_severity(self, severity: str) -> int:
    """Count findings by severity"""
    return len([f for f in self.findings if f['severity'] == severity])
```

---

## Testing

```python
def test_base_interrogator():
    """Test base class functionality"""
    
    class TestInterrogator(JobSourceInterrogator):
        def generate_recommendations(self):
            return ["Test recommendation"]
        
        def run_full_interrogation(self):
            self.add_finding("Test", "Test message", "INFO")
    
    interrogator = TestInterrogator("Test Source")
    interrogator.run_full_interrogation()
    
    assert len(interrogator.findings) == 1
    assert interrogator.findings[0]['category'] == "Test"
    
    summary = interrogator.generate_summary()
    assert summary['total_findings'] == 1
    assert summary['source'] == "Test Source"
```

---

## Common Issues

**Q: Findings not showing in report?**
A: Check that you're calling `self.add_finding()` not `print()`

**Q: Export fails with encoding error?**
A: Ensure `ensure_ascii=False` in `json.dump()` for non-ASCII characters

**Q: Report grouping incorrect?**
A: Use consistent category names (case-sensitive!)

---

## See Also

- [deutsche_bank.py](README_deutsche_bank.md) - Example implementation
- [generic.py](README_generic.md) - Generic job board interrogator
- [DATA_MOBILIZATION_COOKBOOK.md](../docs/DATA_MOBILIZATION_COOKBOOK.md) - Usage patterns
