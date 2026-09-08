import React, { useEffect, useMemo, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useVerificationStore from '../stores/verificationStore'
import Sidebar from '../components/command-center/Sidebar'
import Header from '../components/command-center/Header'
import SelectDropdown from '../components/common/SelectDropdown'
import { WeatherPhenomenonSymbol, VerifiedShield, UnderReviewGlass, AlertTriangle } from '../components/common/Symbols'
import { CityCrest } from '../components/common/BrandLogos'
import { playNotificationChime, playHazardSiren } from '../utils/audioAlerts'

/* ═══════════════════════════════════════════════════════════════
   Constants
   ═══════════════════════════════════════════════════════════════ */

const CAT = {
  heavy_rainfall: 'Heavy Rain', rainfall: 'Rain', flood: 'Flood',
  heatwave: 'Heatwave', thunderstorm: 'Thunderstorm', lightning: 'Lightning',
  strong_wind: 'Strong Wind', hailstorm: 'Hail', dust_storm: 'Dust Storm',
  cyclone: 'Cyclone', fog: 'Fog',
}
const SEV_DOT = {
  low: 'bg-slate-400',
  moderate: 'bg-blue-500',
  high: 'bg-amber-500',
  extreme: 'bg-rose-500',
  critical: 'bg-rose-600',
}
const SEV_LBL = {
  low: 'Low', moderate: 'Moderate', high: 'High',
  extreme: 'Critical', critical: 'Critical',
}
const VER_STYLE = {
  verified: { dot: 'bg-emerald-500', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Verified' },
  pending: { dot: 'bg-slate-400', text: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200', label: 'Pending' },
  needs_review: { dot: 'bg-amber-500', text: 'text-amber-800', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Needs Review' },
  suspicious: { dot: 'bg-rose-500', text: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200', label: 'Suspicious' },
  duplicate: { dot: 'bg-slate-400', text: 'text-slate-600', bg: 'bg-slate-100', border: 'border-slate-200', label: 'Duplicate' },
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Status', icon: '🛡️' },
  { value: 'needs_review', label: 'Needs Review', icon: '🔍', status: 'Review', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'suspicious', label: 'Suspicious', icon: '⚠️', status: 'Flagged', statusColor: 'bg-rose-50 text-rose-700' },
  { value: 'pending', label: 'Pending', icon: '⏳', status: 'Pending', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'verified', label: 'Verified', icon: '✓', status: 'Verified', statusColor: 'bg-emerald-50 text-emerald-700' },
  { value: 'duplicate', label: 'Duplicate', icon: '📋', status: 'Duplicate', statusColor: 'bg-slate-100 text-slate-700' },
]
const CATEGORY_OPTIONS = [
  { value: '', label: 'All Categories', icon: '🌐' },
  { value: 'heavy_rainfall', label: 'Heavy Rain', icon: '🌧️', subtitle: 'Monsoon deluge' },
  { value: 'rainfall', label: 'Rain', icon: '🌦️', subtitle: 'Precipitation' },
  { value: 'flood', label: 'Flood', icon: '🌊', subtitle: 'Urban inundation' },
  { value: 'heatwave', label: 'Heatwave', icon: '🔥', subtitle: 'Thermal anomaly' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: '⛈️', subtitle: 'Lightning storm' },
  { value: 'strong_wind', label: 'Strong Wind', icon: '💨', subtitle: 'Gale force' },
  { value: 'cyclone', label: 'Cyclone', icon: '🌀', subtitle: 'Vortex front' },
  { value: 'fog', label: 'Fog', icon: '🌫️', subtitle: 'Low visibility' },
  { value: 'dust_storm', label: 'Dust Storm', icon: '🌪️', subtitle: 'Particulate front' },
]
const SEVERITY_OPTIONS = [
  { value: '', label: 'All Severities', icon: '⚡' },
  { value: 'low', label: 'Low', icon: '●', status: 'Low', statusColor: 'bg-slate-100 text-slate-700' },
  { value: 'moderate', label: 'Moderate', icon: '●', status: 'Moderate', statusColor: 'bg-blue-50 text-blue-700' },
  { value: 'high', label: 'High', icon: '●', status: 'High', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'extreme', label: 'Extreme / Critical', icon: '●', status: 'Critical', statusColor: 'bg-rose-50 text-rose-700' },
]
const SOURCE_OPTIONS = [
  { value: '', label: 'All Sources', icon: '📡' },
  { value: 'weather_api', label: 'Weather API', icon: '🌐', subtitle: 'Official sensors' },
  { value: 'synthetic', label: 'Synthetic Doppler', icon: '🛰️', subtitle: 'Radar fusion' },
  { value: 'citizen', label: 'Citizen Reports', icon: '👥', subtitle: 'Ground truth' },
]

const VERIFY_ACTIONS = [
  { action: 'verified', label: 'Verify Event', className: 'btn-verify' },
  { action: 'needs_review', label: 'Request Review', className: 'btn-secondary text-amber-700 hover:text-amber-800 hover:border-amber-400' },
  { action: 'marked_suspicious', label: 'Flag Suspicious', className: 'btn-danger' },
  { action: 'marked_duplicate', label: 'Mark Duplicate', className: 'btn-secondary text-slate-600 hover:border-slate-400' },
]

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

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

function fmtIst(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false,
    })
  } catch {
    return iso
  }
}

/* ═══════════════════════════════════════════════════════════════
   Sub-components
   ═══════════════════════════════════════════════════════════════ */

function SummaryCard({ label, value, dotColor, icon = '●' }) {
  return (
    <div className="card-white px-4 py-3 flex-1 min-w-[140px] border border-slate-200 shadow-2xs hover:shadow-xs transition-all">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">{label}</span>
        <div className={`w-2 h-2 rounded-full ${dotColor}`} />
      </div>
      <div className="mono text-2xl font-extrabold text-slate-900 leading-none">{value}</div>
    </div>
  )
}

function VerificationQueueSkeleton({ rows = 8 }) {
  return (
    <tbody>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className="border-b border-slate-100">
          {Array.from({ length: 7 }).map((_, j) => (
            <td key={j} className="px-3 py-3">
              <div className="h-3.5 bg-slate-100 rounded animate-pulse" style={{ width: `${50 + Math.random() * 40}%` }} />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Review Panel
   ═══════════════════════════════════════════════════════════════ */

function ReviewPanel({ detail, loading, onClose, onAction, actionLoading }) {
  if (loading) {
    return (
      <div className="w-[420px] flex-shrink-0 border-l border-slate-200 bg-white overflow-y-auto">
        <div className="p-4 space-y-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i}>
              <div className="h-3 w-20 bg-slate-100 rounded animate-pulse mb-2" />
              <div className="h-4 w-full bg-slate-100 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!detail) return null

  const vs = VER_STYLE[detail.verification?.status] || VER_STYLE.pending
  const loc = detail.location || {}
  const ai = detail.ai || {}
  const verification = detail.verification || {}
  const reasons = verification.verification_reasons || []
  const credibilityReasons = ai.credibility_reasons || []

  return (
    <div className="w-[420px] flex-shrink-0 border-l border-[#D9E0E6] bg-white overflow-y-auto">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#D9E0E6] flex items-center justify-between">
        <div>
          <div className="text-[13px] font-semibold text-[#18232D]">Event Review</div>
          <div className="text-[10px] text-[#7A8794] mono">{detail.event_id?.slice(0, 12)}…</div>
        </div>
        <button
          onClick={onClose}
          className="text-[14px] text-[#7A8794] hover:text-[#18232D] px-1"
          aria-label="Close panel"
        >
          ×
        </button>
      </div>

      {/* Event info */}
      <div className="px-4 py-3 border-b border-[#EDEEF1]">
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-[7px] h-[7px] rounded-full ${SEV_DOT[detail.event?.severity] || 'bg-[#7A8794]'}`} />
          <span className="text-[13px] font-medium text-[#18232D]">
            {CAT[detail.event?.category] || detail.event?.category || '—'}
          </span>
          <span className={`text-[10px] font-medium ${vs.text} ml-auto`}>
            <span className={`inline-block w-[4px] h-[4px] rounded-full ${vs.dot} mr-1`} />
            {vs.label}
          </span>
        </div>
        <div className="text-[11px] text-[#526170] mb-1">
          {loc.city && <span>{loc.city}{loc.state ? `, ${loc.state}` : ''}</span>}
          {!loc.city && loc.state && <span>{loc.state}</span>}
        </div>
        {detail.event?.description && (
          <div className="text-[11px] text-[#526170] mt-2 leading-relaxed">
            {detail.event.description}
          </div>
        )}
        <div className="flex gap-4 mt-2 text-[10px] text-[#7A8794] mono">
          <span>First seen: {fmtIst(detail.event_timestamp)}</span>
          <span>Last seen: {fmtIst(detail.updated_at)}</span>
        </div>
      </div>

      {/* Evidence */}
      <div className="px-4 py-3 border-b border-[#EDEEF1]">
        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Evidence</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-[10px] text-[#7A8794]">Source Count</div>
            <div className="mono text-[14px] font-semibold text-[#18232D]">{detail.source_count ?? '—'}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Report Count</div>
            <div className="mono text-[14px] font-semibold text-[#18232D]">{detail.report_count ?? '—'}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Source</div>
            <div className="text-[11px] text-[#18232D]">{detail.source?.source_name || '—'}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Source Type</div>
            <div className="text-[11px] text-[#18232D]">{detail.source?.source_type || '—'}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Source Trust</div>
            <div className="mono text-[11px] text-[#18232D]">
              {detail.source?.source_trust_score != null ? `${Math.round(detail.source.source_trust_score * 100)}%` : '—'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Location</div>
            <div className="mono text-[11px] text-[#18232D]">
              {loc.latitude != null ? `${loc.latitude?.toFixed(2)}, ${loc.longitude?.toFixed(2)}` : '—'}
            </div>
          </div>
        </div>
      </div>

      {/* AI / Classification */}
      <div className="px-4 py-3 border-b border-[#EDEEF1]">
        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Classification</div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <div className="text-[10px] text-[#7A8794]">Classified As</div>
            <div className="text-[11px] font-medium text-[#18232D]">
              {CAT[ai.classified_category] || ai.classified_category || '—'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Classification Confidence</div>
            <div className="mono text-[11px] text-[#18232D]">{fmtPct(ai.classification_confidence)}</div>
          </div>
        </div>

        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Credibility Assessment</div>
        <div className="mb-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-[#7A8794]">Credibility Score</span>
            <span className="mono text-[13px] font-semibold text-[#18232D]">{fmtPct(ai.credibility_score)}</span>
          </div>
          <div className="w-full h-1.5 bg-[#E4E8EC] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#477D96] rounded-full transition-all"
              style={{ width: `${(ai.credibility_score || 0) * 100}%` }}
            />
          </div>
        </div>

        {credibilityReasons.length > 0 && (
          <div className="space-y-1 mt-2">
            {credibilityReasons.map((r, i) => (
              <div key={i} className="text-[10px] text-[#526170] flex items-start gap-1.5">
                <span className="text-[#477D96] mt-0.5">•</span>
                <span>{r}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Verification */}
      <div className="px-4 py-3 border-b border-[#EDEEF1]">
        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Verification Assessment</div>

        {reasons.length > 0 ? (
          <div className="space-y-1.5">
            {reasons.map((r, i) => {
              const isPositive = r.toLowerCase().includes('strong') || r.toLowerCase().includes('consistent') || r.toLowerCase().includes('trusted') || r.toLowerCase().includes('agreement')
              const isWarning = r.toLowerCase().includes('limited') || r.toLowerCase().includes('warning') || r.toLowerCase().includes('low') || r.toLowerCase().includes('missing')
              return (
                <div key={i} className="flex items-start gap-2 text-[11px]">
                  <span className={`mt-0.5 flex-shrink-0 ${isPositive ? 'text-[#31845D]' : isWarning ? 'text-[#B56F20]' : 'text-[#7A8794]'}`}>
                    {isPositive ? '✓' : isWarning ? '⚠' : '•'}
                  </span>
                  <span className="text-[#526170]">{r}</span>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="text-[11px] text-[#7A8794] italic">No verification reasons available.</div>
        )}

        {verification.verified_by && (
          <div className="mt-2 text-[10px] text-[#7A8794]">
            Verified by: <span className="text-[#526170]">{verification.verified_by}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-4 py-4 border-t border-slate-100 bg-slate-50/50">
        <div className="text-[10px] font-bold tracking-wider text-slate-500 uppercase mb-2.5">Verification Decisions</div>
        <div className="flex flex-wrap gap-2">
          {VERIFY_ACTIONS.map((a) => (
            <button
              key={a.action}
              onClick={() => onAction(detail.event_id, a.action)}
              disabled={actionLoading || detail.verification?.status === a.action?.replace('marked_', '')}
              className={`h-9 px-3.5 text-xs font-bold transition-all shadow-2xs ${a.className} disabled:opacity-40 disabled:cursor-not-allowed`}
            >
              {a.action === 'verified' && <span className="text-sm">✓</span>}
              {a.action === 'needs_review' && <span className="text-sm">⏳</span>}
              {a.action === 'marked_suspicious' && <span className="text-sm">⚠</span>}
              {a.action === 'marked_duplicate' && <span className="text-sm">⧉</span>}
              <span>{a.label}</span>
            </button>
          ))}
        </div>
        <div className="mt-2 text-[10px] text-slate-400 font-medium">
          Actions update canonical event verification status with cryptographic audit logs.
        </div>
      </div>

      {/* View full detail link */}
      <div className="px-4 py-3 border-t border-slate-100 bg-white">
        <Link
          to={`/events/${detail.event_id}`}
          className="btn-secondary w-full text-xs py-2 justify-center font-bold text-blue-700"
        >
          <span>View Full Event Intelligence</span>
          <span>→</span>
        </Link>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Main Page
   ═══════════════════════════════════════════════════════════════ */

export default function VerificationCenter() {
  const navigate = useNavigate()
  const {
    events, total, totalPages, page, pageSize,
    stats, filters, sortBy, sortOrder, search,
    selectedEvent, selectedEventDetail,
    loading, detailLoading, actionLoading, error, lastUpdated,
    setPage, setSortBy, setSortOrder, setSearch, setFilters, clearFilters,
    selectEvent, clearSelection, fetchEvents, fetchStats, fetchEventDetail,
    performVerification, startPolling, stopPolling,
  } = useVerificationStore()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  useEffect(() => {
    if (selectedEvent) {
      fetchEventDetail(selectedEvent.event_id)
    }
  }, [selectedEvent, fetchEventDetail])

  // Client-side search filter
  const displayEvents = useMemo(() => {
    if (!search.trim()) return events
    const q = search.toLowerCase()
    return events.filter((e) =>
      (e.city || '').toLowerCase().includes(q) ||
      (e.state || '').toLowerCase().includes(q) ||
      (e.event_category || '').toLowerCase().includes(q) ||
      (e.source_name || '').toLowerCase().includes(q) ||
      (e.event_id || '').toLowerCase().includes(q)
    )
  }, [events, search])

  const activeFilterCount = Object.values(filters).filter(Boolean).length

  // Bulk selection and checklist state
  const [selectedIds, setSelectedIds] = useState([])
  const [checklistEvent, setChecklistEvent] = useState(null)
  const [evidenceChecks, setEvidenceChecks] = useState({ radar: true, satellite: true, aws: true, citizen: false })
  const [officerRemark, setOfficerRemark] = useState('')

  const toggleSelectId = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const toggleSelectAll = () => {
    if (selectedIds.length === displayEvents.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(displayEvents.map((e) => e.event_id))
    }
  }

  const handleBulkAction = async (action) => {
    if (!selectedIds.length) return
    try {
      for (const id of selectedIds) {
        await performVerification(id, action, 'admin', 'Batch triage executed from verification console')
      }
      setSelectedIds([])
      playNotificationChime()
    } catch (err) {
      console.error('Bulk verification failed:', err)
    }
  }

  const exportAuditLog = () => {
    if (!displayEvents.length) return
    const headers = ['Event ID', 'City', 'State', 'Category', 'Severity', 'Verification Status', 'Confidence', 'Credibility']
    const rows = displayEvents.map((e) => [
      `"${e.event_id || ''}"`,
      `"${e.city || ''}"`,
      `"${e.state || ''}"`,
      `"${e.event_category || ''}"`,
      `"${e.severity || ''}"`,
      `"${e.verification_status || ''}"`,
      `"${Math.round((e.classification_confidence || 0) * 100)}%"`,
      `"${Math.round((e.credibility_score || 0) * 100)}%"`,
    ])
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `verification_audit_trail_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    playNotificationChime()
  }

  const handleAction = useCallback(async (eventId, action) => {
    try {
      await performVerification(eventId, action, 'admin', '')
    } catch (err) {
      console.error('Verification action failed:', err)
    }
  }, [performVerification])

  // Summary counts
  const vStats = stats?.by_verification_status || {}
  const summaryData = useMemo(() => ({
    total: stats?.total_events ?? total ?? 0,
    needs_review: vStats.needs_review || 0,
    suspicious: vStats.suspicious || 0,
    verified: vStats.verified || 0,
    pending: vStats.pending || 0,
    duplicate: vStats.duplicate || 0,
  }), [stats, total, vStats])

  return (
    <div className="flex h-screen bg-slate-50/70 overflow-hidden">
      {/* Unified Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 bg-slate-50/70 overflow-hidden">
        <Header />

        {/* Content */}
        <div className="flex-1 overflow-hidden flex bg-slate-50/70">
          {/* Left: Queue */}
          <div className="flex-1 overflow-y-auto px-5 py-4 min-w-0 scrollbar-thin">
            {/* Page title + Actions */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
              <div>
                <h1 className="text-lg font-bold text-slate-900 tracking-tight mb-0.5">Verification Center</h1>
                <div className="text-xs text-slate-500">
                  Review and manage weather event verification status
                  {lastUpdated && <span className="ml-3 font-mono text-[11px] text-slate-400">Last updated {ago(lastUpdated)}</span>}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={exportAuditLog}
                  className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-2xs font-semibold"
                  title="Export Verification Audit Trail"
                >
                  <span>📋</span>
                  <span>Export Audit Log ({displayEvents.length})</span>
                </button>
              </div>
            </div>

            {/* Summary strip */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
              <SummaryCard label="Total Events" value={summaryData.total} dotColor="bg-blue-600" />
              <SummaryCard label="Needs Review" value={summaryData.needs_review} dotColor="bg-amber-500" />
              <SummaryCard label="Suspicious" value={summaryData.suspicious} dotColor="bg-rose-500" />
              <SummaryCard label="Verified" value={summaryData.verified} dotColor="bg-emerald-500" />
              <SummaryCard label="Pending" value={summaryData.pending} dotColor="bg-slate-400" />
            </div>

            {/* Filters */}
            <div className="mb-3 space-y-2.5">
              <div className="flex items-center gap-3">
                <div className="relative flex-1 max-w-md">
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search events, cities, categories..."
                    className="w-full h-9 bg-white border border-slate-200 rounded-xl px-3.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 shadow-xs"
                  />
                  {search && (
                    <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-700">✕</button>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <div className="w-44">
                  <SelectDropdown
                    options={STATUS_OPTIONS}
                    value={filters.verification_status || ''}
                    onChange={(v) => setFilters({ verification_status: v || null })}
                    placeholder="All Status"
                    compact={true}
                  />
                </div>
                <div className="w-44">
                  <SelectDropdown
                    options={CATEGORY_OPTIONS}
                    value={filters.category || ''}
                    onChange={(v) => setFilters({ category: v || null })}
                    placeholder="All Categories"
                    compact={true}
                  />
                </div>
                <div className="w-40">
                  <SelectDropdown
                    options={SEVERITY_OPTIONS}
                    value={filters.severity || ''}
                    onChange={(v) => setFilters({ severity: v || null })}
                    placeholder="All Severities"
                    compact={true}
                  />
                </div>
                <div className="w-44">
                  <SelectDropdown
                    options={SOURCE_OPTIONS}
                    value={filters.source_type || ''}
                    onChange={(v) => setFilters({ source_type: v || null })}
                    placeholder="All Sources"
                    compact={true}
                  />
                </div>
                {activeFilterCount > 0 && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="h-8 px-2.5 text-xs text-rose-600 hover:text-rose-700 font-bold bg-rose-50 border border-rose-200 rounded-xl shadow-xs transition-colors"
                  >
                    Clear ({activeFilterCount})
                  </button>
                )}
                <div className="flex-1" />
                <span className="text-xs text-slate-400 font-mono font-medium">{total.toLocaleString()} event{total !== 1 ? 's' : ''}</span>
              </div>
            </div>

            {/* Event table */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="px-3 py-3 w-[4%] text-center">
                        <input
                          type="checkbox"
                          checked={selectedIds.length === displayEvents.length && displayEvents.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer"
                        />
                      </th>
                      <th className="px-3 py-3 w-[18%]">Event</th>
                      <th className="px-3 py-3 w-[15%]">Location</th>
                      <th className="px-3 py-3 w-[9%]">Severity</th>
                      <th className="px-3 py-3 w-[9%]">Confidence</th>
                      <th className="px-3 py-3 w-[9%]">Credibility</th>
                      <th className="px-3 py-3 w-[11%]">Status</th>
                      <th className="px-3 py-3 w-[7%]">Sources</th>
                      <th className="px-3 py-3 w-[6%]">Reports</th>
                      <th className="px-3 py-3 w-[12%] text-right">Actions</th>
                    </tr>
                  </thead>

                  {loading && events.length === 0 ? (
                    <VerificationQueueSkeleton />
                  ) : displayEvents.length === 0 ? (
                    <tbody>
                      <tr>
                        <td colSpan={10} className="px-4 py-12 text-center">
                          <div className="text-[13px] font-semibold text-[#18232D] mb-1">
                            {search || activeFilterCount > 0 ? 'No events match your filters' : 'No events requiring review'}
                          </div>
                          <p className="text-[11px] text-[#7A8794] mb-3">
                            {search || activeFilterCount > 0 ? 'Try adjusting or clearing your filters.' : 'All events are verified or no events exist yet.'}
                          </p>
                          {(search || activeFilterCount > 0) && (
                            <button onClick={() => { clearFilters(); setSearch('') }} className="text-[11px] text-[#477D96] hover:text-[#3B6FA0] font-medium">
                              Clear all filters
                            </button>
                          )}
                        </td>
                      </tr>
                    </tbody>
                  ) : (
                    <tbody>
                      {displayEvents.map((e) => {
                        const vs = VER_STYLE[e.verification_status] || VER_STYLE.pending
                        const isSelected = selectedEvent?.event_id === e.event_id
                        const isChecked = selectedIds.includes(e.event_id)

                        return (
                          <tr
                            key={e.event_id}
                            onClick={() => selectEvent(e)}
                            className={`border-b border-[#EDEEF1] cursor-pointer transition-colors ${
                              isSelected ? 'bg-[#F0F4F7]' : isChecked ? 'bg-blue-50/40' : 'hover:bg-[#F8FAFB]'
                            }`}
                            tabIndex={0}
                            onKeyDown={(ev) => { if (ev.key === 'Enter') selectEvent(e) }}
                          >
                            <td className="px-2.5 py-2.5 text-center" onClick={(ev) => ev.stopPropagation()}>
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => toggleSelectId(e.event_id)}
                                className="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer"
                              />
                            </td>
                            <td className="px-3 py-2.5">
                              <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded-md bg-slate-50 border border-slate-200 p-0.5 flex items-center justify-center flex-shrink-0">
                                  <WeatherPhenomenonSymbol category={e.event_category} size={15} />
                                </div>
                                <span className="text-xs font-bold text-slate-900">
                                  {CAT[e.event_category] || e.event_category}
                                </span>
                              </div>
                            </td>
                            <td className="px-3 py-2.5">
                              <div className="flex items-center gap-1.5">
                                <CityCrest city={e.city} size="xs" />
                                <div className="min-w-0">
                                  <div className="text-xs font-semibold text-slate-800 truncate">{e.city || '—'}</div>
                                  <div className="text-[10px] text-slate-400 font-medium">{e.state || ''}</div>
                                </div>
                              </div>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="text-xs font-bold text-slate-700">{SEV_LBL[e.severity] || '—'}</span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="text-xs mono font-bold text-blue-600">{fmtPct(e.classification_confidence)}</span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="text-xs mono font-bold text-emerald-600">{fmtPct(e.credibility_score)}</span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md border ${vs.bg} ${vs.text} ${vs.border}`}>
                                {e.verification_status === 'verified' ? (
                                  <VerifiedShield size={12} />
                                ) : e.verification_status === 'pending' ? (
                                  <UnderReviewGlass size={12} />
                                ) : (
                                  <AlertTriangle size={12} />
                                )}
                                <span>{vs.label}</span>
                              </span>
                            </td>
                            <td className="px-3 py-2.5 mono text-xs font-bold text-slate-700">
                              {e.source_count ?? '—'}
                            </td>
                            <td className="px-3 py-2.5 mono text-xs font-bold text-slate-700">
                              {e.report_count ?? '—'}
                            </td>
                            <td className="px-3 py-2.5 text-right" onClick={(ev) => ev.stopPropagation()}>
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => setChecklistEvent(e)}
                                  className="btn-secondary text-[10px] py-1 px-2 font-bold hover:text-blue-700 hover:border-blue-300"
                                  title="Open Evidence Corroboration Checklist"
                                >
                                  Checklist
                                </button>
                                <button
                                  type="button"
                                  onClick={() => selectEvent(e)}
                                  className="btn-primary text-[10px] py-1 px-2 font-bold"
                                >
                                  Review →
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  )}
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#D9E0E6] bg-[#F8FAFB]">
                  <span className="text-[10px] text-[#7A8794]">
                    Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total.toLocaleString()}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      disabled={page <= 1}
                      onClick={() => setPage(page - 1)}
                      className="h-7 px-2 text-[11px] rounded border border-[#D9E0E6] bg-white text-[#526170] hover:bg-[#F3F5F7] disabled:opacity-30 disabled:cursor-not-allowed"
                    >←</button>
                    {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
                      let pageNum
                      if (totalPages <= 5) pageNum = i + 1
                      else if (page <= 3) pageNum = i + 1
                      else if (page >= totalPages - 2) pageNum = totalPages - 4 + i
                      else pageNum = page - 2 + i
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setPage(pageNum)}
                          className={`h-7 w-7 text-[11px] rounded border ${
                            pageNum === page
                              ? 'bg-[#477D96] text-white border-[#477D96]'
                              : 'bg-white text-[#526170] border-[#D9E0E6] hover:bg-[#F3F5F7]'
                          }`}
                        >{pageNum}</button>
                      )
                    })}
                    <button
                      disabled={page >= totalPages}
                      onClick={() => setPage(page + 1)}
                      className="h-7 px-2 text-[11px] rounded border border-[#D9E0E6] bg-white text-[#526170] hover:bg-[#F3F5F7] disabled:opacity-30 disabled:cursor-not-allowed"
                    >→</button>
                  </div>
                </div>
              )}
            </div>

            {/* Floating Bulk Action Bar */}
            {selectedIds.length > 0 && (
              <div className="sticky bottom-4 mt-3 z-30 bg-white border border-slate-300 shadow-xl rounded-2xl p-3 flex flex-wrap items-center justify-between gap-3 animate-in slide-in-from-bottom duration-150">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
                  <span className="text-xs font-bold text-slate-900">
                    {selectedIds.length} Event{selectedIds.length !== 1 ? 's' : ''} Selected
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleBulkAction('verified')}
                    className="btn-verify text-xs py-1 px-3 shadow-2xs font-bold"
                  >
                    ✓ Bulk Verify
                  </button>
                  <button
                    type="button"
                    onClick={() => handleBulkAction('needs_review')}
                    className="btn-secondary text-xs py-1 px-3 text-amber-700 hover:border-amber-400 font-bold"
                  >
                    🔍 Request Review
                  </button>
                  <button
                    type="button"
                    onClick={() => handleBulkAction('marked_suspicious')}
                    className="btn-danger text-xs py-1 px-3 font-bold"
                  >
                    ✕ Flag Suspicious
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedIds([])}
                    className="text-xs text-slate-400 hover:text-slate-700 ml-1 font-semibold"
                  >
                    Clear
                  </button>
                </div>
              </div>
            )}

            {/* Error banner */}
            {error && events.length > 0 && (
              <div className="mt-2 px-3 py-2 bg-[#F8E7E7] border border-[#F8E7E7] rounded text-[11px] text-[#B84848]">
                DEGRADED — Polling failed. Last successful update: {lastUpdated ? ago(lastUpdated) : '—'}
              </div>
            )}
          </div>

          {/* Right: Review Panel */}
          {selectedEvent && (
            <ReviewPanel
              detail={selectedEventDetail}
              loading={detailLoading}
              onClose={clearSelection}
              onAction={handleAction}
              actionLoading={actionLoading}
            />
          )}
        </div>
      </div>

      {/* Meteorological Corroboration Checklist Modal */}
      {checklistEvent && (
        <div
          className="fixed inset-0 z-[9995] bg-slate-900/40 backdrop-blur-2xs flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setChecklistEvent(null)
          }}
        >
          <div className="w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150 flex flex-col">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center">
                  <WeatherPhenomenonSymbol category={checklistEvent.event_category} size={20} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">
                    Corroboration Checklist · #{checklistEvent.event_id?.slice(0, 8)}
                  </h2>
                  <p className="text-[11px] text-slate-500">
                    {checklistEvent.city} · {CAT[checklistEvent.event_category] || checklistEvent.event_category}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setChecklistEvent(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            {/* Checklist Items */}
            <div className="p-4 space-y-3 text-xs bg-white">
              <p className="text-slate-500 text-[11.5px] leading-relaxed mb-1">
                Verify that this weather event complies with standard meteorological corroboration thresholds before marking as certified:
              </p>

              <label className="flex items-start gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-blue-50/40 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={evidenceChecks.radar}
                  onChange={(e) => setEvidenceChecks({ ...evidenceChecks, radar: e.target.checked })}
                  className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-0"
                />
                <div>
                  <span className="font-bold text-slate-800 block">1. Doppler Weather Radar Echo Match</span>
                  <span className="text-[11px] text-slate-500">Echo reflectivity ≥ 40 dBZ confirmed by regional DWR station</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-blue-50/40 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={evidenceChecks.satellite}
                  onChange={(e) => setEvidenceChecks({ ...evidenceChecks, satellite: e.target.checked })}
                  className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-0"
                />
                <div>
                  <span className="font-bold text-slate-800 block">2. INSAT-3D Thermal Infrared Plume Validated</span>
                  <span className="text-[11px] text-slate-500">Cloud-top brightness temperature anomaly correlates with convective intensity</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-blue-50/40 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={evidenceChecks.aws}
                  onChange={(e) => setEvidenceChecks({ ...evidenceChecks, aws: e.target.checked })}
                  className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-0"
                />
                <div>
                  <span className="font-bold text-slate-800 block">3. Surface Automated Weather Station (AWS) Quorum</span>
                  <span className="text-[11px] text-slate-500">Pressure gradient dip & in-situ precipitation telemetry match event signature</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-blue-50/40 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={evidenceChecks.citizen}
                  onChange={(e) => setEvidenceChecks({ ...evidenceChecks, citizen: e.target.checked })}
                  className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-0"
                />
                <div>
                  <span className="font-bold text-slate-800 block">4. Ground Truth Proximity Verification</span>
                  <span className="text-[11px] text-slate-500">Multi-point reports within 3.5km spatial radius without conflicting anomalies</span>
                </div>
              </label>

              {/* Officer Remark */}
              <div className="pt-2">
                <label className="text-[11px] font-bold text-slate-700 block mb-1">
                  Duty Officer Sign-Off Remarks (Optional)
                </label>
                <textarea
                  value={officerRemark}
                  onChange={(e) => setOfficerRemark(e.target.value)}
                  placeholder="e.g. Cross-referenced with IMD Nowcast bulletin, validated telemetry corroboration."
                  rows={2}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white resize-none"
                />
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-3.5 border-t border-slate-200 bg-slate-50/80 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => setChecklistEvent(null)}
                className="btn-secondary text-xs py-1.5 px-3"
              >
                Cancel
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={async () => {
                    await handleAction(checklistEvent.event_id, 'needs_review')
                    setChecklistEvent(null)
                    playNotificationChime()
                  }}
                  className="btn-secondary text-xs py-1.5 px-3 text-amber-700 hover:border-amber-400"
                >
                  Flag for Review
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    await handleAction(checklistEvent.event_id, 'verified')
                    setChecklistEvent(null)
                    playNotificationChime()
                  }}
                  className="btn-verify text-xs py-1.5 px-4 font-bold"
                >
                  ✓ Sign-Off & Certify
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
