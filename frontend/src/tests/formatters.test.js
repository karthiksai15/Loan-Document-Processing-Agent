import { describe, it, expect } from 'vitest';
import {
  formatINR,
  formatPercent,
  getCibilCategory,
  formatDateTime,
  formatPolicySourceLabel,
  formatAgentRecommendation,
  formatDocumentType,
  getDocumentDisplayLabel,
} from '../services/formatters';

describe('Financial Formatters', () => {
  it('formats Indian Rupees into Lakhs and Crores properly', () => {
    expect(formatINR(25500000)).toBe('₹2.55 Cr');
    expect(formatINR(9200000)).toBe('₹92 Lakh');
    expect(formatINR(1000000)).toBe('₹10 Lakh');
    expect(formatINR(50000)).toBe('₹50k');
    expect(formatINR(500)).toBe('₹500');
    expect(formatINR(0)).toBe('₹0');
  });

  it('formats percentages accurately', () => {
    expect(formatPercent(0.0566)).toBe('5.7%');
    expect(formatPercent(0.956)).toBe('95.6%');
    expect(formatPercent(29.9)).toBe('29.9%');
  });

  it('classifies CIBIL scores according to standard underwriting bands', () => {
    expect(getCibilCategory(900)).toEqual({ label: 'Excellent', level: 'LOW' });
    expect(getCibilCategory(780)).toEqual({ label: 'Excellent', level: 'LOW' });
    expect(getCibilCategory(680)).toEqual({ label: 'Good', level: 'MEDIUM' });
    expect(getCibilCategory(450)).toEqual({ label: 'Fair', level: 'HIGH' });
    expect(getCibilCategory(null)).toEqual({ label: 'Poor', level: 'HIGH' });
  });

  it('formats ISO datetime strings into readable Indian standard format', () => {
    const formatted = formatDateTime('2026-09-08T10:30:00Z');
    expect(formatted).not.toBe('—');
    expect(formatted).toContain('2026');
  });

  it('formats policy source labels cleanly without internal leakages', () => {
    // RBI
    expect(formatPolicySourceLabel('RBI')).toBe('RBI');
    expect(formatPolicySourceLabel({ authority: 'RBI' })).toBe('RBI');
    expect(formatPolicySourceLabel({ source: 'RBI_MASTER_DIRECTION' })).toBe('RBI');

    // HDFC Bank (real)
    expect(formatPolicySourceLabel('HDFC_BANK')).toBe('HDFC Bank');
    expect(formatPolicySourceLabel({ authority: 'HDFC_BANK', is_simulated: false })).toBe('HDFC Bank');
    expect(formatPolicySourceLabel({ source: 'HDFC_BANK_CREDIT_POLICY' })).toBe('HDFC Bank');

    // Internal Demo Policy
    expect(formatPolicySourceLabel('HDFC_INTERNAL_DEMO')).toBe('Internal Demo Policy');
    expect(formatPolicySourceLabel('INTERNAL_DEMO')).toBe('Internal Demo Policy');
    expect(formatPolicySourceLabel({ authority: 'HDFC_BANK', is_simulated: true })).toBe('Internal Demo Policy');
    expect(formatPolicySourceLabel({ authority: 'HDFC_INTERNAL_DEMO', is_simulated: true })).toBe('Internal Demo Policy');

    // Real backend policy references with source_label
    expect(
      formatPolicySourceLabel({
        authority: 'INTERNAL_BANK',
        source_label: 'HDFC_BANK',
      })
    ).toBe('HDFC Bank');
    expect(
      formatPolicySourceLabel({
        authority: 'INTERNAL_BANK',
        source_label: 'INTERNAL_DEMO',
      })
    ).toBe('Internal Demo Policy');
    expect(
      formatPolicySourceLabel({
        authority: 'RBI',
        source_label: 'RBI',
      })
    ).toBe('RBI');

    // Fallbacks
    expect(formatPolicySourceLabel(null)).toBe('Policy');
    expect(formatPolicySourceLabel(undefined)).toBe('Policy');
  });

  it('maps agent review recommendations correctly per specification', () => {
    expect(formatAgentRecommendation('STANDARD_REVIEW')).toBe('Standard Review');
    expect(formatAgentRecommendation('DOCUMENT_FOLLOWUP')).toBe('Request Documents');
    expect(formatAgentRecommendation('OFFICER_INVESTIGATION')).toBe('Officer Investigation');
    expect(formatAgentRecommendation('ESCALATE')).toBe('Escalate for Officer Review');
    expect(formatAgentRecommendation('ESCALATED')).toBe('Escalate for Officer Review');
    expect(formatAgentRecommendation(null)).toBe('Not Reviewed');
    expect(formatAgentRecommendation(undefined)).toBe('Not Reviewed');
    expect(formatAgentRecommendation('NOT_REVIEWED')).toBe('Not Reviewed');
  });

  it('formats document types into human-readable banking labels', () => {
    expect(formatDocumentType('KYC')).toBe('KYC Document');
    expect(formatDocumentType('TAX_RETURN')).toBe('Tax Return (ITR-V)');
    expect(formatDocumentType('BANK_STATEMENT')).toBe('Bank Statement');
    expect(formatDocumentType('PAYSLIP')).toBe('Salary Payslip');
    expect(formatDocumentType('OTHER')).toBe('Other Document');
    expect(formatDocumentType(null)).toBe('Document');
  });

  it('resolves classified document labels dynamically for Evidence Graph records', () => {
    const mockEvidenceData = {
      nodes: [
        {
          node_type: 'DOCUMENT',
          document_id: 'DOC-1',
          title: 'PAYSLIP (01_payslip.txt)',
          value: 'Type: PAYSLIP | Extracted: COMPLETED',
        },
        {
          node_type: 'DOCUMENT',
          document_id: 'DOC-2',
          title: 'BANK_STATEMENT (02_bank_statement.txt)',
          value: 'Type: BANK_STATEMENT | Extracted: COMPLETED',
        },
        {
          node_type: 'DOCUMENT',
          document_id: 'DOC-3',
          title: 'TAX_RETURN (03_tax_return.txt)',
          value: 'Type: TAX_RETURN | Extracted: COMPLETED',
        },
        {
          node_type: 'DOCUMENT',
          document_id: 'DOC-4',
          title: 'KYC (04_kyc.txt)',
          value: 'Type: KYC | Extracted: COMPLETED',
        },
      ],
    };

    // Resolves from evidence graph node when document_type is "OTHER"
    expect(getDocumentDisplayLabel({ document_id: 'DOC-1', document_type: 'OTHER', original_filename: '01_payslip.txt' }, mockEvidenceData)).toBe('Salary Payslip');
    expect(getDocumentDisplayLabel({ document_id: 'DOC-2', document_type: 'OTHER', original_filename: '02_bank_statement.txt' }, mockEvidenceData)).toBe('Bank Statement');
    expect(getDocumentDisplayLabel({ document_id: 'DOC-3', document_type: 'OTHER', original_filename: '03_tax_return.txt' }, mockEvidenceData)).toBe('Tax Return (ITR-V)');
    expect(getDocumentDisplayLabel({ document_id: 'DOC-4', document_type: 'OTHER', original_filename: '04_kyc.txt' }, mockEvidenceData)).toBe('KYC Document');

    // Resolves directly from classified_document_type metadata if available
    expect(getDocumentDisplayLabel({ document_id: 'DOC-X', classified_document_type: 'PAYSLIP', document_type: 'OTHER' }, null)).toBe('Salary Payslip');
    expect(getDocumentDisplayLabel({ document_id: 'DOC-Y', classified_document_type: 'KYC', document_type: 'OTHER' }, null)).toBe('KYC Document');

    // Safe fallback when classified type is unavailable
    expect(getDocumentDisplayLabel({ document_id: 'DOC-Z', document_type: 'CUSTOM_TYPE' }, null)).toBe('Custom Type');
    expect(getDocumentDisplayLabel(null, null)).toBe('Document');
  });
});

