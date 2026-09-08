import React, { useState, useRef, useEffect, useMemo } from 'react'
import { ACTIVE_CITIES, UPCOMING_CITIES } from '../../constants/cities'

/**
 * Premium Supermodel Dropdown Component
 * Features:
 * - City / State / Status icons & logos
 * - Availability indicators (● Available in emerald, ○ Updated Soon in amber)
 * - Search filtering
 * - Keyboard navigation & click outside
 * - Selected checkmarks
 */
export default function ModelSelect({
  label,
  options: customOptions,
  value,
  onChange,
  onSelectUpcoming,
  placeholder = 'Select City...',
  icon = '📍',
  className = '',
  compact = false,
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef(null)

  // Default City Options if no custom options are provided
  const cityOptions = useMemo(() => {
    const active = ACTIVE_CITIES.map((c) => ({
      value: c.name,
      label: c.name,
      state: c.state,
      region: c.region,
      icon: c.name === 'Mumbai' ? '🌆' : c.name === 'Nagpur' ? '🏙️' : '🏞️',
      color: c.color,
      photo: c.photo,
      status: 'available',
      statusText: 'Available · MVP',
    }))

    const upcoming = UPCOMING_CITIES.map((c) => ({
      value: c.name,
      label: c.name,
      state: c.state,
      region: c.region,
      icon: '🔒',
      color: '#94A3B8',
      status: 'updated_soon',
      statusText: 'Updated Soon',
    }))

    return [...active, ...upcoming]
  }, [])

  const options = customOptions || cityOptions

  // Find currently selected option
  const selectedOption = options.find(
    (o) => o.value === value || (value && o.label?.toLowerCase() === value.toLowerCase())
  )

  // Filter options by search term
  const filteredOptions = options.filter((o) => {
    if (!search.trim()) return true
    const term = search.toLowerCase()
    return (
      (o.label && o.label.toLowerCase().includes(term)) ||
      (o.state && o.state.toLowerCase().includes(term)) ||
      (o.region && o.region.toLowerCase().includes(term))
    )
  })

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Dropdown Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-between gap-2.5 w-full bg-white border border-slate-200 rounded-xl text-slate-800 transition-all duration-150 shadow-xs hover:border-slate-300 hover:bg-slate-50/50 ${
          compact ? 'h-8 px-2.5 text-xs' : 'h-9 px-3 text-xs'
        } ${isOpen ? 'border-brand-blue-500 ring-2 ring-brand-blue-500/10' : ''}`}
      >
        <div className="flex items-center gap-2 min-w-0 truncate">
          <span className="text-sm flex-shrink-0">{icon}</span>
          {label && (
            <span className="text-slate-400 font-medium flex-shrink-0">
              {label}:
            </span>
          )}
          {selectedOption ? (
            <div className="flex items-center gap-1.5 min-w-0 truncate">
              {selectedOption.color && (
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: selectedOption.color }}
                />
              )}
              {selectedOption.photo && (
                <img
                  src={selectedOption.photo}
                  alt=""
                  className="w-4 h-4 rounded-full object-cover border border-slate-200 flex-shrink-0"
                />
              )}
              <span className="font-bold text-slate-900 truncate">
                {selectedOption.label}
              </span>
              {selectedOption.state && (
                <span className="text-[10px] text-slate-400 font-normal hidden sm:inline truncate">
                  ({selectedOption.state})
                </span>
              )}
            </div>
          ) : (
            <span className="text-slate-400 truncate">{placeholder}</span>
          )}
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0 ml-1">
          {selectedOption && (
            <span
              onClick={(e) => {
                e.stopPropagation()
                onChange(null)
              }}
              title="Clear selection"
              className="text-slate-300 hover:text-slate-600 text-xs px-1"
            >
              ✕
            </span>
          )}
          <span className="text-slate-400 text-[10px] transition-transform duration-200">
            {isOpen ? '▲' : '▼'}
          </span>
        </div>
      </button>

      {/* Dropdown Menu Popup */}
      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-slate-200 rounded-2xl shadow-dropdown z-50 overflow-hidden min-w-[260px] max-h-[340px] flex flex-col animate-in fade-in-0 zoom-in-95 duration-100">
          {/* Search Box */}
          <div className="p-2.5 border-b border-slate-100 bg-slate-50/70 flex-shrink-0">
            <div className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search city or state..."
                className="w-full h-8 pl-8 pr-7 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-brand-blue-500 focus:ring-1 focus:ring-brand-blue-500 shadow-2xs"
                autoFocus
              />
              <span className="absolute left-2.5 top-2 text-xs text-slate-400">🔍</span>
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {/* Group Header: Active MVP */}
          <div className="overflow-y-auto p-1.5 divide-y divide-slate-50 scrollbar-thin">
            <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
              <span>Active Telemetry Hubs</span>
              <span className="text-emerald-700 font-bold bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                3 Live
              </span>
            </div>

            {filteredOptions.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-400">
                No matching cities found
              </div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = selectedOption?.value === opt.value
                const isUpcoming = opt.status === 'updated_soon'

                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      if (isUpcoming) {
                        setIsOpen(false)
                        if (onSelectUpcoming) onSelectUpcoming(opt)
                      } else {
                        onChange(opt.value)
                        setIsOpen(false)
                        setSearch('')
                      }
                    }}
                    className={`flex items-center justify-between w-full px-2.5 py-2 rounded-xl text-left text-xs transition-all ${
                      isUpcoming
                        ? 'hover:bg-amber-50/50 text-slate-500'
                        : isSelected
                        ? 'bg-brand-blue-50 text-brand-blue-900 font-semibold'
                        : 'text-slate-700 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 truncate">
                      {/* City Icon / Thumbnail */}
                      <div className="w-7 h-7 rounded-lg bg-slate-100 border border-slate-200/80 flex items-center justify-center text-sm flex-shrink-0 overflow-hidden shadow-2xs">
                        {opt.photo ? (
                          <img
                            src={opt.photo}
                            alt=""
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span>{opt.icon || '📍'}</span>
                        )}
                      </div>

                      {/* City Name & State */}
                      <div className="truncate min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                              isUpcoming ? 'bg-amber-400' : 'bg-emerald-500 animate-pulse'
                            }`}
                          />
                          <span className="font-bold text-slate-900 truncate">
                            {opt.label}
                          </span>
                        </div>
                        <div className="text-[10.5px] text-slate-400 truncate">
                          {opt.state} {opt.region ? `· ${opt.region}` : ''}
                        </div>
                      </div>
                    </div>

                    {/* Status Badge & Checkmark */}
                    <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                      {isUpcoming ? (
                        <span className="text-[9.5px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                          Updated Soon
                        </span>
                      ) : (
                        <span className="text-[9.5px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                          Available
                        </span>
                      )}

                      {isSelected && (
                        <span className="text-brand-blue-600 font-bold text-sm ml-1">
                          ✓
                        </span>
                      )}
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
