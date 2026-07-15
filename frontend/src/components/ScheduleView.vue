<script setup>
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { 
  Plus, ChevronLeft, ChevronRight, Clock, Calendar as CalendarIcon 
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
  currentDate, daysOfWeek, calendarDays, currentMonthName, 
  nextMonth, prevMonth, isToday 
} = useCalendar()

// 2. Store & State
const scheduleStore = useScheduleStore()
const authStore = useAuthStore()
const { user } = storeToRefs(authStore)
const { events: scheduleEvents, isLoading } = storeToRefs(scheduleStore)
const { getEventClass, getEventIcon, getIconColorClass } = useEventStyles()

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

watch(currentDate, fetchSchedule)
</script>

<template>
  <div class="flex-1 overflow-y-auto p-8 bg-slate-50 relative">
    
    <div v-if="isLoading" class="absolute inset-0 bg-white/50 backdrop-blur-sm z-[200] flex items-center justify-center">
       <Clock class="w-10 h-10 text-blue-600 animate-spin" />
    </div>

    <!-- Neuer schwebender Button, angepasst an das abgerundete Design -->
    <button 
      @click="isRequestModalOpen = true; editingRequest = null" 
      class="fixed bottom-8 right-8 z-[150] px-5 py-3 bg-blue-600 text-white rounded-xl flex items-center gap-2 hover:bg-blue-700 hover:scale-[1.02] active:scale-95 transition-all shadow-xl hover:shadow-blue-500/20 font-semibold text-sm cursor-pointer"
    >
      <Plus class="w-5 h-5" /> Neuer Antrag
    </button>

    <div class="max-w-6xl mx-auto space-y-8">
      
      <!-- HEADER (NEUES ADMIN-DESIGN-LAYOUT) -->
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="p-2.5 bg-blue-50 text-blue-600 rounded-xl shrink-0">
            <CalendarIcon class="w-6 h-6" />
          </div>
          <div class="text-left">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Mein Kalender</h1>
            <p class="text-slate-500 text-sm mt-0.5">Verwalte und plane hier deine Arbeitszeiten und freien Tage.</p>
          </div>
        </div>
      </section>

      <!-- NAVIGATION & FILTERBAR -->
      <div class="sticky top-0延 z-[90] bg-slate-50 pt-2 pb-2 space-y-4">
        
        <div class="bg-white p-3 rounded-2xl border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
          <div class="flex items-center gap-4">
            <h2 class="text-lg font-bold text-slate-900 min-w-[180px] text-left">{{ currentMonthName }}</h2>
            <div class="flex items-center bg-slate-50 rounded-xl p-1 border border-slate-100">
              <button @click="prevMonth" class="p-1.5 hover:bg-white hover:shadow-sm rounded-lg text-slate-600 hover:text-slate-900 transition-all cursor-pointer">
                <ChevronLeft class="w-5 h-5" />
              </button>
              <button @click="currentDate = new Date()" class="px-3 py-1.5 text-xs font-bold uppercase text-slate-600 hover:text-slate-900 hover:bg-white rounded-lg transition-all cursor-pointer">Heute</button>
              <button @click="nextMonth" class="p-1.5 hover:bg-white hover:shadow-sm rounded-lg text-slate-600 hover:text-slate-900 transition-all cursor-pointer">
                <ChevronRight class="w-5 h-5" />
              </button>
            </div>
          </div>
          
          <!-- Legende -->
          <div class="hidden lg:flex items-center gap-5">
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

        <!-- Wochentage -->
        <div class="grid grid-cols-7 border border-slate-200 border-b-slate-100 rounded-t-2xl bg-white overflow-hidden shadow-sm">
          <div v-for="day in daysOfWeek" :key="day" class="py-3 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400 bg-slate-50/50 border-r last:border-r-0 border-slate-100">
            {{ day }}
          </div>
        </div>

      </div>

      <!-- Kalender-Grid -->
      <div class="bg-white rounded-b-2xl border-x border-b border-slate-200 shadow-sm overflow-hidden grid grid-cols-7 auto-rows-fr mt-[-16px]">
        <div v-for="(day, index) in calendarDays" :key="index"
          :class="['border-r border-b border-slate-100 p-2 flex flex-col gap-1.5 min-h-[120px] transition-colors', day.isCurrentMonth ? 'bg-white' : 'bg-slate-50/30 text-slate-400']"
        >
          <span :class="['text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full', isToday(day.date) ? 'bg-blue-600 text-white shadow-md font-bold' : 'text-slate-600']">
            {{ day.day }}
          </span>

          <div class="flex-1 space-y-1 overflow-hidden">
            <div v-for="event in getEventsForDate(day.date)" :key="event.id"
              @mouseenter="handleMouseEnter(event, $event, index)"
              @mouseleave="hoveredEvent = null"
              @click="handleEventClick(event)"
              :class="['p-1.5 rounded-lg border text-[10px] leading-tight flex flex-col gap-0.5 cursor-pointer transition-all hover:scale-[1.02] hover:shadow-sm relative', getEventClass(event)]"
            >
              <div v-if="event.hasPendingRequest" class="absolute -top-1 -right-1 w-2.5 h-2.5 bg-blue-500 rounded-full border-2 border-white" />
              
              <div class="flex items-center gap-1 font-bold">
                <component :is="getEventIcon(event.type)" class="w-3.5 h-3.5" />
                <span class="truncate">{{ event.title }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

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