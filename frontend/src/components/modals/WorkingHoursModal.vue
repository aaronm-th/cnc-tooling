<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { X, Calendar, Download, CheckCircle2, Loader2, ChevronRight, FileText } from 'lucide-vue-next'
import { useScheduleStore } from '@/stores/scheduleStore'
import { useAuthStore } from '@/stores/authStore'
import { useDocumentStore } from '@/stores/documentStore'
import { useDateFormatter } from '@/composables/useDateFormatter' // Pfad ggf. anpassen
import { useEventStyles } from '@/composables/useEventStyles'

const props = defineProps({ 
  isOpen: { type: Boolean, required: true }
})

const { formatDate } = useDateFormatter()
const { getBadgeColorClass } = useEventStyles()

const emit = defineEmits(['close'])

const docStore = useDocumentStore()
const scheduleStore = useScheduleStore()
const authStore = useAuthStore()

const selectedMonth = ref(new Date().getMonth())
const selectedYear = ref(new Date().getFullYear())
const isFinished = ref(false)


const showPreview = ref(false)
const isGenerating = ref(false)
const previewEvents = ref([])
const isPreviewLoading = ref(false)

const availableMonths = computed(() => {
  const allMonths = [
    { value: 0, name: 'Januar' }, { value: 1, name: 'Februar' },
    { value: 2, name: 'März' }, { value: 3, name: 'April' },
    { value: 4, name: 'Mai' }, { value: 5, name: 'Juni' },
    { value: 6, name: 'Juli' }, { value: 7, name: 'August' },
    { value: 8, name: 'September' }, { value: 9, name: 'Oktober' },
    { value: 10, name: 'November' }, { value: 11, name: 'Dezember' }
  ]

  const rawJoined = authStore.userStats?.joined_at || authStore.user?.joined_at
  if (!rawJoined) return allMonths

  // Logik für Datumsparser
  const parts = rawJoined.split('.')
  let joinedYear, joinedMonth

  if (parts.length === 3) {
    joinedYear = parseInt(parts[2], 10)
    joinedMonth = parseInt(parts[1], 10) - 1
  } else {
    const isoParts = rawJoined.split('-')
    joinedYear = parseInt(isoParts[0], 10)
    joinedMonth = parseInt(isoParts[1], 10) - 1
  }

  const now = new Date()
  const currentYear = now.getFullYear()
  const currentMonth = now.getMonth()
  const selYear = Number(selectedYear.value)

  return allMonths.filter(month => {
    if (selYear === joinedYear && month.value < joinedMonth) return false
    if (selYear < joinedYear) return false
    if (selYear === currentYear && month.value > currentMonth) return false
    if (selYear > currentYear) return false
    return true
  })
}) // <--- Diese Klammer hat gefehlt!

const years = computed(() => {
  const currentYear = new Date().getFullYear()
  let startYear = 2024
  
  const rawJoined = authStore.userStats?.joined_at || authStore.user?.joined_at
  if (rawJoined) {
    const parts = rawJoined.split('.')
    startYear = parts.length === 3 ? parseInt(parts[2], 10) : new Date(rawJoined).getFullYear()
  }

  const yearsArray = []
  for (let y = startYear; y <= currentYear; y++) {
    yearsArray.push(y)
  }
  return yearsArray
})

onMounted(async () => {
  if (!authStore.userStats) {
    try {
      await authStore.fetchUserStats()
    } catch (err) {
      console.error("Eintrittsdatum konnte nicht geladen werden", err)
    }
  }
})

const handleDownload = async () => {
  isGenerating.value = true
  try {
    const success = await docStore.downloadWorkReport(selectedMonth.value + 1, selectedYear.value)
    if (success) isFinished.value = true
  } catch (err) {
    alert(docStore.lastError || "Fehler beim Download")
    isFinished.value = false
  } finally {
    isGenerating.value = false
  }
}

const handleClose = () => {
  emit('close')
  setTimeout(() => {
    isFinished.value = false
  }, 300)
}

const fetchPreviewData = async () => {
  if (!showPreview.value) return
  
  isPreviewLoading.value = true
  try {
    // Holt die exakt gleichen Daten, ohne das PDF zu triggern!
    const reportData = await docStore.getReportData(selectedMonth.value + 1, selectedYear.value)
    previewEvents.value = reportData.events || []
  } catch (err) {
    console.error("Fehler beim Laden der Vorschau", err)
    previewEvents.value = []
  } finally {
    isPreviewLoading.value = false
  }
}


watch(selectedYear, () => {
  if (availableMonths.value.length > 0) {
    const stillAvailable = availableMonths.value.some(m => m.value === selectedMonth.value)
    if (!stillAvailable) {
      selectedMonth.value = availableMonths.value[0].value
    }
  }
})

watch([showPreview, selectedMonth, selectedYear], fetchPreviewData)

</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm"
      >
        <div
          class="absolute inset-0"
          @click="handleClose"
        />
        
        <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-300">
          <!-- Success State -->
          <div
            v-if="isFinished"
            class="p-10 text-center space-y-6"
          >
            <div class="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-3xl flex items-center justify-center mx-auto scale-in duration-500">
              <CheckCircle2 class="w-10 h-10" />
            </div>
            <div class="space-y-2">
              <h2 class="text-2xl font-bold text-slate-900">
                Download gestartet
              </h2>
              <p class="text-slate-500">
                Der Stundennachweis für {{ docStore.months[selectedMonth] }} {{ selectedYear }} wird heruntergeladen.
              </p>
            </div>
            <button 
              class="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold hover:bg-slate-800 transition-all shadow-lg"
              @click="handleClose"
            >
              Zurück
            </button>
          </div>

          <!-- Form State -->
          <template v-else>
            <div class="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div class="flex items-center gap-3">
                <div class="p-2 bg-blue-100 rounded-xl">
                  <Calendar class="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h2 class="text-lg font-bold text-slate-900">
                    Zeitnachweise
                  </h2>
                </div>
              </div>
              <button
                class="p-2 text-slate-400 hover:text-slate-600 hover:bg-white rounded-full transition-all"
                @click="handleClose"
              >
                <X class="w-5 h-5" />
              </button>
            </div>
            
            <div class="p-8 space-y-8">
              <div class="flex items-center justify-between">
                <div class="space-y-1">
                  <h3 class="text-xs font-bold uppercase tracking-widest text-slate-400">
                    Einstellungen & Vorschau
                  </h3>
                  <p class="text-sm text-slate-500">
                    Vorschau deiner Arbeitszeiten.
                  </p>
                </div>
                <button 
                  class="text-xs font-bold text-blue-600 hover:text-blue-700 bg-blue-50 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-2"
                  @click="showPreview = !showPreview"
                >
                  <FileText class="w-3.5 h-3.5" />
                  {{ showPreview ? 'Einstellungen' : 'Vorschau' }}
                </button>
              </div>

              <div
                v-if="showPreview"
                class="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500"
              >
                <div class="bg-slate-50 border border-slate-200 rounded-2xl overflow-hidden">
                  <div class="p-3 border-b border-slate-200 bg-white flex items-center justify-between">
                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Live-Daten Vorschau</span>
                    <span class="text-[10px] font-bold text-blue-600 px-2 py-0.5 bg-blue-50 rounded">
                      {{ docStore.months[selectedMonth] }} {{ selectedYear }}
                    </span>
                  </div>
                  
                  <!-- 1. Lade-Zustand -->
                  <div v-if="isPreviewLoading" class="p-8 text-center space-y-2">
                    <Loader2 class="w-6 h-6 animate-spin text-blue-600 mx-auto" />
                    <p class="text-xs text-slate-400 font-medium">Lade Arbeitszeiten...</p>
                  </div>

                  <!-- 2. Keine Daten vorhanden -->
                  <div v-else-if="previewEvents.length === 0" class="p-8 text-center text-xs text-slate-400 italic">
                    Keine Arbeitszeiten für diesen Zeitraum eingetragen.
                  </div>

                  <!-- 3. Daten vorhanden --><!-- 3. Echte Daten-Liste (jetzt mit Unterscheidung für Feiertage, Wochenenden etc.) -->
                  <div v-else class="p-4 max-h-64 overflow-y-auto space-y-2 divide-y divide-slate-100">
                    <div 
                      v-for="(day, idx) in previewEvents" 
                      :key="idx" 
                      class="flex items-center justify-between text-xs pt-2 first:pt-0"
                    >
                      <!-- Linke Seite: Datum & Detail-Name (z.B. "Labor Day") -->
                      <div class="flex flex-col text-left pr-2">
                        <!-- Nutzt die neue Funktion aus dem vorherigen Schritt -->
                        <span class="font-semibold text-slate-700">{{ formatDate(day.date) }}</span>

                      </div>

                      <!-- Rechte Seite: Status-Badge & Stunden -->
                      <div class="flex items-center gap-2 shrink-0">
                        <!-- Typ-Badge (wird nur angezeigt, wenn es kein normaler Arbeitstag ist) -->
                        <span 
                          v-if="day.day_type && day.day_type !== 'workday'"
                          class="px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider scale-95"
                          :class="getBadgeColorClass(day.day_type)"
                        >
                          {{ day.day_type_display }}
                        </span>

                        <!-- Stunden-Anzeige (wird dezent ausgegraut, wenn 0 Std.) -->
                        <span 
                          class="font-bold px-2.5 py-1 rounded-lg min-w-[65px] text-center"
                          :class="Number(day.actual_hours) > 0 ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-100 text-slate-400'"
                        >
                          {{ parseFloat(day.actual_hours).toFixed(2) }} Std.
                        </span>
                      </div>
                    </div>
                  </div>

                </div>
                
                <p class="text-[10px] text-center text-slate-400 italic">
                  Dies ist eine vereinfachte Übersicht deiner erfassten Zeiten vor dem PDF-Export.
                </p>
              </div>

              <div
                v-else
                class="space-y-6 animate-in fade-in slide-in-from-top-4 duration-500"
              >
                <div class="space-y-4">
                  <div class="space-y-2">
                    <label class="text-xs font-bold uppercase tracking-widest text-slate-400 ml-1">Jahr</label>
                    <div class="grid grid-cols-3 gap-2">
                      <button 
                        v-for="year in years" 
                        :key="year"
                        class="px-4 py-3 rounded-xl text-sm font-bold transition-all border"
                        :class="selectedYear === year ? 'bg-blue-600 border-blue-600 text-white shadow-md' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'"
                        @click="selectedYear = year"
                      >
                        {{ year }}
                      </button>
                    </div>
                  </div>

                  <div class="space-y-2">
                    <label class="text-xs font-bold uppercase tracking-widest text-slate-400 ml-1">Monat</label>
                    <div class="relative group">
                      
                      <select v-model="selectedMonth" class="w-full pl-4 pr-10 py-4 bg-slate-50 border border-slate-200 rounded-2xl appearance-none focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-bold text-slate-700 cursor-pointer">
                        <option v-for="month in availableMonths" :key="month.value" :value="month.value">
                          {{ month.name }}
                        </option>
                      </select>

                      <div class="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                        <ChevronRight class="w-5 h-5 rotate-90" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <button 
                :disabled="isGenerating"
                class="w-full py-4 bg-blue-600 text-white rounded-2xl font-bold hover:bg-blue-700 shadow-xl shadow-blue-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 group"
                @click="handleDownload"
              >
                <Loader2
                  v-if="isGenerating"
                  class="w-5 h-5 animate-spin"
                />
                <Download
                  v-else
                  class="w-5 h-5 group-hover:scale-110 transition-transform"
                />
                <span>{{ isGenerating ? 'Generiere PDF...' : 'Zeitnachweis herunterladen' }}</span>
              </button>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
