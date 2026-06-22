<script setup>
import { computed } from 'vue' // <-- Wichtig: computed importieren
import { X, Calendar, Clock, Info, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { useEventStyles } from '@/composables/useEventStyles'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  event: {
    type: Object,
    default: null
  }
})

defineEmits(['close'])

const { getEventIcon, getIconColorClass } = useEventStyles()

// NEU: Sicherstellen, dass wir ein Date-Objekt haben
const formattedDate = computed(() => {
  if (!props.event?.date) return ''
  
  // Wenn es ein String ist, in Date umwandeln, sonst direkt nutzen
  const dateObj = typeof props.event.date === 'string' 
    ? new Date(props.event.date) 
    : props.event.date

  return dateObj.toLocaleDateString('de-DE', { // 'de-DE' für deutsches Format
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
})

const getStatusLabel = (status) => {
  const labels = {
    approved: 'Genehmigt',
    pending: 'Ausstehend',
    rejected: 'Abgelehnt',
    cancelled: 'Storniert'
  }
  return labels[status] || 'Aktiv'
}

const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'approved': return 'bg-emerald-100 text-emerald-700'
    case 'pending': return 'bg-amber-100 text-amber-700'
    case 'rejected': return 'bg-red-100 text-red-700'
    default: return 'bg-slate-100 text-slate-600'
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
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[10000] flex items-center justify-center p-4"
      >
        <div
          class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
          @click="$emit('close')"
        />
        
        <div class="relative bg-white rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden animate-in fade-in zoom-in duration-300">
          <div class="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div class="flex items-center gap-3">
              <div :class="['p-2 rounded-xl', getIconColorClass(event?.type)]">
                <component
                  :is="getEventIcon(event?.type)"
                  class="w-5 h-5"
                />
              </div>
              <h2 class="text-lg font-bold text-slate-900">
                Event Details
              </h2>
            </div>
            <button
              class="p-2 text-slate-400 hover:text-slate-600 hover:bg-white rounded-full transition-all"
              @click="$emit('close')"
            >
              <X class="w-5 h-5" />
            </button>
          </div>
          
          <div class="p-6 space-y-6">
            <div class="space-y-4">
              <div>
                <h3 class="text-xl font-bold text-slate-900">
                  {{ event?.title }}
                </h3>
                <div 
                  v-if="event?.status" 
                  class="mt-2 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                  :class="getStatusBadgeClass(event.status)"
                >
                  <component 
                    :is="event.status === 'approved' ? CheckCircle2 : (event.status === 'pending' ? Clock : AlertCircle)" 
                    class="w-3 h-3" 
                  />
                  {{ getStatusLabel(event.status) }}
                </div>
              </div>

              <div class="space-y-3">
                <div class="flex items-center gap-3 text-slate-600">
                  <div class="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400">
                    <Calendar class="w-4 h-4" />
                  </div>
                    <div class="text-sm font-medium">
                    {{ formattedDate }}
                    </div>
                </div>

                <div 
                    v-if="event?.note && event.note.length > 0 && event.note !== '[]'" 
                    class="flex items-start gap-3 text-slate-600"
                    >
                    <div class="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400 shrink-0">
                        <Info class="w-4 h-4" />
                    </div>
                    <div class="text-sm font-medium pt-1 italic">
                        {{ Array.isArray(event.note) ? event.note[0] : event.note }}
                    </div>
                </div>
              </div>
            </div>

            <button 
              class="w-full py-3.5 px-4 bg-slate-100 text-slate-700 rounded-xl text-sm font-bold hover:bg-slate-200 transition-all"
              @click="$emit('close')"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
