<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { Bell, Palmtree, Zap, User, Settings, LogOut, ShieldCheck } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/authStore' 
import { useAdminStore } from '@/stores/adminStore'
import { storeToRefs } from 'pinia'
import NotificationDropdown from '@/components/tooltips/NotificationDropdown.vue'



const props = defineProps({
  isAdminView: {
    type: Boolean,
    default: false
  }
})




const authStore = useAuthStore()
const adminStore = useAdminStore()
const { user, userStats } = storeToRefs(authStore)

const { 
  active_employees, 
  requests_count 
} = storeToRefs(adminStore)


const { isSupervisor } = storeToRefs(authStore)

const isProfileMenuOpen = ref(false)
const isNotificationsOpen = ref(false)

let statsInterval = null // Variable für den Timer

const startStatsPolling = () => {
  // Verhindern, dass mehrere Intervalle gleichzeitig laufen
  stopStatsPolling()
  
  // Alle 60 Sekunden (60000ms) die Stats neu laden
  statsInterval = setInterval(() => {
    if (authStore.isAuthenticated) {
      authStore.fetchUserStats()
    }
  }, 60000) 
}

const stopStatsPolling = () => {
  if (statsInterval) {
    clearInterval(statsInterval)
    statsInterval = null
  }
}

const emit = defineEmits(['openEditProfile', 'logout'])

const toggleProfileMenu = () => {
  isProfileMenuOpen.value = !isProfileMenuOpen.value
  if (isProfileMenuOpen.value) isNotificationsOpen.value = false
}

const toggleNotifications = () => {
  isNotificationsOpen.value = !isNotificationsOpen.value
  if (isNotificationsOpen.value) isProfileMenuOpen.value = false
}

const handleEditProfile = () => {
  isProfileMenuOpen.value = false
  emit('openEditProfile')
}

const getStatusColor = (status) => {
  if (!status) return 'bg-slate-300'
  switch (status) {
    case 'Anwesend': return 'bg-emerald-500 animate-pulse';
    case 'Urlaub':   return 'bg-amber-500';
    case 'Krank':     return 'bg-violet-500';
    default:          return 'bg-slate-400';
  }
}

onMounted(() => {
  // Nur laden, wenn wir eingeloggt sind und noch keine Stats haben
  if (authStore.isAuthenticated && !userStats.value) {
    authStore.fetchUserStats()
  }
  startStatsPolling() // Timer starten
})

onUnmounted(() => {
  stopStatsPolling()
})

watch(() => authStore.isAuthenticated, (val) => {
  if (val) {
    if (!userStats.value) authStore.fetchUserStats()
    startStatsPolling()
  } else {
    stopStatsPolling()
  }
}, { immediate: true })

</script>


<template>

  <header class="h-20 bg-white border-b border-slate-200 flex items-center justify-between px-8">
    <div class="flex items-center gap-8 flex-1">
      
      <!-- Header Stats -->
      <div class="hidden md:flex items-center gap-6">

        <!-- ================= MITARBEITER-ANSICHT ================= -->
        <template v-if="!isSupervisor">
          <div class="flex items-center gap-2.5">
            <div :class="['w-2 h-2 rounded-full', getStatusColor(userStats?.status)]"></div>              
            <div class="flex flex-col">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 leading-none">Status</span>
              <span class="text-xs font-bold text-slate-700 mt-0.5">{{ userStats?.status }}</span>
            </div>
          </div>

          <div class="h-8 w-px bg-slate-100"></div>

          <!-- Vacation -->
          <div class="flex items-center gap-2.5">
            <Palmtree class="w-4 h-4 text-emerald-500" />
            <div class="flex flex-col">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 leading-none">Vacation</span>
              <span class="text-xs font-bold text-slate-700 mt-0.5">
                {{ userStats?.vacation?.used_days }} / {{ userStats?.vacation?.total_available_days }} used
              </span>
            </div>
          </div>

          <div class="h-8 w-px bg-slate-100"></div>

          <!-- Overtime -->
          <div class="flex items-center gap-2.5">
            <Zap class="w-4 h-4 text-orange-500" />
            <div class="flex flex-col">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 leading-none">Overtime</span>
              <span class="text-xs font-bold text-slate-700 mt-0.5">{{ userStats?.overtime?.balance }}h</span>
            </div>
          </div>
        </template>

        <!-- ================= CHEF-ANSICHT (SUPERVISOR) ================= -->
        <template v-else>
          <!-- Aktive Mitarbeiter im Team -->
          <div class="flex items-center gap-2.5">
            <User class="w-4 h-4 text-blue-500" />
            <div class="flex flex-col">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 leading-none">Team</span>
              <span class="text-xs font-bold text-slate-700 mt-0.5">
                {{ active_employees ?? 67 }} Mitarbeiter aktiv
              </span>
            </div>
          </div>

          <!-- Ausstehende Anfragen -->
          <div class="flex items-center gap-2.5">
            <Bell class="w-4 h-4 text-yellow-500" />
            <div class="flex flex-col">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 leading-none">Anfragen</span>
              <span class="text-xs font-bold text-slate-700 mt-0.5">
                {{ requests_count ?? 67 }} ausstehend
              </span>
            </div>
          </div>
        </template>
      </div>

    </div>
    
    <div class="flex items-center gap-4">
      <NotificationDropdown 
        :is-open="isNotificationsOpen"
        @toggle="toggleNotifications"
        @close="isNotificationsOpen = false"
      />
      
      <div class="relative">
        <button 
          @click="toggleProfileMenu"
          class="flex items-center gap-3 pl-4 border-l border-slate-200 hover:bg-slate-50 transition-colors py-1 px-2 rounded-lg"
        >
          <div class="text-right hidden sm:block">
            <p class="text-sm font-semibold">{{ user?.name }}</p>
          </div>
          <div v-if="user?.avatar && user.avatar.length > 0" class="w-10 h-10 rounded-full overflow-hidden border border-slate-200">
            <img :src="user?.avatar" class="w-full h-full object-cover" alt="Avatar" referrerPolicy="no-referrer" />
          </div>
          <div v-else class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold">
            {{ user?.initials }}
          </div>
        </button>

        <!-- Profile Dropdown -->
        <div v-if="isProfileMenuOpen" class="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50">
          <div class="px-4 py-3 border-b border-slate-100 mb-1 flex items-center gap-3">
            <div v-if="user?.avatar && user.avatar.length > 0" class="w-10 h-10 rounded-full overflow-hidden border border-slate-100">
              <img :src="user?.avatar" class="w-full h-full object-cover" alt="Avatar" referrerPolicy="no-referrer" />
            </div>
            <div v-else class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold text-sm">
              {{ user?.initials }}
            </div>
            <div>
              <p class="text-sm font-bold text-slate-900 leading-none">{{ user?.name }}</p>
              <p class="text-[10px] text-slate-500 mt-1">{{ user?.email }}</p>
            </div>
          </div>
          <button 
            @click="handleEditProfile"
            class="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <User class="w-4 h-4 text-slate-400" />
            <span>Edit Profile</span>
          </button>
          <button class="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors">
            <Settings class="w-4 h-4 text-slate-400" />
            <span>Settings</span>
          </button>
          <div class="h-px bg-slate-100 my-1"></div>
          <button 
            @click="$emit('logout')"
            class="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            <LogOut class="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
        
        <!-- Backdrop to close menu -->
        <div 
          v-if="isProfileMenuOpen" 
          @click="isProfileMenuOpen = false"
          class="fixed inset-0 z-40"
        ></div>
      </div>
    </div>
  </header>

</template>
