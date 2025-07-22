# ty_extract V11.0 - Template-Based Extraction

**Version**: V11.0  
**Base**: V7.1 template-based architecture  
**LLM**: qwen3:latest (validation winner)  
**Prompt**: 2025-07-20 template (proven format)  

## Key Improvements from V10.0

1. **Correct Prompt**: Uses the exact 2025-07-20 template that produces proper "Your Tasks"/"Your Profile" format
2. **Reliable Architecture**: Based on proven V7.1 codebase
3. **Consistent Output**: Job extractions (not performance reports)
4. **Clean Format**: Matches expected CV-ready structure

## Architecture

- **Base**: V7.1 template-based extraction pipeline
- **LLM**: qwen3:latest (26.5/25 quality score winner)
- **Prompt**: 2025-07-20 validated template
- **Output**: V7.1-compatible markdown format

## Expected Output Format

```markdown
## [Job Title] - Requirements & Responsibilities

### Your Tasks
* **Category**: Detailed responsibility description
* **Category**: Detailed responsibility description
...

### Your Profile
* **Education & Experience**: Requirements and preferred experience
* **Technical Skills**: Specific systems, software, tools mentioned
* **Language Skills**: Language requirements with proficiency levels
...
```

## Usage

```bash
# Process 1 job
python main.py --jobs 1

# Process 5 jobs
python main.py --jobs 5

# With verbose logging
python main.py --jobs 1 --verbose
```

## Quality Standards

- Comprehensive (both role AND requirements)
- Structured (clear sections)
- CV-Ready (suitable for recruitment)
- Professional business language
- NO benefits/company culture sections

---

*V11.0 combines the reliability of V7.1 with the proven 2025-07-20 template for optimal job extraction quality.*
