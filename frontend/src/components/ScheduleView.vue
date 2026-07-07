<script setup>
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { 
  Plus, ChevronLeft, ChevronRight, Clock, Calendar 
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

const handleLeaveSubmit = async (formData) => {
  try {
    if (editingRequest.value?.id) {
      await scheduleStore.updateLeaveRequest(editingRequest.value.id, formData)
    } else {
      await scheduleStore.createLeaveRequest(formData)
    }
    
    isRequestModalOpen.value = false
    editingRequest.value = null
    fetchSchedule() // Kalender neu laden
  } catch (error) {
    alert("Fehler beim Speichern des Antrags.")
  }
}

const handleShiftSubmit = async (payload, onSuccess) => {
  try {
    await scheduleStore.submitShiftChangeRequest(payload)
    
    if (typeof onSuccess === 'function') {
      onSuccess() // Setzt isSubmitted im Modal auf true
    }

    const start = calendarDays.value[0].date.toISOString().split('T')[0]
    const end = calendarDays.value[calendarDays.value.length - 1].date.toISOString().split('T')[0]
    await scheduleStore.fetchCalendarFeed(start, end)
    
  } catch (err) {
    console.error("API Fehler:", err)
    alert(err.response?.data?.error || "Fehler beim Senden der Korrektur")
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

const handleSessionDelete = async (sessionId, callback) => {
  try {
    await scheduleStore.deleteWorkSession(sessionId)
    
    if (selectedShift.value) {
      const sessionIndex = selectedShift.value.sessions.findIndex(s => s.id === sessionId)
      if (sessionIndex !== -1) selectedShift.value.sessions.splice(sessionIndex, 1)
    }

    callback()
  } catch (err) {
    alert('Fehler beim Löschen der Sitzung.')
  }
}


// --- EVENT HANDLER ---
const handleEventClick = async (event) => { // Wichtig: async hinzugefügt
  // Debug-Logs
  console.log("Klick auf Event:", event.title)
  
  // --- 1. Arbeitszeiten (Work Sessions) ---
  if (event.type === 'work') {
    try {

      const rawId = event.workDayId || event.id;
      const cleanId = String(rawId).replace('wd-', '');
      // Falls 'event.workDayId' im Kalender-Feed existiert:
      const dayData = await scheduleStore.fetchWorkDaySessions(event.workDayId || event.id)
      
      selectedShift.value = {
        id: cleanId,
        date: dayData.date,
        sessions: dayData.sessions, // Das ist jetzt ein Array!
        title: "Tagesübersicht",
      }
      isShiftRequestModalOpen.value = true
    } catch (err) {
      console.error(err)
    }
    return
  }

  // --- 2. Offener Abwesenheitsantrag (Edit Leave Modal) ---
  // Hinweis: Achte darauf, ob dein Serializer isPending oder is_pending liefert. 
  // Ich bleibe hier bei deiner Benennung: isPending.
  if (event.isRequest && event.isPending) {
    editingRequest.value = {
      id: event.requestId || event.id.split('-')[1],
      startDate: event.date instanceof Date 
        ? event.date.toISOString().split('T')[0] 
        : event.date,
      endDate: event.endDate || event.date,
      leave_type: event.type,
      note: event.note
    }
    isRequestModalOpen.value = true
    return
  }

  // --- 3. Abgeschlossener Antrag oder Info (Info Modal) ---
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

// --- LIFECYCLE & WATCHER ---
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

    <div class="max-w-6xl mx-auto space-y-8">
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="text-left">
          <h1 class="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Calendar class="w-6 h-6 text-blue-600" /> <span>Mein Kalender</span>
          </h1>
          <p class="text-slate-500 mt-1">Verwalte hier deine Zeiten.</p>
        </div>
        <button @click="isRequestModalOpen = true; editingRequest = null" 
                class="px-4 py-2 bg-blue-600 text-white rounded-xl flex items-center gap-2 hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/20">
          <Plus class="w-4 h-4" /> Neuer Antrag
        </button>
      </section>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 flex items-center justify-between shadow-sm">
        <div class="flex items-center gap-4">
          <h2 class="text-lg font-bold text-slate-900 min-w-[180px]">{{ currentMonthName }}</h2>
          <div class="flex items-center bg-slate-50 rounded-lg p-1">
            <button @click="prevMonth" class="p-1.5 hover:bg-white hover:shadow-sm rounded-md transition-all"><ChevronLeft class="w-5 h-5" /></button>
            <button @click="currentDate = new Date()" class="px-3 py-1.5 text-xs font-bold uppercase text-slate-600 hover:bg-white rounded-md">Heute</button>
            <button @click="nextMonth" class="p-1.5 hover:bg-white hover:shadow-sm rounded-md transition-all"><ChevronRight class="w-5 h-5" /></button>
          </div>
        </div>
        
        <div class="hidden lg:flex items-center gap-6">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded bg-amber-100 border border-amber-300" />
            <span class="text-xs font-bold text-slate-600">Abwesenheit (in Bearbeitung)</span>
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

      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="grid grid-cols-7 border-b border-slate-100">
          <div v-for="day in daysOfWeek" :key="day" class="py-3 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400 bg-slate-50/50">{{ day }}</div>
        </div>
        
        <div class="grid grid-cols-7 grid-rows-6 h-[750px]">
          <div v-for="(day, index) in calendarDays" :key="index"
            :class="['border-r border-b border-slate-100 p-2 flex flex-col gap-1', day.isCurrentMonth ? 'bg-white' : 'bg-slate-50/30 text-slate-400']"
          >
            <span :class="['text-sm font-bold w-7 h-7 flex items-center justify-center rounded-full', isToday(day.date) ? 'bg-blue-600 text-white shadow-md' : '']">
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
                  <component :is="getEventIcon(event.type)" class="w-3 h-3" />
                  <span class="truncate">{{ event.title }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <EventTooltip v-if="hoveredEvent" :event="hoveredEvent" :styles="tooltipStyles"/>

    <RequestLeaveModal :isOpen="isRequestModalOpen" :initialData="editingRequest"
      :leaveTypes="[{ id: 'vacation', name: 'Urlaub' }, { id: 'sick', name: 'Krankheit' }, { id: 'overtime', name: 'GLZ-Abbau' }]"
      @close="isRequestModalOpen = false; editingRequest = null" @submit="handleLeaveSubmit" />

    <ShiftChangeRequestModal 
      ref="shiftModalRef"
      :is-open="isShiftRequestModalOpen"
      :shift="selectedShift"
      :is-loading="scheduleStore.isLoading"  
      @close="isShiftRequestModalOpen = false"
      @submit="handleShiftSubmit"
      @withdraw="handleRequestWithdraw" 
      @delete-session="handleSessionDelete"
    />

    <EventInfoModal :isOpen="isInfoModalOpen" :event="selectedEvent" @close="isInfoModalOpen = false" />
  </div>
</template>