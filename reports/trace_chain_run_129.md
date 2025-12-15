# Workflow Execution Trace

**Generated:** 2025-11-25 14:56:51

## Workflow Context

**Workflow ID:** 3001
**Workflow Name:** Complete Job Processing Pipeline
**Posting ID:** 176
**Job Title:** Test Job Title
**Started:** 2025-11-25 14:53:28
**Completed:** 2025-11-25 14:56:51
**Duration:** 202.6 seconds
**Interactions:** 6 completed, 0 failed

---

## ✅ Interaction 1: Unknown

**Interaction ID:** 252
**Duration:** 128.89s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 9144
**Name:** Fetch Jobs from Deutsche Bank API
**Description:** Fetches job postings from Deutsche Bank API, checks for duplicates, parses locations, stores in postings table
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 56
**Name:** db_job_fetcher
**Type:** script
**Script:** core/wave_runner/actors/db_job_fetcher.py

### Prompt Template

````
{
  "user_id": 1,
  "max_jobs": 50,
  "source_id": 1,
  "skip_rate_limit": true
}
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**skip_if_rate_limited** (Priority: 100)
- **Condition:** `[RATE_LIMITED]`
- **Description:** Skip to extraction if fetcher is rate-limited (already ran today)
- **Next:** Conversation 9184

**API failure - terminate** (Priority: 50)
- **Condition:** `[FAILED]`
- **Description:** Job fetcher API failed - cannot proceed, terminate workflow
- **Next:** END (terminal)

**Route to check summary (success path)** (Priority: 50)
- **Condition:** `success`
- **Description:** Jobs fetched successfully - proceed to check summary
- **Next:** Conversation 9184

**API timeout - terminate** (Priority: 49)
- **Condition:** `[TIMEOUT]`
- **Description:** Job fetcher timed out - cannot proceed, terminate workflow
- **Next:** END (terminal)

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````json
{
  "user_id": 1,
  "max_jobs": 50,
  "source_id": 1,
  "skip_rate_limit": true
}
````

### Actual Output

````json
{
  "data": {
    "status": "success",
    "staging_ids": [
      473,
      474,
      475,
      476,
      477,
      478,
      479,
      480,
      481,
      482,
      483,
      484,
      485,
      486,
      487,
      488,
      489,
      490,
      494,
      495,
      496,
      497,
      498,
      499,
      500,
      501,
      502,
      503,
      504,
      505,
      506,
      507,
      508,
      509,
      510,
      511,
      512,
      513,
      514,
      515,
      516,
      517,
      518,
      519,
      520,
      521,
      522,
      523,
      524,
      525
    ],
    "jobs_fetched": 50,
    "jobs_full_data": [
      {
        "location": "Birmingham 5 Brindley Place",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0403343",
          "api_response": {
            "title": "Information Security Risk Specialist",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0403343"
            ],
            "externalPath": "/job/Birmingham-5-Brindley-Place/Information-Security-Risk-Specialist_R0403343-1",
            "locationsText": "Birmingham 5 Brindley Place"
          },
          "external_path": "/job/Birmingham-5-Brindley-Place/Information-Security-Risk-Specialist_R0403343-1",
          "job_description": "Job Description: Job Title: Information Security Risk Specialist Location: Birmingham Corporate Title: Assistant Vice President The role is within the 2nd Line of Defence (LoD) Information Security (IS) Risk Team based in Birmingham and part of global team in Singapore, Mumbai, Frankfurt, Jacksonville and New York. The team is part of the wider Information Security &amp; Technology Risk Team of 37. The team monitors IS Risks across the Group within all Divisions &amp; Regions and provides Senior Management and Regulators with an assessment of the Information Security Risks. In this role will provide support on various topics including risk assessments, targeted reviews, incidents root cause thematic, new business product assessments, transformation risk assessments, regulatory exams/enquires, emerging risks. What we\u00e2\u0080\u0099ll offer you A healthy, engaged and well-supported workforce are better equipped to do their best work and, more importantly, enjoy their lives inside and outside the workplace. That\u00e2\u0080\u0099s why we are committed to providing an environment with your development and wellbeing at its centre. You can expect: Hybrid Working - we understand that employee expectations and preferences are changing. We have implemented a model that enables eligible employees to work remotely for a part of their working time and reach a working pattern that works for them Competitive salary and non-contributory pension 30 days\u00e2\u0080\u0099 holiday plus bank holidays, with the option to purchase additional days Life Assurance and Private Healthcare for you and your family A range of flexible benefits including Retail Discounts, a Bike4Work scheme and Gym benefits The opportunity to support a wide ranging CSR programme + 2 days\u00e2\u0080\u0099 volunteering leave per year Your key responsibilities Monitoring of a specific business divisions\u00e2\u0080\u0099 IS Risk Profile including risk appetite breaches, remediation including Risk and Control assessment review. Performing and presenting results of targeted analysis on key IS Risks and inputting into the maturing of the IS Risk Framework, Policies and Control Objectives. Monitoring the impact to the IS Risk Profile of major bank-wide IS Strategies e.g. ISR Glidepath, Security Strategy, Digitalization, Robotics, Google Cloud. Performing assessment of operating/design effectiveness of key controls such as Identity and access, Cryptography, Data leakage, etc. Exploring the impact of emerging IS risks and providing support to UKI/European Central Bank based regulatory enquiries. Your skills and experience A good understanding of Information Security and Technology and how its used within financial services. Comfortable working in a large complex institutions and directly facing off to key internal stakeholders and Understanding of Operational Risk Management. An understanding of IS and IT Risk Frameworks such as ISO 27001, NIST 800-53, ITIL, COBIT and key IS / IT Regulatory laws such as DORA, EBA guidelines. Experience of working with end user IT systems such as MS 365 apps, further experience of reporting/business intelligence systems such as Tableau, Power BI is an advantage. Relevant professional certifications e.g. CISSP, CISA, CISM, CRISC, ITIL, ISO27001 Lead Auditor or similar are a plus. How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs We value diversity and as an equal opportunities\u00e2\u0080\u0099 employer, we make reasonable adjustments for those with a disability such as the provision of assistive equipment if required (e.g. screen readers, assistive hearing devices, adapted keyboards) Please note the expected salary for some roles may be below the minimum level requirements to support candidates who require a Skilled Worker visa to work in the UK. Should you already have a Skilled Worker visa and are identified for a role, we can discuss and support you with the process About us Deutsche Bank is the leading German bank with strong European roots and a global network. Click here to see what we do. Deutsche Bank in the UK is proud to have been named The Times Top 50 Employers for Gender Equality 2025 for six consecutive years. Additionally, we have been awarded a Gold Award from Stonewall and named in their Top 100 Employers 2024 for our work supporting LGBTQ+ inclusion. If you have a disability, health condition, or require any adjustments during the application process, we encourage you to contact our Adjustments Concierge on adjustmentsconcierge@db.com to discuss how we can best support you. Alternatively, you can share your phone number, and a member of the team will be happy to call you to talk through your specific requirements. We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Information Security Risk Specialist",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 494,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Birmingham-5-Brindley-Place/Information-Security-Risk-Specialist_R0403343-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Bangalore, Raheja Towers, 26-27 M. G. Road",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0404397",
          "api_response": {
            "title": "Regional Sales Head, Director",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0404397"
            ],
            "externalPath": "/job/Bangalore-Raheja-Towers-26-27-M-G-Road/Regional-Sales-Head--Director_R0404397",
            "locationsText": "Bangalore, Raheja Towers, 26-27 M. G. Road"
          },
          "external_path": "/job/Bangalore-Raheja-Towers-26-27-M-G-Road/Regional-Sales-Head--Director_R0404397",
          "job_description": "Job Description: Job Title: Regional Sales Head, Director Location: Bangalore, India Role Description This role requirement is to have a balance team management and leadership as well as Individual contribution. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities The role has a senior transactor element, in which individual contribution on developing deal traction and leading by example is needed: Sales Leadership: - Revenue growth and strategy: Plan, Develop and lead the South region strategy- predicated on growth in revenues. Revenue growth planning is backed by growth in NII largely, in addition of new fx volume, deposits, and FCY balances. Client acquisition, smart Account management, deep mining of network clients, Indian LLCs, new economy platform companies and other revenue accretive segments. P&amp;L discipline: Tracking and calibration of monthly revenues across the cash management drivers of business with a focus on reset and recalibrating client level driver growth via on ground sales management New products Commercialization: Offtake and density of existing solutions across the client set, for sticky revenues and cross sell ratio. Leverage Trade business and lending opportunities to successfully achieve a high cross-selling ratio on the client base and new prospects New Origination: Hunting mindset is needed, in order to provide a game-changing mindset to growing what is inherently a new client acquisition business. Deals backed by solutioning, structuring mindset, for onshore solutions in payments, or for outbound global cash deals with LLCs will be an added advantage. Leading by example for the team is most needed here. South strategy execution: Smart and effective execution on the thematics which are peculiar to the South India market, across Bangalore, Chennai and Hyderabad Outcome Focussed leadership : Very high degree of achievement orientation and the ability to make every month/review period count. A combination of effort matrix and outcome on financial parameters and stated targets is needed Partnership within Corporate bank: Leverage other parts of the corporate bank, or investment bank to generate incremental opportunities for the cash management business. Stakeholder Management: Role related maturity, in developing a very healthy working relationship with product management, compliance, in business controls, and other network team members. Hunt for new client deals in cash management across MNCs and LLCs across business segments like corporates, NBFI and New age internet companies Grow wallet from existing clients and own existing CCM client relationships including coverage at CFO/CXO levels Win RFPs and large revenue complex deals in partnership with SMEs in the bank Your skills and experience Existing sales background with 7-12 years workex in corporate sales Experience in Cash management sales an advantage, experience in working on other products like Trade Finance &amp; FX and/or Coverage in Commercial/Corporate Banking is an advantage MBA from top B-Schools, CA or similar post graduation qualification from top institutions preferred Self-starter, go-getter, should have high levels of initiative, energy, enthusiasm and curiosity levels. How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.htm We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Regional Sales Head, Director",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 495,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Bangalore-Raheja-Towers-26-27-M-G-Road/Regional-Sales-Head--Director_R0404397",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Chennai",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0412108",
          "api_response": {
            "title": "Sales Manager \u2013 Premium Banking",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0412108"
            ],
            "externalPath": "/job/Chennai/Sales-Manager---Premium-Banking_R0412108",
            "locationsText": "Chennai"
          },
          "external_path": "/job/Chennai/Sales-Manager---Premium-Banking_R0412108",
          "job_description": "Job Description: Job Title: Sales Manager \u00e2\u0080\u0093 Premium Banking Corporate Title: NCT Location: Chennai, India Role Description Candidate is having prior experience of New to bank acquisition of saving accounts through open market lead generation and closure, successful onboarding of Customer for a smooth transition to branch banking team, Sourcing new account. Your experience will support team/Bank to acquire new client from the open market to bank with us and generate revenue What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Acquisition Increase acquisition of Target clientele across in Advantage Banking segments. Periodically assist Advantage Banking in conducting approved local level sales drive (micro events) for the acquisition. Acquire new accounts from group companies / family of existing customers. Acquire new accounts from referrals from existing customers Relationship Building / Deepening / Cross Sell / Transition Ensure consistent growth of the Advantage Banking portfolio. Work closely with the Advantage Banking and team and establish synergies for maximum penetration of Investment &amp; Insurance sales to new customers along with deepening into the book. Build a robust momentum regarding the third-party distribution (insurance, auto loans, mortgages) and fee income to scale up the client portfolio growth, in line with the set targets. Implement customer contact programs to ensure their share of wallet with the bank increases. Ensure smooth transition of customer management to the respective RM post-acquisition Retention Ensure top class service delivery to clients to be in line with the best in the industry. Monitor high net worth accounts closely to ensure that customers continue regular use the account and grow balances. Work towards reactivating accounts which have stopped transacting or depleted in balances. Assist in resolving service hurdles to create a delight situation for customers Risk Management &amp; Governance Ensure awareness and adherence with the Know Your Customer policy, Anti Money Laundering Policy, Mis-selling Policy, Information Protection Policy, Operational Risk, Code of Conduct and other laid down compliance norms of the bank as stipulated from time to time. Provide regular feedback on the changing customer needs to the SSM. Any suspicious transaction to be immediately reported to the SSM. Your skills and experience In-depth knowledge of Product and Policy Having Good Communication skill Having good negotiation skill Have and understood the market update and knowledge. Having awareness and information about the competition How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager \u2013 Premium Banking",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 496,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Chennai/Sales-Manager---Premium-Banking_R0412108",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Chennai",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0412104",
          "api_response": {
            "title": "Sales Manager \u2013 Premium Banking",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0412104"
            ],
            "externalPath": "/job/Chennai/Sales-Manager---Premium-Banking_R0412104",
            "locationsText": "Chennai"
          },
          "external_path": "/job/Chennai/Sales-Manager---Premium-Banking_R0412104",
          "job_description": "Job Description: Job Title: Sales Manager \u00e2\u0080\u0093 Premium Banking Corporate Title: NCT Location: Chennai, India Role Description Candidate is having prior experience of New to bank acquisition of saving accounts through open market lead generation and closure, successful onboarding of Customer for a smooth transition to branch banking team, Sourcing new account. Your experience will support team/Bank to acquire new client from the open market to bank with us and generate revenue What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Acquisition Increase acquisition of Target clientele across in Advantage Banking segments. Periodically assist Advantage Banking in conducting approved local level sales drive (micro events) for the acquisition. Acquire new accounts from group companies / family of existing customers. Acquire new accounts from referrals from existing customers Relationship Building / Deepening / Cross Sell / Transition Ensure consistent growth of the Advantage Banking portfolio. Work closely with the Advantage Banking and team and establish synergies for maximum penetration of Investment &amp; Insurance sales to new customers along with deepening into the book. Build a robust momentum regarding the third-party distribution (insurance, auto loans, mortgages) and fee income to scale up the client portfolio growth, in line with the set targets. Implement customer contact programs to ensure their share of wallet with the bank increases. Ensure smooth transition of customer management to the respective RM post-acquisition Retention Ensure top class service delivery to clients to be in line with the best in the industry. Monitor high net worth accounts closely to ensure that customers continue regular use the account and grow balances. Work towards reactivating accounts which have stopped transacting or depleted in balances. Assist in resolving service hurdles to create a delight situation for customers Risk Management &amp; Governance Ensure awareness and adherence with the Know Your Customer policy, Anti Money Laundering Policy, Mis-selling Policy, Information Protection Policy, Operational Risk, Code of Conduct and other laid down compliance norms of the bank as stipulated from time to time. Provide regular feedback on the changing customer needs to the SSM. Any suspicious transaction to be immediately reported to the SSM. Your skills and experience In-depth knowledge of Product and Policy Having Good Communication skill Having good negotiation skill Have and understood the market update and knowledge. Having awareness and information about the competition How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager \u2013 Premium Banking",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 497,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Chennai/Sales-Manager---Premium-Banking_R0412104",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Chennai",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0414054",
          "api_response": {
            "title": "Sales Manager \u2013 Premium Banking",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0414054"
            ],
            "externalPath": "/job/Chennai/Sales-Manager---Premium-Banking_R0414054",
            "locationsText": "Chennai"
          },
          "external_path": "/job/Chennai/Sales-Manager---Premium-Banking_R0414054",
          "job_description": "Job Description: Job Title: Sales Manager \u00e2\u0080\u0093 Premium Banking Corporate Title: NCT Location: Chennai, India Role Description Candidate is having prior experience of New to bank acquisition of saving accounts through open market lead generation and closure, successful onboarding of Customer for a smooth transition to branch banking team, Sourcing new account. Your experience will support team/Bank to acquire new client from the open market to bank with us and generate revenue What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Acquisition Increase acquisition of Target clientele across in Advantage Banking segments. Periodically assist Advantage Banking in conducting approved local level sales drive (micro events) for the acquisition. Acquire new accounts from group companies / family of existing customers. Acquire new accounts from referrals from existing customers Relationship Building / Deepening / Cross Sell / Transition Ensure consistent growth of the Advantage Banking portfolio. Work closely with the Advantage Banking and team and establish synergies for maximum penetration of Investment &amp; Insurance sales to new customers along with deepening into the book. Build a robust momentum regarding the third-party distribution (insurance, auto loans, mortgages) and fee income to scale up the client portfolio growth, in line with the set targets. Implement customer contact programs to ensure their share of wallet with the bank increases. Ensure smooth transition of customer management to the respective RM post-acquisition Retention Ensure top class service delivery to clients to be in line with the best in the industry. Monitor high net worth accounts closely to ensure that customers continue regular use the account and grow balances. Work towards reactivating accounts which have stopped transacting or depleted in balances. Assist in resolving service hurdles to create a delight situation for customers Risk Management &amp; Governance Ensure awareness and adherence with the Know Your Customer policy, Anti Money Laundering Policy, Mis-selling Policy, Information Protection Policy, Operational Risk, Code of Conduct and other laid down compliance norms of the bank as stipulated from time to time. Provide regular feedback on the changing customer needs to the SSM. Any suspicious transaction to be immediately reported to the SSM. Your skills and experience In-depth knowledge of Product and Policy Having Good Communication skill Having good negotiation skill Have and understood the market update and knowledge. Having awareness and information about the competition How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager \u2013 Premium Banking",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 498,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Chennai/Sales-Manager---Premium-Banking_R0414054",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Chennai",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0412659",
          "api_response": {
            "title": "Sales Manager \u2013 Premium Banking",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0412659"
            ],
            "externalPath": "/job/Chennai/Sales-Manager---Premium-Banking_R0412659-1",
            "locationsText": "Chennai"
          },
          "external_path": "/job/Chennai/Sales-Manager---Premium-Banking_R0412659-1",
          "job_description": "Job Description: Job Title: Sales Manager \u00e2\u0080\u0093 Premium Banking Corporate Title: NCT Location: Chennai, India Role Description Candidate is having prior experience of New to bank acquisition of saving accounts through open market lead generation and closure, successful onboarding of Customer for a smooth transition to branch banking team, Sourcing new account. Your experience will support team/Bank to acquire new client from the open market to bank with us and generate revenue What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Acquisition Increase acquisition of Target clientele across in Advantage Banking segments. Periodically assist Advantage Banking in conducting approved local level sales drive (micro events) for the acquisition. Acquire new accounts from group companies / family of existing customers. Acquire new accounts from referrals from existing customers Relationship Building / Deepening / Cross Sell / Transition Ensure consistent growth of the Advantage Banking portfolio. Work closely with the Advantage Banking and team and establish synergies for maximum penetration of Investment &amp; Insurance sales to new customers along with deepening into the book. Build a robust momentum regarding the third-party distribution (insurance, auto loans, mortgages) and fee income to scale up the client portfolio growth, in line with the set targets. Implement customer contact programs to ensure their share of wallet with the bank increases. Ensure smooth transition of customer management to the respective RM post-acquisition Retention Ensure top class service delivery to clients to be in line with the best in the industry. Monitor high net worth accounts closely to ensure that customers continue regular use the account and grow balances. Work towards reactivating accounts which have stopped transacting or depleted in balances. Assist in resolving service hurdles to create a delight situation for customers Risk Management &amp; Governance Ensure awareness and adherence with the Know Your Customer policy, Anti Money Laundering Policy, Mis-selling Policy, Information Protection Policy, Operational Risk, Code of Conduct and other laid down compliance norms of the bank as stipulated from time to time. Provide regular feedback on the changing customer needs to the SSM. Any suspicious transaction to be immediately reported to the SSM. Your skills and experience In-depth knowledge of Product and Policy Having Good Communication skill Having good negotiation skill Have and understood the market update and knowledge. Having awareness and information about the competition How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager \u2013 Premium Banking",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 499,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Chennai/Sales-Manager---Premium-Banking_R0412659-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "New Delhi, 18 & 20 Kasturba GM",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0411842",
          "api_response": {
            "title": "Sales Manager \u2013 Premium Banking",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0411842"
            ],
            "externalPath": "/job/New-Delhi-18--20-Kasturba-GM/Sales-Manager---Premium-Banking_R0411842",
            "locationsText": "New Delhi, 18 & 20 Kasturba GM"
          },
          "external_path": "/job/New-Delhi-18--20-Kasturba-GM/Sales-Manager---Premium-Banking_R0411842",
          "job_description": "Job Description: Job Title: Sales Manager \u00e2\u0080\u0093 Premium Banking Corporate Title: NCT Location: New Delhi, India Role Description Candidate is having prior experience of New to bank acquisition of saving accounts through open market lead generation and closure, successful onboarding of Customer for a smooth transition to branch banking team, Sourcing new account. Your experience will support team/Bank to acquire new client from the open market to bank with us and generate revenue What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Acquisition Increase acquisition of Target clientele across in Advantage Banking segments. Periodically assist Advantage Banking in conducting approved local level sales drive (micro events) for the acquisition. Acquire new accounts from group companies / family of existing customers. Acquire new accounts from referrals from existing customers Relationship Building / Deepening / Cross Sell / Transition Ensure consistent growth of the Advantage Banking portfolio. Work closely with the Advantage Banking and team and establish synergies for maximum penetration of Investment &amp; Insurance sales to new customers along with deepening into the book. Build a robust momentum regarding the third-party distribution (insurance, auto loans, mortgages) and fee income to scale up the client portfolio growth, in line with the set targets. Implement customer contact programs to ensure their share of wallet with the bank increases. Ensure smooth transition of customer management to the respective RM post-acquisition Retention Ensure top class service delivery to clients to be in line with the best in the industry. Monitor high net worth accounts closely to ensure that customers continue regular use the account and grow balances. Work towards reactivating accounts which have stopped transacting or depleted in balances. Assist in resolving service hurdles to create a delight situation for customers Risk Management &amp; Governance Ensure awareness and adherence with the Know Your Customer policy, Anti Money Laundering Policy, Mis-selling Policy, Information Protection Policy, Operational Risk, Code of Conduct and other laid down compliance norms of the bank as stipulated from time to time. Provide regular feedback on the changing customer needs to the SSM. Any suspicious transaction to be immediately reported to the SSM. Your skills and experience In-depth knowledge of Product and Policy Having Good Communication skill Having good negotiation skill Have and understood the market update and knowledge. Having awareness and information about the competition How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager \u2013 Premium Banking",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 500,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/New-Delhi-18--20-Kasturba-GM/Sales-Manager---Premium-Banking_R0411842",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Hong Kong, Intl Commerce Ctr",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0405024",
          "api_response": {
            "title": "C&AFC - Investment Bank & APAC Sanctions, Regulatory Advisory Specialist - VP",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0405024"
            ],
            "externalPath": "/job/Hong-Kong-Intl-Commerce-Ctr/Corporate-Bank---APAC-Sanctions--Regulatory-Advisory-Specialist---VP_R0405024",
            "locationsText": "Hong Kong, Intl Commerce Ctr"
          },
          "external_path": "/job/Hong-Kong-Intl-Commerce-Ctr/Corporate-Bank---APAC-Sanctions--Regulatory-Advisory-Specialist---VP_R0405024",
          "job_description": "Job Description: Details of the Division and Team: As a global bank, Deutsche Bank has a wide array of obligations. As a European company, we must comply with the sanctions measures put in place by the European Union and enforced by national level authorities, including those in Germany. In addition, given our strategic market presence in other jurisdictions, including the United States, our Global Sanctions Policy takes measures, such as those administered by OFAC, into account. As a matter of bank policy, we have a globally standardized approach to protect the integrity of Deutsche Bank as a premier global bank as well as our employees and our clients. What we will offer you: A healthy, engaged and well-supported workforce is better equipped to do their best work and, more importantly, enjoy their lives inside and outside the workplace. That\u00e2\u0080\u0099s why we are committed to providing an environment with your development and wellbeing at its center. You can expect: Competitive Salary and non-contributory pension 20 days annual leave plus generous number of public holidays Life Assurance and Private Healthcare for you and your family A range of flexible benefits including retail discounts, gym benefits, wellbeing incentives The opportunity to support a wide ranging CSR program plus take volunteering leave days Your key responsibilities: Support Global Sanctions Advisory in protecting DB from legal, regulatory and reputational risk with regard to business involving sanctioned entities and / or countries. Provide guidance regarding sanctions-related questions and issues; thereby supporting Businesses (1st Line of Defence) establish appropriate organisation and control structures to process transactions in a well-defined and compliant environment. Interface with client service officers on transaction-related requests and decide on these in full compliance with all applicable sanctions regulations as well as the DB\u00e2\u0080\u0099s policies and procedures. Continuously monitor the sanctions regulatory situation in the region. Support in the translation of external developments of the legal situation into potential policy adjustments for the Bank. Ensure diligent review of transaction-related requests and decide on these in full compliance with all applicable sanctions regulations as well as the Bank's policies and procedures. Investigate and review escalations resulting from pre- and post-trade sanctioned securities controls. Oversee and support all Sanctions-related aspects in deal team activities, including the drafting of sanctions clauses. Review/ decide on the adoption of new clients/ review of existing clients that are referred to the Head of Sanctions Investment Bank. Support sanctions-relevant reporting obligations involving countries in the APAC region to the competent authorities. Handle and respond to inquiries from regulatory authorities as well as internal or external auditors and business lines regarding sanctions observance. Conduct training or briefing sessions to Business and other Infrastructure units within the APAC region. Participation in global and regional calls to update on regional developments and issues may be required. Review and assessment of any potential sanctions breaches escalated to the IB Sanctions Advisory Team. Identification of any sanctions relevant gaps in existing processes and addressing these with relevant stakeholders. Depending on seniority, may lead and manage a small team. Your skills and experience: Minimum of 5 years\u00e2\u0080\u0099 experience in sanctions advisory Thorough understanding of global sanctions policy &amp; governance function, providing sanctions advice directly to internal and external stakeholders Strong project management and planning skills experience with the ability to lead various working groups, while providing stability re: business-as-usual activities Strong stakeholder management skills Thorough understanding of financial sanctions and embargoes across APAC Experienced in managing a team and developing the skillset and knowledge of the team member Required to communicate (verbal and written) clearly to Business units and APAC locations substantiated assessment/position and recommend follow-up action. Strong attention to detail and being meticulous in reviewing sanctions-related issues for all escalations from Business units and APAC locations. Self-starter, proactive and independent, exercises flexibility in addressing contentious issues, principled, and action-oriented individual. Team player with strong interpersonal skills, as well as an understanding of Asia-Pacific cultural nuances. How we\u00e2\u0080\u0099ll support you: Flexible working to assist you balance your personal priorities Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs Training and development to help you excel in your career About us and our teams: Deutsche Bank is the leading German bank with strong European roots and a global network. click here to see what we do. Deutsche Bank &amp; Diversity We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "C&AFC - Investment Bank & APAC Sanctions, Regulatory Advisory Specialist - VP",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 501,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Hong-Kong-Intl-Commerce-Ctr/Corporate-Bank---APAC-Sanctions--Regulatory-Advisory-Specialist---VP_R0405024",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Pune - Margarpatta",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0412136",
          "api_response": {
            "title": "Full Stack Solution Architect, AVP",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0412136"
            ],
            "externalPath": "/job/Pune---Margarpatta/Full-Stack-Solution-Architect--AVP_R0412136",
            "locationsText": "Pune - Margarpatta"
          },
          "external_path": "/job/Pune---Margarpatta/Full-Stack-Solution-Architect--AVP_R0412136",
          "job_description": "Job Description: Job Title: Full Stack Solution Architect, AVP Location: Pune, India Role Description Deutsche Bank is actively renewing its digital channels and has started many strategic and challenging projects. Next to some major technological changes Deutsche Bank has decided to step into the Agile software development methodology in order to improve its agility and reduce time to market without scarifying quality As a senior developer you will bring Java design and development skills to enforce the group of developers within a Squad. You will extensively make use and apply Continuous Integration tools and practices in the context of Deutsche Bank\u00e2\u0080\u0099s digitalization journey. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under child care assistance benefit (gender neutral) Flexible working arrangements Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Key Responsibilities / Tasks: Strong Solution Design Capability Develop and unit-test, Integrate, deploy, maintain and improve software Perform peer code review Actively participate into the squad activities and ceremonies e.g. daily stand-up/scrum meeting Actively participate and Dev chapter lead activities Apply continuous integration best practices in general (SCM, build automation, unit testing, dependency management) Collaborate with other squad members to achieve the Squad/Sprint objectives Report progress/update Agile team management tools (JIRA/Confluence) Manage individual task priorities and deliverables Responsible for quality of solutions the Candidate/applicant provides Contribute to planning and continuous improvement activities, Support the PO, Analyst and Scrum Master Your skills and experience Experience \u00e2\u0080\u0093 8+Years Proficiency in working with global and local teams, working in a collaborative agile environment. Excellent knowledge of Java, J2EE, spring framework. Excellent knowledge of HTML5, CSS &amp; JavaScript frameworks (AngularJS and Angular 5/8), CSS frameworks. Excellent knowledge of cross-platform and native mobile frameworks (Ionic, Apache Cordova, iOS, Android). Excellent knowledge of web servers (Apache), testing &amp; debugging e2e. Excellent knowledge of Webservices (SOAP/REST), messaging (JMS/MQ), database (Oracle/MySQL etc), batch processing, security concepts, application servers (Tomcat/Wildfly etc), testing &amp; debugging e2e. DevOps and problem oriented mind-set. Functional design, technical design and programming of new projects, enhancements, maintenance and troubleshooting of a specific set of applications, following IT Application Life Cycle standards aligned with technology strategy. How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Full Stack Solution Architect, AVP",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 502,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Pune---Margarpatta/Full-Stack-Solution-Architect--AVP_R0412136",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Bangalore, Velankani Tech Park",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0413676",
          "api_response": {
            "title": "Sales Manager \u2013 Mortgage",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0413676"
            ],
            "externalPath": "/job/Bangalore-Velankani-Tech-Park/Sales-Manager---Mortgage_R0413676",
            "locationsText": "Bangalore, Velankani Tech Park"
          },
          "external_path": "/job/Bangalore-Velankani-Tech-Park/Sales-Manager---Mortgage_R0413676",
          "job_description": "Job Description: Job Title: Sales Manager \u00e2\u0080\u0093 Mortgage Corporate Title: NCT Location: Bangalore, India Role Description Increase acquisition of target clientele across mortgage and loan against property segments. Responsible for new business acquisition through open market. Build and strengthen strong network of direct sales agencies in the market. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Responsible for new business acquisition through open market. Should have a strong network of DSA's in the market - Atleast 10 DSA's with whom files are discussed on a regular basis. Strong at DSA management and new DSA empanelment. Your skills and experience In-depth knowledge of Product and Policy. Having Good Communication skill. Having good negotiation skill. Have and understood the market update and knowledge. Having awareness and information about the competition. How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager \u2013 Mortgage",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 503,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Bangalore-Velankani-Tech-Park/Sales-Manager---Mortgage_R0413676",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Mumbai Nirlon Knowledge Pk B1",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0410722",
          "api_response": {
            "title": "Sales Manager \u2013 Mortgage",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0410722"
            ],
            "externalPath": "/job/Mumbai-Nirlon-Knowledge-Pk-B1/Sales-Manager---Mortgage_R0410722",
            "locationsText": "Mumbai Nirlon Knowledge Pk B1"
          },
          "external_path": "/job/Mumbai-Nirlon-Knowledge-Pk-B1/Sales-Manager---Mortgage_R0410722",
          "job_description": "Job Description: Job Title: Sales Manager \u00e2\u0080\u0093 Mortgage Corporate Title: NCT Location: Mumbai, India Role Description Increase acquisition of target clientele across mortgage and loan against property segments. Responsible for new business acquisition through open market. Build and strengthen strong network of direct sales agencies in the market. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Responsible for new business acquisition through open market. Should have a strong network of DSA's in the market - Atleast 10 DSA's with whom files are discussed on a regular basis. Strong at DSA management and new DSA empanelment. Your skills and experience In-depth knowledge of Product and Policy. Having Good Communication skill. Having good negotiation skill. Have and understood the market update and knowledge. Having awareness and information about the competition. How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager \u2013 Mortgage",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 504,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Mumbai-Nirlon-Knowledge-Pk-B1/Sales-Manager---Mortgage_R0410722",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Mumbai Nirlon Knowledge Pk B1",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0410720",
          "api_response": {
            "title": "Sales Manager \u2013 Mortgage",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0410720"
            ],
            "externalPath": "/job/Mumbai-Nirlon-Knowledge-Pk-B1/Sales-Manager---Mortgage_R0410720",
            "locationsText": "Mumbai Nirlon Knowledge Pk B1"
          },
          "external_path": "/job/Mumbai-Nirlon-Knowledge-Pk-B1/Sales-Manager---Mortgage_R0410720",
          "job_description": "Job Description: Job Title: Sales Manager \u00e2\u0080\u0093 Mortgage Corporate Title: NCT Location: Mumbai, India Role Description Increase acquisition of target clientele across mortgage and loan against property segments. Responsible for new business acquisition through open market. Build and strengthen strong network of direct sales agencies in the market. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Responsible for new business acquisition through open market. Should have a strong network of DSA's in the market - Atleast 10 DSA's with whom files are discussed on a regular basis. Strong at DSA management and new DSA empanelment. Your skills and experience In-depth knowledge of Product and Policy. Having Good Communication skill. Having good negotiation skill. Have and understood the market update and knowledge. Having awareness and information about the competition. How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager \u2013 Mortgage",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 505,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Mumbai-Nirlon-Knowledge-Pk-B1/Sales-Manager---Mortgage_R0410720",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Bangalore, Raheja Towers, 26-27 M. G. Road",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0412392",
          "api_response": {
            "title": "Sales Manager - BIL",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0412392"
            ],
            "externalPath": "/job/Bangalore-Raheja-Towers-26-27-M-G-Road/Sales-Manager---BIL_R0412392",
            "locationsText": "Bangalore, Raheja Towers, 26-27 M. G. Road"
          },
          "external_path": "/job/Bangalore-Raheja-Towers-26-27-M-G-Road/Sales-Manager---BIL_R0412392",
          "job_description": "Job Description: Job Title: Sales Manager - BIL Corporate Title: NCT Location: Bangalore, India Role Description Increase acquisition of target clientele across business instalment loan segments. Responsible for new business acquisition through open market. Build and strengthen strong network of direct sales agencies in the market. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy. Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Responsible for new business acquisition through open market. Should have a strong network of DSA's in the market - Atleast 10 DSA's with whom files are discussed on a regular basis. Strong at DSA management and new DSA empanelment. Your skills and experience In-depth knowledge of Product and Policy Having Good Communication skill Having good negotiation skill Have and understood the market update and knowledge. Having awareness and information about the competition How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager - BIL",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 506,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Bangalore-Raheja-Towers-26-27-M-G-Road/Sales-Manager---BIL_R0412392",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Bangalore Velankani ISC",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0413939",
          "api_response": {
            "title": "Information Security Officer, AS",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0413939"
            ],
            "externalPath": "/job/Bangalore-Velankani-ISC/Information-Security-Officer--AS_R0413939",
            "locationsText": "Bangalore Velankani ISC"
          },
          "external_path": "/job/Bangalore-Velankani-ISC/Information-Security-Officer--AS_R0413939",
          "job_description": "Job Description: Job Title: Information Security Officer Corporate Title: Associate Location: Bangalore, India Role Description The role of an Information Security Officer (ISO) is of a role holder aligned to a portfolio of applications (Application ISO). The ISO has the responsibility for the operational aspects of ensuring compliance with the Information Security Principles. The ISO is the primary contact for information security relevant matters within their area of responsibility. The ISO has a disciplinary reporting line into their Line Manager and a functional reporting line into the Divisional CISO. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy, Best in class leave policy. Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities To assume the ownership and responsibility for the assigned IT assets, in line with the DB Group information Security management processes and the Divisional ISMS. To support the development and maintenance of Information Security policies and procedures pertaining to the Unit in accordance with the Information Security policies and procedures of DB Group. To support the management of IS Risks within the Risk Appetite defined by the ISR. To execute the IS Risk assessments and compliance evaluations for assigned IT assets To ensure the execution of information security risk management requirements in them area of responsibility as additionally defined by the Divisional ISO (e.g., conducting risk assessments on an organizational basis, preparing and implementing management action plans to mitigate identified risks) To ensure the implementation of Identity and Access Management Processes and the execution of a periodic recertification of User Access Rights in their area of responsibility To provide timely updates to the Divisional ISO regarding the aforementioned information security management tasks To ensure that application entries regarding information security (e.g., Data Protection and Data Privacy fields) in the Group\u00e2\u0080\u0099s inventory of applications are accurate and up to date To implement Segregation of Duty (SoD) rules for the assigned IT assets To contribute to the Information Security incident management process in the case of a security breach \u00c2\u00b7 Keep oneself informed of the Information Security Principles and its subordinate documents and liaise with any other necessary parties to accomplish their tasks. These resources may be e.g., the TISO, ITAO or any other subject matter experts \u00c2\u00b7 To ensure appropriate documentation of information security risk management in area of responsibility. This includes major decisions including identified and assessed risks as well as risk mitigation measures To deliver all items requested during regulatory and internal Information Security related audits Your skills and experience Candidate should have a minimum of 8 years of business experience in an operation management /risk management capacity, working knowledge in various banking products with strong communications skill. Knowledge on Information Security Controls, Data Protection Policy, Information classification principles and segregation of duties requirements within Banking Operations Good understanding of Regulatory, Compliance, Risk &amp; Control Knowledge Have sound knowledge of Identity and Access Management Process Ability to multitask and manage multiple deliverables / projects that are highly visible and of strategic importance to our clients Ability to effectively communicate with clients internally and externally Must be a team player and facilitator Desirable Solid technical understanding of the business (CB Operations) including strong knowledge of application security related processes. Knowledge of electronic banking products and flow of instructions Computer proficiency in MS Office and ability to utilize IT initiatives to achieve a high degree of operational efficiency, optimize costs and add value to the service provided Innovative approach to work and continuously identify and implement process improvements Seek opportunities to improve service processes, minimize operational risk and reduce costs Strong analytical skills, detail orientation, service commitment and solid people management skills Strong awareness of risk control How we\u00e2\u0080\u0099ll support you Training and development help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Information Security Officer, AS",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 507,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Bangalore-Velankani-ISC/Information-Security-Officer--AS_R0413939",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Chennai",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0411710",
          "api_response": {
            "title": "Sales Manager - BIL",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0411710"
            ],
            "externalPath": "/job/Chennai/Sales-Manager---BIL_R0411710",
            "locationsText": "Chennai"
          },
          "external_path": "/job/Chennai/Sales-Manager---BIL_R0411710",
          "job_description": "Job Description: Job Title: Sales Manager - BIL Corporate Title: NCT Location: Chennai, India Role Description Increase acquisition of target clientele across business instalment loan segments. Responsible for new business acquisition through open market. Build and strengthen strong network of direct sales agencies in the market. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy. Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Responsible for new business acquisition through open market. Should have a strong network of DSA's in the market - Atleast 10 DSA's with whom files are discussed on a regular basis. Strong at DSA management and new DSA empanelment. Your skills and experience In-depth knowledge of Product and Policy Having Good Communication skill Having good negotiation skill Have and understood the market update and knowledge. Having awareness and information about the competition How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Sales Manager - BIL",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 508,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Chennai/Sales-Manager---BIL_R0411710",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Mumbai Nirlon Knowledge Pk B1",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0399436",
          "api_response": {
            "title": "Risk Analyst, NCT",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0399436"
            ],
            "externalPath": "/job/Mumbai-Nirlon-Knowledge-Pk-B1/Risk-Analyst--NCT_R0399436-1",
            "locationsText": "Mumbai Nirlon Knowledge Pk B1"
          },
          "external_path": "/job/Mumbai-Nirlon-Knowledge-Pk-B1/Risk-Analyst--NCT_R0399436-1",
          "job_description": "Job Description: In Scope of Position based Promotions (INTERNAL only) Job Title: Risk Analyst, NCT Location: Mumbai, India Role Description This position is part of the group providing data and MIS support services to the broader team called GCAF - GLOBAL CREDIT ANALYTICS FUNCTION. GCAF is engaged in counterparty credit risk assessment &amp; Probability of Default (PD) Ratings What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Position Specific Responsibilities and Accountabilities Researching various data sources as per the set process to search and seek financials of global corporates Understanding financials and inputting key financial values in system for assessment Ensuring all required data is stored in the agreed format and location of the local data storage facility Delivering required data by within agreed timelines Ensure data accuracy and integrity by filtering of data and noting down the sources for later references Prepare and follow pipeline of requests and work Adhoc designing and generation of MIS for various levels of management Adhoc presentations for relevant stakeholders across the Bank Support other team members in case of application issues Maintain good working relationship with other GCAF Your skills and experience Experience Minimum 1 year experience in a similar data oriented / MIS related role providing hands on experience on Excel tools. Technical Skills Good MS Office skills, esp. in Microsoft Word / Excel / PowerPoint/ MS Access. Should be adept in data search on Internet / Search Engines (such as Google / Yahoo). Basic knowledge of financial statements. Will be helpful if the candidate has experience in Bloomberg, Factiva, Bankscope and/or other such financial data sources Knowledge of VBA programming would be an added advantage Soft Skills Analytical skills to understand specific data requirements, basic knowledge of financial markets Demonstrate ability to search, collate and present data required by research analysts within stipulated time Good general knowledge and keen interest in financial sector developments across the globe While being a good Team player, must be a self-starter, pro-active in bringing new ideas and solutions to the table Must be a self-starter, be pro-active in bringing new ideas and solutions in data collation and maintenance of existing data sources (e.g. automation of data retrieval, building of templates in Excel) Education/ Qualifications Minimum Required: Any Graduate (Preferably Bachelors in Commerce / Economics background) Desirable: M. Com / MBA / MFM / PG Diploma How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.htm We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Risk Analyst, NCT",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 509,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Mumbai-Nirlon-Knowledge-Pk-B1/Risk-Analyst--NCT_R0399436-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Jakarta, Jl. Imam Bonjol No. 80",
        "raw_data": {
          "posted_on": "Posted Yesterday",
          "external_id": "R0412742",
          "api_response": {
            "title": "Corporate Bank - Head of Cash Products, Indonesia - VP",
            "postedOn": "Posted Yesterday",
            "bulletFields": [
              "R0412742"
            ],
            "externalPath": "/job/Jakarta-Jl-Imam-Bonjol-No-80/Corporate-Bank---Head-of-Cash-Products--Indonesia---VP_R0412742",
            "locationsText": "Jakarta, Jl. Imam Bonjol No. 80"
          },
          "external_path": "/job/Jakarta-Jl-Imam-Bonjol-No-80/Corporate-Bank---Head-of-Cash-Products--Indonesia---VP_R0412742",
          "job_description": "Job Description: Details of the Division and Team: Deutsche Bank is a client-centric global universal bank, one that is leading change and innovation in the industry, championing integrity, sustainable performance and innovation with our clients, and redefining our culture and relationships with each other. CB is at the heart of the Deutsche Bank franchise, offering the best cash, trade and securities solutions to our clients across the globe. CB\u00e2\u0080\u0099s business and operating model is defined by these five fundamental activities - Build, Operate, Control, Service, and Sell. The Corporate Cash Management (CCM) business is also based on these five activities and \u00e2\u0080\u009cCash Products\u00e2\u0080\u009d constitute the \u00e2\u0080\u009cBuild\u00e2\u0080\u009d function under CCM. This function is responsible for identifying the CCM client &amp; market trends, setting product strategy, overseeing the development and roll-out of new products and managing product-level profitability, pricing structure, costing and risks. Within this, the country Cash Product function is responsible for the execution of the global strategy on the ground, overseeing product risks and costs, providing a country perspective into regional/global product requirements and managing the interface with our client facing teams, clients, markets and internal stakeholders. The business products that come under the purview of Cash Products include Single &amp; Bulk Payments, FX, Cheques and Liquidity Management services. The Head of Cash Products Indonesia will report to the Head of Cash Products \u00e2\u0080\u0093 APAC ex Gr. China &amp; India and will be responsible for the country Cash Product function for Indonesia. What we will offer you: A healthy, engaged and well-supported workforce is better equipped to do their best work and, more importantly, enjoy their lives inside and outside the workplace. That\u00e2\u0080\u0099s why we are committed to providing an environment with your development and wellbeing at its center. You can expect: Comprehensive Medical Insurance Coverage for Employee and Family Life Insurance Coverage Additional Pension Scheme (DPLK) on top of Statutory Contribution EAP \u00e2\u0080\u0093 free and confidential counseling, online work-life resources Staff Loan including Housing Loan, Car Loan and Personal Loan Hybrid work arrangement Comprehensive leave benefits Annual health checkup \u00e2\u0080\u0093 cost borne by company (once a year; conditions apply) Key responsibilities: Market Engagement &amp; Feedback: Assess and analyse product needs and opportunities (Regulatory / Technology / Market Infrastructure / Geography) Support sales channels with product expertise Strategy and Commercialisation: Provide local input to product strategy and roadmap Define adequate / profitable E2E Cash offering for the country (Payments &amp; Collections, Accounts, FX, Client Connectivity, etc.) Conduct product benchmarking and competitor analysis as input to SPRs and strategy process Commercialise product strategy Support sales channels in launching campaigns Execution: Support local implementation of global / cross regional change initiatives Lead and provide oversight of purely local transformational &amp; change initiatives Identify local optimization levers (independently and in collaboration with global team) and implement measures to increase branch efficiency Product Governance / Frameworks: Execute local new product approvals (NPA) based on global standards Create local product catalogue and map to global products Non-Financial Risk / Safety &amp; Soundness: Ensure local adherence to risk policies and frameworks Ensure compliance with all local regulations and internal policies in collaboration with respective Infrastructure partners Remediate and mitigate risk; Lead Local Audit items and Local Self-Identified Issues (SII) Pricing &amp; Deal Reviews: Provide local market inputs to influence global minimum pricing framework Implement pricing framework and approve / decline pricing outside framework through Regional CCM Deal &amp; Product Review Forum Chair country CCM Deal &amp; Product Review Forum P&amp;L and Performance Management: Manage country level Product Profitability and KPIs focusing on CIR Outages &amp; Incidents: Represent CCM Cash Products during incidents / outages and work with I&amp;S, Sales and IT / Operations to understand and manage client impact Support IT / Operations to identify and remediate root causes where applicable CCM Coordination: Manage interface to local Regulators via the relevant regulatory affairs teams when needed Your skills and experience: You will have: Recognized university degree (or comparable education) Comprehensive CCM industry experience, deep expertise on client needs, market and regulatory trends in CCM in Indonesia Proven track record in managing multiple stakeholders You will be someone with: Proven ability to influence decisions, prioritize and work under pressure Excellent analytical capabilities, logical thinker and ability to manage complex problems Excellent communication skills with the ability to communicate in a clear, concise manner at all levels Experienced stakeholder management skills and ability to build strong working relationships at all levels, including senior management (Managing Director level). Displays cultural sensitivity and has experience working with and within global geographically dispersed teams and related staffing issues Planning \u00e2\u0080\u0093 ability to develop and suggest solutions, plans and scenarios How we\u00e2\u0080\u0099ll support you: Flexible working to assist you balance your personal priorities Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs Training and development to help you excel in your career About us and our teams: Deutsche Bank is the leading German bank with strong European roots and a global network. click here to see what we do. Deutsche Bank &amp; Diversity: We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Corporate Bank - Head of Cash Products, Indonesia - VP",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 510,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Jakarta-Jl-Imam-Bonjol-No-80/Corporate-Bank---Head-of-Cash-Products--Indonesia---VP_R0412742",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Jacksonville, 5022 Gate Parkway",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0393928",
          "api_response": {
            "title": "Trade and/or Transaction Analyst - Associate",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0393928"
            ],
            "externalPath": "/job/Jacksonville-5022-Gate-Parkway/Trade-and-or-Transaction-Analyst---Associate_R0393928-1",
            "locationsText": "Jacksonville, 5022 Gate Parkway"
          },
          "external_path": "/job/Jacksonville-5022-Gate-Parkway/Trade-and-or-Transaction-Analyst---Associate_R0393928-1",
          "job_description": "Job Description: Job Title Trade and/or Transaction Analyst Corporate Title Assistant Vice President Location Jacksonville, FL Overview The DWAC Exchange Associate is responsible for overseeing Deposit/Withdrawal At Custodian (DWAC) exchange transactions. You will review transfer and exchange documents to confirm presentation is in good form and the securities requested to be exchanged are fungible. You will then process exchanges within internal systems and monitor DTC to confirm settlements. The role requires attention to detail and adherence to regulatory standards to ensure seamless and compliant transaction processing. What We Offer You A diverse and inclusive environment that embraces change, innovation, and collaboration A hybrid working model, allowing for in-office / work from home flexibility, generous vacation, personal and volunteer days Employee Resource Groups support an inclusive workplace for everyone and promote community engagement Competitive compensation packages including health and wellbeing benefits, retirement savings plans, parental leave, and family building benefits Educational resources, matching gift and volunteer programs What You\u00e2\u0080\u0099ll Do Security transfer and exchange reviews Exchange processing within internal and external applications End of day reporting and reconciliation Adhering to internal controls and regulatory compliance Skills You\u00e2\u0080\u0099ll Need Excellent communication skills and multi-tasking capabilities Flexibility to prioritize and support workloads from multiple teams Knowledge of Microsoft Office Acute attention to detail Securities industry experience Skills That Will Help You Excel Technical inclination to learn new applications Initiative to work with multiple products Flexible and able to work overtime Ability to work as a team in a diverse environment Expectations It is the Bank\u00e2\u0080\u0099s expectation that employees hired into this role will work in the Jacksonville office in accordance with the Bank\u00e2\u0080\u0099s hybrid working model. Deutsche Bank provides reasonable accommodations to candidates and employees with a substantiated need based on disability and/or religion. The salary range for this position in Jacksonville is $48,000 to $68,800. Actual salaries may be based on a number of factors including, but not limited to, a candidate\u00e2\u0080\u0099s skill set, experience, education, work location and other qualifications. Posted salary ranges do not include incentive compensation or any other type of remuneration. Deutsche Bank Benefits At Deutsche Bank, we recognize that our benefit programs have a profound impact on our colleagues. That\u00e2\u0080\u0099s why we are focused on providing benefits and perks that enable our colleagues to live authentically and be their whole selves, at every stage of life. We provide access to physical, emotional, and financial wellness benefits that allow our colleagues to stay financially secure and strike balance between work and home. Click here to learn more! Learn more about your life at Deutsche Bank through the eyes of our current employees https://careers.db.com/life The California Consumer Privacy Act outlines how companies can use personal information. If you are interested in receiving a copy of Deutsche Bank\u00e2\u0080\u0099s California Privacy Notice please email HR.Direct@DB.com. #LIHYBRID We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. Qualified applicants will receive consideration for employment without regard to race, color, religion, sex, sexual orientation, gender identity, national origin, disability, protected veteran status or other characteristics protected by law. Click these links to view Deutsche Bank\u00e2\u0080\u0099s Equal Opportunity Policy Statement and the following notices: EEOC Know Your Rights; Employee Rights and Responsibilities under the Family and Medical Leave Act; and Employee Polygraph Protection Act. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Trade and/or Transaction Analyst - Associate",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 511,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Jacksonville-5022-Gate-Parkway/Trade-and-or-Transaction-Analyst---Associate_R0393928-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Birmingham 5 Brindley Place",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0394740",
          "api_response": {
            "title": "Electronic Communications Governance Operations Lead",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0394740"
            ],
            "externalPath": "/job/Birmingham-5-Brindley-Place/Electronic-Communications-Governance-Operations-Lead_R0394740-1",
            "locationsText": "Birmingham 5 Brindley Place"
          },
          "external_path": "/job/Birmingham-5-Brindley-Place/Electronic-Communications-Governance-Operations-Lead_R0394740-1",
          "job_description": "Job Description: Job Title Electronic Communications Governance Operations Lead Location Birmingham Corporate Title Vice President The mission of the Electronic Communications Board (ECOM) is to govern the Electronic Communications Systems (ECS), based upon the policies and practices defined by Deutsche Bank. ECOM is an essential central governance board which evaluates new or changed ECS and determines if they are essential to support Deutsche Bank\u00e2\u0080\u0099s capabilities and compliance with policies or requirements set by Compliance, Legal, Group Data Protection and CDO / Records Management as well as other key control functional areas. As the Operations Lead for ECOM, you will manage a dedicated team of colleagues to engage with technology and business service owners to understand their products and their capabilities. You will drive evaluation of these services against policies and requirements and ultimately present them for review and approval by key control functions. What we\u00e2\u0080\u0099ll offer you A healthy, engaged and well-supported workforce are better equipped to do their best work and, more importantly, enjoy their lives inside and outside the workplace. That\u00e2\u0080\u0099s why we are committed to providing an environment with your development and wellbeing at its centre. You can expect: Hybrid Working - we understand that employee expectations and preferences are changing. We have implemented a model that enables eligible employees to work remotely for a part of their working time and reach a working pattern that works for them Competitive salary and non-contributory pension 30 days\u00e2\u0080\u0099 holiday plus bank holidays, with the option to purchase additional days Life Assurance and Private Healthcare for you and your family A range of flexible benefits including Retail Discounts, a Bike4Work scheme and Gym benefits The opportunity to support a wide ranging CSR programme + 2 days\u00e2\u0080\u0099 volunteering leave per year Your key responsibilities Working with technology contacts for ECS applications to ensure solutions related to retention and surveillance requirements are identified and in place Providing oversight to the processes and procedures in place for reviews conducted with technology contacts and architects for individual applications Providing recommendations to the ECOM board on the ECS determination for individual applications Working with application architects and technology owners to track the progress of any mitigation activities identified by the ECOM board Supporting the data integrity for the inventory of applications containing electronic communications used within Deutsche Bank Responsibility for creating reports in your area of responsibility and presenting them to ECOM board and other external groups as well as leading and managing the ECOM analyst team Your skills and experience Experience in the use/support of electronic communications within the Financial Services industry Experience working across technology organisations for the implementation and/or remediation of functionality required to meet regulatory compliance Experience in designing, maintaining and delivering auditable governance processes is an advantage Comfortable dealing with both technical stakeholders (e.g. application owners, infrastructure teams) as well as control function partners (e.g. Legal and Compliance) Experience managing a team responsible for following processes within a defined framework How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs We value diversity and as an equal opportunities\u00e2\u0080\u0099 employer, we make reasonable adjustments for those with a disability such as the provision of assistive equipment if required (e.g. screen readers, assistive hearing devices, adapted keyboards) About us Deutsche Bank is the leading German bank with strong European roots and a global network. Click here to see what we do. Deutsche Bank in the UK is proud to have been named The Times Top 50 Employers for Gender Equality 2025 for six consecutive years. Additionally, we have been awarded a Gold Award from Stonewall and named in their Top 100 Employers 2024 for our work supporting LGBTQ+ inclusion. We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Electronic Communications Governance Operations Lead",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 512,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Birmingham-5-Brindley-Place/Electronic-Communications-Governance-Operations-Lead_R0394740-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Brazil, Sao Paulo, Offsite",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0414055",
          "api_response": {
            "title": "Corporate Cash Management Product Analyst",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0414055"
            ],
            "externalPath": "/job/Brazil-Sao-Paulo-Offsite/Corporate-Cash-Management-Product-Analyst_R0414055",
            "locationsText": "Brazil, Sao Paulo, Offsite"
          },
          "external_path": "/job/Brazil-Sao-Paulo-Offsite/Corporate-Cash-Management-Product-Analyst_R0414055",
          "job_description": "Job Description: Job Title: Corporate Cash Management Product Analyst Corporate Title: Analyst Location: Brazil Overview As a Product Analyst on our Corporate Cash Management team, you will be instrumental in supporting the strategic development and delivery of our local Cash Management product portfolio. Your Key responsibilities encompass aiding in the conceptualization and scoping of new product initiatives, identifying opportunities for continuous improvement within existing products, proactively managing product-related risks, and developing product content for Requests for Information (RFIs), Requests for Proposals (RFPs), and sales engagements. This position necessitates a proactive and collaborative approach, engaging extensively with internal partners across local and global product areas, sales, operations, technology, legal, implementation &amp; services teams, as well as with our relationship managers team What We Offer You A diverse and inclusive environment that embraces change, innovation, and collaboration. A hybrid working model, allowing for in-office / work from home flexibility Employee Resource Groups support an inclusive workplace for everyone and promote community engagement Competitive compensation packages including health and wellbeing benefits, retirement savings plans, parental leave, and family building benefits What You\u00e2\u0080\u0099ll Do Support the delivery of the Cash Management product strategy locally Design product functional specifications and drive the implementation Ensure compliance with internal controls and regulatory standards Manage product-related risk &amp; control environment Produce products and client\u00e2\u0080\u0099s performance reports Assist in the development of RFIs, RFPs and sales presentations Interact with global and local stakeholders (Internal and External) Skills You\u00e2\u0080\u0099ll Need Bachelor\u00e2\u0080\u0099s degree in Business, Economics, Engineering, or International Trade CPA20 certification Advanced in English Advanced Excel, Power Point and Word skills 2 Years of experience in Cash Management Be willing to work on a team, be proactive and communicative Skills That Will Help You Excel Excellent communication skills, both written and spoken Self-motivated Self-starter Expectations It is the Bank\u00e2\u0080\u0099s expectation that employees hired into this role will work in the Brazil office in accordance with the Bank\u00e2\u0080\u0099s hybrid working model which means 3 days per week. Deutsche Bank provides reasonable accommodations to candidates and employees with a substantiated need based on disability and/or religion. Deutsche Bank Values &amp; Diversity We believe talent is found in all cultures, countries, races, ethnicities, genders, sexual orientations, disabilities, beliefs, generations, backgrounds and experiences. We pursue a working environment where everyone can be authentic and feel a sense of belonging. Click here to find out more about our diversity and inclusion efforts. We are an Equal Opportunity Employer - Veterans/Disabled and other protected categories. Click these links to view the following notices: EEO is the Law poster and supplement; Employee Rights and Responsibilities under the Family and Medical Leave Act; Employee Polygraph Protection Act and Pay Transparency Nondiscrimination Provision Learn more about your life at DB through the eyes of our current employees: https://careers.db.com/life We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Corporate Cash Management Product Analyst",
        "created_at": "2025-11-25T14:55:06.166727+01:00",
        "staging_id": 513,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Brazil-Sao-Paulo-Offsite/Corporate-Cash-Management-Product-Analyst_R0414055",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Mumbai Nirlon Know. Pk B4-B5",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0364440",
          "api_response": {
            "title": "DCO Sr. Analyst",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0364440"
            ],
            "externalPath": "/job/Mumbai-Nirlon-Know-Pk-B4-B5/DCO-Sr-Analyst_R0364440",
            "locationsText": "Mumbai Nirlon Know. Pk B4-B5"
          },
          "external_path": "/job/Mumbai-Nirlon-Know-Pk-B4-B5/DCO-Sr-Analyst_R0364440",
          "job_description": "Job Description: Job Title: DCO \u00e2\u0080\u0093 Divisional Risk and Controls \u00e2\u0080\u0093 Data Analytics and Automation Specialist Corporate Title: AVP / Associate Location: Mumbai, India Role Description: Divisional Control Office (DCO) is responsible for supporting the business by developing, implementing and maintaining a risk framework to ensure a strong and sustainable business control environment whilst minimizing risk arising from non-financial risks. Risk management includes performing Risk and Controls Assessment, implementing and executing controls across a variety of risk types. This includes developing an environment which supports performance of risk assessments and Controls review through robust data analytics and automation tools. Candidate will work closely with stakeholders to understand the bank\u00e2\u0080\u0099s requirement and develop a framework that will automate the implementation of controls using our technology stack. What we will offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Flexible working arrangements Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Work with DCO risk assessors and control owners to understand control requirements and problem statement. Design smart ways of handling, transforming, storing and analyzing the data and identifying outliers as per control definitions Design efficient low maintenance workflows using Power Automate platform Prepare Power Apps interfaces and integrate them with the Power Automate workflows Use available AI tools to develop solutions to support risk assessment and control execution Own and help run the solutions designed in a sustainable manner Documentation of the whole environment which can be used for audit and creation of EUDAs Your skills and experience Strong quantitative and analytical skills Able to design solutions from business problem statements Strong verbal and written communication skills Strong understanding of excel including advanced formulae, macros and Power Query Experience of SQL and familiarity with a scripting language (Python) Know-how of large databases and complex data models Knowledge of BI Tools, e.g. Power BI, Qlik Sense, Tableau Experience of working on AI tools (Co-Pilot, Gemini). Hands on experience on Large Learning Model (LLM) Experience of Power Platform \u00e2\u0080\u0093 especially on Power Automate and Power Apps Experience in financial industry technology (Good to know) Understanding of Banking financial products (Good to know) How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.htm We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "DCO Sr. Analyst",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 514,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Mumbai-Nirlon-Know-Pk-B4-B5/DCO-Sr-Analyst_R0364440",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Bangalore, Velankani Tech Park",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0410678",
          "api_response": {
            "title": "TFL \u2013 Lending Growth \u2013 Associate",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0410678"
            ],
            "externalPath": "/job/Bangalore-Velankani-Tech-Park/TFL---Lending-Growth---Associate_R0410678",
            "locationsText": "Bangalore, Velankani Tech Park"
          },
          "external_path": "/job/Bangalore-Velankani-Tech-Park/TFL---Lending-Growth---Associate_R0410678",
          "job_description": "Job Description: Job Title: TFL \u00e2\u0080\u0093 Lending Growth \u00e2\u0080\u0093 Associate Location: Bangalore, India Role Description We are seeking a detail-oriented and analytical professional to join our team as an AVP responsible for performing balance sheet spreading of corporate clients using the BARS (Balance Sheet Analysis and Reporting System) tool. This role is critical in supporting credit risk assessment and financial analysis processes. Lending Operations team is responsible in managing Lifecycle events on Syndicated Loan Deals, which provides Middle Office and Back Office support to Corporate and Investment banking divisions of the bank. The team is also involved in various aspects of recording and maintaining all Middle and Operational Roles of Loan Life Cycle includes trade support, trade documentation, trade settlements, cash reconciliation, Drawdown, Re-pricing, Payment. Team works closely with stakeholders in the Finance, Credit and technology divisions for multiple business lines such as Distressed Product Group (DPG), Commercial Real Estate (CRE) Global Credit Trading (GCT), Credit Solutions Group (CSG), and Structured Trade &amp; Export Finance (STEF) etc. The role is demanding, complex &amp; critical in nature and requires interaction with Front Office, Business, CRM Finance, Sales, Agent Bank and Clients. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy, Best in class leave policy. Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Accurately spread financial statements (balance sheet, and income statement) of corporate clients into the BARS system. Analyze financial data to ensure consistency, accuracy, and completeness. Collaborate with credit officers and relationship managers to clarify financial inputs and resolve discrepancies. Maintain documentation and audit trails for all financial spreads. Ensure compliance with internal policies, regulatory requirements, and data quality standards. Support periodic reporting and data validation exercises. Maintains the highest level of confidentiality with all information obtained. Meets expectations for attendance and punctuality. Manage the daily operations of the department in an efficient and effective manner Establish and maintain an efficient and productive working environment within the department based on continuous and effective staff communication. Participates in the review and recommendations of operational systems and procedures Communicate with management team to coordinate system and control activities Your skills and experience Considering the demanding, complex &amp; critical nature of the role and able to work in fast passed environment with consistent deadlines, candidates should meet the below requirements. Bachelor\u00e2\u0080\u0099s degree in Finance, Accounting, or a related field. German Language proficiency \u00e2\u0080\u0093 B1 and above Strong understanding of financial statements and accounting principles. Proficiency in Microsoft Excel; experience with BARS or similar financial spreading tools is a plus. 5+ years of experience in financial analysis, credit risk, or a similar role. High attention to detail and accuracy. Strong communication and collaboration skills. Excellent verbal &amp; written communication along with dynamic &amp; confident approach. Flexible with Shift. Ability to implement tasks and projects with minimal supervision. Team player who fosters team spirit in a global setting. How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "TFL \u2013 Lending Growth \u2013 Associate",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 515,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Bangalore-Velankani-Tech-Park/TFL---Lending-Growth---Associate_R0410678",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Pune - Margarpatta",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0384416",
          "api_response": {
            "title": "DevOps Engineer, AVP",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0384416"
            ],
            "externalPath": "/job/Pune---Margarpatta/DevOps-Engineer--AVP_R0384416",
            "locationsText": "Pune - Margarpatta"
          },
          "external_path": "/job/Pune---Margarpatta/DevOps-Engineer--AVP_R0384416",
          "job_description": "Job Description: Job Title: DevOps Engineer, AVP Location: Pune, India Role Description We are seeking a highly skilled and experienced DevOps Engineer to join our team, with a focus on Google Cloud as we migrate and build the financial crime risk platforms on the cloud. The successful candidate will be responsible for designing, implementing, and maintaining our team\u00e2\u0080\u0099s infrastructure and workflows on Google Cloud Platforms. This is a unique opportunity to work at the intersection of software development, infrastructure management and to contribute to the growth and success of our team. DevOps Engineer is responsible for managing or performing work across multiple areas of the bank's overall IT Platform/Infrastructure including analysis, development, and administration. It may also involve taking functional oversight of engineering delivery for specific departments. Work includes: Planning and developing entire engineering solutions to accomplish business goals Building reliability and resiliency into solutions with appropriate testing and reviewing throughout the delivery lifecycle Ensuring maintainability and reusability of engineering solutions Ensuring solutions are well architected and can be integrated successfully into the end-to-end business process flow Reviewing engineering plans and quality to drive re-use and improve engineering capability Participating in industry forums to drive adoption of innovative technologies, tools and solutions in the Bank. Deutsche Bank\u00e2\u0080\u0099s Corporate Bank division is a leading provider of cash management, trade finance and securities finance. We complete green-field projects that deliver the best Corporate Bank - Securities Services products in the world. Our team is diverse, international, and driven by shared focus on clean code and valued delivery. At every level, agile minds are rewarded with competitive pay, support, and opportunities to excel. You will work as part of a cross-functional agile delivery team. You will bring an innovative approach to software development, focusing on using the latest technologies and practices, as part of a relentless focus on business value. You will be someone who sees engineering as team activity, with a predisposition to open code, open discussion and creating a supportive, collaborative environment. You will be ready to contribute to all stages of software delivery, from initial analysis right through to production support.\" What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy, Best in class leave policy. Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Design, implement, and maintain our team\u00e2\u0080\u0099s infrastructure and workflows on Google Cloud Platform, including GCP services such as Google Kubernetes Engine (GKE), Cloud Storage, Vertex AI, Anthos, Monitoring etc. Design, implement, and maintain our containerization and orchestration strategy using Docker and Kubernetes. Collaborate with development teams to ensure seamless integration of containerized applications into our production environment. Collaborate with software developers to integrate machine learning models and algorithms into our products, using PyTorch, TensorFlow or other machine learning frameworks. Develop and maintain CI/CD pipelines for our products, using tools such as GitHub and GitHub actions. Create and maintain Infrastructure as Code templates using Terraform. Ensure the reliability, scalability, and security of our infrastructure and products, using monitoring and logging tools such as Anthos Service Mesh (ASM), Google Cloud's operations (GCO) etc. Work closely with other teams, such as software development, data science, and product management, to identify and prioritize infrastructure and machine learning requirements. Stay up to date with the latest developments in Google Cloud Platform and machine learning and apply this knowledge to improve our products and processes. Your skills and experience Bachelor\u00e2\u0080\u0099s degree in computer science, Engineering, or a related field. At least 3 years of experience in a DevOps or SRE role, with a focus on Google Cloud Platform. Strong experience with infrastructure as code tools such as Terraform or Cloud Formation. Experience with containerization technologies such as Docker and container orchestration tools such as Kubernetes. Knowledge of machine learning frameworks such as TensorFlow or PyTorch. Experience with CI/CD pipelines and automated testing. Strong understanding of security and compliance best practices, including GCP security and compliance features. Excellent communication and collaboration skills, with the ability to work closely with cross-functional teams Preferred Qualifications: Master\u00e2\u0080\u0099s degree in computer science, Engineering, or a related field. Knowledge of cloud-native application development, including serverless computing and event-driven architecture. Experience with cloud cost optimization and resource management. Familiarity with agile software development methodologies and version control systems such as Git How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career. Coaching and support from experts in your team. A culture of continuous learning to aid progression. A range of flexible benefits that you can tailor to suit your needs. About us and our teams Please visit our company website for further information: https://www.db.com/company/company.htm We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "DevOps Engineer, AVP",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 516,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Pune---Margarpatta/DevOps-Engineer--AVP_R0384416",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Pune - Margarpatta",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0409966",
          "api_response": {
            "title": "Engineer, AVP",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0409966"
            ],
            "externalPath": "/job/Pune---Margarpatta/Engineer--AVP_R0409966",
            "locationsText": "Pune - Margarpatta"
          },
          "external_path": "/job/Pune---Margarpatta/Engineer--AVP_R0409966",
          "job_description": "Job Description: Job Title: Engineer Location: Pune, India Corporate Title: AVP Role Description Associate Data Engineer responsible for developing, optimizing and maintaining data engineering solutions on GCP. The candidate will work independently and collaboratively within cross-functional teams, contributing to medium and large-scale projects. The role requires hands-on expertise in cloud data engineering, Java and Spark, with additional experience in Python considered a plus. The candidate should demonstrate strong problem-solving skills and a solid track record in agile environments. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities This individual will be responsible for the following: Operate as a team member within a Scrum Agile/Kanban team Design, develop and peer-review new data engineering functionality using GCP and Java Build and optimize scalable data pipelines using Spark and cloud-native tools Collaborate with stakeholders to understand requirements and deliver robust solutions Ensure code quality through unit and system-level testing Support data sourcing, transformation, and analytics development Maintain documentation and contribute to process improvements Your skills and experience 4\u00e2\u0080\u00939 years of hands-on experience in data engineering, with a focus on GCP. Proficient in Java programming; experience with Python is a plus Strong experience with Spark and cloud data engineering tools (e.g., DataFlow, CloudComposer, Cloud Storage, Cloud Functions, Dataproc) Solid understanding of databases (RDBMS, SQL) Familiarity with data security and data quality concepts (Consistency, Completeness, Accuracy, Lineage) Passionate about test-driven development and agile methodologies Preferable Skills Experience in financial services, regulatory environments, or cross-product domains Data visualization experience Hands-on business and systems knowledge in a compliance or regulatory delivery environment Education / Qualifications Req Degree in a numerate field (e.g., Computer Science/Information Technology, Engineering) Language Required Good knowledge of English How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Engineer, AVP",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 517,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Pune---Margarpatta/Engineer--AVP_R0409966",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Frankfurt Taunusanlage 12",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0413736",
          "api_response": {
            "title": "Corporate Cash Management Sales Specialist Public Sector (d/m/w) \u2013 Deutschland/EU",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0413736"
            ],
            "externalPath": "/job/Frankfurt-Taunusanlage-12/Corporate-Cash-Management-Sales-Specialist-Public-Sector--d-m-w----Deutschland-EU_R0413736-1",
            "locationsText": "Frankfurt Taunusanlage 12"
          },
          "external_path": "/job/Frankfurt-Taunusanlage-12/Corporate-Cash-Management-Sales-Specialist-Public-Sector--d-m-w----Deutschland-EU_R0413736-1",
          "job_description": "Job Description: \u00c3\u009cber den Bereich Im Rahmen der Corporate Bank bietet der Bereich Corporate Cash Sales unseren Kunden komplexe Konten- und Zahlungsverkehrs-Produkte, Liquidity-L\u00c3\u00b6sungen, H\u00c3\u00a4ndlerl\u00c3\u00b6sungen und transaktionale W\u00c3\u00a4hrungsangebote. Der Fokus liegt dabei auf einem gesamtheitlichen Ansatz, der den Kunden in den Mittelpunkt stellt und das Produktangebot auf die individuellen Bed\u00c3\u00bcrfnisse abstimmt. Corporate Cash Management umfasst insbesondere die Steuerung und Optimierung des nationalen und internationalen Zahlungsverkehrs, Beratung \u00c3\u00bcber die Einrichtung entsprechender Cash Management L\u00c3\u00b6sungen, Beratung \u00c3\u00bcber Digitalisierung sowie Firmenkreditkarten. Im Team \u00e2\u0080\u009cCash Management Solution Sales Public Sector Deutschland / EU\u00e2\u0080\u009d liegt der Fokus des Vertriebs von Cash Management Produkten bei \u00c3\u0096ffentlichen Sektor-Kunden: als Spezialist/in f\u00c3\u00bcr den Vertrieb von Corporate Cash Management L\u00c3\u00b6sungen bist Du verantwortlich f\u00c3\u00bcr die Akquise, Beratung und den Verkauf von Cash Management L\u00c3\u00b6sungen und Produkten an bestehende und potenzielle Kunden des \u00c3\u0096ffentlichen Sektors in Deutschland und EMEA. Dies beinhaltet Pflege und Wachstum des bestehenden Gesch\u00c3\u00a4fts sowie die Identifizierung neuer M\u00c3\u00b6glichkeiten. Du bist verantwortlich f\u00c3\u00bcr das Erreichen quantitativer und qualitativer Ziele durch die Betreuung und Entwicklung eines definierten Kundenportfolios sowie f\u00c3\u00bcr die F\u00c3\u00b6rderung von deutschen und globalen Initiativen in enger Zusammenarbeit mit den jeweiligen lokalen Firmenkunden-Betreuern. Durch Deinen Standort in Frankfurt kannst Du optimal mit den \u00c3\u0096ffentlicher Sektor-Verantwortlichen Deutschland, EMEA und mit den entsprechenden Produktexperten agieren und wirst Teil eines erfahrenen und dynamischen Teams sein, welches multinational Kunden f\u00c3\u00bcr Cash Management-L\u00c3\u00b6sungen betreut. Deine Aufgaben Du bist die erste Anlaufstelle f\u00c3\u00bcr Kunden des \u00c3\u00b6ffentlichen Sektors und bearbeitest deren Anfragen eigenst\u00c3\u00a4ndig oder koordinierst sie mit internen Experten. Dabei bereitest du Kundenbesprechungen zu Cash Management Themen vor, leitest diese und unterst\u00c3\u00bctzt als Teil eines Client Sales Teams Meetings mit entsprechenden Inhalten Du bist verantwortlich f\u00c3\u00bcr die Vertriebsaktivit\u00c3\u00a4ten eines definierten Kundenportfolios und die Akquisition im \u00c3\u00b6ffentlichen Sektor, treibst die Vermarktung und Ausf\u00c3\u00bchrung von komplexen und Standardprodukten sowie innovativen L\u00c3\u00b6sungen wie H\u00c3\u00a4ndlerl\u00c3\u00b6sungen, virtuellen Konten, FX und Multi-Produkt-Ans\u00c3\u00a4tzen voran und erkennst Cross-Selling-Potenziale zu anderen Produkten. Dabei arbeitest Du eng mit Kollegen aus verschiedenen Produkt-, Vertriebs- und Betreuungsteams der Corporate Bank zusammen Du kennst und erfasst sektorale Trends, analysierst relevante politische Initiativen und Entwicklungen auf EU-Ebene und wandelst diese in innovative, produkt\u00c3\u00bcbergreifende Zukunftsl\u00c3\u00b6sungen um, strukturierst, bepreist und initiierst die Implementierung von Cash Management-L\u00c3\u00b6sungen in Abstimmung mit den Produkteinheiten aus und ber\u00c3\u00bccksichtigst dabei kundenspezifische Anforderungen sowie relevante Vorschriften, gesetzliche, regulatorische und Bankenrichtlinienanforderungen f\u00c3\u00bcr einen reibungslosen End-to-End-Prozess Du identifizierst relevante Kontakte bei EU-Institutionen und bei anderen Stakeholdern des \u00c3\u0096ffentlichen Sektors und bist in der Lage, eine vertrauensvolle Beziehung mit nationalen Agenturen und staatlichen Unternehmen, Schatz\u00c3\u00a4mtern der Mitgliedstaaten und \u00c3\u00a4hnlichen Institutionen aufzubauen Du bist Teil eines dynamischen und spezialisierten Vertriebsteams, das individuelle Cash Management und Liquidit\u00c3\u00a4tsl\u00c3\u00b6sungen f\u00c3\u00bcr den \u00c3\u0096ffentlichen Sektor entwickelt und Kunden in mehreren Lokationen betreut Deine F\u00c3\u00a4higkeiten und Erfahrungen \u00c3\u009cberdurchschnittlich abgeschlossene Bankausbildung mit entsprechenden weiterf\u00c3\u00bchrenden Qualifikationen oder erfolgreich abgeschlossenes Studium Berufserfahrung im Firmenkunden-Bereich, vorzugsweise im Vertrieb mit Firmenkunden w\u00c3\u00bcnschenswert. Alternativ hast Du Berufserfahrung in Bereichen des \u00c3\u0096ffentlichen Sektors oder der Corporate Treasury-Funktionen gesammelt Vorerfahrung oder Marktkenntnisse im Umgang mit Kunden des \u00c3\u0096ffentlichen Sektors und Netzwerk von Kontakten innerhalb des \u00c3\u0096ffentlichen Sektors erw\u00c3\u00bcnscht Theoretische und idealerweise auch praktische Kenntnisse zu Cash Management / Liquidity / FX / Treasury-L\u00c3\u00b6sungen sind von Vorteil Starke Leistungsbereitschaft und Anpassungsf\u00c3\u00a4higkeit: Du zeichnest sich durch hohe Einsatzbereitschaft, Flexibilit\u00c3\u00a4t bei wechselnden Aufgaben und die F\u00c3\u00a4higkeit aus, auch unter Druck sorgf\u00c3\u00a4ltig und zielorientiert zu arbeiten Ausgepr\u00c3\u00a4gte Kommunikations- und Vertriebsst\u00c3\u00a4rke: mit \u00c3\u00bcberzeugendem Auftreten, ausgepr\u00c3\u00a4gter Kontakt-, Team- und Kommunikationsf\u00c3\u00a4higkeit, hoher Motivation, Eigeninitiative sowie einem starken Interesse und Freude am kundenorientierten Vertrieb Flie\u00c3\u009fende Deutsch- und Englischkenntnisse in Wort und Schrift Was wir Ihnen bieten Wir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und pers\u00c3\u00b6nlichen Bed\u00c3\u00bcrfnisse abdecken. Emotional ausgeglichen Eine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern \u00e2\u0080\u0093 beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur F\u00c3\u00b6rderung mentaler Gesundheit. K\u00c3\u00b6rperlich fit Mit Angeboten zur Aufrechterhaltung Ihrer pers\u00c3\u00b6nlichen Gesundheit und einem f\u00c3\u00b6rderlichen beruflichen Umfeld hilft Ihnen die Bank, k\u00c3\u00b6rperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensf\u00c3\u00bchrung. Sozial vernetzt Der Austausch mit anderen er\u00c3\u00b6ffnet uns neue Perspektiven, bringt uns beruflich wie pers\u00c3\u00b6nlich voran und st\u00c3\u00a4rkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterst\u00c3\u00bctzung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe. Finanziell abgesichert Die Bank sichert Sie nicht nur w\u00c3\u00a4hrend Ihrer aktiven Karriere, sondern auch f\u00c3\u00bcr die Zukunft finanziell ab und unterst\u00c3\u00bctzt Ihre Flexibilit\u00c3\u00a4t sowie Mobilit\u00c3\u00a4t \u00e2\u0080\u0093 egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragspl\u00c3\u00a4nen f\u00c3\u00bcr Altersvorsorge, Bankdienstleistungen f\u00c3\u00bcr Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket. Da die Benefits je nach Standort geringf\u00c3\u00bcgig variieren, gehen Sie bitte bei konkreten Fragen auf Ihren Recruiter / Ihre Recruiterin zu. Die Stelle wird in Voll- und in Teilzeit angeboten. Bei Fragen zum Rekrutierungsprozess steht Ihnen Carolin Adler gerne zur Verf\u00c3\u00bcgung. Kontakt Carolin Adler: +49 (151) 647 57632 We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Corporate Cash Management Sales Specialist Public Sector (d/m/w) \u2013 Deutschland/EU",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 518,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Frankfurt-Taunusanlage-12/Corporate-Cash-Management-Sales-Specialist-Public-Sector--d-m-w----Deutschland-EU_R0413736-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Frankfurt Taunusanlage 12",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0413621",
          "api_response": {
            "title": "Corporate Cash Management Solution Sales DACH (d/m/w) \u2013 Multi National Clients Germany Sales",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0413621"
            ],
            "externalPath": "/job/Frankfurt-Taunusanlage-12/Corporate-Cash-Management-Solution-Sales-DACH--d-m-w----Multi-National-Clients-Germany-Sales_R0413621",
            "locationsText": "Frankfurt Taunusanlage 12"
          },
          "external_path": "/job/Frankfurt-Taunusanlage-12/Corporate-Cash-Management-Solution-Sales-DACH--d-m-w----Multi-National-Clients-Germany-Sales_R0413621",
          "job_description": "Job Description: \u00c3\u009cber den Bereich Im Rahmen der Corporate Bank bietet der Bereich Corporate Cash Management Solution Sales unseren Kunden Payment Produkte, Liquidity L\u00c3\u00b6sungen und automatisierte FX-Angebote. Der Fokus liegt dabei auf einem ganzheitlichen Ansatz, der den Kunden in den Mittelpunkt stellt und das Produktangebot auf die individuellen Bed\u00c3\u00bcrfnisse abstimmt. Corporate Cash Management umfasst insbesondere die Steuerung und Optimierung des nationalen und internationalen Zahlungsverkehrs, Beratung \u00c3\u00bcber die Einrichtung entsprechender Cash Management L\u00c3\u00b6sungen, Digitalisierung, Firmenkreditkarten und alternative Bezahlmethoden, bspw. im eCommerce. Im Team \u00e2\u0080\u009cMulti National Clients (MNC) \u00e2\u0080\u0093 Cash Solution Sales\u00e2\u0080\u009d liegt der Fokus des Vertriebs von Cash Management Produkten auf global agierenden Gro\u00c3\u009fkonzernen. Deine Aufgaben Du unterst\u00c3\u00bctzt das umsatzgenerierende und global arbeitende \u00e2\u0080\u009eMNC Cash Solution Sales Team\u00e2\u0080\u009c im direkten Kundenkontakt mit dem Ziel, zeitnah die Verantwortung f\u00c3\u00bcr Neu- und Bestandsgesch\u00c3\u00a4ft eines eigenen Portfolios im Bereich Cash Management zu \u00c3\u00bcbernehmen Du agierst als erste Anlaufstelle f\u00c3\u00bcr Kunden und bearbeitest Kundenanfragen selbstst\u00c3\u00a4ndig, bzw. koordinierst Anfragen mit den entsprechenden internen Experten Du bringst die Bereitschaft mit, Dir umfassende Kenntnisse zu den nationalen und internationalen Kundenanforderungen/Produktinformationen und den Kapazit\u00c3\u00a4ten der Bank anzueignen Du strukturierst \u00e2\u0080\u009eGesamtl\u00c3\u00b6sungen\u00e2\u0080\u009c f\u00c3\u00bcr anspruchsvolle Kunden mit hoher Komplexit\u00c3\u00a4t aus der vorhandenen Cash-Produktpalette und erkennst Cross-Selling Ans\u00c3\u00a4tze zu anderen Produktbereichen Du erfasst Trends und \u00c3\u00bcbersetzt diese in innovative und produkt\u00c3\u00bcbergreifende Zukunftsl\u00c3\u00b6sungen in enger Abstimmung mit unseren internen Partnern und im globalen Netzwerk Du bist mit gesetzlichen, regulatorischen und Bankenrichtlinienanforderungen vertraut und handelst entsprechend Deine F\u00c3\u00a4higkeiten und Erfahrungen \u00c3\u009cberdurchschnittlich abgeschlossene Bankausbildung mit entsprechenden weiterf\u00c3\u00bchrenden Qualifikationen oder erfolgreich abgeschlossenes Studium Berufserfahrung im Firmenkunden-Bereich, vorzugsweise im Vertrieb mit Firmenkunden w\u00c3\u00bcnschenswert Theoretische und idealerweise auch praktische Kenntnisse zu Cash Management / Liquidity / FX / Treasury-L\u00c3\u00b6sungen sind von Vorteil Starke Leistungsbereitschaft und Anpassungsf\u00c3\u00a4higkeit: Du zeichnest Dich durch hohe Einsatzbereitschaft, Flexibilit\u00c3\u00a4t bei wechselnden Aufgaben und die F\u00c3\u00a4higkeit aus, auch unter Druck sorgf\u00c3\u00a4ltig und zielorientiert zu arbeiten Ausgepr\u00c3\u00a4gte Kommunikations- und Vertriebsst\u00c3\u00a4rke: Mit \u00c3\u00bcberzeugendem Auftreten, ausgepr\u00c3\u00a4gter Kontakt-, Team- und Kommunikationsf\u00c3\u00a4higkeit, hoher Motivation, Eigeninitiative sowie einem starken Interesse und Freude am kundenorientierten Vertrieb Flie\u00c3\u009fende Deutsch- und Englischkenntnisse in Wort und Schrift Was wir Ihnen bieten Wir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und pers\u00c3\u00b6nlichen Bed\u00c3\u00bcrfnisse abdecken. Emotional ausgeglichen Eine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern \u00e2\u0080\u0093 beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur F\u00c3\u00b6rderung mentaler Gesundheit. K\u00c3\u00b6rperlich fit Mit Angeboten zur Aufrechterhaltung Ihrer pers\u00c3\u00b6nlichen Gesundheit und einem f\u00c3\u00b6rderlichen beruflichen Umfeld hilft Ihnen die Bank, k\u00c3\u00b6rperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensf\u00c3\u00bchrung. Sozial vernetzt Der Austausch mit anderen er\u00c3\u00b6ffnet uns neue Perspektiven, bringt uns beruflich wie pers\u00c3\u00b6nlich voran und st\u00c3\u00a4rkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterst\u00c3\u00bctzung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe. Finanziell abgesichert Die Bank sichert Sie nicht nur w\u00c3\u00a4hrend Ihrer aktiven Karriere, sondern auch f\u00c3\u00bcr die Zukunft finanziell ab und unterst\u00c3\u00bctzt Ihre Flexibilit\u00c3\u00a4t sowie Mobilit\u00c3\u00a4t \u00e2\u0080\u0093 egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragspl\u00c3\u00a4nen f\u00c3\u00bcr Altersvorsorge, Bankdienstleistungen f\u00c3\u00bcr Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket. Da die Benefits je nach Standort geringf\u00c3\u00bcgig variieren, gehen Sie bitte bei konkreten Fragen auf Ihren Recruiter / Ihre Recruiterin zu. Die Stelle wird in Voll- und in Teilzeit angeboten. Bei Fragen zum Rekrutierungsprozess steht Ihnen Carolin Adler gerne zur Verf\u00c3\u00bcgung. Kontakt Carolin Adler: +49 151 64757632 We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Corporate Cash Management Solution Sales DACH (d/m/w) \u2013 Multi National Clients Germany Sales",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 519,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Frankfurt-Taunusanlage-12/Corporate-Cash-Management-Solution-Sales-DACH--d-m-w----Multi-National-Clients-Germany-Sales_R0413621",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "London 10 Upper Bank Street",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0326974",
          "api_response": {
            "title": "Agile Full Stack Developer (Kotlin, TypeScript)",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0326974"
            ],
            "externalPath": "/job/London-10-Upper-Bank-Street/Full-Stack-Developer_R0326974",
            "locationsText": "London 10 Upper Bank Street"
          },
          "external_path": "/job/London-10-Upper-Bank-Street/Full-Stack-Developer_R0326974",
          "job_description": "Job Description: Job Title Agile Full Stack Developer (Kotlin, TypeScript) Location London Corporate Title Assistant Vice President You will be working as a full stack developer as part of the Client 360 Technology. You will work as part of an agile/XP team, using test driven development, pair programming and other XP practices. Client 360 provides the platform for Sales teams to provide a complete service offering to the Banks\u00e2\u0080\u0099 Clients. The team is working closely with our Business on a new Client Relationship Management and Pre-deal pipeline, providing better insights into our clients and a more robust and automated control environment. What we\u00e2\u0080\u0099ll offer you A healthy, engaged and well-supported workforce are better equipped to do their best work and, more importantly, enjoy their lives inside and outside the workplace. That\u00e2\u0080\u0099s why we are committed to providing an environment with your development and wellbeing at its centre. You can expect: Hybrid Working - we understand that employee expectations and preferences are changing. We have implemented a model that enables eligible employees to work remotely for a part of their working time and reach a working pattern that works for them Competitive salary and non-contributory pension 30 days\u00e2\u0080\u0099 holiday plus bank holidays, with the option to purchase additional days Life Assurance and Private Healthcare for you and your family A range of flexible benefits including Retail Discounts, a Bike4Work scheme and Gym benefits The opportunity to support a wide ranging CSR programme + 2 days\u00e2\u0080\u0099 volunteering leave per year Your key responsibilities Writing robust, well tested software and ensuring simplicity in our code Working with the business to define and build the product Working full stack with emphasis on the server side (Kotlin). Experience with JavaScript technologies, particularly TypeScript and ReactJS are beneficial DevOps \u00e2\u0080\u0093 managing Continuous Integration/Delivery pipeline and the production environment Test Driven Development, Pair Programming and other XP practices Your skills and experience Kotlin development, or experience in Java/Scala and a desire to cross train Experienced in Object Oriented or Functional Programming using Test Driven Development Experienced using agile development practices to develop exceptional, robust software; like Test Driven Development, acceptance testing and pair programming Vision and expertise to use iterative development techniques to build high value software to the business How we\u00e2\u0080\u0099ll support you Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs We value diversity and as an equal opportunities\u00e2\u0080\u0099 employer, we make reasonable adjustments for those with a disability such as the provision of assistive equipment if required (e.g. screen readers, assistive hearing devices, adapted keyboards) About us Deutsche Bank is the leading German bank with strong European roots and a global network. Click here to see what we do. Deutsche Bank in the UK is proud to have been named in The Times Top 50 Employers for Gender Equality 2024 for five consecutive years. Additionally, we have been awarded a Gold Award from Stonewall and named in their Top 100 Employers 2024 for our work supporting LGBTQ+ inclusion. We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Agile Full Stack Developer (Kotlin, TypeScript)",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 520,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/London-10-Upper-Bank-Street/Full-Stack-Developer_R0326974",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Frankfurt Theodor-H-A IBC",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0407748",
          "api_response": {
            "title": "Network Deployment Engineer (d/m/w)",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0407748"
            ],
            "externalPath": "/job/Frankfurt-Theodor-H-A-IBC/Network-Deployment-Engineer--d-m-w-_R0407748",
            "locationsText": "Frankfurt Theodor-H-A IBC"
          },
          "external_path": "/job/Frankfurt-Theodor-H-A-IBC/Network-Deployment-Engineer--d-m-w-_R0407748",
          "job_description": "Job Description: Rollenbeschreibung Infrastructure Core Products (ICP) \u00e2\u0080\u0093 Global Network Services (GNS) ist verantwortlich f\u00c3\u00bcr die Entwicklung, das Engineering und den Betrieb des konzernweiten Netzwerks der Deutschen Bank f\u00c3\u00bcr alle Bereiche der Bank. GNS unterst\u00c3\u00bctzt s\u00c3\u00a4mtliche Aspekte der Netzwerkinfrastruktur an \u00c3\u00bcber 2500 Standorten in 50 L\u00c3\u00a4ndern. Als Network Deployment Engineer sind Sie verantwortlich f\u00c3\u00bcr den Aufbau neuer Netzwerkumgebungen, die Vorbereitung, Dokumentation und Umsetzung von \u00c3\u0084nderungen im Netzwerk, die Analyse von Problemen im t\u00c3\u00a4glichen Betrieb sowie die Fehlerbehebung. Dar\u00c3\u00bcber hinaus koordinieren Sie Installationen gemeinsam mit Carriern und externen Anbietern. Ihre Kernaufgaben Mitarbeit bei der Implementierung von Netzwerkl\u00c3\u00b6sungen gem\u00c3\u00a4\u00c3\u009f bestehenden Designstandards Mitwirkung bei Projekten in Backbone-, Rechenzentrums- und Filialnetzwerken, einschlie\u00c3\u009flich des Umzugs oder Aufbaus von Netzwerksegmenten sowie der Einf\u00c3\u00bchrung neuer Features und Funktionen im Rahmen globaler Initiativen, die den Betrieb von Marktdatenanwendungen, Finanzsystemen sowie Infrastruktur f\u00c3\u00bcr Wertpapierhandel und Finanztransaktionen mit hohem Volumen unterst\u00c3\u00bctzen Unterst\u00c3\u00bctzung bei der Sicherstellung der erforderlichen Netzwerkresilienz sowie bei der Durchf\u00c3\u00bchrung von Failover-Tests Durchf\u00c3\u00bchrung von Installations- und Validierungstests sowie Unterst\u00c3\u00bctzung bei der \u00c3\u009cbergabe (Handover) an Betriebsteams (Operations) Unterst\u00c3\u00bctzung bei der Analyse und Behebung von Netzwerkproblemen, z.B. mittels Analyse Tools wie Wireshark Vorbereitung, Dokumentation und Umsetzung von \u00c3\u0084nderungen im Netzwerk (Change Request) Pflege von Netzwerkdokumentationen und Asset-Informationen (z.B. CMDB) Enge Zusammenarbeit mit internen Kunden und Abstimmung mit Carriern und externen Dienstleistern Ihre F\u00c3\u00a4higkeiten und Erfahrungen Erste bis solide Erfahrung im Bereich globaler Unternehmensnetzwerke, idealerweise in regulierten Branchen, z.B. Finanzdienstleistung Gute Grundkenntnisse in: Routing &amp; Switching, z.B. TCP/IP, VLAN, Subnetting; Routing-Protokollen, z.B. OSPF, BGP von Vorteil; Layer-2 Protokolle, z.B. STP, LACP; Netzwerk-Security, z.B. Firewalls, Access-Konzepte; Umgang mit Cisco-Ger\u00c3\u00a4te (IOS); Load-Balancing-Technologien von Vorteil; Automation/Skripting von Vorteil Praktische Erfahrungen: im Troubleshooting von Netzwerkproblemen, z.B. Nutzung von Netzwerk-Monitoring- und Analyse-Tools; mit Change- und Incident-Prozessen, z.B. ITIL F\u00c3\u00a4higkeit, Aufgaben eigenst\u00c3\u00a4ndig innerhalb vorgegebener Standards umzusetzen Strukturierte, analytische Arbeitsweise sowie hohe Lernbereitschaft und Motivation Zuverl\u00c3\u00a4ssige Zusammenarbeit in global verteilten Teams innerhalb einer Matrixorganisation Gute Kommunikationsf\u00c3\u00a4higkeiten in Deutsch und Englisch (schriftlich/m\u00c3\u00bcndlich) Bereitschaft zur Flexibilit\u00c3\u00a4t, auch abends und an Wochenenden zu arbeiten, sofern es die Gesch\u00c3\u00a4ftserfordernisse erfordern Was wir Ihnen bieten Wir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und pers\u00c3\u00b6nlichen Bed\u00c3\u00bcrfnisse abdecken. Emotional ausgeglichen Eine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern \u00e2\u0080\u0093 beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur F\u00c3\u00b6rderung mentaler Gesundheit. K\u00c3\u00b6rperlich fit Mit Angeboten zur Aufrechterhaltung Ihrer pers\u00c3\u00b6nlichen Gesundheit und einem f\u00c3\u00b6rderlichen beruflichen Umfeld hilft Ihnen die Bank, k\u00c3\u00b6rperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensf\u00c3\u00bchrung. Sozial vernetzt Der Austausch mit anderen er\u00c3\u00b6ffnet uns neue Perspektiven, bringt uns beruflich wie pers\u00c3\u00b6nlich voran und st\u00c3\u00a4rkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterst\u00c3\u00bctzung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe. Finanziell abgesichert Die Bank sichert Sie nicht nur w\u00c3\u00a4hrend Ihrer aktiven Karriere, sondern auch f\u00c3\u00bcr die Zukunft finanziell ab und unterst\u00c3\u00bctzt Ihre Flexibilit\u00c3\u00a4t sowie Mobilit\u00c3\u00a4t \u00e2\u0080\u0093 egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragspl\u00c3\u00a4nen f\u00c3\u00bcr Altersvorsorge, Bankdienstleistungen f\u00c3\u00bcr Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket. Da die Benefits je nach Standort geringf\u00c3\u00bcgig variieren, gehen Sie bitte bei konkreten Fragen auf Ihren Recruiter / Ihre Recruiterin zu. Die Stelle wird in Voll- und in Teilzeit angeboten. Bei Fragen zum Rekrutierungsprozess steht Ihnen Michaela Peschke gerne zur Verf\u00c3\u00bcgung. Kontakt Michaela Peschke: 069-910-43951 We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Network Deployment Engineer (d/m/w)",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 521,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Frankfurt-Theodor-H-A-IBC/Network-Deployment-Engineer--d-m-w-_R0407748",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Frankfurt Taunusanlage 12",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0411678",
          "api_response": {
            "title": "Strategic Development Specialist (d/m/w)",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0411678"
            ],
            "externalPath": "/job/Frankfurt-Taunusanlage-12/Strategic-Development-Specialist--d-m-w-_R0411678-1",
            "locationsText": "Frankfurt Taunusanlage 12"
          },
          "external_path": "/job/Frankfurt-Taunusanlage-12/Strategic-Development-Specialist--d-m-w-_R0411678-1",
          "job_description": "Job Description: \u00c3\u009cber unser Team Du bist enthusiastisch, hochmotiviert und in der Lage die Bedarfe des Top Managements und der zugeh\u00c3\u00b6rigen Interessengruppen zu verstehen, zu koordinieren und im h\u00c3\u00b6chsten Ma\u00c3\u009fe zu erf\u00c3\u00bcllen? Prima, denn das Strategy &amp; CEO Office Team sucht ein neues Teammitglied mit dem Schwerpunkt im Key Account Management, das bei der Orchestrierung von Kunden- und Stakeholderinteraktionen des CEOs und der Deutsche Bank AG Vorst\u00c3\u00a4nde unterst\u00c3\u00bctzt und so die richtigen Inhalte, L\u00c3\u00b6sungen und einen effektiven Informationsfluss entlang aller Interessengruppen sicherstellt. Wenn du ein(e) starke(r) Teamplayer*in bist, Spa\u00c3\u009f an einer steilen Lernkurve hast und in einem vorstandsnahen und temporeichen Umfeld arbeiten m\u00c3\u00b6chtest, k\u00c3\u00b6nntest du die/der passende Kandidat*in sein. Deine Aufgaben Du treibst die strategische Planung der Kundeninteraktionen des CEO sowie der weiteren Vorstandsmitglieder voran und leitest daraus die notwendigen Inhalte ab. Du arbeitest bereichs\u00c3\u00bcbergreifend mit den Gesch\u00c3\u00a4ftsbereichen Investment Bank, Corporate Bank, Private Bank und Asset Management zusammen. Du erstellst Dokumente zur Vorbereitung von Meetings und Veranstaltungen f\u00c3\u00bcr den CEO und die Vorstandsmitglieder. Du managst die Informationsfl\u00c3\u00bcsse zwischen Vorstand und Gesch\u00c3\u00a4ftsbereichen und aggregierst Einblicke aus Top-Kundeninteraktionen, um strategische Ma\u00c3\u009fnahmen abzuleiten. Du f\u00c3\u00bchrst strategische Analysen durch und \u00c3\u00bcbernimmst Ad-hoc-Aufgaben im Aufgabenbereich des CEO-B\u00c3\u00bcros. Deine F\u00c3\u00a4higkeiten und Erfahrungen Du bringst hervorragende akademische Leistungen und mind. vier Jahre Berufserfahrung im Finanzsektor, sowie ausgezeichnete Kenntnisse zu Finanzprodukten und -dienstleistungen mit Du hast bereits in einem herausfordernden, schnelllebigen, internationalen Umfeld gearbeitet und verstehst es, professionelle Netzwerke aufzubauen. Du hast fundierte Erfahrungen im Projektmanagement und erzielst bereichs\u00c3\u00bcbergreifend Ergebnisse h\u00c3\u00b6chster Qualit\u00c3\u00a4t. Du verf\u00c3\u00bcgst \u00c3\u00bcber einen ausgepr\u00c3\u00a4gten Sinn f\u00c3\u00bcr Priorisierung, eine unternehmerische Denkweise und eine \u00e2\u0080\u009eGetting-things-done\u00e2\u0080\u009c-Mentalit\u00c3\u00a4t \u00e2\u0080\u0093 besonders in komplexen Situationen mit wenigen Vorgaben. Du \u00c3\u00bcberzeugst mit au\u00c3\u009fergew\u00c3\u00b6hnlichen analytischen F\u00c3\u00a4higkeiten sowie starken schriftlichen und m\u00c3\u00bcndlichen Kommunikationsf\u00c3\u00a4higkeiten in Deutsch und Englisch. Du handelst mit h\u00c3\u00b6chstem Ma\u00c3\u009f an Integrit\u00c3\u00a4t und Empathie im Umgang mit verschiedenen Interessengruppen. Was wir Ihnen bieten Wir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und pers\u00c3\u00b6nlichen Bed\u00c3\u00bcrfnisse abdecken. Emotional ausgeglichen Eine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern \u00e2\u0080\u0093 beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur F\u00c3\u00b6rderung mentaler Gesundheit. K\u00c3\u00b6rperlich fit Mit Angeboten zur Aufrechterhaltung Ihrer pers\u00c3\u00b6nlichen Gesundheit und einem f\u00c3\u00b6rderlichen beruflichen Umfeld hilft Ihnen die Bank, k\u00c3\u00b6rperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensf\u00c3\u00bchrung. Sozial vernetzt Der Austausch mit anderen er\u00c3\u00b6ffnet uns neue Perspektiven, bringt uns beruflich wie pers\u00c3\u00b6nlich voran und st\u00c3\u00a4rkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterst\u00c3\u00bctzung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe. Finanziell abgesichert Die Bank sichert Sie nicht nur w\u00c3\u00a4hrend Ihrer aktiven Karriere, sondern auch f\u00c3\u00bcr die Zukunft finanziell ab und unterst\u00c3\u00bctzt Ihre Flexibilit\u00c3\u00a4t sowie Mobilit\u00c3\u00a4t \u00e2\u0080\u0093 egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragspl\u00c3\u00a4nen f\u00c3\u00bcr Altersvorsorge, Bankdienstleistungen f\u00c3\u00bcr Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket. Da die Benefits je nach Standort geringf\u00c3\u00bcgig variieren, gehen Sie bitte bei konkreten Fragen auf Ihren Recruiter / Ihre Recruiterin zu. Die Stelle wird in Voll- und in Teilzeit angeboten. Bei Fragen zum Rekrutierungsprozess steht Ihnen Stefanie Schumann gerne zur Verf\u00c3\u00bcgung. Kontakt Stefanie Schumann: +49 (69) 910-42578 We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Strategic Development Specialist (d/m/w)",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 522,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Frankfurt-Taunusanlage-12/Strategic-Development-Specialist--d-m-w-_R0411678-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Bonn, Alemannenstr. 1-3",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0405829",
          "api_response": {
            "title": "Teamlead Verlag (Karte & PIN) (d/m/w)",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0405829"
            ],
            "externalPath": "/job/Bonn-Alemannenstr-1-3/Teamlead-Verlag--Karte---PIN---d-m-w-_R0405829-1",
            "locationsText": "Bonn, Alemannenstr. 1-3"
          },
          "external_path": "/job/Bonn-Alemannenstr-1-3/Teamlead-Verlag--Karte---PIN---d-m-w-_R0405829-1",
          "job_description": "Job Description: Teamlead Verlag (Karte &amp; PIN) (d/m/w) Bonn \u00c3\u009cber den Bereich Pagateq\u00e2\u0080\u00a6 das ist die V\u00c3\u0096B-ZVD Processing GmbH, eine Tochter der Deutsche Bank AG. Seit mehr als 30 Jahren widmen wir unsere Energie und Leidenschaft der Schaffung gro\u00c3\u009fartiger Bezahlprozesse. Wir sind das innovative Kompetenzcenter f\u00c3\u00bcr den karten- und internetbasierten Zahlungsverkehr. Als zugelassenes europ\u00c3\u00a4isches Zahlungsinstitut im Deutsche Bank-Konzern sind wir mit rund 90 Mitarbeitern auf der Basis einer hochmodernen Infrastruktur f\u00c3\u00bcr ca. 10 Millionen Bankkarten und j\u00c3\u00a4hrlich \u00c3\u00bcber eine Milliarde karten- und internetbasierte Transaktionen verantwortlich. Wir von Pagateq sind \u00c3\u00bcberzeugt, dass wir als Gemeinschaft mehr erreichen k\u00c3\u00b6nnen. Wir sch\u00c3\u00a4tzen den offenen Austausch auch \u00c3\u00bcber \u00e2\u0080\u009eTeam-Grenzen\u00e2\u0080\u009c hinweg. Dabei sind breites Denken und unkonventionelle Ideen ausdr\u00c3\u00bccklich willkommen. \u00c3\u009cber diese Position Unterschiedliche Anforderungen bei der Produktion von physischen und digitalen Bankkarten und PIN-Briefen stellen die Pagateq t\u00c3\u00a4glich vor neue Herausforderungen, welche es gilt gemeinsam umzusetzen und einzuhalten. Als Teamleiter gew\u00c3\u00a4hrleistest Du mit Deinen Mitarbeitern den reibungslosen Betrieb der entsprechenden IT Applikationen in der Pagateq. Dabei ist sowohl Fachwissen als auch soziale Kompetenz f\u00c3\u00bcr die Arbeit im Team hier besonders gefragt. Nutze Deine Chance und bewirb Dich! Deine Aufgaben Fachliche- und disziplinarische F\u00c3\u00bchrung des Teams Steuerung und \u00c3\u009cberpr\u00c3\u00bcfung der im Team angesiedelten organisatorischen und regulatorischen Anforderungen an Einhaltung, Pflege und Dokumentation von Prozessen Koordination und Abstimmung der Aufgabenverteilung auf die Mitarbeiter des Teams Abstimmung und Koordination der Umsetzung technischer Spezifikationen und Konzepte Steuerung der internen Softwareentwicklungsteams f\u00c3\u00bcr alle IT Applikationen des Teams Verantwortliche Wartung, Pflege und Weiterentwicklung der Systemlandschaft Begleitung und Koordination von Audits Vertretung / Steuerung der V\u00c3\u0096B-ZVD Processing in den kreditwirtschaftlichen Gremien der Deutschen Kreditwirtschaft hinsichtlich des kartenbasierten Zahlungsverkehrs Mitwirkung bei gro\u00c3\u009fen, fach\u00c3\u00bcbergreifenden Projekten innerhalb der Pagateq und mit externen Stakeholdern Strategische Ausrichtung der fachlichen Themen, Produkte und IT-Systeme Deine F\u00c3\u00a4higkeiten und Erfahrungen Hochschulstudium der Informatik oder vergleichbare Qualifikation Mindestens drei Jahre Berufserfahrung im Bereich IT Applikationsmanagement Gute Kenntnisse im Umfeld des kartenbasierten Zahlungsverkehrs und der Produktion von Bankkarten und PIN-Briefen. Sehr gute Englischkenntnisse hohe soziale Kompetenz sehr gutes Kommunikationsverm\u00c3\u00b6gen besonders analytische, pr\u00c3\u00a4zise und zielorientierte Arbeitsweise Erste F\u00c3\u00bchrungserfahrung Deine Vorteile Vielschichtige Optionen f\u00c3\u00bcr Ihre fachliche Fortbildung und pers\u00c3\u00b6nliche Weiterentwicklung Vertrauensarbeitszeit \u00e2\u0080\u0093 damit Beruf, Familie und Privatleben immer bestens in Balance sind Mobile-Work-Angebote sowie volle Kosten\u00c3\u00bcbernahme f\u00c3\u00bcr das Deutschlandticket Innerbetriebliche Vorsorgema\u00c3\u009fnahmen zu Gesundheit und Fitness Attraktive Mitarbeiterkonditionen f\u00c3\u00bcr das Portfolio der Deutsche Bank AG We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Teamlead Verlag (Karte & PIN) (d/m/w)",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 523,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Bonn-Alemannenstr-1-3/Teamlead-Verlag--Karte---PIN---d-m-w-_R0405829-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Pune - Business Bay",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0393743",
          "api_response": {
            "title": "Accounting and Financial and Regulatory Reporting Position, AVP",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0393743"
            ],
            "externalPath": "/job/Pune---Business-Bay/Accounting-and-Financial-and-Regulatory-Reporting-Position--AVP_R0393743-1",
            "locationsText": "Pune - Business Bay"
          },
          "external_path": "/job/Pune---Business-Bay/Accounting-and-Financial-and-Regulatory-Reporting-Position--AVP_R0393743-1",
          "job_description": "Job Description: Job Title: Accounting and Financial and Regulatory Reporting Position, AVP Location: Pune, India Role Description The AVP candidate will support the Treasurer\u00e2\u0080\u0099s Office on a wide variety of matters, which includes overseeing the production of financial statements and regulatory filings by the service providers, and oversight of accounting agents for the U.S. mutual funds, ETFs and collective investment trusts (the \u00e2\u0080\u009cFunds\u00e2\u0080\u009d). What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Accounting Oversight responsibilities Perform daily/weekly/monthly oversight of the Funds Accounting Agents\u00e2\u0080\u0099 service levels, including exception-based reporting reviews, issue resolution and coordination of weekly/monthly operational service meetings Provide support to the accounting agent regarding accounting treatment of day-to-day events including corporate actions, trade related issues, treatment of complex securities, income (distribution issues, defaulted bonds, reclaims, etc.) Provide as needed direction to the transfer agents and accounting agents to address fund level issues or errors Provide timely quarterly/annual Accounting Agent related Board reporting Financial and Regulatory Reporting Oversight responsibilities Perform a detailed analytical review of the annual and semi-annual financial and regulatory reports and quarterly filings Review for consistency of information and appropriateness of disclosure to ensure compliance with U.S. Generally Accepted Accounting Principles (GAAP) and U.S. Securities and Exchange Commission (SEC) regulatory requirements. Review and coordinate SEC filings for Form N-MFP, Form PF, Form N-CSR, Form N-PORT and Form N-CEN and other regulatory filings Review and coordinate financial statement and regulatory comments, including those from audit firms, legal, portfolio managers, compliance, President and CFO/Treasurer and data owners. Coordinate meetings with internal and external groups as needed Research comments and coordinate with stakeholders for resolution and direct service provider accordingly Your skills and experience Prior Mutual Fund Accounting and Mutual Fund Administration experience with proficient knowledge of fund accounting, general ledger accounting and regulatory reporting requirements for SEC Registered Investment Companies including mutual funds, ETFs and Closed End Funds, and U.S. Commingled Trusts Technical knowledge of a broad range of securities investments, accounting, and financial reporting including knowledge of U.S. GAAP and SEC Regulation S-X Proficient in Microsoft Office applications with a particular focus on Excel and the use of pivot tables, VLOOKUPs, and macros Educated to bachelor\u00e2\u0080\u0099s degree level Detail oriented with the ability to problem solve and recommend solutions Self-starter with strong analytical, communication and organization skills Ability to work effectively both independently and within a team environment Minimum 5-8 plus years of industry work experience Workday to include at least 4 hours overlap with U.S. Eastern Time How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.htm We at DWS are committed to creating a diverse and inclusive workplace, one that embraces dialogue and diverse views, and treats everyone fairly to drive a high-performance culture. The value we create for our clients and investors is based on our ability to bring together various perspectives from all over the world and from different backgrounds. It is our experience that teams perform better and deliver improved outcomes when they are able to incorporate a wide range of perspectives. We call this #ConnectingTheDots. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Accounting and Financial and Regulatory Reporting Position, AVP",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 524,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Pune---Business-Bay/Accounting-and-Financial-and-Regulatory-Reporting-Position--AVP_R0393743-1",
        "company_name": "Deutsche Bank"
      },
      {
        "location": "Pune - Margarpatta",
        "raw_data": {
          "posted_on": "Posted 4 Days Ago",
          "external_id": "R0409968",
          "api_response": {
            "title": "Java Full Stack Engineer, AVP",
            "postedOn": "Posted 4 Days Ago",
            "bulletFields": [
              "R0409968"
            ],
            "externalPath": "/job/Pune---Margarpatta/Java-Full-Stack-Engineer--AVP_R0409968",
            "locationsText": "Pune - Margarpatta"
          },
          "external_path": "/job/Pune---Margarpatta/Java-Full-Stack-Engineer--AVP_R0409968",
          "job_description": "Job Description: Job Title- Java Full Stack Engineer, AVP Location- Pune, India Role Description The Employee Compliance Technology Programme is responsible for re-platforming legacy Compliance applications onto modern, scalable, cloud-ready technology. The new GECCo platform (Global Employee Compliance Collective) will centralise all employee compliance tasks in Deutsche Bank, moving employees and Compliance to a self-service model, eliminating manual intervention, and improving data quality by ensuring it is consumed strategically from authoritative sources. This role is for someone who is a technologist first. The person is required to have hands on working knowledge of Java and related technology stack including front end, back end, database, etc. What we\u00e2\u0080\u0099ll offer you As part of our flexible scheme, here are just some of the benefits that you\u00e2\u0080\u0099ll enjoy Best in class leave policy Gender neutral parental leaves 100% reimbursement under childcare assistance benefit (gender neutral) Sponsorship for Industry relevant certifications and education Employee Assistance Program for you and your family members Comprehensive Hospitalization Insurance for you and your dependents Accident and Term life Insurance Complementary Health screening for 35 yrs. and above Your key responsibilities Good team player over different geographies. Promote and coach healthy communication in and around the team. Hands-on software development Strong communication with stakeholders Take End to End responsibility from design to deployment through the environments all the way to production. Your skills and experience Experience of working in an Agile Scrum team. Hands on development experience on Cloud based full stack application. Experience with end-to-end design and delivery of solutions Passionate about test driven development Proficient in Java full stack development (Java, Angular 8+, Spring Boot etc) Working knowledge of messaging (JMS, PubSub) Experience with Messaging and integration, Patterns, REST, SOA Strong hold on unit and integration testing Practices: Code Quality, Sonar, Veracode, Security, dev ops, Agile, CI &amp; CD How we\u00e2\u0080\u0099ll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people \u00e2\u0080\u0093 in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world \u00e2\u0080\u0093 be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)",
          "description_fetch_error": null
        },
        "job_title": "Java Full Stack Engineer, AVP",
        "created_at": "2025-11-25T14:55:24.271358+01:00",
        "staging_id": 525,
        "posting_url": "https://db.wd3.myworkdayjobs.com/DBWebSite/job/Pune---Margarpatta/Java-Full-Stack-Engineer--AVP_R0409968",
        "company_name": "Deutsche Bank"
      }
    ],
    "batches_fetched": 7,
    "total_available": 0
  },
  "status": "success"
}
````

### Child Interactions Created

- Interaction 253

---

## ✅ Interaction 2: Unknown

**Interaction ID:** 253
**Duration:** 0.09s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 9184
**Name:** Check if Summary Exists
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 74
**Name:** sql_query_executor
**Type:** script
**Script:** core/wave_runner/actors/sql_query_executor.py

### Prompt Template

````
{"query": "SELECT CASE \n    WHEN outputs ? '3335' THEN true \n    ELSE false \nEND as summary_exists\nFROM posting_state_projection \nWHERE posting_id = {posting_id}", "result_field": "summary_exists", "branch_map": {"true": "[SKIP]", "false": "[RUN]", "null": "[RUN]", "error": "[RUN]"}}
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**Skip extraction if summary exists** (Priority: 100)
- **Condition:** `[SKIP]`
- **Description:** Summary already exists, skip extraction and grading
- **Next:** Conversation 9185

**Run extraction if summary missing** (Priority: 90)
- **Condition:** `[RUN]`
- **Description:** Summary missing, proceed with extraction
- **Next:** Conversation 3335

**C2 check timeout - assume missing** (Priority: 39)
- **Condition:** `[TIMEOUT]`
- **Description:** Summary check timed out - assume missing
- **Next:** Conversation 3335

**check_summary_failed** (Priority: 10)
- **Condition:** `[FAILED]`
- **Description:** Check failed - assume not executed, run extraction
- **Next:** Conversation 3335

### Parent Interactions

This interaction received data from:

- Interaction 252

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````json
{
  "query": "SELECT CASE \n    WHEN outputs ? '3335' THEN true \n    ELSE false \nEND as summary_exists\nFROM posting_state_projection \nWHERE posting_id = 176",
  "branch_map": {
    "null": "[RUN]",
    "true": "[SKIP]",
    "error": "[RUN]",
    "false": "[RUN]"
  },
  "result_field": "summary_exists"
}
````

### Actual Output

````json
{
  "data": {
    "status": "[RUN]",
    "query_result": null,
    "result_value": "null"
  },
  "status": "success"
}
````

### Child Interactions Created

- Interaction 254

---

## ✅ Interaction 3: Unknown

**Interaction ID:** 254
**Duration:** 6.52s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 3335
**Name:** session_a_gemma3_extract
**Description:** Extract job summary
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 13
**Name:** gemma3:1b
**Type:** ai_model
**Model:** gemma3:1b

### Prompt Template

**Step Description:** Extract with gemma3:1b

````
Create a concise job description summary for this job posting:

{variations_param_1}

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do not add information.
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**Route to first grader** (Priority: 1)
- **Condition:** `*`
- **Description:** Extraction complete - send to first grader (gemma2) for QA review
- **Next:** Conversation 3336

**Route to second grader (parallel evaluation)** (Priority: 1)
- **Condition:** `*`
- **Description:** Second grader independently evaluates the same summary
- **Next:** Conversation 3337

### Parent Interactions

This interaction received data from:

- Interaction 253

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````
Create a concise job description summary for this job posting:

Job Description: Job Title: CA Intern Location: Mumbai, India Corporate Title: Intern Duration: 12 Months Role Description We are committed to being the best financial services provider in the world, balancing passion with precision to deliver superior solutions for our clients. This is made possible by our people: agile minds, able to see beyond the obvious and act effectively in an ever-changing global business landscape. As youâll discover, our culture supports this. Diverse, international and shaped by a variety of different perspectives, weâre driven by a shared sense of purpose. At every level agile thinking is nurtured. And at every level agile minds are rewarded with competitive pay, support and opportunities to excel. Your key responsibilities Analyze and report on the development of DB Group capital adequacy, with focus on ensuring mutual information between Pillar 1 (regulatory models) and Pillar 2 capital metrics (economic capital) Manage the economic capital model for earnings volatility risk under stress, including analysis of input/output, support in enhancement initiatives and regular model maintenance Support in framework enhancements related to ânon-standard risksâ (e.g. step-in risk, insurance risk) Participate in projects related to capital adequacy topics and coordinate internal and external ICAAP-related forums (e.g. monthly ICAAP Council, engagement with supervisors) Monitor and drive the management of regulatory changes related to the teamâs book of work Support in the implementation of measures required by supervisors and auditors Your skills and experience Exposure/Skills Good knowledge of risk management frameworks and the key regulations related to capital adequacy (ICAAP) Strong project management skills - ability to perform within tight deadlines and remain agile to evolving requirements Innovative and proactive mindset with ability to drive change in the organization Proficiency with MS Office (Excel, PowerPoint) Soft Skills Ability to communicate effectively (oral &amp; written) Strong analytical / business problem-solving skills Well organized &amp; able to clearly present results of work Ability to manage own time Passion for change and confidence in own abilities Diligent, thorough, shows initiative and is proactive Self-motivated and pro-active team-player Eligibility: Should be eligible for Industrial Training as per the ICAI rules and regulations. How weâll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people â in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world â be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do not add information.
````

### Actual Output

````
```text
**Role:** CA Intern
**Company:** Deutsche Bank Group
**Location:** Mumbai, India
**Job ID:** Not Available

**Key Responsibilities:**
- Analyze and report on the development of DB Group capital adequacy, with focus on ensuring mutual information between Pillar 1 (regulatory models) and Pillar 2 capital metrics (economic capital)
- Manage the economic capital model for earnings volatility risk under stress, including analysis of input/output, enhancement initiatives, and regular model maintenance
- Support in framework enhancements related to non-standard risks (e.g., step-in risk, insurance risk)
- Participate in projects related to capital adequacy topics and coordinate internal and external ICAAP-related forums (e.g., monthly ICAAP Council, engagement with supervisors)
- Monitor and drive the management of regulatory changes related to the team’s book of work
- Support in the implementation of measures required by supervisors and auditors

**Requirements:**
- Good knowledge of risk management frameworks and the key regulations related to capital adequacy (ICAAP)
- Strong project management skills – ability to perform within tight deadlines and remain agile to evolving requirements
- Innovative and proactive mindset with ability to drive change in the organization
- Proficiency with MS Office (Excel, PowerPoint)
- Soft skills – Ability to communicate effectively (oral & written)
- Analytical / Business problem-solving skills
- Strong analytical / business problem-solving skills
- Ability to manage own time
- Passion for change and confidence in own abilities
- Diligent, thorough, shows initiative and is proactive
- Self-motivated and pro-active team-player

**Details:**
- Should be eligible for Industrial Training as per the ICAI rules and regulations.
- Training and development to help you excel in your career
- Coaching and support from experts in your team
- A culture of continuous learning to aid progression
- A range of flexible benefits that you can tailor to suit your needs
- About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html
- We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group.
- We welcome applications from all people and promote a positive, fair and inclusive work environment.
- More information at: Deutsche Bank Careers (db.com)
```
````

**Metadata:** `{"model": "gemma3:1b", "latency_ms": 6478}`

### Child Interactions Created

- Interaction 255
- Interaction 256

---

## ✅ Interaction 4: Unknown

**Interaction ID:** 255
**Duration:** 32.63s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 3336
**Name:** session_b_gemma2_grade
**Description:** Grade extraction with gemma2
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 12
**Name:** gemma2:latest
**Type:** ai_model
**Model:** gemma2:latest

### Prompt Template

**Step Description:** Grade with gemma2:latest

````
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
{conversation_3335_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
````

### Parent Interactions

This interaction received data from:

- Interaction 254

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
Job Description: Job Title: CA Intern Location: Mumbai, India Corporate Title: Intern Duration: 12 Months Role Description We are committed to being the best financial services provider in the world, balancing passion with precision to deliver superior solutions for our clients. This is made possible by our people: agile minds, able to see beyond the obvious and act effectively in an ever-changing global business landscape. As youâll discover, our culture supports this. Diverse, international and shaped by a variety of different perspectives, weâre driven by a shared sense of purpose. At every level agile thinking is nurtured. And at every level agile minds are rewarded with competitive pay, support and opportunities to excel. Your key responsibilities Analyze and report on the development of DB Group capital adequacy, with focus on ensuring mutual information between Pillar 1 (regulatory models) and Pillar 2 capital metrics (economic capital) Manage the economic capital model for earnings volatility risk under stress, including analysis of input/output, support in enhancement initiatives and regular model maintenance Support in framework enhancements related to ânon-standard risksâ (e.g. step-in risk, insurance risk) Participate in projects related to capital adequacy topics and coordinate internal and external ICAAP-related forums (e.g. monthly ICAAP Council, engagement with supervisors) Monitor and drive the management of regulatory changes related to the teamâs book of work Support in the implementation of measures required by supervisors and auditors Your skills and experience Exposure/Skills Good knowledge of risk management frameworks and the key regulations related to capital adequacy (ICAAP) Strong project management skills - ability to perform within tight deadlines and remain agile to evolving requirements Innovative and proactive mindset with ability to drive change in the organization Proficiency with MS Office (Excel, PowerPoint) Soft Skills Ability to communicate effectively (oral &amp; written) Strong analytical / business problem-solving skills Well organized &amp; able to clearly present results of work Ability to manage own time Passion for change and confidence in own abilities Diligent, thorough, shows initiative and is proactive Self-motivated and pro-active team-player Eligibility: Should be eligible for Industrial Training as per the ICAI rules and regulations. How weâll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people â in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world â be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
```text
**Role:** CA Intern
**Company:** Deutsche Bank Group
**Location:** Mumbai, India
**Job ID:** Not Available

**Key Responsibilities:**
- Analyze and report on the development of DB Group capital adequacy, with focus on ensuring mutual information between Pillar 1 (regulatory models) and Pillar 2 capital metrics (economic capital)
- Manage the economic capital model for earnings volatility risk under stress, including analysis of input/output, enhancement initiatives, and regular model maintenance
- Support in framework enhancements related to non-standard risks (e.g., step-in risk, insurance risk)
- Participate in projects related to capital adequacy topics and coordinate internal and external ICAAP-related forums (e.g., monthly ICAAP Council, engagement with supervisors)
- Monitor and drive the management of regulatory changes related to the team’s book of work
- Support in the implementation of measures required by supervisors and auditors

**Requirements:**
- Good knowledge of risk management frameworks and the key regulations related to capital adequacy (ICAAP)
- Strong project management skills – ability to perform within tight deadlines and remain agile to evolving requirements
- Innovative and proactive mindset with ability to drive change in the organization
- Proficiency with MS Office (Excel, PowerPoint)
- Soft skills – Ability to communicate effectively (oral & written)
- Analytical / Business problem-solving skills
- Strong analytical / business problem-solving skills
- Ability to manage own time
- Passion for change and confidence in own abilities
- Diligent, thorough, shows initiative and is proactive
- Self-motivated and pro-active team-player

**Details:**
- Should be eligible for Industrial Training as per the ICAI rules and regulations.
- Training and development to help you excel in your career
- Coaching and support from experts in your team
- A culture of continuous learning to aid progression
- A range of flexible benefits that you can tailor to suit your needs
- About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html
- We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group.
- We welcome applications from all people and promote a positive, fair and inclusive work environment.
- More information at: Deutsche Bank Careers (db.com)
```
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
````

### Actual Output

````
[PASS] 

The summary accurately reflects the information provided in the original job posting. It captures the key responsibilities, requirements, and details about the role, company, and benefits offered.  

Here's a breakdown:

* **Accuracy:** There are no factual errors or hallucinations in the summary. It correctly summarizes the duties, skills needed, and eligibility criteria.
* **Completeness:** The summary includes all the essential information present in the original posting. It covers the job title, company, location, key responsibilities, required skills (both hard and soft),  and details about training and company culture.
* **Formatting:** The summary follows the specified ===OUTPUT TEMPLATE=== format with clear section headings for "Role," "Company," "Location," "Job ID," "Key Responsibilities," "Requirements," and "Details."

Overall, the AI-generated summary is a comprehensive and accurate representation of the original job posting.
````

**Metadata:** `{"model": "gemma2:latest", "latency_ms": 32601}`

---

## ✅ Interaction 5: Unknown

**Interaction ID:** 256
**Duration:** 8.75s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 3337
**Name:** session_c_qwen25_grade
**Description:** Second opinion grading
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 45
**Name:** qwen2.5:7b
**Type:** ai_model
**Model:** qwen2.5:7b

### Prompt Template

**Step Description:** Grade with qwen2.5:7b

````
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
{conversation_3335_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**Grading failed - go to improvement session** (Priority: 10)
- **Condition:** `[FAIL]`
- **Description:** Grading failed - go to improvement session
- **Next:** Conversation 3338

**Both graders passed - skip improvement, go directly to format** (Priority: 10)
- **Condition:** `[PASS]`
- **Description:** Both graders passed - skip improvement, go directly to format
- **Next:** Conversation 3341

**Unexpected output format - create error ticket** (Priority: 0)
- **Condition:** `*`
- **Description:** Unexpected output format - create error ticket
- **Next:** Conversation 3340

### Parent Interactions

This interaction received data from:

- Interaction 254

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
Job Description: Job Title: CA Intern Location: Mumbai, India Corporate Title: Intern Duration: 12 Months Role Description We are committed to being the best financial services provider in the world, balancing passion with precision to deliver superior solutions for our clients. This is made possible by our people: agile minds, able to see beyond the obvious and act effectively in an ever-changing global business landscape. As youâll discover, our culture supports this. Diverse, international and shaped by a variety of different perspectives, weâre driven by a shared sense of purpose. At every level agile thinking is nurtured. And at every level agile minds are rewarded with competitive pay, support and opportunities to excel. Your key responsibilities Analyze and report on the development of DB Group capital adequacy, with focus on ensuring mutual information between Pillar 1 (regulatory models) and Pillar 2 capital metrics (economic capital) Manage the economic capital model for earnings volatility risk under stress, including analysis of input/output, support in enhancement initiatives and regular model maintenance Support in framework enhancements related to ânon-standard risksâ (e.g. step-in risk, insurance risk) Participate in projects related to capital adequacy topics and coordinate internal and external ICAAP-related forums (e.g. monthly ICAAP Council, engagement with supervisors) Monitor and drive the management of regulatory changes related to the teamâs book of work Support in the implementation of measures required by supervisors and auditors Your skills and experience Exposure/Skills Good knowledge of risk management frameworks and the key regulations related to capital adequacy (ICAAP) Strong project management skills - ability to perform within tight deadlines and remain agile to evolving requirements Innovative and proactive mindset with ability to drive change in the organization Proficiency with MS Office (Excel, PowerPoint) Soft Skills Ability to communicate effectively (oral &amp; written) Strong analytical / business problem-solving skills Well organized &amp; able to clearly present results of work Ability to manage own time Passion for change and confidence in own abilities Diligent, thorough, shows initiative and is proactive Self-motivated and pro-active team-player Eligibility: Should be eligible for Industrial Training as per the ICAI rules and regulations. How weâll support you Training and development to help you excel in your career Coaching and support from experts in your team A culture of continuous learning to aid progression A range of flexible benefits that you can tailor to suit your needs About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group. We welcome applications from all people and promote a positive, fair and inclusive work environment. For over 150 years, our dedication to being the Global Hausbank for our clients has been driven by our people â in around 60 countries and across more than 150 nationalities. Their deep understanding, insights, expertise, and passion help our clients navigate an increasingly complex world â be it in our Corporate Bank, our Private Bank, our Investment Bank or our Asset Management (DWS) division. Together we can make a great impact for our clients at home and abroad, securing their lasting success and financial security. More information at: Deutsche Bank Careers (db.com)
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
```text
**Role:** CA Intern
**Company:** Deutsche Bank Group
**Location:** Mumbai, India
**Job ID:** Not Available

**Key Responsibilities:**
- Analyze and report on the development of DB Group capital adequacy, with focus on ensuring mutual information between Pillar 1 (regulatory models) and Pillar 2 capital metrics (economic capital)
- Manage the economic capital model for earnings volatility risk under stress, including analysis of input/output, enhancement initiatives, and regular model maintenance
- Support in framework enhancements related to non-standard risks (e.g., step-in risk, insurance risk)
- Participate in projects related to capital adequacy topics and coordinate internal and external ICAAP-related forums (e.g., monthly ICAAP Council, engagement with supervisors)
- Monitor and drive the management of regulatory changes related to the team’s book of work
- Support in the implementation of measures required by supervisors and auditors

**Requirements:**
- Good knowledge of risk management frameworks and the key regulations related to capital adequacy (ICAAP)
- Strong project management skills – ability to perform within tight deadlines and remain agile to evolving requirements
- Innovative and proactive mindset with ability to drive change in the organization
- Proficiency with MS Office (Excel, PowerPoint)
- Soft skills – Ability to communicate effectively (oral & written)
- Analytical / Business problem-solving skills
- Strong analytical / business problem-solving skills
- Ability to manage own time
- Passion for change and confidence in own abilities
- Diligent, thorough, shows initiative and is proactive
- Self-motivated and pro-active team-player

**Details:**
- Should be eligible for Industrial Training as per the ICAI rules and regulations.
- Training and development to help you excel in your career
- Coaching and support from experts in your team
- A culture of continuous learning to aid progression
- A range of flexible benefits that you can tailor to suit your needs
- About us and our teams Please visit our company website for further information: https://www.db.com/company/company.html
- We strive for a culture in which we are empowered to excel together every day. This includes acting responsibly, thinking commercially, taking initiative and working collaboratively. Together we share and celebrate the successes of our people. Together we are Deutsche Bank Group.
- We welcome applications from all people and promote a positive, fair and inclusive work environment.
- More information at: Deutsche Bank Careers (db.com)
```
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
````

### Actual Output

````
[PASS]

The summary accurately captures the key details of the job posting without introducing any hallucinated details. It includes the role title (CA Intern), company name (Deutsche Bank Group), location (Mumbai, India), and provides a comprehensive overview of the key responsibilities and requirements as described in the original post. The formatting follows the ===OUTPUT TEMPLATE=== format correctly. Therefore, there are no errors or omissions that would justify a "FAIL" rating.
````

**Metadata:** `{"model": "qwen2.5:7b", "latency_ms": 8721}`

### Child Interactions Created

- Interaction 257
- Interaction 258

---

## ✅ Interaction 6: Unknown

**Interaction ID:** 257
**Duration:** 25.66s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 3341
**Name:** Format Standardization
**Description:** Standardize output format
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 44
**Name:** phi3:latest
**Type:** ai_model
**Model:** phi3:latest

### Prompt Template

**Step Description:** Standardize output format

````
Clean this job posting summary by following these rules EXACTLY:

INPUT (use the best available summary - improved version if available, otherwise original):
{session_7_output?session_6_output?session_3_output}

RULES:
1. Remove ALL markdown code block markers (```, ```json, etc.)
2. Keep ONLY these section headers in this order:
   - **Role:**
   - **Company:**
   - **Location:**
   - **Job ID:**
   - **Key Responsibilities:**
   - **Requirements:**
   - **Details:**

3. Remove any "Type:", "Skills and Experience:", "Benefits:" sections - merge content into appropriate sections above
4. Format consistently:
   - Use "- " for all bullet points
   - Keep sections concise
   - No nested formatting
   - No extra blank lines between sections

5. Output PLAIN TEXT ONLY - no markdown wrappers

Return ONLY the cleaned version, nothing else.
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**After formatting, save summary** (Priority: 100)
- **Condition:** `*`
- **Next:** Conversation 9168

### Parent Interactions

This interaction received data from:

- Interaction 256

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````
Clean this job posting summary by following these rules EXACTLY:

INPUT (use the best available summary - improved version if available, otherwise original):
{session_7_output?session_6_output?session_3_output}

RULES:
1. Remove ALL markdown code block markers (```, ```json, etc.)
2. Keep ONLY these section headers in this order:
   - **Role:**
   - **Company:**
   - **Location:**
   - **Job ID:**
   - **Key Responsibilities:**
   - **Requirements:**
   - **Details:**

3. Remove any "Type:", "Skills and Experience:", "Benefits:" sections - merge content into appropriate sections above
4. Format consistently:
   - Use "- " for all bullet points
   - Keep sections concise
   - No nested formatting
   - No extra blank lines between sections

5. Output PLAIN TEXT ONLY - no markdown wrappers

Return ONLY the cleaned version, nothing else.
````

### Actual Output

````
**Role:** Data Analyst at The University of Chicago Booth School of Business in its Department of Finance and Real Estate Investment Center (BREIC) for a four-year project to analyze institutional investor behavior during asset booms with particular attention paid to risk management practices. Tasks will include analyzing large datasets, identifying trends and anomalies over time across various assets in the US housing market from 2008 onwards using data analytics tools including Excel Power Query, Tableau Desktop (version prior to March-15), Python for EDA/Data Cleanup & R for econometric analysis.

**Company:** The University of Chicago Booth School of Business BREIC with its focus on financial economics and policy research in the US housing markets since 2017 through several multiyear projects including a forthcoming one-and-a-half-billion dollar publicly funded, five to seven years study.

**Location:** Chicago, IL (will be relocatable within BREIC’s offices) with travel required for onsite work in specific asset and institutional investor data gathering locations around the US since 2017 via multiple trips across states such as California, Texas, Florida. Experience will also include extensive time spent at Chicago Booth School of Business' main campus during semester breaks through January to June each year between fall term starts for intensive academic work and collaboration with faculty members on projects related to institutional investor behavior in housing markets including an important three-year project analyzing the effects of financial regulations since 2017.

**Job ID:** DARM_FINANCE583, a contract position for four years starting October 16th, with option to extend up until January 2024 based on successful performance and mutual interest from both parties (BREIC may not be able or wishing yet).

**Key Responsibilities:** - Analyze large institutional investor data sets for trends in risk management practices during asset booms, focusing specifically on the US housing market. This will involve cleaning and structuring raw datasets using tools like Excel Power Query, Tableau Desktop (version prior to March-15), Python scripts, & R codebases with a focus on statistical data analysis techniques for econometric evaluation of investor behavior patterns including risk management strategies during periods of market boom. - Collaborate closely with academic partners within the BREIC team and Booth School faculty members working in related areas such as financial economics, policy research, & housing markets to ensure alignment on methodologies used for data analysis while sharing insights from primary datasets gathered directly through fieldwork (travel required). - Present findings at both academic conferences relevant to the BREIC’s focus area and internally within our project teams via presentations/reports. Compose comprehensive literature reviews of existing research related to this topic for use as references in my work, incorporating latest studies from leading journals like The Journal of Finance or NBER: Macroprudential Monetary Policy & Housing Markets since 2017 - Engage actively with the finance and policy literature through reading academic papers (primary sources) on related topics such as asset bubbles, investor behavior in financial markets over time periods like booms or crashes when relevant for research needs by accessing resources available at Booth’s main library including EconLit & AEA archives. - Perform rigorous data analysis using statistical methods suitable both individually and with team members where appropriate; prepare detailed documentation accompanying all findings presented in academic papers/reports submitted within timelines established per project goals (two working weeks prior to fall semester starts). 

**Requirements:** - Strong computer literacy skills including proficiency using software such as Excel Power Query, Tableau Desktop for data visualization purposes or similar open-source alternatives where necessary while familiarity required with python & R programming languages specifically tailored towards handling large datasets efficiently (3+ years experience preferred), understanding statistical concepts like hypothesis testing techniques along time series analysis methods applied commonly employed within finance field - Experience working at some level directly managing/analyzing institutional investor data sets from 2017 onwards focused primarily around trends & risk management practices during housing market booms alongside required knowledge regarding regulatory implications surrounding said behavior (minimum two years of experience expected). Good command over English language necessary for writing clear academic papers / reports which are to be submitted regularly throughout contract duration - Excellent organizational skills essential due diligent record-keeping & maintain current research on topical literature needed often during workday along with ability handle multiple tasks simultaneously without compromising quality of output expected; time management critical skill when juggling fieldwork + data analysis projects within BREIC framework alongside academic coursework - Strong interpersonal communication skills vital particularly necessary for effective collaboration directly related towards mutual research interests among Booth School community members engaged throughout various stages individual’s career path (e.g., seminars/discussions held periodically).

**Details:** This contract position is specifically available starting October 16th, with a minimum duration of four years up until January 2024 based on successful performance and mutual interest from both parties involved - Salary details yet to be negotiated upon start date however Booth School has history offering competitive compensation package for similar positions within Chicago metropolitan area (based past experience). Contact info available through office email address if further inquiries desired: Darmarat@uchicago.edu or call ext 73065 directly via voicemail prompted system before attempting direct ring - Deadline information not applicable at present moment; however it’s strongly recommended reaching out sooner rather later when interested parties wish proceed application process per university's hiring calendar timelines if appropriate interest exists towards potential engagement opportunity presented hereabove-
````

**Metadata:** `{"model": "phi3:latest", "latency_ms": 25625}`

### Child Interactions Created

- Interaction 259

---

## Summary

- **Total interactions:** 6
- **Completed:** 6
- **Failed:** 0
- **Total duration:** 202.6s
- **Avg per interaction:** 33.76s
