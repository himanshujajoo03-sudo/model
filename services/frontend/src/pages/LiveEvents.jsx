import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import useLiveEventsStore from '../stores/liveEventsStore'
import useLayoutStore from '../stores/layoutStore'
import Sidebar from '../components/command-center/Sidebar'
import Header from '../components/command-center/Header'
import ModelSelect from '../components/common/ModelSelect'
import { ACTIVE_CITIES } from '../constants/cities'
import SelectDropdown from '../components/common/SelectDropdown'
import { WeatherPhenomenonSymbol, VerifiedShield, UnderReviewGlass, AlertTriangle } from '../components/common/Symbols'
import { CityCrest, SourceChannelLogo } from '../components/common/BrandLogos'
import { playNotificationChime } from '../utils/audioAlerts'

const CAT_LABELS = {
  heavy_rainfall: 'Heavy Rain',
  rainfall: 'Rainfall',
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

const SEVERITY_BADGE = {
  low: 'bg-slate-100 text-slate-700 border-slate-200',
  moderate: 'bg-sky-50 text-sky-700 border-sky-200',
  high: 'bg-amber-50 text-amber-800 border-amber-200',
  extreme: 'bg-rose-50 text-rose-700 border-rose-200',
  critical: 'bg-rose-50 text-rose-700 border-rose-200',
}

const SEV_DOT = {
  low: 'bg-slate-400',
  moderate: 'bg-sky-500',
  high: 'bg-amber-500',
  extreme: 'bg-rose-500',
  critical: 'bg-rose-600',
}

const VER_STYLE = {
  verified: { dot: 'bg-emerald-500', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Verified' },
  pending: { dot: 'bg-amber-500', text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Under Review' },
  rejected: { dot: 'bg-rose-500', text: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200', label: 'Rejected' },
  suspicious: { dot: 'bg-orange-500', text: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200', label: 'Suspicious' },
  duplicate: { dot: 'bg-slate-400', text: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200', label: 'Duplicate' },
}

const CATEGORIES = [
  { value: '', label: 'All Event Types', icon: '🌐' },
  { value: 'heavy_rainfall', label: 'Heavy Rain', icon: '🌧️', subtitle: 'Monsoon deluge' },
  { value: 'rainfall', label: 'Rainfall', icon: '🌦️', subtitle: 'Precipitation' },
  { value: 'flood', label: 'Flood', icon: '🌊', subtitle: 'Urban inundation' },
  { value: 'heatwave', label: 'Heatwave', icon: '🔥', subtitle: 'Thermal anomaly' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: '⛈️', subtitle: 'Lightning & squall' },
  { value: 'strong_wind', label: 'Strong Wind', icon: '💨', subtitle: 'Gale force' },
  { value: 'cyclone', label: 'Cyclone', icon: '🌀', subtitle: 'Vortex system' },
  { value: 'fog', label: 'Dense Fog', icon: '🌫️', subtitle: 'Low visibility' },
  { value: 'dust_storm', label: 'Dust Storm', icon: '🌪️', subtitle: 'Particulate front' },
]

const SEVERITIES = [
  { value: '', label: 'All Severities', icon: '⚡' },
  { value: 'low', label: 'Low', icon: '●', status: 'Low', statusColor: 'bg-slate-100 text-slate-700' },
  { value: 'moderate', label: 'Moderate', icon: '●', status: 'Moderate', statusColor: 'bg-blue-50 text-blue-700' },
  { value: 'high', label: 'High', icon: '●', status: 'High', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'extreme', label: 'Extreme / Critical', icon: '●', status: 'Critical', statusColor: 'bg-rose-50 text-rose-700' },
]

const VERIFICATIONS = [
  { value: '', label: 'All Statuses', icon: '🛡️' },
  { value: 'verified', label: 'Verified', icon: '✓', status: 'Verified', statusColor: 'bg-emerald-50 text-emerald-700' },
  { value: 'pending', label: 'Under Review', icon: '⏳', status: 'Pending', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'rejected', label: 'Rejected', icon: '✕', status: 'Rejected', statusColor: 'bg-rose-50 text-rose-700' },
  { value: 'suspicious', label: 'Suspicious', icon: '⚠️', status: 'Flagged', statusColor: 'bg-rose-50 text-rose-700' },
]

const SORT_OPTIONS = [
  { value: 0, field: 'event_timestamp', order: 'desc', label: 'Newest First', icon: '🕒', subtitle: 'Chronological desc' },
  { value: 1, field: 'event_timestamp', order: 'asc', label: 'Oldest First', icon: '⏳', subtitle: 'Chronological asc' },
  { value: 2, field: 'severity', order: 'desc', label: 'Highest Severity', icon: '🔥', subtitle: 'Critical first' },
  { value: 3, field: 'classification_confidence', order: 'desc', label: 'Highest AI Confidence', icon: '🎯', subtitle: 'Model certainty' },
  { value: 4, field: 'credibility_score', order: 'desc', label: 'Highest Credibility', icon: '🛡️', subtitle: 'Sensor trust' },
]

const SOURCE_OPTIONS = [
  { value: '', label: 'All Ingestion Sources', icon: '📡' },
  { value: 'weather_api', label: 'Weather API', icon: '🌐', subtitle: 'Official feeds' },
  { value: 'synthetic', label: 'Synthetic Doppler', icon: '🛰️', subtitle: 'Radar fusion' },
  { value: 'citizen', label: 'Citizen Reports', icon: '👥', subtitle: 'Ground truth' },
]

function ago(iso) {
  if (!iso) return '—'
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function fmtPct(v) {
  if (v === null || v === undefined) return '—'
  return `${Math.round(v * 100)}%`
}

function formatLatency(ms) {
  if (ms === null || ms === undefined || isNaN(ms)) return null
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export default function LiveEvents() {
  const navigate = useNavigate()
  const {
    events, total, totalPages, page, pageSize,
    filters, sortBy, sortOrder, search,
    loading, error, lastUpdated, isLiveStreaming,
    setPage, setSortBy, setSortOrder,
    setSearch, setFilters, clearFilters,
    startPolling, stopPolling,
  } = useLiveEventsStore()

  const openUpcomingModal = useLayoutStore((s) => s.openUpcomingModal)
  const [previewEvent, setPreviewEvent] = useState(null)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  // One-Click CSV Export Generator
  const exportToCSV = () => {
    if (!displayEvents.length) return
    const headers = [
      'Event ID',
      'City',
      'State',
      'District',
      'Category',
      'Severity',
      'AI Confidence',
      'Credibility Score',
      'Verification Status',
      'Source',
      'Latitude',
      'Longitude',
      'Timestamp',
    ]
    const rows = displayEvents.map((e) => [
      `"${e.event_id || ''}"`,
      `"${e.city || ''}"`,
      `"${e.state || ''}"`,
      `"${e.district || ''}"`,
      `"${e.event_category || ''}"`,
      `"${e.severity || ''}"`,
      `"${Math.round((e.classification_confidence || 0) * 100)}%"`,
      `"${Math.round((e.credibility_score || 0) * 100)}%"`,
      `"${e.verification_status || ''}"`,
      `"${e.source_name || ''}"`,
      `"${e.latitude || ''}"`,
      `"${e.longitude || ''}"`,
      `"${e.event_timestamp || e.created_at || ''}"`,
    ])

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `meteorological_telemetry_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    playNotificationChime()
  }

  // Client-side search filter
  const displayEvents = useMemo(() => {
    if (!search.trim()) return events
    const q = search.toLowerCase()
    return events.filter((e) =>
      (e.city || '').toLowerCase().includes(q) ||
      (e.state || '').toLowerCase().includes(q) ||
      (e.event_category || '').toLowerCase().includes(q) ||
      (e.classified_category || '').toLowerCase().includes(q) ||
      (e.description || '').toLowerCase().includes(q) ||
      (e.source_name || '').toLowerCase().includes(q) ||
      (e.event_id || '').toLowerCase().includes(q) ||
      (q.includes('reclass') && e.classified_category && e.classified_category !== e.event_category)
    )
  }, [events, search])

  const activeFilterCount = Object.values(filters).filter(Boolean).length
  const currentSortIdx = Math.max(0, SORT_OPTIONS.findIndex((s) => s.field === sortBy && s.order === sortOrder))

  const avgLatencyText = useMemo(() => {
    const eventsWithLatency = displayEvents.filter(
      (e) => typeof e.latency_ms === 'number' && !isNaN(e.latency_ms)
    )
    if (!eventsWithLatency.length) return null
    const sum = eventsWithLatency.reduce((acc, e) => acc + e.latency_ms, 0)
    const avg = sum / eventsWithLatency.length
    return formatLatency(avg)
  }, [displayEvents])

  const changeSort = (idx) => {
    const opt = SORT_OPTIONS[idx]
    if (opt) {
      setSortBy(opt.field)
      setSortOrder(opt.order)
    }
  }

  return (
    <div className="flex min-h-screen bg-slate-50/70">
      {/* Unified Sidebar */}
      <Sidebar />

      {/* Main Container */}
      <div className="flex flex-col flex-1 min-w-0 bg-slate-50/70">
        <Header />

        <div className="flex-1 px-4 lg:px-6 py-4 flex flex-col gap-4 bg-slate-50/70">
          {/* Header row */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 flex-shrink-0">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                  Live Event Telemetry
                </h1>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {total.toLocaleString()} Total Events
                </span>
                <span
                  className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 shadow-2xs"
                  title="Average end-to-end processing latency across visible events (db_written_at - event_timestamp)"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                  <span>Avg processing: {avgLatencyText || 'N/A'}</span>
                </span>
                {isLiveStreaming ? (
                  <span
                    className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 border border-emerald-500/30 shadow-xs"
                    title="Real-time Server-Sent Events stream active"
                  >
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    LIVE SSE
                  </span>
                ) : (
                  <span
                    className="inline-flex items-center gap-1.5 text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200"
                    title="Polling fallback active"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400"></span>
                    POLLING
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Continuous atmospheric intelligence streaming across Mumbai, Nagpur & Nashik
              </p>
            </div>

            {/* Freshness, Filter Indicator & Export Actions */}
            <div className="flex flex-wrap items-center gap-2.5 text-xs">
              {filters.city && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-brand-blue-50 border border-brand-blue-200 rounded-lg text-brand-blue-700 font-semibold">
                  <span>Filtered: {filters.city}</span>
                  <button
                    onClick={() => setFilters({ city: null })}
                    className="hover:text-brand-blue-900 ml-1"
                  >
                    ✕
                  </button>
                </div>
              )}
              {lastUpdated && (
                <span className="text-slate-400 font-mono text-[11px] hidden md:inline">
                  Refreshed {ago(lastUpdated)}
                </span>
              )}

              {/* One-Click CSV Export Button */}
              <button
                type="button"
                onClick={exportToCSV}
                className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-xs"
                title="Download CSV of current table records"
              >
                <span>📥</span>
                <span>Export CSV ({displayEvents.length})</span>
              </button>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3.5 flex-shrink-0 shadow-xs">
            {/* Top row: Search + City ModelSelect + Sort */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
              {/* Search */}
              <div className="md:col-span-5 relative">
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search events, descriptions, hashes, cities..."
                  className="w-full h-9 pl-9 pr-8 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-brand-blue-500 focus:ring-2 focus:ring-brand-blue-500/10 shadow-xs"
                />
                <span className="absolute left-3 top-2.5 text-slate-400 text-xs">🔍</span>
                {search && (
                  <button
                    onClick={() => setSearch('')}
                    className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-slate-700"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* City Selection with Supermodel dropdown */}
              <div className="md:col-span-4">
                <ModelSelect
                  value={filters.city || ''}
                  onChange={(val) => setFilters({ city: val || null })}
                  onSelectUpcoming={openUpcomingModal}
                />
              </div>

              {/* Sort Dropdown with Universal SaaS Component */}
              <div className="md:col-span-3">
                <SelectDropdown
                  options={SORT_OPTIONS}
                  value={currentSortIdx >= 0 ? currentSortIdx : 0}
                  onChange={(val) => changeSort(Number(val))}
                  placeholder="Sort by..."
                />
              </div>
            </div>

            {/* Bottom row: Category, Severity, Status, Source filters */}
            <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-200/70">
              {/* Category */}
              <div className="w-48">
                <SelectDropdown
                  options={CATEGORIES}
                  value={filters.category || ''}
                  onChange={(val) => setFilters({ category: val || null })}
                  placeholder="All Categories"
                  compact={true}
                  searchable={true}
                />
              </div>

              {/* Severity */}
              <div className="w-44">
                <SelectDropdown
                  options={SEVERITIES}
                  value={filters.severity || ''}
                  onChange={(val) => setFilters({ severity: val || null })}
                  placeholder="All Severities"
                  compact={true}
                />
              </div>

              {/* Verification */}
              <div className="w-44">
                <SelectDropdown
                  options={VERIFICATIONS}
                  value={filters.verification_status || ''}
                  onChange={(val) => setFilters({ verification_status: val || null })}
                  placeholder="All Statuses"
                  compact={true}
                />
              </div>

              {/* Source */}
              <div className="w-48">
                <SelectDropdown
                  options={SOURCE_OPTIONS}
                  value={filters.source_type || ''}
                  onChange={(val) => setFilters({ source_type: val || null })}
                  placeholder="All Sources"
                  compact={true}
                />
              </div>

              {activeFilterCount > 0 && (
                <button
                  onClick={clearFilters}
                  className="h-8 px-3 text-xs text-rose-600 hover:text-rose-700 font-semibold bg-rose-50 border border-rose-200 rounded-lg shadow-xs transition-colors"
                >
                  Reset ({activeFilterCount})
                </button>
              )}

              <div className="ml-auto text-xs text-slate-400 font-medium">
                {search ? `${displayEvents.length} matching / ` : ''}Page {page} of {Math.max(totalPages, 1)}
              </div>
            </div>
          </div>

          {/* Events Data Table */}
          <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden flex flex-col flex-1">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="px-4 py-3 w-[24%]">Weather Phenomenon</th>
                    <th className="px-4 py-3 w-[18%]">Location / Hub</th>
                    <th className="px-4 py-3 w-[12%]">Severity</th>
                    <th className="px-4 py-3 w-[12%]">AI Confidence</th>
                    <th className="px-4 py-3 w-[12%]">Credibility</th>
                    <th className="px-4 py-3 w-[14%]">Verification</th>
                    <th className="px-4 py-3 w-[8%] text-right">Inspect</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {loading && events.length === 0 ? (
                    Array.from({ length: 6 }).map((_, i) => (
                      <tr key={i} className="animate-pulse">
                        <td colSpan={7} className="px-4 py-4">
                          <div className="h-4 bg-slate-100 rounded w-3/4 mb-2" />
                          <div className="h-3 bg-slate-50 rounded w-1/2" />
                        </td>
                      </tr>
                    ))
                  ) : displayEvents.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-16 text-center">
                        <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 text-xl font-bold">
                          🌧️
                        </div>
                        <h3 className="text-sm font-bold text-slate-800 mb-1">
                          No Events Found
                        </h3>
                        <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
                          {activeFilterCount > 0 || search
                            ? 'No weather events match your currently active filters or search terms.'
                            : 'No canonical weather events are currently active for this region.'}
                        </p>
                        {(activeFilterCount > 0 || search) && (
                          <button
                            onClick={() => { clearFilters(); setSearch('') }}
                            className="btn-secondary text-xs"
                          >
                            Clear Filters & Search
                          </button>
                        )}
                      </td>
                    </tr>
                  ) : (
                    displayEvents.map((evt) => {
                      const vs = VER_STYLE[evt.verification_status] || VER_STYLE.pending
                      const isTargetCity = ACTIVE_CITIES.some((c) => c.name.toLowerCase() === (evt.city || '').toLowerCase())

                      return (
                        <tr
                          key={evt.event_id}
                          onClick={() => navigate(`/events/${evt.event_id}`)}
                          className="hover:bg-slate-50/70 cursor-pointer transition-colors group"
                        >
                          {/* Phenomenon */}
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-2.5">
                              <div className="w-7 h-7 rounded-lg bg-slate-50 border border-slate-200 p-1 flex items-center justify-center flex-shrink-0 shadow-2xs">
                                <WeatherPhenomenonSymbol category={evt.event_category} size={18} />
                              </div>
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition-colors block truncate">
                                    {CAT_LABELS[evt.event_category] || evt.event_category}
                                  </span>
                                  {evt.classified_category && evt.classified_category !== evt.event_category && (
                                    <span
                                      className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200"
                                      title={`Original category was "${evt.event_category}", reclassified as "${evt.classified_category}" by AI classifier`}
                                    >
                                      <span>Reclassified:</span>
                                      <span className="font-mono">{evt.event_category} → {evt.classified_category}</span>
                                    </span>
                                  )}
                                </div>
                                <span className="text-[10px] text-slate-400 font-mono block">
                                  ID: {evt.event_id?.slice(0, 8)}… · {ago(evt.event_timestamp || evt.created_at)}
                                  {evt.latency_ms != null && (
                                    <span
                                      className="ml-1.5 font-sans font-semibold text-blue-600 bg-blue-50/80 px-1.5 py-0.5 rounded border border-blue-200/60 inline-flex items-center gap-0.5"
                                      title="End-to-end processing latency (db_written_at - event_timestamp)"
                                    >
                                      ⚡ processed in {formatLatency(evt.latency_ms)}
                                    </span>
                                  )}
                                </span>
                              </div>
                            </div>
                          </td>

                          {/* Location */}
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-2">
                              <CityCrest city={evt.city} size="sm" />
                              <div>
                                <div className="flex items-center gap-1.5">
                                  <span className="text-xs font-bold text-slate-800">
                                    {evt.city || evt.district || 'Location Unavailable'}
                                  </span>
                                  {isTargetCity && (
                                    <span className="text-[9px] font-extrabold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                                      MVP
                                    </span>
                                  )}
                                </div>
                                <div className="text-[10px] text-slate-400 font-medium">
                                  {evt.state ? `${evt.state}${evt.district && evt.district !== evt.city ? ` · ${evt.district}` : ''}` : (evt.district || evt.country || 'India')}
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Severity */}
                          <td className="px-4 py-3.5">
                            <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-lg border shadow-2xs ${SEVERITY_BADGE[evt.severity] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                              <span className={`w-2 h-2 rounded-full ${SEV_DOT[evt.severity] || 'bg-slate-400'}`} />
                              <span className="capitalize">{evt.severity || 'Normal'}</span>
                            </span>
                          </td>

                          {/* Confidence */}
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-2">
                              <div className="w-14 h-2 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-blue-600 rounded-full"
                                  style={{ width: `${Math.round((evt.classification_confidence || 0) * 100)}%` }}
                                />
                              </div>
                              <span className="text-xs font-mono font-bold text-slate-700">
                                {fmtPct(evt.classification_confidence)}
                              </span>
                            </div>
                          </td>

                          {/* Credibility */}
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-2">
                              <div className="w-14 h-2 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-emerald-500 rounded-full"
                                  style={{ width: `${Math.round((evt.credibility_score || 0) * 100)}%` }}
                                />
                              </div>
                              <span className="text-xs font-mono font-bold text-slate-700">
                                {fmtPct(evt.credibility_score)}
                              </span>
                            </div>
                          </td>

                          {/* Verification */}
                          <td className="px-4 py-3.5">
                            <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-lg border shadow-2xs ${vs.bg} ${vs.text} ${vs.border}`}>
                              {evt.verification_status === 'verified' ? (
                                <VerifiedShield size={14} />
                              ) : evt.verification_status === 'pending' ? (
                                <UnderReviewGlass size={14} />
                              ) : (
                                <AlertTriangle size={14} />
                              )}
                              <span>{vs.label}</span>
                            </span>
                          </td>

                          {/* Action Buttons */}
                          <td className="px-4 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setPreviewEvent(evt)
                                }}
                                className="btn-secondary text-xs py-1 px-2.5 shadow-2xs font-semibold hover:border-blue-400 hover:text-blue-700"
                                title="Quick Preview Event Summary"
                              >
                                👁️ Preview
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  navigate(`/events/${evt.event_id}`)
                                }}
                                className="btn-primary text-xs py-1 px-2.5 shadow-2xs font-bold"
                                title="Open Full Event Details"
                              >
                                Event Details →
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination footer */}
            {totalPages > 1 && (
              <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between text-xs mt-auto">
                <span className="text-slate-500 font-medium">
                  Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total.toLocaleString()} events
                </span>

                <div className="flex items-center gap-1">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                    className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed font-medium shadow-xs"
                  >
                    Previous
                  </button>

                  {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
                    let pageNum = i + 1
                    if (totalPages > 5) {
                      if (page > 3 && page < totalPages - 2) {
                        pageNum = page - 2 + i
                      } else if (page >= totalPages - 2) {
                        pageNum = totalPages - 4 + i
                      }
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => setPage(pageNum)}
                        className={`w-7 h-7 rounded-lg text-xs font-semibold transition-colors ${
                          pageNum === page
                            ? 'bg-brand-blue-600 text-white shadow-xs'
                            : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    )
                  })}

                  <button
                    disabled={page >= totalPages}
                    onClick={() => setPage(page + 1)}
                    className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed font-medium shadow-xs"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Preview Slide-Over Drawer */}
      {previewEvent && (
        <div
          className="fixed inset-0 z-[9995] bg-slate-900/35 backdrop-blur-2xs flex justify-end animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setPreviewEvent(null)
          }}
        >
          <div className="w-full sm:w-[480px] bg-white h-full shadow-2xl border-l border-slate-200 flex flex-col animate-in slide-in-from-right duration-200 overflow-hidden">
            {/* Drawer Header */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white flex-shrink-0">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center flex-shrink-0 shadow-2xs">
                  <WeatherPhenomenonSymbol category={previewEvent.event_category} size={22} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-sm font-bold text-slate-900 truncate">
                      {CAT_LABELS[previewEvent.event_category] || previewEvent.event_category}
                    </h2>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                      #{previewEvent.event_id?.slice(0, 8)}
                    </span>
                    {previewEvent.classified_category && previewEvent.classified_category !== previewEvent.event_category && (
                      <span
                        className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200"
                        title={`Original category was "${previewEvent.event_category}", reclassified as "${previewEvent.classified_category}" by AI classifier`}
                      >
                        <span>Reclassified:</span>
                        <span className="font-mono">{previewEvent.event_category} → {previewEvent.classified_category}</span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 font-medium truncate">
                    {previewEvent.city || previewEvent.district || 'Location Unavailable'} · {previewEvent.state || previewEvent.country || 'India'}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setPreviewEvent(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin bg-white">
              {/* Telemetry Metrics Grid */}
              <div className="grid grid-cols-2 gap-2.5">
                <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Severity Level
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className={`w-2.5 h-2.5 rounded-full ${SEV_DOT[previewEvent.severity] || 'bg-slate-400'}`} />
                    <span className="text-xs font-bold capitalize text-slate-800">
                      {previewEvent.severity || 'Moderate'}
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Verification State
                  </span>
                  <div className="flex items-center gap-1.5">
                    {previewEvent.verification_status === 'verified' ? (
                      <VerifiedShield size={14} />
                    ) : previewEvent.verification_status === 'pending' ? (
                      <UnderReviewGlass size={14} />
                    ) : (
                      <AlertTriangle size={14} />
                    )}
                    <span className="text-xs font-bold capitalize text-slate-800">
                      {previewEvent.verification_status || 'Under Review'}
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    AI Model Confidence
                  </span>
                  <div className="text-sm font-bold font-mono text-blue-600">
                    {fmtPct(previewEvent.classification_confidence)}
                  </div>
                  {previewEvent.classified_category && previewEvent.classified_category !== previewEvent.event_category && (
                    <span className="text-[10px] text-amber-700 font-semibold block mt-1">
                      Reclassified as {CAT_LABELS[previewEvent.classified_category] || previewEvent.classified_category}
                    </span>
                  )}
                </div>

                <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Sensor Credibility
                  </span>
                  <div className="text-sm font-bold font-mono text-emerald-600">
                    {fmtPct(previewEvent.credibility_score)}
                  </div>
                </div>

                {previewEvent.latency_ms != null && (
                  <div className="col-span-2 p-3 rounded-xl border border-blue-200 bg-blue-50/40">
                    <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider block mb-1">
                      End-to-End Processing Latency
                    </span>
                    <div className="text-sm font-bold font-mono text-blue-700 flex items-center gap-1.5">
                      <span>⚡</span>
                      <span>processed in {formatLatency(previewEvent.latency_ms)}</span>
                      <span className="text-[10px] text-slate-400 font-sans font-normal ml-auto">
                        (db_written_at - event_timestamp)
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Geographic Coordinates Card */}
              <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider">
                    Geospatial Coordinates
                  </span>
                  <CityCrest city={previewEvent.city} size="xs" />
                </div>
                <div className="font-mono text-xs font-semibold text-slate-800 bg-slate-50 p-2 rounded-lg border border-slate-200/80 flex items-center justify-between">
                  <span>Lat: {Number(previewEvent.latitude || 19.076).toFixed(4)}° N</span>
                  <span>Lon: {Number(previewEvent.longitude || 72.8777).toFixed(4)}° E</span>
                </div>
              </div>

              {/* Ingestion Source */}
              <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs">
                <span className="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
                  Telemetry Channel
                </span>
                <div className="flex items-center gap-2.5">
                  <SourceChannelLogo source={previewEvent.source_name || 'radar'} size="sm" />
                  <div>
                    <span className="text-xs font-bold text-slate-800 block">
                      {previewEvent.source_name || 'DWR Doppler Ingestion'}
                    </span>
                    <span className="text-[10.5px] text-slate-400">
                      Timestamp: {new Date(previewEvent.event_timestamp || previewEvent.created_at || Date.now()).toLocaleString('en-IN')}
                    </span>
                  </div>
                </div>
              </div>

              {/* Raw Meteorological Description / Notes */}
              <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs">
                <span className="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                  Observation Synopsis
                </span>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {previewEvent.description ||
                    `Convective weather signal detected in ${previewEvent.city} sector with high spatial correlation across Doppler Radar & in-situ automated telemetry.`}
                </p>
              </div>
            </div>

            {/* Drawer Footer Actions */}
            <div className="p-4 border-t border-slate-200 bg-slate-50/70 flex items-center justify-between gap-3 flex-shrink-0">
              <button
                type="button"
                onClick={() => {
                  navigate(`/verification`)
                  setPreviewEvent(null)
                }}
                className="btn-secondary text-xs py-2 px-3 flex-1 justify-center font-bold"
              >
                <span>🛡️ Verify Queue</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  navigate(`/events/${previewEvent.event_id}`)
                  setPreviewEvent(null)
                }}
                className="btn-primary text-xs py-2 px-3 flex-1 justify-center font-bold"
              >
                <span>Full Investigation →</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
