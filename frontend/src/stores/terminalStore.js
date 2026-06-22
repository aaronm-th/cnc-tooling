import { defineStore } from 'pinia'
import axios from 'axios'

export const useTerminalStore = defineStore('terminal', {
  state: () => ({
    teamMembers: [],
    isLoading: false,
    error: null
  }),

  actions: {
    // 1. Liste laden (Öffentlich)
    async fetchTerminalUsers() {
      this.isLoading = true
      this.error = null
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/terminal/users/`)
        // Da 'name', 'initials' und 'status' direkt aus Django kommen, 
        // können wir sie einfach übernehmen.
        this.teamMembers = res.data
      } catch (err) {
        this.error = "Daten konnten nicht geladen werden."
        console.error("Terminal-Fetch Error:", err)
      } finally {
        this.isLoading = false
      }
    },

    // 2. Stempeln (Öffentlich)
    async toggleEmployeeStempeln(employeeId) {
      this.error = null
      try {
        // Hinweis: Kein Token nötig, da AllowAny im Backend
        const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/terminal/toggle/`, {
          employee_id: employeeId
        })

        // Wir prüfen, ob das Backend eine Warnung (Timer) zurückgibt
        if (res.data.status === 'warning') {
          return res.data // Wir geben das Objekt zurück, damit die View die Sekunden anzeigen kann
        }

        // Erfolg: Wir finden den Mitarbeiter in der lokalen Liste und updaten den Status
        const index = this.teamMembers.findIndex(m => m.id === employeeId)
        if (index !== -1) {
          this.teamMembers[index].status = res.data.new_status
        }

        return res.data
      } catch (err) {
        // Falls ein echter Fehler (z.B. 403 Krank/Urlaub) kommt
        const message = err.response?.data?.error || "Fehler beim Stempeln."
        throw new Error(message)
      }
    }
  }
})