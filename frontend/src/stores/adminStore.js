import { defineStore } from 'pinia'
import axios from 'axios'

export const useAdminStore = defineStore('admin', {
  state: () => ({
    user: null,
    teamMembers: [],        
    currentMember: null,   
    calendarEvents: [],     
    
    employees_count: 0,     
    active_employees: 0,    
    on_leave_today: 0,      
    requests_count: 0,
    leave_requests_count: 0,
    change_requests_count: 0,      
    leaveRequests: [],     
    changeRequests: [],    
    isLoading: false,      
  }),

  getters: {
    filteredTeamMembers: (state) => {
      return (searchQuery) => {
        let validMembers = state.teamMembers?.filter(m => m && m.name && m.name !== 'System');

        // Duplikate entfernen
        const seen = new Set();
        validMembers = validMembers?.filter(m => {
          if (seen.has(m.name)) return false;
          seen.add(m.name);
          return true;
        });

        // Alphabetisch sortieren
        validMembers?.sort((a, b) => a.name.localeCompare(b.name));

        if (!searchQuery) return validMembers;
        return validMembers?.filter(m => 
          m.name.toLowerCase().includes(searchQuery.toLowerCase())
        );
      }
    },

    getEventsForMemberAndDate: (state) => {
      return (memberName, date) => {
        return state.calendarEvents?.filter(e => {
          const eDate = new Date(e.date)
          return e.userName === memberName &&
                eDate.getDate() === date.getDate() &&
                eDate.getMonth() === date.getMonth() &&
                eDate.getFullYear() === date.getFullYear()
        })
      }
    }
  },

  actions: {
    resetState() {
      this.user = null
      this.teamMembers = []
      this.currentMember = null 
      this.calendarEvents = []
      this.employees_count = 0
      this.active_employees = 0
      this.on_leave_today = 0
      this.requests_count = 0
      this.change_requests_count = 0
      this.leave_requests_count = 0
      this.leaveRequests = []
      this.changeRequests = []
      this.isLoading = false
    },

    async fetchDashboardData() {
      this.isLoading = true 
      try {
        const token = localStorage.getItem('access_token')
        const { data } = await axios.get(`${import.meta.env.VITE_API_URL}/api/mgmt/stats/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        Object.assign(this, data)
      } catch (error) {
        console.error('Fehler beim Laden der Dashboard-Daten:', error)
      } finally {
        this.isLoading = false
      }
    },

    async fetchTeamMembers() {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/mgmt/team/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        this.teamMembers = res.data
      } catch (error) {
        console.error("Fehler beim Laden der Teammitglieder:", error)
      } finally {
        this.isLoading = false
      }
    },

    async fetchTeamMemberDetail(userId) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/mgmt/team/${userId}/`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.currentMember = res.data
      } catch (error) {
        console.error(`Fehler beim Laden der Details für User ${userId}:`, error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async createTeamMember(employeeData) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const res = await axios.post(
          `${import.meta.env.VITE_API_URL}/api/mgmt/team/new/`, 
          employeeData, 
          { headers: { Authorization: `Bearer ${token}` }}
        )
        
        this.teamMembers.push(res.data)
        this.employees_count++ 
      } catch (error) {
        console.error("Fehler beim Erstellen eines neuen Mitarbeiters:", error)
        alert("Mitarbeiter konnte nicht erstellt werden.")
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async updateTeamMember(userId, updatedData) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        await axios.patch(`${import.meta.env.VITE_API_URL}/api/mgmt/team/${userId}/`, updatedData, {
          headers: { Authorization: `Bearer ${token}` }
        })

        const index = this.teamMembers.findIndex(m => m.id === userId)
        if (index !== -1) {
          this.teamMembers[index] = { ...this.teamMembers[index], ...updatedData }
        }
      } catch (error) {
        console.error(`Fehler beim Aktualisieren des Users ${userId}:`, error)
        alert("Änderungen konnten nicht gespeichert werden.")
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async createManualEntry(payload) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        await axios.post(`${import.meta.env.VITE_API_URL}/api/mgmt/manual-entries/`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        })
        await this.fetchTeamMembers()
      } catch (error) {
        console.error("Fehler beim Erstellen des manuellen Eintrags im Store:", error)
        throw error 
      } finally {
        this.isLoading = false
      }
    },

    async fetchWorkDayDetail(memberId, date) {
      try {
        const token = localStorage.getItem('access_token')
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/mgmt/manual-entries/`, {
          params: { member_id: memberId, date },
          headers: { Authorization: `Bearer ${token}` }
        })
        return res.data
      } catch (error) {
        console.error('Fehler beim Laden des bestehenden Tages:', error)
        throw error
      }
    },

    async deactivateUser(userId) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        await axios.delete(`${import.meta.env.VITE_API_URL}/api/mgmt/team/${userId}/`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        this.teamMembers = this.teamMembers?.filter(m => m.id !== userId)
        this.employees_count-- 
      } catch (error) {
        console.error("Fehler: Benutzer konnte nicht deactivated werden.", error)
        alert("Mitarbeiter konnte nicht deaktiviert werden.")
      } finally {
        this.isLoading = false
      }
    },

    async fetchLeaveRequests() {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/mgmt/leave-requests/`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.leaveRequests = response.data
      } catch (error) {
        console.error("Fehler beim Laden der Anträge:", error)
      } finally {
        this.isLoading = false
      }
    },

    async handleRequestAction(requestId, action) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token');
        await axios.post(`${import.meta.env.VITE_API_URL}/api/mgmt/leave-requests/`, 
          { request_id: requestId, action: action },
          { headers: { Authorization: `Bearer ${token}` }}
        );

        if (this.pendingRequests) {
          this.pendingRequests = this.pendingRequests.filter(r => r.id !== requestId);
        }

        const request = this.leaveRequests.find(r => r.id === requestId);
        if (request) {
          request.status = action === 'approve' ? 'approved' : 'rejected';
          request.status_display = action === 'approve' ? 'Genehmigt' : 'Abgelehnt';
        }
      } catch (error) {
        const verb = action === 'approve' ? 'genehmigt' : 'abgelehnt';
        console.error(`Fehler: Antrag konnte nicht ${verb} werden.`, error);
        alert(`Fehler beim Verarbeiten der Anfrage.`);
      } finally {
        this.isLoading = false
      }
    },

    async approveRequest(id) { await this.handleRequestAction(id, 'approve') },
    
    async rejectRequest(id) { await this.handleRequestAction(id, 'reject') },

    async fetchChangeRequests() {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/mgmt/change-requests/`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.changeRequests = response.data
      } catch (error) {
        console.error("Fehler beim Laden der Anträge:", error)
      } finally {
        this.isLoading = false
      }
    },

    async handleChangeRequestAction(requestId, action) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token');
        await axios.post(`${import.meta.env.VITE_API_URL}/api/mgmt/change-requests/`, 
          { request_id: requestId, action: action },
          { headers: { Authorization: `Bearer ${token}` }}
        );

        const request = this.changeRequests.find(r => r.id === requestId);
        if (request) {
          request.status = action === 'approve' ? 'approved' : 'rejected';
          request.status_display = action === 'approve' ? 'Genehmigt' : 'Abgelehnt';
        }
      } catch (error) {
        const verb = action === 'approve' ? 'genehmigt' : 'abgelehnt';
        console.error(`Fehler: Antrag konnte nicht ${verb} werden.`, error);
        alert(`Fehler beim Verarbeiten der Anfrage.`);
      } finally {
        this.isLoading = false
        await this.fetchChangeRequests();
      }
    },

    async fetchCalendarEvents() {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/mgmt/calendar-events/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        this.calendarEvents = res.data
      } catch (error) {
        console.error('Fehler beim Laden der Kalender-Events:', error)
      } finally {
        this.isLoading = false
      }
    },

    // --- NEUE AKTIONEN FÜR DEN MONATSABSCHLUSS ---

    /**
     * Schließt den gewählten Monat global für alle aktiven Mitarbeiter ab
     */
    async closeMonthGlobal(month, year) {
      const token = localStorage.getItem('access_token')
      try {
        await axios.post(`${import.meta.env.VITE_API_URL}/api/mgmt/payouts/close-month/`, {
          month,
          year
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch (error) {
        console.error('Fehler beim globalen Monatsabschluss im Store:', error)
        throw error
      }
    },

    /**
     * Rechnet den Monat für einen spezifischen Mitarbeiter ab und fixiert die Daten
     */
    async closeEmployeeMonth(memberId, month, year) {
      const token = localStorage.getItem('access_token')
      try {
        await axios.post(`${import.meta.env.VITE_API_URL}/api/mgmt/payouts/close-employee/`, {
          employee_id: memberId,
          month,
          year
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch (error) {
        console.error(`Fehler beim Sperren von User ${memberId}:`, error)
        throw error
      }
    },

    /**
     * Hebt den Abschluss für einen spezifischen Mitarbeiter auf (Sperre löschen)
     */
    async reopenEmployeeMonth(memberId, month, year) {
      const token = localStorage.getItem('access_token')
      try {
        await axios.post(`${import.meta.env.VITE_API_URL}/api/mgmt/payouts/reopen-employee/`, {
          employee_id: memberId,
          month,
          year
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch (error) {
        console.error(`Fehler beim Öffnen von User ${memberId}:`, error)
        throw error
      }
    }
  }
})