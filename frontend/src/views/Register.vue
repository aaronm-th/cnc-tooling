<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import { LayoutDashboard, User, Lock, Phone, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-vue-next'
import { f } from 'vue-router/dist/router-CWoNjPRp.mjs'

const router = useRouter()
const route = useRoute()

// Formulardaten (Jetzt getrennt nach Vor- und Nachname)
const token = ref('')
const firstname = ref('')
const lastname = ref('')
const password = ref('')
const phone = ref('')

const isLoading = ref(false)
const errorMessage = ref('')
const isSuccess = ref(false)

onMounted(async () => {
  const tokenFromUrl = route.query.token
  if (!tokenFromUrl) {
    errorMessage.value = 'Fehlender Einladungs-Link. Bitte wenden Sie sich an Ihren Vorgesetzten.'
    return
  }

  const cleanToken = (tokenFromUrl as string).trim().replace(/\u2060/g, '')

  try {
    isLoading.value = true
    // 1. Token bei Django prüfen und Namensdaten abholen
    const response = await axios.get(`http://127.0.0.1:8000/api/register/?token=${cleanToken}`)
    
    if (response.data.valid) {
      token.value = cleanToken
      firstname.value = response.data.firstname || ''
      lastname.value = response.data.lastname || ''
    }
  } catch (err: any) {
    errorMessage.value = err.response?.data?.message || 'Dieser Einladungs-Link ist nicht mehr gültig.'
    token.value = ''
  } finally {
    isLoading.value = false
  }
})

const handleRegister = async () => {
  if (!token.value) return

  isLoading.value = true
  errorMessage.value = ''

  try {
    // Da wir die Felder bereits getrennt haben, senden wir sie direkt 1:1 ans Backend
    const response = await axios.post('http://127.0.0.1:8000/api/register/', {
      token: token.value,
      firstname: firstname.value,
      lastname: lastname.value,
      password: password.value,
      phone: phone.value
    })

    if (response.data.success) {
      isSuccess.value = true
      setTimeout(() => {
        router.push('/login')
      }, 2000)
    }
  } catch (err: any) {
    console.error('Registration Error:', err)
    errorMessage.value = err.response?.data?.message || 'Registrierung fehlgeschlagen. Bitte versuche es erneut.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50 p-6">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/20 mb-4">
          <LayoutDashboard class="w-8 h-8 text-white" />
        </div>
        <h1 class="text-2xl font-bold text-slate-900">Profil einrichten</h1>
        <p class="text-slate-500 mt-2">Schließen Sie Ihre Registrierung ab</p>
      </div>

      <div class="bg-white p-8 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100">
        
        <!-- Fehlermeldung -->
        <div v-if="errorMessage" class="mb-6 p-4 bg-red-50 border border-red-100 rounded-2xl flex items-center gap-3 text-red-600 text-sm animate-shake">
          <AlertCircle class="w-5 h-5 flex-shrink-0" />
          <p>{{ errorMessage }}</p>
        </div>

        <!-- Erfolgsmeldung -->
        <div v-if="isSuccess" class="mb-6 p-4 bg-green-50 border border-green-100 rounded-2xl flex items-center gap-3 text-green-600 text-sm">
          <CheckCircle2 class="w-5 h-5 flex-shrink-0" />
          <p>Account erfolgreich aktiviert! Weiterleitung zum Login...</p>
        </div>

        <!-- Formular -->
        <form v-if="token && !isSuccess" @submit.prevent="handleRegister" class="space-y-5">
          
          <!-- NEU: Vorname und Nachname nebeneinander im Grid -->
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-semibold text-slate-700 ml-1">Vorname</label>
              <div class="relative group">
                <User class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                <input 
                  v-model="firstname"
                  type="text" 
                  required
                  placeholder="John"
                  class="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all text-sm"
                />
              </div>
            </div>

            <div class="space-y-2">
              <label class="text-sm font-semibold text-slate-700 ml-1">Nachname</label>
              <div class="relative group">
                <User class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                <input 
                  v-model="lastname"
                  type="text" 
                  required
                  placeholder="Doe"
                  class="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all text-sm"
                />
              </div>
            </div>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 ml-1">Telefonnummer (optional)</label>
            <div class="relative group">
              <Phone class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
              <input 
                v-model="phone"
                type="tel" 
                placeholder="+49 123 456789"
                class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
            </div>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 ml-1">Passwort festlegen</label>
            <div class="relative group">
              <Lock class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
              <input 
                v-model="password"
                type="password" 
                required
                placeholder="••••••••"
                class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
            </div>
          </div>

          <button 
            type="submit"
            :disabled="isLoading"
            class="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-2xl font-bold shadow-lg shadow-blue-500/30 flex items-center justify-center gap-2 group transition-all mt-4 cursor-pointer"
          >
            <span v-if="isLoading" class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <span v-else>Registrierung abschließen</span>
            <ArrowRight v-if="!isLoading" class="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </form>

        <div class="mt-8 pt-8 border-t border-slate-100 text-center">
          <p class="text-sm text-slate-500">
            Du hast funktionierende Zugangsdaten? 
            <router-link to="/login" class="font-bold text-blue-600 hover:underline">Anmelden</router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
.animate-shake {
  animation: shake 0.2s ease-in-out 0s 2;
}
</style>