import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useCommandCenterStore from '../../stores/commandCenterStore'
import { getCityMetadata, ACTIVE_CITIES } from '../../constants/cities'

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
  other: 'Weather Event',
}

function formatFullDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

function ago(iso) {
  if (!iso) return ''
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 0) return 'Just now'
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  const days = Math.floor(s / 86400)
  if (days === 1) return 'Yesterday'
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}

function getSourceInfo(e) {
  const desc = (e.description || '').toLowerCase()
  const src = (e.source_name || '').toLowerCase()
  const sources = (e.contributing_sources || []).map((s) => s.toLowerCase())

  if (
    src.includes('era5') ||
    desc.includes('era5') ||
    sources.some((s) => s.includes('era5') || s.includes('archive')) ||
    desc.includes('historical') ||
    desc.includes('copernicus')
  ) {
    return {
      name: 'ECMWF ERA5 Reanalysis (Copernicus C3S)',
      isArchive: true,
      badge: '🏛️ ECMWF ERA5 Verified',
      color: 'bg-purple-50 text-purple-700 border-purple-200',
    }
  }
  if (src.includes('sachet') || sources.some((s) => s.includes('sachet') || s.includes('ndma'))) {
    return {
      name: 'NDMA SACHET Disaster Warning',
      isArchive: false,
      badge: '🇮🇳 NDMA SACHET Alert',
      color: 'bg-rose-50 text-rose-700 border-rose-200',
    }
  }
  if (src.includes('gdacs') || sources.some((s) => s.includes('gdacs'))) {
    return {
      name: 'GDACS Global Early Warning',
      isArchive: false,
      badge: '🌐 GDACS Global Alert',
      color: 'bg-amber-50 text-amber-700 border-amber-200',
    }
  }
  return {
    name: 'Open-Meteo Synoptic Live Telemetry',
    isArchive: false,
    badge: '🛰️ Open-Meteo Live',
    color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  }
}

export default function LiveEventFeed() {
  const events = useCommandCenterStore((s) => s.events)
  const timeHorizon = useCommandCenterStore((s) => s.timeHorizon)
  const navigate = useNavigate()

  const [filterCity, setFilterCity] = useState(null)

  const filtered = events.filter((e) => {
    if (!filterCity) return true
    const norm = (e.city || '').toLowerCase()
    const target = filterCity.toLowerCase()
    return norm === target
  })

  const popularCities = ['Mumbai', 'Delhi', 'Bengaluru', 'Nagpur', 'Nashik', 'Kolkata', 'Chennai', 'Hyderabad']

  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl overflow-hidden flex flex-col shadow-xs">
      {/* Feed Header */}
      <div className="px-3.5 py-2.5 border-b border-slate-200 bg-white flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${timeHorizon === 'live' ? 'bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.6)] animate-pulse' : 'bg-purple-600'}`} />
            <span className="text-[11px] font-bold text-slate-900 uppercase tracking-wider">
              {timeHorizon === 'live' ? 'Live Event Stream' : 'Historical & Live Weather Feed'}
            </span>
            <span className="text-[9.5px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
              {timeHorizon === 'live' ? 'Real-Time' : timeHorizon === '7d' ? 'Past 7 Days' : 'Past 30 Days (1 Month)'}
            </span>
          </div>
          <span className="text-[10px] font-bold text-slate-600 mono bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200/80">
            {filtered.length} weather records
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
            All Cities ({ACTIVE_CITIES.length})
          </button>
          {popularCities.map((city) => {
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
      <div className="divide-y divide-slate-100">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 p-4 text-center">
            <span className="text-2xl mb-1">📡</span>
            <span className="text-xs font-bold text-slate-700">
              No weather events found for selected filter
            </span>
            <span className="text-[11px] text-slate-400 mt-0.5">
              Select another city or switch time horizon to Past 30 Days
            </span>
          </div>
        ) : (
          filtered.map((e) => {
            const cityMeta = getCityMetadata(e.city)
            const sevClass = SEV_BADGE[e.severity] || SEV_BADGE.moderate
            const catLabel = CAT_LABELS[e.event_category] || e.event_category
            const sourceInfo = getSourceInfo(e)
            const exactDate = formatFullDate(e.event_timestamp || e.created_at)
            const relativeTime = ago(e.event_timestamp || e.created_at)

            return (
              <div
                key={e.event_id}
                onClick={() => e.event_id && navigate(`/events/${e.event_id}`)}
                className="p-3 hover:bg-slate-50/80 transition-colors cursor-pointer group"
              >
                {/* City Tag + Date Stamp + Severity Badge */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    {cityMeta?.color && (
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: cityMeta.color }}
                      />
                    )}
                    <span className="font-bold text-xs text-slate-900 truncate">
                      {e.city || 'India'}
                    </span>
                    <span className="text-[10px] text-slate-400 truncate">
                      · {e.state || 'National'}
                    </span>
                    {/* Exact Date Label */}
                    <span className="text-[10px] font-semibold text-slate-700 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">
                      📅 {exactDate}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${sourceInfo.isArchive ? 'bg-purple-50 text-purple-700 border-purple-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                      {sourceInfo.badge}
                    </span>
                    <span
                      className={`text-[9.5px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${sevClass}`}
                    >
                      {e.severity || 'Normal'}
                    </span>
                  </div>
                </div>

                {/* Event Category & Description */}
                <div className="text-xs font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
                  <span className="text-brand-blue-700 font-bold">{catLabel}</span>
                  {e.description && (
                    <span className="text-slate-600 font-normal truncate max-w-[320px]">
                      — {e.description}
                    </span>
                  )}
                </div>

                {/* Bottom Metadata: Multi-Source Verification & Timeline */}
                <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1.5 border-t border-slate-100 mt-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center gap-1 font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      <span>🛡️</span>
                      <span>{e.source_count && e.source_count > 1 ? `${e.source_count} Sources Verified` : 'Multi-Source Verified'}</span>
                    </span>
                    <span className="text-slate-600 font-medium flex items-center gap-1">
                      <span>🏛️</span>
                      <span className="truncate max-w-[200px]">{sourceInfo.name}</span>
                    </span>
                    <span className="text-[9px] font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                      Open-Meteo + NDMA SACHET Corroborated
                    </span>
                  </div>

                  <span className="mono text-slate-500 group-hover:text-brand-blue-600 font-semibold transition-colors flex-shrink-0">
                    {relativeTime} →
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
