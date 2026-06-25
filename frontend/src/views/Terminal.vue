<script setup>
import { ref, computed, onMounted} from 'vue'
import { Search, Clock, LogIn, LogOut, User, ArrowLeft, CheckCircle } from 'lucide-vue-next'
import Swal from 'sweetalert2'
import { useClock } from '../composables/useClock'
import { useTerminalStore } from '@/stores/terminalStore' // Dein neuer Store
import { useAuthStore } from '@/stores/authStore' // Falls du Teammitglieder von dort lädst
import { storeToRefs } from 'pinia'

// Stores initialisieren
const terminalStore = useTerminalStore()
const { teamMembers } = storeToRefs(terminalStore) // Wir nutzen die zentrale Member-Liste
const { formattedTime, formattedDate } = useClock()

const lockedIds = ref(new Set())
const searchQuery = ref('')

const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'

onMounted(async () => {
  // Teammitglieder laden (falls noch nicht geschehen)
  if (teamMembers.value.length === 0) {
    await terminalStore.fetchTerminalUsers()
  }
})

const toggleStatus = async (teamMember) => {
  if (lockedIds.value.has(teamMember.id)) return;

  try {
    const result = await terminalStore.toggleEmployeeStempeln(teamMember.id);
    
    // FALL 1: Timer-Warnung (Backend 200 mit status: 'warning')
    if (result.status === 'warning') {
      Swal.fire({
        title: 'Bitte warten',
        text: result.message + ` (Noch ${result.remaining_seconds}s)`,
        icon: 'warning',
        toast: true,
        position: 'top-end',
        timer: 3000
      });
      return;
    }

    // FALL 2: Erfolg (Backend 200)
    Swal.fire({
        title: result.message,
        icon: 'success',
        toast: true,
        position: 'top-end',
        timer: 3000,
        showConfirmButton: false
    });

    // Lokaler UI-Lock
    lockedIds.value.add(teamMember.id);
    setTimeout(() => { lockedIds.value.delete(teamMember.id); }, 4000);

  } catch (error) {
    // FALL 3: Fehler (Backend 403, z.B. Urlaub/Krank)
    Swal.fire('Hinweis', error.message, 'info');
  }
};

const filteredEmployees = computed(() => {
  if (!searchQuery.value) return teamMembers.value
  const query = searchQuery.value.toLowerCase()
  return teamMembers.value.filter(e => e.name.toLowerCase().includes(query))
})
</script>



<template>
  <div class="min-h-screen bg-slate-50 flex flex-col">
    <!-- Header -->
    <header class="bg-slate-900 text-white p-6 shadow-lg">

<div class="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-6 relative z-10">
        
        <div class="flex items-center gap-4">
          <router-link to="/login" class="p-2.5 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/40 rounded-xl transition-all text-slate-400 hover:text-white group">
            <ArrowLeft class="w-5 h-5 group-hover:-translate-x-0.5 transition-transform" />
          </router-link>
          
          <div class="w-20 h-20 flex items-center justify-center overflow-hidden">
            <img 
              :src="`${backendUrl}/media/logos/jv_logo.png`" 
              alt="Logo"
              class="w-full h-full object-contain"
            />
          </div>

          <div>
            <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Terminal
            </h1>
            <p class="text-slate-400 text-xs mt-0.5 font-medium tracking-wide uppercase">Zeiterfassung</p>
          </div>
        </div>

        <div class="px-5 py-3 rounded-2xl flex flex-col items-end min-w-[160px]">
          <p class="text-3xl font-mono font-black text-blue-400 tracking-wider leading-none">{{ formattedTime }}</p>
          <p class="text-slate-400 text-[14px] font-semibold uppercase tracking-wider mt-1.5">{{ formattedDate }}</p>
        </div>
      </div>

    </header>

    <!-- Main Content -->
    <main class="flex-1 p-8 max-w-7xl mx-auto w-full">
      <div class="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="relative w-full md:w-96">
          <Search class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="Suche..." 
            spellcheck="false"
            autocomplete="off"
            class="w-full pl-12 pr-4 py-3 bg-white border border-slate-200 rounded-2xl text-lg shadow-sm focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
          />
        </div>

      </div>

      <!-- Employee Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <button v-for="teamMember in filteredEmployees" 
            :key="teamMember.id"
            @click="toggleStatus(teamMember)"
            :class="[
                'group relative p-6 bg-white rounded-3xl border-2 transition-all text-left flex flex-col gap-4',
                teamMember.status === 'Anwesend' ? 'border-emerald-100 bg-emerald-50/10' : 'border-slate-100',
                lockedIds.has(teamMember.id) ? 'opacity-70 cursor-wait' : 'hover:shadow-xl hover:-translate-y-1 active:scale-95'
            ]"
        >
          <div class="flex items-start justify-between">
            <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-500 transition-colors">
              <span v-if="!teamMember.avatar" class="text-xl font-bold tracking-wider uppercase select-none">
                {{ teamMember.initials }}
              </span>             
              <img v-else :src="teamMember.avatar" class="w-full h-full object-cover rounded-2xl" />
            </div>
            <div 
              :class="[
                'px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider',
                teamMember.status === 'Anwesend' 
                  ? 'bg-emerald-100 text-emerald-700' 
                  : 'bg-slate-100 text-slate-500'
              ]"
            >
              {{ teamMember.status }}
            </div>
          </div>

          <div>
            <h3 class="font-bold text-slate-900 text-lg leading-tight">{{ teamMember.name }}</h3>
            <p class="text-slate-500 text-sm mt-1">{{ teamMember.role || 'Mitarbeiter' }}</p>
          </div>

          <div class="mt-auto pt-4 border-t border-slate-50 flex items-center justify-between gap-1">
            <span class="text-xs font-bold uppercase tracking-widest text-slate-400">{{ teamMember.status === 'Anwesend' ? 'Ausstempeln' : 'Einstempeln' }}</span>
            <div 
              :class="[
                'p-2 rounded-xl transition-colors',
                teamMember.status === 'Anwesend' 
                  ? 'bg-red-50 text-red-600' 
                  : 'bg-emerald-50 text-emerald-600'
              ]"
            >
              <LogOut v-if="teamMember.status === 'Anwesend'" class="w-5 h-5" />
              <LogIn v-else class="w-5 h-5" />
            </div>
          </div>

          <div v-if="lockedIds.has(teamMember.id)" class="absolute inset-0 bg-white/40 backdrop-blur-sm rounded-3xl flex items-center justify-center z-10 transition-all">
              <div class="bg-slate-900 text-white text-xs font-bold px-4 py-2 rounded-xl shadow-xl flex items-center gap-2">
                  <CheckCircle class="w-4 h-4 text-emerald-400" />
                  Vorgang erfasst
              </div>
          </div>

        </button>
      </div>

      <!-- Empty State -->
      <div v-if="filteredEmployees.length === 0" class="text-center py-20">
        <div class="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-300">
          <User class="w-10 h-10" />
        </div>
        <h2 class="text-xl font-bold text-slate-900">Keine Mitarbeiter gefunden</h2>
      </div>
    </main>

  </div>
</template>

<style scoped>
.tracking-tight {
  letter-spacing: -0.025em;
}
</style>
