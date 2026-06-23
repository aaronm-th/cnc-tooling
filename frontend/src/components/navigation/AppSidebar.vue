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
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard }, // Nutzt die ID des normalen Dashboards oder 'admin-dashboard', falls nötig
  { id: 'admin-team', name: 'Mitarbeiterübersicht', icon: Users },
  { id: 'admin-requests', name: 'Anfragen verwalten', icon: ClipboardCheck },
  { id: 'admin-calendar', name: 'Teamkalender', icon: Calendar },
]
</script>

<template>
  <aside class="w-64 bg-slate-900 text-white flex flex-col">
    <div class="p-6 flex items-center gap-3">
      <div class="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
        <LayoutDashboard class="w-5 h-5 text-white" />
      </div>
      <span class="font-bold text-xl tracking-tight">CorpConnect</span>
    </div>
    
    <nav class="flex-1 px-4 py-4 space-y-1 overflow-y-auto custom-scrollbar">
      
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

      <template v-else>
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