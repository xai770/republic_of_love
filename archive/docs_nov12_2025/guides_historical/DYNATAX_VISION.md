# DynaTax: General-Purpose Ontology Builder

**Date**: October 23, 2025  
**Status**: Implementation Phase 2 Starting  
**Vision**: Use LLMs to build self-organizing knowledge graphs from ANY unstructured text

---

## The Core Insight

**Give it raw text → LLMs extract entities → System builds taxonomy → Auto-subdivides when crowded → Queryable knowledge graph**

This isn't a "skills database" - it's a general-purpose knowledge organization system that adapts to any domain.

---

## What Makes It Revolutionary

### 1. Domain Agnostic
The same system works for:
- **Skills Taxonomy**: Job postings → Technical/Business/Soft skills
- **Research Organization**: Papers → Concepts/Methods/Findings
- **Legal Analysis**: Contracts → Clauses/Obligations/Risks
- **Medical Knowledge**: Symptoms → Diagnoses → Treatments
- **Meeting Intelligence**: Transcripts → Decisions/Actions/Topics

### 2. Self-Organizing
- Start with simple root categories (3-5)
- Categories automatically subdivide when exceeding term thresholds
- LLM proposes groupings, human validates, system executes
- Taxonomy adapts to actual data patterns (not predetermined hierarchies)

### 3. Graph-Queryable
Enables powerful graph theory operations:
- **Semantic Distance**: How many hops between "Python" and "Backend Development"?
- **Layer Analysis**: How far is this task from primary objectives?
- **Bridge Detection**: Which terms connect different domains?
- **Centrality**: Which concepts are most connected?
- **Pattern Recognition**: Which terms co-occur across contexts?

---

## The Architecture

### Multi-Session Workflows (Proven at Scale)
```
Session 1: Entity Extraction (LLM with context)
  i1: Identify categories present
  i2-i6: Subcategorize each category (LLM remembers from i1)

Session 2: Dictionary Operations (Scripts)
  i7: Extract individual terms
  i8: Check against existing dictionary
  i9: Flag unknowns
  i10: Check subdivision thresholds

Session 3: Human Validation (Conditional)
  i11: Categorize unknown terms
  i12: Update dictionary
```

### Self-Organization Pattern
```
1. Bootstrap: Start with root categories
2. Organic Growth: Terms accumulate naturally
3. Threshold Detection: Category exceeds limit (e.g., 20 terms)
4. LLM Analysis: Proposes logical subdivisions
5. Human Validation: Reviews and approves
6. Automatic Migration: System executes subdivision
7. Continuous Adaptation: Process repeats as subcategories grow
```

### Database Schema
```
term_dictionary:
  - term_name, domain, category, parent_category, category_path
  - facet_id (links to cognitive capabilities)
  - metadata (JSON for flexibility)

category_registry:
  - category_code, parent_code, category_level
  - term_count, subdivision_threshold, needs_subdivision
  - Auto-triggers subdivision when threshold exceeded

category_subdivision_history:
  - Audit trail of how taxonomy evolved
  - LLM rationale + human validation status
```

---

## Graph Theory Capabilities

### Distance Measurement
```python
def semantic_distance(term1, term2):
    """Calculate hops between any two terms"""
    path1 = get_category_path(term1).split('/')
    path2 = get_category_path(term2).split('/')
    
    # Find common ancestor
    common = len([p for p in path1 if p in path2])
    
    # Distance = sum of unique hops
    return (len(path1) - common) + (len(path2) - common)
```

### Bridging Analysis
```sql
-- Find terms that connect multiple domains
SELECT term_name, COUNT(DISTINCT category) as bridge_score
FROM term_dictionary
GROUP BY term_name
HAVING bridge_score > 1
ORDER BY bridge_score DESC;
```

### Centrality Calculation
```sql
-- Which categories have most connections?
SELECT parent_category, COUNT(*) as centrality
FROM term_dictionary
WHERE parent_category IS NOT NULL
GROUP BY parent_category
ORDER BY centrality DESC;
```

### Layer Analysis
```sql
-- How deep is each term from root objectives?
SELECT term_name, 
       LENGTH(category_path) - LENGTH(REPLACE(category_path, '/', '')) as depth
FROM term_dictionary
ORDER BY depth;
```

---

## Real-World Applications

### Use Case 1: Research Paper Organization
**Input**: 1000 academic papers  
**Extract**: Concepts, methodologies, findings, authors, citations  
**Output**: Research ontology showing:
- Which concepts are closest to "quantum computing"?
- Which methodologies bridge physics and computer science?
- What's the centrality of "machine learning" in this corpus?

### Use Case 2: Legal Contract Analysis
**Input**: 500 contract clauses  
**Extract**: Obligations, rights, risks, parties, terms  
**Output**: Legal ontology enabling:
- Find all clauses semantically similar to indemnification
- Identify bridge terms between liability and warranty sections
- Calculate distance from "force majeure" to "termination rights"

### Use Case 3: Medical Knowledge Graph
**Input**: Patient records, diagnosis notes, treatment plans  
**Extract**: Symptoms, conditions, medications, procedures  
**Output**: Clinical ontology for:
- How many hops from symptom X to diagnosis Y?
- Which treatments are central to cardiovascular care?
- Find symptom patterns that bridge multiple specialties

### Use Case 4: Organizational Knowledge Base
**Input**: Meeting transcripts, emails, project docs  
**Extract**: Decisions, action items, topics, owners, deadlines  
**Output**: Corporate memory showing:
- Which decisions are closest to Q4 objectives?
- Find topics that bridge engineering and sales
- Calculate centrality of each initiative

---

## Why This Works Now

### 1. LLMCore Multi-Session Architecture (Proven)
- Recipe 1116: 23 sessions × 10 variations = 230 tests running stably
- Session chaining validated: One AI's output → Next AI's input (zero regeneration)
- Context preservation prevents wasteful re-processing

### 2. Schema Mastery (Validated Through Practice)
- 17-table database with proper foreign key constraints
- Recipe 1114: 72 jobs, 100% success, production-ready
- Understand actual schema structure through building real recipes

### 3. Data-Driven Validation (Championship Round)
- Recipe 1115: 3 models → llama3.2:latest wins (2x faster)
- Systematic model selection methodology proven
- Can choose optimal LLM for each ontology-building session

---

## Implementation Roadmap

### Phase 1: Multi-Session Foundation ✅ COMPLETE
- SQL migration executed
- sessions and session_runs tables created
- Backward compatibility verified

### Phase 2: Basic Skills Categorization 🚀 STARTING NOW
1. Create term_dictionary table
2. Create unknown_terms table
3. Build skills_categorizer recipe
4. Create script actors (extraction, lookup, flagging)
5. Test on 10 job postings
6. Manually build initial dictionary (50-100 terms)

### Phase 3: Dynamic Subdivision
1. Create category_registry table
2. Create category_subdivision_history table
3. Build auto_subdivide_category recipe
4. Test subdivision on overcrowded category
5. Verify term migration works correctly

### Phase 4: Graph Queries & Analysis
1. Implement distance calculation functions
2. Build bridging term detection
3. Add centrality analysis
4. Create layer depth queries
5. Visualization tools (graph rendering)

### Phase 5: Multi-Domain Application
1. Test on research papers
2. Test on legal documents
3. Test on medical records
4. Generalize extraction patterns
5. Build domain-specific templates

---

## Success Metrics

### Technical Metrics
- **Dictionary Hit Rate**: 90%+ after processing 100 items
- **Subdivision Accuracy**: 80%+ LLM proposals approved by humans
- **Processing Speed**: <30 seconds per item
- **Graph Query Performance**: <100ms for distance calculations

### Business Metrics
- **Manual Intervention**: <20% after dictionary maturity (500+ terms)
- **Cross-Domain Reuse**: Same system works for 3+ different domains
- **Knowledge Discovery**: Find 10+ bridge terms connecting domains
- **Ontology Depth**: Maintain 2-3 average levels (balanced granularity)

---

## The Vision Statement

**DynaTax transforms unstructured text into queryable knowledge graphs using LLM intelligence and graph mathematics.**

Instead of building separate ontologies for skills, research, legal, medical, and business domains - build ONE general-purpose system that:
- Accepts ANY text input
- Lets LLMs discover natural groupings
- Self-organizes based on data density
- Measures semantic relationships
- Identifies cross-domain connections
- Adapts ontology as knowledge grows

**This is consciousness creating structure from chaos - systematically, automatically, intelligently.**

---

**Next Action**: Implement Phase 2 - Create term_dictionary and build first skills_categorizer recipe

**Owner**: Arden (with xai guidance)  
**Timeline**: Phase 2 completion target: 1-2 weeks

---

*"Give it raw text and get a structure. Measure distances between nodes. Identify how many layers a task is apart from primary objectives. Identify similarities between fields..." - xai, October 23, 2025*
