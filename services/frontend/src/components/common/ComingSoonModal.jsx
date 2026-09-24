import React, { useState, useRef, useEffect, useMemo } from 'react'
import { ACTIVE_CITIES } from '../../constants/cities'
import useLayoutStore from '../../stores/layoutStore'
import useCommandCenterStore from '../../stores/commandCenterStore'

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
  const setFilters = useCommandCenterStore((s) => s.setFilters)

  const isOpen = propIsOpen !== undefined ? propIsOpen : storeIsOpen
  const isMinimized = propIsMinimized !== undefined ? propIsMinimized : storeIsMinimized
  const onClose = propOnClose || storeClose
  const onMinimize = propOnMinimize || storeMinimize
  const onRestore = propOnRestore || storeRestore

  const bodyRef = useRef(null)
  const savedScrollTop = useRef(0)
  const [citySearch, setCitySearch] = useState('')
  const [selectedCity, setSelectedCity] = useState(null)
  const [selectedZone, setSelectedZone] = useState('All')
  const [isAnimatingOut, setIsAnimatingOut] = useState(false)

  const ZONES = ['All', 'West', 'North', 'South', 'East', 'Central', 'Northeast']

  const handleScroll = (e) => {
    savedScrollTop.current = e.currentTarget.scrollTop
  }

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

  // Lock body overflow while open and not minimized, restore on close/minimize/unmount
  useEffect(() => {
    if (isOpen && !isMinimized) {
      const prevOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = prevOverflow || ''
      }
    }
  }, [isOpen, isMinimized])

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

  const handleRestore = (e) => {
    e?.stopPropagation?.()
    onRestore()
  }

  const handleClose = (e) => {
    e?.stopPropagation?.()
    onClose()
  }

  const handleSelectCity = (city) => {
    setSelectedCity(city)
    setFilters({ city: city.name })
    handleClose()
  }

  const filteredCities = useMemo(() => {
    return ACTIVE_CITIES.filter((c) => {
      const matchesZone = selectedZone === 'All' || c.zone === selectedZone
      const q = citySearch.toLowerCase().trim()
      const matchesSearch =
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.state.toLowerCase().includes(q) ||
        (c.zone && c.zone.toLowerCase().includes(q)) ||
        (c.region && c.region.toLowerCase().includes(q))
      return matchesZone && matchesSearch
    })
  }, [citySearch, selectedZone])

  if (!isOpen) return null

  // Minimized State
  if (isMinimized) {
    return (
      <div
        className="fixed bottom-5 right-5 z-50 w-[380px] max-w-[calc(100vw-2.5rem)] bg-white border border-slate-200/90 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] p-3 flex items-center justify-between gap-3 animate-in slide-in-from-bottom-3 fade-in-0 duration-200 cursor-pointer hover:border-brand-blue-400 hover:shadow-[0_12px_36px_rgb(0,0,0,0.16)] transition-all group select-none"
        onClick={handleRestore}
        role="button"
        tabIndex={0}
        title="Click to restore Pan-India City Weather Explorer"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-brand-blue-50 border border-brand-blue-200/70 flex items-center justify-center text-sm flex-shrink-0 relative">
            <span>🗺️</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 absolute -top-0.5 -right-0.5 ring-2 ring-white animate-pulse" />
          </div>
          <div className="truncate">
            <div className="text-xs font-bold text-slate-900 truncate group-hover:text-brand-blue-600 transition-colors">
              Pan-India City Weather Explorer
            </div>
            <div className="text-[11px] text-slate-500 truncate flex items-center gap-1.5 mt-0.5">
              <span className="font-semibold text-emerald-700 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                {ACTIVE_CITIES.length} Cities Monitored
              </span>
            </div>
          </div>
        </div>

        <div
          className="flex items-center gap-1.5 flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={handleRestore}
            className="px-2.5 py-1 bg-brand-blue-50 hover:bg-brand-blue-100 text-brand-blue-700 border border-brand-blue-200 rounded-lg text-xs font-bold transition-all"
          >
            Restore ↑
          </button>
          <button
            type="button"
            onClick={handleClose}
            className="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center text-sm font-semibold transition-colors"
          >
            ✕
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-xs transition-opacity duration-200 ${
        isAnimatingOut ? 'opacity-0' : 'opacity-100 animate-in fade-in-0'
      }`}
      onClick={handleClose}
    >
      <div
        className={`bg-white rounded-3xl border border-slate-200 shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden transition-all duration-200 ${
          isAnimatingOut
            ? 'scale-95 opacity-0 translate-y-2'
            : 'scale-100 opacity-100 animate-in zoom-in-95'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-brand-blue-50 border border-brand-blue-200 flex items-center justify-center text-base shadow-2xs">
              <span>🇮🇳</span>
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
                Pan-India Meteorological Coverage ({ACTIVE_CITIES.length} Cities)
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                  Live & 30D Past Data
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Real-time Doppler radar telemetry & 30-day historical archive across all Indian zones
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleMinimize}
              className="w-8 h-8 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center text-sm font-bold"
              title="Minimize"
            >
              −
            </button>
            <button
              type="button"
              onClick={handleClose}
              className="w-8 h-8 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center text-sm font-bold"
              title="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div
          ref={bodyRef}
          onScroll={handleScroll}
          className="p-6 overflow-y-auto scrollbar-thin flex flex-col gap-4 flex-1"
        >
          {/* Search Bar & Zone Filter */}
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={citySearch}
                onChange={(e) => setCitySearch(e.target.value)}
                placeholder="Search any Indian city, state, or region..."
                className="w-full h-9 pl-9 pr-8 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-brand-blue-500 focus:bg-white transition-all shadow-2xs"
              />
              <span className="absolute left-3 top-2.5 text-xs text-slate-400">🔍</span>
              {citySearch && (
                <button
                  type="button"
                  onClick={() => setCitySearch('')}
                  className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
              {ZONES.map((zone) => (
                <button
                  key={zone}
                  type="button"
                  onClick={() => setSelectedZone(zone)}
                  className={`text-[10.5px] font-bold px-2.5 py-1.5 rounded-lg transition-all ${
                    selectedZone === zone
                      ? 'bg-brand-blue-600 text-white shadow-2xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {zone}
                </button>
              ))}
            </div>
          </div>

          {/* City Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {filteredCities.map((city) => (
              <div
                key={city.name}
                onClick={() => handleSelectCity(city)}
                className="p-3 rounded-2xl border border-slate-200 hover:border-brand-blue-400 bg-white hover:bg-brand-blue-50/30 transition-all cursor-pointer shadow-xs group"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full ring-2 ring-slate-100"
                      style={{ backgroundColor: city.color }}
                    />
                    <span className="text-xs font-bold text-slate-900 group-hover:text-brand-blue-700">
                      {city.name}
                    </span>
                  </div>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Live Active
                  </span>
                </div>

                <div className="text-[10.5px] text-slate-500 mb-1.5">
                  {city.state} · {city.zone} India
                </div>

                <div className="text-[10px] text-slate-400 line-clamp-1 mb-2">
                  {city.description}
                </div>

                <div className="flex items-center justify-between text-[10px] font-bold text-brand-blue-600 pt-1.5 border-t border-slate-100">
                  <span>{city.sensors.split('·')[0]}</span>
                  <span className="group-hover:translate-x-0.5 transition-transform">Filter →</span>
                </div>
              </div>
            ))}
          </div>

          {filteredCities.length === 0 && (
            <div className="text-center py-8 text-slate-400 text-xs">
              No cities match your search filter.
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between flex-shrink-0">
          <span className="text-xs text-slate-500 font-medium">
            Showing {filteredCities.length} of {ACTIVE_CITIES.length} Indian weather corridors
          </span>

          <button
            type="button"
            onClick={handleClose}
            className="btn-primary text-xs py-1.5 px-4"
          >
            Close Explorer
          </button>
        </div>
      </div>
    </div>
  )
}
