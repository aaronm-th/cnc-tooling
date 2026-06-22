<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { X, Clock, MessageSquare, AlertCircle, CheckCircle2, RotateCcw, Trash2, Plus, FileText } from 'lucide-vue-next'
import { useDateFormatter } from '@/composables/useDateFormatter'

const props = defineProps({
  isOpen: { type: Boolean, required: true },
  shift: { type: Object, default: null },
  isLoading: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'submit', 'withdraw'])
const { formatDate, formatTimeForInput } = useDateFormatter()

const isSubmitted = ref(false)
const localSessions = ref([])

const displayDate = computed(() => formatDate(props.shift?.date))
const isManualAdding = ref(false)

const onKeyDown = (e) => {
  if (e.key === 'Escape' && props.isOpen) handleClose()
}


const addManualSession = () => {
  isManualAdding.value = true
  localSessions.value.push({
    id: null, // Wichtig: null markiert eine neue Session
    check_in: '08:00',
    check_out: '16:00',
    orig_check_in: null,
    orig_check_out: null,
    note: '',
    isPending: false,
    isNew: true // Flag für das UI
  })
}

watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    // 1. Event Listener für Tastatur (ESC) hinzufügen
    window.addEventListener('keydown', onKeyDown)
    
    // 2. Daten initialisieren
    isSubmitted.value = false
    if (props.shift?.sessions) {
      localSessions.value = props.shift.sessions.map(session => ({
        id: session.id,
        check_in: formatTimeForInput(session.pending_request?.requested_check_in || session.check_in),
        check_out: formatTimeForInput(session.pending_request?.requested_check_out || session.check_out),
        orig_check_in: formatTimeForInput(session.check_in),
        orig_check_out: formatTimeForInput(session.check_out),
        note: session.pending_request?.employee_note || '',
        isPending: !!session.pending_request,
        old_ver_exists: session.old_ver_exists || false
      }))
    }
  } else {
    // 3. Cleanup: Listener entfernen und State zurücksetzen
    window.removeEventListener('keydown', onKeyDown)
    localSessions.value = []
  }
}, { immediate: true })

const createPayload = (session) => ({
  workday_id: props.shift.id, // Wir brauchen die ID des Tages für neue Sessions
  worksession_id: session.id, // Bleibt null bei neuen Sessions
  employee_note: session.note,
  requested_check_in: `${props.shift.date}T${session.check_in}:00`,
  requested_check_out: `${props.shift.date}T${session.check_out}:00`,
})

const submitSingleSession = (session) => {
  if (!session.note || session.note.trim() === '') return 
  
  emit('submit', createPayload(session), () => {
    // Optional: Hier könntest du isSubmitted nur auf true setzen,
    // wenn du nach JEDEM Klick die Erfolgsmeldung sehen willst.
    // Falls das Modal offen bleiben soll für weitere Änderungen, 
    // setzen wir es hier NICHT auf true, sondern aktualisieren nur den Status.
    session.isPending = true 
  })
}

const handleClose = () => {
  emit('close')
  setTimeout(() => {
    if (!props.isOpen) isSubmitted.value = false
  }, 300)
}


onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
})

const resetSession = (index) => {
  const session = localSessions.value[index]
  if (!session) return
  
  // Wenn es eine Neuanlage war, setzen wir auf Standardwerte zurück
  if (!session.id) {
    session.check_in = '08:00'
    session.check_out = '16:00'
  } else {
    session.check_in = session.orig_check_in
    session.check_out = session.orig_check_out
  }
  session.note = ''
}

const handleWithdraw = (session) => {
  if (confirm('Möchtest du diesen Korrekturantrag wirklich löschen?')) {
    // Wir senden die session.id an das Parent
    emit('withdraw', session.id, () => {
      // Das ist der Callback, der nach erfolgreichem API-Call 
      // den lokalen UI-Zustand im Modal "säubert"
      session.isPending = false
      session.note = ''
      session.check_in = session.orig_check_in
      session.check_out = session.orig_check_out
    })
  }
}




defineExpose({ isSubmitted })
</script>



<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div v-if="isOpen" class="fixed inset-0 z-[10000] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="handleClose" />
        
        <div class="relative bg-white rounded-[2.0rem] shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh] overflow-hidden">
          
          <div v-if="isSubmitted" class="p-8 text-center space-y-6">
            <div class="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-3xl flex items-center justify-center mx-auto">
              <CheckCircle2 class="w-10 h-10" />
            </div>
            <h2 class="text-2xl font-bold text-slate-900">Änderungen gespeichert</h2>
            <button class="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold" @click="handleClose">Schließen</button>
          </div>

          <template v-else>
            <div class="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div class="flex items-center gap-3">
                <div class="p-2 bg-blue-100 rounded-xl text-blue-600"><Clock class="w-5 h-5" /></div>
                <div>
                  <h2 class="text-base font-bold text-slate-900">Zeiten korrigieren</h2>
                  <p class="text-[10px] text-slate-500 font-medium">{{ displayDate }}</p>
                </div>
              </div>
              <button @click="handleClose" aria-label="Fenster schließen" class="p-2 text-slate-300 hover:text-slate-600 rounded-full transition-all">
                <X class="w-6 h-6" />
              </button>
            </div>
            
            <div class="overflow-y-auto p-5 space-y-4 scrollbar-hide">
              <div class="space-y-4">
                <div v-for="(session, index) in localSessions" :key="session.id" 
                  class="p-4 border border-slate-100 rounded-[2rem] bg-white shadow-sm space-y-3 transition-all"
                  :class="{ 'ring-1 ring-amber-400 border-amber-100 bg-amber-50/5': session.isPending }"
                >
                  <div class="flex justify-between items-center px-1">
                    <span class="text-[9px] font-black uppercase tracking-wider text-slate-400">Eintrag #{{ index + 1 }}</span>
                    
                    <div class="flex items-center gap-3">
                      <button 
                        v-if="session.check_in !== session.orig_check_in || session.check_out !== session.orig_check_out"
                        @click="resetSession(index)"
                        class="text-[9px] font-bold text-blue-500 hover:text-blue-700 flex items-center gap-1"
                      >
                        <RotateCcw class="w-2.5 h-2.5" /> Zurücksetzen
                      </button>

                      <span v-if="session.isPending" class="text-[9px] font-bold text-amber-600 bg-amber-100/50 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <Clock class="w-2.5 h-2.5" /> Offen
                      </span>
                    </div>
                  </div>

                  <div class="grid grid-cols-2 gap-3">
                    <div v-for="type in ['in', 'out']" :key="type" class="space-y-1">
                      <div class="flex justify-between items-center px-1">
                        <label class="text-[9px] font-bold uppercase text-slate-400">{{ type === 'in' ? 'Beginn' : 'Ende' }}</label>
                        <span class="text-[9px] text-slate-400 tabular-nums">Original: {{ type === 'in' ? session.orig_check_in : session.orig_check_out }}</span>
                      </div>
                      <input type="time" v-model="localSessions[index][type === 'in' ? 'check_in' : 'check_out']" :disabled="isLoading" 
                        class="w-full px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/10 outline-none"
                        :class="{ 'text-blue-600 font-bold border-blue-200 bg-blue-50/30': localSessions[index][type === 'in' ? 'check_in' : 'check_out'] !== (type === 'in' ? session.orig_check_in : session.orig_check_out) }">
                    </div>
                  </div>

                  <div class="space-y-2">
                    <textarea 
                      v-model="localSessions[index].note" 
                      :disabled="isLoading"
                      rows="2" 
                      class="w-full px-4 py-2.5 bg-slate-50 border border-slate-100 rounded-xl text-xs outline-none focus:ring-2 focus:ring-blue-500/10 resize-none transition-all"
                      placeholder="Grund der Änderung?"
                    ></textarea>

                    <div class="flex flex-col gap-2">
  
  <template v-if="session.isPending">
    <button 
      @click="submitSingleSession(session)"
      :disabled="isLoading || !session.note || (session.check_in === session.orig_check_in && session.check_out === session.orig_check_out)"
      class="w-full py-2.5 rounded-xl font-bold text-[11px] bg-amber-500 text-white shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-20"
    >
      <component :is="isLoading ? 'Loader2' : CheckCircle2" class="w-3 h-3" :class="{ 'animate-spin': isLoading }" />
      Aktualisieren
    </button>

    <button 
      @click="handleWithdraw(session)"
      :disabled="isLoading"
      class="w-full py-2.5 rounded-xl font-bold text-[11px] bg-red-50 text-red-600 border border-red-100 hover:bg-red-100 transition-all flex items-center justify-center gap-2"
    >
      <Trash2 class="w-3 h-3" />
      Antrag zurückziehen (Löschen)
    </button>
  </template>

  <div v-else-if="session.old_ver_exists" class="flex items-center gap-2 p-2.5 bg-slate-50 rounded-xl border border-slate-100">
    <AlertCircle class="w-3.5 h-3.5 text-slate-400 shrink-0" />
    <span class="text-[10px] text-slate-500 font-medium leading-tight">Diese Session wurde bereits finalisiert und kann nicht mehr korrigiert werden.</span>
  </div>

  <button 
    v-else
    @click="submitSingleSession(session)"
    :disabled="isLoading || !session.note || (session.check_in === session.orig_check_in && session.check_out === session.orig_check_out)"
    class="w-full py-2.5 rounded-xl font-bold text-[11px] bg-slate-900 text-white shadow-lg shadow-slate-900/20 transition-all flex items-center justify-center gap-2 disabled:opacity-20 disabled:shadow-none"
  >
    <component :is="isLoading ? 'Loader2' : Clock" class="w-3 h-3" :class="{ 'animate-spin': isLoading }" />
    Korrektur senden
  </button>

</div>
                  </div>
                </div>
              </div>

              <!-- Bereich für leere Liste / Button zum Hinzufügen -->
              <div v-if="!localSessions.length" class="py-10 flex flex-col items-center justify-center space-y-4">
                <div class="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center text-slate-200">
                  <FileText class="w-8 h-8" />
                </div>
                <div class="text-center">
                  <p class="text-xs font-bold text-slate-400">Keine Arbeitszeiten erfasst</p>
                  <p class="text-[10px] text-slate-300">Systemausfall oder vergessen zu stempeln?</p>
                </div>
                
                <button 
                  @click="addManualSession"
                  class="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-bold text-[11px] shadow-lg shadow-blue-600/20 hover:bg-blue-700 transition-all flex items-center gap-2"
                >
                  <Plus class="w-3.5 h-3.5" />
                  Zeit nachträglich melden
                </button>
              </div>

              <!-- Optionale Ergänzung: Button auch anzeigen, wenn schon Sessions da sind (unten drunter) -->
              <div v-else-if="!isManualAdding" class="pt-2 pb-4">
                <button 
                  @click="addManualSession"
                  class="w-full py-3 border-2 border-dashed border-slate-100 rounded-2xl text-slate-400 text-[10px] font-bold hover:border-blue-200 hover:text-blue-500 transition-all flex items-center justify-center gap-2"
                >
                  <Plus class="w-3 h-3" /> Weiteren Zeitraum hinzufügen
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>