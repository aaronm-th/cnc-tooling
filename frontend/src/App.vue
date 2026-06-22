<script setup>
import { RouterView } from 'vue-router'


</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-100 transition-colors duration-300">
    <RouterView />
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  font-family: 'Inter', system-ui, Avenir, Helvetica, Arial, sans-serif;
}
</style>
