<script setup>
import { 
  LayoutDashboard, Users, Calendar, FileText, 
  ShieldCheck, ClipboardCheck, BarChart3, 
  BookUser, Send 
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/authStore' 
import { storeToRefs } from 'pinia'

defineProps({
  currentTab: { type: String, required: true },
  isAdminView: { type: Boolean, default: true }
})

const emit = defineEmits(['update:currentTab', 'update:isAdminView'])

const authStore = useAuthStore()
const { isSupervisor } = storeToRefs(authStore)

// Navigation Definitionen für einfachere Wartung
const mainNav = [
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard },
  { id: 'team', name: 'Kontakte', icon: BookUser },
  { id: 'schedule', name: 'Kalender', icon: Calendar },
  { id: 'requests', name: 'Meine Anträge', icon: Send },
  { id: 'documents', name: 'Dokumente', icon: FileText },
]

const adminNav = [
  { id: 'admin-dashboard', name: 'Admin Übersicht', icon: BarChart3 },
  { id: 'admin-team', name: 'Mitarbeiterübersicht', icon: Users },
  { id: 'admin-requests', name: 'Anfragen verwalten', icon: ClipboardCheck },
  
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
      <button 
        v-for="item in mainNav" 
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


      <template v-if="isAdminView && isSupervisor">
        <div class="pt-6 pb-2 px-3">
          <p class="text-[10px] font-bold uppercase tracking-widest text-slate-500">Vorgesetzten-Funktionen</p>
        </div>
        
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
        <button 
          :class="[
            'w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
            currentTab === 'admin-calendar' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' : 'text-slate-400 hover:bg-slate-800 hover:text-white'
          ]"
          @click="emit('update:currentTab', 'admin-calendar')"
        >
          <Calendar class="w-5 h-5" />
          <span>Teamkalender</span>
        </button>
      </template>
    </nav>

    <div v-if="isSupervisor" class="p-4 border-t border-slate-800 bg-slate-900/50">
      <div class="flex items-center justify-between px-3 py-2.5 bg-slate-800/40 rounded-xl border border-slate-700/50 transition-all hover:border-slate-600">
        <div class="flex items-center gap-3">
          <ShieldCheck :class="['w-4 h-4 transition-colors', isAdminView ? 'text-blue-400' : 'text-slate-500']" />
          <span class="text-[11px] font-bold text-slate-300 uppercase tracking-tight">Supervisor Mode</span>
        </div>
        <button 
          @click="emit('update:isAdminView', !isAdminView)"
          class="relative inline-flex h-5 w-9 items-center rounded-full transition-all duration-300 focus:outline-none"
          :class="isAdminView ? 'bg-blue-600' : 'bg-slate-700'"
        >
          <span
            class="inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform duration-300"
            :class="isAdminView ? 'translate-x-5' : 'translate-x-0.5'" >
          </span>
        </button>
      </div>
    </div>
  </aside>
</template>