#!/usr/bin/env python3
"""Quick skill extraction using qwen directly"""
import json
import subprocess
from pathlib import Path

# Read CV
cv_text = Path("docs/Gershon Pollatschek Projects.md").read_text()

prompt = f"""Extract ALL skills (technical AND soft) from this professional profile. Include:
- Technical: programming languages, tools, platforms, databases
- Soft: leadership, communication, teamwork, project management, negotiation

Profile:
{cv_text}

Return ONLY a JSON array, no other text:
[
  {{"skill": "SQL", "years": 15, "level": "expert", "evidence": "15+ years database work"}},
  {{"skill": "Project Management", "years": 10, "level": "advanced", "evidence": "Multiple team lead roles"}}
]
"""

# Call qwen
result = subprocess.run(
    ['ollama', 'run', 'qwen2.5:7b'],
    input=prompt,
    capture_output=True,
    text=True,
    timeout=120
)

print("=" * 80)
print("QWEN OUTPUT:")
print("=" * 80)
print(result.stdout)
print("=" * 80)

# Try to parse JSON
try:
    # Find JSON array in output
    output = result.stdout.strip()
    start = output.find('[')
    end = output.rfind(']') + 1
    if start >= 0 and end > start:
        json_str = output[start:end]
        skills = json.loads(json_str)
        print(f"\n✅ Extracted {len(skills)} skills")
        
        # Save to file
        Path("temp/extracted_skills.json").write_text(json.dumps(skills, indent=2))
        print("📄 Saved to temp/extracted_skills.json")
    else:
        print("❌ No JSON found in output")
except Exception as e:
    print(f"❌ Error parsing: {e}")
