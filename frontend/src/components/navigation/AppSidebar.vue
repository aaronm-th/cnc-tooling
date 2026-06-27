<script setup>
import { 
  LayoutDashboard, Users, Calendar, FileText, 
  ClipboardCheck, BarChart3, BookUser, Send 
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/authStore' 
import { storeToRefs } from 'pinia'

defineProps({
  currentTab: { type: String, required: true }
})

const emit = defineEmits(['update:currentTab'])

const authStore = useAuthStore()
const { isSupervisor } = storeToRefs(authStore)

// Backend-URL aus der .env holen (Vite-Standard)
const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'


// Navigation für normale Mitarbeiter
const employeeNav = [
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard },
  { id: 'team', name: 'Kontakte', icon: BookUser },
  { id: 'schedule', name: 'Kalender', icon: Calendar },
  { id: 'requests', name: 'Meine Anträge', icon: Send },
  { id: 'documents', name: 'Dokumente', icon: FileText },
]

// Navigation für Admins / Vorgesetzte
const adminNav = [
  { id: 'admin-dashboard', name: 'Dashboard', icon: LayoutDashboard },
  { id: 'admin-team', name: 'Mitarbeiterübersicht', icon: Users },
  { id: 'admin-requests', name: 'Anfragen verwalten', icon: ClipboardCheck },
  { id: 'admin-calendar', name: 'Teamkalender', icon: Calendar },
]
</script>

<template>
  <aside class="w-64 bg-slate-900 text-white flex flex-col">
    <div class="p-6 flex items-center gap-4 border-b border-slate-800/50">
      <div class="w-15 h-15 flex items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 p-0 shadow-md border border-slate-700/50">
        <img 
          :src="`${backendUrl}/media/logos/jv_logo.png`" 
          alt="Logo"
          class="w-full h-full object-contain"
        />
      </div>
      <div class="flex flex-col">
        <span class="font-bold text-lg tracking-tight leading-none text-white">STEMPELSYSTEM</span>
        <span class="text-[11px] text-blue-400 font-medium mt-1 tracking-wide uppercase">V. 0.1</span>
      </div>
    </div>
    
    <nav class="flex-1 px-4 py-4 space-y-1 overflow-y-auto custom-scrollbar">
      <!-- ... Rest deines Navigations-Codes bleibt absolut identisch ... -->
      <template v-if="isSupervisor">
        <button 
          v-for="item in adminNav" 
          :key="item.id"
          @click="emit('update:currentTab', item.id)"
          :class="[
            'w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200',
            currentTab === item.id 
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/40' 
              : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5" />
          <span class="text-sm font-medium">{{ item.name }}</span>
        </button>
      </template>

      <template v-if="!isSupervisor">
        <button 
          v-for="item in employeeNav" 
          :key="item.id"
          @click="emit('update:currentTab', item.id)"
          :class="[
            'w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200',
            currentTab === item.id 
              ? 'bg-slate-800 text-white' 
              : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5" />
          <span class="text-sm font-medium">{{ item.name }}</span>
        </button>
      </template>
    </nav>
  </aside>
</template>