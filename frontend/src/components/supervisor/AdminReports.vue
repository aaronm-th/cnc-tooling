<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useDocumentStore } from '@/stores/documentStore'
import { storeToRefs } from 'pinia'
import { 
  FileText, 
  Search, 
  Download, 
  Calendar, 
  AlertCircle,
  DownloadIcon
} from 'lucide-vue-next'

const documentStore = useDocumentStore()
const { adminReportsOverview, isAdminFetching, isGenerating } = storeToRefs(documentStore)

const searchQuery = ref('')
const selectedMonth = ref(new Date().getMonth() + 1)
const selectedYear = ref(new Date().getFullYear())

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

const handleDownloadPDF = async (member) => {
  try {
    await documentStore.downloadAdminEmployeeReport(member.id, selectedMonth.value, selectedYear.value)
  } catch (error) {
    alert(`Fehler beim Generieren des Zeitnachweises für ${member.name}`)
  }
}


</script>

<template>
  <div class="flex-1 overflow-y-auto p-8 bg-slate-50">
    <div class="max-w-5xl mx-auto space-y-6">
      
      <!-- Header Area -->
      <section class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <div class="p-2 bg-blue-50 text-blue-600 rounded-xl">
              <FileText class="w-6 h-6" />
            </div>
            Zeitnachweise
          </h1>
          <p class="text-slate-500 mt-1 text-sm">
            Monatliche Arbeitszeitnachweise einsehen und als PDF exportieren.
          </p>
        </div>
        
      </section>

      <!-- Filter Bar -->
      <section class="bg-white p-3 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div class="flex items-center gap-2 w-full sm:w-auto">
          <!-- Monat -->
          <div class="relative w-full sm:w-40">
            <Calendar class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <select 
              v-model="selectedMonth"
              :disabled="isAdminFetching"
              class="w-full pl-9 pr-8 py-2 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:border-blue-500 transition-colors cursor-pointer appearance-none disabled:opacity-50"
            >
              <option v-for="m in months" :key="m.value" :value="m.value">{{ m.name }}</option>
            </select>
            <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none border-l border-t border-slate-400 w-1.5 h-1.5 rotate-135"></div>
          </div>

          <!-- Jahr -->
          <div class="relative w-24 shrink-0">
            <select 
              v-model="selectedYear"
              :disabled="isAdminFetching"
              class="w-full pl-3 pr-8 py-2 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:border-blue-500 transition-colors cursor-pointer appearance-none disabled:opacity-50"
            >
              <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
            </select>
            <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none border-l border-t border-slate-400 w-1.5 h-1.5 rotate-135"></div>
          </div>
        </div>

        <!-- Suche -->
        <div class="relative w-full sm:w-64">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="Mitarbeiter suchen..."
            class="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-medium focus:outline-none focus:border-blue-500 placeholder:text-slate-400 transition-colors"
          />
        </div>
      </section>

      <!-- Loading State -->
      <div v-if="isAdminFetching" class="flex flex-col items-center justify-center p-16 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
        <div class="animate-spin inline-block w-6 h-6 border-3 border-blue-600 border-t-transparent rounded-full"></div>
        <p class="text-slate-500 font-medium text-xs">Lade Übersicht...</p>
      </div>

      <!-- Main Content Table -->
      <div v-else class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200">
                <th class="px-6 py-3.5 text-xs font-bold text-slate-400 uppercase tracking-wider w-1/3">Mitarbeiter</th>
                <th class="px-6 py-3.5 text-xs font-bold text-slate-400 uppercase tracking-wider w-1/3">Arbeitszeitkonto (Monat)</th>
                <th class="px-6 py-3.5 text-xs font-bold text-slate-400 uppercase tracking-wider text-right w-1/3">Aktion</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr 
                v-for="member in filteredMembers" 
                :key="member.id"
                class="hover:bg-slate-50/40 transition-colors group"
              >
                <!-- User Info -->
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

                <!-- Hours Stats -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-semibold text-slate-800">
                    {{ member.ist_hours?.toFixed(2) }} <span class="text-slate-400 font-normal">von</span> {{ member.soll_hours?.toFixed(2) }} Std.
                  </div>
                  <div 
                    :class="[
                      'text-xs font-bold mt-0.5 inline-flex items-center',
                      member.diff_hours >= 0 ? 'text-emerald-600' : 'text-rose-500'
                    ]"
                  >
                    <span>{{ member.diff_hours >= 0 ? '▲ +' : '▼ ' }}{{ member.diff_hours?.toFixed(2) }} Std.</span>
                  </div>
                </td>

                <!-- Large PDF Action Button -->
                <td class="px-6 py-4 whitespace-nowrap text-right">
                  <div class="flex items-center justify-end">
                    <button 
                      @click="handleDownloadPDF(member)"
                      :disabled="isGenerating"
                      class="inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-50 hover:bg-blue-600 text-blue-600 hover:text-white disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed rounded-lg border border-blue-100 hover:border-blue-600 font-semibold text-xs transition-all duration-150 cursor-pointer shadow-sm shadow-blue-50/50"
                    >
                      <template v-if="isGenerating">
                        <span class="animate-spin inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full"></span>
                        <span>Generiere...</span>
                      </template>
                      <template v-else>
                        <DownloadIcon class="w-3.5 h-3.5" />
                        <span>Zeitnachweis herunterladen</span>
                      </template>
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Empty State Inside Table -->
              <tr v-if="filteredMembers.length === 0">
                <td colspan="3" class="px-6 py-14 text-center text-sm text-slate-400 font-medium">
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