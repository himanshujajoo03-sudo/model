import { create } from 'zustand'
import { apiGet } from '../api/client'

const useReportReviewStore = create((set, get) => ({
  // Data
  reports: [],
  stats: null,
  total: 0,
  totalPages: 0,

  // Filters
  filters: {
    source_type: null,
    source_name: null,
    category: null,
    severity: null,
    verification_status: null,
    city: null,
    has_canonical: null,
  },
  search: '',
  page: 1,
  pageSize: 20,
  sortBy: 'event_timestamp',
  sortOrder: 'desc',

  // Selection
  selectedReport: null,
  selectedReportDetail: null,

  // Status
  loading: true,
  detailLoading: false,
  error: null,
  lastUpdated: null,

  // Polling
  pollInterval: null,

  // Actions
  setFilters: (newFilters) => set((state) => ({
    filters: { ...state.filters, ...newFilters },
    page: 1,
  })),

  clearFilters: () => set({
    filters: {
      source_type: null, source_name: null, category: null,
      severity: null, verification_status: null, city: null,
      has_canonical: null,
    },
    search: '',
    page: 1,
  }),

  setSearch: (search) => set({ search, page: 1 }),
  setPage: (page) => set({ page }),
  setSortBy: (sortBy) => set({ sortBy, page: 1 }),
  setSortOrder: (sortOrder) => set({ sortOrder, page: 1 }),

  selectReport: (report) => set({ selectedReport: report, selectedReportDetail: null }),
  clearSelection: () => set({ selectedReport: null, selectedReportDetail: null }),

  fetchReports: async () => {
    const { filters, search, page, pageSize, sortBy, sortOrder } = get()
    try {
      const params = new URLSearchParams({
        page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder,
      })
      if (filters.source_type) params.set('source_type', filters.source_type)
      if (filters.source_name) params.set('source_name', filters.source_name)
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.verification_status) params.set('verification_status', filters.verification_status)
      if (filters.city) params.set('city', filters.city)
      if (filters.has_canonical !== null) params.set('has_canonical', filters.has_canonical)
      if (search) params.set('search', search)

      const data = await apiGet(`/reports?${params.toString()}`)
      set({
        reports: data.items || [],
        total: data.total || 0,
        totalPages: data.total_pages || 0,
        loading: false,
        error: null,
      })
    } catch (err) {
      set((state) => ({ error: err.message, loading: false }))
    }
  },

  fetchStats: async () => {
    try {
      const stats = await apiGet('/reports/stats')
      set({ stats })
    } catch (err) {
      console.warn('Failed to fetch report stats:', err)
    }
  },

  fetchReportDetail: async (reportId) => {
    set({ detailLoading: true })
    try {
      const detail = await apiGet(`/reports/${reportId}`)
      set({ selectedReportDetail: detail, detailLoading: false })
    } catch (err) {
      set({ detailLoading: false, error: err.message })
    }
  },

  refreshAll: async () => {
    const { fetchReports, fetchStats } = get()
    await Promise.all([fetchReports(), fetchStats()])
    set({ lastUpdated: new Date().toISOString() })
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

export default useReportReviewStore
