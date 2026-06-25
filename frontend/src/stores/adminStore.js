import { defineStore } from 'pinia'
import axios from 'axios'

export const useAdminStore = defineStore('admin', {
  state: () => ({
    user: null,
    employees: [],          // von 'teamMembers' geändert
    currentMember: null,   
    calendarEvents: [],    
    employees_count: 0,     // von 'employeesCount' geändert
    active_employees: 0,    // von 'activeEmployees' geändert
    on_leave_today: 0,      // von 'onLeaveTodayCount' geändert
    requests_count: 0,      // von 'pendingRequests: []' geändert, da das Backend eine Zahl schickt!
    leaveRequests: [],     
    changeRequests: [],    
    isLoading: false,      
  }),

  getters: {

    filteredTeamMembers: (state) => {
      return (searchQuery) => {
        // 1. Filter ungültige Einträge & "System" aus
        let validMembers = state.teamMembers?.filter(m => m && m.name && m.name !== 'System');

        // 2. Duplikate anhand des Namens entfernen (falls nötig)
        const seen = new Set();
        validMembers = validMembers?.filter(m => {
          if (seen.has(m.name)) return false;
          seen.add(m.name);
          return true;
        });

        // 3. Alphabetisch nach Name sortieren
        validMembers?.sort((a, b) => a.name.localeCompare(b.name));

        // 4. Suchfilter anwenden
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
      this.employees = []
      this.currentMember = null 
      this.calendarEvents = []
      this.employees_count = 0
      this.active_employees = 0
      this.on_leave_today = 0
      this.requests_count = 0
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

        // Nutzt Object.assign, um alle Felder direkt auf 'this' zu übertragen
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
        // URL bleibt auf dem Kollektions-Endpunkt
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

    // ************************************************************
    // NEU: CRUD-ACTIONS FÜR EINZELNE MITARBEITER (TeamMemberDetailView)
    // ************************************************************

    async fetchTeamMemberDetail(userId) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        // GET an /api/mgmt/team/<id>/
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

    async createTeamMember(employeeData) { // Nimmt jetzt das ganze Objekt entgegen
      this.isLoading = true
      try {

        const token = localStorage.getItem('access_token')

        const res = await axios.post(
          `${import.meta.env.VITE_API_URL}/api/mgmt/team/new/`, 
          employeeData, // Schickt name, email, work_days_schema, etc. gesammelt mit
          { headers: { Authorization: `Bearer ${token}` }}
        )
        
        this.teamMembers.push(res.data)
        this.employeesCount++
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

        // Lokale Liste direkt updaten, damit die UI ohne Refresh aktuell ist
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

    async deactivateUser(userId) {
      this.isLoading = true
      try {
        const token = localStorage.getItem('access_token')
        // MODIFIZIERT: Nutzt jetzt die neue REST-konforme URL /api/mgmt/team/<id>/
        await axios.delete(`${import.meta.env.VITE_API_URL}/api/mgmt/team/${userId}/`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        this.teamMembers = this.teamMembers?.filter(m => m.id !== userId)
        this.employeesCount--

      } catch (error) {
        console.error("Fehler: Benutzer konnte nicht deaktiviert werden.", error)
        alert("Mitarbeiter konnte nicht deaktiviert werden.")
      } finally {
        this.isLoading = false
      }
    },

    // ******************************
    // LEAVE REQUESTS & CHANGE REQUESTS (Unverändert)
    // ******************************

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

        this.pendingRequests = this.pendingRequests?.filter(r => r.id !== requestId);

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
  }
})