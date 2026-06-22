<script setup>
import { ref, watch } from 'vue'
import { useDocumentStore } from '@/stores/documentStore' 
import { X, UploadCloud, File, AlertCircle } from 'lucide-vue-next'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  member: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'success'])
const documentStore = useDocumentStore()

const fileInput = ref(null)
const selectedFile = ref(null)
const documentType = ref('')
const isDragging = ref(false)
const errorMessage = ref('')
const isSubmitting = ref(false)

const DOCUMENT_TYPES = [
  { value: 'sozialversicherung', label: 'Sozialversicherungsnachweis' },
  { value: 'arbeitsvertrag', label: 'Arbeitsvertrag' },
  { value: 'ausweis', label: 'Ausweis / Identifikationsdokument' },
  { value: 'bescheinigung', label: 'Ärztliche Bescheinigung' },
  { value: 'sonstiges', label: 'Sonstiges' }
]

// Reset des Formulars bei Schließen/Öffnen
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    selectedFile.value = null
    documentType.value = ''
    errorMessage.value = ''
    isSubmitting.value = false
  }
})

// Datei-Validierung (Max 5MB, PDF/Bilder)
const validateAndSetFile = (file) => {
  errorMessage.value = ''
  if (!file) return

  const allowedExtensions = ['application/pdf', 'image/jpeg', 'image/png']
  if (!allowedExtensions.includes(file.type)) {
    errorMessage.value = 'Ungültiges Format. Nur PDF, JPG und PNG sind erlaubt.'
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    errorMessage.value = 'Die Datei ist zu groß. Maximal 5 MB erlaubt.'
    return
  }

  selectedFile.value = file
}

// Drag & Drop Handler
const handleDrop = (e) => {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    validateAndSetFile(files[0])
  }
}

const handleFileSelect = (e) => {
  const files = e.target.files
  if (files.length > 0) {
    validateAndSetFile(files[0])
  }
}

const triggerFileSelect = () => {
  fileInput.value.click()
}

const removeFile = () => {
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

// Submit-Logik
const handleSubmit = async () => {
  if (!selectedFile.value || !documentType.value || !props.member?.id) return

  isSubmitting.value = true
  errorMessage.value = ''

  const formData = new FormData()
  formData.append('document', selectedFile.value)
  formData.append('document_type', documentType.value)

  try {
    // Ruft die Aktion in deinem Pinia Store auf
    await documentStore.uploadEmployeeDocument(props.member.id, formData)
    emit('success')
    emit('close')
  } catch (error) {
    console.error("Fehler beim Dokumentenupload:", error)
    errorMessage.value = error.response?.data?.detail || 'Fehler beim Upload des Dokuments.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
  >
    <div class="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden">
      
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 class="font-bold text-lg text-slate-900">Dokument hochladen</h3>
          <p class="text-xs text-slate-500 mt-0.5">für {{ member?.name }}</p>
        </div>
        <button 
          type="button"
          class="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          @click="emit('close')"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <form class="p-6 space-y-5" @submit.prevent="handleSubmit">
        
        <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-100 rounded-xl flex items-start gap-2.5 text-sm text-red-700">
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ errorMessage }}</span>
        </div>

        <div class="space-y-1.5">
          <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Dokumententyp</label>
          <select 
            v-model="documentType"
            required
            class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800 font-medium appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2364748b%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E')] bg-[length:1rem_1rem] bg-[right_1rem_center] bg-no-repeat"
          >
            <option value="" disabled selected>Bitte Typ auswählen...</option>
            <option v-for="type in DOCUMENT_TYPES" :key="type.value" :value="type.value">
              {{ type.label }}
            </option>
          </select>
        </div>

        <div class="space-y-1.5">
          <label class="text-xs font-bold uppercase text-slate-500 tracking-wider">Datei</label>
          
          <div 
            v-if="!selectedFile"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileSelect"
            :class="[
              'border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[160px]',
              isDragging 
                ? 'border-blue-500 bg-blue-50/40 text-blue-600 shadow-inner' 
                : 'border-slate-200 bg-slate-50/50 hover:bg-slate-50 hover:border-slate-300 text-slate-500'
            ]"
          >
            <input 
              ref="fileInput"
              type="file" 
              class="hidden" 
              accept=".pdf,.png,.jpg,.jpeg"
              @change="handleFileSelect"
            />
            
            <div :class="['p-3 rounded-xl mb-3 transition-colors', isDragging ? 'bg-blue-100 text-blue-600' : 'bg-white shadow-sm text-slate-400 border border-slate-100']">
              <UploadCloud class="w-6 h-6" />
            </div>
            <p class="text-sm font-bold text-slate-800">Datei hierher ziehen oder anklicken</p>
            <p class="text-[11px] text-slate-400 mt-1 font-medium">PDF, JPG oder PNG bis maximal 5 MB</p>
          </div>

          <div v-else class="flex items-center justify-between p-4 bg-slate-50 border border-slate-200 rounded-xl">
            <div class="flex items-center gap-3 min-w-0">
              <div class="p-2 bg-blue-100 text-blue-600 rounded-lg">
                <File class="w-5 h-5" />
              </div>
              <div class="min-w-0">
                <p class="text-sm font-bold text-slate-800 truncate">{{ selectedFile.name }}</p>
                <p class="text-xs text-slate-400 font-medium">{{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB</p>
              </div>
            </div>
            <button 
              type="button"
              @click="removeFile"
              class="p-1 hover:bg-slate-200 rounded-md text-slate-400 hover:text-slate-600 transition-all cursor-pointer"
            >
              <X class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div class="pt-2 border-t border-slate-100 flex items-center justify-end gap-3">
          <button 
            type="button" 
            :disabled="isSubmitting"
            class="px-4 py-2 hover:bg-slate-100 rounded-xl text-slate-500 text-sm font-bold transition-all cursor-pointer disabled:opacity-50"
            @click="emit('close')"
          >
            Abbrechen
          </button>
          <button 
            type="submit" 
            :disabled="!selectedFile || !documentType || isSubmitting"
            class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none disabled:cursor-not-allowed rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-900/20 cursor-pointer flex items-center gap-2"
          >
            <span v-if="isSubmitting" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            {{ isSubmitting ? 'Wird hochgeladen...' : 'Dokument speichern' }}
          </button>
        </div>

      </form>
    </div>
  </div>
</template>