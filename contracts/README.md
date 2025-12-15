# Workflow Contracts System

**Location**: `/contracts/`  
**Purpose**: Type-safe data contracts for workflow inputs/outputs and API responses  
**Philosophy**: Code is single source of truth → generates database registry + documentation  

---

## 📋 What Are Contracts?

Contracts are **Python dataclasses** that define the shape of data flowing through Turing workflows. They provide:

1. ✅ **Type Safety**: IDE autocomplete, mypy validation, fewer runtime errors
2. ✅ **Documentation**: Explicit schemas in code AND queryable from database
3. ✅ **Validation**: JSON Schema enforcement at runtime (coming soon)
4. ✅ **Single Source of Truth**: Write Python once, sync to DB automatically

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    contracts/__init__.py                     │
│  - Python dataclasses with @dataclass decorator             │
│  - @register_workflow_contract decorator adds to registry   │
│  - Auto-generates JSON Schema from Python type hints        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
           ┌───────────────────────────────┐
           │  tools/sync_contracts_to_db.py │
           │  - Reads global registry      │
           │  - Syncs to workflow_variables│
           │  - Version management         │
           └───────────────┬───────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │  workflow_variables table  │
              │  - variable_name           │
              │  - workflow_id             │
              │  - scope (input/output)    │
              │  - json_schema (JSONB)     │
              │  - version tracking        │
              └────────────────────────────┘
```

---

## 📝 How to Create a Contract

### Step 1: Define Dataclass Contract

```python
from dataclasses import dataclass
from typing import List, Dict, Any
from contracts import register_workflow_contract, WorkflowContract

@register_workflow_contract(workflow_id=1234, workflow_name="My Workflow")
class MyWorkflowContract(WorkflowContract):
    """
    Contract for My Workflow
    
    Input: user_id
    Output: results, user_id (passed through)
    """
    
    @dataclass
    class Input:
        user_id: int  # Required integer
        max_results: int = 10  # Optional with default
    
    @dataclass
    class Output:
        results: List[Dict[str, Any]]  # Array of objects
        user_id: int  # Pass-through for reference
```

### Step 2: Sync to Database

```bash
# Activate venv (REQUIRED!)
source venv/bin/activate

# Dry-run first (see what would change)
python tools/sync_contracts_to_db.py --dry-run

# Actually sync
python tools/sync_contracts_to_db.py
```

### Step 3: Use in Code

```python
from contracts import MyWorkflowContract

# Type hints help IDE understand the data shape
def run_workflow(input_data: MyWorkflowContract.Input) -> MyWorkflowContract.Output:
    # IDE knows input_data.user_id exists and is an int!
    results = fetch_data(input_data.user_id)
    
    # IDE helps you build correct output
    return MyWorkflowContract.Output(
        results=results,
        user_id=input_data.user_id  # Pass through
    )
```

---

## 🗂️ Registered Contracts

### Workflow 1121: Job Skills Extraction ✅
- **Input**: `posting_id: int`
- **Output**: `skills: List[Dict]`, `posting_id: int`
- **File**: `contracts/__init__.py` → `JobSkillsExtractionContract`
- **Status**: Active, validation enabled

### Workflow 2002: Profile Skills Extraction ✅
- **Input**: `profile_id: int`
- **Output**: `skills: List[Dict]`, `profile_id: int`
- **File**: `contracts/__init__.py` → `ProfileSkillsExtractionContract`
- **Status**: Active, validation enabled

### Workflow 1122: Profile Skill Extraction (Legacy) ✅
- **Input**: `profile_id: int`
- **Output**: `skills: List[Dict]`, `profile_id: int`
- **File**: `contracts/__init__.py` → `ProfileSkillExtractionLegacyContract`
- **Status**: Active, validation enabled

### Workflow 1126: Profile Document Import ✅
- **Input**: `document_text: str`
- **Output**: `profile_id: int`
- **File**: `contracts/__init__.py` → `ProfileDocumentImportContract`
- **Status**: Active, validation enabled
- **Flow**: 4-conversation workflow (Extract → Validate → Import → Error)

### Deutsche Bank Job Fetcher (Internal)
- **Data Class**: `DeutscheBankJobFlattened`
- **Purpose**: Type-safe API response with `ApplyURI` at TOP level (not nested)
- **Usage**: `core/turing_job_fetcher.py` → `_fetch_from_api()` return type
- **Why**: Prevents bugs like looking for ApplyURI in wrong location after flattening

---

**Coverage**: 4 workflows registered (the most frequently used ones!)  
**Next targets**: 1114 (Self Healing Dual Grader), 1124 (Fake Job Detector), 1125 (Profile Career Deep Analysis)

---

## 🔍 Querying Contracts from Database

### Get all variables for a workflow:
```sql
SELECT variable_name, scope, data_type, is_required, description
FROM workflow_variables
WHERE workflow_id = 1121 AND is_current = true
ORDER BY scope, variable_name;
```

### Get workflow contract (input + output as JSON):
```sql
SELECT get_workflow_contract(1121);
-- Returns: (input_vars_json, output_vars_json)
```

### Find workflows using a specific variable:
```sql
SELECT DISTINCT workflow_id, variable_name, scope
FROM workflow_variables
WHERE variable_name ILIKE '%skill%' AND is_current = true;
```

### See contract history (versions):
```sql
SELECT variable_name, scope, version, is_current, created_at
FROM workflow_variables
WHERE workflow_id = 1121
ORDER BY variable_name, version DESC;
```

---

## 🔄 Type Conversion (Python → JSON Schema)

| Python Type | JSON Schema |
|-------------|-------------|
| `int` | `{"type": "integer"}` |
| `str` | `{"type": "string"}` |
| `bool` | `{"type": "boolean"}` |
| `float` | `{"type": "number"}` |
| `List[str]` | `{"type": "array", "items": {"type": "string"}}` |
| `List[Dict]` | `{"type": "array", "items": {"type": "object"}}` |
| `Dict[str, Any]` | `{"type": "object"}` |
| `Optional[int]` | `{"type": ["integer", "null"]}` |

**Defaults**: If dataclass field has `= value`, then `is_required = false` in DB

---

## 🚀 Validation ✅ ACTIVE (Nov 6, 2025)

Validation is **automatically enabled** in `WorkflowExecutor`! No code changes needed.

### How It Works

```python
from core.workflow_executor import WorkflowExecutor

# Initialize with validation enabled (default)
executor = WorkflowExecutor(enable_validation=True)

# Execute workflow - validation happens automatically!
result = executor.execute_workflow(
    workflow_id=1121,
    initial_variables={'posting_id': 42},  # ← Validated before execution
    dry_run=False
)
# Output validated after LLM response ↑
```

### What Gets Validated

**Input Validation** (before workflow starts):
- ✅ All required fields present
- ✅ Field types match contract (int, str, list, dict)
- ❌ Fails fast if validation fails (no LLM call made)

**Output Validation** (after workflow completes):
- ✅ All required output fields present
- ✅ Field types match contract
- ⚠️  Warns if validation fails (doesn't block workflow)

### Smart Output Wrapping

If LLM returns array `[{skill1}, {skill2}]` but contract expects `{skills: [...], posting_id: int}`:
- ✅ Automatically wraps as `{skills: [...]}`
- ✅ Adds pass-through fields from input (`posting_id`)
- ✅ Validation passes!

### Example Validation Errors

**Missing Field:**
```
❌ Input validation failed:
  • Missing required field: posting_id
```

**Wrong Type:**
```
❌ Input validation failed:
  • Field posting_id: expected <class 'int'>, got <class 'str'>
```

**Manual Validation** (advanced use cases):
```python
from contracts import JobSkillsExtractionContract

contract = JobSkillsExtractionContract()

# Validate input manually
valid, errors = contract.validate_input({'posting_id': 'invalid'})
if not valid:
    print(f"Errors: {errors}")
    # Output: ["Field posting_id: expected <class 'int'>, got <class 'str'>"]

# Validate output manually
valid, errors = contract.validate_output({'skills': [], 'posting_id': 42})
print(f"Valid: {valid}")  # True
```

---

## 🐛 Common Issues

### Issue: "NameError: name 'psycopg2' is not defined"
**Fix**: Import added to `tools/sync_contracts_to_db.py` (Nov 6, 2025)

### Issue: "duplicate key value violates unique constraint"  
**Fix**: Migration 058 added `scope` to UNIQUE constraint (Nov 6, 2025)  
**Why**: Same variable name (e.g., `posting_id`) can be input AND output

### Issue: Contract changes not reflected in database
**Fix**: Run `python tools/sync_contracts_to_db.py` after editing contracts

### Issue: IDE doesn't recognize dataclass fields
**Fix**: Make sure you imported the contract class AND used type hints:
```python
from contracts import DeutscheBankJobFlattened
jobs: List[DeutscheBankJobFlattened] = fetch_jobs()  # Type hint!
```

---

## 📚 Related Files

- **Contracts Definition**: `contracts/__init__.py` (300+ lines)
- **Sync Tool**: `tools/sync_contracts_to_db.py` (160+ lines)  
- **Database Table**: `migrations/057_add_workflow_variables_registry.sql`
- **Constraint Fix**: `migrations/058_fix_workflow_variables_unique_constraint.sql`
- **Cheat Sheet**: `docs/___ARDEN_CHEAT_SHEET.md` (secret number: 635864)

---

## 🎯 Next Steps

1. ✅ **DONE**: Create contract system, sync 2 workflows
2. ✅ **DONE**: Update `turing_job_fetcher.py` to use `DeutscheBankJobFlattened`
3. ⏳ **TODO**: Add validation calls in workflow runners
4. ⏳ **TODO**: Add contracts for remaining workflows (1126, 1127, 1114, 1124)
5. ⏳ **TODO**: Document pattern in `WORKFLOW_CREATION_COOKBOOK.md`
6. ⏳ **TODO**: Enable mypy type checking in CI/CD

---

## 💡 Design Decisions

**Q: Why not just use JSON Schema files?**  
A: Python dataclasses provide IDE support, type checking with mypy, and are easier to version control. JSON Schema is auto-generated as a byproduct.

**Q: Why version contracts?**  
A: Allows backward compatibility when contracts evolve. Old workflow runs can reference old contract versions.

**Q: Why store in database if code is source of truth?**  
A: Enables runtime queries like "which workflows need variable X?" and supports future ExecAgent work where AI needs to discover available workflows.

**Q: What if I forget to sync after editing?**  
A: Consider adding pre-commit hook or CI check to detect drift between code and DB.

---

**Last Updated**: November 6, 2025  
**Authors**: Arden & xai  
**Status**: ✅ System deployed, 2 workflows + 1 data class registered
