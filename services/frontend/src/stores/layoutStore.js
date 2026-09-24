import { create } from 'zustand'

const useLayoutStore = create((set) => ({
  // Sidebar expanded / collapsed state (persisted in localStorage)
  sidebarCollapsed: localStorage.getItem('meteo_sidebar_collapsed') === 'true',
  toggleSidebar: () =>
    set((state) => {
      const next = !state.sidebarCollapsed
      localStorage.setItem('meteo_sidebar_collapsed', String(next))
      return { sidebarCollapsed: next }
    }),

  // Mobile drawer open state
  mobileDrawerOpen: false,
  setMobileDrawerOpen: (open) => set({ mobileDrawerOpen: open }),
  toggleMobileDrawer: () =>
    set((state) => ({ mobileDrawerOpen: !state.mobileDrawerOpen })),

  // Geographic Coverage Scope modal state (isOpen, isMinimized)
  upcomingModalOpen: false,
  upcomingModalMinimized: false,
  setUpcomingModalOpen: (open) => set({ upcomingModalOpen: open, upcomingModalMinimized: false }),
  openUpcomingModal: () => set({ upcomingModalOpen: true, upcomingModalMinimized: false }),
  closeUpcomingModal: () => set({ upcomingModalOpen: false, upcomingModalMinimized: false }),
  minimizeUpcomingModal: () => set({ upcomingModalMinimized: true }),
  restoreUpcomingModal: () => set({ upcomingModalMinimized: false }),

  // Global search input
  globalSearch: '',
  setGlobalSearch: (search) => set({ globalSearch: search }),

  // Global Command Palette (Ctrl+K / ⌘K)
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  toggleCommandPalette: () => set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),

  // Alert & Operations Notification Drawer
  alertDrawerOpen: false,
  setAlertDrawerOpen: (open) => set({ alertDrawerOpen: open }),
  toggleAlertDrawer: () => set((state) => ({ alertDrawerOpen: !state.alertDrawerOpen })),

  // Audio alerts mute state
  audioMuted: localStorage.getItem('meteo_audio_muted') === 'true',
  toggleAudioMuted: () =>
    set((state) => {
      const next = !state.audioMuted
      localStorage.setItem('meteo_audio_muted', String(next))
      return { audioMuted: next }
    }),

  // Citizen Event Report Modal
  citizenReportModalOpen: false,
  setCitizenReportModalOpen: (open) => set({ citizenReportModalOpen: open }),
  openCitizenReportModal: () => set({ citizenReportModalOpen: true }),
  closeCitizenReportModal: () => set({ citizenReportModalOpen: false }),
}))

export default useLayoutStore
