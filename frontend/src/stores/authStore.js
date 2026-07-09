import { defineStore } from 'pinia'
import axios from 'axios'
import { useAdminStore } from '@/stores/adminStore'




export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    userStats: null, 
    teamMembers: [],
    notes: '', 
    todos: [],
    isLoading: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    // Prüft, ob der User Untergebene hat (für das Admin-Dashboard)
    isSupervisor: (state) => state.user?.is_supervisor || false,
    firstName: (state) => state.user?.first_name || 'User'
  },

  actions: {
    async fetchUser() {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/user/check/`, {
          headers: { Authorization: `Bearer ${token}` }
        })

        this.user = res.data


        return this.user
      } catch (err) {
        this.error = "User-Auth Fehler"
        console.error(err)
      } finally {
        this.isLoading = false
      }
    },

    async fetchUserStats() {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/user-stats/`, {
          headers: { Authorization: `Bearer ${token}` }
        })

        // Direktes Zuweisen der Backend-Daten ohne manuelles Mapping
        this.userStats = res.data

        return this.userStats
      } catch (err) {
        this.error = "Fehler beim Laden der User-Statistiken"
        console.error(err)
      } finally {
        this.isLoading = false
      }
    },

    async fetchTeamMembers() {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/users/all/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        // Mapping direkt im Store erledigen für saubere Daten in der View
        this.teamMembers = res.data
      } catch (error) {
        console.error("Fehler beim Laden der Teammitglieder:", error)
      } finally {
        this.isLoading = false
      }
    },

    async fetchNotes() {
      try {
        const token = localStorage.getItem('access_token')
        // Erwartet vom Backend z.B. { notes: "Hallo Welt" }
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/user/scratchpad/`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        
        this.notes = res.data.notes || ''
        return this.notes
      } catch (err) {
        console.error("Fehler beim Laden der Notizen vom Server:", err)
        // Fallback auf LocalStorage, falls die API offline ist
        const userId = this.user?.id || 'guest'
        this.notes = localStorage.getItem(`dashboard_scratchpad_${userId}`) || ''
      }
    },

    async updateNotes(notesHtml) {
      try {
        const token = localStorage.getItem('access_token')
        await axios.put(`${import.meta.env.VITE_API_URL}/api/user/scratchpad/`, 
          { notes: notesHtml }, 
          { headers: { Authorization: `Bearer ${token}` } }
        )
        
        this.notes = notesHtml
      } catch (err) {
        console.error("Fehler beim Speichern der Notizen auf dem Server:", err)
        throw err // Reichen wir an die Komponente weiter
      }
    },

    async fetchTodos() {
    try {
      const token = localStorage.getItem('access_token')
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/user/todos/`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      this.todos = res.data
      return this.todos
    } catch (err) {
      console.error("Fehler beim Laden der To-Dos:", err)
    }
  },

  async addTodo(text) {
    try {
      const token = localStorage.getItem('access_token')
      const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/user/todos/`, 
        { text },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      // Das vom Server erstellte Todo (inkl. echter ID) lokal hinzufügen
      this.todos.push(res.data)
    } catch (err) {
      console.error("Fehler beim Erstellen des To-Dos:", err)
    }
  },

  async toggleTodo(todoId, completedStatus) {
    try {
      const token = localStorage.getItem('access_token')
      await axios.put(`${import.meta.env.VITE_API_URL}/api/user/todos/`, 
        { id: todoId, completed: completedStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      // Lokalen Zustand anpassen
      const todo = this.todos.find(t => t.id === todoId)
      if (todo) todo.completed = completedStatus
    } catch (err) {
      console.error("Fehler beim Aktualisieren des To-Dos:", err)
    }
  },

  async deleteTodo(todoId) {
    try {
      const token = localStorage.getItem('access_token')
      await axios.delete(`${import.meta.env.VITE_API_URL}/api/user/todos/`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { id: todoId } // Axios benötigt bei DELETE die Daten im 'data' Objekt
      })
      // Lokal entfernen
      this.todos = this.todos.filter(t => t.id !== todoId)
    } catch (err) {
      console.error("Fehler beim Löschen des To-Dos:", err)
    }
  },


  logout() {
    const adminStore = useAdminStore()

    // 1. Lokalen State komplett resetten
    this.user = null
    this.userStats = null
    this.teamMembers = []
    this.notes = ''
    this.todos = []
    this.isLoading = false

    // 2. ALLE denkbaren Token-Varianten aus dem Speicher werfen
    localStorage.removeItem('access_token')
    localStorage.removeItem('token')
    localStorage.removeItem('activeTab')
    localStorage.removeItem('isAdminView')
    localStorage.removeItem('admin_active_tab')

    // 3. Admin-Store zurücksetzen
    adminStore.resetState()

    // 4. Falls globale Axios-Header gesetzt wurden, diese löschen
    if (axios.defaults.headers.common['Authorization']) {
      delete axios.defaults.headers.common['Authorization']
    }
    
    // HIER KEIN window.location.href mehr!
  }
  }
})