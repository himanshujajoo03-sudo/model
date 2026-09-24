import React from 'react'
import useLayoutStore from '../../stores/layoutStore'
import { toggleAudioMute, playNotificationChime } from '../../utils/audioAlerts'

export default function Header() {
  const {
    toggleMobileDrawer,
    toggleAlertDrawer,
    audioMuted,
    toggleAudioMuted,
    openCitizenReportModal,
  } = useLayoutStore()

  const handleAudioToggle = () => {
    toggleAudioMuted()
    toggleAudioMute()
    playNotificationChime()
  }

  return (
    <header className="sticky top-0 h-[56px] bg-white border-b border-slate-200 flex items-center justify-between px-4 md:px-6 flex-shrink-0 z-20 select-none">
      {/* Left: Mobile Drawer Button */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          onClick={toggleMobileDrawer}
          className="lg:hidden p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          title="Open Navigation"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>

      {/* Right: Report an Event, Audio Siren, Notification Bell & Duty Profile */}
      <div className="flex items-center gap-2 sm:gap-2.5">
        {/* Polished Primary Action: Report an Event */}
        <button
          type="button"
          onClick={openCitizenReportModal}
          id="header-report-event-btn"
          className="group relative inline-flex items-center gap-2 px-3 sm:px-3.5 py-1.5 h-[34px] sm:h-[36px] bg-gradient-to-b from-blue-600 via-blue-700 to-blue-800 hover:from-blue-500 hover:via-blue-600 hover:to-blue-700 active:from-blue-800 active:to-blue-900 text-white rounded-xl text-xs font-bold tracking-tight shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_2px_4px_rgba(30,58,138,0.25),0_1px_2px_rgba(30,58,138,0.15)] hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.45),0_4px_12px_rgba(37,99,235,0.35)] active:shadow-[inset_0_2px_4px_rgba(0,0,0,0.25)] border border-blue-900/80 transition-all duration-150 transform hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 cursor-pointer select-none whitespace-nowrap"
          title="Report an observed weather event or local hazard"
        >
          {/* Weather Warning / Observation Icon */}
          <span className="relative flex items-center justify-center w-5 h-5 rounded-lg bg-white/15 text-white flex-shrink-0 group-hover:bg-white/25 transition-colors">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
              <path d="M12 11v3" stroke="#FDE047" strokeWidth="2.2" />
              <circle cx="12" cy="17" r="0.75" fill="#FDE047" stroke="#FDE047" />
            </svg>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 absolute -top-0.5 -right-0.5 ring-1.5 ring-blue-700 animate-pulse" />
          </span>
          <span className="font-bold text-xs tracking-tight text-white">Report an Event</span>
        </button>

        {/* Audio Siren Toggle Button */}
        <button
          type="button"
          onClick={handleAudioToggle}
          className={`btn-icon relative transition-colors ${
            audioMuted
              ? 'text-slate-400 hover:text-slate-700 bg-slate-50'
              : 'text-emerald-700 bg-emerald-50 border-emerald-200'
          }`}
          title={audioMuted ? 'Audio alerts muted (Click to enable siren/chimes)' : 'Audio alerts active (Click to mute)'}
        >
          <span className="text-xs">{audioMuted ? '🔇' : '🔊'}</span>
        </button>

        {/* Notification Bell -> Opens Alert Drawer */}
        <button
          type="button"
          onClick={toggleAlertDrawer}
          className="btn-icon relative text-slate-600 hover:text-blue-700 hover:bg-blue-50"
          title="Operational Alerts & Dispatches"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-white animate-pulse" />
        </button>

        {/* Officer Duty Avatar */}
        <div className="flex items-center gap-2 pl-1 border-l border-slate-200/80">
          <div className="relative group cursor-pointer">
            <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-300/80 flex items-center justify-center font-mono font-bold text-[11px] text-slate-700 shadow-xs hover:ring-2 hover:ring-brand-blue-500 transition-all">
              IN
            </div>
            <span className="absolute bottom-0 right-0 w-2 h-2 rounded-full bg-emerald-500 ring-1.5 ring-white" />
            <div className="absolute right-0 top-full mt-1.5 hidden group-hover:flex flex-col bg-slate-900 text-white text-[11px] py-1.5 px-2.5 rounded-lg shadow-xl whitespace-nowrap z-50 pointer-events-none">
              <span className="font-bold">National Weather Watcher</span>
              <span className="text-slate-400 text-[10px]">Duty Station: Maharashtra Corridor</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
