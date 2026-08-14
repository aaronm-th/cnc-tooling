import { defineStore } from 'pinia'
import { ref } from 'vue'
import { generateWorkingHoursPDF } from '@/components/services/pdfService'
import { documentApi } from '@/api/documentApi'

export const useDocumentStore = defineStore('document', () => {
  const documents = ref([])
  const isFetching = ref(false)
  const isGenerating = ref(false)
  const isUploading = ref(false)
  const isDownloading = ref(false)
  const lastError = ref(null)

  const adminReportsOverview = ref([])
  const isAdminFetching = ref(false)

  const months = [
    'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
  ]

  async function fetchEmployeeDocuments(memberId = null) {
    isFetching.value = true
    lastError.value = null
    try {
      const { data } = await documentApi.fetchDocuments(memberId)
      documents.value = data
      return data
    } catch (error) {
      lastError.value = error.response?.data?.detail || 'Fehler beim Laden der Dokumentenliste.'
      throw error
    } finally {
      isFetching.value = false
    }
  }

  async function downloadEmployeeDocument(documentId, originalFilename) {
    isDownloading.value = true
    lastError.value = null
    try {
      const response = await documentApi.downloadDocument(documentId)

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
      lastError.value = error.response?.data?.detail || 'Fehler beim Herunterladen der Datei.'
      throw error
    } finally {
      isDownloading.value = false
    }
  }

  async function _generateReportPDF(month, year, employeeId = null) {
    isGenerating.value = true
    lastError.value = null
    try {
      const { data } = await documentApi.fetchMonthlyReportDetail(month, year, employeeId)
      return { ...data, selectedMonth: month - 1 } // 0-based month index for pdfService
    } catch (error) {
      lastError.value = error.response?.data?.detail || 'Fehler beim Laden der Report-Daten.'
      throw error
    } finally {
      isGenerating.value = false
    }
  }

  async function downloadWorkReport(month, year, targetWindow = null) {
    const data = await _generateReportPDF(month, year)
    if (data) await generateWorkingHoursPDF(data, targetWindow)
    return true
  }

  async function downloadAdminEmployeeReport(memberId, month, year, targetWindow = null) {
    const data = await _generateReportPDF(month, year, memberId)
    if (data) await generateWorkingHoursPDF(data, targetWindow)
    return true
  }

  async function uploadEmployeeDocument(memberId, formData) {
    isUploading.value = true
    lastError.value = null
    try {
      const { data } = await documentApi.uploadDocument(memberId, formData)
      await fetchEmployeeDocuments(memberId)
      return data
    } catch (error) {
      lastError.value = error.response?.data?.detail || 'Fehler beim Hochladen des Dokuments.'
      throw error
    } finally {
      isUploading.value = false
    }
  }

  async function deleteEmployeeDocument(documentId, memberId) {
    lastError.value = null
    try {
      await documentApi.deleteDocument(documentId)
      await fetchEmployeeDocuments(memberId)
      return true
    } catch (error) {
      lastError.value = error.response?.data?.detail || 'Fehler beim Löschen des Dokuments.'
      throw error
    }
  }

  async function fetchAdminReportsOverview(month, year) {
    isAdminFetching.value = true
    try {
      const { data } = await documentApi.fetchAdminReportsOverview(month, year)
      adminReportsOverview.value = data
      return data
    } catch (error) {
      console.error('Fehler beim Laden der Admin-Report-Übersicht:', error)
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
    getReportData: _generateReportPDF,
  }
})