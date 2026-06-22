<script setup>
import { ref, watch } from 'vue'
import { User, X, Camera, Mail, Phone, Lock, Upload } from 'lucide-vue-next'
// 1. Store importieren
import { useAuthStore } from '@/stores/authStore'
import { storeToRefs } from 'pinia'
import axios from 'axios'

const props = defineProps({
  isOpen: { type: Boolean, required: true }
})

const emit = defineEmits(['close'])

// 2. Store initialisieren
const authStore = useAuthStore()
const { user: userProfile } = storeToRefs(authStore)

// Lokaler Status für das Formular
const editForm = ref({})
const avatarPreview = ref(null)
const fileInput = ref(null)
const selectedFile = ref(null) // Speichert die echte Datei für den Upload

// Sobald das Modal öffnet, kopieren wir die aktuellen Daten aus Pinia
watch(() => props.isOpen, (newVal) => {
  if (newVal && userProfile.value) {
    editForm.value = { 
      email: userProfile.value.email,
      phone: userProfile.value.phone,
      password: '' // Passwort immer leer starten
    }
    avatarPreview.value = userProfile.value.avatar
  }
})

const handleAvatarUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file // Datei für später speichern
    const reader = new FileReader()
    reader.onload = (e) => {
      avatarPreview.value = e.target.result // Vorschau im Modal
    }
    reader.readAsDataURL(file)
  }
}

const triggerFileInput = () => fileInput.value.click()

// 3. Die Speicher-Logik
const saveProfile = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const formData = new FormData()
    
    formData.append('email', editForm.value.email)
    formData.append('phone', editForm.value.phone)
    if (editForm.value.password) {
      formData.append('password', editForm.value.password)
    }
    if (selectedFile.value) {
      formData.append('photo', selectedFile.value)
    }

    const response = await axios.patch(
      `${import.meta.env.VITE_API_URL}/api/user/update/`, 
      formData, 
      { headers: { Authorization: `Bearer ${token}` } }
    )


    const updatedData = response.data.user ? response.data.user : response.data;

    authStore.user = {
      ...authStore.user,
      ...updatedData
    };

    
    emit('close')
  } catch (error) {
    console.error("Update fehlgeschlagen:", error)
    alert("Fehler beim Speichern!")
  }
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
    <div @click="$emit('close')" class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"></div>
    <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
      <div class="p-6 border-b border-slate-100 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-blue-50 rounded-lg">
            <User class="w-5 h-5 text-blue-600" />
          </div>
          <h2 class="text-xl font-bold text-slate-900">Edit Profile</h2>
        </div>
        <button @click="$emit('close')" class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-full transition-colors">
          <X class="w-5 h-5" />
        </button>
      </div>
      
      <div class="p-8 overflow-y-auto max-h-[70vh]">
        <!-- Avatar Upload Section -->
        <div class="flex flex-col items-center mb-8">
          <div class="relative group">
            <div class="w-24 h-24 rounded-full overflow-hidden border-4 border-slate-50 bg-slate-100 shadow-inner flex items-center justify-center">
              <img v-if="avatarPreview" :src="avatarPreview" class="w-full h-full object-cover" alt="Avatar Preview" referrerPolicy="no-referrer" />
              <User v-else class="w-10 h-10 text-slate-300" />
            </div>
            <button 
              @click="triggerFileInput"
              class="absolute bottom-0 right-0 p-2 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all transform hover:scale-110"
            >
              <Camera class="w-4 h-4" />
            </button>
            <input 
              type="file" 
              ref="fileInput" 
              class="hidden" 
              accept="image/*" 
              @change="handleAvatarUpload"
            />
          </div>
          <p class="text-xs text-slate-500 mt-3">Click the camera icon to upload a profile picture</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="space-y-1.5">
            <label class="text-xs font-bold uppercase tracking-wider text-slate-500">Email Address</label>
            <div class="relative">
              <Mail class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                v-model="editForm.email"
                type="email" 
                class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                placeholder="alex@example.com"
              />
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="text-xs font-bold uppercase tracking-wider text-slate-500">Phone Number</label>
            <div class="relative">
              <Phone class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                v-model="editForm.phone"
                type="tel" 
                class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                placeholder="+1 (555) 000-0000"
              />
            </div>
          </div>

          <div class="space-y-1.5 md:col-span-2">
            <label class="text-xs font-bold uppercase tracking-wider text-slate-500">Password</label>
            <div class="relative">
              <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                v-model="editForm.password"
                type="password" 
                class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                placeholder="••••••••"
              />
            </div>
            <p class="text-[10px] text-slate-400 mt-1">Leave as is to keep your current password</p>
          </div>
        </div>
      </div>
      
      <div class="p-6 bg-slate-50 border-t border-slate-100 flex gap-3">
        <button 
          @click="$emit('close')"
          class="flex-1 py-3 px-4 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Cancel
        </button>
        <button 
          @click="saveProfile"
          class="flex-1 py-3 px-4 bg-blue-600 rounded-xl text-sm font-semibold text-white hover:bg-blue-700 shadow-lg shadow-blue-500/20 transition-all flex items-center justify-center gap-2"
        >
          <Upload class="w-4 h-4" />
          Save Profile
        </button>
      </div>
    </div>
  </div>
</template>
