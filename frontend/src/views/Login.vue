<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios' // Axios importieren
import { LayoutDashboard, Mail, Lock, ArrowRight, AlertCircle, Clock } from 'lucide-vue-next'

const router = useRouter()
const username = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('') // Für Feedback bei Fehlern

const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'


const handleLogin = async () => {
  isLoading.value = true
  errorMessage.value = ''
  
  try {
    // 1. POST Request an dein Django Backend
    // Nutze die IP 127.0.0.1 wegen des Safari/CORS-Themas
    const response = await axios.post('http://127.0.0.1:8000/api/login/', {
      username: username.value,
      password: password.value
    })

    if (response.data.success) {
      // 2. JWT Tokens im LocalStorage speichern
      localStorage.setItem('access_token', response.data.tokens.access)
      localStorage.setItem('refresh_token', response.data.tokens.refresh)
      
      // 3. User-Daten speichern
      localStorage.setItem('user', JSON.stringify(response.data.user))

      // 4. Weiterleitung
      router.push('/')
    }
  } catch (err: any) {
    // Fehlerbehandlung
    console.error('Login Error:', err)
    errorMessage.value = err.response?.data?.message || 'Login fehlgeschlagen. Bitte prüfe deine Daten.'
  } finally {
    isLoading.value = false
  }
}
</script>


<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50 p-6">
    <div class="w-full max-w-md relative"> <!-- Hinzugefügt: 'relative' -->
      
      <!-- Der Logo-Container: Schwebend über der Box -->
      <div class="absolute -top-12 left-1/2 -translate-x-1/2 z-10">
        <div class="w-24 h-24 bg-white p-3 rounded-full shadow-2xl shadow-blue-900/10 border border-slate-100 flex items-center justify-center">
          <img 
            :src="`${backendUrl}/media/logos/jv_logo.png`" 
            alt="Logo"
            class="w-full h-full object-contain filter drop-shadow-[0_4px_12px_rgba(0,0,0,0.08)]"
          />
        </div>
      </div>

      <!-- Login-Box (mit pt-20, um Platz für das Logo zu schaffen) -->
      <div class="bg-white p-8 pt-20 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 relative">
        
        <!-- Titel hinzugefügt, da das Logo jetzt oben schwebt -->
        <div class="text-center mb-8">
          <h1 class="text-2xl font-extrabold text-slate-950 tracking-tighter">Anmelden</h1>
        </div>

        <div v-if="errorMessage" class="mb-6 p-4 bg-red-50 border border-red-100 rounded-2xl flex items-center gap-3 text-red-600 text-sm animate-shake">
          <AlertCircle class="w-5 h-5 flex-shrink-0" />
          <p>{{ errorMessage }}</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-6">
          <!-- ... Rest des Formulars bleibt identisch ... -->
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 ml-1">Nutzername</label>
            <div class="relative group">
              <Mail class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
              <input 
                v-model="username"
                type="text" 
                required
                placeholder="Nutzername"
                class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
            </div>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between ml-1">
              <label class="text-sm font-semibold text-slate-700">Passwort</label>
            </div>
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
            class="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-2xl font-bold shadow-lg shadow-blue-500/30 flex items-center justify-center gap-2 group transition-all"
          >
            <span v-if="isLoading" class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <span v-else>Anmelden</span>
            <ArrowRight v-if="!isLoading" class="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </form>

      </div>


<div class="mt-8 flex flex-col items-center gap-4">
  <router-link 
    to="/terminal" 
    class="inline-flex items-center gap-2 px-5 py-3 bg-slate-100/80 hover:bg-slate-200/80 text-slate-700 rounded-xl text-sm font-bold uppercase tracking-wider text-[11px] transition-all"
  >
    <Clock class="w-4 h-4" />
    Terminal
  </router-link>
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