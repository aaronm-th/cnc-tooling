<script setup>
import { ref, watch, computed } from 'vue'
import { X, Calendar, Loader2, AlertCircle } from 'lucide-vue-next'
import { useEventStyles } from '@/composables/useEventStyles'

const props = defineProps({
  isOpen: { type: Boolean, required: true },
  isLoading: { type: Boolean, default: false },
  leaveTypes: { type: Array, required: true },
  // Adding initialData support from your first snippet
  initialData: { type: Object, default: null }
})

const emit = defineEmits(['close', 'submit'])
const { getEventIcon, getActiveStyles } = useEventStyles()

const leaveForm = ref({
  startDate: new Date().toISOString().split('T')[0],
  endDate: new Date().toISOString().split('T')[0],
  type: 'vacation',
  note: ''
})

const isWeekend = (dateString) => {
  const day = new Date(dateString).getDay()
  return day === 0 || day === 6
}

// Computed: Prüft ob der Zeitraum nur aus Wochenenden besteht
const isOnlyWeekend = computed(() => {
  const start = new Date(leaveForm.value.startDate)
  const end = new Date(leaveForm.value.endDate)
  
  // Wir laufen vom Start- zum Enddatum
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const day = d.getDay()
    // Wenn wir EINEN Tag finden, der kein Wochenende ist (1-5), ist der Antrag valide
    if (day !== 0 && day !== 6) {
      return false
    }
  }
  return true
})

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    if (props.initialData) {
      // Map backend fields back to form if editing
      leaveForm.value = {
        startDate: props.initialData.leave_start || props.initialData.startDate,
        endDate: props.initialData.leave_end || props.initialData.endDate,
        type: props.initialData.leave_type || props.initialData.type,
        note: props.initialData.note || ''
      }
    } else {
      // Reset for new request
      leaveForm.value = {
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
        type: props.leaveTypes[0]?.id || 'vacation',
        note: ''
      }
    }
  }
})

// 2. Smart Date Logic: Automatically adjust end date
watch(() => leaveForm.value.startDate, (newStartDate, oldStartDate) => {
  // If end date was aligned with old start, or is now invalid (before start), move it forward
  if (leaveForm.value.endDate === oldStartDate || leaveForm.value.endDate < newStartDate) {
    leaveForm.value.endDate = newStartDate
  }
})

const handleSubmit = () => {
  // Keeping your functional mapping for the backend
  emit('submit', { 
    leave_type: leaveForm.value.type,
    leave_start: leaveForm.value.startDate,
    leave_end: leaveForm.value.endDate,
    note: leaveForm.value.note
  })
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
        <div @click="!isLoading && $emit('close')" class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"></div>
        
        <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-300">
          <div class="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-blue-100 rounded-xl">
                <Calendar class="w-5 h-5 text-blue-600" />
              </div>
              <h2 class="text-xl font-bold text-slate-900">
                {{ initialData ? 'Antrag bearbeiten' : 'Abwesenheit planen' }}
              </h2>
            </div>
            <button @click="$emit('close')" :disabled="isLoading" class="p-2 text-slate-400 hover:text-slate-600 rounded-full transition-all">
              <X class="w-5 h-5" />
            </button>
          </div>
          
          <form @submit.prevent="handleSubmit" class="p-6 space-y-6">
            <div class="space-y-4">
              <div class="space-y-2">
                <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Typ</label>
                <div class="grid grid-cols-3 gap-2">
                  <button 
                    v-for="type in leaveTypes" 
                    :key="type.id"
                    type="button"
                    @click="leaveForm.type = type.id"
                    :disabled="isLoading"
                    :class="[
                      'px-3 py-4 rounded-2xl text-[10px] transition-all border-2 flex flex-col items-center gap-3 uppercase tracking-tight',
                      leaveForm.type === type.id 
                        ? getActiveStyles(type.id) 
                        : 'bg-slate-50 border-transparent text-slate-500 opacity-60 hover:opacity-100'
                    ]"
                  >
                    <div :class="['p-2 rounded-xl transition-all', leaveForm.type === type.id ? 'bg-white shadow-sm' : 'bg-slate-200/50 text-slate-400']">
                      <component :is="getEventIcon(type.id)" class="w-5 h-5" />
                    </div>
                    {{ type.name }}
                  </button>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                  <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Beginn</label>
                  <input 
                    v-model="leaveForm.startDate" 
                    type="date" 
                    :disabled="isLoading" 
                    class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                  />
                </div>
                <div class="space-y-2">
                  <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Ende</label>
                  <input 
                    v-model="leaveForm.endDate" 
                    type="date" 
                    :min="leaveForm.startDate"
                    :disabled="isLoading" 
                    class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                  />
                </div>
              </div>

              <div class="space-y-2">
                <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Grund / Notiz</label>
                <textarea 
                  v-model="leaveForm.note" 
                  rows="3" 
                  :disabled="isLoading" 
                  class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none resize-none" 
                  placeholder="Optional..."
                ></textarea>
              </div>
            </div>

            <Transition
              enter-active-class="transition duration-200 ease-out"
              enter-from-class="opacity-0 -translate-y-2"
              enter-to-class="opacity-100 translate-y-0"
            >
              <div v-if="isOnlyWeekend" class="p-4 bg-amber-50 border border-amber-100 rounded-2xl flex items-start gap-3">
                <AlertCircle class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <p class="text-xs text-amber-900 font-bold leading-tight">Kein Arbeitstag gewählt</p>
                  <p class="text-[10px] text-amber-700 mt-1 leading-relaxed">
                    Anträge, die ausschließlich am Wochenende liegen, können nicht eingereicht werden.
                  </p>
                </div>
              </div>
            </Transition>

            <div class="flex gap-3 pt-2">
              <button 
                type="button" 
                @click="$emit('close')" 
                :disabled="isLoading" 
                class="flex-1 py-3.5 bg-slate-100 text-slate-600 rounded-xl text-sm font-bold hover:bg-slate-200 transition-all"
              >
                Abbrechen
              </button>
              <button 
                type="submit" 
                :disabled="isLoading || isOnlyWeekend" 
                class="flex-1 py-3.5 px-4 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2"
                :class="[
                  isOnlyWeekend 
                    ? 'bg-slate-200 text-slate-400 cursor-not-allowed' 
                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/20'
                ]"
              >
                <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" />
                <template v-else>
                  {{ initialData ? 'Aktualisieren' : 'Antrag senden' }}
                </template>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>