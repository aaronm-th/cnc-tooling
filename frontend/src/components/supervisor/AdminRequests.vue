<script setup>
import { ref, onMounted, watch } from 'vue'
import { AlertCircle, ShieldAlert, Loader2 } from 'lucide-vue-next' // Search entfernt, da nicht mehr benötigt
import { useAdminStore } from '@/stores/adminStore'
import { useAppStore } from '@/stores/appStore' 
import { storeToRefs } from 'pinia'
import LeaveRequestList from '@/components/supervisor/LeaveRequestList.vue'
import ChangeRequestList from '@/components/supervisor/ChangeRequestList.vue'

const adminStore = useAdminStore()
const appStore = useAppStore() 

const { isLoading } = storeToRefs(adminStore)

const activeTab = ref(localStorage.getItem('admin_active_tab') || 'leave')
const searchQuery = ref('') // Bleibt als leerer String aktiv, damit `:search` keinen Fehler wirft
const statusFilter = ref('all')

const filters = [
  { id: 'all', name: 'Alle' },
  { id: 'pending', name: 'Offen' },
  { id: 'approved', name: 'Genehmigt' },
  { id: 'rejected', name: 'Abgelehnt' },
]

const { 
  requests_count,
  change_requests_count,
  leave_requests_count 
} = storeToRefs(adminStore)

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
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-white p-3 rounded-2xl border border-slate-200 shadow-sm">
        
        <!-- Linke Seite: Der Typen-Wechsler im edlen Pillen-Stil mit Zahlen-Badges -->
        <div class="flex items-center gap-1.5 p-1 bg-slate-50 rounded-xl border border-slate-100 w-full sm:w-auto">
          <!-- Tab: Abwesenheiten -->
          <button 
            :class="[
              'px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-2',
              activeTab === 'leave' 
                ? 'bg-white text-slate-950 shadow-sm border border-slate-200/60' 
                : 'text-slate-500 hover:text-slate-800'
            ]"
            @click="activeTab = 'leave'"
          >
            <span>Abwesenheiten</span>
            <span 
              :class="[
                'px-1.5 py-0.5 rounded-md text-[10px] font-bold transition-all',
                leave_requests_count > 0 ? 'bg-blue-600 text-white' : 'bg-slate-200/70 text-slate-600'
              ]"
            >
              {{ leave_requests_count }}
            </span>
          </button>

          <!-- Tab: Zeitkorrekturen -->
          <button 
            :class="[
              'px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-2',
              activeTab === 'change' 
                ? 'bg-white text-slate-950 shadow-sm border border-slate-200/60' 
                : 'text-slate-500 hover:text-slate-800'
            ]"
            @click="activeTab = 'change'"
          >
            <span>Zeitkorrekturen</span>
            <span 
              :class="[
                'px-1.5 py-0.5 rounded-md text-[10px] font-bold transition-all',
                change_requests_count > 0 ? 'bg-blue-600 text-white' : 'bg-slate-200/70 text-slate-600'
              ]"
            >
              {{ change_requests_count }}
            </span>
          </button>
        </div>

        <!-- Rechte Seite: Status Filter Bar -->
        <div class="flex items-center bg-slate-50 p-1 rounded-xl border border-slate-200/60 overflow-x-auto w-full sm:w-auto justify-start sm:justify-end">
          <button 
            v-for="filter in filters" 
            :key="filter.id"
            :class="[
              'px-4 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap cursor-pointer',
              statusFilter === filter.id 
                ? 'bg-slate-900 text-white shadow-sm' 
                : 'text-slate-500 hover:bg-white hover:text-slate-800'
            ]"
            @click="statusFilter = filter.id"
          >
            {{ filter.name }}
          </button>
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
          :search="searchQuery" 
          :status="statusFilter" 
        />
        <ChangeRequestList 
          v-else 
          :search="searchQuery" 
          :status="statusFilter" 
        />
      </div>
      
    </div>
  </div>
</template>