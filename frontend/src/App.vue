<script setup>
import { ref } from 'vue';
import GCodeEditor from './components/GCodeEditor.vue';
import ThreeCanvas from './components/ThreeCanvas.vue';

const gcodeText = ref(`T0101
G00 X45.0 Z2.0
G01 X-1.0 F0.15
G00 X38.0 Z2.0
G01 Z-50.0 F0.2
G01 X42.0 Z-52.0
G00 X100.0 Z100.0`);

const activeLineNumber = ref(-1);
</script>

<template>
  <div class="flex h-screen w-screen bg-zinc-950 overflow-hidden">
    <div class="w-1/2 h-full border-r border-zinc-800">
      <GCodeEditor 
        v-model="gcodeText" 
        :active-line="activeLineNumber" 
      />
    </div>
    <div class="w-1/2 h-full">
      <ThreeCanvas 
        :gcode="gcodeText" 
        @line-changed="(line) => activeLineNumber = line" 
      />
    </div>
  </div>
</template>