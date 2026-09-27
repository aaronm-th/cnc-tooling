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
  },
  // Erwartet das angeklickte Datum als String (z.B. "2026-09-15")
  initialDate: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'success'])
const adminStore = useAdminStore()

const entryType = ref('')
const date = ref('')             // Für Typ 'work' (Einzeltag)
const startDate = ref('')        // Für Typ 'vacation' / 'sick'
const endDate = ref('')          // Für Typ 'vacation' / 'sick'
const note = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)
const isLoadingDay = ref(false)
const isDeleting = ref(false)
const showDeleteConfirm = ref(false)
const deleteError = ref('')

// Info über einen ggf. bereits bestehenden Tag
const existingDayType = ref(null)          
const existingDayTypeDisplay = ref(null)   
const existingSessionCount = ref(0)
const existingWarning = ref(null)

const isRangeType = computed(() => ['vacation', 'sick'].includes(entryType.value))

const showLoadedInfo = computed(() =>
  entryType.value === 'work' &&
  existingDayType.value === 'work' &&
  existingSessionCount.value > 0
)

const showOverwriteWarning = computed(() =>
  existingDayType.value !== null &&
  entryType.value !== '' &&
  existingDayType.value !== entryType.value
)

const canDelete = computed(() =>
  entryType.value !== '' &&
  existingDayType.value !== null &&
  !isLoadingDay.value
)

let sessionKeyCounter = 0

const makeSession = (data = {}) => ({
  _key: sessionKeyCounter++,
  id: data.id ?? null,
  check_in: data.check_in ?? '',
  check_out: data.check_out ?? '',
  is_auto_checkout: data.is_auto_checkout ?? false
})

const sessions = ref([makeSession()])
const deletedSessionIds = ref([])

const ENTRY_TYPES = [
  { value: 'vacation', label: 'Urlaub' },
  { value: 'sick', label: 'Krankmeldung' },
  { value: 'work', label: 'Stempelzeit nachbuchen (Kommen/Gehen)' }
]

// Setzt das Formular zurück
function resetForm() {
  entryType.value = ''
  const initial = props.initialDate || new Date().toISOString().split('T')[0]
  date.value = initial
  startDate.value = initial
  endDate.value = initial
  note.value = ''
  errorMessage.value = ''
  isSubmitting.value = false
  isLoadingDay.value = false
  isDeleting.value = false
  showDeleteConfirm.value = false
  deleteError.value = ''
  sessions.value = [makeSession()]
  deletedSessionIds.value = []
  existingDayType.value = null
  existingDayTypeDisplay.value = null
  existingSessionCount.value = 0
  existingWarning.value = null

  loadExistingDay()
}

// Watcher für das Öffnen des Modals
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    resetForm()
  }
})

// Wenn sich das Datum aus den Props ändert
watch(() => props.initialDate, (newDate) => {
  if (newDate) {
    date.value = newDate
    startDate.value = newDate
    endDate.value = newDate
    loadExistingDay()
  }
})

async function loadExistingDay() {
  const targetDate = isRangeType.value ? startDate.value : date.value

  if (!targetDate || !props.member?.id) {
    existingDayType.value = null
    existingDayTypeDisplay.value = null
    existingSessionCount.value = 0
    existingWarning.value = null
    return
  }

  isLoadingDay.value = true
  try {
    const data = await adminStore.fetchWorkDayDetail(props.member.id, targetDate)
    deletedSessionIds.value = []

    if (data.exists) {
      existingDayType.value = data.day_type
      existingDayTypeDisplay.value = data.day_type_display || data.day_type
      existingSessionCount.value = data.sessions?.length || 0
      existingWarning.value = data.warning || null

      entryType.value = data.day_type

      if (data.day_type === 'work' && data.sessions?.length) {
        sessions.value = data.sessions.map(s => makeSession(s))
        const hasAutoCheckoutSession = data.sessions.some(s => s.is_auto_checkout)
        
        if (hasAutoCheckoutSession && !note.value) {
          note.value = 'Korrektur Auto-Checkout'
        }
      } else {
        sessions.value = [makeSession()]
      }
    } else {
      existingDayType.value = null
      existingDayTypeDisplay.value = null
      existingSessionCount.value = 0
      existingWarning.value = null
      sessions.value = [makeSession()]
    }
  } catch (error) {
    console.error('Konnte bestehenden Tag nicht laden:', error)
  } finally {
    isLoadingDay.value = false
  }
}

watch([date, startDate], ([newDate, newStart], [oldDate, oldStart]) => {
  if (props.isOpen) {
    if ((newDate && newDate !== oldDate) || (newStart && newStart !== oldStart)) {
      loadExistingDay()
    }
  }
})

watch(sessions, (newSessions) => {
  const hasAutoCheckout = newSessions.some(s => s.is_auto_checkout)
  if (hasAutoCheckout && !note.value) {
    note.value = 'Korrektur Auto-Checkout'
  }
}, { deep: true })

function addSession() {
  sessions.value.push(makeSession())
}

function removeSession(index) {
  const session = sessions.value[index]
  if (session.id) {
    deletedSessionIds.value.push(session.id)
  }
  sessions.value.splice(index, 1)
  if (sessions.value.length === 0) {
    sessions.value.push(makeSession())
  }
}

const isFormValid = () => {
  if (!entryType.value || !note.value || !props.member?.id) return false
  
  if (isRangeType.value) {
    if (!startDate.value || !endDate.value) return false
    if (startDate.value > endDate.value) return false
  } else {
    if (!date.value) return false
    if (entryType.value === 'work') {
      return sessions.value.every(s => s.check_in && s.check_out)
    }
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
    note: note.value,
    ...(isRangeType.value ? {
      start_date: startDate.value,
      end_date: endDate.value,
      date: startDate.value // Fallback für APIs, die ein Hauptdatum erwarten
    } : {
      date: date.value,
      ...(entryType.value === 'work' && {
        sessions: sessions.value.map(s => ({
          ...(s.id ? { id: s.id } : {}),
          check_in: s.check_in,
          check_out: s.check_out
        })),
        deleted_session_ids: deletedSessionIds.value
      })
    })
  }

  try {
    await adminStore.createManualEntry(payload)
    emit('success', { 
      memberId: props.member.id, 
      date: isRangeType.value ? startDate.value : date.value 
    })
    emit('close')
  } catch (error) {
    console.error("Fehler beim manuellen Eintrag:", error)
    const responseData = error.response?.data
    
    if (responseData) {
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

const handleDelete = async () => {
  isDeleting.value = true
  deleteError.value = ''

  const targetDate = isRangeType.value ? startDate.value : date.value

  try {
    await adminStore.deleteManualEntry(props.member.id, targetDate)
    emit('success')
    emit('close')
  } catch (error) {
    console.error("Fehler beim Löschen des Eintrags:", error)
    deleteError.value = error.response?.data?.error || 'Eintrag konnte nicht gelöscht werden.'
    showDeleteConfirm.value = false
  } finally {
    isDeleting.value = false
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
          <form @submit.prevent="handleSubmit" class="flex flex-col flex-1 min-h-0">
            
            <div class="p-6 space-y-6 overflow-y-auto flex-1 chunk-scroll-area">

              <div class="space-y-4">
                <!-- TYPE SELECT -->
                <div class="space-y-2">
                  <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Art des Eintrags</label>
                  <select 
                    v-model="entryType"
                    required
                    :disabled="isSubmitting"
                    style="-webkit-appearance: none; -moz-appearance: none; text-overflow: ellipsis;"
                    class="w-full min-w-0 pl-4 pr-10 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2364748b%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E')] bg-[length:1rem_1rem] bg-[right_1rem_center] bg-no-repeat"
                  >
                    <option value="" disabled selected>Bitte Typ auswählen...</option>
                    <option v-for="type in ENTRY_TYPES" :key="type.value" :value="type.value">
                      {{ type.label }}
                    </option>
                  </select>
                </div>
                
                <!-- DATUMS-FELDER: DYNAMISCH ZWISCHEN SPANNE UND EINZELTAG -->
                <div v-if="isRangeType" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div class="space-y-2 min-w-0">
                    <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Von</label>
                    <input 
                      v-model="startDate" 
                      type="date" 
                      required
                      :disabled="isSubmitting" 
                      class="w-full min-w-0 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                    />
                  </div>
                  <div class="space-y-2 min-w-0">
                    <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Bis (inkl.)</label>
                    <input 
                      v-model="endDate" 
                      type="date" 
                      required
                      :min="startDate"
                      :disabled="isSubmitting" 
                      class="w-full min-w-0 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                    />
                  </div>
                </div>

                <div v-else class="space-y-2">
                  <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Datum</label>
                  <input 
                    v-model="date" 
                    type="date" 
                    required
                    :disabled="isSubmitting" 
                    class="w-full min-w-0 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                  />
                </div>

                <!-- DYNAMISCHER BEREICH NCH TYP -->
                <div v-if="entryType" class="space-y-4 animate-in fade-in duration-300">
                  
                  <!-- SYSTEM-WARNUNG (Auto-Checkout etc.) -->
                  <div 
                    v-if="existingWarning && !isLoadingDay" 
                    class="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-start gap-3"
                  >
                    <AlertTriangle class="w-5 h-5 fill-amber-400 text-slate-900 shrink-0 mt-0.5" />
                    <div>
                      <p class="text-xs text-amber-900 font-bold leading-tight">System-Warnung für diesen Tag</p>
                      <p class="text-[11px] text-amber-800 mt-1 leading-relaxed font-medium">
                        {{ existingWarning }}
                      </p>
                    </div>
                  </div>

                  <!-- HINWEISE ZUM TAG -->
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

                  <!-- STAMPING ZEITEN (NUR BEI 'WORK') -->
                  <div v-if="entryType === 'work'" class="space-y-3 animate-in fade-in duration-200">
                    <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">
                      Erfasste Stempelzeiten
                    </label>

                    <div 
                      v-for="(session, index) in sessions" 
                      :key="session._key" 
                      class="p-2 rounded-2xl transition-all relative"
                      :class="[
                        session.is_auto_checkout 
                          ? 'bg-amber-500/10 border border-amber-300/60 shadow-sm' 
                          : ''
                      ]"
                    >
                      <div 
                        v-if="session.is_auto_checkout" 
                        class="flex items-center gap-1.5 mb-1.5 ml-1 text-amber-800 text-[10px] font-bold"
                      >
                        <AlertTriangle class="w-3.5 h-3.5 fill-amber-400 text-slate-900 shrink-0" />
                        <span>Automatische Ausstempelung / Korrekturbedarf</span>
                      </div>

                      <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] gap-2 items-end">
                        <div class="space-y-1 min-w-0">
                          <label class="text-[9px] font-bold uppercase tracking-widest text-slate-400 ml-1">Kommen</label>
                          <input 
                            v-model="session.check_in" 
                            type="time" 
                            required
                            :disabled="isSubmitting" 
                            class="w-full min-w-0 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                          />
                        </div>

                        <div class="space-y-1 min-w-0">
                          <label class="text-[9px] font-bold uppercase tracking-widest text-slate-400 ml-1">Gehen</label>
                          <input 
                            v-model="session.check_out" 
                            type="time" 
                            required
                            :disabled="isSubmitting" 
                            class="w-full min-w-0 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium"
                            :class="{ 'border-amber-400 font-bold text-amber-900': session.is_auto_checkout }" 
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

                  <!-- BEGRÜNDUNG -->
                  <div class="space-y-2">
                    <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Begründung für System-Korrektur</label>
                    <textarea 
                      v-model="note" 
                      rows="3" 
                      required
                      :disabled="isSubmitting" 
                      class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none resize-none" 
                      placeholder="z.B. Erholungsurlaub genehmigt, AU eingereicht..."
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
            <div class="p-6 border-t border-slate-100 bg-slate-50/50 flex flex-col gap-3 shrink-0">
              <div v-if="deleteError" class="p-3 bg-rose-50 border border-rose-100 rounded-xl flex items-start gap-2">
                <AlertCircle class="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <p class="text-[10px] text-rose-700 leading-relaxed">{{ deleteError }}</p>
              </div>

              <div class="flex gap-3">
                <button 
                  type="button" 
                  @click="$emit('close')" 
                  :disabled="isSubmitting || isDeleting" 
                  class="flex-1 py-3.5 bg-slate-100 text-slate-600 rounded-xl text-sm font-bold hover:bg-slate-200 transition-all disabled:opacity-50"
                >
                  Abbrechen
                </button>
                <button 
                  v-if="canDelete"
                  type="button"
                  @click="showDeleteConfirm = true"
                  :disabled="isSubmitting || isDeleting"
                  class="py-3.5 px-4 bg-rose-50 text-rose-600 rounded-xl text-sm font-bold hover:bg-rose-100 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                  title="Diesen Eintrag vollständig löschen"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
                <button 
                  type="submit" 
                  :disabled="isSubmitting || isDeleting || !isFormValid()" 
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
            </div>
          </form>
        </div>

        <!-- LÖSCH-BESTÄTIGUNG -->
        <Transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0"
          enter-to-class="opacity-100"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <div v-if="showDeleteConfirm" class="absolute inset-0 z-10 flex items-center justify-center p-6">
            <div @click="!isDeleting && (showDeleteConfirm = false)" class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm rounded-3xl"></div>
            <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
              <div class="flex items-start gap-3">
                <div class="p-2 bg-rose-100 rounded-xl shrink-0">
                  <AlertTriangle class="w-5 h-5 text-rose-600" />
                </div>
                <div>
                  <h3 class="text-sm font-bold text-slate-900">Eintrag wirklich löschen?</h3>
                  <p class="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Der komplette Eintrag ("{{ existingDayTypeDisplay }}") für {{ member?.name }} am
                    {{ isRangeType ? startDate : date }} inklusive aller erfassten Zeiten wird unwiderruflich entfernt.
                  </p>
                </div>
              </div>
              <div class="flex gap-3">
                <button
                  type="button"
                  @click="showDeleteConfirm = false"
                  :disabled="isDeleting"
                  class="flex-1 py-3 bg-slate-100 text-slate-600 rounded-xl text-sm font-bold hover:bg-slate-200 transition-all disabled:opacity-50"
                >
                  Abbrechen
                </button>
                <button
                  type="button"
                  @click="handleDelete"
                  :disabled="isDeleting"
                  class="flex-1 py-3 bg-rose-600 text-white rounded-xl text-sm font-bold hover:bg-rose-700 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Loader2 v-if="isDeleting" class="w-4 h-4 animate-spin" />
                  <template v-else>Ja, löschen</template>
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>