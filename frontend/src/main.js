import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './index.css'
import App from './App.vue'
import router from './router'
import axios from 'axios';


const app = createApp(App)
const pinia = createPinia()

app.use(router)
app.use(pinia)

app.mount('#app')


axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // Token ist abgelaufen oder manipuliert
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      router.push({ name: 'Login' });
    }
    return Promise.reject(error);
  }
);