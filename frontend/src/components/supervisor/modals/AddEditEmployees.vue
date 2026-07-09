<script setup>
import { ref, watch, computed } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { X, CalendarDays, Lock, LockOpen } from 'lucide-vue-next'
import { useDateFormatter } from '@/composables/useDateFormatter'


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
const { formatDate } = useDateFormatter()


const DISPLAY_DAYS = [
  { id: '0', label: 'Mo' },
  { id: '1', label: 'Di' },
  { id: '2', label: 'Mi' },
  { id: '3', label: 'Do' },
  { id: '4', label: 'Fr' },
  { id: '5', label: 'Sa' },
  { id: '6', label: 'So' }
]



const todayISO = () => new Date().toISOString().split('T')[0]

const defaultSchema = () => ({
  '0': 8, '1': 8, '2': 8, '3': 8, '4': 8, '5': 0, '6': 0
})

const hasSchema = (schema) => schema && Object.keys(schema).length > 0

const isEditingSchema = ref(false)  // NEU – Lock-Status


const form = ref({
  first_name: '',
  last_name: '',
  joined_at: '', 
  work_days_schema: defaultSchema(),
  schema_valid_from: todayISO(), 
  upcoming_schema_change: null, 
  overtime_balance: 0,
  vacation_total: 30,
  vacation_left: 30
})

const upcomingWeeklyHours = computed(() => {
  const schema = form.value.upcoming_schema_change?.work_days_schema
  if (!hasSchema(schema)) return 0
  return Object.values(schema).reduce((sum, h) => sum + (Number(h) || 0), 0)
})


const weeklyHours = computed(() => {
  if (!form.value.work_days_schema) return 0
  return Object.values(form.value.work_days_schema).reduce((sum, hours) => {
    return sum + (Number(hours) || 0)
  }, 0)
})

const calculateProRataVacation = (entryDateStr, yearlyDays) => {
  if (!entryDateStr) return yearlyDays

  const entryDate = new Date(entryDateStr)
  const entryYear = entryDate.getFullYear()
  const currentYear = new Date().getFullYear()

  // Bereits vor diesem Jahr eingestiegen -> voller Anspruch
  if (entryYear < currentYear) {
    return yearlyDays
  }

  // Einstieg erst in einem zukünftigen Jahr -> noch kein Anspruch fürs laufende Jahr
  if (entryYear > currentYear) {
    return 0
  }

  // Einstieg im laufenden Jahr -> anteilig ab Eintrittsmonat
  const monthsActive = 13 - (entryDate.getMonth() + 1)
  const proRata = (yearlyDays / 12) * monthsActive
  return Math.round(proRata)
}

// Reagiert jetzt immer auf Änderungen - egal ob Neuanlage oder Bearbeitung
watch(
  [() => form.value.joined_at, () => form.value.vacation_days_per_year],
  ([newEntryDate, newYearlyDays]) => {
    form.value.vacation_total = calculateProRataVacation(newEntryDate, Number(newYearlyDays) || 0)
  }
)




const populateForm = (data) => {
  isEditingSchema.value = false   // NEU – bei jedem Öffnen wieder gesperrt

  if (data) {
    form.value = {
      first_name: data.first_name ?? '',
      last_name: data.last_name ?? '',
      joined_at: data.joined_at ?? '',
      work_days_schema: hasSchema(data.work_days_schema) ? { ...data.work_days_schema } : defaultSchema(),
      schema_valid_from: todayISO(),
      upcoming_schema_change: data.upcoming_schema_change ?? null,  // NEU
      overtime_balance: Number(data.overtime_hours ?? 0),
      vacation_days_per_year: Number(data.vacation_days_per_year ?? 30),
      vacation_total: Number(data.vacation_total ?? data.vacation_days_per_year ?? 30)
    }
  } else {
    form.value = {
      first_name: '',
      last_name: '',
      joined_at: todayISO(),
      work_days_schema: defaultSchema(),
      schema_valid_from: todayISO(),
      upcoming_schema_change: null,
      overtime_balance: 0,
      vacation_days_per_year: 30,
      vacation_total: 30
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
  if (form.value.vacation_days_per_year === '') return

  // Fix: props.member statt member
  const schemaChanged = props.member ? isEditingSchema.value : true

  try {
    const cleanedSchema = {}
    Object.entries(form.value.work_days_schema).forEach(([key, value]) => {
      cleanedSchema[key] = Number(value) || 0
    })

    if (props.member) {
      const payload = {
        joined_at: form.value.joined_at,
        overtime_hours: form.value.overtime_balance,
        vacation_days_per_year: form.value.vacation_days_per_year
      }
      if (schemaChanged) {
        payload.work_days_schema = cleanedSchema
        payload.schema_valid_from = form.value.schema_valid_from
      }
      await adminStore.updateTeamMember(props.member.id, payload)
    } else {
      await adminStore.createTeamMember({
        first_name: form.value.first_name,
        last_name: form.value.last_name,
        joined_at: form.value.joined_at,
        work_days_schema: cleanedSchema,
        vacation_days_per_year: form.value.vacation_days_per_year
      })
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
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold bg-blue-50 text-blue-600 px-2.5 py-1 rounded-lg border border-blue-100">
                Soll: <strong>{{ weeklyHours }}</strong> h/Woche
              </span>
              <!-- NEU: Lock-Button, nur im Edit-Modus relevant -->
              <button
                v-if="member"
                type="button"
                @click="isEditingSchema = !isEditingSchema"
                :title="isEditingSchema ? 'Bearbeitung sperren' : 'Bearbeitung freigeben'"
                class="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                :class="{ 'text-amber-500 hover:text-amber-600': isEditingSchema }"
              >
                <component :is="isEditingSchema ? LockOpen : Lock" class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- NEU: Infobox bei bereits geplantem Zukunfts-Schema -->
          <div 
            v-if="form.upcoming_schema_change && isEditingSchema" 
            class="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800"
          >
            <CalendarDays class="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div>
              Es wurde bereits ein neues Schema hinterlegt (<strong>{{ upcomingWeeklyHours }} h/Woche</strong> ab <strong>{{ formatDate(form.upcoming_schema_change.valid_from) }}</strong>).
            </div>
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
                :disabled="member && !isEditingSchema"
                class="w-full text-center p-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-bold text-slate-700 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>

          <!-- Gültig-ab-Datum nur zeigen, wenn Bearbeitung freigegeben ist -->
          <div v-if="member && isEditingSchema" class="pt-1 space-y-1">
            <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Neues Schema gilt ab</label>
            <input 
              v-model="form.schema_valid_from" 
              type="date" 
              :min="todayISO()"
              class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
            <p class="text-[11px] text-slate-400">
              Vergangene Stundennachweise bleiben unverändert – das Schema gilt erst ab diesem Datum.
            </p>
          </div>
        </div>


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

  <div class="space-y-1">
    <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">
      Restanspruch {{ new Date().getFullYear() }}
    </label>
    <div class="w-full px-4 py-2 bg-blue-50/50 border border-blue-100 text-blue-700 rounded-xl text-sm font-semibold flex items-center h-[38px]">
      {{ form.vacation_total }} Tage
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