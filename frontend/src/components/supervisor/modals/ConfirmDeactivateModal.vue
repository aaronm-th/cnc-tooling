<script setup>
import { X, UserX } from 'lucide-vue-next'

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

const emit = defineEmits(['close', 'confirm'])

const handleConfirm = () => {
  emit('confirm')
}
</script>

<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200"
  >
    <div class="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-200">
      
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 class="font-bold text-lg text-slate-900">
          Mitarbeiter deaktivieren
        </h3>
        <button 
          type="button"
          class="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          @click="emit('close')"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="p-6 space-y-6">
        <div class="flex items-start gap-4">
          <div class="w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center text-red-600 shrink-0 border border-red-100/50">
            <UserX class="w-6 h-6" />
          </div>
          <div class="space-y-1.5">
            <p class="text-sm text-slate-600 leading-relaxed">
              Bist du sicher, dass du <strong class="text-slate-900 font-bold">{{ member?.name }}</strong> inaktiv setzen möchtest?
            </p>
            <p class="text-xs text-slate-400 leading-relaxed">
              Der Zugriff auf das System wird für diesen Account gesperrt. Die Stammdaten und historischen Zeiteinträge bleiben jedoch im System erhalten.
            </p>
          </div>
        </div>

        <div class="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
          <button 
            type="button" 
            class="px-4 py-2 hover:bg-slate-100 rounded-xl text-slate-500 text-sm font-bold transition-all cursor-pointer"
            @click="emit('close')"
          >
            Abbrechen
          </button>
          <button 
            type="button"
            @click="handleConfirm"
            class="px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded-xl text-sm font-bold transition-all shadow-lg shadow-red-900/20 cursor-pointer"
          >
            Inaktiv setzen
          </button>
        </div>
      </div>

    </div>
  </div>
</template>