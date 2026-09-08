import { create } from 'zustand'
import { apiGet } from '../api/client'

const useGeospatialStore = create((set, get) => ({
  // Data
  mapEvents: [],
  allEvents: [],
  stats: null,

  // Selection state
  selectedCity: null, // 'Mumbai' | 'Nagpur' | 'Nashik' | null
  selectedState: null, // 'Maharashtra' | null
  selectedEvent: null,

  // Filters
  filters: {
    category: null,
    severity: null,
    verification_status: null,
    city: null,
  },
  timeRange: '24h', // '1h', '6h', '24h', '7d', 'all'

  // Map state
  mapBounds: {
    min_lat: 6.0,
    max_lat: 38.0,
    min_lon: 68.0,
    max_lon: 98.0,
  },
  selectedLayer: 'events', // 'events', 'density', 'risk', 'category', 'verification'

  // Status
  loading: true,
  error: null,
  lastUpdated: null,

  // Polling
  pollInterval: null,

  // Actions
  setSelectedCity: (cityName) => {
    set((state) => ({
      selectedCity: cityName,
      selectedState: cityName ? 'Maharashtra' : state.selectedState,
      filters: { ...state.filters, city: cityName || null },
    }))
    get().refreshAll()
  },

  setSelectedState: (stateName) => set({ selectedState: stateName }),

  setFilters: (newFilters) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
      selectedCity: newFilters.city !== undefined ? newFilters.city : state.selectedCity,
    }))
    get().refreshAll()
  },

  clearFilters: () => {
    set({
      filters: { category: null, severity: null, verification_status: null, city: null },
      timeRange: '24h',
      selectedCity: null,
      selectedState: null,
      selectedEvent: null,
    })
    get().refreshAll()
  },

  setTimeRange: (timeRange) => {
    set({ timeRange })
    get().refreshAll()
  },

  setSelectedLayer: (layer) => set({ selectedLayer: layer }),

  setSelectedEvent: (event) => set({ selectedEvent: event }),

  clearSelectedEvent: () => set({ selectedEvent: null }),

  setMapBounds: (bounds) => set({ mapBounds: bounds }),

  // Compute time filter params
  _getTimeParams: () => {
    const { timeRange } = get()
    if (timeRange === 'all') return {}
    const now = new Date()
    const hours = { '1h': 1, '6h': 6, '24h': 24, '7d': 168 }
    const start = new Date(now.getTime() - (hours[timeRange] || 24) * 3600 * 1000)
    return { start_time: start.toISOString() }
  },

  fetchMapEvents: async () => {
    const { mapBounds, filters, _getTimeParams } = get()
    try {
      const timeParams = _getTimeParams()
      const params = new URLSearchParams({
        min_lat: mapBounds.min_lat,
        max_lat: mapBounds.max_lat,
        min_lon: mapBounds.min_lon,
        max_lon: mapBounds.max_lon,
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
      throw err
    }
  },

  fetchAllEvents: async () => {
    const { filters, _getTimeParams } = get()
    try {
      const timeParams = _getTimeParams()
      const params = new URLSearchParams({
        page: 1,
        page_size: 100,
        sort_by: 'last_seen',
        sort_order: 'desc',
        ...timeParams,
      })
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.verification_status) params.set('verification_status', filters.verification_status)
      if (filters.city) params.set('city', filters.city)

      const data = await apiGet(`/events?${params.toString()}`)
      set({ allEvents: data.items || [] })
    } catch (err) {
      console.warn('Failed to fetch all events:', err)
      throw err
    }
  },

  fetchStats: async () => {
    try {
      const stats = await apiGet('/events/stats')
      set({ stats })
    } catch (err) {
      console.warn('Failed to fetch stats:', err)
      throw err
    }
  },

  refreshAll: async () => {
    const { fetchMapEvents, fetchAllEvents, fetchStats } = get()
    try {
      await Promise.all([fetchMapEvents(), fetchAllEvents(), fetchStats()])
      set({ loading: false, lastUpdated: new Date().toISOString(), error: null })
    } catch (err) {
      console.warn('Geospatial refreshAll error:', err)
      set({ loading: false, error: err.message || 'Geospatial intelligence data temporarily unavailable' })
    }
  },

  startPolling: () => {
    const { pollInterval, refreshAll } = get()
    if (pollInterval) return
    refreshAll()
    const interval = setInterval(() => { refreshAll() }, 10000)
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

export default useGeospatialStore
