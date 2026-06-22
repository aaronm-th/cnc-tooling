import { computed } from 'vue'

export function useDateFormatter() {
  /**
   * Formatiert ein Datum (String oder Objekt) zu "TT.MM.JJJJ"
   */
  const formatDate = (dateInput) => {
    if (!dateInput) return ''
    const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
    
    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  /**
   * Extrahiert die Uhrzeit "HH:mm" aus einem ISO-String oder Date-Objekt
   * Hilfreich für <input type="time">
   */
  const formatTimeForInput = (dateInput) => {
    if (!dateInput) return ''
    // Falls es ein ISO-String ist (2026-04-17T08:00:00Z)
    if (typeof dateInput === 'string' && dateInput.includes('T')) {
      return dateInput.substring(11, 16)
    }
    // Falls es ein Date Objekt ist
    const date = new Date(dateInput)
    return date.toLocaleTimeString('de-DE', { 
      hour: '2-digit', 
      minute: '2-digit', 
      hour12: false 
    })
  }

  return {
    formatDate,
    formatTimeForInput
  }
}