<script setup>
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { X, CalendarDays, Lock, LockOpen, CreditCard, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-vue-next'
import { useDateFormatter } from '@/composables/useDateFormatter'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  member: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])
const adminStore = useAdminStore()
const { formatDate } = useDateFormatter()

const DISPLAY_DAYS = [
  { id: '0', label: 'Mo' },
  { id: '1', label: 'Di' },
  { id: '2', label: 'Mi' },
  { id: '3', label: 'Do' },
  { id: '4', label: 'Fr' },
  { id: '5', label: 'Sa' },
  { id: '6', label: 'So' }
]

// --- STATES ---
const isScanningRFID = ref(false) // Steuert das Overlay für den Scan-Vorgang
const registrationStatus = ref('waiting') // 'waiting' | 'success' | 'already_assigned' | 'error'
const scannedChipId = ref('')
const conflictMemberName = ref('')
const isManualInput = ref(false)
let pollingInterval = null

const todayISO = () => new Date().toISOString().split('T')[0]
const defaultSchema = () => ({ '0': 8, '1': 8, '2': 8, '3': 8, '4': 8, '5': 0, '6': 0 })
const hasSchema = (schema) => schema && Object.keys(schema).length > 0
const isEditingSchema = ref(false)

const form = ref({
  first_name: '',
  last_name: '',
  joined_at: '', 
  work_days_schema: defaultSchema(),
  schema_valid_from: todayISO(), 
  upcoming_schema_change: null, 
  overtime_balance: 0,
  vacation_total: 30,
  vacation_left: 30,
  chip_id: ''
})

const upcomingWeeklyHours = computed(() => {
  const schema = form.value.upcoming_schema_change?.work_days_schema
  if (!hasSchema(schema)) return 0
  return Object.values(schema).reduce((sum, h) => sum + (Number(h) || 0), 0)
})

const weeklyHours = computed(() => {
  if (!form.value.work_days_schema) return 0
  return Object.values(form.value.work_days_schema).reduce((sum, hours) => sum + (Number(hours) || 0), 0)
})

const calculateProRataVacation = (entryDateStr, yearlyDays) => {
  if (!entryDateStr) return yearlyDays
  const entryDate = new Date(entryDateStr)
  if (entryDate.getFullYear() < new Date().getFullYear()) return yearlyDays
  if (entryDate.getFullYear() > new Date().getFullYear()) return 0
  const monthsActive = 13 - (entryDate.getMonth() + 1)
  return Math.round((yearlyDays / 12) * monthsActive)
}

watch(
  [() => form.value.joined_at, () => form.value.vacation_days_per_year],
  ([newEntryDate, newYearlyDays]) => {
    form.value.vacation_total = calculateProRataVacation(newEntryDate, Number(newYearlyDays) || 0)
  }
)

const populateForm = (data) => {
  isEditingSchema.value = false
  isScanningRFID.value = false
  registrationStatus.value = 'waiting'
  scannedChipId.value = ''
  conflictMemberName.value = ''
  isManualInput.value = false
  stopPolling()

  if (data) {
    form.value = {
      first_name: data.first_name ?? '',
      last_name: data.last_name ?? '',
      joined_at: data.joined_at ?? '',
      work_days_schema: hasSchema(data.work_days_schema) ? { ...data.work_days_schema } : defaultSchema(),
      schema_valid_from: todayISO(),
      upcoming_schema_change: data.upcoming_schema_change ?? null,
      overtime_balance: Number(data.overtime_hours ?? 0),
      vacation_days_per_year: Number(data.vacation_days_per_year ?? 30),
      vacation_total: Number(data.vacation_total ?? data.vacation_days_per_year ?? 30),
      chip_id: data.chip_id ?? ''
    }
  } else {
    form.value = {
      first_name: '',
      last_name: '',
      joined_at: todayISO(),
      work_days_schema: defaultSchema(),
      schema_valid_from: todayISO(),
      upcoming_schema_change: null,
      overtime_balance: 0,
      vacation_days_per_year: 30,
      vacation_total: 30,
      chip_id: ''
    }
  }
}

watch(() => props.isOpen, async (newIsOpen) => {
  if (newIsOpen) {
    if (props.member && props.member.id) {
      populateForm(props.member)
      try {
        await adminStore.fetchTeamMemberDetail(props.member.id)
        if (adminStore.currentMember) populateForm(adminStore.currentMember)
      } catch (error) {
        console.error("Fehler beim Laden:", error)
      }
    } else {
      populateForm(null)
    }
  } else {
    stopPolling()
  }
}, { immediate: true })

// --- RFID POLLING LOGIK ---
const startPolling = () => {
  stopPolling()
  pollingInterval = setInterval(async () => {
    try {
      const res = await adminStore.fetchLatestPendingChip() 
      if (res && res.chip_id) {
        handleChipDetected(res.chip_id)
      }
    } catch (e) {
      console.error("Fehler beim Abrufen des ausstehenden Chips:", e)
    }
  }, 2000)
}

const stopPolling = () => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

const enableManualInput = () => {
  isManualInput.value = true
  stopPolling()
}

const startRFIDScanWorkflow = () => {
  isScanningRFID.value = true
  registrationStatus.value = 'waiting'
  startPolling()
}

// Wird aufgerufen, sobald eine ID (egal ob Scan oder Manuell) vorliegt
const handleChipDetected = async (chipId) => {
  stopPolling()
  scannedChipId.value = chipId

  try {
    // Prüfen, ob der Chip bereits vergeben ist (Simulation via API falls nötig, 
    // oder wir übernehmen ihn temporär ins Formular und lassen das Backend beim finalen Speichern meckern)
    // Hier weisen wir ihn direkt dem Formular zu und schließen das Scan-Fenster positiv ab:
    form.value.chip_id = chipId
    registrationStatus.value = 'success'
    
    // Nach kurzem Erfolgsklingeln zurück zum Hauptformular wechseln
    setTimeout(() => {
      isScanningRFID.value = false
    }, 1500)

  } catch (error) {
    registrationStatus.value = 'error'
  }
}

const handleManualSubmit = () => {
  if (scannedChipId.value) {
    handleChipDetected(scannedChipId.value.toUpperCase())
  }
}

// --- FINALES SPEICHERN ---
const handleFinalSubmit = async () => {
  if (!form.value.first_name || !form.value.last_name) return
  if (form.value.vacation_days_per_year === '') return

  const schemaChanged = props.member ? isEditingSchema.value : true

  try {
    const cleanedSchema = {}
    Object.entries(form.value.work_days_schema).forEach(([key, value]) => {
      cleanedSchema[key] = Number(value) || 0
    })

    if (props.member) {
      // BEARBEITEN
      const payload = {
        joined_at: form.value.joined_at,
        overtime_hours: form.value.overtime_balance,
        vacation_days_per_year: form.value.vacation_days_per_year,
        chip_id: form.value.chip_id // Schickt den aktuell verknüpften Chip mit
      }
      if (schemaChanged) {
        payload.work_days_schema = cleanedSchema
        payload.schema_valid_from = form.value.schema_valid_from
      }

      const response = await adminStore.updateTeamMember(props.member.id, payload)
      
      if (response?.status === 'already_assigned') {
        alert(`Fehler: Dieser Chip ist bereits ${response.assigned_to || 'jemand anderem'} zugewiesen.`)
      } else {
        emit('close')
      }
      
    } else {
      // NEUANLAGE
      const response = await adminStore.createTeamMember({
        first_name: form.value.first_name,
        last_name: form.value.last_name,
        joined_at: form.value.joined_at,
        work_days_schema: cleanedSchema,
        vacation_days_per_year: form.value.vacation_days_per_year,
        chip_id: form.value.chip_id
      })

      if (response?.status === 'already_assigned') {
        alert(`Fehler: Dieser Chip ist bereits ${response.assigned_to || 'jemand anderem'} zugewiesen.`)
      } else {
        emit('close')
      }
    }
  } catch (error) {
    console.error("Fehler bei der Registrierung:", error)
  }
}

onBeforeUnmount(() => {
  stopPolling()
})
</script>


<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
  >
    <div class="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden transition-all">
      
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 class="font-bold text-lg text-slate-900">
          {{ isScanningRFID ? 'RFID Transponder verknüpfen' : (member ? 'Mitarbeiter bearbeiten' : 'Mitarbeiter anlegen') }}
        </h3>
        <button 
          type="button"
          class="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          @click="emit('close')"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <form v-if="!isScanningRFID" class="p-6 space-y-4" @submit.prevent="handleFinalSubmit">
        
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Vorname</label>
            <input 
              v-model="form.first_name" 
              required
              :disabled="!!member"
              type="text" 
              class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Nachname</label>
            <input 
              v-model="form.last_name" 
              required
              :disabled="!!member"
              type="text" 
              class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Eintrittsdatum</label>
            <div class="relative">
              <input 
                v-model="form.joined_at" 
                required
                type="date" 
                class="w-full pl-4 pr-10 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 font-medium"
              />
              <CalendarDays class="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">RFID Transponder</label>
            
            <div v-if="form.chip_id" class="flex items-center justify-between gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl h-[38px]">
              <div class="flex items-center gap-1.5 min-w-0">
                <CreditCard class="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                <span class="text-xs font-mono font-bold text-slate-700 truncate uppercase">{{ form.chip_id }}</span>
              </div>
              <button 
                type="button"
                class="text-[11px] text-blue-600 hover:text-blue-700 font-bold transition-colors cursor-pointer flex-shrink-0"
                @click="startRFIDScanWorkflow"
              >
                Ändern
              </button>
            </div>

            <div v-else class="flex items-center justify-between gap-2 px-3 py-1.5 bg-amber-50/60 border border-amber-100 rounded-xl h-[38px]">
              <span class="text-xs text-amber-700 font-medium truncate">Kein Chip verknüpft</span>
              <button 
                type="button"
                class="text-[11px] text-blue-600 hover:text-blue-700 font-bold transition-colors cursor-pointer flex-shrink-0"
                @click="startRFIDScanWorkflow"
              >
                Verknüpfen
              </button>
            </div>
          </div>
        </div>

        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Arbeitszeit-Schema (Std.)</label>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold bg-blue-50 text-blue-600 px-2.5 py-1 rounded-lg border border-blue-100">
                Soll: <strong>{{ weeklyHours }}</strong> h/Woche
              </span>
              <button
                v-if="member"
                type="button"
                @click="isEditingSchema = !isEditingSchema"
                class="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                :class="{ 'text-amber-500 hover:text-amber-600': isEditingSchema }"
              >
                <component :is="isEditingSchema ? LockOpen : Lock" class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div v-if="form.upcoming_schema_change && isEditingSchema" class="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
            <CalendarDays class="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div>
              Es wurde bereits ein neues Schema hinterlegt (<strong>{{ upcomingWeeklyHours }} h/Woche</strong> ab <strong>{{ formatDate(form.upcoming_schema_change.valid_from) }}</strong>).
            </div>
          </div>

          <div class="grid grid-cols-7 gap-1">
            <div v-for="day in DISPLAY_DAYS" :key="day.id" class="space-y-1 text-center" :class="{'p-0.5 rounded-md hover:bg-slate-50': day.id === '5' || day.id === '6'}">
              <span class="text-[10px] font-bold uppercase text-slate-400 block">{{ day.label }}</span>
              <input 
                v-model.number="form.work_days_schema[day.id]" 
                type="number" step="any" min="0" max="24"
                :disabled="member && !isEditingSchema"
                class="w-full text-center p-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-bold text-slate-700 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>

          <div v-if="member && isEditingSchema" class="pt-1 space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Neues Schema gilt ab</label>
            <input v-model="form.schema_valid_from" type="date" :min="todayISO()" class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Urlaub / Jahr</label>
            <input v-model.number="form.vacation_days_per_year" type="number" min="0" class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20" />
          </div>
          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Restanspruch {{ new Date().getFullYear() }}</label>
            <div class="w-full px-4 py-2 bg-blue-50/50 border border-blue-100 text-blue-700 rounded-xl text-sm font-semibold flex items-center h-[38px]">
              {{ form.vacation_total }} Tage
            </div>
          </div>
        </div>

        <div class="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
          <button type="button" class="px-4 py-2 hover:bg-slate-100 rounded-xl text-slate-500 text-sm font-bold transition-all cursor-pointer" @click="emit('close')">
            Abbrechen
          </button>
          <button type="submit" class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-900/20 cursor-pointer">
            Fertigstellen
          </button>
        </div>
      </form>

      <div v-else class="p-8 flex flex-col items-center text-center space-y-6">
        
        <template v-if="isManualInput && registrationStatus === 'waiting'">
          <div class="flex items-center justify-center w-16 h-16 bg-slate-100 rounded-full text-slate-600 border border-slate-200">
            <CreditCard class="w-7 h-7" />
          </div>
          <div class="space-y-2 w-full text-left">
            <h4 class="font-bold text-slate-900 text-lg text-center">Manuelle Eingabe</h4>
            <p class="text-xs text-slate-500 text-center mb-4">
              Trage die Hexadezimal-ID des Chips manuell ein.
            </p>
            <label class="text-[10px] font-bold uppercase text-slate-400 tracking-wider block">Chip-ID (Hex)</label>
            <input 
              v-model="scannedChipId"
              type="text"
              placeholder="z.B. A3B4C5D6"
              class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-center uppercase tracking-widest"
              @keyup.enter="handleManualSubmit"
            />
          </div>
          
          <button 
            type="button"
            :disabled="!scannedChipId"
            class="w-full px-4 py-2.5 bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-900/20 cursor-pointer"
            @click="handleManualSubmit"
          >
            Chip übernehmen
          </button>
        </template>

        <template v-else-if="registrationStatus === 'waiting'">
          <div class="relative flex items-center justify-center w-24 h-24 bg-blue-50 rounded-full text-blue-600 border border-blue-100 animate-pulse">
            <CreditCard class="w-10 h-10" />
            <Loader2 class="w-24 h-24 absolute text-blue-500/30 animate-spin" style="animation-duration: 3s;" />
          </div>
          <div class="space-y-2">
            <h4 class="font-bold text-slate-900 text-lg">Bitte Chip auflegen</h4>
            <p class="text-sm text-slate-500 max-w-xs">
              Halte den neuen RFID-Chip an das Zeiterfassungs-Terminal.
            </p>
          </div>
          
          <button 
            type="button"
            class="text-xs text-blue-600 hover:text-blue-700 font-medium underline cursor-pointer pt-2"
            @click="enableManualInput"
          >
            Chip-ID manuell eintragen
          </button>
        </template>

        <template v-else-if="registrationStatus === 'success'">
          <div class="flex items-center justify-center w-24 h-24 bg-emerald-50 rounded-full text-emerald-600 border border-emerald-100">
            <CheckCircle2 class="w-12 h-12" />
          </div>
          <div class="space-y-2">
            <h4 class="font-bold text-slate-900 text-lg">Erfolgreich zugewiesen!</h4>
            <p class="text-sm text-slate-500">
              Der Chip wird im Formular eingetragen...
            </p>
          </div>
        </template>

        <div class="pt-4 w-full flex items-center justify-center gap-3 border-t border-slate-100">
          <button 
            v-if="registrationStatus === 'waiting'"
            type="button" 
            class="px-5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-sm font-bold transition-all cursor-pointer"
            @click="isScanningRFID = false; stopPolling(); isManualInput = false;"
          >
            Abbrechen
          </button>
          
          <button 
            v-if="isManualInput && registrationStatus === 'waiting'"
            type="button" 
            class="px-5 py-2 bg-slate-50 hover:bg-slate-100 text-slate-500 rounded-xl text-sm font-bold transition-all cursor-pointer"
            @click="isManualInput = false; startPolling(); scannedChipId = '';"
          >
            Wieder scannen
          </button>
        </div>

      </div>

    </div>
  </div>
</template>