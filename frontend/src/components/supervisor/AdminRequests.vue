<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { ShieldAlert, Loader2, ChevronDown, User, Calendar } from 'lucide-vue-next' // Search entfernt, da nicht mehr benötigt
import { useAdminStore } from '@/stores/adminStore'
import { useAppStore } from '@/stores/appStore' 
import { storeToRefs } from 'pinia'
import LeaveRequestList from '@/components/supervisor/LeaveRequestList.vue'
import ChangeRequestList from '@/components/supervisor/ChangeRequestList.vue'

const adminStore = useAdminStore()
const appStore = useAppStore() 

const { 
  isLoading, 
  leaveRequests, 
  changeRequests,
  change_requests_count,
  leave_requests_count 
} = storeToRefs(adminStore)


const activeTab = ref(localStorage.getItem('admin_active_tab') || 'leave')
const searchQuery = ref('') // Bleibt als leerer String aktiv, damit `:search` keinen Fehler wirft
const statusFilter = ref('all')


const selectedEmployee = ref('all')
const selectedMonth = ref('all')

const filters = [
  { id: 'all', name: 'Alle' },
  { id: 'pending', name: 'Offen' },
  { id: 'approved', name: 'Genehmigt' },
  { id: 'rejected', name: 'Abgelehnt' },
]

const employeeOptions = computed(() => {
  const names = new Set()
  
  // Namen aus beiden Antragsarten sammeln
  leaveRequests.value.forEach(r => {
    if (r.employee_name || r.name) names.add(r.employee_name || r.name)
  })
  changeRequests.value.forEach(r => {
    const n = r.requester?.name
    if (n) names.add(n)
  })
  
  return ['all', ...Array.from(names).sort()]
})


// Generiert alle 12 Monate des aktuellen Jahres (Neueste zuerst)
const monthOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  const months = []
  
  // Schleife rückwärts von Dezember (12) bis Januar (1)
  for (let m = 12; m >= 1; m--) {
    const monthStr = String(m).padStart(2, '0')
    months.push(`${currentYear}-${monthStr}`)
  }
  
  // Falls du auch das Vorjahr oder Folgejahr brauchst, könntest du hier weitere hinzufügen
  return ['all', ...months]
})

// Wandelt "2026-07" in "Juli 2026" um
const formatMonthName = (yearMonthStr) => {
  if (yearMonthStr === 'all') return 'Alle Monate'
  const [year, month] = yearMonthStr.split('-')
  const date = new Date(parseInt(year), parseInt(month) - 1, 1)
  return date.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' })
}


onMounted(() => {
  adminStore.fetchLeaveRequests()
  adminStore.fetchChangeRequests()
  
  if (appStore.activeSubTab) {
    activeTab.value = appStore.activeSubTab
    appStore.activeSubTab = null 
  }
})

watch(() => appStore.activeSubTab, (newSubTab) => {
  if (newSubTab) {
    activeTab.value = newSubTab
    appStore.activeSubTab = null 
  }
})

watch(activeTab, (newTab) => {
  localStorage.setItem('admin_active_tab', newTab)
})


watch(activeTab, () => {
  selectedEmployee.value = 'all'
  selectedMonth.value = 'all'
})

</script>

<template>
  <div class="flex-1 overflow-y-auto bg-slate-50 p-8">
    <div class="max-w-7xl mx-auto space-y-8">
      
      <!-- Identischer Header -->
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="p-2.5 bg-blue-50 text-blue-600 rounded-xl shrink-0">
            <ShieldAlert class="w-6 h-6" />
          </div>
          <div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Anträge & Freigaben</h1>
            <p class="text-slate-500 text-sm mt-0.5">
              Prüfe und verwalte die eingereichten Urlaubsanträge und nachträglichen Zeitkorrekturen deines Teams.
            </p>
          </div>
        </div>
      </section>

      <!-- DIE KOMBIFILTER-BOX (Eine Box, kein Suchen-Feld mehr) -->
<div class="flex flex-col xl:flex-row items-stretch xl:items-center justify-between gap-4 bg-white p-3 rounded-2xl border border-slate-200 shadow-sm">
  
  <div class="flex items-center gap-1.5 p-1 bg-slate-50 rounded-xl border border-slate-200/60 w-full xl:w-auto overflow-x-auto min-w-0 shrink-0">
    <button 
      :class="[
        'flex-1 xl:flex-none px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center justify-center gap-2',
        activeTab === 'leave' 
          ? 'bg-slate-900 text-white shadow-sm' 
          : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
      ]"
      @click="activeTab = 'leave'"
    >
      <span>Abwesenheiten</span>
      <span 
        :class="[
          'px-1.5 py-0.5 rounded-md text-[10px] font-bold transition-all',
          activeTab === 'leave'
            ? (leave_requests_count > 0 ? 'bg-white/20 text-white' : 'bg-white/10 text-white/60')
            : (leave_requests_count > 0 ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-500')
        ]"
      >
        {{ leave_requests_count }}
      </span>
    </button>

    <button 
      :class="[
        'flex-1 xl:flex-none px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center justify-center gap-2',
        activeTab === 'change' 
          ? 'bg-slate-900 text-white shadow-sm' 
          : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
      ]"
      @click="activeTab = 'change'"
    >
      <span>Zeitkorrekturen</span>
      <span 
        :class="[
          'px-1.5 py-0.5 rounded-md text-[10px] font-bold transition-all',
          activeTab === 'change'
            ? (change_requests_count > 0 ? 'bg-white/20 text-white' : 'bg-white/10 text-white/60')
            : (change_requests_count > 0 ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-500')
        ]"
      >
        {{ change_requests_count }}
      </span>
    </button>
  </div>

  <div class="flex flex-col md:flex-row items-stretch md:items-center gap-3 w-full xl:w-auto flex-wrap">
    
    <div class="flex items-center bg-slate-50 p-1 rounded-xl border border-slate-200/60 overflow-x-auto justify-start w-full md:w-auto min-w-0">
      <button 
        v-for="filter in filters" 
        :key="filter.id"
        :class="[
          'flex-1 md:flex-none px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap cursor-pointer text-center',
          statusFilter === filter.id 
            ? 'bg-slate-900 text-white shadow-sm' 
            : 'text-slate-500 hover:bg-white/60 hover:text-slate-800'
        ]"
        @click="statusFilter = filter.id"
      >
        {{ filter.name }}
      </button>
    </div>

    <div class="flex items-center gap-2 w-full md:w-auto">
      <div class="relative flex-1 md:flex-none min-w-[140px]">
        <select 
          v-model="selectedEmployee"
          class="w-full md:w-40 pl-8 pr-8 py-1.5 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 appearance-none focus:outline-none focus:ring-2 focus:ring-slate-900 cursor-pointer hover:border-slate-300 transition-colors"
        >
          <option value="all">Alle Mitarbeiter</option>
          <option v-for="emp in employeeOptions.filter(e => e !== 'all')" :key="emp" :value="emp">
            {{ emp }}
          </option>
        </select>
        <User class="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <ChevronDown class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>

      <div class="relative flex-1 md:flex-none min-w-[130px]">
        <select 
          v-model="selectedMonth"
          class="w-full md:w-36 pl-8 pr-8 py-1.5 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 appearance-none focus:outline-none focus:ring-2 focus:ring-slate-900 cursor-pointer hover:border-slate-300 transition-colors"
        >
          <option value="all">Alle Monate</option>
          <option v-for="m in monthOptions.filter(mo => mo !== 'all')" :key="m" :value="m">
            {{ formatMonthName(m) }}
          </option>
        </select>
        <Calendar class="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <ChevronDown class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>
    </div>

  </div>

</div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center p-12 space-y-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
        <Loader2 class="w-8 h-8 animate-spin text-blue-600" />
        <p class="text-slate-500 font-medium text-sm">Daten werden geladen...</p>
      </div>

      <!-- Listen-Inhalt -->
      <div v-else class="space-y-6">
        <!-- Props werden jetzt exakt wie im Original weitergereicht, es bricht nichts ab -->
        <LeaveRequestList 
          v-if="activeTab === 'leave'" 
          :status="statusFilter"
          :search="searchQuery"
          :employee-filter="selectedEmployee"
          :month-filter="selectedMonth"
        />

        <ChangeRequestList 
          v-else 
          :status="statusFilter"
          :search="searchQuery"
          :employee-filter="selectedEmployee"
          :month-filter="selectedMonth"
        />
      </div>
      
    </div>
  </div>
</template>