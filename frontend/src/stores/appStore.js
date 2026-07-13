import { defineStore } from 'pinia'

const getInitialTab = () => {
  const savedTab = localStorage.getItem('activeTab')
  return savedTab || 'dashboard'
}

export const useAppStore = defineStore('app', {
  state: () => ({
    activeTab: getInitialTab(),
    activeSubTab: null,
    isSidebarOpen: false
  }),

  actions: {

    setTab(tabName, subTabName = null) {
      this.activeTab = tabName
      localStorage.setItem('activeTab', tabName)
      
      // Unter-Tab setzen (oder leeren, wenn keiner mitgegeben wird)
      this.activeSubTab = subTabName

      if (typeof window !== 'undefined') {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
    },

    toggleSidebar() {
      this.isSidebarOpen = !this.isSidebarOpen
    }
  },
  
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