import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useCommandCenterStore from '../../stores/commandCenterStore'
import { getCityMetadata } from '../../constants/cities'

const SEV_BADGE = {
  critical: 'bg-rose-50 text-rose-700 border-rose-200',
  extreme: 'bg-rose-50 text-rose-700 border-rose-200',
  high: 'bg-orange-50 text-orange-700 border-orange-200',
  moderate: 'bg-blue-50 text-blue-700 border-blue-200',
  low: 'bg-slate-50 text-slate-600 border-slate-200',
}

const CAT_LABELS = {
  heavy_rainfall: 'Heavy Rain',
  rainfall: 'Rain',
  urban_flooding: 'Urban Flood',
  flood: 'Flood',
  heatwave: 'Heatwave',
  thunderstorm: 'Thunderstorm',
  lightning: 'Lightning',
  strong_wind: 'Strong Wind',
  hailstorm: 'Hailstorm',
  dust_storm: 'Dust Storm',
  cyclone: 'Cyclone',
  fog: 'Dense Fog',
}

function ago(iso) {
  if (!iso) return ''
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h`
  return `${Math.floor(s / 86400)}d`
}

export default function LiveEventFeed() {
  const events = useCommandCenterStore((s) => s.events)
  const lastUpdated = useCommandCenterStore((s) => s.lastUpdated)
  const navigate = useNavigate()

  const [filterCity, setFilterCity] = useState(null)

  // Filter and sort events
  const filtered = events.filter((e) => {
    if (!filterCity) return true
    const norm = (e.city || '').toLowerCase()
    const target = filterCity.toLowerCase()
    if (target === 'nashik' || target === 'nasik') {
      return norm === 'nashik' || norm === 'nasik'
    }
    return norm === target
  })

  return (
    <div className="h-full bg-white border border-slate-200 rounded-2xl overflow-hidden flex flex-col shadow-xs">
      {/* Feed Header */}
      <div className="px-3.5 py-2.5 border-b border-slate-200 bg-white flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.6)]" />
            <span className="text-[11px] font-bold text-slate-900 uppercase tracking-wider">
              Live Event Feed
            </span>
          </div>
          <span className="text-[10px] font-bold text-slate-600 mono bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200/80">
            {filtered.length} stream items
          </span>
        </div>

        {/* City Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-thin">
          <button
            type="button"
            onClick={() => setFilterCity(null)}
            className={`px-2.5 py-1 text-[10.5px] font-bold rounded-lg transition-all ${
              !filterCity
                ? 'bg-blue-600 text-white shadow-2xs'
                : 'bg-slate-100 hover:bg-slate-200/80 text-slate-600 border border-slate-200/60'
            }`}
          >
            All
          </button>
          {['Mumbai', 'Nagpur', 'Nashik'].map((city) => {
            const isSelected = filterCity === city
            return (
              <button
                key={city}
                type="button"
                onClick={() => setFilterCity(isSelected ? null : city)}
                className={`px-2.5 py-1 text-[10.5px] font-bold rounded-lg transition-all ${
                  isSelected
                    ? 'bg-blue-600 text-white shadow-2xs'
                    : 'bg-slate-100 hover:bg-slate-200/80 text-slate-600 border border-slate-200/60'
                }`}
              >
                {city}
              </button>
            )
          })}
        </div>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 scrollbar-thin">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 p-4 text-center">
            <span className="text-2xl mb-1">📡</span>
            <span className="text-xs font-bold text-slate-700">
              No active events in scope
            </span>
            <span className="text-[11px] text-slate-400 mt-0.5">
              Live feeds update automatically every 5s
            </span>
          </div>
        ) : (
          filtered.map((e) => {
            const cityMeta = getCityMetadata(e.city)
            const sevClass = SEV_BADGE[e.severity] || SEV_BADGE.moderate
            const catLabel = CAT_LABELS[e.event_category] || e.event_category

            return (
              <div
                key={e.event_id}
                onClick={() => e.event_id && navigate(`/events/${e.event_id}`)}
                className="p-3 hover:bg-slate-50/80 transition-colors cursor-pointer group"
              >
                {/* City Tag & Severity Badge */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5 min-w-0">
                    {cityMeta?.color && (
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: cityMeta.color }}
                      />
                    )}
                    <span className="font-bold text-xs text-slate-900 truncate">
                      {e.city || 'India'}
                    </span>
                    <span className="text-[10px] text-slate-400 truncate">
                      {e.district || ''}
                    </span>
                  </div>

                  <span
                    className={`text-[9.5px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${sevClass}`}
                  >
                    {e.severity || 'Normal'}
                  </span>
                </div>

                {/* Event Category & Description */}
                <div className="text-xs font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
                  <span className="text-brand-blue-700">{catLabel}</span>
                  {e.description && (
                    <span className="text-slate-400 font-normal truncate max-w-[180px]">
                      — {e.description}
                    </span>
                  )}
                </div>

                {/* Bottom Metadata */}
                <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                  <div className="flex items-center gap-2">
                    {e.classification_confidence != null && (
                      <span>
                        Confidence{' '}
                        <strong className="text-slate-700 mono">
                          {Math.round(e.classification_confidence * 100)}%
                        </strong>
                      </span>
                    )}
                    {e.verification_status && (
                      <span className="flex items-center gap-1 text-slate-600 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        {e.verification_status}
                      </span>
                    )}
                  </div>

                  <span className="mono text-slate-400 group-hover:text-brand-blue-600 font-medium transition-colors">
                    {ago(e.event_timestamp)} ago →
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
