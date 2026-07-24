import api from './client'

export const documentApi = {
  fetchDocuments: (employeeId = null) =>
    api.get('/api/documents/', employeeId ? { params: { employee_id: employeeId } } : {}),

  downloadDocument: (documentId) =>
    api.get(`/api/documents/download/${documentId}/`, { responseType: 'blob' }),

  uploadDocument: (employeeId, formData) =>
    api.post(`/api/documents/upload/${employeeId}/`, formData),

  deleteDocument: (documentId) => api.delete(`/api/documents/delete/${documentId}/`),

  fetchMonthlyReportDetail: (month, year, employeeId = null) =>
    api.get('/api/reports/monthly-detail/', {
      params: employeeId ? { month, year, employee_id: employeeId } : { month, year },
    }),

  fetchAdminReportsOverview: (month, year) =>
    api.get('/api/reports/admin/overview/', { params: { month, year } }),
}