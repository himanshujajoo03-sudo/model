import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useLayoutStore from '../../stores/layoutStore'
import { CityCrest } from './BrandLogos'
import { WeatherPhenomenonSymbol, VerifiedShield, AlertTriangle } from './Symbols'
import {
  isAudioMuted,
  toggleAudioMute,
  playRadarChirp,
  playHazardSiren,
  playNotificationChime,
} from '../../utils/audioAlerts'

const INITIAL_ALERTS = [
  {
    id: 'alt-01',
    severity: 'critical',
    title: 'Heavy Inundation Warning — Mumbai Harbor',
    location: 'Mumbai',
    description: 'Santacruz & Kurla telemetry clusters report precipitation rate exceeding 65mm/hr. High tide confluence alert.',
    time: '2m ago',
    type: 'critical',
    category: 'flood',
    read: false,
  },
  {
    id: 'alt-02',
    severity: 'high',
    title: 'Vidarbha Convective Squall Line — Nagpur Sector',
    location: 'Nagpur',
    description: 'Doppler radar echoes detect rapid vertical storm development with surface wind gusts up to 55 km/h.',
    time: '8m ago',
    type: 'radar',
    category: 'thunderstorm',
    read: false,
  },
  {
    id: 'alt-03',
    severity: 'moderate',
    title: 'Godavari Hydrological Catchment Surge — Nashik',
    location: 'Nashik',
    description: 'Upstream rainfall monitoring station reports gauge level 1.4m below yellow danger mark. Triage queue active.',
    time: '18m ago',
    type: 'sensor',
    category: 'heavy_rainfall',
    read: false,
  },
  {
    id: 'alt-04',
    severity: 'info',
    title: 'INSAT-3D Rapid-Scan Radiometer Resync Complete',
    location: 'Mumbai',
    description: 'Cloud top brightness temperature layer synchronized with IMD national telemetry pipeline.',
    time: '34m ago',
    type: 'operational',
    category: 'cyclone',
    read: true,
  },
]

export default function AlertNotificationDrawer() {
  const navigate = useNavigate()
  const { alertDrawerOpen, setAlertDrawerOpen, audioMuted, toggleAudioMuted } = useLayoutStore()
  const [alerts, setAlerts] = useState(INITIAL_ALERTS)
  const [activeTab, setActiveTab] = useState('all') // 'all', 'critical', 'radar', 'operational'

  if (!alertDrawerOpen) return null

  const unreadCount = alerts.filter((a) => !a.read).length

  const filteredAlerts = alerts.filter((a) => {
    if (activeTab === 'critical') return a.severity === 'critical' || a.severity === 'high'
    if (activeTab === 'radar') return a.type === 'radar' || a.type === 'sensor'
    if (activeTab === 'operational') return a.type === 'operational'
    return true
  })

  const markAllRead = () => {
    setAlerts((prev) => prev.map((a) => ({ ...a, read: true })))
    playNotificationChime()
  }

  const handleTestSound = () => {
    if (audioMuted) {
      toggleAudioMuted()
      toggleAudioMute()
    }
    playHazardSiren()
  }

  return (
    <div
      className="fixed inset-0 z-[9990] bg-slate-900/35 backdrop-blur-2xs flex justify-end animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) setAlertDrawerOpen(false)
      }}
    >
      <div className="w-full sm:w-[420px] bg-white h-full shadow-2xl border-l border-slate-200 flex flex-col animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-white flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900">Alerts & Dispatches</h2>
                {unreadCount > 0 && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-rose-500 text-white animate-pulse">
                    {unreadCount} new
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500">Live operational warning telemetry</p>
            </div>
          </div>

          {/* Header Action Tools */}
          <div className="flex items-center gap-1.5">
            {/* Audio Siren Toggle */}
            <button
              type="button"
              onClick={() => {
                toggleAudioMuted()
                toggleAudioMute()
                playNotificationChime()
              }}
              className={`p-1.5 rounded-lg border text-xs transition-colors ${
                audioMuted
                  ? 'bg-slate-100 border-slate-300 text-slate-400 hover:text-slate-700'
                  : 'bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100'
              }`}
              title={audioMuted ? 'Audio alerts are muted (Click to enable)' : 'Audio alerts are active (Click to mute)'}
            >
              {audioMuted ? '🔇' : '🔊'}
            </button>

            {/* Close Button */}
            <button
              type="button"
              onClick={() => setAlertDrawerOpen(false)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Filter Navigation Tabs */}
        <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-1 text-[11px] font-bold">
            {[
              { id: 'all', label: 'All' },
              { id: 'critical', label: 'Critical' },
              { id: 'radar', label: 'Sensors' },
              { id: 'operational', label: 'Feeds' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-2.5 py-1 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white border border-slate-300 text-blue-700 shadow-2xs font-extrabold'
                    : 'text-slate-500 hover:text-slate-800 hover:bg-slate-200/60'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {unreadCount > 0 && (
            <button
              type="button"
              onClick={markAllRead}
              className="text-[10.5px] font-semibold text-blue-600 hover:text-blue-800 hover:underline"
            >
              Mark all read
            </button>
          )}
        </div>

        {/* Audio Test Bar */}
        <div className="px-4 py-2 bg-blue-50/60 border-b border-blue-100 flex items-center justify-between text-[11px] text-blue-900 flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-ping" />
            <span className="font-semibold">Web Audio Synthesizer:</span>
            <span className="text-slate-600">{audioMuted ? 'Muted' : 'Armed'}</span>
          </div>
          <button
            type="button"
            onClick={handleTestSound}
            className="text-[10px] font-bold px-2 py-0.5 rounded bg-white border border-blue-300 text-blue-700 hover:bg-blue-100/70 shadow-2xs transition-colors"
          >
            🔊 Test Alert Tone
          </button>
        </div>

        {/* Alerts Scrollable Feed */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2.5 scrollbar-thin bg-white">
          {filteredAlerts.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <div className="text-3xl mb-2">✅</div>
              <p className="text-xs font-bold text-slate-700">No active alerts in this category</p>
              <p className="text-[11px] text-slate-400">All corridors within normal operational margins</p>
            </div>
          ) : (
            filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-3 rounded-xl border transition-all ${
                  alert.read
                    ? 'bg-white border-slate-200 text-slate-700'
                    : alert.severity === 'critical'
                    ? 'bg-rose-50/40 border-rose-200 shadow-2xs'
                    : 'bg-amber-50/30 border-amber-200 shadow-2xs'
                }`}
              >
                {/* Top Row: Crest + Title + Badge */}
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <CityCrest city={alert.location} size="xs" />
                    <span className="text-xs font-bold text-slate-900 truncate">
                      {alert.title}
                    </span>
                  </div>
                  <span
                    className={`text-[9.5px] font-mono font-bold px-1.5 py-0.5 rounded uppercase border flex-shrink-0 ${
                      alert.severity === 'critical'
                        ? 'bg-rose-100 text-rose-800 border-rose-300'
                        : alert.severity === 'high'
                        ? 'bg-amber-100 text-amber-800 border-amber-300'
                        : 'bg-slate-100 text-slate-700 border-slate-200'
                    }`}
                  >
                    {alert.severity}
                  </span>
                </div>

                {/* Description */}
                <p className="text-[11.5px] text-slate-600 leading-relaxed mb-2.5">
                  {alert.description}
                </p>

                {/* Bottom Row: Timestamp + Action Buttons */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100/90 text-[10.5px]">
                  <span className="text-slate-400 font-medium">{alert.time}</span>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        navigate('/geospatial')
                        setAlertDrawerOpen(false)
                      }}
                      className="font-bold text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      Inspect GIS →
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        navigate('/events')
                        setAlertDrawerOpen(false)
                      }}
                      className="font-bold text-slate-600 hover:text-slate-900 hover:underline"
                    >
                      Dossier
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
          <span className="font-semibold text-slate-700">Maharashtra Dispatch Grid</span>
          <span className="text-slate-400">Coverage: Mumbai · Nagpur · Nashik</span>
        </div>
      </div>
    </div>
  )
}
