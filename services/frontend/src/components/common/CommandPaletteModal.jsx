import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import useLayoutStore from '../../stores/layoutStore'
import useCommandCenterStore from '../../stores/commandCenterStore'
import { WeatherPhenomenonSymbol } from './Symbols'
import { CityCrest } from './BrandLogos'
import { toggleAudioMute, playNotificationChime } from '../../utils/audioAlerts'

const NAVIGATION_ITEMS = [
  { id: 'nav-cc', title: 'Command Center', subtitle: 'National weather overview & interactive GIS', path: '/', category: 'Navigation', icon: '🏛️' },
  { id: 'nav-live', title: 'Live Events', subtitle: 'Atmospheric telemetry stream across 3 active hubs', path: '/events', category: 'Navigation', icon: '📡' },
  { id: 'nav-geo', title: 'Geospatial Intelligence', subtitle: 'Regional GIS micro-corridors & telemetry analysis', path: '/geospatial', category: 'Navigation', icon: '🗺️' },
  { id: 'nav-emerging', title: 'Emerging Events', subtitle: 'Pre-incident anomaly detection & spatial clustering', path: '/emerging', category: 'Navigation', icon: '⚡' },
  { id: 'nav-verify', title: 'Verification Center', subtitle: 'Doppler radar cross-check & officer sign-off', path: '/verification', category: 'Navigation', icon: '🛡️' },
  { id: 'nav-trends', title: 'Event Trends & Analytics', subtitle: 'Statistical temporal patterns & hazard frequency', path: '/analytics/events', category: 'Navigation', icon: '📈' },
  { id: 'nav-citizen', title: 'Citizen Report', subtitle: 'Public crowd-sourced observation desk & reporting form', path: '/citizen-report', category: 'Navigation', icon: '📢' },
  { id: 'nav-review', title: 'Report Review', subtitle: 'Automated briefing reports & incident summaries', path: '/report-review', category: 'Navigation', icon: '📑' },
  { id: 'nav-sys', title: 'System Monitoring', subtitle: 'Pipeline health, ingestion throughput & API status', path: '/system-monitoring', category: 'Navigation', icon: '⚙️' },
]

export default function CommandPaletteModal() {
  const navigate = useNavigate()
  const {
    commandPaletteOpen,
    setCommandPaletteOpen,
    openUpcomingModal,
    toggleAudioMuted,
    audioMuted,
  } = useLayoutStore()

  const mapEvents = useCommandCenterStore((s) => s.mapEvents)
  const setSelectedEvent = useCommandCenterStore((s) => s.setSelectedEvent)

  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef(null)

  // Keyboard shortcut listener: Ctrl+K or Cmd+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(!commandPaletteOpen)
      } else if (e.key === 'Escape' && commandPaletteOpen) {
        setCommandPaletteOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [commandPaletteOpen, setCommandPaletteOpen])

  // Lock body overflow while open, restore on close/unmount
  useEffect(() => {
    if (commandPaletteOpen) {
      const prevOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = prevOverflow || ''
      }
    }
  }, [commandPaletteOpen])

  // Focus input when opened
  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [commandPaletteOpen])

  // Build searchable items list
  const results = useMemo(() => {
    const q = query.trim().toLowerCase()

    // 1. Navigation items
    const matchedNav = NAVIGATION_ITEMS.filter(
      (item) => item.title.toLowerCase().includes(q) || item.subtitle.toLowerCase().includes(q)
    )

    // 2. Quick Actions
    const quickActions = [
      {
        id: 'action-mumbai',
        title: 'Focus Mumbai Corridor',
        subtitle: 'Konkan coast telemetry & radar reflectivity',
        category: 'Quick Actions',
        icon: '🌆',
        city: 'Mumbai',
        action: () => {
          navigate('/geospatial')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-nagpur',
        title: 'Focus Nagpur Corridor',
        subtitle: 'Vidarbha thermal & thunderstorm sensor array',
        category: 'Quick Actions',
        icon: '🏙️',
        city: 'Nagpur',
        action: () => {
          navigate('/geospatial')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-nashik',
        title: 'Focus Nashik Corridor',
        subtitle: 'Western Ghats hydrological & catchment tracking',
        category: 'Quick Actions',
        icon: '🏞️',
        city: 'Nashik',
        action: () => {
          navigate('/geospatial')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-audio',
        title: audioMuted ? 'Unmute Audio Siren Alerts' : 'Mute Audio Siren Alerts',
        subtitle: audioMuted ? 'Enable high-tech radar chirp & hazard alert tones' : 'Silence synthesizer tones',
        category: 'Quick Actions',
        icon: audioMuted ? '🔇' : '🔊',
        action: () => {
          toggleAudioMuted()
          toggleAudioMute()
          playNotificationChime()
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-scope',
        title: 'Geographic Coverage Scope',
        subtitle: 'View active Maharashtra corridors & upcoming 15 national cities',
        category: 'Quick Actions',
        icon: '🗺️',
        action: () => {
          setCommandPaletteOpen(false)
          openUpcomingModal()
        },
      },
    ].filter((a) => a.title.toLowerCase().includes(q) || a.subtitle.toLowerCase().includes(q))

    // 3. Live active events matching query
    const matchedEvents = mapEvents
      .filter((ev) => {
        if (!q) return true
        return (
          ev.city?.toLowerCase().includes(q) ||
          ev.event_id?.toLowerCase().includes(q) ||
          ev.event_category?.toLowerCase().includes(q) ||
          ev.severity?.toLowerCase().includes(q) ||
          ev.state?.toLowerCase().includes(q)
        )
      })
      .slice(0, 5)
      .map((ev) => ({
        id: `event-${ev.event_id}`,
        title: `${ev.event_category?.replace(/_/g, ' ').toUpperCase() || 'WEATHER EVENT'} · ${ev.city || 'Sector'}`,
        subtitle: `ID: #${ev.event_id} · Severity: ${ev.severity?.toUpperCase()} · State: ${ev.state || 'MH'}`,
        category: 'Live Weather Telemetry',
        categorySymbol: ev.event_category,
        city: ev.city,
        action: () => {
          setSelectedEvent(ev)
          navigate('/events')
          setCommandPaletteOpen(false)
        },
      }))

    return [...matchedNav, ...quickActions, ...matchedEvents]
  }, [query, mapEvents, audioMuted, navigate, openUpcomingModal, setSelectedEvent, toggleAudioMuted, setCommandPaletteOpen])

  // Handle keyboard arrow selection
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, results.length))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev - 1 + results.length) % Math.max(1, results.length))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const selected = results[selectedIndex]
      if (selected) {
        if (selected.path) {
          navigate(selected.path)
          setCommandPaletteOpen(false)
        } else if (selected.action) {
          selected.action()
        }
      }
    }
  }

  if (!commandPaletteOpen) return null

  return (
    <div
      className="fixed inset-0 z-[9999] bg-slate-900/45 backdrop-blur-xs flex items-start justify-center pt-16 sm:pt-24 px-4 p-4 animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) setCommandPaletteOpen(false)
      }}
    >
      <div className="w-full max-w-2xl bg-white border border-slate-200/90 rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-900 animate-in zoom-in-95 duration-150">
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-200 bg-white">
          <svg className="w-5 h-5 text-blue-600 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search events, cities, navigation, or operational commands..."
            className="flex-1 bg-transparent border-none outline-none text-sm font-medium text-slate-900 placeholder:text-slate-400"
          />
          {query ? (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="text-xs text-slate-400 hover:text-slate-700 w-5 h-5 flex items-center justify-center rounded-full hover:bg-slate-100"
            >
              ✕
            </button>
          ) : (
            <div className="flex items-center gap-1">
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-500">
                ESC
              </kbd>
            </div>
          )}
        </div>

        {/* Results List */}
        <div className="max-h-[380px] overflow-y-auto p-2 divide-y divide-slate-100 scrollbar-thin bg-white">
          {results.length === 0 ? (
            <div className="py-12 text-center text-slate-400">
              <div className="text-3xl mb-2">🔍</div>
              <p className="text-sm font-semibold text-slate-600">No matching events or commands found</p>
              <p className="text-xs text-slate-400 mt-1">Try searching for "Mumbai", "Flood", "Radar", or "Verify"</p>
            </div>
          ) : (
            results.map((item, idx) => {
              const isSelected = idx === selectedIndex
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    if (item.path) {
                      navigate(item.path)
                      setCommandPaletteOpen(false)
                    } else if (item.action) {
                      item.action()
                    }
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-blue-50/80 border border-blue-200/90 text-blue-950'
                      : 'hover:bg-slate-50 text-slate-800'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-sm shadow-2xs flex-shrink-0">
                      {item.categorySymbol ? (
                        <WeatherPhenomenonSymbol category={item.categorySymbol} size={18} />
                      ) : item.city ? (
                        <CityCrest city={item.city} size="xs" />
                      ) : (
                        <span>{item.icon || '📌'}</span>
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs truncate">{item.title}</span>
                        <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-slate-100 text-slate-500 border border-slate-200/80">
                          {item.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate">{item.subtitle}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 text-[11px] text-slate-400 font-mono pl-2">
                    {isSelected && (
                      <span className="text-blue-600 font-bold flex items-center gap-1">
                        <span>Select</span>
                        <span>↵</span>
                      </span>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer Shortcut Bar */}
        <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-white border border-slate-200 font-mono text-[9.5px]">↑</kbd>
              <kbd className="px-1 py-0.5 rounded bg-white border border-slate-200 font-mono text-[9.5px]">↓</kbd>
              <span>to navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 font-mono text-[9.5px]">↵</kbd>
              <span>to select</span>
            </span>
          </div>
          <span className="text-slate-400 font-medium">
            3 Active Hubs: Mumbai · Nagpur · Nashik
          </span>
        </div>
      </div>
    </div>
  )
}
