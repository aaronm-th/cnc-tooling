<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { useEventStyles } from '@/composables/useEventStyles'
import EventTooltip from '@/components/tooltips/EventTooltip.vue'
import ManualEntryModal from '@/components/supervisor/modals/ManualEntryModal.vue' // <-- NEU: Modal-Import (Pfad ggf. anpassen)
import { useHolidays } from '@/composables/useHolidays'

import { useDateFormatter } from '@/composables/useDateFormatter'
const { formatDate } = useDateFormatter()

// Calendar importiert für das Icon in der Filterleiste
import { 
  Calendar,
  Calendar as CalendarIcon,
  Search,
  User,
  AlertTriangle
} from 'lucide-vue-next'

const adminStore = useAdminStore()
const { getEventClass } = useEventStyles()
const { getHolidaysForYear } = useHolidays()

const currentYear = new Date().getFullYear()

// NEU: State für das Manual Entry Modal
const isManualModalOpen = ref(false)
const selectedMember = ref(null)
const selectedDateStr = ref('')

// NEU: Reaktive Variablen für die Dropdowns (Standard: aktueller Monat & aktuelles Jahr)
const selectedMonth = ref(new Date().getMonth()) // 0 = Januar, 11 = Dezember
const selectedYear = ref(currentYear)
const searchQuery = ref('')

// NEU: Jahre-Array für das Dropdown generieren (z. B. aktuelles Jahr -3 bis +3)
const years = computed(() => {
  const yearsList = []
  for (let i = currentYear - 3; i <= currentYear + 3; i++) {
    yearsList.push(i)
  }
  return yearsList
})

// NEU: Die Monats-Objektliste, passend zu den values im Template (0-11)
const months = [
  { value: 0, name: 'Januar' },
  { value: 1, name: 'Februar' },
  { value: 2, name: 'März' },
  { value: 3, name: 'April' },
  { value: 4, name: 'Mai' },
  { value: 5, name: 'Juni' },
  { value: 6, name: 'Juli' },
  { value: 7, name: 'August' },
  { value: 8, name: 'September' },
  { value: 9, name: 'Oktober' },
  { value: 10, name: 'November' },
  { value: 11, name: 'Dezember' }
]

// NEU: Rechnet selectedMonth und selectedYear in das von deinem restlichen Code erwartete Date-Objekt um
const viewDate = computed(() => {
  return new Date(selectedYear.value, selectedMonth.value, 1)
})

// Hilfsfunktion: Konvertiert ein Date-Objekt in das ISO-Format YYYY-MM-DD
const formatDateToYYYYMMDD = (dateObj) => {
  const year = dateObj.getFullYear()
  const month = String(dateObj.getMonth() + 1).padStart(2, '0')
  const day = String(dateObj.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// NEU: Modal zum Bearbeiten/Anlegen eines Tages öffnen
const openManualEntryModal = (member, dayObj) => {
  if (isBeforeJoinedDate(member, dayObj)) return

  selectedMember.value = member
  selectedDateStr.value = formatDateToYYYYMMDD(dayObj)
  isManualModalOpen.value = true
}

const handleModalSaved = async () => {
  // 1. Modal schließen
  isManualModalOpen.value = false
  
  // 2. Kalenderevents / Warn-Icons im Kalender aktualisieren
  await adminStore.fetchCalendarEvents()
  
  // 3. Berichtsübersicht (Reports) im Hintergrund aktualisieren, falls vorhanden
  if (documentStore.fetchAdminReportsOverview) {
    await documentStore.fetchAdminReportsOverview(selectedMonth.value, selectedYear.value)
  }
}

// Prüft, ob der Mitarbeiter an diesem Tag bereits im Unternehmen war
const isBeforeJoinedDate = (member, day) => {
  if (!member || !member.joined_at || !day) return false
  
  const joinedDate = new Date(member.joined_at)
  joinedDate.setHours(0, 0, 0, 0)
  
  const currentDay = new Date(day)
  currentDay.setHours(0, 0, 0, 0)
  
  return currentDay < joinedDate
}

onMounted(async () => {
  await Promise.all([
    adminStore.fetchTeamMembers(),
    adminStore.fetchCalendarEvents()
  ])
})

// Berechnet Feiertage passend zum aktuell angezeigten Jahr
const currentHolidays = computed(() => {
  if (!viewDate.value) return []
  const year = viewDate.value.getFullYear()
  return getHolidaysForYear(year)
})

const daysInMonth = computed(() => {
  const year = viewDate.value.getFullYear()
  const month = viewDate.value.getMonth()
  return new Date(year, month + 1, 0).getDate()
})

const monthDays = computed(() => {
  const days = []
  const year = viewDate.value.getFullYear()
  const month = viewDate.value.getMonth()
  for (let i = 1; i <= daysInMonth.value; i++) {
    days.push(new Date(year, month, i))
  }
  return days
})

const teamMembers = computed(() => {
  return adminStore.filteredTeamMembers(searchQuery.value)
})

const getEvents = (member, day) => {
  if (!member || !day) return []

  const backendEvents = adminStore.getEventsForMemberAndDate(member.name, day)
  if (backendEvents && backendEvents.length > 0) return backendEvents

  if (currentHolidays.value && currentHolidays.value.length > 0) {
    const holidayMatch = currentHolidays.value.find(h => {
      const hDate = new Date(h.date)
      return hDate.getDate() === day.getDate() &&
             hDate.getMonth() === day.getMonth() &&
             hDate.getFullYear() === day.getFullYear()
    })

    if (holidayMatch) {
      return [{
        id: `holiday-${day.getTime()}`,
        type: 'holiday',
        title: holidayMatch.name,
        note: null,
        date: day
      }]
    }
  }

  if (isWeekend(day)) {
    const dayName = day.getDay() === 0 ? 'Sonntag' : 'Samstag'
    return [{
      id: `weekend-${day.getTime()}`,
      type: 'weekend',
      title: dayName,
      note: null,
      date: day
    }]
  }

  return []
}

const isToday = (date) => {
  const today = new Date()
  return date.getDate() === today.getDate() &&
         date.getMonth() === today.getMonth() &&
         date.getFullYear() === today.getFullYear()
}

const isWeekend = (date) => {
  const day = date.getDay()
  return day === 0 || day === 6
}

// Tooltip-Logik für Hover-Zustände
const hoveredEvent = ref(null)
const tooltipStyles = ref({})
const arrowStyles = ref({})

const handleMouseEnter = (event, e) => {
  const rect = e.currentTarget.getBoundingClientRect()
  const targetCenter = rect.left + rect.width / 2
  const isTooCloseToTop = rect.top < 160
  const top = isTooCloseToTop ? rect.bottom + 8 : rect.top - 8
  
  const tooltipWidth = 256
  const padding = 16
  
  let tooltipLeft = targetCenter - tooltipWidth / 2
  tooltipLeft = Math.max(padding, Math.min(window.innerWidth - tooltipWidth - padding, tooltipLeft))
  
  let arrowLeft = targetCenter - tooltipLeft
  arrowLeft = Math.max(16, Math.min(tooltipWidth - 16, arrowLeft))

  hoveredEvent.value = { 
    ...event, 
    date: new Date(event.date),
    index: isTooCloseToTop ? 2 : 10 
  }

  tooltipStyles.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${tooltipLeft}px`,
    transform: isTooCloseToTop ? 'none' : 'translateY(-100%)',
    zIndex: 9999
  }

  arrowStyles.value = {
    left: `${arrowLeft}px`,
    transform: 'translateX(-50%)'
  }
}

const handleMouseLeave = () => { hoveredEvent.value = null }
</script>

<template>
  <div class="flex-1 overflow-y-auto bg-slate-50 p-8">
    <div class="max-w-7xl mx-auto space-y-8">
      
      <!-- Identischer Header -->
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="p-2.5 bg-blue-50 text-blue-600 rounded-xl shrink-0">
            <CalendarIcon class="w-6 h-6" />
          </div>
          <div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Teamkalender</h1>
            <p class="text-slate-500 text-sm mt-0.5">
              Anwendungsübersicht für die Urlaubsplanung, Abwesenheiten und wichtige Termine deines Teams.
            </p>
          </div>
        </div>
      </section>

      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-3 rounded-2xl border border-slate-200 shadow-sm">
        <div class="relative w-full sm:w-64">
          <Search class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="Mitarbeiter suchen..."
            class="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 placeholder:text-slate-400 transition-all shadow-sm text-slate-800"
          />
        </div>

        <div class="flex items-center gap-2 w-full sm:w-auto justify-end">
          <div class="relative w-full sm:w-40">
            <Calendar class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <select 
              v-model="selectedMonth"
              class="w-full pl-10 pr-8 py-2 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-xl text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer appearance-none"
            >
              <option v-for="m in months" :key="m.value" :value="m.value">{{ m.name }}</option>
            </select>
          </div>

          <div class="relative w-24 shrink-0">
            <select 
              v-model="selectedYear"
              class="w-full pl-3 pr-8 py-2 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-xl text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer appearance-none"
            >
              <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Kalender-Grid-Bereich -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        
        <!-- Tabellen-Header (Tage 1-31) -->
        <div class="flex border-b border-slate-100 bg-slate-50/50 sticky top-0 z-20">
          <div class="w-52 shrink-0 p-3 font-bold text-[10px] text-slate-400 uppercase tracking-widest border-r border-slate-100 bg-slate-50 flex items-center">
            Mitarbeiter
          </div>

          <div class="flex-1 flex min-w-0">
            <div 
              v-for="day in monthDays" 
              :key="day.getTime()"
              class="flex-1 min-w-0 min-h-[44px] border-r border-slate-100 last:border-r-0 flex flex-col items-center justify-center relative p-1 text-xs font-semibold"
              :class="[
                isToday(day) ? 'text-blue-600 bg-blue-50/20' : (isWeekend(day) ? 'text-slate-400 bg-slate-100/40' : 'text-slate-500')
              ]"
            >
              <span 
                class="flex items-center justify-center w-6 h-6 rounded-full text-[11px] transition-all"
                :class="isToday(day) ? 'bg-blue-600 text-white font-bold' : ''"
              >
                {{ day.getDate() }}
              </span>
            </div>
          </div>
        </div>

        <!-- Tabellen-Body (Mitarbeiter Zeilen) -->
        <div class="flex-1 overflow-y-auto">
          <div 
            v-for="member in teamMembers" 
            :key="member.id"
            class="flex border-b border-slate-100 hover:bg-slate-50/30 transition-colors group min-h-[64px] relative"
          >
            <!-- Linker Block: Mitarbeiter Info (Sticky) -->
            <div class="w-52 shrink-0 p-3 border-r border-slate-100 bg-white sticky left-0 z-10 flex items-center gap-3 shadow-[4px_0_8px_-4px_rgba(0,0,0,0.05)]">
              <div class="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors shrink-0">
                <div v-if="member.avatar" class="w-10 h-10 rounded-full overflow-hidden border border-slate-200 shrink-0">
                  <img :src="member.avatar" class="w-full h-full object-cover" />
                </div>
                <div v-else class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold shrink-0 text-sm">
                  {{ member.initials || '??' }}
                </div>
              </div>
              <div class="min-w-0 flex-1">
                <div class="text-xs font-bold text-slate-900 truncate">{{ member.name }}</div>
                <div class="text-[10px] text-slate-400 truncate">{{ member.username }}</div>
              </div>
            </div>

<!-- Rechter Block: Die Kalendertage im Grid -->
          <div class="flex-1 flex min-w-0 relative">
            
            <!-- Overlay-Text über den gesamten ausgegrauten Bereich -->
            <div 
              v-if="monthDays.filter(d => isBeforeJoinedDate(member, d)).length > 0"
              class="absolute inset-y-0 left-0 z-10 select-none flex items-center justify-center px-4 pointer-events-none"
              :style="{
                width: `${(monthDays.filter(d => isBeforeJoinedDate(member, d)).length / monthDays.length) * 100}%`
              }"
            >
              <span 
                v-if="monthDays.filter(d => isBeforeJoinedDate(member, d)).length >= 4"
                :title="`Eintrittsdatum: ${formatDate(member.joined_at)}`"
                class="font-bold text-xs text-slate-500/80 tracking-wide truncate max-w-full text-center block px-2 pointer-events-auto cursor-help"
              >
                Eintrittsdatum: {{ formatDate(member.joined_at) }}
              </span>
            </div>

            <!-- Die einzelnen Tages-Zellen -->
            <div 
              v-for="day in monthDays" 
              :key="day.getTime()"
              @click="openManualEntryModal(member, day)"
              class="flex-1 min-w-0 min-h-[64px] border-r border-slate-100 last:border-r-0 flex items-center justify-center relative p-1 transition-colors"
              :class="[
                isBeforeJoinedDate(member, day) 
                  ? 'bg-slate-200/50 cursor-not-allowed select-none' 
                  : (isWeekend(day) ? 'bg-slate-50/60 hover:bg-blue-50/50 cursor-pointer' : 'hover:bg-blue-50/50 cursor-pointer')
              ]"
            >
              <template v-if="!isBeforeJoinedDate(member, day)">
                <template v-if="getEvents(member, day).length > 0">
                  <div 
                    v-for="item in getEvents(member, day)"
                    :key="item.id"
                    class="w-full h-7 rounded-lg border flex items-center justify-center cursor-pointer transition-all hover:scale-105 hover:z-30 hover:shadow-md relative"
                    :class="getEventClass(item.type)"
                    @mouseenter="handleMouseEnter(item, $event)"
                    @mouseleave="handleMouseLeave"
                  >
                    <AlertTriangle 
                      v-if="item.warning" 
                      class="w-3.5 h-3.5 fill-amber-400 text-slate-900 shrink-0 drop-shadow-sm" 
                    />
                  </div>
                </template>
              </template>
            </div>

          </div>

          </div>

          <!-- Empty State -->
          <div 
            v-if="teamMembers?.length === 0" 
            class="flex flex-col items-center justify-center p-20 text-center"
          >
            <div class="w-20 h-20 bg-slate-50 rounded-3xl flex items-center justify-center mb-4 border border-slate-100">
              <User class="w-10 h-10 text-slate-200" />
            </div>
            <h3 class="text-slate-900 font-bold text-lg">Keine Mitarbeiter gefunden</h3>
            <p class="text-slate-500 text-sm max-w-xs mx-auto">
              Es konnten keine Teammitglieder gefunden werden, die den Suchkriterien entsprechen.
            </p>
          </div>
        </div>
      </div>

      <!-- Legend / Footer -->
      <div class="flex items-center justify-center gap-8 py-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded bg-amber-100 border border-amber-300" />
          <span class="text-xs font-bold text-slate-600">Offener Antrag</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded bg-green-100 border border-green-300" />
          <span class="text-xs font-bold text-slate-600">Urlaub</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded bg-red-100 border border-red-300" />
          <span class="text-xs font-bold text-slate-600">Krankheit</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded bg-violet-200 border border-violet-300" />
          <span class="text-xs font-bold text-slate-600">Feiertag</span>
        </div>
      </div>

    </div>

    <EventTooltip 
      :event="hoveredEvent"
      :styles="tooltipStyles"
      :arrow-style="arrowStyles"
    />

    <ManualEntryModal
      :is-open="isManualModalOpen"
      :member="selectedMember"
      :initial-date="selectedDateStr"
      @close="isManualModalOpen = false"
      @success="handleModalSaved"
    />
  </div>
</template>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>