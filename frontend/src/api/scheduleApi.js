import api from './client'

// Some IDs arrive prefixed as 'wd-123' (from calendar event objects) --
// this strips that prefix consistently everywhere it's needed.
const cleanId = (id) => String(id).replace('wd-', '')

export const scheduleApi = {
  fetchMonthlyWorkSessions: (startDate, endDate) =>
    api.get('/api/work-days/', { params: { start: startDate, end: endDate } }),

  fetchWorkDaySessions: (workDayId) =>
    api.get(`/api/workday-details/${cleanId(workDayId)}/`),

  fetchWorkSessionDetail: (sessionId) =>
    api.get(`/api/work-session-request/${cleanId(sessionId)}/`),

  fetchChangeRequests: () => api.get('/api/change-request/'),

  // Correcting an existing WorkSession
  submitSessionCorrection: (worksessionId, payload) =>
    api.post(`/api/work-session-request/${cleanId(worksessionId)}/`, payload),

  // Reporting a day that has no session at all yet
  submitDayRequest: (workdayId, payload) =>
    api.post(`/api/work-day-request/${cleanId(workdayId)}/`, payload),

  withdrawChangeRequest: (targetId) =>
    api.delete(`/api/work-session-request/${cleanId(targetId)}/`),

  fetchCalendarFeed: (start, end) =>
    api.get('/api/user-calendar/', { params: { start, end } }),

  fetchLeaveRequests: () => api.get('/api/leave-request/'),
  createLeaveRequest: (formData) => api.post('/api/leave-request/', formData),
  updateLeaveRequest: (leaveId, formData) =>
    api.put(`/api/leave-request/${cleanId(leaveId)}/`, formData),
  deleteLeaveRequest: (leaveId) => api.delete(`/api/leave-request/${cleanId(leaveId)}/`),

  cleanId,
}