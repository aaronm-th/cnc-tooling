import { defineStore } from 'pinia'
import { ref } from 'vue'
import { scheduleApi } from '@/api/scheduleApi'

export const useScheduleStore = defineStore('schedule', () => {
  const events = ref([])
  const leaveRequests = ref([])
  const changeRequests = ref([])
  const activeSession = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // --- WORK SESSIONS & DAYS ---

  async function fetchMonthlyWorkSessions(month, year) {
    isLoading.value = true
    try {
      const startDate = `${year}-${String(month + 1).padStart(2, '0')}-01`
      const endDate = new Date(year, month + 1, 0).toISOString().split('T')[0]
      const { data } = await scheduleApi.fetchMonthlyWorkSessions(startDate, endDate)
      return data
    } catch (err) {
      error.value = 'Konnte Arbeitszeiten nicht laden'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchWorkDaySessions(workDayId) {
    isLoading.value = true
    try {
      const { data } = await scheduleApi.fetchWorkDaySessions(workDayId)
      return data // { date: '...', sessions: [...] }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchWorkSessionDetail(sessionId) {
    isLoading.value = true
    try {
      const { data } = await scheduleApi.fetchWorkSessionDetail(sessionId)
      return data
    } finally {
      isLoading.value = false
    }
  }

  async function fetchChangeRequests() {
    try {
      const { data } = await scheduleApi.fetchChangeRequests()
      changeRequests.value = data
    } catch (err) {
      console.error('Fehler beim Laden der Änderungsanträge:', err)
    }
  }

  async function submitShiftChangeRequest(payload) {
    isLoading.value = true
    try {
      // A worksession_id means we're correcting an existing session;
      // otherwise it's a fresh day-level request (e.g. a forgotten day).
      const isSessionCorrection = !!payload.worksession_id

      const { data } = isSessionCorrection
        ? await scheduleApi.submitSessionCorrection(payload.worksession_id, payload)
        : await scheduleApi.submitDayRequest(payload.workday_id, payload)

      return data
    } catch (err) {
      console.error('Fehler beim Schicht-Antrag:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function withdrawShiftChangeRequest(targetId) {
    isLoading.value = true
    try {
      await scheduleApi.withdrawChangeRequest(targetId)
    } finally {
      isLoading.value = false
    }
  }

  // --- CALENDAR & LEAVE ---

  async function fetchCalendarFeed(start, end) {
    if (!start || !end) return
    isLoading.value = true
    try {
      const { data } = await scheduleApi.fetchCalendarFeed(start, end)
      events.value = data
    } finally {
      isLoading.value = false
    }
  }

  async function fetchLeaveRequests() {
    const { data } = await scheduleApi.fetchLeaveRequests()
    leaveRequests.value = data
  }

  async function createLeaveRequest(formData) {
    isLoading.value = true
    try {
      const { data } = await scheduleApi.createLeaveRequest(formData)
      await fetchLeaveRequests()
      return data
    } finally {
      isLoading.value = false
    }
  }

  async function updateLeaveRequest(leaveId, formData) {
    isLoading.value = true
    try {
      const { data } = await scheduleApi.updateLeaveRequest(leaveId, formData)
      await fetchLeaveRequests()
      return data
    } finally {
      isLoading.value = false
    }
  }

  async function deleteLeaveRequest(leaveId) {
    isLoading.value = true
    try {
      await scheduleApi.deleteLeaveRequest(leaveId)
    } catch (err) {
      const serverMessage =
        err.response?.data?.error || err.response?.data?.detail || 'Ein unerwarteter Fehler ist aufgetreten.'
      const customError = new Error(serverMessage)
      customError.response = err.response
      throw customError
    } finally {
      isLoading.value = false
    }
  }

  return {
    events,
    leaveRequests,
    changeRequests,
    activeSession,
    isLoading,
    error,
    fetchMonthlyWorkSessions,
    fetchWorkDaySessions,
    fetchWorkSessionDetail,
    fetchChangeRequests,
    submitShiftChangeRequest,
    withdrawShiftChangeRequest,
    fetchCalendarFeed,
    fetchLeaveRequests,
    createLeaveRequest,
    updateLeaveRequest,
    deleteLeaveRequest,
  }
})