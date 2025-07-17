"""
Test Content Extraction Specialist v2.0 - Skill Matching Optimized
================================================================

Tests for the optimized content extraction specialist that produces
clean, standardized output for CV-to-job skill matching.

Date: June 26, 2025
Version: 2.0
"""

import pytest
import sys
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from content_extraction_specialist_v2 import ContentExtractionSpecialistV2, extract_job_content_v2  # type: ignore

# Test data based on real job postings from Sandy's daily report
SAMPLE_JOB_POSTING = """
DWS - Operations Specialist - Performance Measurement (m/f/d) Job ID:R0364215 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-03 Location: Frankfurt Position Overview About DWS:At DWS, we're capturing the opportunities of tomorrow. You can be part of a leading, client-committed, global Asset Manager, making an impact on individuals, communities, and the world.Join us on our journey, and you can shape our transformation by working side by side with industry thought-leaders and gaining new and diverse perspectives. You can share ideas and be yourself, whilst driving innovative and sustainable solutions that influence markets and behaviours for the better.Every day brings the opportunity to discover a new now, and here at DWS, you'll be supported as you overcome challenges and reach your ambitions. This is your chance to lead an extraordinary career and invest in your future.Read more about DWS and who we are here.Our team:The aim of performance measurement is to provide a detailed overview of investment performance measured against individual investor benchmarks and precise quantitative data that can be used for further investment decisions as part of the portfolio management process. Performance measurement is an essential part of our active customer support and our commitment to transparency. Clear reports are not only helpful when evaluating an entire portfolio. They can be particularly important when analyzing the impact of components of exposure in individual markets and asset classes on the overall performance of a mandate. Performance measurement techniques are evolving dynamically. The most up-to-date measurement system can quickly become outdated. We are therefore constantly developing additional methods of risk and attribution analysis with the aim of maintaining the highest asset management standards in the industry and the best practices in all aspects of performance measurement.Your tasks:In the future, you will take responsibility for maintenance of benchmark data and calculate theoretical prices used for calculation of performance fee for retail funds. Act as contact person for internal and external questions related to performance fee of retail fundsYou will take responsibility for the monthly performance attributions and the analytical reviews that you carry out in coordination with portfolio management and other report recipients.You independently carry out calculations of the performance indicators and, if necessary, explain the details of the calculation and the underlying methodology to the relationship managers and institutional customersYou advise relationship and portfolio management on all topics related to performance measurement, in particular performance attributions.If necessary, you carry out ad hoc evaluations and analysesYou skillfully exploit existing optimization potential within our processesMeasuring, managing, and presenting (potential) risks and determining suitable measures to mitigate and avoid them in the long termEnsuring smooth and efficient service provision, taking into account all upstream and downstream processesManaging the suppliers of relevant services provided for the operating segmentYou independently familiarize yourself with complex systems (e.g. StatPro, Aladdin, Sim Corp Dimension, Coric) and maintain or further develop Access databases that are used for the reconciliation processesLast but not least, you independently carry out projects within the business unitYour profile:Degree in business mathematics or business administration (focus on finance and banking), alternatively several years of professional experience in the area of ​​performance calculation and risk figures for investment banking productsExcellent knowledge in the area of ​​investment accounting, FX, fixed income, equity products as well as performance calculation and risk analysis is preferredRoutine use of databases (Access/Oracle) and data analysisPerfect handling of MS Office, especially Excel and AccessProgramming knowledge in VBA, Python or similar programming languages. Understanding of modern technology like AI is preferred.CFA/CIPM is preferredCommitted, thoroughly analytical thinker with a strong sense of responsibility, knowing how to set priorities and keep a cool head in hot phasesStrong communication skills, team spirit and an independent, careful way of workingFluent written and spoken English and GermanPublication period: 12.5.2025 until further noticeWhat we'll offer you:Without the ambitions of our people, our achievements wouldn't be possible. And it's important to us that you enjoy coming to work - feeling healthy, happy and rewarded. At DWS, you'll have access to a range of benefits which you can choose from to create a personalised plan unique to your lifestyle. Whether you're interested in healthcare, company perks or are thinking about your retirement plan, there's something for everyone.Some of our core benefits:Physical and Mental Health Well-Being benefits including (but not limited to) Statutory Health Insurance (BKK), sickness benefit allowance and support helplines for employeesFamily friendly benefits including generous parental leave packages (supporting all variations of family set-ups) and support in finding childcare options including DWS's own kindergarten serviceA wide selection of pension plans, Personal Budget Accounts to enable sabbaticals or early retirement and capital-forming benefitsThe opportunity to support our CSR strategy which is focused on combatting climate change & achieving greater social justice. You can make donations to our partnered organisations or take part in corporate volunteering opportunities in your local communities by providing on hand support.DWS' current Hybrid Working model is designed to find the balance between in-person collaboration & engagement in the office, which is core to our working culture, whilst still remaining focused on supporting our employees with flexibility. We are committed to support flexible and hybrid working agreements across the globe. Depending on the location or role you are applying for, the split between working in the office and at home will be discussed and made clear as part of your application and interview process.We will continue to review and evolve our working environments and methods to ensure that we are working in the best way possible for our people.If you require any adjustments or changes to be made to the interview process for any reason including, or related to a disability or long-term health condition, then please contact your recruiter and let us know what assistance you may need. Examples of adjustments include providing a change to the format of the interview or providing assistance when at the DWS office. This will not affect your application and your recruitment team will discuss options with you.
"""

class TestContentExtractionSpecialistV2:
    """Test suite for Content Extraction Specialist v2.0"""
    
    def setup_method(self):
        """Setup test environment"""
        self.specialist = ContentExtractionSpecialistV2()
    
    def test_initialization(self):
        """Test specialist initialization"""
        assert self.specialist.format_version == "v2.0"
        assert hasattr(self.specialist, 'extract_content_optimized')
        assert hasattr(self.specialist, 'extract_content')
    
    def test_extract_content_structure(self):
        """Test that extracted content has proper structure"""
        result = self.specialist.extract_content(SAMPLE_JOB_POSTING)
        
        # Check result structure
        assert hasattr(result, 'extracted_content')
        assert hasattr(result, 'format_version')
        assert result.format_version == "v2.0"
        
        # Check content reduction
        assert result.extracted_length < result.original_length
        assert result.reduction_percentage > 0
    
    def test_standardized_format_sections(self):
        """Test that output contains required standardized sections"""
        result = self.specialist.extract_content(SAMPLE_JOB_POSTING)
        content = result.extracted_content
        
        # Required sections per Sandy's spec
        required_sections = [
            "**Position:**",
            "**Required Skills:**", 
            "**Key Responsibilities:**",
            "**Experience Required:**"
        ]
        
        for section in required_sections:
            assert section in content, f"Missing required section: {section}"
    
    def test_no_boilerplate_text(self):
        """Test that boilerplate text is removed"""
        result = self.specialist.extract_content(SAMPLE_JOB_POSTING)
        content = result.extracted_content.lower()
        
        # Should NOT contain these boilerplate phrases
        boilerplate_phrases = [
            "here is the extracted content",
            "based on the job posting",
            "the extracted information is",
            "here's the standardized format"
        ]
        
        for phrase in boilerplate_phrases:
            assert phrase not in content, f"Found boilerplate phrase: {phrase}"
    
    def test_redundancy_removal(self):
        """Test that redundant information is removed"""
        result = self.specialist.extract_content(SAMPLE_JOB_POSTING)
        content = result.extracted_content
        
        # Should not have excessive repetition of basic job info
        job_title_count = content.lower().count("operations specialist")
        location_count = content.lower().count("frankfurt")
        
        # Should mention these only once or twice, not repeatedly
        assert job_title_count <= 2, f"Job title repeated too many times: {job_title_count}"
        assert location_count <= 2, f"Location repeated too many times: {location_count}"
    
    def test_skill_extraction_focus(self):
        """Test that technical skills are properly extracted"""
        result = self.specialist.extract_content(SAMPLE_JOB_POSTING)
        content = result.extracted_content.lower()
        
        # Should contain key technical skills from the posting
        expected_skills = [
            "python", "excel", "access", "sql", "vba"
        ]
        
        skill_found_count = sum(1 for skill in expected_skills if skill in content)
        assert skill_found_count >= 3, f"Not enough technical skills found: {skill_found_count}"
    
    def test_benefits_removal(self):
        """Test that benefits and company culture content is removed"""
        result = self.specialist.extract_content(SAMPLE_JOB_POSTING)
        content = result.extracted_content.lower()
        
        # Should NOT contain extensive benefits information
        benefits_indicators = [
            "health insurance", "pension plan", "parental leave",
            "hybrid working", "volunteering", "childcare"
        ]
        
        benefits_found = sum(1 for indicator in benefits_indicators if indicator in content)
        assert benefits_found <= 1, f"Too much benefits content found: {benefits_found}"
    
    def test_domain_signals_extraction(self):
        """Test that domain signals are properly identified"""
        result = self.specialist.extract_content(SAMPLE_JOB_POSTING)
        
        # Should identify technical domain signals
        assert len(result.domain_signals) > 0, "No domain signals extracted"
        
        # Check for expected technical terms
        signals_text = " ".join(result.domain_signals).lower()
        expected_signals = ["sql", "python", "excel"]
        
        signal_matches = sum(1 for signal in expected_signals if signal in signals_text)
        assert signal_matches >= 1, f"Expected domain signals not found: {signal_matches}"
    
    def test_processing_performance(self):
        """Test that processing performance is reasonable"""
        result = self.specialist.extract_content(SAMPLE_JOB_POSTING)
        
        # Processing time should be reasonable (under 30 seconds)
        assert result.llm_processing_time < 30.0, f"Processing too slow: {result.llm_processing_time}s"
        
        # Should achieve significant reduction
        assert result.reduction_percentage > 50, f"Insufficient reduction: {result.reduction_percentage}%"
    
    def test_convenience_function(self):
        """Test the convenience function extract_job_content_v2"""
        result = extract_job_content_v2(SAMPLE_JOB_POSTING)
        
        assert result.format_version == "v2.0"
        assert "**Position:**" in result.extracted_content
        assert result.extracted_length < result.original_length

def test_fallback_mode():
    """Test fallback processing when LLM is unavailable"""
    # Create specialist with invalid URL to trigger fallback
    specialist = ContentExtractionSpecialistV2(ollama_url="http://invalid:99999")
    
    result = specialist.extract_content("Test job posting content")
    
    # Should still return a valid result
    assert hasattr(result, 'extracted_content')
    assert "fallback" in result.model_used
    assert result.format_version.endswith("-fallback")

if __name__ == "__main__":
    # Run basic tests
    print("🧪 Testing Content Extraction Specialist v2.0...")
    
    specialist = ContentExtractionSpecialistV2()
    result = specialist.extract_content(SAMPLE_JOB_POSTING)
    
    print(f"✅ Basic functionality test passed")
    print(f"📊 Original length: {result.original_length}")
    print(f"📊 Extracted length: {result.extracted_length}")
    print(f"📊 Reduction: {result.reduction_percentage:.1f}%")
    print(f"📊 Format version: {result.format_version}")
    print(f"⏱️ Processing time: {result.llm_processing_time:.2f}s")
    
    print("\n📋 Extracted Content Sample:")
    print("=" * 50)
    print(result.extracted_content[:500] + "..." if len(result.extracted_content) > 500 else result.extracted_content)
    print("=" * 50)
    
    print("\n🎯 Domain Signals Found:")
    print(", ".join(result.domain_signals[:10]))
    
    print("\n✅ Content Extraction Specialist v2.0 validation complete!")
