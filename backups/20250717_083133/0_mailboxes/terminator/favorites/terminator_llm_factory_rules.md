# Terminator@LLM-Factory Engineering Rules
*Updated: June 25, 2025 - Enhanced for Better Workflow*

## Core Development Principles

1. **Always use LLMs in specialists to perform tasks, never use hardcoded logic!**
   - LLMs provide adaptive intelligence and natural language understanding
   - Hardcoded rules become brittle and require manual maintenance
   - Exception: Simple utilities like file operations or basic validations

2. **Always use template-based output from Ollama, never use JSON!**
   - Templates are more reliable for structured LLM responses
   - JSON parsing can fail on malformed output; templates are more forgiving
   - Use clear section markers like `CONFLICT_DETECTED: YES/NO`

3. **Always create a zero-dependency test script and run it to ensure we are using Ollama, template-based output and achieve expected results!**
   - Validation is critical before delivery
   - Zero-dependency scripts ensure portability and ease of testing
   - Include both the specialist file and demo script in delivery folder

4. **Always adjust SLA to current performance, throughput and other quantitative targets.**
   - LLM performance ≠ hardcoded performance
   - SLAs must be realistic for the technology being used
   - Example: 3-8s per job for LLM vs 0.1s for hardcoded logic
   - Batch processing: 10-20 jobs/minute for LLM vs 1000+/minute hardcoded

## Quality Assurance

5. **Always discuss with terminator@llm_factory if the provided code does not deliver as expected.**
   - Early escalation prevents wasted effort
   - Collaborative problem-solving improves outcomes
   - Test with golden test cases before escalating

6. **Always validate edge cases with LLM specialists:**
   - Empty inputs, whitespace-only content, malformed data
   - LLMs may generate content even for empty inputs - this behavior should be tested and documented
   - Template parsing failures should have sensible fallbacks

## Delivery Standards

7. **Always remove files in 0_mailboxes/sandy@consciousness/inbox that are not part of this delivery to 0_mailboxes/sandy@consciousness/inbox/archive.**
   - Maintain clean communication channels
   - Archive old deliveries for reference
   - Keep only current delivery files in inbox

8. **Always deliver to sandy@consciousness:**
   - A zero-dependency demo script (with specialist file included)
   - Full documentation of what and how the specialist works
   - Performance metrics and validation results
   - Integration examples and usage patterns
   - Clear upgrade/migration instructions if replacing existing specialist

## Integration Requirements

9. **Always ensure specialists integrate with existing LLM Factory pipeline:**
   - Compatible with versioned specialist structure (`v1_0`, `v2_0`, etc.)
   - Proper error handling and logging
   - Statistics tracking for monitoring
   - Maintain API compatibility when upgrading (same method signatures)

10. **Always provide fallback mechanisms for LLM failures:**
    - Timeout handling (30s default for Ollama calls)
    - Connection error recovery
    - Graceful degradation when Ollama is unavailable
    - Template parsing fallbacks for malformed responses

## Enhanced Workflow Guidelines

11. **Version control for specialist upgrades:**
    - Create new version folder (v2_0) when switching from hardcoded to LLM
    - Keep old version for rollback capability
    - Document breaking changes and migration steps

12. **Always request 5 real-life examples from the business owner for golden test validation:**
    - Use standardized JSON format: `golden_test_cases_{specialist_name}.json`
    - Include test cases with: id, name, input_data, expected_output, notes
    - Add output_requirements and business_context sections
    - This format is reusable across all specialists and enables automated validation
    - Document test results and performance metrics on real business data
    - Include validation report in delivery package

13. **Ollama connection management:**
    - Always verify Ollama connection during initialization
    - Log connection status clearly for debugging
    - Use consistent timeout values across all specialists
    - Test with actual model before delivery

14. **Template design best practices:**
    - Use ALL_CAPS field names for easy parsing (e.g., `CONFLICT_DETECTED:`)
    - Include confidence scores as percentages (0-100)
    - Provide reasoning/explanation fields for debugging
    - Use consistent field ordering across specialists

15. **Performance monitoring:**
    - Track processing times per job
    - Monitor success/failure rates
    - Log LLM response quality metrics
    - Alert on performance degradation

## Demo Script Requirements (Added June 27, 2025)

16. **Always create comprehensive validation scripts, not simple demos:**
    - Command-line interface with `--test-file` parameter support
    - JSON output format for business system integration
    - Quantitative accuracy metrics with pass/fail criteria
    - Performance benchmarking with timing measurements
    - Format compliance validation for production use cases
    - Production readiness assessment with clear recommendations

17. **Demo script output format standards:**
    - JSON structure with specialist_version, test_date, overall_accuracy
    - Detailed test_results array with accuracy_score, missing_skills, extra_skills
    - Summary section with total_tests, passed_tests, average_accuracy
    - Performance metrics including processing_time per test case
    - Format compliance validation (clean output, no boilerplate text)
    - Comparative analysis showing improvement vs previous versions

18. **Business validation requirements:**
    - Validate against golden test cases with exact skill matching
    - Include accuracy threshold validation (90%+ for production)
    - Check output suitability for automated comparison algorithms
    - Measure format compliance to ensure clean skill extraction
    - Provide clear deployment recommendations based on results