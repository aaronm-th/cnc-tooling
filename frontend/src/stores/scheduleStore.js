import { defineStore } from 'pinia'
import axios from 'axios'

export const useScheduleStore = defineStore('schedule', {
  state: () => ({
    events: [],           
    leaveRequests: [],
    changeRequests: [],    
    activeSession: null,  
    isLoading: false,
    error: null
  }),

  actions: {
    getAuthHeader() {
      const token = localStorage.getItem('access_token')
      return { Authorization: `Bearer ${token}` }
    },

    cleanId(id) {
      return String(id).replace('wd-', '')
    },

    // --- WORK SESSIONS & DAYS ---

    async fetchMonthlyWorkSessions(month, year) {
      this.isLoading = true;
      try {
        const startDate = `${year}-${String(month + 1).padStart(2, '0')}-01`;
        const endDate = new Date(year, month + 1, 0).toISOString().split('T')[0];

        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/work-days/`, {
          params: { start: startDate, end: endDate },
          headers: this.getAuthHeader()
        });
        return res.data; 
      } catch (err) {
        this.error = "Konnte Arbeitszeiten nicht laden";
        throw err; 
      } finally {
        this.isLoading = false;
      }
    },

    async fetchWorkDaySessions(workDayId) {
      this.isLoading = true
      try {
        const id = this.cleanId(workDayId)
        const res = await axios.get(
          `${import.meta.env.VITE_API_URL}/api/workday-details/${id}/`, 
          { headers: this.getAuthHeader() }
        )
        return res.data // { date: '...', sessions: [...] }
      } catch (error) {
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async fetchWorkSessionDetail(sessionId) {
      this.isLoading = true
      try {
        const id = this.cleanId(sessionId)
        const res = await axios.get(
          `${import.meta.env.VITE_API_URL}/api/work-session-request/${id}/`, 
          { headers: this.getAuthHeader() }
        )
        return res.data
      } catch (error) {
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async fetchChangeRequests() {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/change-request/`, {
          headers: this.getAuthHeader()
        })
        // Korrigiert: Jetzt wird der changeRequests-State befüllt!
        this.changeRequests = res.data
      } catch (error) {
        console.error("Fehler beim Laden der Änderungsanträge:", error)
      }
    },

  async submitShiftChangeRequest(payload) {
    this.isLoading = true
    try {
      // Wenn eine worksession_id existiert ODER es sich um einen Eintrag handelt,
      // der bereits eine ID besitzt, aber keine originale Session hat.
      const isSessionCorrection = !!payload.worksession_id;
      
      // Falls keine Session existiert, aber das Objekt eine ID hat, ist es ein Update eines bestehenden Day-Level-Requests
      const isDayRequestUpdate = !payload.worksession_id && !!payload.id;

      let url;
      if (isSessionCorrection) {
        url = `${import.meta.env.VITE_API_URL}/api/work-session-request/${this.cleanId(payload.worksession_id)}/`;
      } else {
        url = `${import.meta.env.VITE_API_URL}/api/work-day-request/${this.cleanId(payload.workday_id)}/`;
      }

      const res = await axios.post(url, payload, { 
        headers: this.getAuthHeader() 
      });
      
      return res.data;
    } catch (error) {
      console.error("Fehler beim Schicht-Antrag:", error);
      throw error;
    } finally {
      this.isLoading = false;
    }
  },

    async withdrawShiftChangeRequest(targetId) {
      this.isLoading = true
      try {
        
        const id = this.cleanId(targetId)
        await axios.delete(
          `${import.meta.env.VITE_API_URL}/api/work-session-request/${id}/`, 
          { headers: this.getAuthHeader() }
        )
        
      } catch (error) {
        throw error
      } finally {
        this.isLoading = false
      }
    },

    // --- CALENDER & LEAVE (Unverändert, nur Cleanup) ---

    async fetchCalendarFeed(start, end) {
      if (!start || !end) return
      this.isLoading = true
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/user-calendar/`, {
          params: { start, end },
          headers: this.getAuthHeader()
        })
        this.events = res.data
      } finally {
        this.isLoading = false
      }
    },

    async fetchLeaveRequests() {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/leave-request/`, {
        headers: this.getAuthHeader()
      })

      this.leaveRequests = res.data
    },

    async createLeaveRequest(formData) {
      this.isLoading = true
      try {
        const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/leave-request/`, formData, { headers: this.getAuthHeader() })
        await this.fetchLeaveRequests() 
        return res.data
      } finally { this.isLoading = false }
    },

    async deleteLeaveRequest(leaveId) {
      this.isLoading = true
      try {
        const id = this.cleanId(leaveId)
        await axios.delete(
          `${import.meta.env.VITE_API_URL}/api/leave-request/${id}/`, 
          { headers: this.getAuthHeader() }
        )
      } catch (error) {
        // Extrahiere die Fehlermeldung vom Backend
        const serverMessage = error.response?.data?.error || error.response?.data?.detail || "Ein unerwarteter Fehler ist aufgetreten."
        
        // Erstelle einen neuen Fehler mit der Nachricht vom Server
        const customError = new Error(serverMessage)
        customError.response = error.response // Falls du den Statuscode noch brauchst
        throw customError
      } finally {
        this.isLoading = false
      }
    },

  }
})