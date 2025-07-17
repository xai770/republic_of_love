# 🚀 QUICK START REFERENCE CARD
## For: New AI Agent (Republic of Love Project)
## Critical Commands & Patterns for Day 1

---

## ⚡ INSTANT SETUP (5 Minutes)

```bash
# Navigate to project
cd /home/xai/Documents/llm_factory

# Install dependencies 
pip install -r requirements.txt

# Test everything works
python customer_demo.py

# Verify Ollama is running with llama3.2
curl http://localhost:11434/api/tags
```

---

## 🎯 CREATE YOUR FIRST SPECIALIST (30 Minutes)

### Step 1: Clone Proven Structure
```bash
# Copy the best template
cp -r llm_factory/modules/quality_validation/specialists_versioned/job_match_scoring_engine/v1_0 \
      llm_factory/modules/quality_validation/specialists_versioned/relationship_compatibility/v1_0

cd llm_factory/modules/quality_validation/specialists_versioned/relationship_compatibility/v1_0
```

### Step 2: Basic Adaptation
```python
# Edit src/relationship_compatibility_specialist.py
class RelationshipCompatibilitySpecialist(LLMModule):
    def __init__(self):
        super().__init__()
        self.module_name = "relationship_compatibility"
        self.version = "v1_0"
    
    def _build_prompt(self, person_a_profile: str, person_b_profile: str) -> str:
        return f"""
        Analyze the compatibility between these two people for a romantic relationship.
        
        Person A Profile: {person_a_profile}
        Person B Profile: {person_b_profile}
        
        Provide a JSON response with:
        {{
            "compatibility_score": <0-100 integer>,
            "strengths": ["strength1", "strength2", ...],
            "potential_challenges": ["challenge1", "challenge2", ...],
            "advice": "specific relationship advice"
        }}
        """
```

### Step 3: Add to Demo System
```python
# Edit customer_demo.py - add to AVAILABLE_SPECIALISTS:
"relationship_compatibility": {
    "class": RelationshipCompatibilitySpecialist,
    "description": "Analyzes romantic compatibility between two people"
}
```

---

## 📋 ESSENTIAL CODE PATTERNS

### LLM Integration (Copy-Paste Ready)
```python
def _call_llm(self, prompt: str) -> str:
    try:
        response = self.ollama_client.generate(
            model="llama3.2",
            prompt=prompt,
            stream=False
        )
        return response if isinstance(response, str) else response.get('response', '')
    except Exception as e:
        self.logger.error(f"LLM call failed: {e}")
        raise
```

### JSON Response Parsing (Battle-Tested)
```python
def _parse_response(self, response: str) -> dict:
    try:
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        raise ValueError("No valid JSON in response")
    except Exception as e:
        # Fallback for partial responses
        return {"error": "parsing_failed", "raw_response": response}
```

### Error Handling (Production Ready)
```python
def process(self, module_input: ModuleInput) -> ModuleResult:
    try:
        # Your processing logic here
        result = self._do_processing(module_input)
        
        return ModuleResult(
            success=True,
            data=result,
            metadata={"specialist": self.module_name, "version": self.version}
        )
    except Exception as e:
        self.logger.error(f"Processing failed: {e}")
        return ModuleResult(
            success=False,
            error=str(e),
            metadata={"specialist": self.module_name, "error_type": type(e).__name__}
        )
```

---

## 🧪 TESTING COMMANDS

```bash
# Test your specialist
python -c "
from llm_factory.modules.quality_validation.specialists_versioned.relationship_compatibility.v1_0.src.relationship_compatibility_specialist import RelationshipCompatibilitySpecialist
specialist = RelationshipCompatibilitySpecialist()
result = specialist.process({'text': 'test data'})
print(result)
"

# Run all tests
python -m pytest llm_factory/tests/

# Type checking
mypy llm_factory/

# Full demo with your specialist
python customer_demo.py
```

---

## 📂 CRITICAL FILE LOCATIONS

```
llm_factory/
├── customer_demo.py                    # 🎯 Main demo - add your specialists here
├── llm_factory/core/
│   ├── types.py                       # 📋 Data types - ModuleInput, ModuleResult
│   └── module_base.py                 # 🏗️ Base class - inherit from LLMModule
└── llm_factory/modules/quality_validation/specialists_versioned/
    ├── job_match_scoring_engine/v1_0/  # 📖 Best template to copy
    ├── skill_requirement_analyzer/v1_0/ # 📖 Alternative template
    └── [your_specialist]/v1_0/         # 🎯 Your new specialist goes here
```

---

## 🎯 SUCCESS METRICS

**Your specialist is ready when:**
- ✅ Returns valid JSON responses
- ✅ Handles errors gracefully  
- ✅ Integrates with customer_demo.py
- ✅ Passes basic tests
- ✅ Response time < 30 seconds

---

## 🆘 EMERGENCY CONTACTS

**Technical Issues:**
- Check existing specialists for patterns
- Review error logs in terminal output
- Validate Ollama is running: `curl http://localhost:11434/api/tags`

**Architecture Questions:**
- Study `llm_factory/core/module_base.py`
- Reference any working specialist in `specialists_versioned/`
- Check the comprehensive technical brief in `0_mailboxes/new_ai_agent/`

---

## 🚀 CONFIDENCE BOOST

**Remember:** Every pattern you need is already implemented and working. You're not building from scratch - you're adapting proven solutions for the love domain.

**Your first specialist will work because:**
- The LLM integration is bulletproof
- The error handling is comprehensive  
- The patterns are battle-tested
- The framework handles the complexity

**Just focus on:** Your prompts, your parsing logic, and your domain expertise.

---

**You've got this! Build something beautiful! 💝**
