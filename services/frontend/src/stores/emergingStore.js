import { create } from 'zustand'
import { apiGet } from '../api/client'

const useEmergingStore = create((set, get) => ({
  // Data
  events: [],
  mapEvents: [],
  stats: null,

  // Filters
  filters: {
    category: null,
    severity: null,
    verification_status: null,
    city: null,
  },
  timeRange: '24h',

  // Selection
  selectedEvent: null,

  // Status
  loading: true,
  error: null,
  lastUpdated: null,

  // Polling
  pollInterval: null,

  // Actions
  setFilters: (newFilters) => set((state) => ({
    filters: { ...state.filters, ...newFilters },
  })),

  clearFilters: () => set({
    filters: { category: null, severity: null, verification_status: null, city: null },
    timeRange: '24h',
  }),

  setTimeRange: (timeRange) => set({ timeRange }),

  setSelectedEvent: (event) => set({ selectedEvent: event }),

  clearSelectedEvent: () => set({ selectedEvent: null }),

  _getTimeParams: () => {
    const { timeRange } = get()
    if (timeRange === 'all') return {}
    const now = new Date()
    const hours = { '1h': 1, '6h': 6, '24h': 24, '7d': 168 }
    const start = new Date(now.getTime() - (hours[timeRange] || 24) * 3600 * 1000)
    return { start_time: start.toISOString() }
  },

  fetchEvents: async () => {
    const { filters, _getTimeParams } = get()
    try {
      const timeParams = _getTimeParams()
      const params = new URLSearchParams({
        page: 1, page_size: 100, sort_by: 'last_seen', sort_order: 'desc',
        ...timeParams,
      })
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.verification_status) params.set('verification_status', filters.verification_status)
      if (filters.city) params.set('city', filters.city)

      const data = await apiGet(`/events?${params.toString()}`)
      set({ events: data.items || [], loading: false, error: null })
    } catch (err) {
      set((state) => ({ error: err.message, loading: false }))
    }
  },

  fetchMapEvents: async () => {
    const { filters, _getTimeParams } = get()
    try {
      const timeParams = _getTimeParams()
      const params = new URLSearchParams({
        min_lat: 6, max_lat: 38, min_lon: 68, max_lon: 98,
        ...timeParams,
      })
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.verification_status) params.set('verification_status', filters.verification_status)
      if (filters.city) params.set('city', filters.city)

      const data = await apiGet(`/events/map?${params.toString()}`)
      set({ mapEvents: data.events || [] })
    } catch (err) {
      console.warn('Failed to fetch map events:', err)
    }
  },

  fetchStats: async () => {
    try {
      const stats = await apiGet('/events/stats')
      set({ stats })
    } catch (err) {
      console.warn('Failed to fetch stats:', err)
    }
  },

  refreshAll: async () => {
    const { fetchEvents, fetchMapEvents, fetchStats } = get()
    await Promise.all([fetchEvents(), fetchMapEvents(), fetchStats()])
    set({ lastUpdated: new Date().toISOString() })
  },

  startPolling: () => {
    const { pollInterval, refreshAll } = get()
    if (pollInterval) return
    refreshAll()
    const interval = setInterval(() => { refreshAll() }, 5000)
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

export default useEmergingStore
