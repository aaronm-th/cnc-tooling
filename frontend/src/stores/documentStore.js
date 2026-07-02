import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useScheduleStore } from './scheduleStore'
import { useAuthStore } from './authStore'
import { generateWorkingHoursPDF } from '@/components/services/pdfService'
import axios from 'axios'

export const useDocumentStore = defineStore('document', () => {
  const scheduleStore = useScheduleStore()
  const authStore = useAuthStore()

  // States
  const documents = ref([]) // Speichert die Liste der Dokumente
  const isFetching = ref(false)
  const isGenerating = ref(false)
  const isUploading = ref(false)
  const isDownloading = ref(false) // Separater Ladestatus für Datei-Downloads
  const lastError = ref(null)

  const months = [
    'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
  ]

  /**
   * Holt alle Dokumente des aktuell eingeteilten Nutzers vom Backend
   */
  async function fetchEmployeeDocuments(memberId = null) {
      isFetching.value = true
      lastError.value = null
      try {

        const url = memberId 
          ? `${import.meta.env.VITE_API_URL}/api/documents/?employee_id=${memberId}`
          : `${import.meta.env.VITE_API_URL}/api/documents/`

        const response = await axios.get(url)
        
        documents.value = response.data
        return response.data
      } catch (error) {
        lastError.value = error.response?.data?.detail || "Fehler beim Laden der Dokumentenliste."
        throw error
      } finally {
        isFetching.value = false
      }
  }

  /**
   * Lädt eine Datei sicher als BLOB herunter und triggert den Browser-Download
   * @param {String|Number} documentId - Die ID des EmployeeDocument
   * @param {String} originalFilename - Der Name, unter dem die Datei gespeichert werden soll
   */
  async function downloadEmployeeDocument(documentId, originalFilename) {
    isDownloading.value = true
    lastError.value = null
    try {
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/documents/download/${documentId}/`, 
        { responseType: 'blob' } // CRITICAL: Erwartet Binärdaten statt JSON
      )

      // Blob-Erzeugung und unsichtbarer Link-Trigger
      const blob = new Blob([response.data], { type: response.headers['content-type'] })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      link.download = originalFilename
      
      document.body.appendChild(link)
      link.click()
      
      // Cleanup
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

  /**
   * Generiert und lädt den Arbeitszeitreport für einen Monat herunter
   */
  async function downloadWorkReport(month, year) {
    isGenerating.value = true
    lastError.value = null
    
    try {
      const fetchedEvents = await scheduleStore.fetchMonthlyWorkSessions(month, year)

      const reportData = {
        monthName: months[month],
        selectedMonth: month,
        year: year,
        userName: authStore.user ? `${authStore.user.first_name} ${authStore.user.last_name}` : 'User',
        userRole: authStore.user?.is_supervisor ? 'Supervisor' : 'Employee',
        events: fetchedEvents 
      }

      await generateWorkingHoursPDF(reportData)
      return true
    } catch (error) {
      lastError.value = error.response?.data?.detail || 
                    (Array.isArray(error.response?.data) ? error.response.data[0] : "Fehler beim Laden der Daten")
      throw error 
    } finally {
      isGenerating.value = false
    }
  }

  /**
   * Lädt ein Dokument für einen spezifischen Mitarbeiter hoch
   */
  async function uploadEmployeeDocument(memberId, formData) {
      isUploading.value = true
      lastError.value = null

      try {
        const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/documents/upload/${memberId}/`, formData)
        
        // Nach erfolgreichem Upload direkt die Liste DIESES Mitarbeiters neu laden,
        // damit das Modal sofort aktuell ist
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
        await axios.delete(`${import.meta.env.VITE_API_URL}/api/documents/delete/${documentId}/`)
        
        await fetchEmployeeDocuments(memberId)
        return true
      } catch (error) {
        lastError.value = error.response?.data?.detail || "Fehler beim Löschen des Dokuments."
        throw error
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
    deleteEmployeeDocument
  }
})