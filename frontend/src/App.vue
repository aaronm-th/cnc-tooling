<!-- src/App.vue -->
<template>
  <div class="flex flex-col h-screen w-screen bg-zinc-900 text-zinc-200 font-sans">
    <!-- Header / Topbar -->
    <header class="h-12 border-b border-zinc-800 flex items-center px-4 justify-between bg-zinc-950 select-none">
      <div class="flex items-center gap-2">
        <span class="font-bold text-lg text-blue-400">CNC-IDE</span>
        <span class="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">Mill-Turn v0.1</span>
      </div>

      <!-- Playback Controls -->
      <div class="flex items-center gap-2">
        <button class="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded font-medium text-sm transition flex items-center gap-1 shadow">
          ▶ Start
        </button>
        <button class="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-white rounded font-medium text-sm transition border border-zinc-700">
          ❚❚ Pause
        </button>
        <button class="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-red-400 rounded font-medium text-sm transition border border-zinc-700">
          ◼ Reset
        </button>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-xs text-zinc-500">Zeile: {{ activeLine }}</span>
        <button class="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm font-medium shadow">
          Werkzeuge
        </button>
      </div>
    </header>

    <!-- Main Workspace (Splitscreen) -->
    <main class="flex-1 flex overflow-hidden">
      <!-- Linker Panel: Code Editor -->
      <section class="w-1/2 h-full border-r border-zinc-800">
        <GCodeEditor 
          v-model="gcode" 
          @cursorChange="handleCursorChange" 
        />
      </section>

      <!-- Rechter Panel: 3D-Viewport -->
      <section class="w-1/2 h-full relative">
        <ThreeCanvas />
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import ThreeCanvas from './components/ThreeCanvas.vue';
import GCodeEditor from './components/GCodeEditor.vue';

// Demo G-Code für Mill-Turn
const gcode = ref(`( --- DEMO MILL-TURN PROGRAMM --- )
( WERKSTUECK: ZYLINDER D=40 L=80 )

T0101 (DREHMEISSEL SCHRUPPEN)
G97 S1200 M03
G00 X45.0 Z2.0 M08
G01 X-1.0 F0.15 (PLANEN)
G00 X38.0 Z2.0
G01 Z-50.0 F0.2 (LÄNGS SCHRUPPEN)
G01 X42.0 Z-52.0
G00 X100.0 Z100.0 M09

( ANGETRIEBENES WERKZEUG: QUERBOHRUNG )
T0202 (BOHRER D=8.0)
G28 C0
G97 S2500 M03
G00 X45.0 Z-25.0 C0.0
G01 X15.0 F0.08 (QUERBOHRUNG TIEFE 12.5MM)
G00 X45.0
M30
`);

const activeLine = ref(1);

const handleCursorChange = ({ lineNumber }) => {
  activeLine.value = lineNumber;
};
</script>