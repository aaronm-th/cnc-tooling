<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios' // Axios importieren
import { LayoutDashboard, Mail, Lock, ArrowRight, AlertCircle, Clock } from 'lucide-vue-next'

const router = useRouter()
const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('') // Für Feedback bei Fehlern

const handleLogin = async () => {
  isLoading.value = true
  errorMessage.value = ''
  
  try {
    // 1. POST Request an dein Django Backend
    // Nutze die IP 127.0.0.1 wegen des Safari/CORS-Themas
    const response = await axios.post('http://127.0.0.1:8000/api/login/', {
      email: email.value,
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
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/20 mb-4">
          <LayoutDashboard class="w-8 h-8 text-white" />
        </div>
        <h1 class="text-2xl font-bold text-slate-900">Willkommen zurück</h1>
        <p class="text-slate-500 mt-2">Melden Sie sich bei Ihrem Corporate Connect-Konto an</p>
      </div>

      <div class="bg-white p-8 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100">
        
        <div v-if="errorMessage" class="mb-6 p-4 bg-red-50 border border-red-100 rounded-2xl flex items-center gap-3 text-red-600 text-sm animate-shake">
          <AlertCircle class="w-5 h-5 flex-shrink-0" />
          <p>{{ errorMessage }}</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-6">
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 ml-1">Email Addresse</label>
            <div class="relative group">
              <Mail class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
              <input 
                v-model="email"
                type="email" 
                required
                placeholder="name@company.com"
                class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
            </div>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between ml-1">
              <label class="text-sm font-semibold text-slate-700">Passwort</label>
              <a href="#" class="text-xs font-semibold text-blue-600 hover:underline">Passwort vergessen?</a>
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

        <div class="mt-8 pt-8 border-t border-slate-100 text-center">
          <p class="text-sm text-slate-500">
            Sie haben noch keinen Account? 
            <router-link to="/register" class="font-bold text-blue-600 hover:underline">Account erstellen</router-link>
          </p>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-8 flex flex-col items-center gap-4">
        <router-link 
          to="/terminal" 
          class="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-bold uppercase tracking-widest transition-all"
        >
          <Clock class="w-4 h-4" />
          Terminal
        </router-link>
        <p class="text-xs text-slate-400">
          &copy; 2026 Corporate Connect Inc. All rights reserved.
        </p>
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