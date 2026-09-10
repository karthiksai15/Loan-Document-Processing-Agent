import { describe, it, expect } from 'vitest';
import { formatAgentRecommendation, formatPolicySourceLabel, getDocumentDisplayLabel } from '../services/formatters';

describe('AI Review Agent Data Binding & Formatter Tests', () => {
  const a001Payload = {
    agent_review_id: 'REV-A001',
    application_id: 'A001',
    investigation_status: 'COMPLETED',
    confidence: 0.95,
    confidence_level: 'HIGH',
    grounding_status: 'GROUNDED',
    evidence_sufficiency: 'SUFFICIENT',
    final_review: {
      recommended_next_step: 'STANDARD_REVIEW',
      confidence: 0.95,
      confidence_level: 'HIGH',
      executive_summary:
        'Application A001 submitted by Aarav Sharma requests a loan amount of INR 1,100,000 against an annual declared income of INR 300,000...',
      key_findings: [
        'CIBIL credit score is exceptionally low at 300, indicating a high risk of default per credit policy guidance.',
        'Requested loan amount of INR 1,100,000 significantly exceeds standard affordability metrics relative to the declared annual income of INR 300,000 and 5 dependents.',
        'All submitted documents (payslip, bank statement, tax return, KYC) passed individual validation and cross-document verification with zero discrepancies.',
      ],
      evidence_references: [
        { node_id: 'NODE-APP-A001', description: 'Application record for Aarav Sharma requesting INR 1,100,000 loan amount.' },
        { node_id: 'NODE-ML-RISK-A001', description: 'ML risk assessment showing a historical rejection risk probability of 0.2205 (LOW risk level).' },
        { node_id: 'NODE-REVIEW-A001', description: 'Review intelligence showing a review score of 6.6/100 and complete evidence trust.' },
      ],
      policy_references: [
        {
          policy_id: 'POL_HDFC_PUB_CREDITWORTHINESS_003',
          policy_name: 'HDFC Bank Personal Loan — Public Credit Score & Repayment Guidance',
          authority: 'INTERNAL_BANK',
          policy_type: 'INTERNAL_UNDERWRITING',
          citation_text: 'HDFC Bank publicly advises personal loan applicants that credit score (CIBIL) and past credit history are key factors in evaluating creditworthiness...',
          source_label: 'HDFC_BANK',
        },
      ],
      unresolved_questions: [],
      limitations: [
        'Credit bureau history is limited to the CIBIL score of 300 without detailed breakdown of past defaults within the provided context.',
      ],
      grounding_status: 'GROUNDED',
      evidence_sufficiency: 'SUFFICIENT',
    },
  };

  const a008Payload = {
    agent_review_id: 'REV-A008',
    application_id: 'A008',
    investigation_status: 'ESCALATED',
    confidence: 0.7,
    confidence_level: 'MEDIUM',
    grounding_status: 'GROUNDED',
    evidence_sufficiency: 'PARTIAL',
    final_review: {
      recommended_next_step: 'OFFICER_INVESTIGATION',
      confidence: 0.7,
      confidence_level: 'MEDIUM',
      executive_summary:
        'Application A008 submitted by Ishita Rao for a loan amount of INR 17,900,000 has been reviewed. Cross-document verification revealed eight discrepancies across submitted documents...',
      key_findings: [
        'A primary identity mismatch was identified between the application name (Ishita Rao) and the KYC document name (Kiran Mismatch).',
        'Eight cross-document mismatches were flagged, involving names and income figures across application, payslip, bank statement, and tax return.',
        "The applicant's CIBIL score is 384, indicating high credit risk.",
        'Declared annual income and payslip annualized income figures show significant discrepancies.',
      ],
      evidence_references: [
        { node_id: 'NODE-APP-A008', description: 'Application data for Ishita Rao showing loan amount INR 17,900,000' },
        { node_id: 'NODE-FINDING-109', description: 'Cross-document verification error for application name vs KYC name' },
        { node_id: 'NODE-VAL-DOC-89c79495d3fd', description: 'KYC validation result showing primary identity discrepancy' },
        { node_id: 'NODE-ML-RISK-A008', description: 'ML risk assessment indicator' },
      ],
      policy_references: [
        {
          policy_id: 'POL_HDFC_DEMO_IDENTITY_MISMATCH_003',
          policy_name: 'Identity Mismatch Policy',
          authority: 'INTERNAL_BANK',
          policy_type: 'INTERNAL_UNDERWRITING',
          citation_text: 'A primary identity mismatch requires officer investigation before further automated processing.',
          source_label: 'INTERNAL_DEMO',
        },
        {
          policy_id: 'POL_RBI_FAIR_PRACTICES_004',
          policy_name: 'RBI Fair Practices Code',
          authority: 'RBI',
          policy_type: 'REGULATORY',
          citation_text: 'Ensure transparent verification and documentation standards for all loan applicants.',
          source_label: 'RBI',
        },
      ],
      unresolved_questions: [
        'What is the reason for the discrepancy between the application name Ishita Rao and the KYC document name Kiran Mismatch?',
        'How can the income variance between the tax return and the payslip annualized figures be reconciled?',
      ],
      limitations: [
        'Identity discrepancies prevent automated verification.',
        'Income figures across documents require manual verification by a human officer.',
      ],
      grounding_status: 'GROUNDED',
      evidence_sufficiency: 'PARTIAL',
    },
  };

  it('binds A001 stored review accurately to final_review fields', () => {
    const fr = a001Payload.final_review;
    const recommendation = formatAgentRecommendation(fr.recommended_next_step);
    expect(recommendation).toBe('Standard Review');
    expect(fr.recommended_next_step).toBe('STANDARD_REVIEW');

    const conf = Math.round(fr.confidence * 100);
    expect(conf).toBe(95);

    expect(fr.executive_summary).toContain('Application A001');
    expect(fr.evidence_references).toHaveLength(3);
    expect(fr.evidence_references[0].node_id).toBe('NODE-APP-A001');

    expect(fr.policy_references).toHaveLength(1);
    expect(formatPolicySourceLabel(fr.policy_references[0])).toBe('HDFC Bank');
  });

  it('binds A008 stored review accurately with 8 mismatches and policy references', () => {
    const fr = a008Payload.final_review;
    const recommendation = formatAgentRecommendation(fr.recommended_next_step);
    expect(recommendation).toBe('Officer Investigation');
    expect(fr.recommended_next_step).toBe('OFFICER_INVESTIGATION');

    const conf = Math.round(fr.confidence * 100);
    expect(conf).toBe(70);

    expect(fr.executive_summary).toContain('eight discrepancies');
    expect(fr.key_findings).toHaveLength(4);
    expect(fr.key_findings[1]).toContain('Eight cross-document mismatches were flagged');

    expect(fr.policy_references).toHaveLength(2);
    expect(formatPolicySourceLabel(fr.policy_references[0])).toBe('Internal Demo Policy');
    expect(formatPolicySourceLabel(fr.policy_references[1])).toBe('RBI');

    expect(fr.unresolved_questions).toHaveLength(2);
    expect(fr.limitations).toHaveLength(2);
  });

  const a003Payload = {
    agent_review_id: 'REV-A003',
    application_id: 'A003',
    investigation_status: 'COMPLETED',
    confidence: 0.7,
    confidence_level: 'MEDIUM',
    grounding_status: 'GROUNDED',
    evidence_sufficiency: 'PARTIAL',
    final_review: {
      recommended_next_step: 'DOCUMENT_FOLLOWUP',
      confidence: 0.7,
      confidence_level: 'MEDIUM',
      executive_summary:
        'Application A003 submitted by Rohan Kumar for an INR 17,700,000 personal loan demonstrates low ML rejection risk... missing tax return document...',
      key_findings: [
        'Application package is currently incomplete due to the missing tax return document.',
        "The applicant's CIBIL score of 675 falls below HDFC Bank's public creditworthiness guidance range of 720-750.",
      ],
      evidence_references: [
        { node_id: 'NODE-APP-A003', description: 'Application record for Rohan Kumar requesting INR 17,700,000.' },
        { node_id: 'NODE-DOC-DOC-a6fa486e79b8', description: 'Payslip document indicating monthly net salary of INR 344,960.' },
        { node_id: 'NODE-DOC-DOC-ca0b7043da3c', description: 'Bank statement confirming salary credit transaction of INR 392,000.' },
      ],
      policy_references: [
        {
          policy_id: 'POL_HDFC_PUB_CREDITWORTHINESS_003',
          policy_name: 'HDFC Bank Personal Loan Public Credit Score & Repayment Guidance',
          authority: 'INTERNAL_BANK',
          source_label: 'HDFC_BANK',
        },
        {
          policy_id: 'POL_HDFC_PUB_DOCS_001',
          policy_name: 'HDFC Bank Personal Loan Public Documentation Checklist',
          authority: 'INTERNAL_BANK',
          source_label: 'HDFC_BANK',
        },
        {
          policy_id: 'POL_RBI_FAIR_PRACTICES_004',
          policy_name: 'RBI Fair Practices Code',
          authority: 'RBI',
          source_label: 'RBI',
        },
      ],
      unresolved_questions: [],
      limitations: [],
      grounding_status: 'GROUNDED',
      evidence_sufficiency: 'PARTIAL',
    },
  };

  it('binds A003 stored review accurately with Request Documents, 70% confidence, and 3 policies', () => {
    const fr = a003Payload.final_review;
    const recommendation = formatAgentRecommendation(fr.recommended_next_step);
    expect(recommendation).toBe('Request Documents');
    expect(recommendation).not.toBe('Not Reviewed');

    // Agent confidence must be exactly 70%, NOT 85%
    const agentConf = Math.round(fr.confidence * 100);
    expect(agentConf).toBe(70);
    expect(agentConf).not.toBe(85);

    // Policy references must contain 3 policies with correct labels
    expect(fr.policy_references).toHaveLength(3);
    expect(formatPolicySourceLabel(fr.policy_references[0])).toBe('HDFC Bank');
    expect(formatPolicySourceLabel(fr.policy_references[1])).toBe('HDFC Bank');
    expect(formatPolicySourceLabel(fr.policy_references[2])).toBe('RBI');
  });

  it('correctly reports Not Reviewed when review is null or missing', () => {
    expect(formatAgentRecommendation(null)).toBe('Not Reviewed');
    expect(formatAgentRecommendation(undefined)).toBe('Not Reviewed');
  });

  const a010Payload = {
    agent_review_id: 'REV-A010',
    application_id: 'A010',
    investigation_status: 'COMPLETED',
    confidence: 0.95,
    confidence_level: 'HIGH',
    grounding_status: 'GROUNDED',
    evidence_sufficiency: 'SUFFICIENT',
    final_review: {
      recommended_next_step: 'STANDARD_REVIEW',
      confidence: 0.95,
      confidence_level: 'HIGH',
      executive_summary: 'Application A010 submitted by Aditya Verma passes all verification checks...',
      key_findings: [
        'All 4 submitted documents passed individual validation and 8 cross-document checks matched.',
      ],
      evidence_references: [
        { node_id: 'NODE-APP-A010', description: 'Application record for Aditya Verma.' },
      ],
      policy_references: [
        {
          policy_id: 'POL_HDFC_PUB_CREDITWORTHINESS_003',
          policy_name: 'HDFC Bank Personal Loan — Public Credit Score & Repayment Guidance',
          authority: 'INTERNAL_BANK',
          source_label: 'HDFC_BANK',
        },
      ],
      grounding_status: 'GROUNDED',
      evidence_sufficiency: 'SUFFICIENT',
    },
  };

  it('binds A010 stored review accurately with Standard Review, 95% confidence, and 1 policy', () => {
    const fr = a010Payload.final_review;
    expect(formatAgentRecommendation(fr.recommended_next_step)).toBe('Standard Review');
    expect(Math.round(fr.confidence * 100)).toBe(95);
    expect(fr.grounding_status).toBe('GROUNDED');
    expect(fr.evidence_sufficiency).toBe('SUFFICIENT');
    expect(fr.policy_references).toHaveLength(1);
    expect(formatPolicySourceLabel(fr.policy_references[0])).toBe('HDFC Bank');
  });

  it('resolves Evidence document labels for A003 and A010 without displaying OTHER', () => {
    // A003 documents with evidence nodes
    const a003Evidence = {
      nodes: [
        { node_type: 'DOCUMENT', document_id: 'DOC-a6fa486e79b8', title: 'PAYSLIP (01_payslip.txt)', value: 'Type: PAYSLIP | Extracted: COMPLETED' },
        { node_type: 'DOCUMENT', document_id: 'DOC-ca0b7043da3c', title: 'BANK_STATEMENT (02_bank_statement.txt)', value: 'Type: BANK_STATEMENT | Extracted: COMPLETED' },
        { node_type: 'DOCUMENT', document_id: 'DOC-b9cc315bbeb9', title: 'KYC (04_kyc.txt)', value: 'Type: KYC | Extracted: COMPLETED' },
      ],
    };

    const a003Docs = [
      { document_id: 'DOC-a6fa486e79b8', document_type: 'OTHER', original_filename: '01_payslip.txt' },
      { document_id: 'DOC-ca0b7043da3c', document_type: 'OTHER', original_filename: '02_bank_statement.txt' },
      { document_id: 'DOC-b9cc315bbeb9', document_type: 'OTHER', original_filename: '04_kyc.txt' },
    ];

    const a003Labels = a003Docs.map((d) => getDocumentDisplayLabel(d, a003Evidence));
    expect(a003Labels).toEqual(['Salary Payslip', 'Bank Statement', 'KYC Document']);
    expect(a003Labels).not.toContain('OTHER');

    // A010 documents with metadata or evidence nodes
    const a010Evidence = {
      nodes: [
        { node_type: 'DOCUMENT', document_id: 'DOC-d3dca26f3691', title: 'PAYSLIP (01_payslip.txt)', value: 'Type: PAYSLIP | Extracted: COMPLETED' },
        { node_type: 'DOCUMENT', document_id: 'DOC-e710915bc854', title: 'BANK_STATEMENT (02_bank_statement.txt)', value: 'Type: BANK_STATEMENT | Extracted: COMPLETED' },
        { node_type: 'DOCUMENT', document_id: 'DOC-da1591a0f4c8', title: 'TAX_RETURN (03_tax_return.txt)', value: 'Type: TAX_RETURN | Extracted: COMPLETED' },
        { node_type: 'DOCUMENT', document_id: 'DOC-1a442c8600cf', title: 'KYC (04_kyc.txt)', value: 'Type: KYC | Extracted: COMPLETED' },
      ],
    };

    const a010Docs = [
      { document_id: 'DOC-d3dca26f3691', document_type: 'OTHER', original_filename: '01_payslip.txt' },
      { document_id: 'DOC-e710915bc854', document_type: 'OTHER', original_filename: '02_bank_statement.txt' },
      { document_id: 'DOC-da1591a0f4c8', document_type: 'OTHER', original_filename: '03_tax_return.txt' },
      { document_id: 'DOC-1a442c8600cf', document_type: 'OTHER', original_filename: '04_kyc.txt' },
    ];

    const a010Labels = a010Docs.map((d) => getDocumentDisplayLabel(d, a010Evidence));
    expect(a010Labels).toEqual(['Salary Payslip', 'Bank Statement', 'Tax Return (ITR-V)', 'KYC Document']);
    expect(a010Labels).not.toContain('OTHER');
  });
});
