<!-- src/components/ThreeCanvas.vue -->
<template>
  <div class="w-full h-full relative">
    <!-- Status-Overlay für Koordinaten & Tool-Info -->
    <div class="absolute top-3 left-3 z-10 bg-zinc-900/80 p-2.5 rounded border border-zinc-700/50 text-xs font-mono text-zinc-300 backdrop-blur pointer-events-none select-none">
      <div class="font-bold text-blue-400 mb-1">Position & Werkzeug</div>
      <div>X: <span class="text-white">{{ currentPos.x.toFixed(3) }}</span> mm</div>
      <div>Y: <span class="text-white">{{ currentPos.y.toFixed(3) }}</span> mm</div>
      <div>Z: <span class="text-white">{{ currentPos.z.toFixed(3) }}</span> mm</div>
      <div class="mt-1 pt-1 border-t border-zinc-700/50 text-zinc-400">
        Spindel: <span class="text-green-400">T01 (Ø10mm)</span>
      </div>
    </div>

    <!-- Container für das Three.js Canvas -->
    <div ref="canvasContainer" class="w-full h-full cursor-grab active:cursor-grabbing"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const canvasContainer = ref<HTMLDivElement | null>(null);

// Live-Koordinaten für das Overlay
const currentPos = reactive({ x: 0, y: 0, z: 0 });

let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let controls: OrbitControls;
let animationFrameId: number;

onMounted(() => {
  if (!canvasContainer.value) return;

  // 1. Szene erstellen (Dunkler CAD-Hintergrund)
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x121214);

  // 2. Kamera aufsetzen (Perspektive)
  const width = canvasContainer.value.clientWidth;
  const height = canvasContainer.value.clientHeight;
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(100, 80, 120);

  // 3. Renderer initialisieren
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  canvasContainer.value.appendChild(renderer.domElement);

  // 4. OrbitControls (Kamera drehen/zoomen mit der Maus)
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;

  // 5. Beleuchtung (Ambient + Directional)
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(50, 100, 50);
  scene.add(dirLight);

  // 6. Grid & Koordinatenachsen (X=Rot, Y=Grün, Z=Blau)
  const gridHelper = new THREE.GridHelper(200, 40, 0x555555, 0x222222);
  gridHelper.position.y = -0.01; // Leichter Offset gegen Z-Fighting
  scene.add(gridHelper);

  const axesHelper = new THREE.AxesHelper(30);
  scene.add(axesHelper);

  // 7. Dummy-Rohteil (Vorübergehender Zylinder als Werkstück)
  const stockGeometry = new THREE.CylinderGeometry(20, 20, 80, 32);
  // Zylinder flachlegen für Drehmaschinen-Orientierung (Z-Achse)
  stockGeometry.rotateX(Math.PI / 2);
  const stockMaterial = new THREE.MeshStandardMaterial({
    color: 0x90a4ae,
    roughness: 0.3,
    metalness: 0.8,
  });
  const stockMesh = new THREE.Mesh(stockGeometry, stockMaterial);
  scene.add(stockMesh);

  // Resize-Listener
  window.addEventListener('resize', onWindowResize);

  // Animation Loop (60 FPS Render-Schleife)
  const animate = () => {
    animationFrameId = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  };
  animate();
});

const onWindowResize = () => {
  if (!canvasContainer.value || !renderer || !camera) return;
  const width = canvasContainer.value.clientWidth;
  const height = canvasContainer.value.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
};

onUnmounted(() => {
  window.removeEventListener('resize', onWindowResize);
  cancelAnimationFrame(animationFrameId);
  if (renderer) renderer.dispose();
});
</script>