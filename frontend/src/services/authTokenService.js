/**
 * Single place that knows about localStorage keys related to auth.
 * Nothing else in the app should call localStorage.getItem/setItem/removeItem
 * for tokens directly -- go through this service instead.
 */

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

// Legacy / UI-state keys that a full logout should also clear.
// (Kept as a list so it's obvious what "logging out" actually resets.)
const KEYS_TO_CLEAR_ON_LOGOUT = [
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  'token',
  'activeTab',
  'isAdminView',
  'admin_active_tab',
  'user',
]

export const authTokenService = {
  getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY)
  },

  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  },

  hasToken() {
    return !!this.getAccessToken()
  },

  setTokens({ access, refresh } = {}) {
    if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },

  clearAll() {
    KEYS_TO_CLEAR_ON_LOGOUT.forEach((key) => localStorage.removeItem(key))
  },
}