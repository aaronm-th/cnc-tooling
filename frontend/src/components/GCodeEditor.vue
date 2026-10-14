<!-- src/components/GCodeEditor.vue -->
<template>
  <div class="w-full h-full flex flex-col bg-[#1e1e1e]">
    <!-- Tab / Dateiname Bar -->
    <div class="h-8 bg-[#181818] px-3 flex items-center justify-between text-xs text-zinc-400 font-mono border-b border-zinc-800 select-none">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-blue-500"></span>
        <span>main_program.nc</span>
      </div>
      <div class="text-[10px] text-zinc-500">G-Code (ISO 6983)</div>
    </div>

    <!-- Editor Container -->
    <div ref="editorContainer" class="flex-1 w-full h-full"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as monaco from 'monaco-editor';

self.MonacoEnvironment = {
  getWorker() {
    return new Worker(
      URL.createObjectURL(
        new Blob(
          [`self.onmessage = function () { postMessage({ id: 0, result: true }); };`],
          { type: 'text/javascript' }
        )
      )
    );
  }
};

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  activeLine: {
    type: Number,
    default: -1
  }
});

const emit = defineEmits(['update:modelValue', 'cursorChange']);

const editorContainer = ref(null);
let editorInstance = null;
let lineDecorations = [];

// Einfache Syntax-Highlighting Regeln für G-Code registrieren
const registerGCodeLanguage = () => {
  if (monaco.languages.getLanguages().some(lang => lang.id === 'gcode')) {
    return;
  }

  monaco.languages.register({ id: 'gcode' });

  monaco.languages.setMonarchTokensProvider('gcode', {
    defaultToken: '',
    ignoreCase: true,
    tokenizer: {
      root: [
        [/\(.*\)/, 'comment'],
        [/;.*$/, 'comment'],
        [/G\d+/, 'keyword'],
        [/M\d+/, 'keyword.control'],
        [/[XYZCURFST]-?\d+(\.\d+)?/, 'type'],
        [/\d+(\.\d+)?/, 'number'],
      ]
    }
  });

  monaco.editor.defineTheme('gcodeTheme', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
      { token: 'keyword', foreground: '569CD6', fontStyle: 'bold' },
      { token: 'keyword.control', foreground: 'C586C0', fontStyle: 'bold' },
      { token: 'type', foreground: '4EC9B0' },
      { token: 'number', foreground: 'B5CEA8' },
    ],
    colors: {
      'editor.background': '#1e1e1e',
      'editor.lineHighlightBackground': '#2A2D2E',
      'editorLineNumber.foreground': '#5A5A5A',
      'editorLineNumber.activeForeground': '#007ACC',
    }
  });
};

onMounted(() => {
  if (!editorContainer.value) return;

  registerGCodeLanguage();

  editorInstance = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: 'gcode',
    theme: 'gcodeTheme',
    automaticLayout: true,
    fontSize: 13,
    fontFamily: 'JetBrains Mono, Fira Code, Consolas, monospace',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbers: 'on',
    renderLineHighlight: 'all',
    tabSize: 2,
  });

  editorInstance.onDidChangeModelContent(() => {
    const value = editorInstance.getValue();
    emit('update:modelValue', value);
  });

  editorInstance.onDidChangeCursorPosition((e) => {
    emit('cursorChange', {
      lineNumber: e.position.lineNumber,
      lineContent: editorInstance.getModel().getLineContent(e.position.lineNumber)
    });
  });
});

// Gelbes Highlighting auf der aktiven Zeile setzen
watch(() => props.activeLine, (newLine) => {
  if (!editorInstance) return;

  if (newLine < 1) {
    lineDecorations = editorInstance.deltaDecorations(lineDecorations, []);
    return;
  }

  editorInstance.revealLineInCenter(newLine);

  lineDecorations = editorInstance.deltaDecorations(lineDecorations, [
    {
      range: new monaco.Range(newLine, 1, newLine, 1),
      options: {
        isWholeLine: true,
        className: 'bg-yellow-500/20 border-l-4 border-yellow-400'
      }
    }
  ]);
});

watch(() => props.modelValue, (newValue) => {
  if (editorInstance && newValue !== editorInstance.getValue()) {
    editorInstance.setValue(newValue);
  }
});

onUnmounted(() => {
  if (editorInstance) {
    editorInstance.dispose();
  }
});
</script>