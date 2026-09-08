/**
 * API client wrapper.
 * API client wrapper for SIH26069 Platform.
 * Uses VITE_API_URL for the backend base URL.
 * Automatically manages JWT bearer authentication and token lifecycle.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
const TOKEN_KEY = 'weather_access_token'

let inMemoryToken = null

/**
 * Get the current JWT token from memory or localStorage.
 */
export function getToken() {
  if (inMemoryToken) return inMemoryToken
  if (typeof window !== 'undefined' && window.localStorage) {
    inMemoryToken = window.localStorage.getItem(TOKEN_KEY)
  }
  return inMemoryToken
}

/**
 * Set and persist the JWT token.
 */
export function setToken(token) {
  inMemoryToken = token
  if (typeof window !== 'undefined' && window.localStorage) {
    if (token) {
      window.localStorage.setItem(TOKEN_KEY, token)
    } else {
      window.localStorage.removeItem(TOKEN_KEY)
    }
  }
}

/**
 * Clear current authentication.
 */
export function logout() {
  setToken(null)
}

/**
 * Authenticate with the API and store the JWT.
 */
export async function login(username = 'admin', password = 'admin') {
  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!response.ok) {
      const err = await extractErrorMessage(response)
      throw new Error(err)
    }
    const data = await response.json()
    if (data.access_token) {
      setToken(data.access_token)
      return data.access_token
    }
    throw new Error('No access_token returned by backend')
  } catch (err) {
    console.warn('[Auth] Auto-login failed:', err.message)
    throw err
  }
}

/**
 * Ensure a valid token exists; if missing, automatically authenticate as admin.
 */
export async function ensureToken() {
  const existing = getToken()
  if (existing) return existing
  try {
    return await login('admin', 'admin')
  } catch {
    return null
  }
}

/**
 * Extract human-readable error from response.
 */
async function extractErrorMessage(response) {
  try {
    const body = await response.json()
    if (body?.detail?.error?.message) return body.detail.error.message
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg
    if (body?.message) return body.message
    return `API error: ${response.status} ${response.statusText}`
  } catch {
    return `API error: ${response.status} ${response.statusText}`
  }
}

/**
 * Build request headers including optional Bearer token.
 */
function buildHeaders(customHeaders = {}, token = null) {
  const headers = { ...customHeaders }
  const auth = token || getToken()
  if (auth && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${auth}`
  }
  return headers
}

/**
 * GET request wrapper with automatic authentication handling.
 */
export async function apiGet(path, options = {}) {
  const token = await ensureToken()
  const headers = buildHeaders(options.headers || {}, token)

  let response = await fetch(`${API_BASE}${path}`, {
    ...options,
    method: 'GET',
    headers,
  })

  // Handle 401 token expiry: refresh token and retry once
  if (response.status === 401 && !options._retried) {
    setToken(null)
    const freshToken = await ensureToken()
    if (freshToken) {
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        _retried: true,
        method: 'GET',
        headers: buildHeaders(options.headers || {}, freshToken),
      })
    }
  }

  if (!response.ok) {
    const msg = await extractErrorMessage(response)
    throw new Error(msg)
  }

  return response.json()
}

/**
 * POST request wrapper with automatic authentication handling.
 */
export async function apiPost(path, data, options = {}) {
  const token = await ensureToken()
  const headers = buildHeaders(
    {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    token
  )

  let response = await fetch(`${API_BASE}${path}`, {
    ...options,
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  })

  // Handle 401 token expiry: refresh token and retry once
  if (response.status === 401 && !options._retried) {
    setToken(null)
    const freshToken = await ensureToken()
    if (freshToken) {
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        _retried: true,
        method: 'POST',
        headers: buildHeaders(
          {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
          },
          freshToken
        ),
        body: JSON.stringify(data),
      })
    }
  }

  if (!response.ok) {
    const msg = await extractErrorMessage(response)
    throw new Error(msg)
  }

  return response.json()
}

/**
 * Check current auth state.
 */
export function getAuthStatus() {
  return {
    isAuthenticated: !!getToken(),
    token: getToken(),
  }
}
