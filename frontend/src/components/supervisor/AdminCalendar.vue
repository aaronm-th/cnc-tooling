<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { useEventStyles } from '@/composables/useEventStyles'
import EventTooltip from '@/components/tooltips/EventTooltip.vue'
import { useHolidays } from '@/composables/useHolidays'

import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar as CalendarIcon,
  Search,
  User
} from 'lucide-vue-next'

const adminStore = useAdminStore()
const { getEventClass } = useEventStyles()
const { getHolidaysForYear } = useHolidays()

const viewDate = ref(new Date())
const searchQuery = ref('')

onMounted(async () => {
  // Lädt die Daten parallel beim Mounten der Komponente
  await Promise.all([
    adminStore.fetchTeamMembers(),
    adminStore.fetchCalendarEvents()
  ])
})

const months = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
]

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

// Greift nun fehlerfrei auf die korrekte Store-Variable zu
const teamMembers = computed(() => {
  return adminStore.filteredTeamMembers(searchQuery.value)
})

// Kombiniert Backend-Events mit dynamischen Frontend-Feiertagen und Wochenenden
const getEvents = (member, day) => {
  if (!member || !day) return []

  // 1. Priorität: Echtes Event vom Backend (Arbeit, Krankheit, genehmigter Urlaub)
  const backendEvents = adminStore.getEventsForMemberAndDate(member.name, day)
  if (backendEvents && backendEvents.length > 0) return backendEvents

  // 2. Priorität: Gesetzlicher Feiertag aus dem Frontend-Composable
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
        note: null, // Versteckt das Notizfeld im Tooltip komplett
        date: day
      }]
    }
  }

  // 3. Priorität: Reguläres Wochenende
  if (isWeekend(day)) {
    const dayName = day.getDay() === 0 ? 'Sonntag' : 'Samstag'
    return [{
      id: `weekend-${day.getTime()}`,
      type: 'weekend',
      title: dayName,
      note: null, // Versteckt das Notizfeld im Tooltip komplett
      date: day
    }]
  }

  return []
}

const prevMonth = () => {
  viewDate.value = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth() - 1, 1)
}

const nextMonth = () => {
  viewDate.value = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth() + 1, 1)
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
  <div class="flex-1 flex flex-col min-h-0 bg-slate-50">
    <header class="p-8 pb-6 flex flex-col gap-6">
      <div class="max-w-7xl w-full mx-auto">
        <h1 class="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <CalendarIcon class="w-8 h-8 text-blue-600" />
          Teamkalender
        </h1>
        <p class="text-slate-500 mt-1 text-sm">
          Anwendungsübersicht für die Urlaubsplanung, Abwesenheiten und wichtige Termine deines Teams. 
        </p>
      </div>

      <div class="max-w-7xl w-full mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="relative w-full sm:max-w-sm h-10">
          <Search class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="Suche..."
            class="w-full h-full pl-10 pr-4 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm"
          >
        </div>

        <div class="flex items-center justify-between bg-white px-1 rounded-xl border border-slate-200 shadow-sm w-full sm:w-auto sm:min-w-[240px] h-10">
          <button 
            class="p-1.5 hover:bg-slate-100 rounded-lg transition-colors flex items-center justify-center"
            @click="prevMonth"
          >
            <ChevronLeft class="w-4 h-4 text-slate-600" />
          </button>
          <div class="px-4 font-bold text-slate-900 min-w-[140px] text-center text-sm select-none leading-none">
            {{ months[viewDate.getMonth()] }} {{ viewDate.getFullYear() }}
          </div>
          <button 
            class="p-1.5 hover:bg-slate-100 rounded-lg transition-colors flex items-center justify-center"
            @click="nextMonth"
          >
            <ChevronRight class="w-4 h-4 text-slate-600" />
          </button>
        </div>
      </div>
    </header>

    <div class="flex-1 overflow-hidden px-8 pb-8">
      <div class="max-w-7xl mx-auto h-full bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden flex flex-col">
        
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

        <div class="flex-1 overflow-y-auto">
          <div 
            v-for="member in teamMembers" 
            :key="member.id"
            class="flex border-b border-slate-100 hover:bg-slate-50/30 transition-colors group min-h-[64px]"
          >
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

            <div class="flex-1 flex min-w-0">
              <div 
                v-for="day in monthDays" 
                :key="day.getTime()"
                class="flex-1 min-w-0 min-h-[64px] border-r border-slate-100 last:border-r-0 flex items-center justify-center relative p-1"
                :class="isWeekend(day) ? 'bg-slate-50/60' : ''"
              >

                <template v-if="getEvents(member, day).length > 0">
                  <div 
                    v-for="event in getEvents(member, day)"
                    :key="event.id"
                    class="w-full h-7 rounded-lg border flex items-center justify-center cursor-help transition-all hover:scale-105 hover:z-30 hover:shadow-md"
                    :class="getEventClass(event.type)"
                    @mouseenter="handleMouseEnter(event, $event)"
                    @mouseleave="handleMouseLeave"
                  />
                </template>
              </div>
            </div>
          </div>

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
    </div>
    
    <footer class="px-8 pb-8">
      <div class="max-w-7xl mx-auto flex items-center justify-center gap-8 py-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
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
    </footer>

    <EventTooltip 
      :event="hoveredEvent"
      :styles="tooltipStyles"
      :arrow-style="arrowStyles"
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