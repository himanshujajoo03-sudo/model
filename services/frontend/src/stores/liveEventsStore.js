import { create } from 'zustand'
import { apiGet } from '../api/client'

const useLiveEventsStore = create((set, get) => ({
  // Data
  events: [],
  total: 0,
  totalPages: 0,

  // Pagination
  page: 1,
  pageSize: 20,

  // Filters
  filters: {
    category: null,
    severity: null,
    verification_status: null,
    city: null,
    source_type: null,
    min_credibility: null,
  },

  // Sort
  sortBy: 'event_timestamp',
  sortOrder: 'desc',

  // Search (client-side against loaded data)
  search: '',

  // Status
  loading: true,
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

  setFilters: (newFilters) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
      page: 1,
    }))
    get().fetchEvents()
  },

  clearFilters: () => {
    set({
      filters: {
        category: null, severity: null, verification_status: null,
        city: null, source_type: null, min_credibility: null,
      },
      search: '',
      page: 1,
    })
    get().fetchEvents()
  },

  fetchEvents: async () => {
    const { page, pageSize, filters, sortBy, sortOrder } = get()
    try {
      const params = new URLSearchParams({
        page: page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.verification_status) params.set('verification_status', filters.verification_status)
      if (filters.city) params.set('city', filters.city)
      if (filters.source_type) params.set('source_type', filters.source_type)
      if (filters.min_credibility) params.set('min_credibility', filters.min_credibility)

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
        // Preserve previous data on transient polling errors
      }))
    }
  },

  startPolling: () => {
    const { pollInterval, fetchEvents } = get()
    if (pollInterval) return

    fetchEvents()
    const interval = setInterval(() => {
      fetchEvents()
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

export default useLiveEventsStore
