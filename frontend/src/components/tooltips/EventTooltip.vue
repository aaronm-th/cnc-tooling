<script setup>
import { Calendar, AlertTriangle, Clock } from 'lucide-vue-next'
import { useEventStyles } from '@/composables/useEventStyles'

defineProps({
  event: {
    type: Object,
    default: null
  },
  styles: {
    type: Object,
    default: () => ({})
  },
  arrowStyle: {
    type: Object,
    default: () => ({})
  }
})

const { getIconColorClass, getEventIcon } = useEventStyles()
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div 
        v-if="event"
        :style="styles"
        class="w-64 p-4 bg-slate-900 text-white rounded-2xl shadow-2xl pointer-events-none space-y-3"
      >
        <!-- Header (Name & Event-Typ) -->
        <div class="flex items-center gap-2">
          <div :class="['p-1.5 rounded-lg bg-white/10', getIconColorClass(event.type)]">
            <component :is="getEventIcon(event.type)" class="w-4 h-4" />
          </div>
          <div class="flex flex-col min-w-0">
            <span v-if="event.userName" class="text-[11px] font-medium text-slate-200 leading-tight truncate">
              {{ event.userName }}
            </span>
            <span class="font-bold uppercase tracking-widest text-[9px] opacity-60">
              {{ event.title }}
            </span>
          </div>
        </div>

        <!-- Warnmeldung (z. B. Auto-Checkout) -->
        <div 
          v-if="event.warning" 
          class="flex items-start gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px]"
        >
          <AlertTriangle class="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span class="leading-tight font-medium">{{ event.warning }}</span>
        </div>

        <!-- Inhaltsbereich (Sessions & Notiz) -->
        <div 
          v-if="(event.sessions && event.sessions.length > 0) || event.note"
          class="max-h-40 overflow-y-auto custom-scrollbar pr-1 space-y-2 border-t border-white/10 pt-2"
        >
          <!-- Einzelne Check-in / Check-out Zeiten -->
          <div v-if="event.sessions && event.sessions.length > 0" class="space-y-1">
            <div 
              v-for="(session, sIdx) in event.sessions" 
              :key="sIdx"
              class="text-slate-300 text-[11px] flex items-center gap-2"
            >
              <div class="w-1.5 h-1.5 rounded-full bg-blue-400/50 shrink-0"></div>
              <span class="leading-tight">{{ session }}</span>
            </div>
          </div>

          <!-- Freitext-Bemerkung -->
          <div 
            v-if="event.note" 
            class="text-slate-400 text-[11px] italic leading-relaxed pt-1"
          >
            {{ event.note }}
          </div>
        </div>

        <!-- Gesamtzeit -->
        <div 
          v-if="event.sessions && event.totalHours !== undefined && event.totalHours !== null" 
          class="flex items-center justify-between text-blue-400 font-semibold text-[11px] pt-2 border-t border-white/10"
        >
          <span class="flex items-center gap-1.5 text-slate-400 font-normal">
            <Clock class="w-3 h-3 text-blue-400" /> Gesamtzeit:
          </span>
          <span>{{ event.totalHours }} Std.</span>
        </div>

        <!-- Footer (Datum) -->
        <div class="pt-2 border-t border-white/5 flex items-center gap-2 text-[10px] text-slate-400">
          <Calendar class="w-3 h-3" />
          <span class="capitalize">
            {{ new Date(event.date).toLocaleDateString('de-DE', { weekday: 'long', month: 'short', day: 'numeric' }) }}
          </span>
        </div>
        
        <!-- Pfeil -->
        <div 
          :style="arrowStyle"
          :class="[
            'absolute border-8 border-transparent transition-all duration-200',
            event.index < 7 ? 'bottom-full border-b-slate-900' : 'top-full border-t-slate-900',
            Object.keys(arrowStyle).length === 0 ? (event.index % 7 === 0 ? 'left-4' : (event.index % 7 === 6 ? 'right-4' : 'left-1/2 -translate-x-1/2')) : ''
          ]"
        ></div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 2px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
}
</style>