<script setup>
import { ref, watch, computed } from 'vue'
import { X, Calendar, Loader2, AlertCircle } from 'lucide-vue-next'
import { useEventStyles } from '@/composables/useEventStyles'
import { useScheduleStore } from '@/stores/scheduleStore'

const props = defineProps({
  isOpen: { type: Boolean, required: true },
  initialData: { type: Object, default: null },
  leaveTypes: { type: Array, required: true }
})

const emit = defineEmits(['close', 'success'])
const { getEventIcon, getActiveStyles } = useEventStyles()
const scheduleStore = useScheduleStore()

const isSubmitting = ref(false)
const backendErrors = ref(null)

const leaveForm = ref({
  startDate: new Date().toISOString().split('T')[0],
  endDate: new Date().toISOString().split('T')[0],
  type: 'vacation',
  note: ''
})

// Dynamische Fehlerextraktion (Bleibt aktiv für die Infobox)
const errorMessage = computed(() => {
  if (!backendErrors.value) return null
  if (typeof backendErrors.value === 'string') return backendErrors.value

  const extractFirstError = (obj) => {
    if (typeof obj === 'string') return obj
    if (Array.isArray(obj)) {
      for (const item of obj) {
        const found = extractFirstError(item)
        if (found) return found
      }
    } else if (obj && typeof obj === 'object') {
      if (obj.non_field_errors) return extractFirstError(obj.non_field_errors)
      if (obj.detail) return extractFirstError(obj.detail)
      for (const key in obj) {
        const found = extractFirstError(obj[key])
        if (found) return found
      }
    }
    return null
  }
  return extractFirstError(backendErrors.value) || 'Validierungsfehler aufgetreten.'
})

const isOnlyWeekend = computed(() => {
  const start = new Date(leaveForm.value.startDate)
  const end = new Date(leaveForm.value.endDate)
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const day = d.getDay()
    if (day !== 0 && day !== 6) return false
  }
  return true
})

const defaultLeaveType = computed(() => props.leaveTypes?.[0]?.id || 'vacation')

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    backendErrors.value = null

    if (props.initialData) {
      leaveForm.value = {
        startDate: props.initialData.leave_start || props.initialData.startDate,
        endDate: props.initialData.leave_end || props.initialData.endDate,
        type: props.initialData.leave_type || props.initialData.type || defaultLeaveType.value,
        note: props.initialData.note || ''
      }
    } else {
      leaveForm.value = {
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
        type: defaultLeaveType.value,
        note: ''
      }
    }
  }
})

watch(() => leaveForm.value.startDate, (newStartDate, oldStartDate) => {
  if (leaveForm.value.endDate === oldStartDate || leaveForm.value.endDate < newStartDate) {
    leaveForm.value.endDate = newStartDate
  }
})

watch(leaveForm, () => { backendErrors.value = null }, { deep: true })

const handleSubmit = async () => {
  isSubmitting.value = true
  backendErrors.value = null

  const payload = {
    leave_type: leaveForm.value.type,
    leave_start: leaveForm.value.startDate,
    leave_end: leaveForm.value.endDate,
    note: leaveForm.value.note
  }

  try {
    // Das Modal kennt initialData bereits -> entscheidet selbst Create vs. Update.
    if (props.initialData?.id) {
      await scheduleStore.updateLeaveRequest(props.initialData.id, payload)
    } else {
      await scheduleStore.createLeaveRequest(payload)
    }

    emit('success')
    emit('close')
  } catch (error) {
    console.error("Fehler beim Speichern des Antrags:", error)
    backendErrors.value = error.response?.data || "Verbindung zum Server fehlgeschlagen."
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
                <Calendar class="w-5 h-5 text-blue-600" />
              </div>
              <h2 class="text-xl font-bold text-slate-900">
                {{ initialData ? 'Antrag bearbeiten' : 'Abwesenheit planen' }}
              </h2>
            </div>
            <button @click="$emit('close')" :disabled="isSubmitting" class="p-2 text-slate-400 hover:text-slate-600 rounded-full transition-all">
              <X class="w-5 h-5" />
            </button>
          </div>
          
          <form @submit.prevent="handleSubmit" class="p-6 space-y-6">
            <div class="space-y-4">
              <div class="space-y-2">
                <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Typ</label>
                <div class="grid grid-cols-2 gap-2">
                  <button 
                    v-for="type in leaveTypes" 
                    :key="type.id"
                    type="button"
                    @click="leaveForm.type = type.id"
                    :disabled="isSubmitting"
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
                    :disabled="isSubmitting" 
                    class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                  />
                </div>
                <div class="space-y-2">
                  <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Ende</label>
                  <input 
                    v-model="leaveForm.endDate" 
                    type="date" 
                    :min="leaveForm.startDate"
                    :disabled="isSubmitting" 
                    class="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-medium" 
                  />
                </div>
              </div>

              <Transition
                enter-active-class="transition duration-200 ease-out"
                enter-from-class="opacity-0 -translate-y-2"
                enter-to-class="opacity-100 translate-y-0"
              >
                <div v-if="errorMessage" class="p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-start gap-3">
                  <AlertCircle class="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                  <div>
                    <p class="text-xs text-rose-900 font-bold leading-tight">Antrag ungültig</p>
                    <p class="text-[10px] text-rose-700 mt-1 leading-relaxed">
                      {{ errorMessage }}
                    </p>
                  </div>
                </div>
              </Transition>

              <div class="space-y-2">
                <label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1">Grund / Notiz</label>
                <textarea 
                  v-model="leaveForm.note" 
                  rows="3" 
                  :disabled="isSubmitting" 
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
                :disabled="isSubmitting" 
                class="flex-1 py-3.5 bg-slate-100 text-slate-600 rounded-xl text-sm font-bold hover:bg-slate-200 transition-all"
              >
                Abbrechen
              </button>
              <button 
                type="submit" 
                :disabled="isSubmitting || isOnlyWeekend" 
                class="flex-1 py-3.5 px-4 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2"
                :class="[
                  isOnlyWeekend 
                    ? 'bg-slate-200 text-slate-400 cursor-not-allowed' 
                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/20'
                ]"
              >
                <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
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