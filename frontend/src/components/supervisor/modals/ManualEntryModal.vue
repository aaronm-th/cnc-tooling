<script setup>
import { ref, watch, computed } from 'vue'
import { useAdminStore } from '@/stores/adminStore' // Passe den Store-Pfad ggf. an deine Logik an
import { X, CalendarPlus, AlertCircle, Clock } from 'lucide-vue-next'

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

const emit = defineEmits(['close', 'success'])
const adminStore = useAdminStore()

const entryType = ref('')
const date = ref('')
const durationOrTime = ref('') // Für Stunden (Krank/Urlaub) oder exakte Uhrzeit
const timeOut = ref('')        // Nur für Stempelzeiten (Gehen-Zeit)
const note = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

const ENTRY_TYPES = [
  { value: 'urlaub', label: 'Urlaubssemester / Urlaubstag' },
  { value: 'krankheit', label: 'Krankmeldung (Manuell)' },
  { value: 'zeiterfassung', label: 'Stempelzeit nachbuchen (Kommen/Gehen)' }
]

// Reset des Formulars bei Schließen/Öffnen
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    entryType.value = ''
    date.value = ''
    durationOrTime.value = ''
    timeOut.value = ''
    note.value = ''
    errorMessage.value = ''
    isSubmitting.value = false
  }
})

const handleSubmit = async () => {
  if (!entryType.value || !date.value || !props.member?.id) return

  isSubmitting.value = true
  errorMessage.value = ''

  // Vorbereitung der Payload je nach Typ
  const payload = {
    member_id: props.member.id,
    type: entryType.value,
    date: date.value,
    note: note.value,
    // Je nach Typ mappen wir die Felder passend für das Backend
    ...(entryType.value === 'zeiterfassung' 
        ? { check_in: durationOrTime.value, check_out: timeOut.value } 
        : { hours_or_days: durationOrTime.value }
    )
  }

  try {
    // Ersetze dies durch deine tatsächliche API/Store-Aktion
    if (typeof adminStore.createManualEntry === 'function') {
      await adminStore.createManualEntry(payload)
    } else {
      // Mock/Fallback für Entwicklungszwecke, falls die Store-Methode noch fehlt
      console.log("Sende an API:", payload)
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
    
    emit('success')
    emit('close')
  } catch (error) {
    console.error("Fehler beim manuellen Eintrag:", error)
    errorMessage.value = error.response?.data?.detail || 'Fehler beim Speichern des Eintrags.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
  >
    <div class="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden">
      
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 class="font-bold text-lg text-slate-900">Manueller Eintrag</h3>
          <p class="text-xs text-slate-500 mt-0.5">Notfall-Korrektur für {{ member?.name }}</p>
        </div>
        <button 
          type="button"
          class="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          @click="emit('close')"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <form class="p-6 space-y-5" @submit.prevent="handleSubmit">
        
        <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-100 rounded-xl flex items-start gap-2.5 text-sm text-red-700">
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ errorMessage }}</span>
        </div>

        <div class="space-y-1.5">
          <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Art des Eintrags</label>
          <select 
            v-model="entryType"
            required
            class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800 font-medium appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2364748b%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E')] bg-[length:1rem_1rem] bg-[right_1rem_center] bg-no-repeat"
          >
            <option value="" disabled selected>Bitte Typ auswählen...</option>
            <option v-for="type in ENTRY_TYPES" :key="type.value" :value="type.value">
              {{ type.label }}
            </option>
          </select>
        </div>

        <div v-if="entryType" class="space-y-4 animate-fadeIn">
          
          <div class="space-y-1.5">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Datum</label>
            <input 
              v-model="date"
              type="date"
              required
              class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
            />
          </div>

          <div v-if="entryType === 'urlaub' || entryType === 'krankheit'" class="space-y-1.5">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">
              Dauer (in Stunden)
            </label>
            <input 
              v-model="durationOrTime"
              type="number"
              step="0.5"
              placeholder="z.B. 8.0"
              required
              class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
            />
          </div>

          <div v-if="entryType === 'zeiterfassung'" class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Kommen (Zeit)</label>
              <input 
                v-model="durationOrTime"
                type="time"
                required
                class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Gehen (Zeit)</label>
              <input 
                v-model="timeOut"
                type="time"
                required
                class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
              />
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Begründung für System-Korrektur</label>
            <textarea 
              v-model="note"
              rows="3"
              placeholder="z.B. Server-Ausfall am Terminal von 08:00 - 10:00 Uhr..."
              required
              class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800 resize-none"
            ></textarea>
          </div>

        </div>

        <div v-else class="p-4 bg-slate-50/50 border border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center min-h-[120px] text-center text-slate-400">
          <Clock class="w-6 h-6 mb-2 text-slate-300" />
          <p class="text-xs font-medium">Bitte wähle zuerst die Art des Eintrags aus,<br> um die Optionen anzuzeigen.</p>
        </div>

        <div class="pt-2 border-t border-slate-100 flex items-center justify-end gap-3">
          <button 
            type="button" 
            :disabled="isSubmitting"
            class="px-4 py-2 hover:bg-slate-100 rounded-xl text-slate-500 text-sm font-bold transition-all cursor-pointer disabled:opacity-50"
            @click="emit('close')"
          >
            Abbrechen
          </button>
          <button 
            type="submit" 
            :disabled="!entryType || !date || !note || isSubmitting"
            class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none disabled:cursor-not-allowed rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-900/20 cursor-pointer flex items-center gap-2"
          >
            <span v-if="isSubmitting" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            {{ isSubmitting ? 'Wird gespeichert...' : 'Eintrag buchen' }}
          </button>
        </div>

      </form>
    </div>
  </div>
</template>