import { create } from 'zustand'
import { apiGet } from '../api/client'

const useCommandCenterStore = create((set, get) => ({
  // Data
  events: [],
  mapEvents: [],
  stats: null,
  health: null,

  // UI state
  loading: true,
  error: null,
  lastUpdated: null,
  selectedEvent: null,
  filters: {
    category: null,
    severity: null,
    verification: null,
    city: null,
  },
  mapBounds: {
    min_lat: 6.0,
    max_lat: 38.0,
    min_lon: 68.0,
    max_lon: 98.0,
  },

  // Polling
  pollInterval: null,

  // Actions
  setFilters: (filters) => {
    set((state) => ({
      filters: { ...state.filters, ...filters },
    }))
    // Immediately fetch updated events
    get().refreshAll()
  },

  setSelectedEvent: (event) => set({ selectedEvent: event }),

  clearSelectedEvent: () => set({ selectedEvent: null }),

  setMapBounds: (bounds) => set({ mapBounds: bounds }),

  fetchStats: async () => {
    try {
      const stats = await apiGet('/events/stats')
      set({ stats })
    } catch (err) {
      console.warn('Failed to fetch stats:', err)
    }
  },

  fetchMapEvents: async () => {
    const { mapBounds, filters } = get()
    try {
      const params = new URLSearchParams({
        min_lat: mapBounds.min_lat,
        max_lat: mapBounds.max_lat,
        min_lon: mapBounds.min_lon,
        max_lon: mapBounds.max_lon,
      })
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.verification) params.set('verification_status', filters.verification)
      if (filters.city) params.set('city', filters.city)

      const data = await apiGet(`/events/map?${params.toString()}`)
      set({ mapEvents: data.events || [] })
    } catch (err) {
      console.warn('Failed to fetch map events:', err)
    }
  },

  fetchEvents: async () => {
    const { filters } = get()
    try {
      const params = new URLSearchParams({
        page: 1,
        page_size: 20,
        sort_by: 'last_seen',
        sort_order: 'desc',
      })
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.verification) params.set('verification_status', filters.verification)
      if (filters.city) params.set('city', filters.city)

      const data = await apiGet(`/events?${params.toString()}`)
      set({
        events: data.items || [],
        loading: false,
        lastUpdated: new Date().toISOString(),
      })
    } catch (err) {
      set({ error: err.message, loading: false })
    }
  },

  fetchHealth: async () => {
    try {
      const health = await apiGet('/health')
      set({ health })
    } catch (err) {
      set({ health: { status: 'unreachable' } })
    }
  },

  refreshAll: async () => {
    const { fetchStats, fetchMapEvents, fetchEvents, fetchHealth } = get()
    await Promise.all([
      fetchStats(),
      fetchMapEvents(),
      fetchEvents(),
      fetchHealth(),
    ])
  },

  startPolling: () => {
    const { pollInterval, refreshAll } = get()
    if (pollInterval) return

    // Initial fetch
    refreshAll()

    // Poll every 5 seconds
    const interval = setInterval(() => {
      refreshAll()
    }, 5000)

    set({ pollInterval: interval })
  },

  stopPolling: () => {
    const { pollInterval } = get()
    if (pollInterval) {
      clearInterval(pollInterval)
      set({ pollInterval: null })
    }
  },
}))

export default useCommandCenterStore
