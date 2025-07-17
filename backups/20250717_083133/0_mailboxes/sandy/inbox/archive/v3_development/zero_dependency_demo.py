# ZERO-DEPENDENCY DEMO SCRIPT: Four-Specialist Pipeline (Template-Based)
# For Deutsche Bank Content Extraction Specialist (v3.1 Enhanced)
# No external dependencies. All output is template-based (no JSON).

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from content_extraction_specialist_v3_1_ENHANCED import ContentExtractionSpecialistV31

if __name__ == "__main__":
    # Example input (replace with any job description or resume text)
    input_text = """
    Deutsche Bank is seeking a candidate with experience in Python, stakeholder management, process optimization, and effective communication. Familiarity with regulatory reporting and agile methodologies is a plus.
    """
    
    # Run the Four-Specialist Pipeline using LLMs
    specialist = ContentExtractionSpecialistV31()
    result = specialist.extract_skills(input_text)
    
    # Print results in template-based format
    print("--- EXTRACTED SKILLS ---")
    for skill in result.all_skills:
        print(f"- {skill}")
    print("------------------------")
