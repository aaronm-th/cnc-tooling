<script setup>
import { ref, watch } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { X, CalendarDays } from 'lucide-vue-next' // CalendarDays Icon hinzugefügt

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

const emit = defineEmits(['close'])
const adminStore = useAdminStore()

const DISPLAY_DAYS = [
  { id: '0', label: 'Mo' },
  { id: '1', label: 'Di' },
  { id: '2', label: 'Mi' },
  { id: '3', label: 'Do' },
  { id: '4', label: 'Fr' },
  { id: '5', label: 'Sa' },
  { id: '6', label: 'So' }
]

const defaultSchema = () => ({
  '0': 8, '1': 8, '2': 8, '3': 8, '4': 8, '5': 0, '6': 0
})

const form = ref({
  first_name: '',
  last_name: '',
  joined_at: '', // NEU: Eintrittsdatum (YYYY-MM-DD)
  work_days_schema: defaultSchema(),
  weekly_hours: 40,
  overtime_balance: 0,
  vacation_days_per_year: 30,
  vacation_left: 30
})




const calculateProRataVacation = (entryDateStr, yearlyDays) => {
  if (!entryDateStr) return yearlyDays
  
  const entryDate = new Date(entryDateStr)
  // Wichtig: Wir nehmen das Jahr des Eintrittsdatums, nicht das aktuelle Jahr!
  const entryYear = entryDate.getFullYear() 
  
  // Monate berechnen: 13 - Eintrittsmonat (Januar = 1, Dezember = 12)
  const monthsActive = 13 - (entryDate.getMonth() + 1)
  const proRata = (yearlyDays / 12) * monthsActive
  
  return Math.round(proRata)
}

// WATCHER: Reagiert sofort bei der Eingabe im Formular
watch(
  [() => form.value.joined_at, () => form.value.vacation_days_per_year],
  ([newEntryDate, newYearlyDays]) => {
    // Nur bei der Neuanlage eine Live-Vorschau anzeigen
    if (!props.member) {
      form.value.vacation_left = calculateProRataVacation(newEntryDate, Number(newYearlyDays) || 0)
    }
  }
)

// WATCHER : Berechnet die Wochenstunden automatisch
watch(() => form.value.work_days_schema, (newHours) => {
  if (newHours) {
    const sum = Object.values(newHours).reduce((acc, val) => acc + (Number(val) || 0), 0)
    form.value.weekly_hours = Number(sum.toFixed(2))
  }
}, { deep: true })

const populateForm = (data) => {
  // Fall 1: Modal wird mit bestehenden Mitarbeiterdaten geöffnet (Editieren)
  if (data) {
    form.value = {
      first_name: data.first_name ?? '',
      last_name: data.last_name ?? '',
      joined_at: data.joined_at ?? '',
      
      // Kopiert das Schema tief oder fällt sauber auf das Standard-Schema zurück
      work_days_schema: data.work_days_schema ? { ...data.work_days_schema } : defaultSchema(),
      
      // Typkonvertierung sichern (API-Zahlen zu JS-Zahlen)
      weekly_hours: Number(data.weekly_hours ?? 40),
      overtime_balance: Number(data.overtime_hours ?? data.overtime_balance ?? 0),
      vacation_days_per_year: Number(data.vacation_days_per_year ?? data.vacation_days ?? 30),
      vacation_left: Number(data.vacation_left ?? 30)
    }
  } 
  // Fall 2: Modal wird ohne Daten geöffnet (Neuanlage / Reset)
  else {
    const todayISO = new Date().toISOString().split('T')[0]
    form.value = {
      first_name: '',
      last_name: '',
      joined_at: todayISO, 
      work_days_schema: defaultSchema(),
      weekly_hours: 40,
      overtime_balance: 0,
      vacation_days_per_year: 30,
      vacation_left: 30
    }
  }
}

watch(() => props.isOpen, async (newIsOpen) => {
  if (newIsOpen) {
    if (props.member && props.member.id) {
      populateForm(props.member)
      try {
        await adminStore.fetchTeamMemberDetail(props.member.id)
        if (adminStore.currentMember) {
          populateForm(adminStore.currentMember)
        }
      } catch (error) {
        console.error("Fehler beim asynchronen Nachladen der Mitarbeiterdetails:", error)
      }
    } else {
      populateForm(null)
    }
  }
}, { immediate: true })

const handleSubmit = async () => {
  if (!form.value.first_name || !form.value.last_name) return
  
  try {
    const cleanedSchema = {}
    Object.entries(form.value.work_days_schema).forEach(([key, value]) => {
      cleanedSchema[key] = Number(value) || 0
    })

    const profilePayload = {
      joined_at: form.value.joined_at, // Übergabe an das Backend
      work_days_schema: cleanedSchema,
      overtime_hours: form.value.overtime_balance,
      vacation_days_per_year: form.value.vacation_days_per_year,
      vacation_left: form.value.vacation_left
    }

    if (props.member) {
      await adminStore.updateTeamMember(props.member.id, { ...profilePayload })
    } else {
        // NEUANLAGE:
        await adminStore.createTeamMember({
          first_name: form.value.first_name,
          last_name: form.value.last_name,
          joined_at: form.value.joined_at,
          work_days_schema: cleanedSchema,
          
          vacation_days_per_year: form.value.vacation_days_per_year, 
          // Hier senden wir den berechneten anteiligen Wert als Startwert ans Backend
          vacation_total: form.value.vacation_left 
        })
    }

    if (typeof adminStore.fetchTeamMembers === 'function') {
      await adminStore.fetchTeamMembers()
    }
    emit('close')
  } catch (error) {
    console.error("Fehler beim Verarbeiten des Mitarbeiters im Modal:", error)
  }
}
</script>

<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
  >
    <div class="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden">
      
      <!-- Modal Header -->
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 class="font-bold text-lg text-slate-900">
          {{ member ? 'Mitarbeiter bearbeiten' : 'Mitarbeiter anlegen' }}
        </h3>
        <button 
          type="button"
          class="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          @click="emit('close')"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Modal Form Content -->
      <form class="p-6 space-y-4" @submit.prevent="handleSubmit">
        
        <!-- Vorname & Nachname -->
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Vorname</label>
            <input 
              v-model="form.first_name" 
              required
              :disabled="!!member"
              type="text" 
              class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Nachname</label>
            <input 
              v-model="form.last_name" 
              required
              :disabled="!!member"
              type="text" 
              class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
        </div>



        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Eintrittsdatum</label>
            <div class="relative">
              <input 
                v-model="form.joined_at" 
                required
                type="date" 
                class="w-full pl-4 pr-10 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 font-medium"
              />
              <CalendarDays class="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        </div>

        <!-- Arbeitszeit-Schema (Wochenstunden) -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Arbeitszeit-Schema (Std.)</label>
            <span class="text-xs font-bold bg-blue-50 text-blue-600 px-2.5 py-1 rounded-lg border border-blue-100">
              Soll: <strong>{{ form.weekly_hours }}</strong> h/Woche
            </span>
          </div>
          
          <div class="grid grid-cols-7 gap-1">
            <div 
              v-for="day in DISPLAY_DAYS" 
              :key="day.id" 
              class="space-y-1 text-center"
              :class="{'p-0.5 rounded-md hover:bg-slate-50': day.id === '5' || day.id === '6'}"
            >
              <span class="text-[10px] font-bold uppercase text-slate-400 block">{{ day.label }}</span>
              <input 
                v-model.number="form.work_days_schema[day.id]" 
                type="number" 
                step="any"
                min="0"
                max="24"
                class="w-full text-center p-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-bold text-slate-700 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
              />
            </div>
          </div>
        </div>

        <!-- Urlaubstage & Überstunden -->
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Urlaub / Jahr</label>
            <input 
              v-model.number="form.vacation_days_per_year" 
              type="number" 
              min="0"
              class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div v-if="!member" class="space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Anteilig (Vorschau)</label>
            <div class="w-full px-4 py-2 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl text-sm font-semibold flex items-center gap-2 h-[38px]">
              <span>{{ form.vacation_left }} Tage</span>
              <span class="text-[10px] text-amber-600 font-normal">(bis Jahresende)</span>
            </div>
          </div>
        </div>

        <!-- Modal Footer Actions -->
        <div class="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
          <button 
            type="button" 
            class="px-4 py-2 hover:bg-slate-100 rounded-xl text-slate-500 text-sm font-bold transition-all cursor-pointer"
            @click="emit('close')"
          >
            Abbrechen
          </button>
          <button 
            type="submit" 
            class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-900/20 cursor-pointer"
          >
            Speichern
          </button>
        </div>

      </form>
    </div>
  </div>
</template>