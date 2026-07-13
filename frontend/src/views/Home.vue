<script setup>
import { ref, watch, onMounted } from 'vue'
import { Users, Calendar, FileText, Briefcase } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useAdminStore } from '@/stores/adminStore'
import { useAppStore } from '@/stores/appStore'
import { storeToRefs } from 'pinia'
 

import AppSidebar from '@/components/navigation/AppSidebar.vue'
import AppHeader from '@/components/navigation/AppHeader.vue'

import DashboardTab from '@/components/DashboardTab.vue'
import TeamView from '@/components/TeamView.vue'
import ScheduleView from '@/components/ScheduleView.vue'
import RequestsView from '@/components/RequestsView.vue'
import DocumentsView from '@/components/DocumentsView.vue'

import EditProfileModal from '@/components/modals/EditProfileModal.vue'

import AdminDashboard from '@/components/supervisor/AdminDashboard.vue'
import AdminTeamView from '@/components/supervisor/AdminTeamView.vue'
import AdminRequests from '@/components/supervisor/AdminRequests.vue'
import AdminCalendar from '@/components/supervisor/AdminCalendar.vue'
import AdminReports from '@/components/supervisor/AdminReports.vue'

// Stores initialisieren
const authStore = useAuthStore()
const adminStore = useAdminStore()
const appStore = useAppStore()
const router = useRouter()
const isReady = ref(false)

const { user, isSupervisor } = storeToRefs(authStore)
const { activeTab } = storeToRefs(appStore) // Wir nutzen activeTab aus dem Store

// Lokale Zustände
const isEditProfileModalOpen = ref(false)
const isAdminView = ref(true)

// --- Tab-Logik & Persistence ---

watch(activeTab, (newTab) => {
  localStorage.setItem('activeTab', newTab)
  console.log("Tab gewechselt zu:", newTab)
})

// --- Supervisor / Admin-Modus Logik ---
const applyStoredPreference = () => {
  if (!user.value || Object.keys(user.value).length === 0) return

  if (isSupervisor.value) {
    const saved = localStorage.getItem('isAdminView')
    isAdminView.value = saved !== null ? saved === 'true' : true
  } else {
    isAdminView.value = false
  }
}

// Beobachte Änderungen am Supervisor-Status
watch(isSupervisor, (newValue) => {
  if (newValue !== undefined) {
    applyStoredPreference()
    
    // Falls der Status erst hier bekannt wird, jetzt die Daten holen
    if (newValue === true) {
      adminStore.fetchDashboardData()
    }
  }
}, { immediate: true })

// Logik wenn der Admin-Modus umgeschaltet wird
watch(isAdminView, (newValue) => {
  if (!isReady.value) return // Blockieren, solange die App nicht fertig initialisiert ist

  if (isSupervisor.value) {
    localStorage.setItem('isAdminView', newValue.toString())
  }
  
  if (newValue === false) {
    const adminTabs = ['admin-dashboard', 'admin-team', 'admin-requests', 'admin-calendar', 'admin-reports']
    if (adminTabs.includes(activeTab.value)) {
      appStore.setTab('dashboard')
    }
  }
})

// --- Lifecycle ---
onMounted(async () => {
  if (typeof authStore.fetchUser === 'function') {
    if (!user.value || Object.keys(user.value).length === 0) {
      await authStore.fetchUser()
    }
  }
  
  applyStoredPreference()

  // KORREKTUR: Umleitung für Supervisors in der Admin-Ansicht optimieren
  if (isSupervisor.value && isAdminView.value) {
    // Mapping von Mitarbeiter-Tabs zu Admin-Tabs
    const tabMapping = {
      'dashboard': 'admin-dashboard',
      'team': 'admin-team',
      'calendar': 'admin-calendar',
      'requests': 'admin-requests'
    }

    if (tabMapping[appStore.activeTab]) {
      appStore.setTab(tabMapping[appStore.activeTab])
    }
  } 
  // Schutz für normale Mitarbeiter (falls ein Admin-Tab im LocalStorage hing)
  else if (!isSupervisor.value && ['admin-dashboard', 'admin-team', 'admin-requests', 'admin-calendar', 'admin-reports'].includes(appStore.activeTab)) {
    appStore.setTab('dashboard')
  }

  if (isSupervisor.value) {
    adminStore.fetchDashboardData()
  }

  isReady.value = true
})

// --- Aktionen ---
const logout = () => {
  // 1. Tab-State zurücksetzen, bevor wir den Store leeren
  appStore.setTab('dashboard')
  localStorage.removeItem('activeTab')

  // Store-Logout aufrufen (löscht alle States & LocalStorages)
  authStore.logout()
  
  // Sauber per Vue-Router weiterleiten
  router.push('/login')
}

const quickLinks = [
  { name: 'Adressbuch', icon: Users, color: 'text-blue-600', tab: 'team' },
  { name: 'Kalender', icon: Calendar, color: 'text-emerald-600', tab: 'calendar' },
  { name: 'Meine Dokumente', icon: FileText, color: 'text-purple-600', tab: 'documents' },
]

</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <AppSidebar 
      v-model:currentTab="appStore.activeTab" 
      v-model:isAdminView="isAdminView"
    />

    <main class="flex-1 flex flex-col overflow-hidden">
      <AppHeader 
        @openEditProfile="isEditProfileModalOpen = true"
        @logout="logout"
      />

      <div class="flex-1 overflow-y-auto bg-slate-50">
        
        <DashboardTab 
          v-if="activeTab === 'dashboard'" 
          :quickLinks="quickLinks"
          @changeTab="appStore.setTab($event)"
        />

        <TeamView 
          v-if="activeTab === 'team'" 
        />
        
        <ScheduleView v-if="activeTab === 'calendar'" />

        <RequestsView v-if="activeTab === 'requests'"/>

        <DocumentsView v-if="activeTab === 'documents'" />


        <template v-if="isAdminView">
          <AdminDashboard v-if="activeTab === 'admin-dashboard'" />
          <AdminTeamView v-if="activeTab === 'admin-team'" />
          <AdminRequests v-if="activeTab === 'admin-requests'" />
          <AdminCalendar v-if="activeTab === 'admin-calendar'" />
          <AdminReports v-if="activeTab === 'admin-reports'" />
        </template>

      </div>
    </main>

    <EditProfileModal 
      :isOpen="isEditProfileModalOpen"
      @close="isEditProfileModalOpen = false"
    />
  </div>
</template>