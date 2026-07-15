<script setup>
import { computed } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { storeToRefs } from 'pinia'
import { Calendar, Clock, CheckCircle2, XCircle, User, AlertCircle } from 'lucide-vue-next'
import { useEventStyles } from '@/composables/useEventStyles'
import { useDateFormatter } from '@/composables/useDateFormatter'

const props = defineProps({
  search: String,
  status: String,
  employeeFilter: String, // NEU
  monthFilter: String     // NEU
})

const adminStore = useAdminStore()
const { leaveRequests } = storeToRefs(adminStore)
const { getEventIcon, getIconColorClass, getStatusColorClass } = useEventStyles()
const { formatDate } = useDateFormatter()

const filtered = computed(() => {
  return leaveRequests.value.filter(req => {
    const name = (req.employee_name || req.name || '').toLowerCase()

    // 1. Textsuche (falls aktiv)
    const matchesSearch = name.includes((props.search || '').toLowerCase())

    // 2. Status-Filter
    const matchesStatus = props.status === 'all' || req.status === props.status

    // 3. NEU: Mitarbeiter-Filter
    const reqNameNormalized = req.employee_name || req.name || ''
    const matchesEmployee = props.employeeFilter === 'all' || reqNameNormalized === props.employeeFilter

    let matchesMonth = true
    if (props.monthFilter && props.monthFilter !== 'all') {
      const targetDate = req.leave_start
      if (targetDate) {
        // Extrahiert entweder YYYY-MM aus "YYYY-MM-DD" oder wandelt deutsches Format "DD.MM.YYYY" um
        let ym = ''
        if (targetDate.includes('-')) {
          // ISO-Format: "2026-07-15..." -> "2026-07"
          ym = targetDate.substring(0, 7)
        } else if (targetDate.includes('.')) {
          // Deutsches Format: "15.07.2026" -> "2026-07"
          const parts = targetDate.split('.')
          if (parts.length === 3) {
            const day = parts[0].trim()
            const month = parts[1].trim().padStart(2, '0')
            const year = parts[2].trim().substring(0, 4)
            ym = `${year}-${month}`
          }
        } else {
          // Fallback auf JavaScript Date, falls es ein anderes Format ist
          const dateObj = new Date(targetDate)
          if (!isNaN(dateObj.getTime())) {
            ym = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}`
          }
        }
        
        matchesMonth = ym === props.monthFilter
      } else {
        matchesMonth = false
      }
    }

    return matchesSearch && matchesStatus && matchesEmployee && matchesMonth
  })
})
</script>

<template>
  <div class="space-y-4">
    <div v-if="filtered.length === 0" class="bg-white rounded-[2.5rem] border border-slate-200 border-dashed p-16 text-center space-y-4">
      <div class="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto text-slate-300">
        <AlertCircle class="w-8 h-8" />
      </div>
      <div class="space-y-1">
        <h3 class="text-xl font-bold text-slate-900">Keine Einträge gefunden</h3>
        <p class="text-slate-500 max-w-xs mx-auto text-sm">
          Es wurden keine Urlaubsanträge für die aktuellen Filterkriterien gefunden.
        </p>
      </div>
    </div>

    <div
      v-for="req in filtered"
      :key="req.id"
      class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all group"
    >
      <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">

        <div class="flex items-start gap-4 flex-1 min-w-0">
          <div class="shrink-0">
            <div v-if="req.avatar" class="w-12 h-12 rounded-xl overflow-hidden border border-slate-200 shadow-sm">
              <img :src="req.avatar" class="w-full h-full object-cover" />
            </div>
            <div v-else class="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 font-bold text-sm border border-blue-100 shadow-sm">
              {{ req.initials }}
            </div>
          </div>

          <div class="space-y-1 text-left flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-3">
              <h3 class="font-bold text-slate-900 text-base truncate">
                {{ req.name }}
              </h3>
              <span :class="['px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider', getStatusColorClass(req.status)]">
                {{ req.status_display }}
              </span>
              <span class="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                <User class="w-3 h-3" />
                Beantragt am {{ formatDate(req.request_date) || req.request_date }}
              </span>
            </div>

            <div class="flex flex-wrap items-center gap-4 text-sm text-slate-500 mt-1">
              <div class="flex items-center gap-1.5 font-medium">
                <Calendar class="w-4 h-4 opacity-60" />
                <span>{{ formatDate(req.leave_start) || req.leave_start }} - {{ formatDate(req.leave_end) || req.leave_end }}</span>
              </div>
              <div class="flex items-center gap-1.5 font-medium" :class="getIconColorClass(req.leave_type)">
                <component :is="getEventIcon(req.leave_type)" class="w-4 h-4 opacity-60" />
                {{ req.leave_type_display }}
              </div>
              <div class="flex items-center gap-1.5 font-medium">
                <Clock class="w-4 h-4 opacity-60" />
                {{ req.duration ?? 0 }} {{ (req.duration ?? 0) === 1 ? 'Tag' : 'Tage' }}
              </div>
            </div>

            <p v-if="req.note" class="text-sm text-slate-400 mt-2 italic leading-relaxed">
              "{{ req.note }}"
            </p>
          </div>
        </div>

        <div class="w-full lg:w-auto flex shrink-0">
          <div v-if="req.status === 'pending'" class="flex items-center gap-2 w-full lg:w-auto">
            <button
              @click="adminStore.handleRequestAction(req.id, 'reject')"
              class="flex-1 lg:flex-none justify-center px-4 py-2 text-sm font-bold text-red-600 hover:bg-red-50 rounded-xl border border-red-100 transition-all flex items-center gap-2 cursor-pointer shadow-sm"
              title="Ablehnen"
            >
              <XCircle class="w-4 h-4" /> <span class="lg:inline">Ablehnen</span>
            </button>
            <button
              @click="adminStore.handleRequestAction(req.id, 'approve')"
              class="flex-1 lg:flex-none justify-center px-4 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-md hover:shadow-lg transition-all flex items-center gap-2 cursor-pointer"
              title="Genehmigen"
            >
              <CheckCircle2 class="w-4 h-4" /> <span class="lg:inline">Genehmigen</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>