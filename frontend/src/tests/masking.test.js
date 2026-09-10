import { describe, it, expect } from 'vitest';
import { maskAadhaar, maskPAN, maskBankAccount, maskDocumentText } from '../services/masking';

describe('PII Masking Utilities', () => {
  it('masks 12-digit Aadhaar numbers correctly', () => {
    expect(maskAadhaar('123456789012')).toBe('XXXX-XXXX-9012');
    expect(maskAadhaar('1234 5678 9012')).toBe('XXXX-XXXX-9012');
    expect(maskAadhaar('1234-5678-9012')).toBe('XXXX-XXXX-9012');
  });

  it('masks 10-character PAN cards correctly', () => {
    expect(maskPAN('ABCDE1234F')).toBe('XXXXX1234X');
    expect(maskPAN('abcde9876z')).toBe('XXXXX9876X');
  });

  it('masks bank account numbers preserving last 4 digits', () => {
    expect(maskBankAccount('1234567890')).toBe('XXXXXX7890');
    expect(maskBankAccount('98765432101234')).toBe('XXXXXX1234');
  });

  it('masks document text containing embedded PII', () => {
    const rawText = 'Applicant Aadhaar: 9876 5432 1098. PAN Card: ABCDE1234F. Account No: 1122334455.';
    const masked = maskDocumentText(rawText);
    expect(masked).toContain('XXXX-XXXX-1098');
    expect(masked).toContain('XXXXX1234X');
    expect(masked).toContain('XXXXXX4455');
    expect(masked).not.toContain('9876 5432');
    expect(masked).not.toContain('ABCDE1234F');
  });
});
