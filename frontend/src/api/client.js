import axios from 'axios'
import router from '@/router'
import { authTokenService } from '@/services/authTokenService'

/**
 * Single shared axios instance for the whole app.
 *
 * Replaces the old pattern of every store doing:
 *   const token = localStorage.getItem('access_token')
 *   axios.get(url, { headers: { Authorization: `Bearer ${token}` } })
 *
 * Now every store just calls the relevant `*Api` module, and auth
 * happens here, once, for every request.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

// Attach the bearer token to every outgoing request, if we have one.
// (Terminal endpoints are AllowAny on the backend -- if there's no
// token, e.g. on /api/terminal/..., this simply attaches nothing.)
api.interceptors.request.use((config) => {
  const token = authTokenService.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Centralized 401 handling: if a request ever comes back unauthorized,
// the token is stale/invalid -- clear it and send the user back to login.
// Individual stores no longer need to handle this themselves.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      authTokenService.clearAll()
      if (router.currentRoute.value.name !== 'Login') {
        router.push({ name: 'Login' })
      }
    }
    return Promise.reject(error)
  }
)

export default api