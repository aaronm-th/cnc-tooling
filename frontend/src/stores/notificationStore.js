import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationApi } from '@/api/notificationApi'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  const unreadCount = ref(0)

  function updateUnreadCount() {
    unreadCount.value = notifications.value.filter((n) => !n.read).length
  }

  async function fetchNotifications() {
    const { data } = await notificationApi.fetchAll()
    notifications.value = data
    updateUnreadCount()
  }

  async function markAsRead(notificationId) {
    await notificationApi.markAsRead(notificationId)
    const n = notifications.value.find((n) => n.id === notificationId)
    if (n) {
      n.read = true
      updateUnreadCount()
    }
  }

  async function markAllAsRead() {
    await notificationApi.markAllAsRead()
    notifications.value.forEach((n) => {
      n.read = true
    })
    unreadCount.value = 0
  }

  async function clearNotification(notificationId) {
    await notificationApi.delete(notificationId)
    notifications.value = notifications.value.filter((n) => n.id !== notificationId)
    updateUnreadCount()
  }

  async function clearAll() {
    await notificationApi.deleteAll()
    notifications.value = []
    unreadCount.value = 0
  }

  return {
    notifications,
    unreadCount,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    clearNotification,
    clearAll,
  }
})