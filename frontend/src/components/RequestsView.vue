<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useScheduleStore } from '@/stores/scheduleStore'
import { storeToRefs } from 'pinia'
import { useEventStyles } from '@/composables/useEventStyles'
import { useDateFormatter } from '@/composables/useDateFormatter'
import { Calendar, Clock, Trash2, Edit3, AlertCircle, Loader2, Plus, Send, ChevronDown } from 'lucide-vue-next'
import RequestLeaveModal from '@/components/modals/RequestLeaveModal.vue'

const scheduleStore = useScheduleStore()

const leaveTypes = [
  { id: 'vacation', name: 'Urlaub' }, 
  { id: 'sick', name: 'Krankheit' }
]

const { leaveRequests, changeRequests, isLoading } = storeToRefs(scheduleStore)
const { getEventIcon, getIconColorClass, getStatusColorClass } = useEventStyles()
const { formatDate, formatTime } = useDateFormatter()

const currentFilter = ref('all')
const selectedMonth = ref('all')
const errorMessage = ref('')

const activeTab = ref(localStorage.getItem('active_request_tab') || 'leave')

watch(activeTab, (newTab) => {
  localStorage.setItem('active_request_tab', newTab)
})

const filters = [
  { id: 'all', name: 'Alle' },
  { id: 'pending', name: 'Offen' },
  { id: 'approved', name: 'Genehmigt' },
  { id: 'rejected', name: 'Abgelehnt' },
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

const filteredLeaveRequests = computed(() => {
  let list = leaveRequests.value || []

  if (currentFilter.value !== 'all') {
    list = list.filter(req => req.status === currentFilter.value)
  } else {
    list = list.filter(req => req.status !== 'cancelled')
  }

  if (selectedMonth.value !== 'all') {
    const [filterYear, filterMonth] = selectedMonth.value.split('-').map(Number)
    list = list.filter(req => {
      const dateField = req.leave_start || req.start_date || req.start
      if (!dateField) return false 
      const reqDate = new Date(dateField)
      return reqDate.getFullYear() === filterYear && (reqDate.getMonth() + 1) === filterMonth
    })
  }
  return list
})

const filteredChangeRequests = computed(() => {
  let list = changeRequests.value || []
  if (currentFilter.value !== 'all') {
    list = list.filter(req => req.status === currentFilter.value)
  } else {
    list = list.filter(req => req.status !== 'cancelled')
  }
  
  if (selectedMonth.value !== 'all') {
    const [filterYear, filterMonth] = selectedMonth.value.split('-').map(Number)
    list = list.filter(req => {
      const dateField = req.requested_check_in || req.requested_check_out
      if (!dateField) return false 
      const reqDate = new Date(dateField)
      return reqDate.getFullYear() === filterYear && (reqDate.getMonth() + 1) === filterMonth
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

const cancelChangeRequest = async (shiftId) => {
  if (confirm('Möchtest du diesen Änderungsantrag wirklich stornieren?')) {
    try {
      errorMessage.value = ''
      await scheduleStore.withdrawShiftChangeRequest(shiftId)
      await scheduleStore.fetchChangeRequests()
    } catch (err) {
      errorMessage.value = err.message
      alert(errorMessage.value)
    }
  }
}

const closeModals = () => {
  isEditModalOpen.value = false
  isRequestModalOpen.value = false
  editingRequest.value = null
}

const handleLeaveSuccess = () => {
  closeModals()
  scheduleStore.fetchLeaveRequests()
}
</script>

<template>
  <div class="flex-1 overflow-y-auto p-8 bg-slate-50">
    <div class="max-w-7xl mx-auto space-y-8">
      
      <!-- HEADER -->
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="p-2.5 bg-blue-50 text-blue-600 rounded-xl shrink-0">
            <Send class="w-6 h-6" />
          </div>
          <div class="text-left">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Meine Anträge</h1>
            <p class="text-slate-500 text-sm mt-0.5">Verwalte und verfolge deine eingereichten Abwesenheiten und Korrekturen.</p>
          </div>
        </div>
      </section>

      <!-- DIE KOMBIFILTER-BOX (Identisch zum neuen Admin-Design) -->
      <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 bg-white p-3 rounded-2xl border border-slate-200 shadow-sm">
          
        <div class="flex items-center gap-1.5 p-1 bg-slate-50 rounded-xl border border-slate-100 w-full lg:w-auto overflow-x-auto min-w-0 shrink-0">
          <button 
            :class="[
              'flex-1 lg:flex-none px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center justify-center gap-2',
              activeTab === 'leave' 
                ? 'bg-slate-900 text-white shadow-sm' 
                : 'text-slate-500 hover:text-slate-800'
            ]"
            @click="activeTab = 'leave'"
          >
            <span>Urlaubsanträge</span>
          </button>

          <button 
            :class="[
              'flex-1 lg:flex-none px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center justify-center gap-2',
              activeTab === 'change' 
                ? 'bg-slate-900 text-white shadow-sm' 
                : 'text-slate-500 hover:text-slate-800'
            ]"
            @click="activeTab = 'change'"
          >
            <span>Zeitkorrekturen</span>
          </button>
        </div>

        <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full lg:w-auto flex-wrap">
          
          <div class="relative flex-1 sm:flex-none min-w-[140px]">
            <Calendar class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
            <select 
              v-model="selectedMonth"
              class="w-full sm:w-40 pl-9 pr-8 py-1.5 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer appearance-none shadow-sm"
            >
              <option v-for="month in monthOptions" :key="month.id" :value="month.id">
                {{ month.name }}
              </option>
            </select>
            <ChevronDown class="w-3.5 h-3.5 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <div class="flex items-center bg-slate-50 p-1 rounded-xl border border-slate-200/60 overflow-x-auto w-full sm:w-auto min-w-0">
            <button 
              v-for="filter in filters" 
              :key="filter.id"
              :class="[
                'flex-1 sm:flex-none px-4 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap cursor-pointer text-center',
                currentFilter === filter.id 
                  ? 'bg-slate-900 text-white shadow-sm' 
                  : 'text-slate-500 hover:bg-white hover:text-slate-800'
              ]"
              @click="currentFilter = filter.id"
            >
              {{ filter.name }}
            </button>
          </div>
        </div>

      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center p-16 bg-white rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <Loader2 class="w-6 h-6 animate-spin text-blue-600" />
        <p class="text-slate-500 font-medium text-xs">Anträge werden geladen...</p>
      </div>

      <div v-else>
        <!-- TAB 1: URLAUBSANTRÄGE -->
        <div v-if="activeTab === 'leave'" class="space-y-6">
          <div v-if="filteredLeaveRequests.length > 0" class="space-y-4">
            <div 
              v-for="req in filteredLeaveRequests" 
              :key="req.id"
              class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all group"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex items-start gap-4">
                  <div :class="['p-2.5 rounded-xl bg-slate-50 border border-slate-100', getIconColorClass(req.leave_type)]">
                    <component :is="getEventIcon(req.leave_type)" class="w-5 h-5" />
                  </div>

                  <div class="space-y-1 text-left">
                    <div class="flex flex-wrap items-center gap-2">
                      <h3 class="font-bold text-slate-900 text-sm">
                        {{ req.type_display || req.leave_type }}
                      </h3>
                      <span :class="['px-2 py-0.5 rounded-md text-[9px] font-extrabold uppercase tracking-wider', getStatusColorClass(req.status)]">
                        {{ req.status_display || req.status }} 
                      </span>
                      <span v-if="req.status !== 'pending' && req.status !== 'cancelled'" class="text-[10px] font-medium text-slate-400">
                        am {{ formatDate(req.reviewed_date) }}
                      </span>
                      <span v-if="req.status === 'pending'" class="text-[10px] font-medium text-slate-400">
                        Beantragt am {{ formatDate(req.request_date) }}
                      </span>
                    </div>

                    <div class="flex items-center gap-4 text-xs text-slate-500">
                      <div class="flex items-center gap-1.5 font-semibold">
                        <Calendar class="w-4 h-4 opacity-50 text-slate-400" />
                        <span>
                          {{ formatDate(req.leave_start) }}
                          <span v-if="req.leave_start !== req.leave_end"> - {{ formatDate(req.leave_end) }}</span>
                        </span>
                      </div>
                      <div class="flex items-center gap-1.5 font-semibold">
                        <Clock class="w-4 h-4 opacity-50 text-slate-400" />
                        {{ req.days_count }} {{ req.days_count === 1 ? 'Tag' : 'Tage' }}
                      </div>
                    </div>

                    <p v-if="req.note" class="text-xs text-slate-400 mt-2 italic border-l-2 border-slate-200 pl-2">
                      "{{ req.note }}"
                    </p>
                  </div>
                </div>

                <!-- Aktionsbuttons bei Hover -->
                <div class="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-all">
                  <button 
                    v-if="req.status === 'pending'"
                    @click="openEditModal(req)"
                    class="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all cursor-pointer"
                    title="Antrag bearbeiten"
                  >
                    <Edit3 class="w-4 h-4" />
                  </button>
                  <button 
                    v-if="['pending'].includes(req.status)"
                    @click="confirmDelete(req.id)"
                    class="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all cursor-pointer"
                    title="Antrag stornieren"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Neuer Antrag Button am Listenende -->
            <button 
              class="w-full py-5 border-2 border-dashed border-slate-200 hover:border-blue-300 rounded-2xl text-slate-400 font-bold text-xs hover:text-blue-600 hover:bg-blue-50/20 transition-all flex items-center justify-center gap-2 group cursor-pointer"
              @click="openNewRequestModal"
            >
              <Plus class="w-4 h-4 group-hover:scale-110 transition-transform" />
              Neuen Abwesenheitsantrag erstellen
            </button>
          </div>

          <!-- Empty State Urlaub -->
          <div v-else class="bg-white rounded-[2.5rem] border border-slate-200 border-dashed p-16 text-center space-y-4">
            <div class="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto text-slate-300">
              <AlertCircle class="w-7 h-7" />
            </div>
            <div class="space-y-1">
              <h3 class="text-lg font-bold text-slate-900">Keine Einträge gefunden</h3>
              <p class="text-slate-400 max-w-xs mx-auto text-xs">
                {{ currentFilter === 'all' 
                  ? "Du hast bisher noch keine Abwesenheiten für den gewählten Zeitraum beantragt." 
                  : "Keine Urlaubsanträge mit diesem Status vorhanden." 
                }}
              </p>
            </div>
            <button 
              class="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition-all mx-auto cursor-pointer"
              @click="openNewRequestModal"
            >
              <Plus class="w-4 h-4" />
              Neuen Abwesenheitsantrag erstellen
            </button>
          </div>
        </div>

        <!-- TAB 2: ÄNDERUNGSANTRÄGE -->
        <div v-else class="space-y-6">
          <div v-if="filteredChangeRequests.length > 0" class="space-y-4">
            <div 
              v-for="request in filteredChangeRequests" 
              :key="request.id"
              class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all group"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex items-start gap-4">
                  <div class="p-2.5 rounded-xl bg-slate-50 text-blue-600 border border-slate-100">
                    <Clock class="w-5 h-5" />
                  </div>

                  <div class="space-y-1 text-left">
                    <div class="flex flex-wrap items-center gap-2">
                      <h3 class="font-bold text-slate-900 text-sm">Arbeitszeitkorrektur</h3>
                      <span :class="['px-2 py-0.5 rounded-md text-[9px] font-extrabold uppercase tracking-wider', getStatusColorClass(request.status)]">
                        {{ request.status_display || request.status }}
                      </span>
                      <span v-if="request.status !== 'pending' && request.status !== 'cancelled'" class="text-[10px] font-medium text-slate-400">
                        am {{ formatDate(request.reviewed_date) }}
                      </span>
                      <span v-if="request.status === 'pending'" class="text-[10px] font-medium text-slate-400">
                        Beantragt am {{ formatDate(request.request_date) }}
                      </span>
                    </div>

                    <div class="flex flex-wrap items-center gap-4 text-xs text-slate-500 mt-1">
                      <div class="flex items-center gap-1.5 font-semibold">
                        <Calendar class="w-4 h-4 opacity-50 text-slate-400" />
                        <span>{{ formatDate(request.requested_check_in) }}</span>
                      </div>
                      <div class="flex items-center gap-1.5 font-semibold">
                        <Clock class="w-4 h-4 opacity-50 text-slate-400" />
                        <span>
                          <span class="line-through text-slate-400">{{ formatTime(request.old_check_in) }} - {{ formatTime(request.old_check_out) }}</span>
                          <span class="text-blue-600 font-bold ml-1.5">→ {{ formatTime(request.requested_check_in) }} - {{ formatTime(request.requested_check_out) }}</span>
                        </span>
                        
                        <span v-if="request.time_diff" class="text-[9px] font-bold px-1.5 py-0.5 rounded-md border bg-amber-50 text-amber-600 border-amber-100 shrink-0">
                          {{ request.time_diff }}
                        </span>
                      </div>
                    </div>

                    <p v-if="request.employee_note" class="text-xs text-slate-400 mt-2 italic border-l-2 border-slate-200 pl-2">
                      "{{ request.employee_note }}"
                    </p>
                  </div>
                </div>

                <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                  <button 
                    v-if="request.status === 'pending'"
                    @click="cancelChangeRequest(request.id)"
                    class="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all cursor-pointer"
                    title="Änderung stornieren"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State Korrekturen -->
          <div v-else class="bg-white rounded-[2.5rem] border border-slate-200 border-dashed p-16 text-center space-y-4">
            <div class="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto text-slate-300">
              <AlertCircle class="w-7 h-7" />
            </div>
            <div class="space-y-1">
              <h3 class="text-lg font-bold text-slate-900">Keine Arbeitszeitkorrekturen gefunden</h3>
              <p class="text-slate-400 max-w-xs mx-auto text-xs">
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

<RequestLeaveModal 
  ref="leaveModalRef"
  :is-open="isEditModalOpen || isRequestModalOpen"
  :leaveTypes="leaveTypes"
  :initial-data="editingRequest"
  @close="closeModals"
  @success="handleLeaveSuccess"
/>
</template>