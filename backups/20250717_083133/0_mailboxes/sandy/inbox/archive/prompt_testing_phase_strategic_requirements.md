# Prompt Testing Phase - Strategic Requirements Extraction
**Date**: July 11, 2025  
**Phase**: Pre-Implementation Prompt Engineering & Model Testing  
**Target**: Test strategic requirements extraction prompts with available Ollama models

---

## Available Models for Testing

```
phi3:latest                   4f2222927938    2.2 GB    8 weeks ago     
dolphin3:8b                   d5ab9ae8e1f2    4.9 GB    2 months ago    
codegemma:2b                  926331004170    1.6 GB    2 months ago    
codegemma:latest              0c96700aaada    5.0 GB    2 months ago    
olmo2:latest                  4208d3b406db    4.5 GB    2 months ago    
dolphin3:latest               d5ab9ae8e1f2    4.9 GB    2 months ago    
mistral:latest                f974a74358d6    4.1 GB    2 months ago    
qwen3:4b                      a383baf4993b    2.6 GB    2 months ago    
qwen3:1.7b                    458ce03a2187    1.4 GB    2 months ago    
qwen3:0.6b                    3bae9c93586b    522 MB    2 months ago    
gemma3:1b                     8648f39daa8f    815 MB    2 months ago    
deepseek-r1:8b                28f8fd6cdc67    4.9 GB    2 months ago    
qwen3:latest                  e4b5fd7f8af0    5.2 GB    2 months ago    
phi4-mini-reasoning:latest    3ca8c2865ce9    3.2 GB    2 months ago    
phi3:3.8b                     4f2222927938    2.2 GB    2 months ago    
gemma3:4b                     a2af6cc3eb7f    3.3 GB    2 months ago    
llama3.2:latest              a80c4f17acd5    2.0 GB    2 months ago    
```

**Recommended Testing Order**:
1. **mistral:latest** (4.1GB) - Good multilingual support
2. **qwen3:latest** (5.2GB) - Strong reasoning capabilities
3. **dolphin3:latest** (4.9GB) - Good instruction following
4. **phi4-mini-reasoning:latest** (3.2GB) - Reasoning-focused
5. **deepseek-r1:8b** (4.9GB) - Strong analytical capabilities

---

## Test 1: Strategic Elements Detection

### Prompt 1A: Rotation Program Detection

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are analyzing job descriptions for STRATEGIC CAREER DEVELOPMENT PROGRAMS. Focus on rotation programs, cross-functional exposure, and structured development paths.\n\nDetect rotation/development programs in this job description:\n\nJob Description:\nAlle 3-6 Monate rotierst Du in neue Projektteams und lernst so alle Unternehmensbereiche (Corporate & Investment Bank, DWS, Privat- und Firmenkundenbank) sowie Infrastrukturfunktionen (z.B. Risiko, Finanzen) der Bank kennen. You can expect challenging and varying tasks - from day one. As part of your job, you will rotate into new project teams every 3-6 months and get to know all business divisions.\n\nExtract ROTATION PROGRAM details:\n- Frequency: \n- Divisions/Areas:\n- Development Focus:\n- Confidence (1-10):",
  "stream": false
}'
```

### Prompt 1B: Cultural Fit Emphasis Detection

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are analyzing job descriptions for CULTURAL FIT and PERSONALITY EMPHASIS indicators. Look for signals that personality/culture is prioritized over pure technical qualifications.\n\nDetect cultural emphasis in this job description:\n\nJob Description:\nFachliche Qualifikation ist uns sehr wichtig, noch entscheidender für uns ist jedoch Deine Persönlichkeit. Um innovatives Denken zu fördern, setzen wir auf ein Team aus verschiedensten Persönlichkeiten. Wir legen Wert darauf, ein Arbeitsumfeld zu schaffen, in dem sich jedes Teammitglied zugehörig fühlen und authentisch sein kann. Professional qualifications are very important to us, but even more crucial is your personality. To deliver impact, we build an inclusive team with different backgrounds to drive innovative thinking.\n\nExtract CULTURAL EMPHASIS indicators:\n- Personality Priority: \n- Diversity Focus:\n- Authenticity Emphasis:\n- Confidence (1-10):",
  "stream": false
}'
```

### Prompt 1C: Leadership Access Detection

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are analyzing job descriptions for LEADERSHIP ACCESS and STRATEGIC POSITIONING. Look for indicators of executive exposure, board-level work, and senior management interaction.\n\nDetect leadership access in this job description:\n\nJob Description:\nZusammen mit dem DBMC Engagement Manager verantwortest du die Vorbereitung von Entscheidungsvorlagen für das Senior Management und den Vorstand. Du stehst im direkten Austausch mit unseren Kunden innerhalb der Bank und führst eigenständig Termine durch. Our team members obtain an unrivaled level of exposure and access to the Bank'\''s most senior executives. Together with the DBMC Engagement Manager, you are responsible for preparing decision templates for senior management and the board.\n\nExtract LEADERSHIP ACCESS indicators:\n- Executive Level:\n- Board Interaction:\n- Decision Authority:\n- Strategic Positioning:\n- Confidence (1-10):",
  "stream": false
}'
```

---

## Test 2: Bilingual German/English Processing

### Prompt 2A: German Professional Terms

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are analyzing a German/English job description for 5D requirements extraction. Recognize both German and English terminology.\n\nCommon German banking terms:\n- Kundenorientierung (customer orientation)\n- fundierte Berufserfahrung (solid professional experience)\n- Hochschule (university/college)\n- Teamplayer (team player)\n- Lösungsorientierung (solution orientation)\n- Führungsverantwortung (leadership responsibility)\n- Projektmanagement (project management)\n\nExtract SOFT SKILLS from this job description. List both German terms and their English equivalents:\n\nJob Description:\nSie sind verantwortlich für die eigenständige Analyse von Geschäftsprozessen, den Entwurf und die Entwicklung umfangreicher Softwarelösungen auf Basis von SAP-Plattformen unter Nutzung unserer agilen Methodik in einem großen Entwicklungsteam. Teamplayer*in, die/der in einem globalen und vielfältigen Team zusammenarbeitet. Ausgeprägte Kunden- und strategische Lösungsorientierung. Sie unterstützen das kontinuierliche Lernen und die offene Feedback-Kultur. Du bist konfliktfähig und überzeugst andere gerne von Deinen Ideen und Lösungsansätzen.\n\nSOFT SKILLS (format: German term | English equivalent):",
  "stream": false
}'
```

### Prompt 2B: Experience Requirements in German

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are analyzing German/English job descriptions for EXPERIENCE REQUIREMENTS. Recognize German professional experience terminology.\n\nGerman experience terms:\n- einschlägige Berufserfahrung (relevant professional experience)\n- fundierte Erfahrung (solid experience)\n- mehrjährige Erfahrung (multi-year experience)\n- Praxiserfahrung (practical experience)\n- Branchenerfahrung (industry experience)\n\nExtract EXPERIENCE REQUIREMENTS from this job description:\n\nJob Description:\nDu hast einschlägige Berufserfahrung gesammelt, idealerweise im Projektmanagement oder in einer Unternehmensberatung. Du bist eine verantwortungsbewusste, engagierte Persönlichkeit mit hervorragenden analytischen Fähigkeiten. You have relevant professional experience, ideally in project management or consulting. Fundierte Berufserfahrung in der Entwicklung und Programmierung großer und komplexer Softwarelösungen.\n\nEXPERIENCE REQUIREMENTS:\n- Years Required:\n- Industry Preference:\n- Specific Experience Types:\n- German Terms Found:\n- Confidence (1-10):",
  "stream": false
}'
```

---

## Test 3: Consulting-Specific Requirements

### Prompt 3A: Management Consulting Detection

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are analyzing job descriptions for MANAGEMENT CONSULTING and STRATEGIC ADVISORY roles. Focus on consulting-specific requirements and strategic project elements.\n\nDetect consulting requirements in this job description:\n\nJob Description:\nAls Teil des Deutsche Bank Management Consulting (DBMC), der globalen Managementberatung der Deutschen Bank, arbeitest du mit Führungskräften zusammen, um zu den Erfolgen der Bank beizutragen. Zu unseren Beratungsschwerpunkten zählen die Umsetzung von Strategie- und Transformationsprojekten, u.a. hinsichtlich der Förderung von Innovations- und Wachstumsthemen sowie weiterer wichtiger Herausforderungen der Bank. You will be joining Deutsche Bank Management Consulting (DBMC), the Bank'\''s in-house management consulting global function that partners with senior executives across the bank to deliver impact.\n\nExtract CONSULTING REQUIREMENTS:\n- Consulting Type:\n- Strategic Focus Areas:\n- Transformation Elements:\n- Executive Partnership:\n- Innovation Components:\n- Confidence (1-10):",
  "stream": false
}'
```

### Prompt 3B: Project Management & Leadership

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are analyzing job descriptions for PROJECT MANAGEMENT and LEADERSHIP RESPONSIBILITIES in consulting contexts.\n\nDetect project leadership requirements in this job description:\n\nJob Description:\nDu arbeitest an strategischen Projekten und übernimmst Verantwortung für Aufgaben in Teilprojekten und für Teammitglieder. Du unterstützt die Entwicklung deines Projektteams sowie die Konzeption von Best Practices und weiteren Methoden. You work on strategic projects and take responsibility for tasks in sub-projects and for team members. You support the development of your project team as well as the conception of best practices and other methods.\n\nExtract PROJECT LEADERSHIP requirements:\n- Project Types:\n- Team Responsibility:\n- Development Role:\n- Strategic Elements:\n- Methodology Focus:\n- Confidence (1-10):",
  "stream": false
}'
```

---

## Test 4: 5D Requirements Integration

### Prompt 4A: Complete 5D Extraction

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are a 5D Requirements Extraction Specialist. Extract ALL FIVE dimensions from this job description with strategic elements.\n\nDimensions to extract:\n1. TECHNICAL: Technologies, tools, programming languages, platforms\n2. BUSINESS: Domain knowledge, industry experience, business processes\n3. SOFT SKILLS: Communication, leadership, teamwork, analytical skills\n4. EXPERIENCE: Years required, specific role experience, industry background\n5. EDUCATION: Degree requirements, field of study, certifications\n\nJob Description:\nSenior Consultant (d/m/w) – Deutsche Bank Management Consulting. Du arbeitest an strategischen Projekten und übernimmst Verantwortung für Aufgaben in Teilprojekten und für Teammitglieder. Zusammen mit dem DBMC Engagement Manager verantwortest du die Vorbereitung von Entscheidungsvorlagen für das Senior Management und den Vorstand. Alle 3-6 Monate rotierst Du in neue Projektteams. Wir sind auf der Suche nach Talenten mit überdurchschnittlichen akademischen Leistungen aller Fachrichtungen (Bachelor-/Master-Abschluss). Du hast einschlägige Berufserfahrung gesammelt, idealerweise im Projektmanagement oder in einer Unternehmensberatung.\n\nExtract in this format:\nTECHNICAL:\n- [list]\n\nBUSINESS:\n- [list]\n\nSOFT SKILLS:\n- [list]\n\nEXPERIENCE:\n- [list]\n\nEDUCATION:\n- [list]\n\nSTRATEGIC ELEMENTS:\n- [rotation programs, cultural fit, leadership access]\n\nCONFIDENCE: [1-10]",
  "stream": false
}'
```

---

## Test 5: Template-Based Output Format

### Prompt 5A: Structured Template Output

```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "mistral:latest",
  "prompt": "You are a requirements extraction specialist that MUST use the exact template format provided. Do not deviate from the template structure.\n\nTemplate:\n```\nSTATUS: SUCCESS|ERROR\nEXTRACTION_TYPE: strategic_requirements\nCONFIDENCE: [0-10]\nLANGUAGE_DETECTED: [german|english|mixed]\n\nSTRATEGIC_ELEMENTS:\nrotation_program: [description or NONE]\ncultural_emphasis: [description or NONE]\nleadership_access: [description or NONE]\ntransformation_focus: [description or NONE]\n\nCONSULTING_ELEMENTS:\nmanagement_consulting: [YES|NO]\nstrategic_projects: [description or NONE]\nexecutive_partnership: [description or NONE]\n\nVALIDATION:\npatterns_found: [number]\nvalidation_confidence: [0-10]\nrequires_human_review: [YES|NO]\n```\n\nAnalyze this job description and respond using ONLY the template format:\n\nJob Description:\nAlle 3-6 Monate rotierst Du in neue Projektteams und lernst so alle Unternehmensbereiche kennen. Fachliche Qualifikation ist uns sehr wichtig, noch entscheidender für uns ist jedoch Deine Persönlichkeit. Zusammen mit dem DBMC Engagement Manager verantwortest du die Vorbereitung von Entscheidungsvorlagen für das Senior Management und den Vorstand.",
  "stream": false
}'
```

---

## Testing Protocol

### Phase 1: Individual Prompt Testing (Day 1)
1. **Test each prompt with 3 models**: mistral, qwen3, dolphin3
2. **Compare outputs** for consistency and accuracy  
3. **Identify best-performing model** for each prompt type
4. **Note hallucinations** and confidence accuracy

### Phase 2: Model Comparison (Day 2)
1. **Test all prompts with top 3 models**
2. **Evaluate German language handling**
3. **Assess strategic element detection accuracy**
4. **Measure template compliance**

### Phase 3: Prompt Refinement (Day 3)
1. **Refine prompts** based on test results
2. **Add validation patterns** to improve accuracy
3. **Test refined prompts** with best-performing models
4. **Create final prompt templates**

### Phase 4: Integration Testing (Day 4)
1. **Test with complete Deutsche Bank job description**
2. **Validate against our manual analysis**
3. **Ensure Golden Rules compliance**
4. **Document final specifications**

---

## Expected Results & Validation

### Success Criteria:
1. **Strategic Elements**: Detect rotation programs in 100% of test cases
2. **German Processing**: Recognize German professional terms accurately
3. **Template Compliance**: Follow exact output format consistently
4. **Confidence Accuracy**: Confidence scores correlate with actual accuracy
5. **No Hallucinations**: Facts extracted must exist in source text

### Validation Dataset:
- Deutsche Bank Senior Consultant (our deep dive job)
- SAP Engineer (technical role)
- Consulting roles from other banks
- German-only job descriptions
- English-only job descriptions

---

## Test Results Template

```markdown
## Model: [model_name]
## Prompt: [prompt_id]

### Output:
[model response]

### Evaluation:
- Accuracy: [1-10]
- German Recognition: [1-10] 
- Template Compliance: [1-10]
- Hallucinations: [YES/NO]
- Processing Time: [seconds]

### Notes:
[observations]
```

---

## Next Steps

1. **Run all tests** with curl commands
2. **Document results** using test results template
3. **Select best model-prompt combinations**
4. **Create implementation specifications**
5. **Build the actual specialist** based on validated prompts

This prompt testing phase will ensure our final implementation follows Golden Rule #1 (LLM-First) with confidence, using the most effective prompts and models for strategic requirements extraction.

**Ready to start testing?** Shall I begin with the strategic elements detection prompts using mistral:latest?
