<script setup>
  import { ref, watch, onMounted } from 'vue'
  import { 
    ChevronRight, 
    ListChecks, 
    Edit3, 
    Bold,
    Italic,
    List,
    ListOrdered,
    Plus,
    Trash2,
    Square,
    CheckSquare
  } from 'lucide-vue-next'
  import { useAuthStore } from '@/stores/authStore'
  import { storeToRefs } from 'pinia'
  import { useClock } from '@/composables/useClock'

  defineProps({
    quickLinks: { type: Array, required: true }
  })

  defineEmits(['changeTab'])

  const authStore = useAuthStore()
  // 'todos' kommt jetzt direkt reaktiv aus dem Pinia Store!
  const { user, notes: storeNotes, todos } = storeToRefs(authStore)
  const { formattedTime, formattedDate } = useClock()

  // --- SCRATCHPAD STATE & LOGIC ---
  const editorRef = ref(null)
  const notesHtml = ref('')
  const isSaving = ref(false)

  const format = (command) => {
    document.execCommand(command, false, null)
    editorRef.value?.focus()
    updateContent()
  }

  const updateContent = () => {
    if (editorRef.value) {
      // textContent holt den reinen Text ohne HTML-Tags.
      // replace(/\u200B/g, '') entfernt unsichtbare, breitenlose Leerzeichen, die Browser gern nutzen
      const pureText = editorRef.value.textContent.replace(/\u200B/g, '').trim()
      
      // Wenn kein echter Text drin steht oder das Feld nur aus Umbrüchen/Leerzeichen besteht
      if (!pureText || editorRef.value.innerHTML === '<br>') {
        editorRef.value.innerHTML = ''
      }
      
      notesHtml.value = editorRef.value.innerHTML
    }
  }

  // --- TODO LIST STATE & LOGIC (JETZT ÜBER STORE) ---
  const newTodoText = ref('')

  const handleAddTodo = async () => {
    const text = newTodoText.value.trim()
    if (!text) return
    
    await authStore.addTodo(text)
    newTodoText.value = ''
  }

  const handleToggleTodo = async (todo) => {
    // Wir übergeben die ID und den invertierten Status
    await authStore.toggleTodo(todo.id, !todo.completed)
  }

  const handleDeleteTodo = async (id) => {
    await authStore.deleteTodo(id)
  }

  // --- INITIALISIERUNG BEIM LADEN ---
  onMounted(async () => {
    // Notizen und To-Dos parallel von der API laden
    await Promise.all([
      authStore.fetchNotes(),
      authStore.fetchTodos()
    ])
    
    if (editorRef.value) {
      // Falls storeNotes leer oder null ist, setzen wir einen leeren String ein
      const initialContent = storeNotes.value || ''
      editorRef.value.innerHTML = initialContent
      notesHtml.value = initialContent
    }
  })

  // --- WATCHER FÜR SCRATCHPAD ---
  let saveTimeout = null
  watch(notesHtml, (newHtml) => {
    if (newHtml === storeNotes.value) return
    isSaving.value = true
    if (saveTimeout) clearTimeout(saveTimeout)
    
    saveTimeout = setTimeout(async () => {
      try {
        await authStore.updateNotes(newHtml)
        const userId = user.value?.id || 'guest'
        localStorage.setItem(`dashboard_scratchpad_${userId}`, newHtml)
      } catch (error) {
        console.error("Speichern fehlgeschlagen:", error)
      } finally {
        isSaving.value = false
      }
    }, 1000)
  })
</script>

<template>
  <div class="flex-1 overflow-y-auto p-4 sm:p-8 bg-slate-50">
    <div class="max-w-6xl mx-auto space-y-8">
      
      <!-- HEADING SECTION -->
      <section class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold text-slate-900 tracking-tight">
            Guten Morgen, {{ user?.name ? user.name.split(' ')[0] : 'User' }}!
          </h1>
          <p class="text-slate-500 mt-1 flex items-center gap-2">
            <span>{{ formattedDate }}</span>
            <span class="text-slate-300">•</span>
            <span class="font-semibold text-blue-600">
              {{ formattedTime }}
            </span>
          </p>
        </div>
      </section>

      <!-- QUICKLINKS -->
      <section class="space-y-3">
        <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Schnellzugriff</h2>
        <div class="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-4">
          <button 
            v-for="link in quickLinks" 
            :key="link.name"
            @click="link.tab ? $emit('changeTab', link.tab) : null"
            class="p-4 bg-white rounded-2xl border border-slate-200 hover:shadow-md hover:border-slate-300 transition-all text-center flex flex-col items-center gap-3 group"
          >
            <div :class="['p-3 rounded-xl bg-slate-50 group-hover:scale-110 transition-transform', link.color]">
              <component :is="link.icon" class="w-5 h-5" />
            </div>
            <span class="text-xs font-semibold text-slate-700 tracking-tight">{{ link.name }}</span>
          </button>
        </div>
      </section>

      <!-- MAIN CONTENT GRID -->
      <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,350px),1fr))] lg:grid-cols-3 gap-8">        
        <!-- LINKE SEITE: Schnelle Notizen -->
        <div class="lg:col-span-2 flex flex-col min-w-[280px]">
          <div class="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col flex-1 min-h-[400px]">
            
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
              <h2 class="font-bold text-lg flex items-center gap-2 text-slate-800">
                <Edit3 class="w-5 h-5 text-amber-500" />
                Schnelle Notizen
              </h2>
              
              <div class="flex items-center gap-3">
                <span class="text-[11px] font-medium px-2 py-0.5 rounded transition-colors duration-300"
                      :class="isSaving ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'">
                  {{ isSaving ? 'Speichert...' : 'gespeichert' }}
                </span>

                <div class="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
                  <button @click="format('bold')" type="button" title="Fett" class="p-1.5 hover:bg-white rounded-lg text-slate-600 hover:text-slate-900 transition-colors">
                    <Bold class="w-4 h-4" />
                  </button>
                  <button @click="format('italic')" type="button" title="Kursiv" class="p-1.5 hover:bg-white rounded-lg text-slate-600 hover:text-slate-900 transition-colors">
                    <Italic class="w-4 h-4" />
                  </button>
                  <div class="w-px h-4 bg-slate-200 mx-1"></div>
                  <button @click="format('insertUnorderedList')" type="button" title="Aufzählung" class="p-1.5 hover:bg-white rounded-lg text-slate-600 hover:text-slate-900 transition-colors">
                    <List class="w-4 h-4" />
                  </button>
                  <button @click="format('insertOrderedList')" type="button" title="Nummerierte Liste" class="p-1.5 hover:bg-white rounded-lg text-slate-600 hover:text-slate-900 transition-colors">
                    <ListOrdered class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
            
            <div
              ref="editorRef"
              contenteditable="true"
              @input="updateContent"
              class="prose prose-sm max-w-none w-full flex-1 p-4 rounded-xl bg-slate-50 border border-slate-150 text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 overflow-y-auto leading-relaxed empty:before:content-[attr(placeholder)] empty:before:text-slate-400"
              placeholder="Schreibe hier deine Notizen. Sie werden automatisch gespeichert und sind nur für dich sichtbar."
            ></div>
          </div>
        </div>

        <!-- RECHTE SEITE: Die neue To-Do Liste -->
        <div class="lg:col-span-1 flex flex-col min-w-[280px]">
          <div class="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col flex-1 min-h-[400px]">
            
            <!-- Header -->
            <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <h2 class="font-bold text-lg flex items-center gap-2 text-slate-800">
                <ListChecks class="w-5 h-5 text-blue-600" />
                Meine Aufgaben
              </h2>
              <span class="text-xs font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                {{ todos?.filter(t => !t.completed)?.length ?? 0}} offen
              </span>
            </div>

            <!-- Input-Bereich -->
            <form @submit.prevent="handleAddTodo" class="flex gap-2 mb-4">
              <input 
                v-model="newTodoText"
                type="text" 
                placeholder="Neue Aufgabe hinzufügen..." 
                class="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-700"
              />
              <button 
                type="submit" 
                class="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors shrink-0 flex items-center justify-center"
              >
                <Plus class="w-5 h-5" />
              </button>
            </form>

            <!-- Scrollbare To-Do Liste -->
            <div class="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[320px]">
              <div 
                v-for="todo in todos" 
                :key="todo.id" 
                class="flex items-center justify-between p-3 rounded-xl border transition-all group"
                :class="todo.completed ? 'bg-slate-25 border-slate-100 opacity-60' : 'bg-white border-slate-200 hover:border-slate-300'"
              >
                <div class="flex items-center gap-3 min-w-0 flex-1 cursor-pointer" @click="handleToggleTodo(todo)">
                  <button type="button" class="shrink-0 text-slate-400 hover:text-blue-600 transition-colors">
                    <CheckSquare v-if="todo.completed" class="w-5 h-5 text-blue-600" />
                    <Square v-else class="w-5 h-5" />
                  </button>
                  <span 
                    class="text-sm truncate transition-all text-slate-700"
                    :class="{ 'line-through text-slate-400': todo.completed }"
                  >
                    {{ todo.text }}
                  </span>
                </div>

                <button 
                  @click="handleDeleteTodo(todo.id)"
                  class="p-1 text-slate-400 hover:text-rose-500 rounded-lg hover:bg-rose-50 md:opacity-0 group-hover:opacity-100 transition-all duration-200"
                  title="Aufgabe löschen"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>

              <!-- Empty State -->
              <div v-if="!todos || todos.length === 0" class="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
                <p class="text-sm font-medium">Alles erledigt!</p>
                <p class="text-xs mt-0.5 text-slate-400">Trage oben deine erste Aufgabe ein.</p>
              </div>
            </div>

          </div>
        </div>

      </div> 
    </div>
  </div>
</template>

<style scoped>
[contenteditable="true"] :deep(ul), [contenteditable="true"] ul {
  list-style-type: disc !important;
  padding-left: 1.5rem !important;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}
[contenteditable="true"] :deep(ol), [contenteditable="true"] ol {
  list-style-type: decimal !important;
  padding-left: 1.5rem !important;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}
[contenteditable="true"] :deep(li), [contenteditable="true"] li {
  display: list-item !important;
  margin-bottom: 0.25rem;
}

/* Schöne, sanfte Scrollbar für die To-Dos */
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>