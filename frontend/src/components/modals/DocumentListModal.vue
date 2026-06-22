<script setup>
import { computed } from 'vue'
import { useDocumentStore } from '@/stores/documentStore'
import { storeToRefs } from 'pinia'
import { X, Download, FileText, Loader2 } from 'lucide-vue-next'

const props = defineProps({
  isOpen: Boolean,
  category: {
    type: Object,
    default: () => ({ id: '', name: '', icon: null })
  }
})

const emit = defineEmits(['close'])

const documentStore = useDocumentStore()
const { documents, isDownloading } = storeToRefs(documentStore)

// Filtert die Dokumente aus dem Store passend zur angeklickten Kategorie-ID
const filteredDocuments = computed(() => {
  return documents.value.filter(doc => doc.document_type === props.category?.id)
})

const handleDownload = async (docId, filename) => {
  try {
    await documentStore.downloadEmployeeDocument(docId, filename)
  } catch (err) {
    alert(documentStore.lastError || "Download fehlgeschlagen")
  }
}
</script>

<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-in"
  >
    <div class="bg-white w-full max-w-xl rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col max-h-[85vh]">
      
      <div class="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50">
        <div class="flex items-center gap-3 text-left">
          <div v-if="category?.icon" class="p-2 bg-blue-50 text-blue-600 rounded-xl">
            <component :is="category.icon" class="w-5 h-5" />
          </div>
          <div>
            <h3 class="text-lg font-bold text-slate-900">{{ category?.name }}</h3>
            <p class="text-xs text-slate-500">Verfügbare Dokumente in dieser Kategorie</p>
          </div>
        </div>
        <button 
          @click="emit('close')" 
          class="p-1.5 hover:bg-slate-200 text-slate-400 hover:text-slate-600 rounded-lg transition-colors"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <div class="p-6 overflow-y-auto flex-1">
        
        <div v-if="filteredDocuments.length === 0" class="text-center py-8 text-slate-400">
          <FileText class="w-12 h-12 mx-auto text-slate-200 mb-2" />
          <p class="font-medium text-slate-500 text-sm">Keine Dokumente hinterlegt</p>
          <p class="text-xs text-slate-400 mt-1">In dieser Kategorie wurden noch keine Dateien hochgeladen.</p>
        </div>

        <div v-else class="divide-y divide-slate-100">
          <div 
            v-for="doc in filteredDocuments" 
            :key="doc.id" 
            class="flex items-center justify-between py-3.5 first:pt-0 last:pb-0"
          >
            <div class="flex items-center gap-3 text-left min-w-0 flex-1">
              <div class="bg-slate-100 p-2 rounded-lg text-slate-500 shrink-0">
                <FileText class="w-5 h-5" />
              </div>
              <div class="min-w-0 flex-1">
                <p class="font-medium text-slate-700 text-sm truncate" :title="doc.original_filename">
                  {{ doc.original_filename }}
                </p>
                <p class="text-xs text-slate-400 mt-0.5">
                  {{ new Date(doc.uploaded_at).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) }}
                </p>
              </div>
            </div>
            
            <button 
              @click="handleDownload(doc.id, doc.original_filename)"
              :disabled="isDownloading"
              class="p-2 hover:bg-blue-50 text-slate-500 hover:text-blue-600 rounded-xl transition-all disabled:opacity-50 shrink-0 ml-4"
            >
              <Loader2 v-if="isDownloading" class="w-5 h-5 animate-spin" />
              <Download v-else class="w-5 h-5" />
            </button>
          </div>
        </div>

      </div>

      <div class="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
        <button 
          @click="emit('close')"
          class="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl font-medium text-sm transition-colors shadow-sm"
        >
          Schließen
        </button>
      </div>

    </div>
  </div>
</template>