import React, { useEffect, useMemo, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip } from 'react-leaflet'
import useEmergingStore from '../stores/emergingStore'
import Sidebar from '../components/command-center/Sidebar'
import Header from '../components/command-center/Header'
import SelectDropdown from '../components/common/SelectDropdown'

/* ═══════════════════════════════════════════════════════════════
   Constants
   ═══════════════════════════════════════════════════════════════ */

const CAT = {
  heavy_rainfall: 'Heavy Rain', rainfall: 'Rain', flood: 'Flood',
  heatwave: 'Heatwave', thunderstorm: 'Thunderstorm', lightning: 'Lightning',
  strong_wind: 'Strong Wind', hailstorm: 'Hail', dust_storm: 'Dust Storm',
  cyclone: 'Cyclone', fog: 'Fog',
}
const CAT_COLOR = {
  heavy_rainfall: '#0284C7', rainfall: '#38BDF8', flood: '#2563EB',
  heatwave: '#F59E0B', thunderstorm: '#DC2626', lightning: '#EAB308',
  strong_wind: '#0D9488', hailstorm: '#64748B', dust_storm: '#D97706',
  cyclone: '#E11D48', fog: '#94A3B8',
}
const SEV_COLOR = {
  low: '#10B981', moderate: '#0284C7', high: '#F59E0B',
  extreme: '#DC2626', critical: '#991B1B',
}
const SEV_SIZE = { low: 7, moderate: 9, high: 13, extreme: 17, critical: 21 }
const SEV_LABEL = { low: 'Low', moderate: 'Moderate', high: 'High', extreme: 'Extreme', critical: 'Critical' }
const VER_COLOR = {
  verified: '#059669', pending: '#D97706', needs_review: '#EA580C',
  suspicious: '#DC2626', duplicate: '#64748B',
}
const VER_LABEL = {
  verified: 'Verified', pending: 'Pending', needs_review: 'Needs Review',
  suspicious: 'Suspicious', duplicate: 'Duplicate',
}

const TIME_RANGES = [
  { value: '1h', label: '1h' }, { value: '6h', label: '6h' },
  { value: '24h', label: '24h' }, { value: '7d', label: '7d' },
  { value: 'all', label: 'All' },
]

const CATEGORIES = [
  { value: '', label: 'All Categories', icon: '⚡' },
  { value: 'heavy_rainfall', label: 'Heavy Rain', icon: '🌧️' },
  { value: 'rainfall', label: 'Rain', icon: '🌦️' },
  { value: 'flood', label: 'Flood', icon: '🌊' },
  { value: 'heatwave', label: 'Heatwave', icon: '☀️' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: '⛈️' },
  { value: 'strong_wind', label: 'Strong Wind', icon: '💨' },
  { value: 'cyclone', label: 'Cyclone', icon: '🌀' },
  { value: 'fog', label: 'Fog', icon: '🌫️' },
  { value: 'dust_storm', label: 'Dust Storm', icon: '🏜️' },
]

const SEVERITIES = [
  { value: '', label: 'All Severities', icon: '📊' },
  { value: 'low', label: 'Low', icon: '🟢', subtitle: 'Normal monitoring' },
  { value: 'moderate', label: 'Moderate', icon: '🟡', subtitle: 'Elevated attention' },
  { value: 'high', label: 'High', icon: '🟠', subtitle: 'Urgent response' },
  { value: 'extreme', label: 'Extreme', icon: '🔴', subtitle: 'Critical hazard' },
]

const VERIFICATIONS = [
  { value: '', label: 'All Status', icon: '🏷️' },
  { value: 'verified', label: 'Verified', icon: '✅', status: 'ACTIVE', statusColor: 'emerald' },
  { value: 'pending', label: 'Pending', icon: '⏳', status: 'IN REVIEW', statusColor: 'amber' },
  { value: 'needs_review', label: 'Needs Review', icon: '⚠️', status: 'ATTENTION', statusColor: 'orange' },
  { value: 'suspicious', label: 'Suspicious', icon: '🚨', status: 'FLAGGED', statusColor: 'red' },
]

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

function fmtPct(v) {
  if (v === null || v === undefined) return '—'
  return `${Math.round(v * 100)}%`
}

function fmtTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

function ago(iso) {
  if (!iso) return ''
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function hoursAgo(iso) {
  if (!iso) return Infinity
  return (Date.now() - new Date(iso).getTime()) / (1000 * 60 * 60)
}

/**
 * ATTENTION PRIORITY — transparent deterministic ranking.
 *
 * Weighting:
 *   severity       40%  (low=0.1, moderate=0.3, high=0.7, extreme/critical=1.0)
 *   recency        25%  (0-24h = 1.0, 24-72h = linear decay, 72h+ = 0.1)
 *   report activity 20% (capped: min(report_count/50, 1.0))
 *   source corroboration 15% (source_count: 1=0.2, 2=0.6, 3+=1.0)
 *
 * Score is clamped to [0, 1].
 * Label: High (>=0.7), Elevated (>=0.5), Moderate (>=0.3), Low (<0.3)
 */
function computeAttentionPriority(event) {
  const sevMap = { low: 0.1, moderate: 0.3, high: 0.7, extreme: 1.0, critical: 1.0 }
  const sev = sevMap[event.severity] || 0.3

  const hours = hoursAgo(event.event_timestamp)
  const recency = hours <= 24 ? 1.0 : hours <= 72 ? Math.max(0.1, 1.0 - (hours - 24) / 48) : 0.1

  const reportAct = Math.min((event.report_count || 1) / 50, 1.0)

  const srcCount = event.source_count || 1
  const corroboration = srcCount >= 3 ? 1.0 : srcCount === 2 ? 0.6 : 0.2

  const score = Math.max(0, Math.min(1,
    sev * 0.40 + recency * 0.25 + reportAct * 0.20 + corroboration * 0.15
  ))

  let label, color
  if (score >= 0.7) { label = 'High'; color = '#B84848' }
  else if (score >= 0.5) { label = 'Elevated'; color = '#B56F20' }
  else if (score >= 0.3) { label = 'Moderate'; color = '#B98220' }
  else { label = 'Low'; color = '#7A8794' }

  return { score, label, color }
}


/* ═══════════════════════════════════════════════════════════════
   Evidence Reasons — only factual statements
   ═══════════════════════════════════════════════════════════════ */

function getEmergenceReasons(event) {
  const reasons = []
  const hours = hoursAgo(event.event_timestamp)

  if (hours <= 1) reasons.push('First observed within the last hour')
  else if (hours <= 6) reasons.push('First observed within the last 6 hours')
  else if (hours <= 24) reasons.push('First observed within the last 24 hours')

  if ((event.report_count || 0) > 1) reasons.push(`${event.report_count} contributing reports`)
  if ((event.source_count || 0) > 1) reasons.push(`${event.source_count} source types corroborating`)

  const sev = event.severity
  if (sev === 'extreme' || sev === 'critical') reasons.push('Extreme severity')
  else if (sev === 'high') reasons.push('High severity')

  if (event.verification_status === 'needs_review') reasons.push('Requires verification review')
  if (event.verification_status === 'suspicious') reasons.push('Flagged as suspicious')

  if (reasons.length === 0) reasons.push('Activity observed within selected time window')

  return reasons
}

/* ═══════════════════════════════════════════════════════════════
   Emerging Map
   ═══════════════════════════════════════════════════════════════ */

function EmergingMap({ events, selectedEvent, onSelectEvent }) {
  const navigate = useNavigate()

  return (
    <div className="h-full bg-white border border-[#D9E0E6] rounded-md overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#D9E0E6] bg-[#F8FAFB] flex-shrink-0">
        <span className="text-[10px] font-semibold tracking-wider text-[#7A8794] uppercase">Situation Map</span>
        <span className="text-[10px] text-[#7A8794]">{events.length} event{events.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="flex-1 relative">
        <MapContainer
          center={[22.5, 82.0]}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
          zoomControl={true}
          attributionControl={false}
        >
          {/* MapTiler Streets Base Tiles */}
          <TileLayer
            url={`https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${import.meta.env.VITE_MAPTILER_API_KEY}`}
            maxZoom={19}
            tileSize={512}
            zoomOffset={-1}
            attribution='&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
          />

          {events.map((event) => {
            if (!event.latitude || !event.longitude) return null
            const priority = computeAttentionPriority(event)
            const isSelected = selectedEvent?.event_id === event.event_id
            const radius = SEV_SIZE[event.severity] || 9

            return (
              <CircleMarker
                key={event.event_id}
                center={[event.latitude, event.longitude]}
                radius={isSelected ? radius + 3 : radius}
                pathOptions={{
                  fillColor: SEV_COLOR[event.severity] || '#477D96',
                  fillOpacity: isSelected ? 0.9 : 0.7,
                  color: isSelected ? '#18232D' : '#FFFFFF',
                  weight: isSelected ? 2.5 : 1.5,
                }}
                eventHandlers={{
                  click: () => onSelectEvent(event),
                }}
              >
                <Tooltip direction="top" offset={[0, -radius]}>
                  <div className="text-[11px]">
                    <div className="font-semibold">{CAT[event.event_category] || event.event_category}</div>
                    <div>{event.city || 'Unknown'}</div>
                    <div className="text-[#7A8794]">{SEV_LABEL[event.severity]}</div>
                  </div>
                </Tooltip>
                <Popup>
                  <div className="min-w-[200px] p-2 text-[11px]">
                    <div className="font-semibold text-[13px] mb-1">
                      {CAT[event.event_category] || event.event_category}
                    </div>
                    <div className="text-[#526170] mb-2">{event.city || 'Unknown'}</div>
                    <div className="space-y-1 mb-2">
                      <div className="flex justify-between"><span className="text-[#7A8794]">Severity</span><span style={{ color: SEV_COLOR[event.severity] }}>{SEV_LABEL[event.severity]}</span></div>
                      <div className="flex justify-between"><span className="text-[#7A8794]">Attention</span><span style={{ color: priority.color }}>{priority.label}</span></div>
                    </div>
                    <button
                      onClick={() => navigate(`/events/${event.event_id}`)}
                      className="text-[#477D96] hover:text-[#3B6FA0] font-medium"
                    >
                      View Event Intelligence →
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>

        {events.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#F3F5F7]/80 z-[1000]">
            <div className="text-center text-[12px] text-[#7A8794]">
              No locations to display for current filters
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Evidence Panel
   ═══════════════════════════════════════════════════════════════ */

function EvidencePanel({ event, onClose }) {
  const navigate = useNavigate()
  if (!event) return null

  const priority = computeAttentionPriority(event)
  const reasons = getEmergenceReasons(event)
  const hours = hoursAgo(event.event_timestamp)

  return (
    <div className="card-white rounded-xl overflow-hidden mb-4 border border-blue-200/80 shadow-md">
      <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-blue-50/50 to-indigo-50/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-slate-800">Situation Detail & Live Evidence</span>
          <span className="badge-live text-[10px]">EVALUATING</span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700 w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors">✕</button>
      </div>

      <div className="p-4 space-y-4">
        {/* Situation */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2.5 h-2.5 rounded-full ring-2 ring-offset-1 ring-blue-300" style={{ background: SEV_COLOR[event.severity] }} />
              <span className="text-base font-bold text-slate-900">
                {CAT[event.event_category] || event.event_category}
              </span>
            </div>
            <div className="text-xs font-medium text-slate-600 flex items-center gap-1.5">
              <span>📍 {event.city || 'Unknown'}{event.state ? `, ${event.state}` : ''}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full border shadow-sm" style={{ color: priority.color, background: `${priority.color}15`, borderColor: `${priority.color}40` }}>
              Priority: {priority.label}
            </span>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full border shadow-sm" style={{ color: VER_COLOR[event.verification_status], background: `${VER_COLOR[event.verification_status]}15`, borderColor: `${VER_COLOR[event.verification_status]}40` }}>
              {VER_LABEL[event.verification_status]}
            </span>
          </div>
        </div>

        {/* Observed Activity */}
        <div className="bg-slate-50/70 p-3 rounded-xl border border-slate-100">
          <div className="text-[10px] font-bold tracking-wider text-slate-500 uppercase mb-2">Observed Activity Telemetry</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white p-2.5 rounded-lg border border-slate-100">
              <div className="text-[10px] text-slate-400 font-medium">First Observed</div>
              <div className="text-xs mono font-bold text-slate-800 mt-0.5">{fmtTime(event.event_timestamp)}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{ago(event.event_timestamp)}</div>
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-slate-100">
              <div className="text-[10px] text-slate-400 font-medium">Corroborating Reports</div>
              <div className="text-base mono font-extrabold text-blue-700 mt-0.5">{event.report_count ?? '—'}</div>
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-slate-100">
              <div className="text-[10px] text-slate-400 font-medium">Distinct Sources</div>
              <div className="text-base mono font-extrabold text-indigo-700 mt-0.5">{event.source_count ?? '—'}</div>
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-slate-100">
              <div className="text-[10px] text-slate-400 font-medium">Detection Age</div>
              <div className="text-base mono font-extrabold text-slate-700 mt-0.5">{hours <= 24 ? `${Math.round(hours)}h` : `${Math.round(hours / 24)}d`}</div>
            </div>
          </div>
        </div>

        {/* Verification */}
        <div className="bg-slate-50/70 p-3 rounded-xl border border-slate-100">
          <div className="text-[10px] font-bold tracking-wider text-slate-500 uppercase mb-2">Verification Quality Metrics</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white p-2.5 rounded-lg border border-slate-100">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-slate-400 font-medium">Classification Confidence</span>
                <span className="text-xs mono font-bold text-blue-600">{fmtPct(event.classification_confidence)}</span>
              </div>
              <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                <div className="bg-gradient-to-r from-blue-500 to-indigo-600 h-full rounded-full" style={{ width: fmtPct(event.classification_confidence) }} />
              </div>
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-slate-100">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-slate-400 font-medium">Credibility Score</span>
                <span className="text-xs mono font-bold text-emerald-600">{fmtPct(event.credibility_score)}</span>
              </div>
              <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                <div className="bg-gradient-to-r from-emerald-400 to-teal-500 h-full rounded-full" style={{ width: fmtPct(event.credibility_score) }} />
              </div>
            </div>
          </div>
        </div>

        {/* Emergence Evidence */}
        <div>
          <div className="text-[10px] font-bold tracking-wider text-slate-500 uppercase mb-1.5">Algorithmic Emergence Triggers</div>
          <div className="space-y-1.5">
            {reasons.map((r, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-slate-700 bg-slate-50 px-3 py-2 rounded-lg border border-slate-100">
                <span className="text-blue-600 font-bold mt-0.5">✦</span>
                <span className="font-medium">{r}</span>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
          <button
            onClick={() => navigate(`/events/${event.event_id}`)}
            className="btn-primary text-xs py-2 px-4 inline-flex items-center gap-2"
          >
            <span>Open Deep Event Intelligence</span>
            <span>→</span>
          </button>
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Main Page
   ═══════════════════════════════════════════════════════════════ */

export default function EmergingEvents() {
  const navigate = useNavigate()
  const {
    events, mapEvents, filters, timeRange, selectedEvent,
    loading, error, lastUpdated,
    setFilters, clearFilters, setTimeRange, setSelectedEvent, clearSelectedEvent,
    startPolling, stopPolling,
  } = useEmergingStore()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  const handleSelectEvent = useCallback((event) => {
    setSelectedEvent(event)
  }, [setSelectedEvent])

  const activeFilterCount = Object.values(filters).filter(Boolean).length + (timeRange !== '24h' ? 1 : 0)

  // ── Rank events by attention priority ──
  const rankedEvents = useMemo(() => {
    if (!events || events.length === 0) return []
    return events
      .map((e) => ({ ...e, _priority: computeAttentionPriority(e) }))
      .sort((a, b) => b._priority.score - a._priority.score)
  }, [events])

  // ── Summary stats ──
  const summary = useMemo(() => {
    if (!rankedEvents.length) return null
    const highPriority = rankedEvents.filter((e) => e._priority.score >= 0.7).length
    const elevated = rankedEvents.filter((e) => e._priority.score >= 0.5 && e._priority.score < 0.7).length
    const cities = new Set(rankedEvents.map((e) => e.city).filter(Boolean))
    return { total: rankedEvents.length, highPriority, elevated, cityCount: cities.size }
  }, [rankedEvents])

  return (
    <div className="flex min-h-screen bg-white">
      {/* Unified Sidebar */}
      <Sidebar />

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        <Header />

        {/* Page content */}
        <div className="flex-1 flex flex-col bg-white">
          {/* Title + Methodology */}
          <div className="px-6 py-4 bg-white border-b border-slate-200 flex-shrink-0">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-xl shadow-sm">
                  ⚡
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-base font-bold text-slate-900">Emerging Weather Situations</h1>
                    <span className="badge-live text-[10px]">REAL-TIME RADAR</span>
                  </div>
                  <p className="text-xs text-slate-500 font-medium">
                    Algorithmic multi-source correlation detecting newly observed or rapidly escalating weather anomalies
                  </p>
                </div>
              </div>
              {lastUpdated && (
                <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-600 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Telemetry live: {ago(lastUpdated)}</span>
                </div>
              )}
            </div>

            {/* Methodology strip */}
            <div className="px-3.5 py-2 bg-blue-50/60 border border-blue-100 rounded-lg text-xs text-blue-800 flex items-center gap-2">
              <span className="text-blue-600 font-bold">ℹ️</span>
              <span><strong>Detection Methodology:</strong> Emerging status is computed deterministically from multi-channel recency, severity weight, corroborating report velocity, and source trust scores.</span>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-2.5 flex-wrap mt-3 pt-2 border-t border-slate-100">
              <div className="flex items-center gap-1 bg-slate-100/90 rounded-xl p-1 border border-slate-200 shadow-sm">
                {TIME_RANGES.map((tr) => (
                  <button
                    key={tr.value}
                    onClick={() => setTimeRange(tr.value)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                      timeRange === tr.value
                        ? 'bg-white text-blue-700 shadow-sm border border-blue-100 font-bold'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                    }`}
                  >{tr.label}</button>
                ))}
              </div>

              <SelectDropdown
                label="Category"
                options={CATEGORIES}
                value={filters.category || ''}
                onChange={(v) => setFilters({ category: v || null })}
                searchable={false}
                width="w-44"
              />
              <SelectDropdown
                label="Severity"
                options={SEVERITIES}
                value={filters.severity || ''}
                onChange={(v) => setFilters({ severity: v || null })}
                searchable={false}
                width="w-40"
              />
              <SelectDropdown
                label="Status"
                options={VERIFICATIONS}
                value={filters.verification_status || ''}
                onChange={(v) => setFilters({ verification_status: v || null })}
                searchable={false}
                width="w-44"
              />

              {activeFilterCount > 0 && (
                <button
                  onClick={clearFilters}
                  className="h-9 px-3 text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-colors border border-rose-200"
                >
                  Clear Filters ({activeFilterCount})
                </button>
              )}

              <div className="flex-1" />
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
                  {rankedEvents.length} situation{rankedEvents.length !== 1 ? 's' : ''} detected
                </span>
              </div>
            </div>
          </div>

          {/* Summary strip */}
          {summary && (
            <div className="px-6 py-2.5 bg-white border-b border-slate-200 flex-shrink-0">
              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-2 bg-slate-50 px-3 py-1 rounded-lg border border-slate-200 text-xs">
                  <span className="text-slate-500 font-medium">Total Situations:</span>
                  <span className="mono font-bold text-slate-800">{summary.total}</span>
                </div>
                {summary.highPriority > 0 && (
                  <div className="flex items-center gap-2 bg-rose-50 px-3 py-1 rounded-lg border border-rose-200 text-xs">
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                    <span className="font-bold text-rose-700">{summary.highPriority} High Priority</span>
                  </div>
                )}
                {summary.elevated > 0 && (
                  <div className="flex items-center gap-2 bg-amber-50 px-3 py-1 rounded-lg border border-amber-200 text-xs">
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    <span className="font-bold text-amber-700">{summary.elevated} Elevated</span>
                  </div>
                )}
                <div className="flex items-center gap-2 bg-blue-50 px-3 py-1 rounded-lg border border-blue-200 text-xs">
                  <span className="text-blue-600 font-medium">Coverage Area:</span>
                  <span className="font-bold text-blue-800">{summary.cityCount} cit{summary.cityCount !== 1 ? 'ies' : 'y'}</span>
                </div>
              </div>
            </div>
          )}

          {/* Main workspace: Queue + Map + Evidence */}
          <div className="flex-1 flex">
            {/* Left: Queue + Evidence */}
            <div className="flex-1 px-6 py-4 min-w-0">
              {loading && rankedEvents.length === 0 ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="card-white rounded-xl p-4 animate-pulse">
                      <div className="h-4 w-32 bg-slate-200 rounded mb-2.5" />
                      <div className="h-3 w-56 bg-slate-200 rounded" />
                    </div>
                  ))}
                </div>
              ) : rankedEvents.length === 0 ? (
                <div className="card-white rounded-xl p-10 text-center border border-slate-200">
                  <div className="text-3xl mb-3">🔍</div>
                  <div className="text-sm font-bold text-slate-800 mb-1">
                    {activeFilterCount > 0
                      ? 'No emerging situations match current filters'
                      : 'No emerging situations detected'}
                  </div>
                  <p className="text-xs text-slate-500 mb-4 max-w-md mx-auto">
                    {activeFilterCount > 0
                      ? 'Try adjusting or clearing your category, severity, or status filters.'
                      : 'Atmospheric telemetry is currently within baseline parameters across monitored sectors.'}
                  </p>
                  {activeFilterCount > 0 && (
                    <button onClick={clearFilters} className="btn-secondary text-xs px-4 py-2">
                      Clear all filters
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Evidence panel for selected event */}
                  {selectedEvent && (
                    <EvidencePanel event={selectedEvent} onClose={clearSelectedEvent} />
                  )}

                  {/* Emerging Situation Queue Header */}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-xs font-bold tracking-wider text-slate-500 uppercase">
                      Emerging Situation Queue ({rankedEvents.length})
                    </span>
                    <span className="text-[11px] text-slate-400">Sorted by dynamic attention priority</span>
                  </div>

                  {rankedEvents.map((event) => {
                    const isSelected = selectedEvent?.event_id === event.event_id
                    const reasons = getEmergenceReasons(event)

                    return (
                      <div
                        key={event.event_id}
                        onClick={() => handleSelectEvent(event)}
                        className={`card-white rounded-xl p-4 cursor-pointer transition-all border ${
                          isSelected
                            ? 'border-blue-500 ring-2 ring-blue-500/20 bg-blue-50/20 shadow-md'
                            : 'border-slate-200 hover:border-slate-300 hover:shadow-md'
                        }`}
                      >
                        {/* Top row: category + priority */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full ring-2 ring-offset-1 ring-slate-200" style={{ background: SEV_COLOR[event.severity] }} />
                            <span className="text-sm font-bold text-slate-900">
                              {CAT[event.event_category] || event.event_category}
                            </span>
                            <span className="text-xs text-slate-400 font-medium">
                              · {event.city || 'Unknown'}{event.state ? `, ${event.state}` : ''}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span
                              className="text-xs font-bold px-2 py-0.5 rounded-full border shadow-sm"
                              style={{ color: event._priority.color, background: `${event._priority.color}15`, borderColor: `${event._priority.color}40` }}
                            >
                              ● {event._priority.label}
                            </span>
                            <span
                              className="text-xs font-bold px-2 py-0.5 rounded-full border shadow-sm"
                              style={{ color: VER_COLOR[event.verification_status], background: `${VER_COLOR[event.verification_status]}15`, borderColor: `${VER_COLOR[event.verification_status]}40` }}
                            >
                              {VER_LABEL[event.verification_status]}
                            </span>
                          </div>
                        </div>

                        {/* Metrics row */}
                        <div className="flex items-center gap-4 text-xs text-slate-500 bg-slate-50/70 px-3 py-2 rounded-lg border border-slate-100 mb-2.5 flex-wrap">
                          <span>Reports: <strong className="mono text-slate-800 font-bold">{event.report_count ?? '—'}</strong></span>
                          <span>Sources: <strong className="mono text-slate-800 font-bold">{event.source_count ?? '—'}</strong></span>
                          <span>Confidence: <strong className="mono text-blue-600 font-bold">{fmtPct(event.classification_confidence)}</strong></span>
                          <span>Credibility: <strong className="mono text-emerald-600 font-bold">{fmtPct(event.credibility_score)}</strong></span>
                          <span>First detected: <strong className="mono text-slate-700 font-medium">{ago(event.event_timestamp)}</strong></span>
                        </div>

                        {/* Evidence reasons */}
                        <div className="flex flex-wrap gap-1.5">
                          {reasons.slice(0, 3).map((r, i) => (
                            <span key={i} className="text-[11px] font-medium text-slate-700 bg-white border border-slate-200 px-2 py-0.5 rounded-md shadow-xs">
                              ✦ {r}
                            </span>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Error banner */}
              {error && rankedEvents.length > 0 && (
                <div className="mt-3 px-4 py-2.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 font-medium flex items-center gap-2">
                  <span>⚠️ Data refresh delayed. Last successful update: {lastUpdated ? ago(lastUpdated) : '—'}</span>
                </div>
              )}
            </div>

            {/* Right: Map */}
            <div className="w-[420px] flex-shrink-0 p-3 pl-0">
              <EmergingMap
                events={mapEvents}
                selectedEvent={selectedEvent}
                onSelectEvent={handleSelectEvent}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
