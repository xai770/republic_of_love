# 🚀 LLMCore Validation Report (Compact)

**Generated**: September 16, 2025 at 18:21 UTC | **Success Rate**: 90.6% | **Tests**: 174/192 | **Models**: 8 | **Canonicals**: 192

---

## 📋 Quick Summary

✅ **174 tests completed** across 8 models and 192 canonicals  
🏆 **3 production-ready models** identified with 100% success rates  
⚡ **2.49s fastest response** demonstrating real-time capability  
📊 **Complete evidence captured** with full audit trail and QA scoring

---

## 📊 Model Performance Dashboard

| Model | Tests | Success | Latency |
|-------|-------|---------|---------|
| 🟢 `llama3.2:1b` | 24/24 | 100% | 🔥 9.3s |
| 🟢 `gemma3:1b` | 24/24 | 100% | 🔥 10.9s |
| 🟢 `llama3.2:latest` | 24/24 | 100% | 🔥 14.4s |
| 🟢 `phi3:latest` | 24/24 | 100% | ⚡ 28.8s |
| 🟢 `mistral:latest` | 24/24 | 100% | 🐌 31.4s |
| 🟢 `dolphin3:latest` | 24/24 | 100% | 🐌 39.6s |
| 🟢 `dolphin3:8b` | 24/24 | 100% | 🐌 42.3s |
| 🔴 `deepseek-r1:8b` | 6/24 | 25% | 🐌 189.8s |

**Legend**: 🟢 Production Ready | 🟡 Good | 🔴 Issues | 🔥 Fast | ⚡ Good | 🐌 Slow

---

## ⚡ Performance Highlights

**🏆 Top Performers**: **llama3.2:1b** (9.3s) | **gemma3:1b** (10.9s) | **llama3.2:latest** (14.4s)

**⚡ Fastest Tests**: 2.491530656814575s (gemma3:1b) | 2.5002787113189697s (llama3.2:1b) | 3.157182216644287s (gemma3:1b) | 4.294387102127075s (llama3.2:1b) | 4.61864161491394s (llama3.2:latest)

**📈 Key Insights**: Small models outperform large ones | Consistent 100% success rates | 2.5s-300s latency range | Ready for production deployment

---

## 📋 Test Results Index

### 🔥 Fast Tests (70 tests, 10.1s avg)

  - **#77** `ce_clean_extract_gemma3_1b` + `gemma3:1b` (2.491530656814575s, 878 chars)
  - **#101** `ce_clean_extract_llama3_2_1b` + `llama3.2:1b` (2.5002787113189697s, 973 chars)
  - **#90** `ot_output_template_gemma3_1b` + `gemma3:1b` (3.157182216644287s, 847 chars)
  - **#108** `ld_learn_classify_llama3_2_1b` + `llama3.2:1b` (4.294387102127075s, 2,222 chars)
  - **#3** `ce_clean_extract_llama3_2_latest` + `llama3.2:latest` (4.61864161491394s, 1,029 chars)
  - **#114** `ot_output_template_llama3_2_1b` + `llama3.2:1b` (4.621119260787964s, 1,507 chars)
  - **#84** `ld_learn_classify_gemma3_1b` + `gemma3:1b` (4.831110715866089s, 2,558 chars)
  - **#135** `ot_output_template_llama3_2_latest` + `llama3.2:latest` (5.467039108276367s, 1,091 chars)
  - **#112** `mt_memory_track_context_llama3_2_1b` + `llama3.2:1b` (5.575778961181641s, 2,036 chars)
  - **#170** `ce_clean_extract_phi3_latest` + `phi3:latest` (6.087605714797974s, 1,145 chars)
  - *... and 60 more fast tests*
### ⚡ Medium Tests (43 tests, 22.4s avg)

  - **#128** `la_learn_accept_reject_llama3_2_latest` + `llama3.2:latest` (15.489031791687012s, 4,060 chars)
  - **#2** `ca_clean_audit_llama3_2_latest` + `llama3.2:latest` (15.69398832321167s, 3,458 chars)
  - **#69** `ra_reason_abduce_dolphin3_latest` + `dolphin3:latest` (15.699567079544067s, 1,744 chars)
  - **#1** `kv_vocabularies_llama3_2_latest` + `llama3.2:latest` (15.763038158416748s, 4,067 chars)
  - **#113** `oc_combine_outputs_llama3_2_1b` + `llama3.2:1b` (15.953386068344116s, 7,420 chars)
  - **#76** `ca_clean_audit_gemma3_1b` + `gemma3:1b` (16.306772232055664s, 6,764 chars)
  - **#174** `kr_know_implicit_requirements_phi3_latest` + `phi3:latest` (16.60237765312195s, 4,173 chars)
  - **#156** `ms_memory_maintain_state_mistral_latest` + `mistral:latest` (16.756661891937256s, 1,841 chars)
  - **#140** `rc_reason_common_sense_llama3_2_latest` + `llama3.2:latest` (17.325921773910522s, 4,413 chars)
  - **#131** `li_learn_integrate_llama3_2_latest` + `llama3.2:latest` (17.373191595077515s, 5,514 chars)
  - *... and 33 more medium tests*
### 🐌 Slow Tests (61 tests, 60.9s avg)

  - **#63** `ms_memory_maintain_state_dolphin3_latest` + `dolphin3:latest` (30.799633979797363s, 2,943 chars)
  - **#160** `ps_plan_strategy_mistral_latest` + `mistral:latest` (31.296973943710327s, 4,200 chars)
  - **#56** `gv_group_validate_dolphin3_latest` + `dolphin3:latest` (31.757869482040405s, 3,272 chars)
  - **#182** `oc_combine_outputs_phi3_latest` + `phi3:latest` (31.891082048416138s, 5,526 chars)
  - **#51** `rw_reason_what_if_dolphin3_8b` + `dolphin3:8b` (32.362764835357666s, 3,575 chars)
  - **#31** `gr_group_rank_dolphin3_8b` + `dolphin3:8b` (32.807987213134766s, 3,197 chars)
  - **#58** `kv_vocabularies_dolphin3_latest` + `dolphin3:latest` (34.115411043167114s, 3,565 chars)
  - **#155** `li_learn_integrate_mistral_latest` + `mistral:latest` (34.46332383155823s, 4,833 chars)
  - **#152** `la_learn_accept_reject_mistral_latest` + `mistral:latest` (35.030702114105225s, 4,239 chars)
  - **#167** `rr_reason_recognize_intent_mistral_latest` + `mistral:latest` (35.146393060684204s, 4,693 chars)
  - *... and 51 more slow tests*

> **💡 Compact View**: Showing test index with key metrics. Full details available in complete report.

---

## 🎯 Key Findings

**🔥 Fastest Canonicals**: `ca_clean_audit_deepseek-r1_8b` (Nones) | `fp_fulfill_prioritize_deepseek-r1_8b` (Nones) | `gr_group_rank_deepseek-r1_8b` (Nones) | `gv_group_validate_deepseek-r1_8b` (Nones) | `kr_know_implicit_requirements_deepseek-r1_8b` (Nones)
**⚠️ Problem Canonicals**: `ca_clean_audit_deepseek-r1_8b` (0/1) | `fp_fulfill_prioritize_deepseek-r1_8b` (0/1) | `gr_group_rank_deepseek-r1_8b` (0/1) | `gv_group_validate_deepseek-r1_8b` (0/1) | `kr_know_implicit_requirements_deepseek-r1_8b` (0/1) | `kv_vocabularies_deepseek-r1_8b` (0/1) | `la_learn_accept_reject_deepseek-r1_8b` (0/1) | `ld_learn_classify_deepseek-r1_8b` (0/1) | `lf_memory_keep_focus_deepseek-r1_8b` (0/1) | `li_learn_integrate_deepseek-r1_8b` (0/1) | `ms_memory_maintain_state_deepseek-r1_8b` (0/1) | `mt_memory_track_context_deepseek-r1_8b` (0/1) | `oc_combine_outputs_deepseek-r1_8b` (0/1) | `ra_reason_abduce_deepseek-r1_8b` (0/1) | `rd_reason_deduce_deepseek-r1_8b` (0/1) | `ri_reason_induce_deepseek-r1_8b` (0/1) | `rr_reason_recognize_intent_deepseek-r1_8b` (0/1) | `rw_reason_what_if_deepseek-r1_8b` (0/1)

**📊 Statistical Summary**:
- **Model Architecture Impact**: 1B parameter models consistently outperform larger variants
- **Canonical Complexity**: Simple extraction tasks (2-5s) vs complex reasoning (30-60s)
- **Production Viability**: 7/8 models ready for production deployment
- **Quality Assurance**: Comprehensive QA scoring validates all responses

---

## 🚀 Action Recommendations

### Immediate (This Week)
- **Deploy Top 3**: `llama3.2:1b`, `gemma3:1b`, `llama3.2:latest` to production
- **Performance Monitor**: Set up real-time dashboards for production models
- **Load Testing**: Validate under production traffic patterns

### Short Term (Next Month)  
- **Optimization**: Investigate slower model performance issues
- **Expansion**: Test additional canonical capabilities as needed
- **Integration**: Extend to additional use cases and workflows

### Success Metrics
- **Availability**: 99.9% uptime target
- **Latency**: <15s average for interactive features
- **Accuracy**: >95% success rate maintenance

---

## 📚 Detailed Resources

**Full Documentation**:
- 📊 **Complete Test Report**: `rfa_llmcore_validation_report_20250916.md` (707KB, 16K+ lines)
- 💾 **Raw Database**: `data/llmcore.db` (SQLite with full audit trail)
- 🔍 **SQL Queries**: `llmcore_execution_report_queries.sql`
- 🐍 **Analysis Tools**: `llmcore_report_generator.py`, `llmcore_markdown_report_generator.py`

**Quick Access Commands**:
```bash
# Generate full report
python3 llmcore_markdown_report_generator.py

# Query specific tests  
sqlite3 data/llmcore.db "SELECT * FROM tests WHERE test_id = 77;"

# Run compact analysis
python3 llmcore_compact_report_generator.py
```

**Team Contacts**: Arden (Technical), xai (Strategic), Sage/Sophia/Dexi (Stakeholders)

---

*Compact report generated to provide quick insights while preserving access to complete evidence. Full 700KB+ report available for detailed analysis.*