import React, { useState, useRef, useEffect, useMemo } from 'react'
import { UPCOMING_CITIES, ACTIVE_CITIES } from '../../constants/cities'
import useLayoutStore from '../../stores/layoutStore'

export default function ComingSoonModal({
  isOpen: propIsOpen,
  onClose: propOnClose,
  isMinimized: propIsMinimized,
  onMinimize: propOnMinimize,
  onRestore: propOnRestore,
}) {
  const storeIsOpen = useLayoutStore((s) => s.upcomingModalOpen)
  const storeIsMinimized = useLayoutStore((s) => s.upcomingModalMinimized)
  const storeClose = useLayoutStore((s) => s.closeUpcomingModal)
  const storeMinimize = useLayoutStore((s) => s.minimizeUpcomingModal)
  const storeRestore = useLayoutStore((s) => s.restoreUpcomingModal)

  const isOpen = propIsOpen !== undefined ? propIsOpen : storeIsOpen
  const isMinimized = propIsMinimized !== undefined ? propIsMinimized : storeIsMinimized
  const onClose = propOnClose || storeClose
  const onMinimize = propOnMinimize || storeMinimize
  const onRestore = propOnRestore || storeRestore

  const bodyRef = useRef(null)
  const savedScrollTop = useRef(0)
  const [citySearch, setCitySearch] = useState('')
  const [selectedCityName, setSelectedCityName] = useState(null)
  const [isAnimatingOut, setIsAnimatingOut] = useState(false)

  // Track user scroll position within the modal
  const handleScroll = (e) => {
    savedScrollTop.current = e.currentTarget.scrollTop
  }

  // Restore scroll position whenever the modal transitions back from minimized to open
  useEffect(() => {
    if (isOpen && !isMinimized && bodyRef.current) {
      const raf = requestAnimationFrame(() => {
        if (bodyRef.current) {
          bodyRef.current.scrollTop = savedScrollTop.current
        }
      })
      return () => cancelAnimationFrame(raf)
    }
  }, [isOpen, isMinimized])

  // Handle minimize with smooth 200ms transition
  const handleMinimize = (e) => {
    e?.stopPropagation?.()
    if (bodyRef.current) {
      savedScrollTop.current = bodyRef.current.scrollTop
    }
    setIsAnimatingOut(true)
    setTimeout(() => {
      setIsAnimatingOut(false)
      onMinimize()
    }, 200)
  }

  // Handle restore back to full modal
  const handleRestore = (e) => {
    e?.stopPropagation?.()
    onRestore()
  }

  // Handle permanent close
  const handleClose = (e) => {
    e?.stopPropagation?.()
    onClose()
  }

  // Filter upcoming cities
  const filteredUpcomingCities = useMemo(() => {
    if (!citySearch.trim()) return UPCOMING_CITIES
    const q = citySearch.toLowerCase()
    return UPCOMING_CITIES.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.state.toLowerCase().includes(q)
    )
  }, [citySearch])

  if (!isOpen) return null

  // ═══════════════════════════════════════════════════════════════
  // Minimized State: Floating card at bottom-right corner
  // ═══════════════════════════════════════════════════════════════
  if (isMinimized) {
    return (
      <div
        className="fixed bottom-5 right-5 z-50 w-[380px] max-w-[calc(100vw-2.5rem)] bg-white border border-slate-200/90 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] p-3 flex items-center justify-between gap-3 animate-in slide-in-from-bottom-3 fade-in-0 duration-200 cursor-pointer hover:border-brand-blue-400 hover:shadow-[0_12px_36px_rgb(0,0,0,0.16)] transition-all group select-none"
        onClick={handleRestore}
        role="button"
        tabIndex={0}
        title="Click to restore Geographic Coverage Scope"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            handleRestore(e)
          }
        }}
      >
        {/* Left: Icon & Information */}
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-brand-blue-50 border border-brand-blue-200/70 flex items-center justify-center text-sm flex-shrink-0 relative">
            <span>📍</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 absolute -top-0.5 -right-0.5 ring-2 ring-white animate-pulse" />
          </div>
          <div className="truncate">
            <div className="text-xs font-bold text-slate-900 truncate group-hover:text-brand-blue-600 transition-colors">
              Geographic Coverage Scope
            </div>
            <div className="text-[11px] text-slate-500 truncate flex items-center gap-1.5 mt-0.5">
              <span className="font-semibold text-emerald-700 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                3 Active Cities
              </span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-600">15 Cities Scheduled</span>
            </div>
          </div>
        </div>

        {/* Right: Action Buttons */}
        <div
          className="flex items-center gap-1.5 flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={handleRestore}
            title="Restore"
            className="px-2.5 py-1 bg-brand-blue-50 hover:bg-brand-blue-100 text-brand-blue-700 border border-brand-blue-200 rounded-lg text-xs font-bold flex items-center gap-1 transition-all shadow-2xs hover:scale-[1.02] active:scale-[0.98]"
          >
            <span>Restore</span>
            <span className="text-xs font-black">↑</span>
          </button>
          <button
            type="button"
            onClick={handleClose}
            title="Close"
            className="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center text-sm font-semibold transition-colors"
          >
            ✕
          </button>
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════════════════
  // Open State: Polished centered modal with dimmed page backdrop
  // ═══════════════════════════════════════════════════════════════
  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs transition-opacity duration-200 ${
        isAnimatingOut ? 'opacity-0 pointer-events-none' : 'opacity-100 animate-in fade-in-0'
      }`}
      onClick={handleMinimize}
    >
      <div
        className={`relative w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-dropdown overflow-hidden flex flex-col max-h-[85vh] transition-all duration-200 ease-out ${
          isAnimatingOut
            ? 'scale-90 translate-y-12 translate-x-12 opacity-0'
            : 'scale-100 translate-y-0 translate-x-0 opacity-100 animate-in zoom-in-95 duration-200'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 bg-slate-50/50 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-blue-50 border border-brand-blue-200/70 flex items-center justify-center text-brand-blue-700 font-bold text-sm relative">
              📍
              <span className="w-2 h-2 rounded-full bg-emerald-500 absolute -top-0.5 -right-0.5 ring-2 ring-white animate-pulse" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Geographic Coverage Scope
              </h3>
              <p className="text-[11px] text-slate-500">
                National Weather Intelligence Pipeline · Multi-Hub Scope
              </p>
            </div>
          </div>

          {/* Header Action Buttons: Minimize (−) and Close (✕) */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleMinimize}
              title="Minimize"
              className="w-8 h-8 rounded-lg bg-white hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 flex items-center justify-center font-bold text-base transition-colors shadow-2xs"
              aria-label="Minimize"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
            </button>

            <button
              type="button"
              onClick={handleClose}
              title="Close"
              className="w-8 h-8 rounded-lg bg-white hover:bg-rose-50 text-slate-400 hover:text-rose-600 border border-slate-200 hover:border-rose-200 flex items-center justify-center text-sm font-semibold transition-colors shadow-2xs"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Modal Body with preserved scroll position */}
        <div
          ref={bodyRef}
          onScroll={handleScroll}
          className="p-5 overflow-y-auto space-y-4 scrollbar-thin flex-1"
        >
          {/* Active Cities Banner */}
          <div className="p-3.5 bg-emerald-50/70 border border-emerald-200 rounded-xl">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-bold text-emerald-950 uppercase tracking-wide">
                  Currently Live (3 Active Hubs)
                </span>
              </div>
              <span className="text-[10px] font-bold text-emerald-700 px-2 py-0.5 bg-white border border-emerald-200 rounded-md shadow-2xs">
                MVP Active
              </span>
            </div>
            <p className="text-xs text-emerald-900 mb-2 leading-relaxed">
              Full real-time streaming, automated verification, and GIS risk mapping are operational for:
            </p>
            <div className="flex flex-wrap gap-2">
              {ACTIVE_CITIES.map((c) => (
                <div
                  key={c.name}
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-white border border-emerald-300 rounded-lg text-xs font-bold text-slate-800 shadow-xs hover:border-emerald-400 transition-colors"
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: c.color }}
                  />
                  <span>{c.name}</span>
                  <span className="text-[10px] text-slate-400 font-normal">
                    ({c.region})
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming Cities Section */}
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 mb-2">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center gap-1.5">
                <span>Phase II Rollout Cities</span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                  Updated Soon
                </span>
              </span>
              <span className="text-[11px] text-slate-400">
                15 Cities Scheduled
              </span>
            </div>
            <p className="text-xs text-slate-600 mb-3 leading-relaxed">
              Integration of additional radar networks, local automated weather stations, and municipal citizen feeds is underway for the following tier-1 urban corridors:
            </p>

            {/* Quick Search Filter inside modal */}
            <div className="mb-3 relative">
              <input
                type="text"
                value={citySearch}
                onChange={(e) => setCitySearch(e.target.value)}
                placeholder="Search upcoming cities (e.g. Pune, Delhi, Bengaluru)..."
                className="w-full h-8 pl-8 pr-7 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-brand-blue-500 focus:bg-white transition-all"
              />
              <span className="absolute left-2.5 top-2 text-xs text-slate-400">🔍</span>
              {citySearch && (
                <button
                  type="button"
                  onClick={() => setCitySearch('')}
                  className="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {filteredUpcomingCities.map((city) => {
                const isSelected = selectedCityName === city.name
                return (
                  <div
                    key={city.name}
                    onClick={() => setSelectedCityName(isSelected ? null : city.name)}
                    className={`p-2 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? 'bg-amber-50 border-amber-300 ring-1 ring-amber-300'
                        : 'bg-slate-50 border-slate-200/80 hover:bg-slate-100/80'
                    }`}
                  >
                    <div className="truncate min-w-0 pr-1">
                      <div className="text-xs font-semibold text-slate-800 truncate">
                        {city.name}
                      </div>
                      <div className="text-[10px] text-slate-400 truncate">
                        {city.state}
                      </div>
                    </div>
                    <span
                      className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0"
                      title="Phase II: Updated Soon"
                    />
                  </div>
                )
              })}
            </div>

            {selectedCityName && (
              <div className="mt-3 p-2.5 bg-amber-50/60 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center justify-between animate-in fade-in-0 duration-150">
                <div>
                  <span className="font-bold">{selectedCityName}</span> is slated for automated radar telemetry in Phase II.
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedCityName(null)}
                  className="text-[10px] font-bold text-amber-700 hover:text-amber-900 ml-2"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between flex-shrink-0">
          <button
            type="button"
            onClick={handleMinimize}
            className="text-xs text-slate-500 hover:text-brand-blue-600 font-semibold flex items-center gap-1.5 transition-colors"
          >
            <span>Minimize to corner</span>
            <span className="text-[11px] font-black text-slate-400 group-hover:text-brand-blue-600">↘</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleMinimize}
              className="btn-secondary text-xs py-1.5 px-3"
            >
              Minimize
            </button>
            <button
              type="button"
              onClick={handleClose}
              className="btn-primary text-xs py-1.5 px-4"
            >
              Got it
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
