import api from './client'

// Note: these endpoints are AllowAny on the backend (Section 2.1 of the docs) --
// the request interceptor simply won't attach a token, which is fine.
export const terminalApi = {
  fetchUsers: () => api.get('/api/terminal/users/'),
  toggle: (employeeId) => api.post('/api/terminal/toggle/', { employee_id: employeeId }),
}