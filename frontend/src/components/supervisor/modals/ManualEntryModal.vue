<script setup>
import { ref, watch, computed } from 'vue'
import { useAdminStore } from '@/stores/adminStore' 
import { X, CalendarPlus, AlertCircle, Clock, AlertTriangle, Loader2, Plus, Trash2 } from 'lucide-vue-next'

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
const date = ref(new Date().toISOString().split('T')[0])
const note = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)
const isLoadingDay = ref(false)

// Info über einen ggf. bereits bestehenden Tag (für den Warnhinweis)
const existingDayType = ref(null)          // Rohwert, z.B. 'work', 'vacation', 'sick'
const existingDayTypeDisplay = ref(null)   // Anzeigetext, z.B. "Arbeitstag"
const existingSessionCount = ref(0)

// Zeigt den neutralen "Zeiten geladen"-Hinweis nur, wenn es tatsächlich etwas zu bearbeiten gibt
const showLoadedInfo = computed(() =>
  entryType.value === 'work' &&
  existingDayType.value === 'work' &&
  existingSessionCount.value > 0
)

// Zeigt die Überschreibungs-Warnung nur, wenn beim Speichern wirklich etwas verloren geht,
// also der bestehende Tagestyp vom neu gewählten Typ abweicht (z.B. Arbeit -> Krank).
// Ein leerer WorkDay vom selben Typ (z.B. "work" ohne Sessions) ist keine Datenlöschung.
const showOverwriteWarning = computed(() =>
  existingDayType.value !== null &&
  existingDayType.value !== entryType.value
)

// Jede Session: { _key, id (null = neu), check_in, check_out }
let sessionKeyCounter = 0
const makeSession = (data = {}) => ({
  _key: sessionKeyCounter++,
  id: data.id ?? null,
  check_in: data.check_in ?? '',
  check_out: data.check_out ?? ''
})

const sessions = ref([makeSession()])
// IDs von Sessions, die der Supervisor im Modal aktiv entfernt hat -> werden beim Speichern gelöscht
const deletedSessionIds = ref([])

const ENTRY_TYPES = [
  { value: 'vacation', label: 'Urlaub' },
  { value: 'sick', label: 'Krankmeldung' },
  { value: 'work', label: 'Stempelzeit nachbuchen (Kommen/Gehen)' }
]

function resetForm() {
  entryType.value = ''
  date.value = new Date().toISOString().split('T')[0]  
  note.value = ''
  errorMessage.value = ''
  isSubmitting.value = false
  isLoadingDay.value = false
  sessions.value = [makeSession()]
  deletedSessionIds.value = []
  existingDayType.value = null
  existingDayTypeDisplay.value = null
  existingSessionCount.value = 0

  loadExistingDay()
}

// Reset bei Sichtbarkeitswechsel
watch(() => props.isOpen, (newVal) => {
  if (newVal) resetForm()
})

// Sobald Datum (und Mitglied) feststehen: bestehenden Tag laden.
// So werden vorhandene Stempelzeiten zum Bearbeiten vorbefüllt, statt sie
// beim Speichern blind zu überschreiben.
async function loadExistingDay() {
  if (!date.value || !props.member?.id) {
    existingDayType.value = null
    existingDayTypeDisplay.value = null
    existingSessionCount.value = 0
    return
  }

  isLoadingDay.value = true
  try {
    const data = await adminStore.fetchWorkDayDetail(props.member.id, date.value)
    deletedSessionIds.value = []

    if (data.exists) {
      existingDayType.value = data.day_type
      existingDayTypeDisplay.value = data.day_type_display || data.day_type
      existingSessionCount.value = data.sessions?.length || 0

      if (data.day_type === 'work' && data.sessions?.length) {
        sessions.value = data.sessions.map(s => makeSession(s))
      } else {
        sessions.value = [makeSession()]
      }
    } else {
      existingDayType.value = null
      existingDayTypeDisplay.value = null
      existingSessionCount.value = 0
      sessions.value = [makeSession()]
    }
  } catch (error) {
    console.error('Konnte bestehenden Tag nicht laden:', error)
  } finally {
    isLoadingDay.value = false
  }
}

watch(date, () => {
  loadExistingDay()
})

function addSession() {
  sessions.value.push(makeSession())
}

function removeSession(index) {
  const session = sessions.value[index]
  // Nur bestehende (gespeicherte) Sessions müssen dem Backend explizit als "löschen" mitgeteilt werden
  if (session.id) {
    deletedSessionIds.value.push(session.id)
  }
  sessions.value.splice(index, 1)
  if (sessions.value.length === 0) {
    sessions.value.push(makeSession())
  }
}

const isFormValid = () => {
  if (!entryType.value || !date.value || !note.value || !props.member?.id) return false
  if (entryType.value === 'work') {
    return sessions.value.every(s => s.check_in && s.check_out)
  }
  return true
}

const showDuplicateTypeWarning = computed(() =>
  existingDayType.value !== null &&
  existingDayType.value === entryType.value &&
  existingDayType.value !== 'work'
)

const handleSubmit = async () => {
  if (!isFormValid()) return

  isSubmitting.value = true
  errorMessage.value = ''

  const payload = {
    member_id: props.member.id,
    type: entryType.value,
    date: date.value,
    note: note.value,
    ...(entryType.value === 'work' && {
      sessions: sessions.value.map(s => ({
        ...(s.id ? { id: s.id } : {}),
        check_in: s.check_in,
        check_out: s.check_out
      })),
      deleted_session_ids: deletedSessionIds.value
    })
  }

  try {
    await adminStore.createManualEntry(payload)
    emit('success')
    emit('close')
  } catch (error) {
    console.error("Fehler beim manuellen Eintrag:", error)
    
    const responseData = error.response?.data
    
    if (responseData) {
      // Hilfsfunktion, um rekursiv den ersten String aus dem DRF-Fehlerobjekt zu extrahieren
      const extractFirstError = (obj) => {
        if (typeof obj === 'string') return obj;
        if (Array.isArray(obj)) {
          for (const item of obj) {
            const found = extractFirstError(item);
            if (found) return found;
          }
        } else if (obj && typeof obj === 'object') {
          for (const key in obj) {
            const found = extractFirstError(obj[key]);
            if (found) return found;
          }
        }
        return null;
      };

      // Erst nach "detail" suchen (Standard bei API-Ausnahmen), sonst das gesamte Objekt durchwühlen
      if (responseData.detail) {
        if (typeof responseData.detail === 'string') {
          errorMessage.value = responseData.detail;
        } else {
          errorMessage.value = extractFirstError(responseData.detail) || 'Ein Fehler ist aufgetreten.';
        }
      } else {
        errorMessage.value = extractFirstError(responseData) || 'Validierungsfehler aufgetreten.';
      }

    } else {
      errorMessage.value = 'Fehler beim Speichern des Eintrags. Bitte Serververbindung prüfen.';
    }
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
        
        <!-- flex flex-col und max-h-full stellt sicher, dass das Modal nie größer als der Bildschirm wird -->
        <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-md max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-300">
          
          <!-- FIXIERTER HEADER -->
          <div class="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50 shrink-0">
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
          
          <!-- FORMULAR MIT SCROLL-BEREICH -->
          <!-- flex-1 und overflow-y-auto lassen nur diesen Teil scrollen -->
          <form @submit.prevent="handleSubmit" class="flex flex-col flex-1 min-h-0">
            
            <div class="p-6 space-y-6 overflow-y-auto flex-1 chunk-scroll-area">

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
                    mode="out-in"
                  >
                    <div 
                      v-if="showLoadedInfo && !isLoadingDay" 
                      class="p-4 bg-blue-50 border border-blue-100 rounded-2xl flex items-start gap-3"
                    >
                      <Clock class="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                      <div>
                        <p class="text-xs text-blue-900 font-bold leading-tight">Bestehende Zeiten geladen</p>
                        <p class="text-[10px] text-blue-700 mt-1 leading-relaxed">
                          Für diesen Tag sind bereits Stempelzeiten erfasst. Du kannst sie unten bearbeiten,
                          entfernen oder weitere hinzufügen.
                        </p>
                      </div>
                    </div>

                    <div 
                      v-else-if="showOverwriteWarning && !isLoadingDay" 
                      class="p-4 bg-amber-50 border border-amber-100 rounded-2xl flex items-start gap-3"
                    >
                      <AlertTriangle class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <p class="text-xs text-amber-900 font-bold leading-tight">Überschreibungs-Gefahr!</p>
                        <p class="text-[10px] text-amber-700 mt-1 leading-relaxed">
                          An diesem Tag existiert bereits ein Eintrag ("{{ existingDayTypeDisplay }}"), der beim
                          Speichern durch "{{ ENTRY_TYPES.find(t => t.value === entryType)?.label }}" ersetzt wird.
                        </p>
                      </div>
                    </div>

                    <div 
                      v-else-if="showDuplicateTypeWarning && !isLoadingDay" 
                      class="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex items-start gap-3"
                    >
                      <AlertCircle class="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />
                      <div>
                        <p class="text-xs text-slate-900 font-bold leading-tight">Eintrag bereits vorhanden</p>
                        <p class="text-[10px] text-slate-600 mt-1 leading-relaxed">
                          Dieser Tag ist bereits als "{{ existingDayTypeDisplay }}" erfasst. 
                          Ein erneutes Speichern aktualisiert lediglich die Begründung.
                        </p>
                      </div>
                    </div>
                  </Transition>

                  <Transition
                    enter-active-class="transition duration-200 ease-out"
                    enter-from-class="opacity-0 -translate-y-2"
                    enter-to-class="opacity-100 translate-y-0"
                  >
                    <div v-if="errorMessage" class="p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-start gap-3 mt-3">
                      <AlertCircle class="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                      <div>
                        <p class="text-xs text-rose-900 font-bold leading-tight">Fehler beim Speichern</p>
                        <p class="text-[10px] text-rose-700 mt-1 leading-relaxed">{{ errorMessage }}</p>
                      </div>
                    </div>
                  </Transition>

                  <div v-if="entryType === 'work'" class="space-y-3 animate-in fade-in duration-200">
                    <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Erfasste Stempelzeiten</label>

                    <div 
                      v-for="(session, index) in sessions" 
                      :key="session._key" 
                      class="grid grid-cols-[1fr_1fr_auto] gap-2 items-end"
                    >
                      <div class="space-y-1">
                        <label class="text-[9px] font-bold uppercase tracking-widest text-slate-400 ml-1">Kommen</label>
                        <input 
                          v-model="session.check_in" 
                          type="time" 
                          required
                          :disabled="isSubmitting" 
                          class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                        />
                      </div>
                      <div class="space-y-1">
                        <label class="text-[9px] font-bold uppercase tracking-widest text-slate-400 ml-1">Gehen</label>
                        <input 
                          v-model="session.check_out" 
                          type="time" 
                          required
                          :disabled="isSubmitting" 
                          class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                        />
                      </div>
                      <button 
                        type="button"
                        @click="removeSession(index)"
                        :disabled="isSubmitting"
                        class="p-3 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all"
                        title="Diese Zeit entfernen"
                      >
                        <Trash2 class="w-4 h-4" />
                      </button>
                    </div>

                    <button 
                      type="button"
                      @click="addSession"
                      :disabled="isSubmitting"
                      class="w-full py-2.5 flex items-center justify-center gap-2 text-xs font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-xl transition-all"
                    >
                      <Plus class="w-4 h-4" />
                      Weitere Zeit hinzufügen
                    </button>
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
            </div>

            <!-- FIXIERTER FOOTER -->
            <!-- Durch die Platzierung außerhalb der Scroll-Zone bleiben die Buttons immer unten stehen -->
            <div class="p-6 border-t border-slate-100 bg-slate-50/50 flex gap-3 shrink-0">
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
                :disabled="isSubmitting || !isFormValid()" 
                class="flex-1 py-3.5 px-4 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2"
                :class="[
                  !isFormValid()
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