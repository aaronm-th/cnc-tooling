import { defineStore } from 'pinia'
import { ref } from 'vue'
import { terminalApi } from '@/api/terminalApi'

export const useTerminalStore = defineStore('terminal', () => {
  const teamMembers = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  async function fetchTerminalUsers() {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await terminalApi.fetchUsers()
      teamMembers.value = data
    } catch (err) {
      error.value = 'Daten konnten nicht geladen werden.'
      console.error('Terminal-Fetch Error:', err)
    } finally {
      isLoading.value = false
    }
  }

  async function toggleEmployeeStempeln(employeeId) {
    error.value = null
    try {
      const { data } = await terminalApi.toggle(employeeId)

      if (data.status === 'warning') {
        return data
      }

      const index = teamMembers.value.findIndex((m) => m.id === employeeId)
      if (index !== -1) {
        teamMembers.value[index].status = data.new_status
      }

      return data
    } catch (err) {
      const message = err.response?.data?.error || 'Fehler beim Stempeln.'
      throw new Error(message)
    }
  }

  return { teamMembers, isLoading, error, fetchTerminalUsers, toggleEmployeeStempeln }
})