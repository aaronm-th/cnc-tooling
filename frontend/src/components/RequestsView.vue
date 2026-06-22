<script setup>
import { ref, computed, onMounted } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'
import { storeToRefs } from 'pinia'
import { useEventStyles } from '@/composables/useEventStyles'
import { Calendar, Clock, Trash2, Edit3, AlertCircle, Loader2, Plus, Send, ChevronDown } from 'lucide-vue-next'
import RequestLeaveModal from '@/components/modals/RequestLeaveModal.vue'

const scheduleStore = useScheduleStore()

const { leaveRequests, changeRequests, isLoading } = storeToRefs(scheduleStore)
const { getEventIcon, getIconColorClass, getStatusColorClass } = useEventStyles()

const currentFilter = ref('all')
const selectedMonth = ref('all')
const errorMessage = ref('')
const activeTab = ref('leave') // Steuert die Tabs wie im AI-Studio Design

const formatTime = (dateStr) => {
  if (!dateStr) return '--:--'
  return new Date(dateStr).toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const filters = [
  { id: 'all', name: 'Alle' },
  { id: 'pending', name: 'Offen' },
  { id: 'approved', name: 'Genehmigt' },
  { id: 'rejected', name: 'Abgelehnt' },
  { id: 'cancelled', name: 'Storniert' }
]

const monthOptions = computed(() => {
  const options = [{ id: 'all', name: 'Alle Monate' }]
  const now = new Date()
  
  for (let i = -6; i <= 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1)
    const id = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const name = d.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' })
    options.push({ id, name })
  }
  return options
})

const isEditModalOpen = ref(false)
const isRequestModalOpen = ref(false)
const editingRequest = ref(null)

onMounted(() => {
  scheduleStore.fetchLeaveRequests()
  scheduleStore.fetchChangeRequests()
})

// Filter-Logik für Urlaubsanträge
const filteredLeaveRequests = computed(() => {
  let list = leaveRequests.value || []

  // 1. Status Filter
  if (currentFilter.value !== 'all') {
    list = list.filter(req => req.status === currentFilter.value)
  } else {
    list = list.filter(req => req.status !== 'cancelled')
  }

  // 2. Datums Filter
  if (selectedMonth.value !== 'all') {
    // Teilt z.B. "2026-06" in Jahr = 2026 und Monat = 6
    const [filterYear, filterMonth] = selectedMonth.value.split('-').map(Number)
    
    list = list.filter(req => {
      const dateField = req.leave_start || req.start_date || req.start
      if (!dateField) return false // Ohne Datum passt es nicht in den Monat
      
      const reqDate = new Date(dateField)
      
      // Holt das Jahr (z.B. 2026) und den Monat (0-11, daher + 1) des Antrags
      const reqYear = reqDate.getFullYear()
      const reqMonth = reqDate.getMonth() + 1 
      
      // Nur anzeigen, wenn Jahr UND Monat exakt übereinstimmen
      return reqYear === filterYear && reqMonth === filterMonth
    })
  }

  return list
})

// Filter-Logik für Änderungsanträge (Zuvor aus Store-Events extrahiert)
const filteredChangeRequests = computed(() => {
  let list = changeRequests.value || []
    
  // 1. Status Filter
  if (currentFilter.value !== 'all') {
    list = list.filter(req => req.status === currentFilter.value)
  } else {
    list = list.filter(req => req.status !== 'cancelled')
  }
  
  // 2. Datums Filter (angepasst an typische Schicht-/Korrektur-Daten)
  if (selectedMonth.value !== 'all') {
    const [filterYear, filterMonth] = selectedMonth.value.split('-').map(Number)
    
    list = list.filter(req => {
      // Prüft die typischen Datumsfelder von Arbeitszeitkorrekturen (date oder request_date)
      const dateField = req.requested_check_in || req.requested_check_out
      if (!dateField) return false 
      
      const reqDate = new Date(dateField)
      const reqYear = reqDate.getFullYear()
      const reqMonth = reqDate.getMonth() + 1 
      
      return reqYear === filterYear && reqMonth === filterMonth
    })
  }
  
  return list
})

const openEditModal = (req) => {
  editingRequest.value = {
    id: req.id,
    startDate: req.leave_start,
    endDate: req.leave_end,
    leave_type: req.leave_type,
    note: req.note
  }
  isEditModalOpen.value = true
}

const openNewRequestModal = () => {
  editingRequest.value = null 
  isRequestModalOpen.value = true
}

const handleFormSubmit = async (formData) => {
  try {
    if (editingRequest.value?.id) {
      await scheduleStore.updateLeaveRequest(editingRequest.value.id, formData)
    } else {
      await scheduleStore.createLeaveRequest(formData)
    }
    await scheduleStore.fetchLeaveRequests()
    closeModals()
  } catch (error) {
    console.error("Fehler beim Speichern:", error)
  }
}

const confirmDelete = async (id) => {
  if (confirm('Möchtest du diesen Antrag wirklich stornieren?')) {
    try {
      errorMessage.value = ''
      await scheduleStore.deleteLeaveRequest(id)
      await scheduleStore.fetchLeaveRequests()
    } catch (err) {
      errorMessage.value = err.message
      alert(errorMessage.value)
    }
  }
}

const cancelChangeRequest = (shiftId) => {
  if (confirm('Möchtest du diesen Änderungsantrag wirklich stornieren?')) {
    scheduleStore.cancelShiftChangeRequest(shiftId)
  }
}

const closeModals = () => {
  isEditModalOpen.value = false
  isRequestModalOpen.value = false
  editingRequest.value = null
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}
</script>

<template>
  <div class="flex-1 overflow-y-auto p-8 bg-slate-50">
    <div class="max-w-4xl mx-auto space-y-8">
      
      <!-- Header & Controls -->
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Send class="w-6 h-6 text-blue-600" /> Meine Anträge
          </h1>
          <p class="text-slate-500 mt-1">
            Verwalte und verfolge deine eingereichten Abwesenheiten und Korrekturen.
          </p>
        </div>
        
        <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <!-- Time Filter (Monats-Auswahl) -->
          <div class="relative min-w-[160px]">
            <select 
              v-model="selectedMonth"
              class="w-full appearance-none pl-4 pr-10 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer shadow-sm"
            >
              <option v-for="month in monthOptions" :key="month.id" :value="month.id">
                {{ month.name }}
              </option>
            </select>
            <ChevronDown class="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <!-- Status Filter Bar -->
          <div class="flex items-center bg-white p-1 rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
            <button 
              v-for="filter in filters" 
              :key="filter.id"
              :class="[
                'px-4 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap',
                currentFilter === filter.id 
                  ? 'bg-slate-900 text-white shadow-md' 
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
              ]"
              @click="currentFilter = filter.id"
            >
              {{ filter.name }}
            </button>
          </div>
        </div>
      </section>

      <!-- Tab-Leiste zur Unterscheidung der Antragsarten -->
      <div class="flex border-b border-slate-200">
        <button 
          :class="[
            'pb-3.5 px-6 font-bold text-sm border-b-2 transition-all cursor-pointer whitespace-nowrap',
            activeTab === 'leave'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          ]"
          @click="activeTab = 'leave'"
        >
          Urlaubsanträge
        </button>
        <button 
          :class="[
            'pb-3.5 px-6 font-bold text-sm border-b-2 transition-all cursor-pointer whitespace-nowrap',
            activeTab === 'change'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          ]"
          @click="activeTab = 'change'"
        >
          Änderungsanträge (Korrekturen)
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center p-12 space-y-4">
        <Loader2 class="w-8 h-8 animate-spin text-blue-600" />
        <p class="text-slate-500 font-medium">Anträge werden geladen...</p>
      </div>

      <div v-else>
        <!-- TAB 1: URLAUBSANTRÄGE -->
        <div v-if="activeTab === 'leave'" class="space-y-6">
          <div v-if="filteredLeaveRequests.length > 0" class="space-y-4">
            <div 
              v-for="req in filteredLeaveRequests" 
              :key="req.id"
              class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all group"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex items-start gap-4">
                  <div :class="['p-3 rounded-xl bg-slate-50', getIconColorClass(req.leave_type)]">
                    <component :is="getEventIcon(req.leave_type)" class="w-6 h-6" />
                  </div>

                  <div class="space-y-1 text-left">
                    <div class="flex flex-wrap items-center gap-3">
                      <h3 class="font-bold text-slate-900 text-base">
                        {{ req.type_display || req.leave_type }}
                      </h3>
                      <span :class="['px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider', getStatusColorClass(req.status)]">
                        {{ req.status_display || req.status }} 
                      </span>
                      <span v-if="req.status !== 'pending' && req.status !== 'cancelled'" class="text-[10px] font-semibold text-slate-400">
                        • am {{ formatDate(req.reviewed_date) }} von {{ req.reviewed_by }}
                      </span>
                      <span v-if="req.status === 'pending'" class="text-[10px] font-semibold text-slate-400">
                        • beantragt am {{ formatDate(req.request_date) }}
                      </span>
                    </div>

                    <div class="flex items-center gap-4 text-sm text-slate-500">
                      <div class="flex items-center gap-1.5 font-medium">
                        <Calendar class="w-4 h-4 opacity-60" />
                        <span>
                          {{ formatDate(req.leave_start) }}
                          <span v-if="req.leave_start !== req.leave_end"> - {{ formatDate(req.leave_end) }}</span>
                        </span>
                      </div>
                      <div class="flex items-center gap-1.5 font-medium">
                        <Clock class="w-4 h-4 opacity-60" />
                        {{ req.days_count }} {{ req.days_count === 1 ? 'Tag' : 'Tage' }}
                      </div>
                    </div>

                    <p v-if="req.note" class="text-sm text-slate-400 mt-2 italic leading-relaxed">
                      "{{ req.note }}"
                    </p>
                  </div>
                </div>

                <!-- Aktionsbuttons (Sichtbar bei Hover über Gruppenkarte) -->
                <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                  <button 
                    v-if="req.status === 'pending'"
                    @click="openEditModal(req)"
                    class="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all"
                    title="Antrag bearbeiten"
                  >
                    <Edit3 class="w-5 h-5" />
                  </button>
                  <button 
                    v-if="['pending', 'approved'].includes(req.status)"
                    @click="confirmDelete(req.id)"
                    class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
                    title="Antrag stornieren"
                  >
                    <Trash2 class="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Neuer Antrag Button am Listenende -->
            <button 
              class="w-full py-6 border-2 border-dashed border-slate-200 rounded-2xl text-slate-400 font-bold hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50 transition-all flex items-center justify-center gap-2 group cursor-pointer"
              @click="openNewRequestModal"
            >
              <Plus class="w-5 h-5 group-hover:scale-110 transition-transform" />
              Neuen Abwesenheitsantrag erstellen
            </button>
          </div>

          <!-- Empty State Urlaub -->
          <div v-else class="bg-white rounded-[2.5rem] border border-slate-200 border-dashed p-16 text-center space-y-4">
            <div class="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto text-slate-300">
              <AlertCircle class="w-8 h-8" />
            </div>
            <div class="space-y-1">
              <h3 class="text-xl font-bold text-slate-900">Keine Einträge gefunden</h3>
              <p class="text-slate-500 max-w-xs mx-auto text-sm">
                {{ currentFilter === 'all' 
                  ? "Du hast bisher noch keine Abwesenheiten für den gewählten Zeitraum beantragt." 
                  : "Keine Urlaubsanträge mit diesem Status vorhanden." 
                }}
              </p>
            </div>
            <button 
              v-if="currentFilter === 'all'"
              class="flex items-center gap-2 px-6 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all mx-auto cursor-pointer"
              @click="openNewRequestModal"
            >
              <Plus class="w-4 h-4" />
              Ersten Antrag einreichen
            </button>
          </div>
        </div>

        <!-- TAB 2: ÄNDERUNGSANTRÄGE -->
        <div v-else class="space-y-6">
          <div v-if="filteredChangeRequests.length > 0" class="space-y-4">
            <div 
              v-for="request in filteredChangeRequests" 
              :key="request.id"
              class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all group"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex items-start gap-4">
                  <!-- Icon-Box analog zu den Urlaubsanträgen -->
                  <div class="p-3 rounded-xl bg-slate-50 text-blue-600">
                    <Clock class="w-6 h-6" />
                  </div>

                  <div class="space-y-1 text-left">
                    <!-- Titelzeile mit Status-Badge -->
                    <div class="flex flex-wrap items-center gap-3">
                      <h3 class="font-bold text-slate-900 text-base">
                        Arbeitszeitkorrektur
                      </h3>
                      <span :class="['px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider', getStatusColorClass(request.status)]">
                        {{ request.status_display || request.status }}
                      </span>
                      <span v-if="request.status !== 'pending' && request.status !== 'cancelled'" class="text-[10px] font-semibold text-slate-400">
                        • am {{ formatDate(request.reviewed_date) }} von {{ request.reviewed_by }}
                      </span>
                      <span v-if="request.status === 'pending'" class="text-[10px] font-semibold text-slate-400">
                        • beantragt am {{ formatDate(request.request_date) }}
                      </span>
                    </div>

                    <!-- Metadaten-Zeile (Exakt gleiches Layout wie bei Tab 1) -->
                    <div class="flex flex-wrap items-center gap-4 text-sm text-slate-500 mt-1">
                      <div class="flex items-center gap-1.5 font-medium">
                        <Calendar class="w-4 h-4 opacity-60" />
                        <span>{{ formatDate(request.requested_check_in) }}</span>
                      </div>
                      <div class="flex items-center gap-1.5 font-medium">
                        <Clock class="w-4 h-4 opacity-60" />
                        <span>
                          <span class="line-through text-slate-400">{{ formatTime(request.old_check_in) }} - {{ formatTime(request.old_check_out) }}</span>
                          <span class="text-blue-600 font-bold ml-1.5">→ {{ formatTime(request.requested_check_in) }} - {{ formatTime(request.requested_check_out) }}</span>
                        </span>
                      </div>
                    </div>

                    <!-- Mitarbeiter-Notiz im exakt gleichen Look -->
                    <p v-if="request.employee_note" class="text-sm text-slate-400 mt-2 italic leading-relaxed">
                      "{{ request.employee_note }}"
                    </p>
                  </div>
                </div>

                <!-- Aktionsbuttons (Sichtbar bei Hover über der Gruppenkarte) -->
                <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                  <button 
                    v-if="request.status === 'pending'"
                    @click="cancelChangeRequest(request.id)"
                    class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all cursor-pointer"
                    title="Änderung stornieren"
                  >
                    <Trash2 class="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State Korrekturen -->
          <div v-else class="bg-white rounded-[2.5rem] border border-slate-200 border-dashed p-16 text-center space-y-4">
            <div class="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto text-slate-300">
              <AlertCircle class="w-8 h-8" />
            </div>
            <div class="space-y-1">
              <h3 class="text-xl font-bold text-slate-900">Keine Arbeitszeitkorrekturen gefunden</h3>
              <p class="text-slate-500 max-w-xs mx-auto text-sm">
                {{ currentFilter === 'all' 
                  ? "Du hast für diesen Zeitraum noch keine Korrekturanträge eingereicht." 
                  : "Keine Korrekturanträge mit diesem Status vorhanden." 
                }}
              </p>
            </div>
          </div>
        </div>
      </div>
      
    </div>
  </div>

  <!-- Modal-Komponente bleibt voll funktionsfähig eingebunden -->
  <RequestLeaveModal 
    :is-open="isEditModalOpen || isRequestModalOpen"
    :leaveTypes="[
      { id: 'vacation', name: 'Urlaub' }, 
      { id: 'sick', name: 'Krankheit' },
      { id: 'overtime', name: 'GLZ-Abbau' }
    ]"
    :initial-data="editingRequest"
    @close="closeModals"
    @submit="handleFormSubmit"
  />
</template>