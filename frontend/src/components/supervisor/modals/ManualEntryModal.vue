<script setup>
import { ref, watch, computed } from 'vue'
import { useAdminStore } from '@/stores/adminStore' 
import { useDateFormatter } from '@/composables/useDateFormatter'
import { X, CalendarPlus, AlertCircle, Clock, AlertTriangle, Loader2 } from 'lucide-vue-next'

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
const { formatTimeForInput } = useDateFormatter()

const entryType = ref('')
const date = ref('')
const timeIn = ref('')        
const timeOut = ref('')       
const note = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

const ENTRY_TYPES = [
  { value: 'vacation', label: 'Urlaub' },
  { value: 'sick', label: 'Krankmeldung' },
  { value: 'work', label: 'Stempelzeit nachbuchen (Kommen/Gehen)' }
]

// Reaktiv bestehende Events am ausgewählten Tag herausfiltern
const existingEvents = computed(() => {
  if (!date.value || !props.member?.name) return []
  const selectedDate = new Date(date.value)
  
  // Holt das Event aus dem Store
  const rawEvents = adminStore.getEventsForMemberAndDate(props.member.name, selectedDate) || []
  
  return rawEvents.map(event => {
    // Wenn eine Note existiert und der Typ 'work' ist, extrahieren wir die Stempelzeiten
    if (event.type === 'work' && event.note) {
      // Splittet den String am Pipe-Symbol |
      const parts = event.note.split('|')
      const timeRange = parts[0]?.trim() // Liefert z.B. "08:00 - 16:00"
      
      if (timeRange && timeRange.includes('-')) {
        return {
          id: event.id,
          label: `${event.title || 'Arbeitszeit'}: ${timeRange} Uhr`
        }
      }
    }
    
    // Fallback für Urlaub, Krankheit oder wenn das Format mal abweicht
    return {
      id: event.id,
      label: event.title || 'Bereits erfasste Zeitbuchung'
    }
  })
})

// Reset bei Sichtbarkeitswechsel
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    entryType.value = ''
    date.value = ''
    timeIn.value = ''
    timeOut.value = ''
    note.value = ''
    errorMessage.value = ''
    isSubmitting.value = false
    
    if (!adminStore.calendarEvents.length) {
      adminStore.fetchCalendarEvents()
    }
  }
})

const handleSubmit = async () => {
  if (!entryType.value || !date.value || !note.value || !props.member?.id) return

  isSubmitting.value = true
  errorMessage.value = ''

  const payload = {
    member_id: props.member.id,
    type: entryType.value,
    date: date.value,
    note: note.value,
    ...(entryType.value === 'work' && { check_in: timeIn.value, check_out: timeOut.value })
  }

  try {
    await adminStore.createManualEntry(payload)
    emit('success')
    emit('close')
  } catch (error) {
    console.error("Fehler beim manuellen Eintrag:", error)
    errorMessage.value = error.response?.data?.detail || 
                         (error.response?.data && Object.values(error.response.data).flat()[0]) || 
                         'Fehler beim Speichern des Eintrags.'
  } finally {
    isSubmitting.value = false
  }
}
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
      <div v-if="isOpen" class="fixed inset-0 z-[10000] flex items-center justify-center p-4">
        <div @click="!isSubmitting && $emit('close')" class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"></div>
        
        <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-300">
          
          <div class="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-blue-100 rounded-xl">
                <CalendarPlus class="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 class="text-xl font-bold text-slate-900">Manueller Eintrag</h2>
                <p class="text-[10px] text-slate-500 font-medium mt-0.5">Notfall-Korrektur für {{ member?.name }}</p>
              </div>
            </div>
            <button @click="$emit('close')" :disabled="isSubmitting" class="p-2 text-slate-400 hover:text-slate-600 rounded-full transition-all">
              <X class="w-5 h-5" />
            </button>
          </div>
          
          <form @submit.prevent="handleSubmit" class="p-6 space-y-6">
            
            <Transition
              enter-active-class="transition duration-200 ease-out"
              enter-from-class="opacity-0 -translate-y-2"
              enter-to-class="opacity-100 translate-y-0"
            >
              <div v-if="errorMessage" class="p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-start gap-3">
                <AlertCircle class="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <p class="text-xs text-rose-900 font-bold leading-tight">Fehler beim Speichern</p>
                  <p class="text-[10px] text-rose-700 mt-1 leading-relaxed">{{ errorMessage }}</p>
                </div>
              </div>
            </Transition>

            <div class="space-y-4">
              <div class="space-y-2">
                <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Art des Eintrags</label>
                <select 
                  v-model="entryType"
                  required
                  :disabled="isSubmitting"
                  class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2364748b%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E')] bg-[length:1rem_1rem] bg-[right_1rem_center] bg-no-repeat"
                >
                  <option value="" disabled selected>Bitte Typ auswählen...</option>
                  <option v-for="type in ENTRY_TYPES" :key="type.value" :value="type.value">
                    {{ type.label }}
                  </option>
                </select>
              </div>

              <div v-if="entryType" class="space-y-4 animate-in fade-in duration-300">
                
                <div class="space-y-2">
                  <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Datum</label>
                  <input 
                    v-model="date" 
                    type="date" 
                    required
                    :disabled="isSubmitting" 
                    class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                  />
                </div>

                <Transition
                  enter-active-class="transition duration-200 ease-out"
                  enter-from-class="opacity-0 -translate-y-2"
                  enter-to-class="opacity-100 translate-y-0"
                >
                  <div v-if="existingEvents.length > 0" class="p-4 bg-amber-50 border border-amber-100 rounded-2xl flex items-start gap-3">
                    <AlertTriangle class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <p class="text-xs text-amber-900 font-bold leading-tight">Überschreibungs-Gefahr!</p>
                      <p class="text-[10px] text-amber-700 mt-1 leading-relaxed">
                        An diesem Tag existieren bereits Einträge, die beim Speichern restlos überschrieben werden:
                      </p>
                      
                      <ul class="list-disc list-inside mt-1.5 text-[10px] text-amber-800 font-semibold space-y-0.5">
                        <li v-for="event in existingEvents" :key="event.id">
                          {{ event.label }}
                        </li>
                      </ul>
                      
                    </div>
                  </div>
                </Transition>

                <div v-if="entryType === 'work'" class="grid grid-cols-2 gap-4 animate-in fade-in duration-200">
                  <div class="space-y-2">
                    <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Kommen</label>
                    <input 
                      v-model="timeIn" 
                      type="time" 
                      required
                      :disabled="isSubmitting" 
                      class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                    />
                  </div>
                  <div class="space-y-2">
                    <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Gehen</label>
                    <input 
                      v-model="timeOut" 
                      type="time" 
                      required
                      :disabled="isSubmitting" 
                      class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                    />
                  </div>
                </div>

                <div class="space-y-2">
                  <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Begründung für System-Korrektur</label>
                  <textarea 
                    v-model="note" 
                    rows="3" 
                    required
                    :disabled="isSubmitting" 
                    class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none resize-none" 
                    placeholder="z.B. Server-Ausfall am Terminal, Mitarbeiter war regulär im Dienst..."
                  ></textarea>
                </div>
              </div>

              <div v-else class="p-6 bg-slate-50/50 border border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center min-h-[140px] text-center text-slate-400">
                <Clock class="w-6 h-6 mb-2 text-slate-300" />
                <p class="text-xs font-bold text-slate-500">Art des Eintrags fehlt</p>
                <p class="text-[10px] text-slate-400 mt-1 max-w-[200px] leading-normal">Bitte wähle zuerst einen Typ aus, um die Optionen anzuzeigen.</p>
              </div>

            </div>

            <div class="flex gap-3 pt-2">
              <button 
                type="button" 
                @click="$emit('close')" 
                :disabled="isSubmitting" 
                class="flex-1 py-3.5 bg-slate-100 text-slate-600 rounded-xl text-sm font-bold hover:bg-slate-200 transition-all disabled:opacity-50"
              >
                Abbrechen
              </button>
              <button 
                type="submit" 
                :disabled="isSubmitting || !entryType || !date || !note || (entryType === 'work' && (!timeIn || !timeOut))" 
                class="flex-1 py-3.5 px-4 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2"
                :class="[
                  (!entryType || !date || !note || (entryType === 'work' && (!timeIn || !timeOut)))
                    ? 'bg-slate-200 text-slate-400 cursor-not-allowed' 
                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/20'
                ]"
              >
                <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
                <template v-else>
                  Eintrag buchen
                </template>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

