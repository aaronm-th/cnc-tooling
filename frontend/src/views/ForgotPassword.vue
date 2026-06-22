<script setup>
import { ref } from 'vue'
import { LayoutDashboard, Mail, ArrowLeft, Send, CheckCircle2 } from 'lucide-vue-next'

const email = ref('')
const isLoading = ref(false)
const isSubmitted = ref(false)

const handleResetRequest = async () => {
  if (!email.value) return
  
  isLoading.value = true
  
  // Simulate API call
  setTimeout(() => {
    isLoading.value = false
    isSubmitted.value = true
  }, 1500)
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50 p-6">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/20 mb-4">
          <LayoutDashboard class="w-8 h-8 text-white" />
        </div>
        <h1 class="text-2xl font-bold text-slate-900">
          Reset Password
        </h1>
        <p class="text-slate-500 mt-2">
          Enter your email to receive recovery instructions
        </p>
      </div>

      <!-- Success State -->
      <div 
        v-if="isSubmitted"
        class="bg-white p-8 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 text-center animate-in fade-in zoom-in duration-300"
      >
        <div class="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <CheckCircle2 class="w-8 h-8" />
        </div>
        <h2 class="text-xl font-bold text-slate-900 mb-2">
          Check your email
        </h2>
        <p class="text-slate-500 mb-8">
          We've sent password reset instructions to <br>
          <span class="font-semibold text-slate-900">{{ email }}</span>
        </p>
        
        <router-link 
          to="/login"
          class="w-full py-4 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl font-bold flex items-center justify-center gap-2 transition-all"
        >
          <ArrowLeft class="w-5 h-5" />
          Back to Login
        </router-link>
      </div>

      <!-- Form State -->
      <div 
        v-else
        class="bg-white p-8 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100"
      >
        <form
          class="space-y-6"
          @submit.prevent="handleResetRequest"
        >
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 ml-1">Email Address</label>
            <div class="relative group">
              <Mail class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
              <input 
                v-model="email"
                type="email" 
                required
                placeholder="name@company.com"
                class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              >
            </div>
          </div>

          <button 
            type="submit"
            :disabled="isLoading || !email"
            class="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-2xl font-bold shadow-lg shadow-blue-500/30 flex items-center justify-center gap-2 group transition-all"
          >
            <span
              v-if="isLoading"
              class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"
            />
            <template v-else>
              <span>Send Instructions</span>
              <Send class="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
            </template>
          </button>
        </form>

        <div class="mt-8 pt-8 border-t border-slate-100 text-center">
          <router-link
            to="/login"
            class="inline-flex items-center gap-2 text-sm font-bold text-blue-600 hover:underline"
          >
            <ArrowLeft class="w-4 h-4" />
            Back to Login
          </router-link>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-8 text-center text-xs text-slate-400">
        <p>&copy; 2026 Corporate Connect Inc. All rights reserved.</p>
      </div>
    </div>
  </div>
</template>
