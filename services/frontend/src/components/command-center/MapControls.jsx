import React, { useState } from 'react'
import useCommandCenterStore from '../../stores/commandCenterStore'

const CATEGORIES = [
  { value: null, label: 'All' },
  { value: 'rainfall', label: 'Rain' },
  { value: 'heavy_rainfall', label: 'Heavy Rain' },
  { value: 'flood', label: 'Flood' },
  { value: 'heatwave', label: 'Heat' },
  { value: 'thunderstorm', label: 'Storm' },
  { value: 'strong_wind', label: 'Wind' },
]

const SEVERITIES = [
  { value: null, label: 'All' },
  { value: 'low', label: 'Low' },
  { value: 'moderate', label: 'Mod' },
  { value: 'high', label: 'High' },
  { value: 'extreme', label: 'Extreme' },
]

export default function MapControls() {
  const filters = useCommandCenterStore((s) => s.filters)
  const setFilters = useCommandCenterStore((s) => s.setFilters)
  const [open, setOpen] = useState(false)

  return (
    <div className="absolute top-2 right-2 z-[1000]">
      <button
        onClick={() => setOpen(!open)}
        className="bg-white/95 border border-[#D9E0E6] px-2.5 py-1 text-[10px] text-[#526170] hover:text-[#18232D] transition-colors rounded font-medium shadow-[0_1px_3px_rgba(0,0,0,0.08)]"
      >
        Filters {open ? '▾' : '▸'}
      </button>

      {open && (
        <div className="absolute top-8 right-0 bg-white border border-[#D9E0E6] rounded-panel p-2.5 min-w-[180px] shadow-[0_2px_12px_rgba(0,0,0,0.1)]">
          <div className="mb-2">
            <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-1">Category</div>
            <div className="flex flex-wrap gap-1">
              {CATEGORIES.map((c) => (
                <button
                  key={c.label}
                  onClick={() => setFilters({ category: c.value })}
                  className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
                    filters.category === c.value
                      ? 'bg-[#E7F0F4] text-[#477D96] border border-[#477D96]/30'
                      : 'text-[#526170] hover:text-[#18232D] border border-[#D9E0E6]'
                  }`}
                >{c.label}</button>
              ))}
            </div>
          </div>
          <div className="mb-2">
            <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-1">Severity</div>
            <div className="flex flex-wrap gap-1">
              {SEVERITIES.map((s) => (
                <button
                  key={s.label}
                  onClick={() => setFilters({ severity: s.value })}
                  className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
                    filters.severity === s.value
                      ? 'bg-[#E7F0F4] text-[#477D96] border border-[#477D96]/30'
                      : 'text-[#526170] hover:text-[#18232D] border border-[#D9E0E6]'
                  }`}
                >{s.label}</button>
              ))}
            </div>
          </div>
          {(filters.category || filters.severity) && (
            <button
              onClick={() => setFilters({ category: null, severity: null, verification: null })}
              className="text-[10px] text-[#7A8794] hover:text-[#18232D]"
            >Clear</button>
          )}
        </div>
      )}
    </div>
  )
}
