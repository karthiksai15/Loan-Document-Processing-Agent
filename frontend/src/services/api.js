import axios from 'axios';

const rawBase = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
const API_BASE = rawBase
  ? (rawBase.endsWith('/api/v1') ? rawBase : `${rawBase}/api/v1`)
  : '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const TOKEN_STORAGE_KEY = 'genbank_access_token';

// Request interceptor to attach Authorization: Bearer <token>
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined' && window.localStorage) {
    const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor for unified error message extraction
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected network error occurred';
    const err = new Error(message);
    err.status = error.response?.status;
    err.data = error.response?.data;
    return Promise.reject(err);
  }
);

export const api = {
  // Authentication (Google OAuth 2.0 & Session)
  authGoogle: (idToken, role = null) =>
    apiClient.post('/auth/google', { id_token: idToken, role }),
  getMe: () => apiClient.get('/auth/me'),

  // System Health & Info
  getSystemHealth: () => apiClient.get('/health'),
  getSystemInfo: () => apiClient.get('/system/info'),

  // Dashboard & Application listing
  getDashboardOverview: () => apiClient.get('/applications/dashboard/overview'),
  seedDemoData: () => apiClient.post('/applications/seed-demo-data'),
  getApplications: () => apiClient.get('/applications'),
  getApplication: (appId) => apiClient.get(`/applications/${appId}`),

  // Verification & Evidence Graph
  getVerification: (appId) => apiClient.get(`/applications/${appId}/verification`),
  verifyApplication: (appId) => apiClient.post(`/applications/${appId}/verify`),
  getEvidence: (appId) => apiClient.get(`/applications/${appId}/evidence`),
  buildEvidence: (appId) => apiClient.post(`/applications/${appId}/evidence`),

  // ML Risk & Review Score
  predictRisk: (appId) => apiClient.post(`/applications/${appId}/risk/predict`),
  getReviewScore: (appId) => apiClient.get(`/applications/${appId}/review-score`),
  calculateReviewScore: (appId) => apiClient.post(`/applications/${appId}/review-score`),

  // Documents
  listDocuments: (appId) => apiClient.get(`/applications/${appId}/documents`),
  getDocumentText: (docId) => apiClient.get(`/documents/${docId}/text`),
  getDocumentFields: (docId) => apiClient.get(`/documents/${docId}/extracted-fields`),
  getDocumentValidation: (docId) => apiClient.get(`/documents/${docId}/validation`),
  getDocumentDownloadUrl: (docId) => `${API_BASE}/documents/${docId}/download`,

  // AI Review Agent (LangGraph)
  runAgentReview: (appId, forceRebuild = false) =>
    apiClient.post(`/applications/${appId}/agent/review`, { force_rebuild: forceRebuild }),
  getAgentReview: (appId) => apiClient.get(`/applications/${appId}/agent/review`),
  getAgentTrace: (appId) => apiClient.get(`/applications/${appId}/agent/trace`),

  // Confidence & Human Review Gate
  getHumanReview: (appId) => apiClient.get(`/applications/${appId}/human-review`),
  evaluateHumanReview: (appId) => apiClient.post(`/applications/${appId}/human-review`),
  acknowledgeReview: (appId, officerId) =>
    apiClient.post(`/applications/${appId}/human-review/acknowledge`, { officer_id: officerId }),
  addOfficerNote: (appId, officerId, note) =>
    apiClient.post(`/applications/${appId}/human-review/note`, { officer_id: officerId, note }),
  requestDocuments: (appId, officerId, documents, reason) =>
    apiClient.post(`/applications/${appId}/human-review/request-documents`, {
      officer_id: officerId,
      documents,
      reason,
    }),
  recordHumanDecision: (appId, { officerId, decision, decisionReason, overrideReason, notes }) =>
    apiClient.post(`/applications/${appId}/human-review/decision`, {
      officer_id: officerId,
      decision,
      decision_reason: decisionReason,
      override_reason: overrideReason,
      notes,
    }),
  getHumanReviewAudit: (appId) => apiClient.get(`/applications/${appId}/human-review/audit`),

  // Decision History & Feedback
  getDecisionHistory: (appId) => apiClient.get(`/applications/${appId}/decision-history`),
  submitFeedback: (appId, { officerId, feedback, category }) =>
    apiClient.post(`/applications/${appId}/feedback`, {
      officer_id: officerId,
      feedback,
      category,
    }),

  // Policies (RAG Knowledge Base)
  listPolicies: (params = {}) => apiClient.get('/policies', { params }),
  searchPolicies: (query, options = {}) =>
    apiClient.post('/policies/search', {
      query,
      top_k: options.topK || 5,
      filter_authority: options.authority || null,
      filter_policy_type: options.policyType || null,
      filter_category: options.category || null,
    }),

  // Customer Portal (Phase 1)
  getCustomerApplications: () => apiClient.get('/customer/applications'),
  createCustomerApplication: (payload) => apiClient.post('/customer/applications', payload),
  getCustomerApplication: (appId) => apiClient.get(`/customer/applications/${appId}`),
  uploadCustomerDocument: (appId, file, documentType) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    return apiClient.post(`/customer/applications/${appId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  deleteCustomerDocument: (appId, docId) =>
    apiClient.delete(`/customer/applications/${appId}/documents/${docId}`),
  submitCustomerApplication: (appId) =>
    apiClient.post(`/customer/applications/${appId}/submit`),
};
