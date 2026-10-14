<!-- src/components/ThreeCanvas.vue -->
<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as THREE from 'three';
import initWasm, { VoxelStock } from '../wasm/calculator_engine.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { parseGCode } from '../utils/gcodeParser';
import { GCodeExecutor } from '../utils/gcodeExecutor';

const props = defineProps({
  gcode: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['line-changed']);

const canvasContainer = ref(null);

// Rohteil Parameter
const stockType = ref('cylinder');
const stockDiameter = ref(40.0);
const stockWidthX = ref(40.0);
const stockHeightY = ref(40.0);
const stockLengthZ = ref(80.0);
const voxelResolution = ref(60);

// Simulator State
const isPlaying = ref(false);
let simulationInterval = null;

let stockEngine = null;
let stockMesh = null;
let scene = null;
let toolMesh = null;

const executor = new GCodeExecutor();

const rebuildStock = () => {
  if (!scene) return;

  if (stockType.value === 'cylinder') {
    stockEngine = VoxelStock.new_cylinder(
      parseFloat(stockDiameter.value),
      parseFloat(stockLengthZ.value),
      parseInt(voxelResolution.value)
    );
  } else {
    stockEngine = VoxelStock.new_cuboid(
      parseFloat(stockWidthX.value),
      parseFloat(stockHeightY.value),
      parseFloat(stockLengthZ.value),
      parseInt(voxelResolution.value)
    );
  }

  // STANDARD-FALLBACK: Nutze das Demo-Programm, falls props.gcode noch leer ist
  const codeToRun = (props.gcode && props.gcode.trim().length > 0) 
    ? props.gcode 
    : `( --- DEMO MILL-TURN PROGRAMM --- )
T0101 (DREHMEISSEL SCHRUPPEN)
G97 S1200 M03
G00 X45.0 Z2.0
G01 X-1.0 F0.15
G00 X38.0 Z2.0
G01 Z-50.0 F0.2
G01 X42.0 Z-52.0
G00 X100.0 Z100.0`;

  const parsedCommands = parseGCode(codeToRun);
  console.log("Geladene G-Code Befehle:", parsedCommands);

  // Startposition direkt am Rohteil ansetzen
  executor.loadProgram(parsedCommands, { x: 45, y: 0, z: 2.0 });
  
  updateMesh();
  updateToolPosition(executor.getPosition());
  emit('line-changed', -1);
};

const updateMesh = () => {
  if (!stockEngine || !scene) return;

  const rawVertices = stockEngine.get_mesh_vertices();
  const positionBuffer = new Float32Array(rawVertices);

  if (stockMesh) {
    scene.remove(stockMesh);
    stockMesh.geometry.dispose();
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positionBuffer, 3));
  geometry.computeVertexNormals();

  const material = new THREE.MeshStandardMaterial({
    color: 0x90a4ae,
    roughness: 0.35,
    metalness: 0.8,
    side: THREE.DoubleSide
  });

  stockMesh = new THREE.Mesh(geometry, material);
  scene.add(stockMesh);
};

const updateToolPosition = (pos) => {
  if (!toolMesh) return;
  // Positionierung im 3D-Raum (X als Radius)
  toolMesh.position.set(pos.x / 2.0, pos.y, pos.z);
};

onMounted(async () => {
  await initWasm();

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x121214);

  const camera = new THREE.PerspectiveCamera(45, canvasContainer.value.clientWidth / canvasContainer.value.clientHeight, 0.1, 1000);
  camera.position.set(80, 60, 100);
  camera.lookAt(0, 0, 40);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(canvasContainer.value.clientWidth, canvasContainer.value.clientHeight);
  canvasContainer.value.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0, 40);
  controls.enableDamping = true;

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
  dirLight.position.set(50, 100, 50);
  scene.add(dirLight);

  // 3D-Werkzeug Kugel
  const toolGeo = new THREE.SphereGeometry(2.0, 16, 16);
  const toolMat = new THREE.MeshStandardMaterial({ color: 0xff3333, metalness: 0.5, roughness: 0.2 });
  toolMesh = new THREE.Mesh(toolGeo, toolMat);
  scene.add(toolMesh);

  const animate = () => {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  };
  animate();

  rebuildStock();
});

watch(() => props.gcode, () => {
  rebuildStock();
});

const stepSimulation = () => {
  if (!stockEngine || executor.isFinished()) {
    pauseSimulation();
    return;
  }

  const newPos = executor.step(stockEngine);
  if (newPos) {
    updateToolPosition(newPos);
    updateMesh();
    emit('line-changed', executor.getCurrentLineNumber());
  }
};

const playSimulation = () => {
  if (isPlaying.value) return;
  isPlaying.value = true;
  simulationInterval = setInterval(() => {
    if (executor.isFinished()) {
      pauseSimulation();
    } else {
      stepSimulation();
    }
  }, 250);
};

const pauseSimulation = () => {
  isPlaying.value = false;
  if (simulationInterval) clearInterval(simulationInterval);
};

const resetSimulation = () => {
  pauseSimulation();
  rebuildStock();
};

onUnmounted(() => {
  pauseSimulation();
});
</script>

<template>
  <div class="w-full h-full relative">
    <!-- Kontroll-Panel oben links -->
    <div class="absolute top-4 left-4 z-20 bg-zinc-900/90 p-4 rounded-lg shadow-lg border border-zinc-700 text-white w-64 space-y-3 backdrop-blur-sm">
      <h3 class="font-semibold text-sm text-zinc-300 border-b border-zinc-700 pb-1">Rohteil Einstellungen</h3>
      
      <div class="flex bg-zinc-800 p-1 rounded border border-zinc-700">
        <button @click="stockType = 'cylinder'; rebuildStock();" :class="stockType === 'cylinder' ? 'bg-blue-600 text-white' : 'text-zinc-400'" class="flex-1 py-1 text-xs font-medium rounded transition">Zylinder</button>
        <button @click="stockType = 'cuboid'; rebuildStock();" :class="stockType === 'cuboid' ? 'bg-blue-600 text-white' : 'text-zinc-400'" class="flex-1 py-1 text-xs font-medium rounded transition">Quader</button>
      </div>

      <div v-if="stockType === 'cylinder'">
        <label class="text-xs text-zinc-400 block mb-1">Durchmesser Ø (mm): {{ stockDiameter }}</label>
        <input v-model.number="stockDiameter" @change="rebuildStock" type="range" min="10" max="100" step="1" class="w-full accent-blue-500 cursor-pointer" />
      </div>

      <template v-else>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Breite X (mm): {{ stockWidthX }}</label>
          <input v-model.number="stockWidthX" @change="rebuildStock" type="range" min="10" max="100" step="1" class="w-full accent-blue-500 cursor-pointer" />
        </div>
        <div>
          <label class="text-xs text-zinc-400 block mb-1">Höhe Y (mm): {{ stockHeightY }}</label>
          <input v-model.number="stockHeightY" @change="rebuildStock" type="range" min="10" max="100" step="1" class="w-full accent-blue-500 cursor-pointer" />
        </div>
      </template>

      <div>
        <label class="text-xs text-zinc-400 block mb-1">Länge Z (mm): {{ stockLengthZ }}</label>
        <input v-model.number="stockLengthZ" @change="rebuildStock" type="range" min="20" max="200" step="2" class="w-full accent-blue-500 cursor-pointer" />
      </div>

      <div>
        <label class="text-xs text-zinc-400 block mb-1">Voxel-Auflösung: {{ voxelResolution }}</label>
        <select v-model.number="voxelResolution" @change="rebuildStock" class="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-200">
          <option :value="30">30 (Grob)</option>
          <option :value="60">60 (Mittel)</option>
          <option :value="90">90 (Fein)</option>
        </select>
      </div>
    </div>

    <!-- Simulation Controls oben rechts -->
    <div class="absolute top-4 right-4 z-20 flex gap-2 bg-zinc-900/90 p-2 rounded-lg border border-zinc-700 backdrop-blur-sm">
      <button v-if="!isPlaying" @click="playSimulation" class="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white font-bold text-xs rounded transition flex items-center gap-1">
        ▶ Play
      </button>
      <button v-else @click="pauseSimulation" class="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 text-white font-bold text-xs rounded transition flex items-center gap-1">
        ⏸ Pause
      </button>
      <button @click="stepSimulation" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded transition">
        ⏭ Step
      </button>
      <button @click="resetSimulation" class="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 text-white font-bold text-xs rounded transition">
        ↺ Reset
      </button>
    </div>

    <div ref="canvasContainer" class="w-full h-full"></div>
  </div>
</template>