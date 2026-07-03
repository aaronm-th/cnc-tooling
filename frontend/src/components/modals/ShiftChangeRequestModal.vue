<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { X, Clock, MessageSquare, AlertCircle, CheckCircle2, RotateCcw, Trash2, Plus, FileText, HelpCircle } from 'lucide-vue-next'
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

const onKeyDown = (e) => {
  if (e.key === 'Escape' && props.isOpen) handleClose()
}

const addManualSession = () => {
  localSessions.value.push({
    id: null,
    check_in: '08:00',
    check_out: '16:00',
    orig_check_in: null,
    orig_check_out: null,
    note: '',
    isPending: false,
    isNew: true
  })
}

watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    window.addEventListener('keydown', onKeyDown)
    isSubmitted.value = false
    
    if (props.shift?.sessions) {
      localSessions.value = props.shift.sessions.map(session => {
        // Da das Backend ein Objekt liefert, greifen wir direkt darauf zu (ohne [0])
        const pendingData = session.pending_requests
        const hasPending = !!pendingData
        
        const defaultCheckIn = session.check_in || '08:00'
        const defaultCheckOut = session.check_out || '16:00'

        return {
          id: session.id,
          change_request_id: pendingData?.id || null,
          check_in: formatTimeForInput(pendingData?.requested_check_in || defaultCheckIn),
          check_out: formatTimeForInput(pendingData?.requested_check_out || defaultCheckOut),
          orig_check_in: session.check_in ? formatTimeForInput(session.check_in) : null,
          orig_check_out: session.check_out ? formatTimeForInput(session.check_out) : null,
          note: pendingData?.employee_note || '',
          isPending: hasPending,
          pending_details: hasPending ? {
            check_in: formatTimeForInput(pendingData.requested_check_in),
            check_out: formatTimeForInput(pendingData.requested_check_out)
          } : null
        }
      })
    }
  } else {
    window.removeEventListener('keydown', onKeyDown)
    localSessions.value = []
  }
}, { immediate: true })

const createPayload = (session) => {
  const payload = {
    workday_id: props.shift.id,
    worksession_id: session.orig_check_in ? session.id : null,
    employee_note: session.note,
    requested_check_in: `${props.shift.date}T${session.check_in}:00`,
    requested_check_out: `${props.shift.date}T${session.check_out}:00`,
  }

  if (!session.orig_check_in && session.change_request_id) {
    payload.id = session.change_request_id
  }

  return payload
}

const submitSingleSession = (session) => {
  if (!session.note || session.note.trim() === '') return 
  emit('submit', createPayload(session), () => {
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
  if (!session.id) {
    session.check_in = '08:00'
    session.check_out = '16:00'
  } else {
    session.check_in = session.orig_check_in
    session.check_out = session.orig_check_out
  }
  session.note = ''
}

// Erweitert um den index, um lokale Einträge direkt entfernen zu können
const handleWithdraw = (session, index) => {
  if (confirm('Möchtest du diesen Korrekturantrag wirklich löschen?')) {
    if (!session.id && !session.isPending) {
      localSessions.value.splice(index, 1)
      return
    }

    const targetId = session.id ? session.id : session.change_request_id

    if (!targetId) {
      console.error("Keine gültige ID zum Löschen gefunden.");
      return;
    }

    emit('withdraw', targetId, () => {
      session.isPending = false
      session.note = ''
      session.check_in = session.orig_check_in
      session.check_out = session.orig_check_out
      session.pending_details = null
      
      if (!session.id) {
        localSessions.value.splice(index, 1)
      }
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
                <div v-for="(session, index) in localSessions" :key="session.id || index" 
                  class="p-4 border border-slate-100 rounded-[2rem] bg-white shadow-sm space-y-3 transition-all"
                  :class="{ 'ring-1 ring-amber-400 border-amber-100 bg-amber-50/5': session.isPending }"
                >
                  <div class="flex justify-between items-center px-1">
                    <span class="text-[9px] font-black uppercase tracking-wider text-slate-400">
                      {{ session.id ? `Eintrag #${index + 1}` : 'Nachträgliche Meldung' }}
                    </span>
                    
                    <div class="flex items-center gap-3">
                      <button 
                        v-if="session.check_in !== session.orig_check_in || session.check_out !== session.orig_check_out"
                        @click="resetSession(index)"
                        class="text-[9px] font-bold text-blue-500 hover:text-blue-700 flex items-center gap-1"
                      >
                        <RotateCcw class="w-2.5 h-2.5" /> Zurücksetzen
                      </button>

                      <span v-if="session.isPending" class="text-[9px] font-bold text-amber-600 bg-amber-100/50 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <Clock class="w-2.5 h-2.5" /> Antrag läuft
                      </span>
                    </div>
                  </div>

                  <!-- NEU: Visueller Hinweis auf bereits beantragte Zeiten innerhalb der Card -->
                  <div v-if="session.isPending && session.pending_details" class="p-2.5 bg-amber-50 rounded-xl border border-amber-100/70 flex items-start gap-2 text-[10px] text-amber-800">
                    <HelpCircle class="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                    <div>
                      <span class="font-bold">Aktuell beantragt:</span> 
                      <span class="tabular-nums ml-1">{{ session.pending_details.check_in }} - {{ session.pending_details.check_out }} Uhr</span>
                      <p class="text-[9px] text-amber-600/80 mt-0.5">Du kannst den bestehenden Antrag unten überschreiben oder komplett zurückziehen.</p>
                    </div>
                  </div>

                  <div class="grid grid-cols-2 gap-3">
                    <div v-for="type in ['in', 'out']" :key="type" class="space-y-1">
                      <div class="flex justify-between items-center px-1">
                        <label class="text-[9px] font-bold uppercase text-slate-400">{{ type === 'in' ? 'Beginn' : 'Ende' }}</label>
                        <span v-if="session.id" class="text-[9px] text-slate-400 tabular-nums">Original: {{ type === 'in' ? session.orig_check_in : session.orig_check_out }}</span>
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
                          :disabled="isLoading || !session.note"
                          class="w-full py-2.5 rounded-xl font-bold text-[11px] bg-amber-500 text-white shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-20"
                        >
                          <component :is="isLoading ? 'Loader2' : CheckCircle2" class="w-3 h-3" :class="{ 'animate-spin': isLoading }" />
                          Antrag aktualisieren
                        </button>

                        <button 
                          @click="handleWithdraw(session, index)"
                          :disabled="isLoading"
                          class="w-full py-2.5 rounded-xl font-bold text-[11px] bg-red-50 text-red-600 border border-red-100 hover:bg-red-100 transition-all flex items-center justify-center gap-2"
                        >
                          <Trash2 class="w-3 h-3" /> Antrag zurückziehen (Löschen)
                        </button>
                      </template>


                      <button 
                        v-else
                        @click="submitSingleSession(session)"
                        :disabled="isLoading || !session.note || (session.id && session.check_in === session.orig_check_in && session.check_out === session.orig_check_out)"
                        class="w-full py-2.5 rounded-xl font-bold text-[11px] bg-slate-900 text-white shadow-lg shadow-slate-900/20 transition-all flex items-center justify-center gap-2 disabled:opacity-20 disabled:shadow-none"
                      >
                        <component :is="isLoading ? 'Loader2' : Clock" class="w-3 h-3" :class="{ 'animate-spin': isLoading }" />
                        Korrektur senden
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="!localSessions.length" class="py-10 flex flex-col items-center justify-center space-y-6">
                <div class="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center text-slate-200">
                  <FileText class="w-8 h-8" />
                </div>
                <div class="text-center space-y-1">
                  <p class="text-xs font-bold text-slate-400">Keine Arbeitszeiten erfasst</p>
                  <p class="text-[10px] text-slate-300">Systemausfall oder vergessen zu stempeln?</p>
                </div>
                
                <button 
                  @click="addManualSession"
                  class="w-full py-6 border-2 border-dashed border-slate-200 rounded-2xl text-slate-400 font-bold hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50 transition-all flex items-center justify-center gap-2 group cursor-pointer text-xs"
                >
                  <Plus class="w-5 h-5 group-hover:scale-110 transition-transform" />
                  Zeit nachträglich melden
                </button>
              </div>

              <div v-else class="pt-2 pb-4">
                <button 
                  @click="addManualSession"
                  class="w-full py-6 border-2 border-dashed border-slate-200 rounded-2xl text-slate-400 font-bold hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50 transition-all flex items-center justify-center gap-2 group cursor-pointer text-xs"
                >
                  <Plus class="w-5 h-5 group-hover:scale-110 transition-transform" /> 
                  Weiteren Zeitraum hinzufügen
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>