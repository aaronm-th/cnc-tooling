import api from './client'

export const authApi = {
  login: (username, password) => api.post('/api/login/', { username, password }),

  fetchMe: () => api.get('/api/user/check/'),
  fetchStats: () => api.get('/api/user-stats/'),
  fetchAllUsers: () => api.get('/api/users/all/'),

  fetchScratchpad: () => api.get('/api/user/scratchpad/'),
  updateScratchpad: (notes) => api.put('/api/user/scratchpad/', { notes }),

  fetchTodos: () => api.get('/api/user/todos/'),
  createTodo: (text) => api.post('/api/user/todos/', { text }),
  updateTodo: (id, completed) => api.put('/api/user/todos/', { id, completed }),
  deleteTodo: (id) => api.delete('/api/user/todos/', { data: { id } }),
}