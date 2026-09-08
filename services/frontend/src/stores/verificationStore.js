import { create } from 'zustand'
import { apiGet, apiPost } from '../api/client'

const useVerificationStore = create((set, get) => ({
  // Data
  events: [],
  total: 0,
  totalPages: 0,
  stats: null,

  // Pagination
  page: 1,
  pageSize: 20,

  // Filters
  filters: {
    verification_status: null,
    category: null,
    severity: null,
    source_type: null,
  },

  // Sort
  sortBy: 'last_seen',
  sortOrder: 'desc',

  // Search
  search: '',

  // Selected event for review panel
  selectedEvent: null,
  selectedEventDetail: null,

  // Status
  loading: true,
  detailLoading: false,
  actionLoading: false,
  error: null,
  lastUpdated: null,

  // Polling
  pollInterval: null,

  // Actions
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
  setSortBy: (sortBy) => set({ sortBy, page: 1 }),
  setSortOrder: (sortOrder) => set({ sortOrder, page: 1 }),
  setSearch: (search) => set({ search }),

  setFilters: (newFilters) => set((state) => ({
    filters: { ...state.filters, ...newFilters },
    page: 1,
  })),

  clearFilters: () => set({
    filters: {
      verification_status: null,
      category: null,
      severity: null,
      source_type: null,
    },
    search: '',
    page: 1,
  }),

  selectEvent: (event) => set({ selectedEvent: event, selectedEventDetail: null }),

  clearSelection: () => set({ selectedEvent: null, selectedEventDetail: null }),

  fetchEvents: async () => {
    const { page, pageSize, filters, sortBy, sortOrder } = get()
    try {
      const params = new URLSearchParams({
        page: page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      if (filters.verification_status) params.set('verification_status', filters.verification_status)
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.source_type) params.set('source_type', filters.source_type)

      const data = await apiGet(`/events?${params.toString()}`)
      set({
        events: data.items || [],
        total: data.total || 0,
        totalPages: data.total_pages || 0,
        loading: false,
        error: null,
        lastUpdated: new Date().toISOString(),
      })
    } catch (err) {
      set((state) => ({
        error: err.message,
        loading: false,
      }))
    }
  },

  fetchStats: async () => {
    try {
      const stats = await apiGet('/events/stats')
      set({ stats })
    } catch (err) {
      console.warn('Failed to fetch verification stats:', err)
    }
  },

  fetchEventDetail: async (eventId) => {
    set({ detailLoading: true })
    try {
      const detail = await apiGet(`/events/${eventId}`)
      set({ selectedEventDetail: detail, detailLoading: false })
    } catch (err) {
      set({ detailLoading: false, error: err.message })
    }
  },

  performVerification: async (eventId, action, performedBy = 'admin', notes = '') => {
    set({ actionLoading: true })
    try {
      const result = await apiPost('/verification', {
        event_id: eventId,
        action,
        performed_by: performedBy,
        notes,
      })
      set({ actionLoading: false })
      // Refresh data
      const { fetchEvents, fetchStats, fetchEventDetail } = get()
      await Promise.all([fetchEvents(), fetchStats()])
      if (get().selectedEvent?.event_id === eventId) {
        await fetchEventDetail(eventId)
      }
      return result
    } catch (err) {
      set({ actionLoading: false, error: err.message })
      throw err
    }
  },

  refreshAll: async () => {
    const { fetchEvents, fetchStats } = get()
    await Promise.all([fetchEvents(), fetchStats()])
  },

  startPolling: () => {
    const { pollInterval, refreshAll } = get()
    if (pollInterval) return
    refreshAll()
    const interval = setInterval(() => {
      refreshAll()
    }, 10000) // 10-second polling for verification center
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

export default useVerificationStore
