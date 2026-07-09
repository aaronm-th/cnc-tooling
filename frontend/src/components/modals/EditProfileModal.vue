<script setup>
import { ref, watch } from 'vue'
// Eye und EyeOff importiert für die Passwort-Sichtbarkeit
import { User, X, Camera, Mail, Phone, Lock, Upload, Trash2, Eye, EyeOff, AlertCircle } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/authStore'
import { storeToRefs } from 'pinia'
import axios from 'axios'

const props = defineProps({
  isOpen: { type: Boolean, required: true }
})

const emit = defineEmits(['close'])

const authStore = useAuthStore()
const { user: userProfile } = storeToRefs(authStore)

// Lokaler Status für das Formular
const editForm = ref({})
const avatarPreview = ref(null)
const fileInput = ref(null)
const selectedFile = ref(null)
const avatarDeleted = ref(false)

// Status für die Passwort-Sichtbarkeit
const showOldPassword = ref(false)
const showNewPassword = ref(false)

const errorMessage = ref(null)

// Sobald das Modal öffnet, kopieren wir die aktuellen Daten
watch(() => props.isOpen, (newVal) => {
  if (newVal && userProfile.value) {
    editForm.value = { 
      email: userProfile.value.email || '',
      phone: userProfile.value.phone || '',
      oldPassword: '', // Altes Passwort Feld
      newPassword: ''  // Neues Passwort Feld
    }
    avatarPreview.value = userProfile.value.avatar
    avatarDeleted.value = false
    showOldPassword.value = false
    showNewPassword.value = false
    errorMessage.value = null
  }
})

const handleAvatarUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
    avatarDeleted.value = false

    const reader = new FileReader()
    reader.onload = (e) => {
      avatarPreview.value = e.target.result
    }
    reader.readAsDataURL(file)
  }
}

const removeAvatar = () => {
  avatarPreview.value = null
  selectedFile.value = null
  avatarDeleted.value = true
  if (fileInput.value) fileInput.value.value = ''
}

const triggerFileInput = () => fileInput.value.click()

const saveProfile = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const formData = new FormData()
    
    formData.append('email', editForm.value.email)
    formData.append('phone', editForm.value.phone)
    
    // Passwort-Logik anpassen: Nur mitsenden, wenn das neue Passwort ausgefüllt ist
    if (editForm.value.newPassword) {
      formData.append('old_password', editForm.value.oldPassword)
      formData.append('new_password', editForm.value.newPassword)
    }

    if (avatarDeleted.value) {
      formData.append('photo', '') 
    } else if (selectedFile.value) {
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
      
      // Hier fangen wir die Django-Validierungsfehler ab
      if (error.response?.data) {
        const data = error.response.data
        
        if (data.old_password) {
          // Falls das alte Passwort falsch war oder fehlte
          errorMessage.value = Array.isArray(data.old_password) ? data.old_password[0] : data.old_password
        } else if (data.email) {
          errorMessage.value = Array.isArray(data.email) ? data.email[0] : data.email
        } else if (data.message) {
          errorMessage.value = data.message
        } else {
          errorMessage.value = "Fehler beim Speichern der Profildaten."
        }
      } else {
        errorMessage.value = "Netzwerkfehler. Bitte versuche es später noch einmal."
      }
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
          <h2 class="text-xl font-bold text-slate-900">Profil bearbeiten</h2>
        </div>
        <button @click="$emit('close')" class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-full transition-colors">
          <X class="w-5 h-5" />
        </button>
      </div>
      
      <div class="p-8 overflow-y-auto max-h-[70vh]">
        
        <div v-if="errorMessage" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-700 animate-fadeIn">
          <AlertCircle class="w-5 h-5 mt-0.5 flex-shrink-0" />
          <div class="text-sm font-medium">
            {{ errorMessage }}
          </div>
        </div>

        <div class="flex flex-col items-center mb-8">
          <div class="relative group">
            <div class="w-24 h-24 rounded-full overflow-hidden border-4 border-slate-50 bg-slate-100 shadow-inner flex items-center justify-center">
              <img v-if="avatarPreview" :src="avatarPreview" class="w-full h-full object-cover" alt="Vorschau" referrerPolicy="no-referrer" />
              <User v-else class="w-10 h-10 text-slate-300" />
            </div>
            
            <div class="absolute bottom-0 right-0 flex gap-1">
              <button 
                v-if="avatarPreview"
                @click="removeAvatar"
                type="button"
                class="p-2 bg-red-600 text-white rounded-full shadow-lg hover:bg-red-700 transition-all transform hover:scale-110"
                title="Foto löschen"
              >
                <Trash2 class="w-4 h-4" />
              </button>

              <button 
                @click="triggerFileInput"
                type="button"
                class="p-2 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all transform hover:scale-110"
                title="Foto ändern"
              >
                <Camera class="w-4 h-4" />
              </button>
            </div>

            <input 
              type="file" 
              ref="fileInput" 
              class="hidden" 
              accept="image/*" 
              @change="handleAvatarUpload"
            />
          </div>
          <p class="text-xs text-slate-500 mt-3">Auf Icons klicken um ein Profilbild hochzuladen oder zu löschen.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <div class="space-y-1.5">
            <label class="text-xs font-bold tracking-wider text-slate-500"><span class="uppercase">E-Mail</span> (optional)</label>
            <div class="relative">
              <Mail class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                :value="editForm.email === null ? '' : editForm.email"
                @input="editForm.email = $event.target.value"
                type="email" 
                class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                placeholder="E-Mail Adresse eingeben..."
              />
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="text-xs font-bold tracking-wider text-slate-500"><span class="uppercase">Telefonnummer</span> (optional)</label>
            <div class="relative">
              <Phone class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                v-model="editForm.phone"
                type="tel" 
                class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                placeholder="Telefonnummer eingeben..."
              />
            </div>
          </div>

          <div class="md:col-span-2 my-1 border-t border-slate-100 pt-4">
            <h3 class="text-sm font-semibold text-slate-700 mb-1">Passwort ändern</h3>
          </div>

          <div class="space-y-1.5">
            <label class="text-xs font-bold uppercase tracking-wider text-slate-500">Altes Passwort</label>
            <div class="relative">
              <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                v-model="editForm.oldPassword"
                :type="showOldPassword ? 'text' : 'password'" 
                class="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                placeholder="Aktuelles Passwort"
              />
              <button 
                type="button"
                @click="showOldPassword = !showOldPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors focus:outline-none"
              >
                <Eye v-if="!showOldPassword" class="w-4 h-4" />
                <EyeOff v-else class="w-4 h-4" />
              </button>
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="text-xs font-bold uppercase tracking-wider text-slate-500">Neues Passwort</label>
            <div class="relative">
              <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                v-model="editForm.newPassword"
                :type="showNewPassword ? 'text' : 'password'" 
                class="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                placeholder="Neues Passwort"
              />
              <button 
                type="button"
                @click="showNewPassword = !showNewPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors focus:outline-none"
              >
                <Eye v-if="!showNewPassword" class="w-4 h-4" />
                <EyeOff v-else class="w-4 h-4" />
              </button>
            </div>
          </div>

        </div>
      </div>
      
      <div class="p-6 bg-slate-50 border-t border-slate-100 flex gap-3">
        <button 
          @click="$emit('close')"
          class="flex-1 py-3 px-4 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Abbruch
        </button>
        <button 
          @click="saveProfile"
          class="flex-1 py-3 px-4 bg-blue-600 rounded-xl text-sm font-semibold text-white hover:bg-blue-700 shadow-lg shadow-blue-500/20 transition-all flex items-center justify-center gap-2"
        >
          <Upload class="w-4 h-4" />
          Speichern
        </button>
      </div>
    </div>
  </div>
</template>


<style scoped>
/* Kleine Animation für das sanfte Einblenden der Fehlermeldung */
.animate-fadeIn {
  animation: fadeIn 0.2s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>