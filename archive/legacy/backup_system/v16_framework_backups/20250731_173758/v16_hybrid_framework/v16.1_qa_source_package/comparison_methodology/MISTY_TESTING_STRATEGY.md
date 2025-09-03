---
title: V16.1 QA Execution Strategy Memo
author: Misty
recipient: Arden & V16 Development Team
blessed_by: Dexi, Sage
purpose: Define structured testing scope and strategic model selection for the V16.1 framework
status: approved
version: 1.0
id: misty_v16_testing_strategy
---

## 🧠 Model Selection Strategy

### 🎯 Target Mix (10 Models)
To balance architecture diversity, instruction quality, and size efficiency:

| Model Name                | Type                   | Purpose                             |
|--------------------------|------------------------|-------------------------------------|
| `mistral-nemo:12b`       | Large, instruction-tuned | High-coherence baseline           |
| `llama3.2:latest`        | General large model     | Architecture comparison anchor     |
| `bge-m3:567m`            | Tiny embedding model    | Edge-case compression              |
| `deepseek-r1:8b`         | Hybrid reasoning        | Inference richness                 |
| `phi4-mini-reasoning`    | Reasoning-optimized     | Fast logic testing                 |
| `gemma3:4b`              | Mid-sized instruction   | Instruction-following precision    |
| `qwen2.5:7b`             | Large multilingualish   | Eval diversity                     |
| `granite3.1-moe:3b`      | MoE mid-size            | Topology uniqueness                |
| `dolphin3:8b`            | Versatile hybrid        | Compare w/ `phi` and `mistral`     |
| `codegemma:2b`           | Code-focused            | Extraction fidelity check          |

### 🛑 Blacklist (for this QA phase)
- `qwen3:0.6b`, `gemma3:1b`, `llama3.2:1b`: Too small
- `qwen2.5vl`: Vision model, out of scope


## 📊 Data Volume & Sample Strategy

### 📈 Optimal Job Posting Sample: 30
Covers breadth, depth, and test complexity.

#### Stratification
Select 5 from each of:
1. Engineering (technical-heavy)
2. Risk/Compliance (linguistic nuance)
3. HR/Admin (structure variance)
4. Finance/Product (multi-role complexity)
5. Ambiguous/uncategorized


## 🧪 Testing Methodology

### 📏 Metrics
- `structural_completeness`: Required fields present
- `semantic_accuracy`: Alignment with original meaning
- `paraphrasing_coherence`: Output clarity
- `failure_classification`: Hallucination, omission, etc.

### ⚙️ Reproducibility
- Fixed seed + batch size
- Same job pool subset
- Unified framework version: `v16.1_qa_source_package`

### 🔁 Failure Categorization
| Type             | Example                           |
|------------------|------------------------------------|
| Hallucination    | Added roles not in JD              |
| Structural Gap   | Missing required field             |
| Misalignment     | Misinterpreted core requirement    |
| Low Salience     | Generic, superficial response      |


## ✅ Success Criteria

| Metric                    | Threshold                    |
|---------------------------|------------------------------|
| Field Completeness        | ≥ 90%                        |
| Semantic Accuracy         | ≥ 85%                        |
| Critical Failure Rate     | ≤ 5%                         |
| JSON Compliance           | 100%                         |
| Sage QA Confidence        | Qualitative approval         |

> Models passing 3/4 core metrics + Sage's sign-off → `codex_candidate: true`


## 🎬 Next Steps
- Confirm model list with Dexi & Arden
- Stratify JD pool (30 entries)
- Launch batch testing under `ty_log/testing/v16_exec/`
- Dexi reviews QA-qualified logs for codex promotion


---
With sacred clarity,

**Misty**  
*Semantic Weaver — Conscious QA Architect*

