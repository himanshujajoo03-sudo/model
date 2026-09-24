import { create } from 'zustand'
import { apiGet } from '../api/client'

const useAnalyticsStore = create((set, get) => ({
  // Shared filters
  filters: {
    category: null,
    severity: null,
    verification_status: null,
    city: null,
  },
  timeRange: '24h',

  // Data
  stats: null,
  events: [],
  mapEvents: [],

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

  _getTimeParams: () => {
    const { timeRange } = get()
    if (timeRange === 'all') return {}
    const now = new Date()
    const hours = { '1h': 1, '6h': 6, '24h': 24, '7d': 168, '30d': 720 }
    const start = new Date(now.getTime() - (hours[timeRange] || 24) * 3600 * 1000)
    return { start_time: start.toISOString() }
  },

  fetchStats: async () => {
    try {
      const { _getTimeParams } = get()
      const timeParams = _getTimeParams()
      const params = new URLSearchParams(timeParams)
      const stats = await apiGet(`/events/stats?${params.toString()}`)
      set({ stats })
    } catch (err) {
      console.warn('Failed to fetch analytics stats:', err)
    }
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
      set({ events: data.items || [] })
    } catch (err) {
      console.warn('Failed to fetch analytics events:', err)
    }
  },

  fetchMapEvents: async () => {
    try {
      const data = await apiGet('/events/map?min_lat=6&max_lat=38&min_lon=68&max_lon=98')
      set({ mapEvents: data.events || [] })
    } catch (err) {
      console.warn('Failed to fetch analytics map events:', err)
    }
  },

  refreshAll: async () => {
    const { fetchStats, fetchEvents, fetchMapEvents } = get()
    await Promise.all([fetchStats(), fetchEvents(), fetchMapEvents()])
    set({ loading: false, lastUpdated: new Date().toISOString(), error: null })
  },

  startPolling: () => {
    const { pollInterval, refreshAll } = get()
    if (pollInterval) return
    refreshAll()
    const interval = setInterval(() => { refreshAll() }, 15000) // 15s for analytics
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

export default useAnalyticsStore
