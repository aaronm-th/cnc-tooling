import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { authApi } from '@/api/authApi'
import { authTokenService } from '@/services/authTokenService'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const userStats = ref(null)
  const teamMembers = ref([])
  const notes = ref('')
  const todos = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  const isAuthenticated = computed(() => !!user.value)
  const isSupervisor = computed(() => user.value?.is_supervisor || false)
  const firstName = computed(() => user.value?.first_name || 'User')

  async function fetchUser() {
    isLoading.value = true
    try {
      const { data } = await authApi.fetchMe()
      user.value = data
      return user.value
    } catch (err) {
      error.value = 'User-Auth Fehler'
      console.error(err)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchUserStats() {
    isLoading.value = true
    try {
      const { data } = await authApi.fetchStats()
      userStats.value = data
      return userStats.value
    } catch (err) {
      error.value = 'Fehler beim Laden der User-Statistiken'
      console.error(err)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTeamMembers() {
    isLoading.value = true
    try {
      const { data } = await authApi.fetchAllUsers()
      teamMembers.value = data
    } catch (err) {
      console.error('Fehler beim Laden der Teammitglieder:', err)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchNotes() {
    if (!authTokenService.hasToken()) return

    try {
      const { data } = await authApi.fetchScratchpad()
      notes.value = data.notes || ''
      return notes.value
    } catch (err) {
      console.error('Fehler beim Laden der Notizen vom Server:', err)
      // Offline-Fallback: letzten bekannten Stand aus localStorage nehmen
      const userId = user.value?.id || 'guest'
      notes.value = localStorage.getItem(`dashboard_scratchpad_${userId}`) || ''
    }
  }

  async function updateNotes(notesHtml) {
    try {
      await authApi.updateScratchpad(notesHtml)
      notes.value = notesHtml
    } catch (err) {
      console.error('Fehler beim Speichern der Notizen auf dem Server:', err)
      throw err
    }
  }

  async function fetchTodos() {
    if (!authTokenService.hasToken()) return

    try {
      const { data } = await authApi.fetchTodos()
      todos.value = data
      return todos.value
    } catch (err) {
      console.error('Fehler beim Laden der To-Dos:', err)
    }
  }

  async function addTodo(text) {
    try {
      const { data } = await authApi.createTodo(text)
      todos.value.push(data)
    } catch (err) {
      console.error('Fehler beim Erstellen des To-Dos:', err)
    }
  }

  async function toggleTodo(todoId, completedStatus) {
    try {
      await authApi.updateTodo(todoId, completedStatus)
      const todo = todos.value.find((t) => t.id === todoId)
      if (todo) todo.completed = completedStatus
    } catch (err) {
      console.error('Fehler beim Aktualisieren des To-Dos:', err)
    }
  }

  async function deleteTodo(todoId) {
    try {
      await authApi.deleteTodo(todoId)
      todos.value = todos.value.filter((t) => t.id !== todoId)
    } catch (err) {
      console.error('Fehler beim Löschen des To-Dos:', err)
    }
  }

  function logout() {
    const adminStore = useAdminStore()

    user.value = null
    userStats.value = null
    teamMembers.value = []
    notes.value = ''
    todos.value = []
    isLoading.value = false

    // Clears access/refresh token + all legacy/UI-state keys in one place
    authTokenService.clearAll()
    adminStore.resetState()

    // No manual axios.defaults cleanup needed anymore -- the shared
    // client (src/api/client.js) reads the token fresh on every request
    // rather than caching it in a global default header.
  }

  return {
    user,
    userStats,
    teamMembers,
    notes,
    todos,
    isLoading,
    error,
    isAuthenticated,
    isSupervisor,
    firstName,
    fetchUser,
    fetchUserStats,
    fetchTeamMembers,
    fetchNotes,
    updateNotes,
    fetchTodos,
    addTodo,
    toggleTodo,
    deleteTodo,
    logout,
  }
})