
import { defineStore } from 'pinia'
import axios from 'axios'

export const useNotificationStore = defineStore('notification', {
  state: () => ({
    notifications: [],
    unreadCount: 0
  }),

  actions: {
    // Hilfsmethode für Header (weniger Tipparbeit)
    getHeaders() {
      return { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } };
    },

    async fetchNotifications() {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/notifications/`, this.getHeaders());
      this.notifications = res.data;
      this.updateUnreadCount();
    },

    updateUnreadCount() {
      this.unreadCount = this.notifications.filter(n => !n.read).length;
    },

    async markAsRead(notificationId) {
      // Einzel-Pfad: /api/notifications/ID/
      await axios.patch(`${import.meta.env.VITE_API_URL}/api/notifications/${notificationId}/`, { read: true }, this.getHeaders());
      const n = this.notifications.find(n => n.id === notificationId);
      if (n) { n.read = true; this.updateUnreadCount(); }
    },

    async markAllAsRead() {
      // Custom-Pfad: /api/notifications/mark-all-as-read/
      await axios.patch(`${import.meta.env.VITE_API_URL}/api/notifications/mark-all-as-read/`, {}, this.getHeaders());
      this.notifications.forEach(n => n.read = true);
      this.unreadCount = 0;
    },

    async clearNotification(notificationId) {
      // Standard-Delete-Pfad: /api/notifications/ID/
      await axios.delete(`${import.meta.env.VITE_API_URL}/api/notifications/${notificationId}/`, this.getHeaders());
      this.notifications = this.notifications.filter(n => n.id !== notificationId);
      this.updateUnreadCount();
    },

    async clearAll() {
      // Custom-Pfad: /api/notifications/delete-all/
      await axios.delete(`${import.meta.env.VITE_API_URL}/api/notifications/delete-all/`, this.getHeaders());
      this.notifications = [];
      this.unreadCount = 0;
    }
  }
})


