<script setup>
import { computed } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import { storeToRefs } from 'pinia'
import { Clock, ArrowRight, CheckCircle2, XCircle, User } from 'lucide-vue-next'

const props = defineProps(['search', 'status'])
const adminStore = useAdminStore()
const { changeRequests } = storeToRefs(adminStore)

const filtered = computed(() => {
  return changeRequests.value.filter(req => {
    const name = (req.employee_name || req.name || '').toLowerCase()
    const matchesSearch = name.includes(props.search.toLowerCase())
    const matchesStatus = props.status === 'all' || req.status === props.status
    return matchesSearch && matchesStatus
  })
})

const getStatusClass = (s) => {
  if (s === 'approved') return 'bg-emerald-50 text-emerald-700 border-emerald-100'
  if (s === 'rejected') return 'bg-red-50 text-red-700 border-red-100'
  return 'bg-amber-50 text-amber-700 border-amber-100'
}
</script>

<template>
  <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
    <div v-if="filtered.length === 0" class="p-16 text-center text-slate-500 font-medium">
      Keine Zeitkorrekturen gefunden.
    </div>

    <div v-for="req in filtered" :key="req.id" class="p-6 hover:bg-slate-50/50 transition-colors">
      <div class="flex flex-col lg:flex-row justify-between gap-6">
        
        <div class="flex items-start gap-5 flex-1">
          <div class="shrink-0">
            <div v-if="req.avatar" class="w-12 h-12 rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
              <img :src="req.avatar" class="w-full h-full object-cover" />
            </div>
            <div v-else class="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center text-blue-600 font-bold text-sm border border-blue-100 shadow-sm">
              {{ req.initials }}
            </div>
          </div>
          
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-bold text-slate-900">{{ req.name }}</span>
              <span :class="['px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase', getStatusClass(req.status)]">
                {{ req.status_display }}
              </span>
            </div>
            
            <div class="flex items-center gap-3 my-2 text-xs text-slate-500">
              <span class="flex items-center gap-1.5 text-slate-400">
                <User class="w-3.5 h-3.5" /> 
                Beantragt am {{ req.request_date }}
              </span>
            </div>

            <div class="flex flex-wrap items-center gap-3 my-2">
              <div class="text-xs text-slate-400 bg-slate-50 p-1.5 rounded border border-slate-100 flex items-center gap-1 font-mono shrink-0">
                <Clock class="w-3 h-3" /> 
                {{ req.old_check_in }} - {{ req.old_check_out }}
              </div>

              <ArrowRight class="w-3 h-3 text-slate-300 shrink-0" />

              <div class="flex items-center gap-2 flex-wrap ">
                <div class="text-xs text-blue-700 font-bold bg-blue-50 p-1.5 rounded border border-blue-100 flex items-center gap-1 font-mono shrink-0">
                  <Clock class="w-3 h-3" /> 
                  {{ req.requested_check_in }} - {{ req.requested_check_out }}
                </div>

                <span v-if="req.time_diff" class="text-[10px] font-bold px-1.5 py-0.5 rounded-md border bg-amber-50 text-amber-600 border-amber-100 shrink-0">
                  {{ req.time_diff }}
                </span>
              </div>
            </div>

            <p v-if="req.employee_note" class="text-sm text-slate-600 mt-3 bg-slate-50 p-3 rounded-xl border border-slate-100 italic relative">
              <span class="absolute -top-2 left-3 bg-white px-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest border border-slate-100 rounded-md shadow-sm">Bemerkung</span>
              {{ req.employee_note }}
            </p>

            <div v-if="req.status === 'pending'" class="flex min-[1100px]:hidden gap-2 mt-4 ">
              <button @click="adminStore.handleChangeRequestAction(req.id, 'reject')" 
                class="flex-1 sm:flex-none justify-center px-4 py-2 text-sm font-bold text-red-600 hover:bg-red-50 rounded-xl border border-red-100 transition-all flex items-center gap-2">
                <XCircle class="w-4 h-4" /> Ablehnen
              </button>
              <button @click="adminStore.handleChangeRequestAction(req.id, 'approve')" 
                class="flex-1 sm:flex-none justify-center px-4 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-lg transition-all flex items-center gap-2">
                <CheckCircle2 class="w-4 h-4" /> Genehmigen
              </button>
            </div>
          </div>
        </div>

        <div v-if="req.status === 'pending'" class="hidden min-[1100px]:flex gap-2 shrink-0 items-center">
          <button @click="adminStore.handleChangeRequestAction(req.id, 'reject')" 
            class="px-4 py-2 text-sm font-bold text-red-600 hover:bg-red-50 rounded-xl border border-red-100 transition-all flex items-center gap-2">
            <XCircle class="w-4 h-4" /> Ablehnen
          </button>
          <button @click="adminStore.handleChangeRequestAction(req.id, 'approve')" 
            class="px-4 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-lg transition-all flex items-center gap-2">
            <CheckCircle2 class="w-4 h-4" /> Genehmigen
          </button>
        </div>

      </div>
    </div>
  </div>
</template>