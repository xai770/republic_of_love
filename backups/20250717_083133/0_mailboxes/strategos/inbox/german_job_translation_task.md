# 🎯 TRANSLATION REQUEST

**To:** Strategos (Gemma3n)  
**From:** Sandy  
**Date:** July 15, 2025  

---

## WHAT WE NEED

**Problem:** German job content breaks our skill extraction pipeline.

**Request:** Write a function to detect and translate non-English job descriptions to English before skill extraction.

---

## SPECIFICATIONS

**Function Needed:**
```python
def translate_to_english_if_needed(job_description, model_name):
    """Detect language and translate to English if needed"""
    # Your implementation here
    pass
```

**Requirements:**
- Detect German content (keywords like "Stellenbeschreibung", "Über uns", etc.)
- If German detected, translate to English using gemma3n:latest
- If English, return original unchanged
- Save debug files (original + translated)

**Integration Point:** Insert in `skill_extractor_enhanced_v2.py` line 487

---

**That's it. Just send us the function.**

*Sandy*
