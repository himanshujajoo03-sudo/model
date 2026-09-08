import React from 'react'
import useLayoutStore from '../../stores/layoutStore'
import { toggleAudioMute, playNotificationChime } from '../../utils/audioAlerts'

export default function Header() {
  const {
    toggleMobileDrawer,
    toggleAlertDrawer,
    audioMuted,
    toggleAudioMuted,
  } = useLayoutStore()

  const handleAudioToggle = () => {
    toggleAudioMuted()
    toggleAudioMute()
    playNotificationChime()
  }

  return (
    <header className="h-[56px] bg-white border-b border-slate-200 flex items-center justify-between px-4 md:px-6 flex-shrink-0 z-10 select-none">
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

      {/* Right: Audio Siren, Notification Bell & Duty Profile */}
      <div className="flex items-center gap-2 sm:gap-2.5">
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
