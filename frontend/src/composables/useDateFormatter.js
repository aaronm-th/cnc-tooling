import { computed } from 'vue'

export function useDateFormatter() {
  /**
   * Formatiert ein Datum (String oder Objekt) zu "TT.MM.JJJJ"
   */
  const formatDate = (dateInput) => {
    if (!dateInput) return ''
    
    let date;

    if (typeof dateInput === 'string') {
      // Falls das Datum Punkte enthält (z.B. "15.07.2026"), wandeln wir es 
      // für den JS-Parser temporär in das lesbare ISO-Format "2026-07-15" um
      if (dateInput.includes('.')) {
        const parts = dateInput.split('.')
        if (parts.length === 3) {
          const day = parts[0].trim().padStart(2, '0')
          const month = parts[1].trim().padStart(2, '0')
          const year = parts[2].trim().substring(0, 4)
          date = new Date(`${year}-${month}-${day}T00:00:00`)
        }
      } 
      
      // Falls es kein deutsches Format war, nutzen wir den Standard-Parser
      if (!date || isNaN(date.getTime())) {
        date = new Date(dateInput)
      }
    } else {
      date = dateInput
    }

    // Schutz vor "Invalid Date" Objekten[cite: 3]
    if (!date || isNaN(date.getTime())) return ''
    
    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      timeZone: 'Europe/Berlin' // Verhindert das Umspringen des Datums[cite: 3]
    })
  }
 
  const formatTime = (dateStr) => {
    if (!dateStr) return '--:--'
    return new Date(dateStr).toLocaleTimeString('de-DE', {
      hour: '2-digit',
      minute: '2-digit'
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
    formatTimeForInput,
    formatTime
  }
}