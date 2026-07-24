import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const ACTIVE_TAB_KEY = 'activeTab'

function getInitialTab() {
  return localStorage.getItem(ACTIVE_TAB_KEY) || 'dashboard'
}

// Purely UI-state persistence -- not auth-related, so this stays a
// simple direct localStorage read/write rather than going through
// authTokenService.
export const useAppStore = defineStore('app', () => {
  const activeTab = ref(getInitialTab())
  const activeSubTab = ref(null)
  const isSidebarOpen = ref(false)

  function setTab(tabName, subTabName = null) {
    activeTab.value = tabName
    localStorage.setItem(ACTIVE_TAB_KEY, tabName)
    activeSubTab.value = subTabName

    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  function toggleSidebar() {
    isSidebarOpen.value = !isSidebarOpen.value
  }

  const TAB_TITLES = {
    dashboard: 'Übersicht',
    attendance: 'Anwesenheit',
    calendar: 'Kalender',
  }

  const currentTabTitle = computed(() => TAB_TITLES[activeTab.value] || 'Home')

  return {
    activeTab,
    activeSubTab,
    isSidebarOpen,
    setTab,
    toggleSidebar,
    currentTabTitle,
  }
})