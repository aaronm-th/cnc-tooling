import { defineStore } from 'pinia'

const getInitialTab = () => {
  const savedTab = localStorage.getItem('activeTab')
  if (savedTab) return savedTab


  return savedTab || 'dashboard'
}


export const useAppStore = defineStore('app', {
  state: () => ({
    activeTab: getInitialTab(),
  }),

  actions: {
    // Funktion zum Wechseln des Tabs
    setTab(tabName) {
      this.activeTab = tabName
      // Direkt im Store speichern, dann brauchst du den Watcher in der Hauptkomponente nicht mal mehr!
      localStorage.setItem('activeTab', tabName)
      
      if (typeof window !== 'undefined') {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
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