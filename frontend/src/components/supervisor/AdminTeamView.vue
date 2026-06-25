<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { storeToRefs } from 'pinia'
import { 
  MoreVertical, 
  AlertCircle,
  FileEdit,
  UserX,
  Search,
  UserPlus,
  UploadCloud
} from 'lucide-vue-next'
import AddEditEmployees from './modals/AddEditEmployees.vue'
import UploadDocumentModal from './modals/UploadDocumentModal.vue'
import ConfirmDeactivateModal from './modals/ConfirmDeactivateModal.vue'

import { useDateFormatter } from '@/composables/useDateFormatter'

const adminStore = useAdminStore()
const { teamMembers } = storeToRefs(adminStore)
const { formatDate } = useDateFormatter()

const searchQuery = ref('')
const isModalOpen = ref(false)
const isUploadModalOpen = ref(false)

const selectedMember = ref(null)
const selectedMemberForUpload = ref(null)

const isFutureEmployee = (joinedAt) => {
  if (!joinedAt) return false
  const joinDate = new Date(joinedAt)
  joinDate.setHours(0, 0, 0, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0) 
  return joinDate > today
}


const openUploadModal = (member) => {
  selectedMemberForUpload.value = member
  isUploadModalOpen.value = true
}

const handleUploadSuccess = async () => {
  // Optionale Optimierung: Lade die Mitarbeiterdaten neu, 
  // falls im UI direkt die Anzahl hochgeladener Dokumente o.ä. angezeigt werden soll
  try {
    await adminStore.fetchTeamMembers()
  } catch (error) {
    console.error("Fehler beim Aktualisieren der Daten nach Upload:", error)
  }
}

const getOvertimeClass = (hours) => {
  if (hours > 20) return 'bg-red-100 text-red-700'
  if (hours > 0) return 'bg-amber-100 text-amber-700'
  return 'bg-emerald-100 text-emerald-700'
}

// Filtered team members based on search bar
const filteredMembers = computed(() => {
  // Sicherstellen, dass wir immer ein Array haben
  const members = adminStore.teamMembers || []
  
  if (!searchQuery.value) return members
  
  const query = searchQuery.value.toLowerCase()
  return members.filter(member => 
    member.name?.toLowerCase().includes(query) || 
    member.username?.toLowerCase().includes(query) ||
    member.role?.toLowerCase().includes(query)
  )
})

onMounted(async () => {
  try {
    await adminStore.fetchTeamMembers()
  } catch (error) {
    console.error("Fehler beim Laden der Mitarbeiter-Stammdaten:", error)
  }
})

const openAddModal = () => {
  selectedMember.value = null
  isModalOpen.value = true
}

const openEditModal = (member) => {
  selectedMember.value = member
  isModalOpen.value = true
}


// 2. Erstelle zwei neue reaktive Variablen
const isConfirmModalOpen = ref(false)
const selectedMemberForDeactivation = ref(null)

// 3. Funktion zum Öffnen des Modals
const openConfirmModal = (member) => {
  selectedMemberForDeactivation.value = member
  isConfirmModalOpen.value = true
}

// 4. Funktion zum finalen Ausführen über den Store
const handleDeactivateConfirm = async () => {
  if (!selectedMemberForDeactivation.value) return
  
  try {
    await adminStore.deactivateUser(selectedMemberForDeactivation.value.id)
    isConfirmModalOpen.value = false
    selectedMemberForDeactivation.value = null
  } catch (error) {
    console.error("Fehler beim Deaktivieren:", error)
  }
}

</script>


<template>
  <div class="flex-1 overflow-y-auto bg-slate-50 p-8">
    
    <div class="max-w-7xl mx-auto space-y-8">
      
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold text-slate-900">Mitarbeiter-Verwaltung</h1>
          <p class="text-slate-500 mt-1">Stammdaten, Arbeitszeiten und Urlaubsansprüche bearbeiten.</p>
        </div>
        
        <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div class="relative min-w-[260px]">
            <Search class="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input 
              v-model="searchQuery"
              type="text" 
              placeholder="Mitarbeiter suchen..." 
              class="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800"
            />
          </div>

          <button 
            @click="openAddModal"
            class="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-bold hover:bg-blue-700 transition-all shadow-lg shadow-blue-900/20 cursor-pointer"
          >
            <UserPlus class="w-4 h-4" />
            Mitarbeiter anlegen
          </button>
        </div>
      </section>

      <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/50 border-b border-slate-100">
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500">Mitarbeiter</th>
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 text-center">Wochenstunden</th>
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 text-center">Überstunden</th>
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 text-center">Urlaub</th>
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 text-center">Status</th>
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 text-center">Aktionen</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr 
                v-for="member in filteredMembers" 
                :key="member.id" 
                :class="[
                  'hover:bg-slate-50/50 transition-colors group',
                  isFutureEmployee(member.joined_at) ? 'bg-slate-50/40 opacity-75' : ''
                ]"
              >
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div v-if="member.avatar" class="w-10 h-10 rounded-full overflow-hidden border border-slate-200 shrink-0">
                      <img :src="member.avatar" class="w-full h-full object-cover" />
                    </div>
                    <div v-else class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold shrink-0">
                      {{ member.initials }}
                    </div>
                    <div>
                      <div class="font-bold text-slate-900 leading-tight">{{ member.name }}</div>
                      <div class="text-[11px] text-slate-500">{{ member.username }}</div>
                    </div>
                  </div>
                </td>

                <td class="px-6 py-4 text-center">
                  <span class="text-sm font-medium text-slate-700">{{ member.weekly_hours || '40.0' }} h</span>
                </td>

                <td class="px-6 py-4 text-center">
                  <span :class="['px-2.5 py-1 rounded-lg text-xs font-bold', getOvertimeClass(member.overtime_hours)]">
                    {{ member.overtime_hours > 0 ? '+' : '' }}{{ member.overtime_hours || '0' }} h
                  </span>
                </td>

                <td class="px-6 py-4 text-center">
                  <div class="flex flex-col items-center">
                    <span class="text-sm font-bold text-slate-800">
                      {{ member.vacation_used }} / {{ member.vacation_total }}
                    </span>
                    <span class="text-[9px] text-slate-400 uppercase font-bold tracking-tighter">Tage verbraucht</span>
                  </div>
                </td>

                <td class="px-6 py-4">
                  <div class="flex items-start gap-2">
                    <span :class="[
                      'w-2 h-2 rounded-full mt-1.5 shrink-0',
                      isFutureEmployee(member.joined_at) 
                        ? 'bg-amber-400' 
                        : (member.status_text === 'Anwesend' ? 'bg-emerald-500' : 'bg-slate-300')
                    ]"></span>
                    
                    <div class="flex flex-col items-start leading-none">
                      <span class="text-sm text-slate-700">
                        {{ isFutureEmployee(member.joined_at) ? 'Noch nicht aktiv' : member.status_text }}
                      </span>
                      <div v-if="isFutureEmployee(member.joined_at)" class="text-[10px] text-amber-600 font-medium mt-1">
                        Startet am {{ formatDate(member.joined_at) }}
                      </div>
                    </div>
                  </div>
                </td>

                <td class="px-6 py-4 text-right">
                  <div class="flex justify-end gap-1">
                    <button 
                      @click="openUploadModal(member)" 
                      title="Dokument hochladen" 
                      class="p-2 hover:bg-emerald-50 text-slate-400 hover:text-emerald-600 rounded-lg transition-colors cursor-pointer"
                    >
                      <UploadCloud class="w-4 h-4" />
                    </button>

                    <button 
                      @click="openEditModal(member)" 
                      title="Bearbeiten" 
                      class="p-2 hover:bg-blue-50 text-slate-400 hover:text-blue-600 rounded-lg transition-colors cursor-pointer"
                    >
                      <FileEdit class="w-4 h-4" />
                    </button>
                    
                    <button 
                      @click="openConfirmModal(member)"
                      title="Inaktiv setzen" 
                      class="p-2 hover:bg-red-50 text-slate-400 hover:text-red-600 rounded-lg transition-colors cursor-pointer" 
                    >
                      <UserX class="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
              
              <tr v-if="filteredMembers.length === 0">
                <td colspan="6" class="px-6 py-10 text-center text-sm text-slate-400">
                  Keine Mitarbeiter gefunden, die den Kriterien entsprechen.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </div>

    <AddEditEmployees
      :is-open="isModalOpen"
      :member="selectedMember"
      @close="isModalOpen = false"
    />

    <UploadDocumentModal
      :is-open="isUploadModalOpen"
      :member="selectedMemberForUpload"
      @close="isUploadModalOpen = false"
      @success="handleUploadSuccess"
    />

    <ConfirmDeactivateModal
      :is-open="isConfirmModalOpen"
      :member="selectedMemberForDeactivation"
      @close="isConfirmModalOpen = false"
      @confirm="handleDeactivateConfirm"
    />

  </div>
</template>