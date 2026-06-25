<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Bell, CheckCircle, Info, AlertTriangle, X } from 'lucide-vue-next'
import { useNotificationStore } from '@/stores/notificationStore'
import { useAppStore } from '@/stores/appStore' // WICHTIG: Den AppStore für die Tabs importieren

const notificationStore = useNotificationStore()
const appStore = useAppStore() // Initialisieren

const displayNotifications = ref([]) 
let intervalId = null

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['toggle', 'close'])

// Beim Öffnen laden wir den aktuellen Stand aus dem Store in die lokale Anzeige
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    displayNotifications.value = [...notificationStore.notifications]
  }
})

// Sofortiges Entfernen aus der UI, wenn eine Nachricht gelöscht wird (X-Button)
watch(() => notificationStore.notifications.length, () => {
  displayNotifications.value = displayNotifications.value.filter(dn => 
    notificationStore.notifications.some(n => n.id === dn.id)
  )
}, { deep: true })

// Polling & Daten Initialisierung
onMounted(() => {
  notificationStore.fetchNotifications()
  intervalId = setInterval(() => {
    notificationStore.fetchNotifications()
  }, 60000)
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})

// Zentrale Klick-Logik
const handleNotificationClick = async (notification) => {
  // 1. Als gelesen markieren (Backend & Store Update)
  await notificationStore.markAsRead(notification.id)
  
  // 2. Tab wechseln über den globalen appStore
  if (notification.link_to) {
    appStore.setTab(notification.link_to)
    
    // 3. Dropdown schließen für bessere UX
    emit('close')
  }
}

// Styling Helper
const getNotificationIcon = (type) => {
  switch (type) {
    case 'success': return CheckCircle
    case 'warning': return AlertTriangle
    case 'info': return Info
    case 'error': return X
    default: return Bell
  }
}

const getNotificationColor = (type) => {
  switch (type) {
    case 'success': return 'text-emerald-500 bg-emerald-50'
    case 'warning': return 'text-amber-500 bg-amber-50'
    case 'info': return 'text-blue-500 bg-blue-50'
    case 'error': return 'text-red-500 bg-red-50'
    default: return 'text-slate-500 bg-slate-50'
  }
}
</script>

<template>
  <div class="relative">
    <button 
      class="p-2 text-slate-500 hover:bg-slate-50 rounded-full relative transition-colors focus:outline-none"
      :class="{ 'bg-slate-100 text-slate-800': isOpen }"
      @click="emit('toggle')"
    >
      <Bell class="w-5 h-5" />
      <span 
        v-if="notificationStore.unreadCount > 0" 
        class="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white"
      />
    </button>

    <div 
      v-if="isOpen" 
      class="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden z-50"
    >
      <div class="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <h3 class="font-bold text-slate-900 text-sm">Benachrichtigungen</h3>
        
        <div class="flex gap-4">
          <button 
            v-if="notificationStore.unreadCount > 0"
            class="text-[10px] font-bold uppercase tracking-widest text-blue-600 hover:text-blue-700 transition-colors"
            @click="notificationStore.markAllAsRead"
          >
            Alle öffnen
          </button>

          <button 
            v-if="displayNotifications.length > 0"
            class="text-[10px] font-bold uppercase tracking-widest text-red-500 hover:text-red-600 transition-colors"
            @click="notificationStore.clearAll" 
          >
            Alle löschen
          </button>
        </div>
      </div>

      <div class="max-h-[400px] overflow-y-auto custom-scrollbar">
        <div v-if="displayNotifications.length === 0" class="p-8 text-center">
          <Bell class="w-8 h-8 text-slate-200 mx-auto mb-2" />
          <p class="text-xs text-slate-400">Keine neuen Benachrichtigungen</p>
        </div>

        <div 
            v-for="notification in displayNotifications" 
            :key="notification.id"
            class="p-4 border-b border-slate-50 hover:bg-slate-50 transition-all relative group cursor-pointer"
            :class="{ 
                'bg-blue-50/30': !notification.read,
                'opacity-60 grayscale-[0.2]': notification.read 
            }"
            @click="handleNotificationClick(notification)"
        >
          <div class="flex gap-3">
            <div :class="['p-2 rounded-xl shrink-0 h-fit', getNotificationColor(notification.type)]">
              <component :is="getNotificationIcon(notification.type)" class="w-4 h-4" />
            </div>
            <div class="space-y-0.5 pr-4">
              <p class="text-sm font-bold text-slate-900 leading-tight">
                {{ notification.title }}
              </p>
              <p class="text-xs text-slate-500 leading-normal line-clamp-3">
                {{ notification.message }}
              </p>
              <p class="text-[10px] text-slate-400 font-medium pt-1">
                {{ notification.time }}
              </p>
            </div>
          </div>

          <button 
            class="absolute top-4 right-3 p-1 text-slate-500 hover:text-slate-800 opacity-50 group-hover:opacity-100 transition-all"
            @click.stop="notificationStore.clearNotification(notification.id)"
          >
            <X class="w-3.5 h-3.5" />
          </button>

          <div 
            v-if="!notification.read" 
            class="absolute top-4 right-4 w-1.5 h-1.5 bg-blue-600 rounded-full group-hover:opacity-0 transition-opacity"
          />
        </div>
      </div>

    </div>

    <div v-if="isOpen" class="fixed inset-0 z-40" @click="emit('close')" />
  </div>
</template>