"""
Content Extraction Specialist v2.0 - Integration Example
======================================================

Demonstrates how to use the optimized Content Extraction Specialist v2.0
for Sandy's CV-to-job skill matching pipeline.

This example shows the improved output format and reduced redundancy
compared to the original v1.0 specialist.

Date: June 26, 2025
Version: 2.0
"""

import sys
import os
import time

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from content_extraction_specialist_v2 import ContentExtractionSpecialistV2, extract_job_content_v2  # type: ignore

def main():
    """
    Demonstrate Content Extraction Specialist v2.0 optimization
    """
    
    print("🚀 Content Extraction Specialist v2.0 - Skill Matching Optimized")
    print("=" * 70)
    
    # Sample job posting from Sandy's daily report
    sample_job = """
    FX Corporate Sales - Analyst - Associate Job ID:R0383730 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-11 Location: New York Position Overview Job Title: FX Corporate SalesCorporate Title: Analyst - AssociateLocation: New York, NYALL ROLES TO BE CONSIDEREDOverviewThe Risk Management Solutions (RMS) desk is responsible for providing foreign exchange, interest rate and workflow solutions to multi-national investment grade and high yield corporations in the Americas. Clients span a variety of sectors including healthcare, consumers, financial sponsors, TMT, industrials, and energy. The RMS desk provides clients with full access to the Corporate and Investment Bank's full product suite, with this role focusing on FX solutions, from basic spot, forward, swap (cross-currency), vanilla options up to more complex structured FX derivatives. FX RMS desk also provides automated solutions geared towards manual tasks related to intercompany netting and cash pooling exercises.What We Offer You A diverse and inclusive environment that embraces change, innovation, and collaborationA hybrid working model, allowing for in-office / work from home flexibility, generous vacation, personal and volunteer daysEmployee Resource Groups support an inclusive workplace for everyone and promote community engagementCompetitive compensation packages including health and wellbeing benefits, retirement savings plans, parental leave, and family building benefitsEducational resources, matching gift, and volunteer programsWhat You'll Do Front to back-end execution, including pricing and structuring FX/Rates/Commodities vanilla and exotics products depending upon clients' requirementsCollaboration with Trading, Structuring and Corporate Finance focusing on CFOs, treasurers, and finance departments of corporate clientsLiaise with e-trading and product partners for client flow optimization and performance tracking on electronic platforms and marketing DB's workflow solutionsHelp maximize revenue growth, increase in client penetration, share of wallet, cross selling and acquisition of significant deals and new clientsPrioritize KYC, documentation and approvals, et ceteraSkills You'll Need Bachelor's degree required. Familiarity with global financial markets and derivatives. Strong quantitative and technical abilityAbility to multi-task in a dynamic and fast-paced environment; Effective communication and interpersonal skills that allow for comfort in client-facing situationsProblem solving skills and a highly motivated, self-starter attitudeUnderstanding of key hedge accounting concepts and regulationsAbility to prepare a pitch both internally and externallySkills That Will Help You ExcelExcellent communication and relationship-building skillsEntrepreneurial thinking with a proactive, innovative mindsetAbility to work independently and manage multiple priorities across distinct functionsSelf-motivated and a self-starter attitudeStrong analytical and evaluative judgment skillsExpectationsIt is the Bank's expectation that employees hired into this role will work in the New York, NY office in accordance with the Bank's hybrid working model.Deutsche Bank provides reasonable accommodations to candidates and employees with a substantiated need based on disability and/or religion.The salary range for this position in New York City is $78,000 to $139,000. Actual salaries may be based on a number of factors including, but not limited to, a candidate's skill set, experience, education, work location and other qualifications. Posted salary ranges do not include incentive compensation or any other type of remuneration.Deutsche Bank Benefits At Deutsche Bank, we recognize that our benefit programs have a profound impact on our colleagues. That's why we are focused on providing benefits and perks that enable our colleagues to live authenti­cally and be their whole selves, at every stage of life. We provide access to physical, emotional, and financial wellness benefits that allow our colleagues to stay financially secure and strike balance between work and home. Click here to learn more!Learn more about your life at Deutsche Bank through the eyes of our current employees: https://careers.db.com/lifeThe California Consumer Privacy Act outlines how companies can use personal information. If you are interested in receiving a copy of Deutsche Bank's California Privacy Notice, please email HR.Direct@DB.com.#LI-HYBRID We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively.Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group.We welcome applications from all people and promote a positive, fair and inclusive work environment.Qualified applicants will receive consideration for employment without regard to race, color, religion, sex, sexual orientation, gender identity, national origin, disability, protected veteran status or other characteristics protected by law. Click these links to view "Deutsche Bank's Equal Opportunity Policy Statement" and the following notices: "EEOC Know Your Rights"; "Employee Rights and Responsibilities under the Family and Medical Leave Act"; and "Employee Polygraph Protection Act".
    """
    
    print(f"📥 Processing job posting ({len(sample_job)} characters)")
    print()
    
    # Method 1: Using the convenience function
    print("🔧 Method 1: Using convenience function")
    start_time = time.time()
    result1 = extract_job_content_v2(sample_job)
    end_time = time.time()
    
    print(f"   ⏱️  Processing time: {end_time - start_time:.2f}s")
    print(f"   📊 Reduction: {result1.reduction_percentage:.1f}%")
    print(f"   🎯 Domain signals: {len(result1.domain_signals)}")
    print()
    
    # Method 2: Using the specialist class directly
    print("🔧 Method 2: Using specialist class")
    specialist = ContentExtractionSpecialistV2()
    result2 = specialist.extract_content_optimized(sample_job)
    
    print(f"   ⏱️  Processing time: {result2.llm_processing_time:.2f}s")
    print(f"   📊 Format version: {result2.format_version}")
    print(f"   🤖 Model used: {result2.model_used}")
    print()
    
    # Display the optimized output
    print("📋 OPTIMIZED OUTPUT (Sandy's Format)")
    print("=" * 50)
    print(result2.extracted_content)
    print("=" * 50)
    print()
    
    # Show the improvement metrics
    print("📈 OPTIMIZATION METRICS")
    print("-" * 30)
    print(f"Original length:    {result2.original_length:,} characters")
    print(f"Extracted length:   {result2.extracted_length:,} characters")
    print(f"Size reduction:     {result2.reduction_percentage:.1f}%")
    print(f"Processing time:    {result2.llm_processing_time:.2f} seconds")
    print(f"Domain signals:     {len(result2.domain_signals)} found")
    print()
    
    # Show domain signals found
    if result2.domain_signals:
        print("🎯 DOMAIN SIGNALS DETECTED")
        print("-" * 30)
        for signal in result2.domain_signals[:10]:  # Show first 10
            print(f"   • {signal}")
        if len(result2.domain_signals) > 10:
            print(f"   ... and {len(result2.domain_signals) - 10} more")
        print()
    
    # Show what was removed
    print("🗑️  CONTENT REMOVED")
    print("-" * 30)
    for section in result2.removed_sections:
        print(f"   • {section}")
    print()
    
    # Validate Sandy's requirements
    print("✅ SANDY'S REQUIREMENTS VALIDATION")
    print("-" * 40)
    
    content = result2.extracted_content
    
    # Check for required sections
    required_sections = ["**Position:**", "**Required Skills:**", "**Key Responsibilities:**", "**Experience Required:**"]
    for section in required_sections:
        status = "✅" if section in content else "❌"
        print(f"   {status} {section}")
    
    # Check for removed boilerplate
    boilerplate_removed = "Here is the extracted content:" not in content
    print(f"   {'✅' if boilerplate_removed else '❌'} Boilerplate text removed")
    
    # Check for reduced redundancy
    title_count = content.lower().count("analyst")
    location_count = content.lower().count("new york")
    redundancy_reduced = title_count <= 2 and location_count <= 2
    print(f"   {'✅' if redundancy_reduced else '❌'} Redundancy reduced")
    
    print()
    print("🎉 Content Extraction Specialist v2.0 demonstration complete!")
    print("   Ready for Sandy's CV-to-job skill matching pipeline.")

def compare_with_v1():
    """
    Compare v2.0 output with what v1.0 would produce (conceptually)
    """
    print("\n🔍 COMPARISON: v1.0 vs v2.0 FORMAT")
    print("=" * 50)
    
    print("❌ v1.0 Format (OLD - with redundancy):")
    print("""
Here is the extracted content:

**Job Title and Role Specifics**
* Job Title: Analyst - Associate
* Full/Part-Time: Full-time
* Regular/Temporary: Regular
* Listed: 2025-06-11
* Location: New York, NY

**Technical Skills and Requirements**
* Bachelor's degree required
* Familiarity with global financial markets and derivatives
* Strong quantitative and technical ability
* [... more sections ...]

**Industry-Specific Terminology**
* FX derivatives
* Risk Management Solutions
* Cross-currency swaps
* [... repeated terms ...]

**Location Information**
* Location: New York, NY
* Office requirements: New York office
""")
    
    print("\n✅ v2.0 Format (NEW - optimized):")
    print("""
**Position:** Analyst - Associate - New York, NY

**Required Skills:**
- Bachelor's degree in finance, economics, or related field
- Familiarity with global financial markets and derivatives
- Strong quantitative and technical ability
- Understanding of hedge accounting concepts and regulations

**Key Responsibilities:**
- Front to back-end execution of FX/Rates/Commodities products
- Collaboration with Trading, Structuring and Corporate Finance
- Client flow optimization and performance tracking
- Revenue growth and client acquisition

**Experience Required:**
- Bachelor's degree required
- Experience with financial markets and derivatives
- Strong analytical and problem-solving skills
- Client-facing communication abilities
""")
    
    print("\n📊 KEY IMPROVEMENTS:")
    print("   ✅ Single position line (no repetition)")
    print("   ✅ Focused on matchable skills")
    print("   ✅ No boilerplate text")
    print("   ✅ Consistent section headers")
    print("   ✅ Removed redundant location mentions")
    print("   ✅ No 'Industry-Specific Terminology' section")
    print("   ✅ Clean format for automated parsing")

if __name__ == "__main__":
    main()
    compare_with_v1()
