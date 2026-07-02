<script setup>
import { ref, onMounted } from 'vue'
import { useDocumentStore } from '@/stores/documentStore'
import WorkingHoursModal from '@/components/modals/WorkingHoursModal.vue'
import DocumentListModal from '@/components/modals/DocumentListModal.vue'
import { 
  FileText, 
  Shield, 
  FileSignature,
  Calendar
} from 'lucide-vue-next'

const documentStore = useDocumentStore()

const isWorkModalOpen = ref(false)
const isDocModalOpen = ref(false)     
const selectedCategory = ref(null)      

// Hinweis: IDs exakt auf Django-Choices gemappt
const categories = [
  { id: 'sozialversicherung', name: 'Sozialversicherungsnachweise', icon: Shield, color: 'text-amber-500', bg: 'bg-amber-50' },
  { id: 'arbeitsvertrag', name: 'Arbeitsvertrag', icon: FileSignature, color: 'text-purple-500', bg: 'bg-purple-50' },
  { id: 'zeitnachweise', name: 'Zeitnachweise', icon: Calendar, color: 'text-blue-600', bg: 'bg-blue-50' },
  { id: 'sonstiges', name: 'Sonstiges', icon: FileText, color: 'text-slate-500', bg: 'bg-slate-50' },

]

const handleCategoryClick = (cat) => {
  if (cat.id === 'zeitnachweise') {
    isWorkModalOpen.value = true
  } else {
    // Für alle echten Dokumententypen öffnen wir das neue Listen-Modal
    selectedCategory.value = cat
    isDocModalOpen.value = true
  }
}

onMounted(async () => {
  try {
    await documentStore.fetchEmployeeDocuments()
  } catch (err) {
    console.error("Fehler beim Laden der Dokumente:", err)
  }
})
</script>

<template>
  <div class="flex-1 overflow-y-auto bg-slate-50 p-8">
    <div class="max-w-6xl mx-auto space-y-8">
      
      <section class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="text-left">
          <h1 class="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <FileText class="w-6 h-6 text-blue-600" /> 
            <span>Meine Dokumente</span>
          </h1>
          <p class="text-slate-500 mt-1">Verwalte deine Abrechnungen, Verträge und Berichte.</p>
        </div>
      </section>

      <div class="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-4">
        <button 
          v-for="cat in categories" 
          :key="cat.id"
          @click="handleCategoryClick(cat)" 
          class="flex flex-col items-center p-5 bg-white border border-slate-200 rounded-2xl hover:shadow-md hover:border-blue-200 transition-all group"
        >
          <div :class="[cat.bg, cat.color, 'p-3 rounded-xl mb-3 group-hover:scale-110 transition-transform']">
            <component :is="cat.icon" class="w-6 h-6" />
          </div>
          <span class="text-xs font-bold text-slate-700 text-center w-full break-words hyphens-auto" lang="de">
              {{ cat.name }}
          </span>
        </button>
      </div>

      </div>

    <WorkingHoursModal 
      :is-open="isWorkModalOpen" 
      @close="isWorkModalOpen = false" 
    />

    <DocumentListModal 
      :is-open="isDocModalOpen"
      :category="selectedCategory"
      @close="isDocModalOpen = false"
    />
  </div>
</template>