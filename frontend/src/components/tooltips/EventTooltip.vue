<script setup>
import { Calendar } from 'lucide-vue-next'
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
        class="w-64 p-4 bg-slate-900 text-white rounded-2xl shadow-2xl pointer-events-none"
      >
        <div class="flex items-center gap-2 mb-2">
          <div :class="['p-1.5 rounded-lg bg-white/10', getIconColorClass(event.type)]">
            <component :is="getEventIcon(event.type)" class="w-4 h-4" />
          </div>
          <span class="font-bold uppercase tracking-widest text-[10px] opacity-60">
            {{ event.title }}
          </span>
        </div>

        <div v-if="event.note" class="h-px bg-white/10 my-2"></div>
        
        <div v-if="event.note" class="max-h-40 overflow-y-auto custom-scrollbar pr-2 space-y-2">
          <template v-if="event.type === 'work'">
            <div 
              v-for="(line, sIdx) in (Array.isArray(event.note) ? event.note : event.note.split('|'))" 
              :key="sIdx" 
            >
              <div 
                v-if="line.startsWith('TOTAL:')" 
                class="text-blue-400 font-semibold text-[11px] mt-2 pt-1 border-t border-white/10"
              >
                {{ line.replace('TOTAL:', '').trim() }}
              </div>

              <div 
                v-else 
                class="text-slate-300 text-[11px] flex items-start gap-2 mb-1"
              >
                <div class="w-1.5 h-1.5 rounded-full bg-blue-400/50 mt-1 shrink-0"></div>
                <span class="leading-tight">{{ line.trim() }}</span>
              </div>
            </div>
          </template>

          <p v-else class="text-slate-300 text-[11px] leading-relaxed italic">
            {{ Array.isArray(event.note) ? event.note[0] : event.note }}
          </p>
        </div>

        <div class="mt-3 pt-3 border-t border-white/5 flex items-center gap-2 text-[10px] text-slate-400">
          <Calendar class="w-3 h-3" />
          <span class="capitalize">
            {{ new Date(event.date).toLocaleDateString('de-DE', { weekday: 'long', month: 'short', day: 'numeric' }) }}
          </span>
        </div>
        
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
  background: rgba(255, 255, 255, 0.2); /* Leicht transparentes Weiß passend zum Dark-Theme */
  border-radius: 10px;
}
</style>