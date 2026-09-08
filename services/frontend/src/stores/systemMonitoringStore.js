import { create } from 'zustand'
import { apiGet } from '../api/client'

const useSystemMonitoringStore = create((set, get) => ({
  // System status data
  systemStatus: null,
  health: null,
  dataStats: null,

  // Status
  loading: true,
  error: null,
  lastUpdated: null,

  // Polling
  pollInterval: null,

  fetchSystemStatus: async () => {
    try {
      const [status, health, stats] = await Promise.all([
        apiGet('/system/status'),
        apiGet('/health'),
        apiGet('/events/stats'),
      ])
      set({
        systemStatus: status,
        health: health,
        dataStats: stats,
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

  refresh: async () => {
    await get().fetchSystemStatus()
  },

  startPolling: () => {
    const { pollInterval, fetchSystemStatus } = get()
    if (pollInterval) return
    fetchSystemStatus()
    const interval = setInterval(() => { fetchSystemStatus() }, 15000)
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

export default useSystemMonitoringStore
