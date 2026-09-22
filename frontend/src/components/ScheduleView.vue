<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { 
  Plus, Clock, Calendar as CalendarIcon, AlertTriangle
} from 'lucide-vue-next'

// --- STORES ---
import { useScheduleStore } from '@/stores/scheduleStore'
import { useAuthStore } from '@/stores/authStore'

// --- COMPOSABLES ---
import { useCalendar } from '@/composables/useCalendar'
import { useEventStyles } from '@/composables/useEventStyles'

// --- COMPONENTS ---
import EventTooltip from '@/components/tooltips/EventTooltip.vue'
import RequestLeaveModal from '@/components/modals/RequestLeaveModal.vue'
import ShiftChangeRequestModal from '@/components/modals/ShiftChangeRequestModal.vue'
import EventInfoModal from '@/components/modals/EventInfoModal.vue'

// 1. Kalender-Logik
const { 
  currentDate, daysOfWeek, calendarDays, isToday 
} = useCalendar()

// 2. Store & State
const scheduleStore = useScheduleStore()
const authStore = useAuthStore()
const { user } = storeToRefs(authStore)
const { events: scheduleEvents, isLoading } = storeToRefs(scheduleStore)
const { getEventClass, getEventIcon } = useEventStyles()

// --- UI STATE MODALS ---
const isRequestModalOpen = ref(false)
const isShiftRequestModalOpen = ref(false)
const isInfoModalOpen = ref(false)

const hoveredEvent = ref(null)
const tooltipStyles = ref({ top: '0px', left: '0px' })

const selectedEvent = ref(null) // Für Info Modal
const selectedShift = ref(null) // Für Schichtwechsel
const editingRequest = ref(null) // Für Bearbeitung von Anträgen
const shiftModalRef = ref(null)

// --- DROPDOWN LOGIK (Identisch mit AdminCalendar.vue) ---
const currentYear = new Date().getFullYear()
const selectedMonth = ref(new Date().getMonth()) // 0 = Januar, 11 = Dezember
const selectedYear = ref(currentYear)

const years = computed(() => {
  const yearsList = []
  for (let i = currentYear - 3; i <= currentYear + 3; i++) {
    yearsList.push(i)
  }
  return yearsList
})

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

// Aktualisiert das currentDate-Objekt des useCalendar-Composables bei Dropdown-Änderung
watch([selectedMonth, selectedYear], ([newMonth, newYear]) => {
  currentDate.value = new Date(newYear, newMonth, 1)
})

// Synchronisiert die Dropdowns, falls currentDate von außen (z.B. Initialisierung) gesetzt wird
watch(currentDate, (newDate) => {
  if (newDate) {
    selectedMonth.value = newDate.getMonth()
    selectedYear.value = newDate.getFullYear()
  }
}, { immediate: true })


// --- API METHODEN ---
const fetchSchedule = () => {
  if (!calendarDays.value?.length) return
  const start = calendarDays.value[0].date.toISOString().split('T')[0]
  const end = calendarDays.value[calendarDays.value.length - 1].date.toISOString().split('T')[0]
  scheduleStore.fetchCalendarFeed(start, end)
}

const handleLeaveSuccess = () => {
  isRequestModalOpen.value = false
  editingRequest.value = null
  fetchSchedule()
}

const handleShiftSubmit = async (payload, onSuccess, onError) => {
  try {
    await scheduleStore.submitShiftChangeRequest(payload)
    
    if (typeof onSuccess === 'function') {
      onSuccess()
    }

    const start = calendarDays.value[0].date.toISOString().split('T')[0]
    const end = calendarDays.value[calendarDays.value.length - 1].date.toISOString().split('T')[0]
    await scheduleStore.fetchCalendarFeed(start, end)
    
  } catch (err) {
    console.error("API Fehler im Kalender abgefangen:", err)
    
    const errorMessage = 
      err.response?.data?.non_field_errors?.[0] || 
      err.response?.data?.detail || 
      err.response?.data?.error ||
      err.response?.data?.[0] || 
      "Fehler beim Senden der Korrektur";

    if (typeof onError === 'function') {
      onError(errorMessage)
    }
  }
}

const handleRequestWithdraw = async (sessionId, callback) => {
  try {
    await scheduleStore.withdrawShiftChangeRequest(sessionId)
    
    if (selectedShift.value) {
      const session = selectedShift.value.sessions.find(s => s.id === sessionId)
      if (session) session.pending_request = null
    }

    callback()
  } catch (err) {
    alert('Fehler beim Löschen des Antrags.')
  }
}

// --- EVENT HANDLER ---
const handleEventClick = async (event) => {
  if (event.type === 'work') {
    try {
      const rawId = event.workDayId || event.id;
      const cleanId = String(rawId).replace('wd-', '');
      const dayData = await scheduleStore.fetchWorkDaySessions(event.workDayId || event.id)
      
      selectedShift.value = {
        id: cleanId,
        date: dayData.date,
        sessions: dayData.sessions,
        title: "Tagesübersicht",
      }
      isShiftRequestModalOpen.value = true
    } catch (err) {
      console.error(err)
    }
    return
  }

  if (event.isRequest && event.isPending) {
    editingRequest.value = {
      id: event.requestId || event.id.split('-')[1],
      startDate: event.leave_start || event.date,
      endDate: event.leave_end || event.date,
      leave_type: event.type,
      note: event.note
    }
    isRequestModalOpen.value = true
    return
  }

  if (
    event.status === 'approved' || 
    event.type === 'system' || 
    (['vacation', 'sick', 'overtime'].includes(event.type) && !event.isPending)
  ) {
    selectedEvent.value = event
    isInfoModalOpen.value = true
    return
  }
}

const getEventsForDate = (calendarDayDate) => {
  if (!scheduleEvents.value) return []
  return scheduleEvents.value.filter(event => {
    const eDate = event.date instanceof Date ? event.date : new Date(event.date)
    return eDate.toDateString() === calendarDayDate.toDateString() && event.status !== 'cancelled'
  })
}

const handleMouseEnter = (event, e, index) => {
  const rect = e.currentTarget.getBoundingClientRect()
  hoveredEvent.value = { ...event, index }
  
  const isFirstRow = index < 7
  const isFirstCol = index % 7 === 0
  const isLastCol = index % 7 === 6
  
  let top = isFirstRow ? rect.bottom + 12 : rect.top - 12
  let left, transform = isFirstRow ? '' : 'translateY(-100%)'

  if (isFirstCol) {
    left = rect.left
    transform += ' translateX(0)'
  } else if (isLastCol) {
    left = rect.right
    transform += ' translateX(-100%)'
  } else {
    left = rect.left + (rect.width / 2)
    transform += ' translateX(-50%)'
  }

  tooltipStyles.value = {
    position: 'fixed', top: `${top}px`, left: `${left}px`,
    transform, zIndex: 9999
  }
}

onMounted(async () => {
  if (!user.value) await authStore.fetchUser()
  if (calendarDays.value.length > 0) fetchSchedule()
})

watch(calendarDays, (newDays) => {
  if (newDays && newDays.length > 0) {
    fetchSchedule()
  }
}, { immediate: true })
</script>

<template>
  <div class="flex-1 overflow-y-auto bg-slate-50 p-8 relative">
    
    <div v-if="isLoading" class="absolute inset-0 bg-white/50 backdrop-blur-sm z-[200] flex items-center justify-center">
       <Clock class="w-10 h-10 text-blue-600 animate-spin" />
    </div>

    <!-- Schwebender Button -->
    <button 
      @click="isRequestModalOpen = true; editingRequest = null" 
      class="fixed bottom-8 right-8 z-[150] px-5 py-3 bg-blue-600 text-white rounded-xl flex items-center gap-2 hover:bg-blue-700 hover:scale-[1.02] active:scale-95 transition-all shadow-xl hover:shadow-blue-500/20 font-semibold text-sm cursor-pointer"
    >
      <Plus class="w-5 h-5" /> Neuer Antrag
    </button>

    <div class="max-w-7xl mx-auto space-y-8">
      
      <!-- IDENTISCHER HEADER (Genau wie AdminCalendar) -->
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="p-2.5 bg-blue-50 text-blue-600 rounded-xl shrink-0">
            <CalendarIcon class="w-6 h-6" />
          </div>
          <div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Mein Kalender</h1>
            <p class="text-slate-500 text-sm mt-0.5">
              Verwalte und plane hier deine Arbeitszeiten und freien Tage.
            </p>
          </div>
        </div>
      </section>

      <!-- NAVIGATION & FILTERBAR (Heute links, Dropdowns rechts, Legende mittig/rechts) -->
      <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 bg-white p-3 rounded-2xl border border-slate-200 shadow-sm">
        
        <!-- Linker Bereich: "Heute" und die Dropdowns direkt daneben -->
        <div class="flex flex-wrap items-center gap-2">
          <!-- Button zum Zurücksetzen auf aktuellen Monat -->
          <button 
            @click="currentDate = new Date()" 
            class="px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-slate-200 rounded-xl transition-all cursor-pointer h-9 shrink-0"
          >
            Heute
          </button>

          <!-- Monats-Dropdown -->
          <div class="relative w-36 sm:w-40 h-9">
            <CalendarIcon class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <select 
              v-model="selectedMonth"
              class="w-full h-full pl-10 pr-8 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-xl text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer appearance-none"
            >
              <option v-for="m in months" :key="m.value" :value="m.value">{{ m.name }}</option>
            </select>
          </div>

          <!-- Jahres-Dropdown -->
          <div class="relative w-24 h-9 shrink-0">
            <select 
              v-model="selectedYear"
              class="w-full h-full pl-3 pr-8 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-xl text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer appearance-none"
            >
              <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
        </div>

        <!-- Rechter Bereich: Legende (in der oberen Box) -->
        <div class="flex flex-wrap items-center gap-4 md:gap-5">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded bg-amber-100 border border-amber-300" />
            <span class="text-[11px] font-bold text-slate-500">In Bearbeitung</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded bg-green-100 border border-green-300" />
            <span class="text-[11px] font-bold text-slate-500">Urlaub</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded bg-red-100 border border-red-300" />
            <span class="text-[11px] font-bold text-slate-500">Krankheit</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded bg-violet-200 border border-violet-300" />
            <span class="text-[11px] font-bold text-slate-500">Feiertag</span>
          </div>
        </div>
      </div>

      <!-- Kalender-Bereich -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        
        <!-- Wochentage (Header des Grids) -->
        <div class="grid grid-cols-7 border-b border-slate-100 bg-slate-50/50 sticky top-0 z-20">
          <div 
            v-for="day in daysOfWeek" 
            :key="day" 
            class="py-3 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400 bg-slate-50/50 border-r last:border-r-0 border-slate-100"
          >
            {{ day }}
          </div>
        </div>

        <!-- Kalender-Days (Grid) -->
        <div class="grid grid-cols-7 auto-rows-fr">
          <div 
            v-for="(day, index) in calendarDays" 
            :key="index"
            class="border-r border-b last:border-r-0 border-slate-100 p-2 flex flex-col gap-1.5 min-h-[120px] transition-colors"
            :class="[day.isCurrentMonth ? 'bg-white' : 'bg-slate-50/30 text-slate-400/70']"
          >
            <span 
              class="text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full"
              :class="isToday(day.date) ? 'bg-blue-600 text-white shadow-md font-bold' : 'text-slate-600'"
            >
              {{ day.day }}
            </span>

            <div class="flex-1 space-y-1 overflow-hidden">
              <div 
                v-for="event in getEventsForDate(day.date)" 
                :key="event.id"
                @mouseenter="handleMouseEnter(event, $event, index)"
                @mouseleave="hoveredEvent = null"
                @click="handleEventClick(event)"
                class="p-1.5 rounded-lg border text-[10px] leading-tight flex flex-col gap-0.5 cursor-pointer transition-all hover:scale-[1.02] hover:shadow-sm relative"
                :class="getEventClass(event)"
              >
                <div v-if="event.hasPendingRequest" class="absolute -top-1 -right-1 w-2.5 h-2.5 bg-blue-500 rounded-full border-2 border-white" />
                
                  <div class="flex items-center justify-between gap-1 font-bold w-full">
                    <div class="flex items-center gap-1 truncate">
                      <component :is="getEventIcon(event.type)" class="w-3.5 h-3.5 shrink-0" />
                      <span class="truncate">{{ event.title }}</span>
                    </div>

                    <!-- Warndreieck anzeigen, wenn warning vorhanden ist -->
                    <AlertTriangle 
                      v-if="event.warning" 
                      class="w-3.5 h-3.5 fill-amber-400 text-slate-900 shrink-0 drop-shadow-sm" 
                      title="Achtung: Prüfbedarf"
                    />
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

    </div>

    <!-- Tooltips und Modals -->
    <EventTooltip v-if="hoveredEvent" :event="hoveredEvent" :styles="tooltipStyles"/>

    <RequestLeaveModal :isOpen="isRequestModalOpen" :initialData="editingRequest"
      :leaveTypes="[{ id: 'vacation', name: 'Urlaub' }, { id: 'sick', name: 'Krankheit' }]"
      @close="isRequestModalOpen = false; editingRequest = null" 
      @success="handleLeaveSuccess" />

    <ShiftChangeRequestModal 
      ref="shiftModalRef"
      :is-open="isShiftRequestModalOpen"
      :shift="selectedShift"
      :is-loading="scheduleStore.isLoading"  
      @close="isShiftRequestModalOpen = false"
      @submit="handleShiftSubmit"
      @withdraw="handleRequestWithdraw" 
    />

    <EventInfoModal :isOpen="isInfoModalOpen" :event="selectedEvent" @close="isInfoModalOpen = false" />
  </div>
</template>

<style scoped>
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>