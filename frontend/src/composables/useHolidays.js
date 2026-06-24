import { computed } from 'vue'

export function useHolidays() {
  // Gaußsche Osterformel zur Berechnung der beweglichen Feiertage
  const getEasterSunday = (year) => {
    const a = year % 19
    const b = Math.floor(year / 100)
    const c = year % 100
    const d = Math.floor(b / 4)
    const e = b % 4
    const f = Math.floor((b + 8) / 25)
    const g = Math.floor((b - f + 1) / 3)
    const h = (19 * a + b - d - g + 15) % 30
    const i = Math.floor(c / 4)
    const k = c % 4
    const l = (32 + 2 * e + 2 * i - h - k) % 7
    const m = Math.floor((a + 11 * h + 22 * l) / 451)
    const month = Math.floor((h + l - 7 * m + 114) / 31)
    const day = ((h + l - 7 * m + 114) % 31) + 1
    return new Date(year, month - 1, day)
  }

  // Hilfsfunktion zum Addieren von Tagen
  const addDays = (baseDate, days) => {
    const res = new Date(baseDate)
    res.setDate(res.getDate() + days)
    return res
  }

  // Gibt eine Funktion zurück, die die Feiertage für ein bestimmtes Jahr generiert
  const getHolidaysForYear = (year) => {
    if (!year) return []

    // Fixe Feiertage (Monat ist 0-basiert)
    const holidays = [
      { name: 'Neujahr', date: new Date(year, 0, 1) },
      { name: 'Tag der Arbeit', date: new Date(year, 4, 1) },
      { name: 'Tag der Deutschen Einheit', date: new Date(year, 9, 3) },
      { name: 'Allerheiligen', date: new Date(year, 10, 1) },
      { name: '1. Weihnachtstag', date: new Date(year, 11, 25) },
      { name: '2. Weihnachtstag', date: new Date(year, 11, 26) }
    ]

    // Bewegliche Feiertage berechnen
    const easterSunday = getEasterSunday(year)

    holidays.push(
      { name: 'Karfreitag', date: addDays(easterSunday, -2) },
      { name: 'Ostermontag', date: addDays(easterSunday, 1) },
      { name: 'Christi Himmelfahrt', date: addDays(easterSunday, 39) },
      { name: 'Pfingstmontag', date: addDays(easterSunday, 50) },
      { name: 'Fronleichnam', date: addDays(easterSunday, 60) }
    )

    return holidays
  }

  return {
    getHolidaysForYear
  }
}