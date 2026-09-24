import { create } from 'zustand'
import { apiGet } from '../api/client'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export function computeEventLatency(event) {
  if (!event || !event.db_written_at) return null
  const eventTimeStr = event.event_timestamp || event.timestamp || event.event_time || event.created_at
  if (!eventTimeStr) return null
  const dbTime = new Date(event.db_written_at).getTime()
  const eventTime = new Date(eventTimeStr).getTime()
  if (isNaN(dbTime) || isNaN(eventTime)) return null
  const diff = dbTime - eventTime
  return diff >= 0 ? diff : null
}

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
  isLiveStreaming: false,
  lastSseReceivedAt: null,
  eventSource: null,

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
        scope: 'live',
      })
      if (filters.category) params.set('category', filters.category)
      if (filters.severity) params.set('severity', filters.severity)
      if (filters.verification_status) params.set('verification_status', filters.verification_status)
      if (filters.city) params.set('city', filters.city)
      if (filters.source_type) params.set('source_type', filters.source_type)
      if (filters.min_credibility) params.set('min_credibility', filters.min_credibility)

      const data = await apiGet(`/events?${params.toString()}`)
      const rawItems = data.items || []
      const items = rawItems.map((item) => ({
        ...item,
        latency_ms: computeEventLatency(item),
      }))
      set({
        events: items,
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

  connectSse: () => {
    const { eventSource } = get()
    if (eventSource) return

    const streamUrl = `${API_BASE}/events/stream?scope=live`
    try {
      const es = new EventSource(streamUrl)
      es.onmessage = (e) => {
        if (!e.data || e.data.startsWith(':')) return
        try {
          const newEvent = JSON.parse(e.data)
          if (!newEvent || !newEvent.event_id) return
          const eventWithLatency = {
            ...newEvent,
            latency_ms: computeEventLatency(newEvent),
          }
          set((state) => {
            const exists = state.events.some((ev) => ev.event_id === eventWithLatency.event_id)
            const updatedEvents = exists
              ? state.events.map((ev) => (ev.event_id === eventWithLatency.event_id ? eventWithLatency : ev))
              : [eventWithLatency, ...state.events]
            return {
              events: updatedEvents,
              total: exists ? state.total : state.total + 1,
              lastUpdated: new Date().toISOString(),
              isLiveStreaming: true,
              lastSseReceivedAt: Date.now(),
            }
          })
        } catch (err) {
          console.warn('Failed to parse SSE event:', err)
        }
      }

      es.onerror = () => {
        set({ isLiveStreaming: false })
      }

      set({ eventSource: es })
    } catch (err) {
      console.warn('Could not initialize EventSource:', err)
      set({ isLiveStreaming: false })
    }
  },

  disconnectSse: () => {
    const { eventSource } = get()
    if (eventSource) {
      eventSource.close()
      set({ eventSource: null, isLiveStreaming: false })
    }
  },

  startPolling: () => {
    const { pollInterval, fetchEvents, connectSse } = get()
    connectSse()
    if (pollInterval) return

    fetchEvents()
    const interval = setInterval(() => {
      fetchEvents()
    }, 5000)
    set({ pollInterval: interval })
  },

  stopPolling: () => {
    const { pollInterval, disconnectSse } = get()
    disconnectSse()
    if (pollInterval) {
      clearInterval(pollInterval)
      set({ pollInterval: null })
    }
  },
}))

export default useLiveEventsStore
