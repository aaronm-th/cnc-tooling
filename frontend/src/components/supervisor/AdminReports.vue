<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useDocumentStore } from '@/stores/documentStore'
import { useAdminStore } from '@/stores/adminStore' // Neu importiert für die Sperr-Logik
import { storeToRefs } from 'pinia'
import { 
  FileText, 
  Search, 
  Calendar, 
  AlertCircle,
  DownloadIcon,
  Lock,
  Unlock,
  CheckCircle2,
  AlertTriangle
} from 'lucide-vue-next'

const documentStore = useDocumentStore()
const adminStore = useAdminStore() // Instanziiert

const { adminReportsOverview, isAdminFetching, isGenerating } = storeToRefs(documentStore)

const searchQuery = ref('')
const selectedMonth = ref(new Date().getMonth() + 1)
const selectedYear = ref(new Date().getFullYear())
const isProcessingAction = ref(false) // Lokaler Lade-State für Lock/Unlock

const months = [
  { value: 1, name: 'Januar' },
  { value: 2, name: 'Februar' },
  { value: 3, name: 'März' },
  { value: 4, name: 'April' },
  { value: 5, name: 'Mai' },
  { value: 6, name: 'Juni' },
  { value: 7, name: 'Juli' },
  { value: 8, name: 'August' },
  { value: 9, name: 'September' },
  { value: 10, name: 'Oktober' },
  { value: 11, name: 'November' },
  { value: 12, name: 'Dezember' }
]

const currentYear = new Date().getFullYear()
const years = [currentYear - 1, currentYear, currentYear + 1]

// Lädt die Übersicht (wird getriggert bei Mount & Filter-Wechsel)
const loadReportOverview = async () => {
  await documentStore.fetchAdminReportsOverview(selectedMonth.value, selectedYear.value)
}

onMounted(async () => {
  await loadReportOverview()
})

watch([selectedMonth, selectedYear], async () => {
  await loadReportOverview()
})

const filteredMembers = computed(() => {
  const members = adminReportsOverview.value || []
  return members.filter(member => {
    const name = (member.name || '').toLowerCase()
    return name.includes(searchQuery.value.toLowerCase())
  })
})

// PDF Zeitnachweis herunterladen
const handleDownloadPDF = async (member) => {
  const newTab = window.open('', '_blank')
  if (newTab) {
    newTab.document.write('Zeitnachweis wird erstellt …')
  }
  try {
    await documentStore.downloadAdminEmployeeReport(member.id, selectedMonth.value, selectedYear.value, newTab)
  } catch (error) {
    if (newTab) newTab.close()
    alert(`Fehler beim Generieren des Zeitnachweises für ${member.name}`)
  }
}


// EINZELNEN MITARBEITER ABRECHNEN ODER WIEDER ÖFFNEN
const handleToggleEmployeeLock = async (member) => {
  isProcessingAction.value = true
  try {
    if (member.is_processed) {
      // Wenn bereits abgerechnet: Wieder öffnen (Admin-Override)
      const confirmed = confirm(`Achtung: Du öffnest den Monat für ${member.name} erneut. Bereits exportierte Payout-Daten werden zurückgesetzt. Fortfahren?`)
      if (!confirmed) return
      
      await adminStore.reopenEmployeeMonth(member.id, selectedMonth.value, selectedYear.value)
      alert(`Monat für ${member.name} wieder geöffnet.`)
    } else {
      // Wenn offen: Abrechnen & Fixieren
      await adminStore.closeEmployeeMonth(member.id, selectedMonth.value, selectedYear.value)
      alert(`Monat für ${member.name} erfolgreich abgerechnet.`)
    }
    await loadReportOverview()
  } catch (error) {
    alert('Fehler beim Ändern des Abrechnungsstatus.')
  } finally {
    isProcessingAction.value = false
  }
}
</script>

<template>
  <div class="flex-1 overflow-y-auto bg-slate-50 p-8">
    <div class="max-w-7xl mx-auto space-y-8">
      
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="p-2.5 bg-blue-50 text-blue-600 rounded-xl shrink-0">
            <FileText class="w-6 h-6" />
          </div>
          <div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Zeitnachweise & Monatsabschluss</h1>
            <p class="text-slate-500 text-sm mt-0.5">
              Monatliche Arbeitszeitnachweise einsehen, verriegeln und für die Auszahlung freigeben.
            </p>
          </div>
        </div>
      </section>
      
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-3 rounded-2xl border border-slate-200 shadow-sm mt-4">
        <div class="relative w-full sm:w-64">
          <Search class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="Mitarbeiter suchen..."
            class="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 placeholder:text-slate-400 transition-all shadow-sm text-slate-800"
          />
        </div>

        <div class="flex items-center gap-2 w-full sm:w-auto justify-end">
          <div class="relative w-full sm:w-40">
            <Calendar class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <select 
              v-model="selectedMonth"
              :disabled="isAdminFetching || isProcessingAction"
              class="w-full pl-10 pr-8 py-2 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-xl text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer appearance-none disabled:opacity-50"
            >
              <option v-for="m in months" :key="m.value" :value="m.value">{{ m.name }}</option>
            </select>
          </div>

          <div class="relative w-24 shrink-0">
            <select 
              v-model="selectedYear"
              :disabled="isAdminFetching || isProcessingAction"
              class="w-full pl-3 pr-8 py-2 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-xl text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer appearance-none disabled:opacity-50"
            >
              <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
        </div>
      </div>

      <div v-if="isAdminFetching" class="flex flex-col items-center justify-center p-16 bg-white rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <div class="animate-spin inline-block w-6 h-6 border-3 border-blue-600 border-t-transparent rounded-full"></div>
        <p class="text-slate-500 font-medium text-xs">Lade Übersicht...</p>
      </div>

      <div v-else class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/50 border-b border-slate-100">
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 w-1/4">Mitarbeiter</th>
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 w-1/4">Arbeitszeitkonto (Monat)</th>
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 w-1/4">Status</th>
                <th class="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 text-right w-1/4">Aktionen</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr 
                v-for="member in filteredMembers" 
                :key="member.id"
                class="hover:bg-slate-50/40 transition-colors group"
              >
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    <div v-if="member.avatar" class="w-9 h-9 rounded-full overflow-hidden border border-slate-200 shrink-0">
                      <img :src="member.avatar" class="w-full h-full object-cover" />
                    </div>
                    <div v-else class="w-9 h-9 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-bold shrink-0">
                      {{ member.initials || 'MA' }}
                    </div>
                    <div>
                      <div class="font-semibold text-slate-900 text-sm group-hover:text-blue-600 transition-colors">{{ member.name }}</div>
                      <div class="text-xs text-slate-400 font-medium">@{{ member.username || 'mitarbeiter' }}</div>
                    </div>
                  </div>
                </td>

                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-semibold text-slate-800">
                    {{ member.ist_hours?.toFixed(2) }} <span class="text-slate-400 font-normal">von</span> {{ member.soll_hours?.toFixed(2) }} Std.
                  </div>
                  <div 
                    :class="[
                      'text-xs font-bold mt-0.5 inline-flex items-center',
                      (member.ist_hours - member.soll_hours) >= 0 ? 'text-emerald-600' : 'text-rose-500'
                    ]"
                  >
                    <span>
                      {{ (member.ist_hours - member.soll_hours) >= 0 ? '▲ +' : '▼ ' }}
                      {{ (member.ist_hours - member.soll_hours)?.toFixed(2) }} Std.
                    </span>
                  </div>
                </td>

                <td class="px-6 py-4 whitespace-nowrap">
                  <span 
                    v-if="member.is_processed" 
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg"
                  >
                    <CheckCircle2 class="w-3.5 h-3.5 text-emerald-600" />
                    Abgerechnet & Fixiert
                  </span>
                  <span 
                    v-else 
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 rounded-lg"
                  >
                    <AlertTriangle class="w-3.5 h-3.5 text-amber-500" />
                    Offen
                  </span>
                </td>

                <td class="px-6 py-4 whitespace-nowrap text-right">
                  <div class="flex items-center justify-end gap-2">
                    
                    <button 
                      @click="handleToggleEmployeeLock(member)"
                      :disabled="isProcessingAction"
                      :class="[
                        'inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg font-medium text-xs border transition-all cursor-pointer',
                        member.is_processed 
                          ? 'bg-rose-50 border-rose-200 text-rose-600 hover:bg-rose-600 hover:text-white' 
                          : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                      ]"
                    >
                      <template v-if="member.is_processed">
                        <Unlock class="w-3 h-3" />
                        <span>Öffnen</span>
                      </template>
                      <template v-else>
                        <Lock class="w-3 h-3" />
                        <span>Abschließen</span>
                      </template>
                    </button>

                    <button 
                      @click="handleDownloadPDF(member)"
                      :disabled="isGenerating"
                      class="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-blue-50 hover:bg-blue-600 text-blue-600 hover:text-white disabled:bg-slate-100 disabled:text-slate-400 rounded-lg border border-blue-100 hover:border-blue-600 font-semibold text-xs transition-all cursor-pointer"
                    >
                      <DownloadIcon class="w-3 h-3" />
                      <span>PDF</span>
                    </button>
                    
                  </div>
                </td>
              </tr>

              <tr v-if="filteredMembers.length === 0">
                <td colspan="4" class="px-6 py-14 text-center text-sm text-slate-400 font-medium">
                  <AlertCircle class="w-7 h-7 text-slate-300 mx-auto mb-2" />
                  Keine Einträge für die aktuelle Auswahl vorhanden.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </div>
</template>