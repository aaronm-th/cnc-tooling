<script setup>
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { 
  Users, 
  Clock, 
  Calendar, 
  CheckCircle2, 
  XCircle, 
  TrendingUp,
  FileText
} from 'lucide-vue-next'

// Stores & Composables
import { useAdminStore } from '@/stores/adminStore'
import { useAppStore } from '@/stores/appStore'
import { useEventStyles } from '@/composables/useEventStyles'

// 1. Stores & Composables initialisieren
const adminStore = useAdminStore()
const appStore = useAppStore()
const { getEventIcon, getIconColorClass, getBadgeColorClass } = useEventStyles()

// 2. Reaktive Daten direkt aus dem Admin-Store ziehen
// 'onLeaveTodayCount' fängt deine Fehlermeldung ab
const { teamMembers, pendingRequests, onLeaveTodayCount, employeesCount } = storeToRefs(adminStore)


// 4. Actions (Direkt an den Store weitergeleitet)
const approveRequest = (id) => adminStore.approveRequest(id)
const rejectRequest = (id) => {
  if (confirm('Anfrage wirklich ablehnen?')) adminStore.rejectRequest(id)
}


// 5. Lifecycle Hook (Daten beim Laden der Komponente einmalig holen)
onMounted(async () => {
  await adminStore.fetchDashboardData()
})
</script>



<template>
  <div class="flex-1 h-screen overflow-y-auto bg-slate-50">
    <div class="max-w-7xl mx-auto p-8 space-y-8">
      
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold text-slate-900">Admin Dashboard</h1>
          <p class="text-slate-500 mt-1">Übersicht über Team-Performance und offene Aufgaben.</p>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div class="p-4 bg-blue-50 rounded-2xl text-blue-600">
            <Users class="w-7 h-7" />
          </div>
          <div>
            <p class="text-sm font-medium text-slate-500">Mitarbeiter Gesamt</p>
            <h3 class="text-2xl font-bold text-slate-900">{{ employeesCount || 0 }}</h3>
          </div>
        </div>
        
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div class="p-4 bg-amber-50 rounded-2xl text-amber-600">
            <Clock class="w-7 h-7" />
          </div>
          <div>
            <p class="text-sm font-medium text-slate-500">Offene Anträge</p>
            <h3 class="text-2xl font-bold text-slate-900">{{ pendingRequests ?? 0 }}</h3>
          </div>
        </div>
        
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div class="p-4 bg-emerald-50 rounded-2xl text-emerald-600">
            <Calendar class="w-7 h-7" />
          </div>
          <div>
            <p class="text-sm font-medium text-slate-500">Heute Abwesend</p>
            <h3 class="text-2xl font-bold text-slate-900">{{ onLeaveTodayCount || 0 }}</h3>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">

        <div class="lg:col-span-2 space-y-8">
          <div class="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
            <h2 class="font-bold text-lg text-slate-900 mb-6 flex items-center gap-2">
              <TrendingUp class="w-5 h-5 text-blue-600" />
              Team Status
            </h2>
            <div class="space-y-5">
              <div v-for="member in teamMembers.slice(0, 5)" :key="member.id" class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-xs font-bold text-blue-600 border-2 border-white shadow-sm">
                    {{ member.initials }}
                  </div>
                  <div>
                    <p class="text-sm font-bold text-slate-900">{{ member.name }}</p>
                  </div>
                </div>
                <span :class="[
                  'px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider',
                  member.status === 'Anwesend' || member.status === 'Active' ? 'bg-emerald-100 text-emerald-700' : 
                  member.status === 'Urlaub' || member.status === 'Vacation' ? 'bg-blue-100 text-blue-700' :
                  'bg-amber-100 text-amber-700'
                ]">
                  {{ member.status }}
                </span>
              </div>
            </div>
            <button 
              @click="appStore.setTab('admin-team')" 
              class="block w-full text-center mt-8 py-3 text-sm font-bold text-blue-600 hover:bg-blue-50 rounded-2xl transition-all border border-blue-100"
            >
              Alle Mitarbeiter anzeigen
            </button>
          </div>


        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Custom Scrollbar für den Main Content */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background-color: #e2e8f0;
  border-radius: 10px;
}
</style>