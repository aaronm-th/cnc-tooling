// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Terminal from '../views/Terminal.vue'

const routes = [
  { 
    path: '/', 
    name: 'Home', 
    component: Home 
  },
  { 
    path: '/login', 
    name: 'Login', 
    component: Login 
  },
  {
      path: '/terminal',
      name: 'Terminal',
      component: Terminal
    }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})


router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token');
  
  const publicPages = ['Login', 'Register', 'Terminal'];
  const authRequired = !publicPages.includes(to.name);

  // 1. Wenn kein Token da ist und die Seite geschützt ist -> Login
  if (authRequired && !token) {
    next({ name: 'Login' });
  } 
  // 2. Wenn Token da ist und User zum Login/Register will -> Dashboard
  else if (token && (to.name === 'Login' || to.name === 'Register')) {
    next({ name: 'Home' }); // Achte darauf, dass der Name 'Home' ist, nicht 'Dashboard'
  }
  else {
    next(); // Überall sonst: Durchlassen
  }
});

export default router