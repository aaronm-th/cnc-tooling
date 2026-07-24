import api from './client'

export const notificationApi = {
  fetchAll: () => api.get('/api/notifications/'),
  markAsRead: (id) => api.patch(`/api/notifications/${id}/`, { read: true }),
  markAllAsRead: () => api.patch('/api/notifications/mark-all-as-read/', {}),
  delete: (id) => api.delete(`/api/notifications/${id}/`),
  deleteAll: () => api.delete('/api/notifications/delete-all/'),
}