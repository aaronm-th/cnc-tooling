<script setup>
import { ref, onMounted, watch } from 'vue'
import { AlertCircle, Calendar, History, Search, Filter, ChevronDown, ShieldAlert } from 'lucide-vue-next'
import { useAdminStore } from '@/stores/adminStore'
import { storeToRefs } from 'pinia'
import LeaveRequestList from '@/components/supervisor/LeaveRequestList.vue'
import ChangeRequestList from '@/components/supervisor/ChangeRequestList.vue'

const adminStore = useAdminStore()
const { isLoading } = storeToRefs(adminStore)

const activeTab = ref(localStorage.getItem('admin_active_tab') || 'leave')
const searchQuery = ref('')
const statusFilter = ref('all')

const { 
  requests_count,
  change_requests_count,
  leave_requests_count 
} = storeToRefs(adminStore)



onMounted(() => {
  adminStore.fetchLeaveRequests()
  adminStore.fetchChangeRequests()
})

watch(activeTab, (newTab) => {
  localStorage.setItem('admin_active_tab', newTab)
})
</script>

<template>
  <div class="flex-1 overflow-y-auto p-8 bg-slate-50">
    <div class="max-w-4xl mx-auto space-y-8">
      
      <!-- Header & Controls -->
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <ShieldAlert class="w-6 h-6 text-blue-600" /> Anfragen verwalten
          </h1>
          <p class="text-slate-500 mt-1">
            Zentrale Freigabe und Verwaltung aller Team-Abwesenheiten und Arbeitszeitkorrekturen.
          </p>
        </div>
        
        <!-- Offen-Badge im Design des Headers -->
        <div v-if="requests_count > 0" class="flex items-center bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 self-start md:self-center shadow-sm gap-2">
          <AlertCircle class="w-4 h-4 text-amber-500" />
          <span class="text-xs font-bold text-amber-700">
            Offen: {{ requests_count ?? 0 }}
          </span>
        </div>
      </section>

      <!-- Filter- & Suchleiste (Übernommen aus dem Steuerungs-Stil von View 1) -->
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <!-- Suchfeld -->
        <div class="relative flex-1">
          <Search class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Suchen..." 
            class="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm outline-none"
          />
        </div>

        <!-- Status Filter Dropdown -->
        <div class="relative min-w-[160px]">
          <select 
            v-model="statusFilter"
            class="w-full appearance-none pl-10 pr-10 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer shadow-sm"
          >
            <option value="all">Alle Status</option>
            <option value="pending">Offen</option>
            <option value="approved">Genehmigt</option>
            <option value="rejected">Abgelehnt</option>
          </select>
          <Filter class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <ChevronDown class="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

<!-- Tab-Leiste (Orientiert an deinem Notification-Design) -->
    <div class="flex border-b border-slate-200">
      
      <!-- Tab: Abwesenheiten -->
      <button 
        :class="[
          'pb-3.5 px-6 pr-8 font-bold text-sm border-b-2 transition-all cursor-pointer whitespace-nowrap relative',
          activeTab === 'leave'
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-slate-500 hover:text-slate-800'
        ]"
        @click="activeTab = 'leave'"
      >
        Abwesenheiten
        <!-- Roter Punkt exakt wie beim Notification-Badge -->
        <span 
          v-if="leave_requests_count > 0" 
          class="absolute top-1 right-4 w-2 h-2 bg-red-500 rounded-full border-2 border-white"
        />
      </button>
      
      <!-- Tab: Zeitkorrekturen -->
      <button 
        :class="[
          'pb-3.5 px-6 pr-8 font-bold text-sm border-b-2 transition-all cursor-pointer whitespace-nowrap relative',
          activeTab === 'change'
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-slate-500 hover:text-slate-800'
        ]"
        @click="activeTab = 'change'"
      >
        Zeitkorrekturen
        <!-- Roter Punkt exakt wie beim Notification-Badge -->
        <span 
          v-if="change_requests_count > 0" 
          class="absolute top-1 right-4 w-2 h-2 bg-red-500 rounded-full border-2 border-white"
        />
      </button>

    </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center p-12 space-y-4">
        <div class="animate-spin inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
        <p class="text-slate-500 font-medium text-sm">Lade Daten...</p>
      </div>

      <!-- Listen-Inhalt -->
      <div v-else class="space-y-6">
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