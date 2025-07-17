# Revised Golden Rules for Requirements Extraction Specialists

## Core Principles

### 1. LLM-First Architecture with Strategic Validation
- **Primary Rule**: Use LLMs for semantic understanding, pattern recognition, and categorization
- **Validation Layer**: Implement data-driven validation using structured datasets (JSON) for known value sets
- **Hybrid Approach**: Combine LLM intelligence with rule-based guardrails for quality assurance
- **Never**: Pure hardcoded logic without LLM involvement

### 2. Structured Output & Template-Based Responses
- **Always**: Use template-based output from Ollama (never raw JSON from LLMs)
- **Structure**: Define clear templates for each extraction dimension
- **Consistency**: Ensure reproducible, parseable output formats
- **Validation**: Templates should include confidence indicators and fallback values

### 3. Scalable Data Management
- **Static Data**: Store limited value sets (academic degrees, programming languages, etc.) as JSON
- **Update Mechanism**: Implement processes to evolve and maintain reference data
- **Caching**: Cache LLM responses for repeated extractions
- **Batch Processing**: Design for efficient processing of hundreds/thousands of jobs

### 4. Quality Control & Error Handling
- **Confidence Scoring**: LLMs should provide confidence levels for extractions
- **Fallback Mechanisms**: Graceful degradation when LLMs fail or produce low-confidence results
- **Validation Layers**: Cross-check LLM outputs against known data patterns
- **Human Review Triggers**: Flag extractions requiring manual review based on confidence thresholds

### 5. Performance & Cost Optimization
- **API Cost Management**: Monitor and optimize LLM API usage
- **Latency Considerations**: Balance accuracy with response time requirements
- **Retry Logic**: Implement smart retry mechanisms with exponential backoff
- **Resource Monitoring**: Track performance metrics and costs

## Implementation Standards

### 6. Zero-Dependency Testing
- **Always**: Create and run zero-dependency test scripts
- **Validation**: Ensure Ollama integration and template-based output work correctly
- **Coverage**: Test all extraction dimensions and error scenarios
- **Documentation**: Include expected results and validation criteria

### 7. Modular Architecture
- **Separation of Concerns**: Separate extraction logic, validation, and output formatting
- **Testability**: Each component should be unit-testable
- **Maintainability**: Clear interfaces between modules
- **Extensibility**: Easy to add new extraction dimensions or validation rules

### 8. Delivery Standards
- **Target**: Always deliver to `0_mailboxes/sandy@consciousness/inbox`
- **Contents**: 
  - Zero-dependency demo script
  - Complete documentation of functionality and architecture
  - Test results and validation data
  - Reference datasets (JSON) used for validation
- **Cleanup**: Archive non-delivery files to `0_mailboxes/sandy@consciousness/inbox/archive`

## Specific to Requirements Extraction

### 9. Five-Dimensional Extraction Framework
- **Technical Requirements**: Programming languages, frameworks, tools
- **Business Requirements**: Domain knowledge, processes, methodologies
- **Soft Skills**: Communication, leadership, teamwork abilities
- **Experience Requirements**: Years of experience, specific role types
- **Education Requirements**: Degrees, certifications, academic qualifications

### 10. Domain-Specific Validation
- **Location Validation**: Use structured datasets for cities, states, countries
- **Technology Validation**: Maintain curated lists of programming languages, frameworks
- **Education Validation**: Standardized degree titles and certification names
- **Experience Validation**: Reasonable ranges and common role patterns

### 11. Continuous Improvement
- **Feedback Loops**: Collect and analyze extraction quality metrics
- **A/B Testing**: Test prompt improvements and validation rule changes
- **Version Control**: Track changes to prompts, templates, and validation rules
- **Evolution**: Adapt to new job types, technologies, and market trends

## Quality Metrics

### 12. Success Criteria
- **Accuracy**: >95% accuracy on known validation datasets
- **Coverage**: Complete extraction across all five dimensions
- **Consistency**: Reproducible results for identical inputs
- **Performance**: Processing time suitable for batch operations
- **Cost**: API costs within acceptable limits for scale

### 13. Monitoring & Alerting
- **Quality Dashboards**: Real-time monitoring of extraction quality
- **Error Tracking**: Log and analyze extraction failures
- **Performance Metrics**: Track API usage, latency, and costs
- **Trend Analysis**: Identify degradation patterns and improvement opportunities

---

## Migration Strategy from Current State

### Phase 1: Hybrid Implementation
- Implement LLM-based extraction with current regex validation
- Create template-based output system
- Build reference datasets for validation

### Phase 2: Quality Enhancement
- Implement confidence scoring and human review triggers
- Add comprehensive error handling and fallback mechanisms
- Optimize for performance and cost

### Phase 3: Scale Preparation
- Implement caching and batch processing
- Add monitoring and alerting systems
- Create feedback loops for continuous improvement

### Phase 4: Full Production
- Complete migration to LLM-first architecture
- Implement automated quality assurance
- Deploy continuous improvement mechanisms

---

*These rules represent our learnings from the July 2025 requirements extraction quality investigation and should be updated based on ongoing experience and technological developments.*
