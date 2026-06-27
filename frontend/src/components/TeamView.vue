<script setup>
import { ref, computed, onMounted } from 'vue'
import { Search, BookUser } from 'lucide-vue-next'
import { useEventStyles } from '@/composables/useEventStyles'
import { useAuthStore } from '@/stores/authStore'
import { storeToRefs } from 'pinia'

const { getStatusColor } = useEventStyles()
const authStore = useAuthStore()
const { teamMembers } = storeToRefs(authStore)

const searchQuery = ref('')

onMounted(() => {
  // Wir laden die Member nur, wenn noch keine da sind
  if (teamMembers.value.length === 0) {
    authStore.fetchTeamMembers()
  }
})

const filteredMembers = computed(() => {
  if (!searchQuery.value) return teamMembers.value
  const query = searchQuery.value.toLowerCase()
  return teamMembers.value.filter(member => 
    member.name?.toLowerCase().includes(query) || 
    member.email?.toLowerCase().includes(query) ||
    member.phone?.includes(query)
  )
})
</script>

<template>
  <div class="flex-1 overflow-y-auto p-8 bg-slate-50/50">
    <div class="max-w-6xl mx-auto space-y-8">
      
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="text-left">
          <h1 class="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <BookUser class="w-6 h-6 text-blue-600" /> <span>Kontakte</span>
          </h1>
          <p class="text-slate-500 mt-1">Alle Kollegen im Überblick.</p>
        </div>
        
        <div class="flex items-center gap-3">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              v-model="searchQuery"
              type="text" 
              placeholder="Kollegen finden..." 
              class="pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all w-80 shadow-sm"
            />
          </div>
        </div>
      </section>

      <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/50 border-b border-slate-100">
                <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Name</th>
                <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">E-Mail</th>
                <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Telefon</th>
                <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="member in filteredMembers" :key="member.id" class="hover:bg-slate-50/50 transition-colors">
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div v-if="member.avatar" class="w-10 h-10 rounded-full overflow-hidden border border-slate-100">
                      <img :src="member.avatar" class="w-full h-full object-cover" :alt="member.name" />
                    </div>
                    <div v-else class="w-10 h-10 bg-blue-50 rounded-full flex items-center justify-center text-blue-600 font-bold text-sm">
                      {{ member.initials }}
                    </div>
                    <div>
                      <span class="font-semibold text-slate-900 block leading-tight">{{ member.name }}</span>
                      <span class="text-[11px] text-slate-400">{{ member.username}}</span>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 text-sm text-slate-600">
                  <a :href="`mailto:${member.email}`" class="hover:text-blue-600 transition-colors">{{ member.email || '-' }}</a>
                </td>
                <td class="px-6 py-4 text-sm text-slate-600">{{ member.phone || '-' }}</td>
                <td class="px-6 py-4">
                  <span :class="['px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide', getStatusColor(member.status_text)]">
                    {{ member.status_text }}
                  </span>
                </td>
              </tr>

              <tr v-if="filteredMembers.length === 0">
                <td colspan="4" class="px-6 py-12 text-center">
                  <p class="text-slate-400 italic">Keine Teammitglieder gefunden.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </div>
</template>