"""
Seed data definitions for Phase 13 Policy Knowledge Base.

Contains:
1. RBI Regulatory Master Directions and Guidelines (Source: RBI official publications)
2. Internal Bank Credit Underwriting Policy (Source: Internal Risk Committee rules)
"""

SEED_POLICIES = [
    {
        "policy_doc_id": "POL_RBI_KYC_2016",
        "title": "Master Direction - Know Your Customer (KYC) Direction, 2016",
        "policy_type": "REGULATORY",
        "authority": "RBI",
        "category": "KYC",
        "version": "2025-08-14",
        "reference_code": "RBI/DBR/2015-16/18 DBR.AML.BC.No.81/14.01.001/2015-16",
        "official_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566",
        "source_filename": "media_1788873166778.pdf",
        "effective_date": "2016-02-25",
        "description": "Master Direction laying down customer acceptance, identification, officially valid documents (OVDs), and periodic KYC updation guidelines under PML Act 2002.",
        "status": "ACTIVE",
        "sections": [
            {
                "section_id": "SEC_KYC_CH4_16",
                "chapter_or_part": "Chapter IV",
                "section_number": "Section 16",
                "section_title": "Officially Valid Documents (OVD) for Customer Identification Procedure",
                "page_number": 14,
                "content_text": (
                    "For customer identification procedure of individuals, Regulated Entities (REs) shall obtain "
                    "any one of the following Officially Valid Documents (OVDs): Passport, Driving Licence, Proof of possession "
                    "of Aadhaar number, Voter's Identity Card issued by Election Commission of India, Job card issued by NREGA "
                    "duly signed by an officer of the State Government, or Letter issued by National Population Register. "
                    "Where the OVD furnished by the customer does not contain updated address, alternative utility bills "
                    "not older than two months may be accepted for a temporary period of three months."
                ),
                "summary": "Mandatory Officially Valid Documents (OVD) list for identity and address verification.",
            },
            {
                "section_id": "SEC_KYC_CH5_18",
                "chapter_or_part": "Chapter V",
                "section_number": "Section 18",
                "section_title": "Video-based Customer Identification Process (V-CIP)",
                "page_number": 22,
                "content_text": (
                    "Regulated Entities may undertake Video-based Customer Identification Process (V-CIP) for onboarding "
                    "individual customers. V-CIP must be carried out by an authorized official of the RE, incorporating "
                    "liveness check, real-time geo-tagging (GPS location within India), and clear video interaction. "
                    "The video recording must be stored securely along with timestamped audio-visual records."
                ),
                "summary": "Rules for remote digital onboarding using V-CIP with geo-tagging and liveness verification.",
            },
            {
                "section_id": "SEC_KYC_CH6_38",
                "chapter_or_part": "Chapter VI",
                "section_number": "Section 38",
                "section_title": "Periodic Updation of KYC Records",
                "page_number": 45,
                "content_text": (
                    "Regulated Entities shall carry out periodic updation of KYC records at least once in every two years "
                    "for high risk customers, once in every eight years for medium risk customers, and once in every ten years "
                    "for low risk customers, from the date of opening of the account or last KYC verification."
                ),
                "summary": "Mandatory periodic KYC updation schedule based on customer risk categorization.",
            },
        ],
        "rules": [
            {
                "rule_id": "RULE_REG_KYC_OVD_VALIDATION",
                "section_id": "SEC_KYC_CH4_16",
                "rule_code": "OVD_LIST_CHECK",
                "rule_name": "Officially Valid Document List Validation",
                "field_name": "kyc_document_type",
                "operator": "IN_LIST",
                "threshold_value": ["Aadhaar", "Passport", "Voter_ID", "Driving_Licence", "NREGA_Job_Card", "NPR_Letter"],
                "description": "Applicant KYC document must be one of the RBI-prescribed Officially Valid Documents (OVDs).",
                "is_regulatory": True,
            },
            {
                "rule_id": "RULE_REG_KYC_PERIODIC_UPDATE",
                "section_id": "SEC_KYC_CH6_38",
                "rule_code": "KYC_PERIODIC_UPDATE_TIMELINE",
                "rule_name": "KYC Refresh Schedule by Risk Level",
                "field_name": "kyc_refresh_years",
                "operator": "LESS_THAN_EQUAL",
                "threshold_value": {"HIGH_RISK": 2, "MEDIUM_RISK": 8, "LOW_RISK": 10},
                "description": "KYC refresh intervals must not exceed 2 years for High Risk, 8 years for Medium Risk, and 10 years for Low Risk.",
                "is_regulatory": True,
            },
        ],
    },
    {
        "policy_doc_id": "POL_RBI_DIGITAL_LENDING_2022",
        "title": "Guidelines on Digital Lending",
        "policy_type": "REGULATORY",
        "authority": "RBI",
        "category": "DIGITAL_LENDING",
        "version": "2022-09-02",
        "reference_code": "RBI/2022-23/111 DOR.CRE.REC.66/21.07.001/2022-23",
        "official_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12382&Mode=0",
        "source_filename": "media_1788873163308.pdf",
        "effective_date": "2022-09-02",
        "description": "Directives on digital lending apps (DLAs), direct disbursement to bank accounts, Key Fact Statement (KFS), APR disclosure, and cooling-off period.",
        "status": "ACTIVE",
        "sections": [
            {
                "section_id": "SEC_DL_DISBURSEMENT_03",
                "chapter_or_part": "Section A",
                "section_number": "Clause 3",
                "section_title": "Direct Disbursement and Repayment Protocol",
                "page_number": 3,
                "content_text": (
                    "All loan disbursements and repayments shall be executed directly between the borrower's bank account "
                    "and the Regulated Entity's (RE's) bank account without any pass-through or pool account of any third party "
                    "or Lending Service Provider (LSP). Any deviation or routing through third-party wallets/pool accounts is strictly prohibited."
                ),
                "summary": "Strict direct account-to-account transfer prohibition on third-party pool accounts.",
            },
            {
                "section_id": "SEC_DL_KFS_05",
                "chapter_or_part": "Section A",
                "section_number": "Clause 5",
                "section_title": "Key Fact Statement (KFS) and APR Disclosure",
                "page_number": 5,
                "content_text": (
                    "REs shall provide a standardized Key Fact Statement (KFS) to the borrower before execution of the loan contract. "
                    "The KFS must explicitly disclose the Annual Percentage Rate (APR), processing fees, recovery charges, "
                    "and total cost of credit. Any fee or charge not mentioned in the KFS shall not be charged to the borrower."
                ),
                "summary": "Mandatory provision of standardized KFS disclosing APR and total credit cost before contract execution.",
            },
            {
                "section_id": "SEC_DL_COOLINGOFF_07",
                "chapter_or_part": "Section A",
                "section_number": "Clause 7",
                "section_title": "Cooling-off / Look-up Period",
                "page_number": 7,
                "content_text": (
                    "A cooling-off/look-up period shall be provided to borrowers during which they may exit the digital loan "
                    "by paying the principal amount and proportionate APR without any penalty. The cooling-off period shall be "
                    "not less than 3 days for loans of tenor 7 days or more, and 1 day for loans of tenor less than 7 days."
                ),
                "summary": "Mandatory look-up period allowing penalty-free exit upon repayment of principal.",
            },
        ],
        "rules": [
            {
                "rule_id": "RULE_REG_DL_DIRECT_DISBURSEMENT",
                "section_id": "SEC_DL_DISBURSEMENT_03",
                "rule_code": "DIRECT_ACCOUNT_TRANSFER",
                "rule_name": "Direct Bank Account Disbursement Requirement",
                "field_name": "disbursement_channel",
                "operator": "EQUALS",
                "threshold_value": "DIRECT_RE_TO_BORROWER_ACCOUNT",
                "description": "Loan disbursements must go directly into borrower verified bank account with zero intermediate pool accounts.",
                "is_regulatory": True,
            },
            {
                "rule_id": "RULE_REG_DL_MIN_COOLING_OFF",
                "section_id": "SEC_DL_COOLINGOFF_07",
                "rule_code": "MIN_COOLING_OFF_DAYS",
                "rule_name": "Minimum Cooling-off Period Requirement",
                "field_name": "cooling_off_days",
                "operator": "GREATER_THAN_EQUAL",
                "threshold_value": 3,
                "description": "Digital loans with tenor >= 7 days must provide a minimum 3-day penalty-free cooling-off look-up period.",
                "is_regulatory": True,
            },
        ],
    },
    {
        "policy_doc_id": "POL_RBI_CREDIT_REPORTING_2025",
        "title": "Master Direction – Reserve Bank of India (Credit Information Reporting) Directions, 2025",
        "policy_type": "REGULATORY",
        "authority": "RBI",
        "category": "CREDIT_REPORTING",
        "version": "2025-01-06",
        "reference_code": "RBI/DoR/2024-25/125 DoR.FIN.REC.70/20.16.056/2024-25",
        "official_url": "https://www.rbi.org.in",
        "source_filename": "media_1788873161154.pdf",
        "effective_date": "2025-04-01",
        "description": "Consolidated directions governing credit reporting frequency, Uniform Credit Reporting Format (UCRF), Data Quality Index (DQI), and customer dispute delay compensation.",
        "status": "ACTIVE",
        "sections": [
            {
                "section_id": "SEC_CIR_DATA_SUBMISSION_04",
                "chapter_or_part": "Section II",
                "section_number": "Section 4",
                "section_title": "Fortnightly Credit Data Submission Frequency",
                "page_number": 8,
                "content_text": (
                    "Credit Institutions shall update and submit credit information of all borrowers to Credit Information Companies (CICs) "
                    "at fortnightly intervals (15th and last day of every month) or shorter intervals as mutually agreed, "
                    "to ensure credit records reflect accurate outstanding balances and repayment status."
                ),
                "summary": "Mandatory 15-day fortnightly credit reporting update cycle to credit bureaus.",
            },
            {
                "section_id": "SEC_CIR_DISPUTE_COMPENSATION_12",
                "chapter_or_part": "Section IV",
                "section_number": "Section 12",
                "section_title": "Customer Dispute Resolution Timelines and Delay Compensation",
                "page_number": 19,
                "content_text": (
                    "Credit Institutions and CICs shall resolve customer credit report grievance/dispute within a maximum period of "
                    "30 calendar days from the date of receipt of complaint. Where resolution exceeds 30 days, the defaulting "
                    "Credit Institution or CIC shall pay compensation at the rate of Rs. 100 per calendar day of delay to the complainant."
                ),
                "summary": "30-day maximum grievance resolution SLA with ₹100/day delay compensation requirement.",
            },
        ],
        "rules": [
            {
                "rule_id": "RULE_REG_CIR_DISPUTE_SLA",
                "section_id": "SEC_CIR_DISPUTE_COMPENSATION_12",
                "rule_code": "CREDIT_DISPUTE_MAX_DAYS",
                "rule_name": "Credit Information Dispute Resolution SLA",
                "field_name": "dispute_resolution_days",
                "operator": "LESS_THAN_EQUAL",
                "threshold_value": 30,
                "description": "Credit report dispute resolution must be completed within 30 days.",
                "is_regulatory": True,
            },
        ],
    },
    {
        "policy_doc_id": "POL_RBI_FAIR_PRACTICES_2003",
        "title": "Guidelines on Fair Practices Code for Lenders",
        "policy_type": "REGULATORY",
        "authority": "RBI",
        "category": "FAIR_PRACTICES",
        "version": "2003-05-05",
        "reference_code": "DBOD. Leg. No.BC. 104 /09.07.007/2002-03",
        "official_url": "https://www.rbi.org.in",
        "source_filename": "media_1788873165074.pdf",
        "effective_date": "2003-05-05",
        "description": "Directives framed under Lenders' Liability Laws requiring written rejection reasons for small loans and mandatory provision of loan agreement copies.",
        "status": "ACTIVE",
        "sections": [
            {
                "section_id": "SEC_FPC_REJECTION_REASON_02",
                "chapter_or_part": "Main Code",
                "section_number": "Clause 2(b)",
                "section_title": "Written Communication of Loan Application Rejection",
                "page_number": 2,
                "content_text": (
                    "In the case of small loans (up to Rs. 2 Lakhs) and overall personal loans, the lender shall convey in writing "
                    "the specific main reason(s) which led to the rejection of the loan application, to ensure transparency and accountability."
                ),
                "summary": "Mandatory written communication of specific rejection reasons to loan applicants.",
            },
            {
                "section_id": "SEC_FPC_AGREEMENT_COPY_03",
                "chapter_or_part": "Main Code",
                "section_number": "Clause 3(a)",
                "section_title": "Provision of Loan Agreement Copy to Borrower",
                "page_number": 3,
                "content_text": (
                    "Lenders shall furnish a copy of the loan agreement along with a copy of all enclosures quoted in the loan agreement "
                    "to all borrowers at the time of sanction or disbursement of the loan."
                ),
                "summary": "Mandatory requirement to provide signed copy of loan agreement and enclosures to applicant.",
            },
        ],
        "rules": [
            {
                "rule_id": "RULE_REG_FPC_WRITTEN_REJECTION",
                "section_id": "SEC_FPC_REJECTION_REASON_02",
                "rule_code": "WRITTEN_REJECTION_MANDATE",
                "rule_name": "Written Rejection Reason Requirement",
                "field_name": "rejection_notice_type",
                "operator": "EQUALS",
                "threshold_value": "WRITTEN_NOTICE_WITH_REASONS",
                "description": "Loan rejection notices must be communicated in writing specifying clear reasons.",
                "is_regulatory": True,
            },
        ],
    },
    {
        "policy_doc_id": "POL_INT_UNDERWRITING_2025",
        "title": "Retail Credit Underwriting Policy & Exposure Rules",
        "policy_type": "INTERNAL_UNDERWRITING",
        "authority": "INTERNAL_BANK",
        "category": "UNDERWRITING_METRICS",
        "version": "2025.1",
        "reference_code": "POL-CREDIT-2025-v1",
        "official_url": None,
        "source_filename": "internal_credit_policy_2025.json",
        "effective_date": "2025-01-01",
        "description": "Internal institutional underwriting criteria for personal and retail loans, defining financial ratio limits and credit score cutoffs.",
        "status": "ACTIVE",
        "sections": [
            {
                "section_id": "SEC_INT_FOIR_01",
                "chapter_or_part": "Part 1 - Debt Capacity",
                "section_number": "Section 1.1",
                "section_title": "Fixed Obligation to Income Ratio (FOIR) Maximum Threshold",
                "page_number": 4,
                "content_text": (
                    "The applicant's Total Monthly Debt Obligations (existing EMIs + proposed loan EMI) divided by Net Monthly Income "
                    "shall not exceed 50.0% (0.50). Any applicant with FOIR > 50% must be flagged for manual credit risk review or rejection."
                ),
                "summary": "Max 50% FOIR ceiling for retail loan eligibility.",
            },
            {
                "section_id": "SEC_INT_MIN_INCOME_02",
                "chapter_or_part": "Part 1 - Income Verification",
                "section_number": "Section 1.2",
                "section_title": "Minimum Monthly Net Income Threshold",
                "page_number": 5,
                "content_text": (
                    "To qualify for an unsecured retail loan, the primary applicant must demonstrate a verified net monthly income "
                    "of at least INR 25,000 (INR 300,000 per annum). Income must be verified via latest 3 months payslips and bank statement."
                ),
                "summary": "Minimum net monthly salary requirement of ₹25,000.",
            },
            {
                "section_id": "SEC_INT_CIBIL_03",
                "chapter_or_part": "Part 2 - Bureau Credit Quality",
                "section_number": "Section 2.1",
                "section_title": "Minimum CIBIL Bureau Credit Score Cutoff",
                "page_number": 8,
                "content_text": (
                    "An applicant must have a CIBIL credit score of at least 650 to qualify for standard automated processing. "
                    "CIBIL scores between 600 and 649 require Senior Underwriter approval. Scores below 600 are declined."
                ),
                "summary": "Minimum CIBIL bureau score cutoff of 650.",
            },
            {
                "section_id": "SEC_INT_LTV_04",
                "chapter_or_part": "Part 3 - Collateral & Asset Cover",
                "section_number": "Section 3.1",
                "section_title": "Maximum Loan-to-Value (LTV) Ratio Ceiling",
                "page_number": 12,
                "content_text": (
                    "For secured credit facilities, the maximum Loan-to-Value (LTV) ratio shall not exceed 80.0% (0.80) of the appraised "
                    "value of total declared assets (residential, commercial, or liquid bank deposits)."
                ),
                "summary": "Maximum 80% LTV ratio ceiling against total assets.",
            },
            {
                "section_id": "SEC_INT_AGE_05",
                "chapter_or_part": "Part 4 - Demographic Eligibility",
                "section_number": "Section 4.1",
                "section_title": "Applicant Age Eligibility Window",
                "page_number": 15,
                "content_text": (
                    "The applicant must be at least 21 years of age at the time of loan application and must not exceed 60 years of age "
                    "at the scheduled loan maturity date."
                ),
                "summary": "Eligible applicant age bracket between 21 and 60 years.",
            },
        ],
        "rules": [
            {
                "rule_id": "RULE_INT_MAX_FOIR",
                "section_id": "SEC_INT_FOIR_01",
                "rule_code": "MAX_FOIR_THRESHOLD",
                "rule_name": "Maximum Fixed Obligation to Income Ratio",
                "field_name": "foir",
                "operator": "LESS_THAN_EQUAL",
                "threshold_value": 0.50,
                "description": "Calculated FOIR must not exceed 0.50 (50%).",
                "is_regulatory": False,
            },
            {
                "rule_id": "RULE_INT_MIN_MONTHLY_INCOME",
                "section_id": "SEC_INT_MIN_INCOME_02",
                "rule_code": "MIN_MONTHLY_INCOME_THRESHOLD",
                "rule_name": "Minimum Net Monthly Income Requirement",
                "field_name": "monthly_income",
                "operator": "GREATER_THAN_EQUAL",
                "threshold_value": 25000.0,
                "description": "Verified net monthly income must be at least INR 25,000.",
                "is_regulatory": False,
            },
            {
                "rule_id": "RULE_INT_MIN_CIBIL_SCORE",
                "section_id": "SEC_INT_CIBIL_03",
                "rule_code": "MIN_CIBIL_SCORE_THRESHOLD",
                "rule_name": "Minimum CIBIL Credit Score Requirement",
                "field_name": "cibil_score",
                "operator": "GREATER_THAN_EQUAL",
                "threshold_value": 650,
                "description": "Bureau CIBIL score must be at least 650.",
                "is_regulatory": False,
            },
            {
                "rule_id": "RULE_INT_MAX_LTV",
                "section_id": "SEC_INT_LTV_04",
                "rule_code": "MAX_LTV_THRESHOLD",
                "rule_name": "Maximum Loan to Value Ratio",
                "field_name": "ltv_ratio",
                "operator": "LESS_THAN_EQUAL",
                "threshold_value": 0.80,
                "description": "Calculated LTV ratio must not exceed 0.80 (80%).",
                "is_regulatory": False,
            },
            {
                "rule_id": "RULE_INT_ELIGIBLE_AGE",
                "section_id": "SEC_INT_AGE_05",
                "rule_code": "ELIGIBLE_AGE_RANGE",
                "rule_name": "Applicant Age Window Requirement",
                "field_name": "applicant_age",
                "operator": "RANGE",
                "threshold_value": {"min_age": 21, "max_age": 60},
                "description": "Applicant age must be between 21 and 60 years.",
                "is_regulatory": False,
            },
        ],
    },
]
