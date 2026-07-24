import api from './client'

export const adminApi = {
  // Dashboard
  fetchDashboardStats: () => api.get('/api/mgmt/stats/'),
  fetchCalendarEvents: () => api.get('/api/mgmt/calendar-events/'),

  // Team
  fetchTeam: () => api.get('/api/mgmt/team/'),
  fetchTeamMember: (id) => api.get(`/api/mgmt/team/${id}/`),
  createTeamMember: (payload) => api.post('/api/mgmt/team/new/', payload),
  updateTeamMember: (id, payload) => api.patch(`/api/mgmt/team/${id}/`, payload),
  deactivateTeamMember: (id) => api.delete(`/api/mgmt/team/${id}/`),

  // Manual entries
  fetchManualEntry: (memberId, date) =>
    api.get('/api/mgmt/manual-entries/', { params: { member_id: memberId, date } }),
  createManualEntry: (payload) => api.post('/api/mgmt/manual-entries/', payload),
  deleteManualEntry: (memberId, date) =>
    api.delete('/api/mgmt/manual-entries/', { params: { member_id: memberId, date } }),

  // Leave requests (supervisor side)
  fetchLeaveRequests: () => api.get('/api/mgmt/leave-requests/'),
  handleLeaveRequest: (requestId, action) =>
    api.post('/api/mgmt/leave-requests/', { request_id: requestId, action }),

  // Change requests (supervisor side)
  fetchChangeRequests: () => api.get('/api/mgmt/change-requests/'),
  handleChangeRequest: (requestId, action) =>
    api.post('/api/mgmt/change-requests/', { request_id: requestId, action }),

  // NFC chip enrollment
  fetchLatestPendingChip: () => api.get('/api/mgmt/pending-chip/'),

  // Month-end closing
  closeMonthGlobal: (month, year) => api.post('/api/mgmt/payouts/close-month/', { month, year }),
  closeEmployeeMonth: (employeeId, month, year) =>
    api.post('/api/mgmt/payouts/close-employee/', { employee_id: employeeId, month, year }),
  reopenEmployeeMonth: (employeeId, month, year) =>
    api.post('/api/mgmt/payouts/reopen-employee/', { employee_id: employeeId, month, year }),
}