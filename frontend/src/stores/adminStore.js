import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { adminApi } from '@/api/adminApi'

export const useAdminStore = defineStore('admin', () => {
  const user = ref(null)
  const teamMembers = ref([])
  const currentMember = ref(null)
  const calendarEvents = ref([])

  const employees_count = ref(0)
  const active_employees = ref(0)
  const on_leave_today = ref(0)

  const leaveRequests = ref([])
  const changeRequests = ref([])
  const isLoading = ref(false)

  // ─── Derived state ──────────────────────────────────────────────────
  // These stay `computed()` (not plain functions) so call sites keep
  // using them as properties, e.g. `adminStore.requests_count`.

  const leave_requests_count = computed(
    () => leaveRequests.value.filter((r) => r.status === 'pending').length
  )

  const change_requests_count = computed(
    () => changeRequests.value.filter((r) => r.status === 'pending').length
  )

  const requests_count = computed(() => leave_requests_count.value + change_requests_count.value)

  // These two take arguments, so they were already called as functions
  // in the Options-API version too (a getter returning a function) --
  // call sites don't need to change.
  function filteredTeamMembers(searchQuery) {
    let validMembers = teamMembers.value?.filter((m) => m && m.name && m.name !== 'System')
    const seen = new Set()
    validMembers = validMembers?.filter((m) => {
      if (seen.has(m.name)) return false
      seen.add(m.name)
      return true
    })
    validMembers?.sort((a, b) => a.name.localeCompare(b.name))
    if (!searchQuery) return validMembers
    return validMembers?.filter((m) => m.name.toLowerCase().includes(searchQuery.toLowerCase()))
  }

  function getEventsForMemberAndDate(memberName, date) {
    return calendarEvents.value?.filter((e) => {
      const eDate = new Date(e.date)
      return (
        e.userName === memberName &&
        eDate.getDate() === date.getDate() &&
        eDate.getMonth() === date.getMonth() &&
        eDate.getFullYear() === date.getFullYear()
      )
    })
  }

  // ─── Actions ────────────────────────────────────────────────────────

  function resetState() {
    user.value = null
    teamMembers.value = []
    currentMember.value = null
    calendarEvents.value = []
    employees_count.value = 0
    active_employees.value = 0
    on_leave_today.value = 0
    leaveRequests.value = []
    changeRequests.value = []
    isLoading.value = false
  }

  async function fetchDashboardData() {
    isLoading.value = true
    try {
      const { data } = await adminApi.fetchDashboardStats()
      // Explicit field mapping (rather than a blanket Object.assign) so
      // it's obvious exactly what the dashboard endpoint is expected to return.
      if (data.employees) teamMembers.value = data.employees
      employees_count.value = data.employees_count ?? 0
      active_employees.value = data.active_employees ?? 0
      on_leave_today.value = data.on_leave_today ?? 0
    } catch (error) {
      console.error('Fehler beim Laden der Dashboard-Daten:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTeamMembers() {
    isLoading.value = true
    try {
      const { data } = await adminApi.fetchTeam()
      teamMembers.value = data
    } catch (error) {
      console.error('Fehler beim Laden der Teammitglieder:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTeamMemberDetail(userId) {
    isLoading.value = true
    try {
      const { data } = await adminApi.fetchTeamMember(userId)
      currentMember.value = data
    } catch (error) {
      console.error(`Fehler beim Laden der Details für User ${userId}:`, error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function createTeamMember(employeeData) {
    isLoading.value = true
    try {
      const { data } = await adminApi.createTeamMember(employeeData)

      if (data && data.status !== 'already_assigned') {
        teamMembers.value.push(data)
        employees_count.value++
      }

      return data
    } catch (error) {
      console.error('Fehler beim Erstellen eines neuen Mitarbeiters:', error)
      alert('Mitarbeiter konnte nicht erstellt werden.')
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function updateTeamMember(userId, updatedData) {
    isLoading.value = true
    try {
      const { data } = await adminApi.updateTeamMember(userId, updatedData)

      const index = teamMembers.value.findIndex((m) => m.id === userId)
      if (index !== -1) {
        teamMembers.value[index] = { ...teamMembers.value[index], ...data }
      }
      if (currentMember.value?.id === userId) {
        currentMember.value = data
      }

      return data
    } catch (error) {
      console.error(`Fehler beim Aktualisieren des Users ${userId}:`, error)
      alert('Änderungen konnten nicht gespeichert werden.')
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function createManualEntry(payload) {
    isLoading.value = true
    try {
      await adminApi.createManualEntry(payload)
      await fetchTeamMembers()
    } catch (error) {
      console.error('Fehler beim Erstellen des manuellen Eintrags im Store:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function deleteManualEntry(memberId, date) {
    isLoading.value = true
    try {
      await adminApi.deleteManualEntry(memberId, date)
      await fetchTeamMembers()
    } catch (error) {
      console.error('Fehler beim Löschen des manuellen Eintrags:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function fetchWorkDayDetail(memberId, date) {
    try {
      const { data } = await adminApi.fetchManualEntry(memberId, date)
      return data
    } catch (error) {
      console.error('Fehler beim Laden des bestehenden Tages:', error)
      throw error
    }
  }

  async function deactivateUser(userId) {
    isLoading.value = true
    try {
      await adminApi.deactivateTeamMember(userId)
      teamMembers.value = teamMembers.value?.filter((m) => m.id !== userId)
      employees_count.value--
    } catch (error) {
      console.error('Fehler: Benutzer konnte nicht deaktiviert werden.', error)
      alert('Mitarbeiter konnte nicht deaktiviert werden.')
    } finally {
      isLoading.value = false
    }
  }

  async function fetchLeaveRequests() {
    isLoading.value = true
    try {
      const { data } = await adminApi.fetchLeaveRequests()
      leaveRequests.value = data
    } catch (error) {
      console.error('Fehler beim Laden der Anträge:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function handleRequestAction(requestId, action) {
    isLoading.value = true
    try {
      await adminApi.handleLeaveRequest(requestId, action)

      // Optimistic local update -- once the getter (leave_requests_count)
      // re-evaluates, the badge counter updates automatically.
      const request = leaveRequests.value.find((r) => r.id === requestId)
      if (request) {
        request.status = action === 'approve' ? 'approved' : 'rejected'
        request.status_display = action === 'approve' ? 'Genehmigt' : 'Abgelehnt'
      }
    } catch (error) {
      const verb = action === 'approve' ? 'genehmigt' : 'abgelehnt'
      console.error(`Fehler: Antrag konnte nicht ${verb} werden.`, error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function approveRequest(id) {
    await handleRequestAction(id, 'approve')
  }

  async function rejectRequest(id) {
    await handleRequestAction(id, 'reject')
  }

  async function fetchChangeRequests() {
    isLoading.value = true
    try {
      const { data } = await adminApi.fetchChangeRequests()
      changeRequests.value = data
    } catch (error) {
      console.error('Fehler beim Laden der Anträge:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function handleChangeRequestAction(requestId, action) {
    isLoading.value = true
    try {
      await adminApi.handleChangeRequest(requestId, action)

      // Same optimistic-update policy as handleRequestAction above --
      // no extra refetch, for consistency between the two request types.
      const request = changeRequests.value.find((r) => r.id === requestId)
      if (request) {
        request.status = action === 'approve' ? 'approved' : 'rejected'
        request.status_display = action === 'approve' ? 'Genehmigt' : 'Abgelehnt'
      }
    } catch (error) {
      const verb = action === 'approve' ? 'genehmigt' : 'abgelehnt'
      console.error(`Fehler: Antrag konnte nicht ${verb} werden.`, error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function fetchCalendarEvents() {
    isLoading.value = true
    try {
      const { data } = await adminApi.fetchCalendarEvents()
      calendarEvents.value = data
    } catch (error) {
      console.error('Fehler beim Laden der Kalender-Events:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function closeMonthGlobal(month, year) {
    try {
      await adminApi.closeMonthGlobal(month, year)
    } catch (error) {
      console.error('Fehler beim globalen Monatsabschluss im Store:', error)
      throw error
    }
  }

  async function closeEmployeeMonth(memberId, month, year) {
    try {
      await adminApi.closeEmployeeMonth(memberId, month, year)
    } catch (error) {
      console.error(`Fehler beim Sperren von User ${memberId}:`, error)
      throw error
    }
  }

  async function reopenEmployeeMonth(memberId, month, year) {
    try {
      await adminApi.reopenEmployeeMonth(memberId, month, year)
    } catch (error) {
      console.error(`Fehler beim Öffnen von User ${memberId}:`, error)
      throw error
    }
  }

  async function fetchLatestPendingChip() {
    try {
      const { data } = await adminApi.fetchLatestPendingChip()
      return data
    } catch (error) {
      console.error('Fehler beim Abrufen des ausstehenden Chips:', error)
      return null
    }
  }

  return {
    user,
    teamMembers,
    currentMember,
    calendarEvents,
    employees_count,
    active_employees,
    on_leave_today,
    leaveRequests,
    changeRequests,
    isLoading,

    leave_requests_count,
    change_requests_count,
    requests_count,
    filteredTeamMembers,
    getEventsForMemberAndDate,

    resetState,
    fetchDashboardData,
    fetchTeamMembers,
    fetchTeamMemberDetail,
    createTeamMember,
    updateTeamMember,
    createManualEntry,
    deleteManualEntry,
    fetchWorkDayDetail,
    deactivateUser,
    fetchLeaveRequests,
    handleRequestAction,
    approveRequest,
    rejectRequest,
    fetchChangeRequests,
    handleChangeRequestAction,
    fetchCalendarEvents,
    closeMonthGlobal,
    closeEmployeeMonth,
    reopenEmployeeMonth,
    fetchLatestPendingChip,
  }
})