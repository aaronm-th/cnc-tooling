import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './authStore'
import { generateWorkingHoursPDF } from '@/components/services/pdfService'
import axios from 'axios'

export const useDocumentStore = defineStore('document', () => {
  const authStore = useAuthStore()

  // States
  const documents = ref([]) // Speichert die Liste der Dokumente
  const isFetching = ref(false)
  const isGenerating = ref(false)
  const isUploading = ref(false)
  const isDownloading = ref(false) // Separater Ladestatus für Datei-Downloads
  const lastError = ref(null)

  const adminReportsOverview = ref([])
  const isAdminFetching = ref(false)

  const months = [
    'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
  ]

  // Hilfsmethode für auth-Header, um Code-Duplikate zu vermeiden
  const getAuthHeader = () => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }


  async function fetchEmployeeDocuments(memberId = null) {
    isFetching.value = true
    lastError.value = null
    try {
      const url = memberId 
        ? `${import.meta.env.VITE_API_URL}/api/documents/?employee_id=${memberId}`
        : `${import.meta.env.VITE_API_URL}/api/documents/`

      const response = await axios.get(url, { headers: getAuthHeader() })
      documents.value = response.data
      return response.data
    } catch (error) {
      lastError.value = error.response?.data?.detail || "Fehler beim Laden der Dokumentenliste."
      throw error
    } finally {
      isFetching.value = false
    }
  }

  
  async function downloadEmployeeDocument(documentId, originalFilename) {
    isDownloading.value = true
    lastError.value = null
    try {
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/documents/download/${documentId}/`, 
        { 
          responseType: 'blob',
          headers: getAuthHeader()
        }
      )

      const blob = new Blob([response.data], { type: response.headers['content-type'] })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      link.download = originalFilename
      
      document.body.appendChild(link)
      link.click()
      
      document.body.removeChild(link)
      window.URL.revokeObjectURL(link.href)
      return true
    } catch (error) {
      lastError.value = error.response?.data?.detail || "Fehler beim Herunterladen der Datei."
      throw error
    } finally {
      isDownloading.value = false
    }
  }

  async function _generateReportPDF(month, year, employeeId = null) {
    isGenerating.value = true
    lastError.value = null
    try {
      const params = { month, year }
      if (employeeId) {
        params.employee_id = employeeId
      }

      const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/reports/monthly-detail/`, {
        params,
        headers: getAuthHeader()
      })

      const reportData = {
        ...response.data,
        selectedMonth: month - 1 // Für den 0-basierten JS-Index im pdfService
      }

      // WICHTIG: Wir geben die Daten hier zurück, damit andere Funktionen (wie die Vorschau) sie nutzen können
      return reportData
    } catch (error) {
      lastError.value = error.response?.data?.detail || "Fehler beim Laden der Report-Daten."
      throw error
    } finally {
      isGenerating.value = false
    }
  }

  async function downloadWorkReport(month, year) {
    const data = await _generateReportPDF(month, year)
    if (data) await generateWorkingHoursPDF(data)
    return true
  }

  async function downloadAdminEmployeeReport(memberId, month, year) {
    const data = await _generateReportPDF(month, year, memberId)
    if (data) await generateWorkingHoursPDF(data)
    return true
  }

  async function uploadEmployeeDocument(memberId, formData) {
    isUploading.value = true
    lastError.value = null
    try {
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/documents/upload/${memberId}/`, 
        formData,
        { headers: getAuthHeader() }
      )
      await fetchEmployeeDocuments(memberId)
      return response.data
    } catch (error) {
      lastError.value = error.response?.data?.detail || "Fehler beim Hochladen des Dokuments."
      throw error 
    } finally {
      isUploading.value = false
    }
  }

  async function deleteEmployeeDocument(documentId, memberId) {
    lastError.value = null
    try {
      await axios.delete(`${import.meta.env.VITE_API_URL}/api/documents/delete/${documentId}/`, {
        headers: getAuthHeader()
      })
      await fetchEmployeeDocuments(memberId)
      return true
    } catch (error) {
      lastError.value = error.response?.data?.detail || "Fehler beim Löschen des Dokuments."
      throw error
    }
  }

  async function fetchAdminReportsOverview(month, year) {
    isAdminFetching.value = true
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/reports/admin/overview/`, {
        params: { month, year },
        headers: getAuthHeader()
      })
      adminReportsOverview.value = response.data
      return response.data
    } catch (error) {
      console.error("Fehler beim Laden der Admin-Report-Übersicht:", error)
      throw error
    } finally {
      isAdminFetching.value = false
    }
  }

  return {
    documents,
    isFetching,
    isGenerating,
    isUploading,
    isDownloading,
    lastError,
    months,
    fetchEmployeeDocuments,
    downloadEmployeeDocument,
    downloadWorkReport,
    uploadEmployeeDocument,
    deleteEmployeeDocument,
    adminReportsOverview,
    isAdminFetching,
    fetchAdminReportsOverview,
    downloadAdminEmployeeReport,
    getReportData: _generateReportPDF
  }
})