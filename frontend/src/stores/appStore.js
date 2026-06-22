// src/stores/appStore.js
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    // Der Name des aktuell aktiven Tabs (entspricht dem Standard beim Laden)
    activeTab: 'dashboard'
  }),

  actions: {
    // Funktion zum Wechseln des Tabs
    setTab(tabName) {
      this.activeTab = tabName
      // Optional: Scrolle nach oben, wenn der Tab gewechselt wird
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },

    // Nützlich, um die Sidebar auf Mobile zu steuern
    toggleSidebar() {
      this.isSidebarOpen = !this.isSidebarOpen
    }
  },
  
  // Getter sind wie Computed Properties für deinen Store
  getters: {
    currentTabTitle: (state) => {
      const titles = {
        'dashboard': 'Übersicht',
        'attendance': 'Anwesenheit',
        'calendar': 'Kalender'
      }
      return titles[state.activeTab] || 'Home'
    }
  }
})