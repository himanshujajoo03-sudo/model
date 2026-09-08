import React, { useEffect, useMemo, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useReportReviewStore from '../stores/reportReviewStore'
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
const SEV_COLOR = {
  low: '#7A8794', moderate: '#477D96', high: '#B56F20',
  extreme: '#B84848', critical: '#9C3C3C',
}
const SEV_LABEL = { low: 'Low', moderate: 'Moderate', high: 'High', extreme: 'Extreme', critical: 'Critical' }
const VER_COLOR = {
  verified: '#31845D', pending: '#7A8794', needs_review: '#B56F20',
  suspicious: '#B84848', duplicate: '#8E9EAD',
}
const VER_LABEL = {
  verified: 'Verified', pending: 'Pending', needs_review: 'Needs Review',
  suspicious: 'Suspicious', duplicate: 'Duplicate',
}
const SRC_TYPE_LABEL = {
  weather_api: 'Weather API', government_dataset: 'Government', website: 'Website',
  rss: 'RSS', citizen: 'Citizen', social: 'Social Media',
  simulated_social: 'Simulated Social', synthetic: 'Synthetic',
}

const SOURCE_TYPES = [
  { value: '', label: 'All Sources', icon: '📡' },
  { value: 'weather_api', label: 'Weather API', icon: '🌐', subtitle: 'Official sensors' },
  { value: 'synthetic', label: 'Synthetic Doppler', icon: '🛰️', subtitle: 'Radar fusion' },
  { value: 'citizen', label: 'Citizen Reports', icon: '👥', subtitle: 'Ground truth' },
  { value: 'social', label: 'Social Feeds', icon: '💬', subtitle: 'Public signals' },
]
const CATEGORIES = [
  { value: '', label: 'All Categories', icon: '🌐' },
  { value: 'heavy_rainfall', label: 'Heavy Rain', icon: '🌧️', subtitle: 'Monsoon deluge' },
  { value: 'rainfall', label: 'Rain', icon: '🌦️', subtitle: 'Precipitation' },
  { value: 'flood', label: 'Flood', icon: '🌊', subtitle: 'Urban inundation' },
  { value: 'heatwave', label: 'Heatwave', icon: '🔥', subtitle: 'Thermal anomaly' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: '⛈️', subtitle: 'Lightning storm' },
  { value: 'strong_wind', label: 'Strong Wind', icon: '💨', subtitle: 'Gale force' },
]
const SEVERITIES = [
  { value: '', label: 'All Severities', icon: '⚡' },
  { value: 'low', label: 'Low', icon: '●', status: 'Low', statusColor: 'bg-slate-100 text-slate-700' },
  { value: 'moderate', label: 'Moderate', icon: '●', status: 'Moderate', statusColor: 'bg-blue-50 text-blue-700' },
  { value: 'high', label: 'High', icon: '●', status: 'High', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'extreme', label: 'Extreme / Critical', icon: '●', status: 'Critical', statusColor: 'bg-rose-50 text-rose-700' },
]
const VERIFICATIONS = [
  { value: '', label: 'All Status', icon: '🛡️' },
  { value: 'needs_review', label: 'Needs Review', icon: '🔍', status: 'Review', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'duplicate', label: 'Duplicate', icon: '📋', status: 'Duplicate', statusColor: 'bg-slate-100 text-slate-700' },
  { value: 'pending', label: 'Pending', icon: '⏳', status: 'Pending', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'verified', label: 'Verified', icon: '✓', status: 'Verified', statusColor: 'bg-emerald-50 text-emerald-700' },
  { value: 'suspicious', label: 'Suspicious', icon: '⚠️', status: 'Flagged', statusColor: 'bg-rose-50 text-rose-700' },
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

/* ═══════════════════════════════════════════════════════════════

/* ═══════════════════════════════════════════════════════════════
   Report Detail Panel
   ═══════════════════════════════════════════════════════════════ */

function ReportDetailPanel({ detail, loading, onClose, navigate }) {
  if (loading) {
    return (
      <div className="w-[420px] flex-shrink-0 border-l border-[#D9E0E6] bg-white overflow-y-auto">
        <div className="p-4 space-y-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i}>
              <div className="h-3 w-20 bg-[#E4E8EC] rounded animate-pulse mb-2" />
              <div className="h-4 w-full bg-[#E4E8EC] rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!detail) return null

  const vs = VER_COLOR[detail.verification_status] || '#7A8794'
  const isDuplicate = detail.duplicate_score != null && detail.duplicate_score >= 0.85

  return (
    <div className="w-[420px] flex-shrink-0 border-l border-[#D9E0E6] bg-white overflow-y-auto">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#D9E0E6] flex items-center justify-between">
        <div>
          <div className="text-[13px] font-semibold text-[#18232D]">Source Report</div>
          <div className="text-[10px] text-[#7A8794] mono">{detail.report_id?.slice(0, 12)}…</div>
        </div>
        <button onClick={onClose} className="text-[14px] text-[#7A8794] hover:text-[#18232D] px-1" aria-label="Close">✕</button>
      </div>

      {/* Source Information */}
      <div className="px-4 py-3 border-b border-[#EDEEF1]">
        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Source Information</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-[10px] text-[#7A8794]">Source Name</div>
            <div className="text-[12px] font-medium text-[#18232D]">{detail.source_name || '—'}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Source Type</div>
            <div className="text-[12px] text-[#18232D]">{SRC_TYPE_LABEL[detail.source_type] || detail.source_type}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Source ID</div>
            <div className="text-[10px] mono text-[#526170]">{detail.source_id || '—'}</div>
          </div>
          {detail.source_trust_score != null && (
            <div>
              <div className="text-[10px] text-[#7A8794]">Trust Score</div>
              <div className="text-[12px] mono text-[#18232D]">{fmtPct(detail.source_trust_score)}</div>
            </div>
          )}
        </div>
      </div>

      {/* Report Content */}
      <div className="px-4 py-3 border-b border-[#EDEEF1]">
        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Report Content</div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-[7px] h-[7px] rounded-full" style={{ background: SEV_COLOR[detail.severity] }} />
          <span className="text-[13px] font-medium text-[#18232D]">
            {CAT[detail.event_category] || detail.event_category}
          </span>
          <span className="text-[10px] font-medium" style={{ color: SEV_COLOR[detail.severity] }}>
            {SEV_LABEL[detail.severity]}
          </span>
        </div>
        <div className="text-[11px] text-[#526170] mb-2">
          {detail.city || 'Unknown'}{detail.state ? `, ${detail.state}` : ''}{detail.district ? `, ${detail.district}` : ''}
        </div>
        {detail.description && (
          <div className="text-[11px] text-[#526170] leading-relaxed bg-[#F8FAFB] border border-[#EDEEF1] rounded p-2.5">
            {detail.description}
          </div>
        )}
        <div className="flex gap-4 mt-2 text-[10px] text-[#7A8794]">
          <span>Observed: <span className="mono text-[#526170]">{fmtTime(detail.event_timestamp)}</span></span>
          <span>Ingested: <span className="mono text-[#526170]">{fmtTime(detail.ingestion_timestamp)}</span></span>
        </div>
      </div>

      {/* Assessment */}
      <div className="px-4 py-3 border-b border-[#EDEEF1]">
        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Assessment</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-[10px] text-[#7A8794]">Classification Confidence</div>
            <div className="text-[12px] mono text-[#18232D]">{fmtPct(detail.classification_confidence)}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Credibility Score</div>
            <div className="text-[12px] mono text-[#18232D]">{fmtPct(detail.credibility_score)}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Duplicate Score</div>
            <div className="text-[12px] mono" style={{ color: isDuplicate ? '#B84848' : '#18232D' }}>
              {fmtPct(detail.duplicate_score)}
              {isDuplicate && <span className="text-[9px] ml-1 text-[#B84848]">High duplicate</span>}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-[#7A8794]">Review Status</div>
            <div className="text-[12px] font-medium" style={{ color: vs }}>
              {VER_LABEL[detail.verification_status] || detail.verification_status}
            </div>
          </div>
        </div>

        {detail.credibility_reasons && detail.credibility_reasons.length > 0 && (
          <div className="mt-3">
            <div className="text-[10px] text-[#7A8794] mb-1">Credibility Reasons</div>
            <div className="space-y-1">
              {detail.credibility_reasons.map((r, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[10px] text-[#526170]">
                  <span className="text-[#477D96] mt-0.5">•</span>
                  <span>{r}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Canonical Event Link */}
      <div className="px-4 py-3 border-b border-[#EDEEF1]">
        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Canonical Event</div>
        {detail.canonical_event_id ? (
          <div className="bg-[#F8FAFB] border border-[#EDEEF1] rounded p-3">
            <div className="text-[10px] text-[#7A8794] mb-1">This report contributes to:</div>
            <div className="flex items-center gap-2 mb-1.5">
              <div className="w-[6px] h-[6px] rounded-full bg-[#477D96]" />
              <span className="text-[12px] font-medium text-[#18232D]">
                {CAT[detail.canonical_event_category] || detail.canonical_event_category || 'Unknown'}
              </span>
            </div>
            <div className="text-[10px] text-[#526170]">
              {detail.canonical_event_city || 'Unknown'} · {SEV_LABEL[detail.canonical_event_severity] || detail.canonical_event_severity || '—'}
            </div>
            <button
              onClick={() => navigate(`/events/${detail.canonical_event_id}`)}
              className="text-[11px] text-[#477D96] hover:text-[#3B6FA0] font-medium mt-2"
            >
              View Canonical Event →
            </button>
          </div>
        ) : (
          <div className="text-[11px] text-[#7A8794] italic">
            Not linked to a canonical event
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="px-4 py-3">
        <div className="text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase mb-2">Timestamps</div>
        <div className="space-y-1.5">
          <div className="flex justify-between text-[10px]">
            <span className="text-[#7A8794]">Created</span>
            <span className="mono text-[#526170]">{fmtTime(detail.created_at)}</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-[#7A8794]">Updated</span>
            <span className="mono text-[#526170]">{fmtTime(detail.updated_at)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Main Page
   ═══════════════════════════════════════════════════════════════ */

export default function ReportReview() {
  const navigate = useNavigate()
  const {
    reports, stats, total, totalPages, page, pageSize,
    filters, search, sortBy, sortOrder,
    selectedReport, selectedReportDetail,
    loading, detailLoading, error, lastUpdated,
    setFilters, clearFilters, setSearch, setPage, setSortBy, setSortOrder,
    selectReport, clearSelection, fetchReportDetail,
    startPolling, stopPolling,
  } = useReportReviewStore()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  useEffect(() => {
    if (selectedReport) {
      fetchReportDetail(selectedReport.report_id)
    }
  }, [selectedReport, fetchReportDetail])

  const activeFilterCount = Object.values(filters).filter(Boolean).length + (search ? 1 : 0)

  // Summary stats
  const summary = useMemo(() => {
    if (!stats) return null
    return {
      total: stats.total_reports ?? 0,
      needsReview: stats.by_verification_status?.needs_review ?? 0,
      duplicate: stats.by_verification_status?.duplicate ?? 0,
      pending: stats.by_verification_status?.pending ?? 0,
      verified: stats.by_verification_status?.verified ?? 0,
    }
  }, [stats])

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      {/* Unified Sidebar */}
      <Sidebar />

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 bg-white overflow-hidden">
        <Header />

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Left: Queue */}
          <div className="flex-1 overflow-y-auto px-5 py-4 min-w-0">
            {/* Title */}
            <div className="mb-4">
              <h1 className="text-[16px] font-semibold text-[#18232D] mb-0.5">Report Review</h1>
              <div className="text-[11px] text-[#7A8794]">
                Review individual source reports and their contribution to canonical weather events
                {lastUpdated && <span className="ml-3">Updated {ago(lastUpdated)}</span>}
              </div>
            </div>

            {/* Summary strip */}
            {summary && (
              <div className="flex gap-3 mb-4 flex-wrap">
                {[
                  { label: 'Reports in Queue', value: summary.total, color: '#2563EB', icon: '📋' },
                  { label: 'Needs Review', value: summary.needsReview, color: '#F59E0B', icon: '🔍' },
                  { label: 'Duplicate', value: summary.duplicate, color: '#64748B', icon: '📑' },
                  { label: 'Pending Queue', value: summary.pending, color: '#0284C7', icon: '⏳' },
                  { label: 'Reviewed & Verified', value: summary.verified, color: '#10B981', icon: '✓' },
                ].map(({ label, value, color, icon }) => (
                  <div key={label} className="card-white px-4 py-3 flex-1 min-w-[140px] border border-slate-200 shadow-2xs hover:shadow-sm transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">{label}</span>
                      <span className="text-xs">{icon}</span>
                    </div>
                    <div className="mono text-2xl font-extrabold tracking-tight" style={{ color }}>{value}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Filters */}
            <div className="mb-3 space-y-2">
              <div className="flex items-center gap-3">
                <div className="relative flex-1 max-w-md">
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search reports, sources, cities..."
                    className="w-full h-8 bg-white border border-[#D9E0E6] rounded px-3 text-[12px] text-[#18232D] placeholder:text-[#7A8794] focus:outline-none focus:border-[#477D96]/40"
                  />
                  {search && (
                    <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-[#7A8794] hover:text-[#18232D]">✕</button>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <div className="w-44">
                  <SelectDropdown
                    options={SOURCE_TYPES}
                    value={filters.source_type || ''}
                    onChange={(v) => setFilters({ source_type: v || null })}
                    placeholder="All Sources"
                    compact={true}
                  />
                </div>
                <div className="w-44">
                  <SelectDropdown
                    options={CATEGORIES}
                    value={filters.category || ''}
                    onChange={(v) => setFilters({ category: v || null })}
                    placeholder="All Categories"
                    compact={true}
                  />
                </div>
                <div className="w-40">
                  <SelectDropdown
                    options={SEVERITIES}
                    value={filters.severity || ''}
                    onChange={(v) => setFilters({ severity: v || null })}
                    placeholder="All Severities"
                    compact={true}
                  />
                </div>
                <div className="w-44">
                  <SelectDropdown
                    options={VERIFICATIONS}
                    value={filters.verification_status || ''}
                    onChange={(v) => setFilters({ verification_status: v || null })}
                    placeholder="All Status"
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
                <span className="text-xs text-slate-400 font-mono font-medium">{total.toLocaleString()} report{total !== 1 ? 's' : ''}</span>
              </div>
            </div>

            {/* Report table */}
            <div className="bg-white border border-[#D9E0E6] rounded-md overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-[#F8FAFB] border-b border-[#D9E0E6]">
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[14%]">Source</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[12%]">Type</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[13%]">Category</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[10%]">Location</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[8%]">Severity</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[8%]">Credibility</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[8%]">Duplicate</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[10%]">Status</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[12%]">Canonical</th>
                      <th className="px-3 py-2 text-[9px] font-semibold tracking-wider text-[#7A8794] uppercase w-[5%]"></th>
                    </tr>
                  </thead>

                  {loading && reports.length === 0 ? (
                    <tbody>
                      {Array.from({ length: 8 }).map((_, i) => (
                        <tr key={i} className="border-b border-[#EDEEF1]">
                          {Array.from({ length: 10 }).map((_, j) => (
                            <td key={j} className="px-3 py-3">
                              <div className="h-3.5 bg-[#E4E8EC] rounded animate-pulse" style={{ width: `${50 + Math.random() * 40}%` }} />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  ) : reports.length === 0 ? (
                    <tbody>
                      <tr>
                        <td colSpan={10} className="px-4 py-12 text-center">
                          <div className="text-[13px] font-semibold text-[#18232D] mb-1">
                            {activeFilterCount > 0 ? 'No reports match your filters' : 'No source reports available'}
                          </div>
                          <p className="text-[11px] text-[#7A8794] mb-3">
                            {activeFilterCount > 0 ? 'Try adjusting or clearing your filters.' : 'No ingestion records found in the database.'}
                          </p>
                          {activeFilterCount > 0 && (
                            <button onClick={clearFilters} className="text-[11px] text-[#477D96] hover:text-[#3B6FA0] font-medium">Clear all filters</button>
                          )}
                        </td>
                      </tr>
                    </tbody>
                  ) : (
                    <tbody>
                      {reports.map((r) => {
                        const isSelected = selectedReport?.report_id === r.report_id
                        const isHighDup = r.duplicate_score != null && r.duplicate_score >= 0.85
                        return (
                          <tr
                            key={r.report_id}
                            onClick={() => selectReport(r)}
                            className={`border-b border-[#EDEEF1] cursor-pointer transition-colors ${
                              isSelected ? 'bg-[#F0F4F7]' : 'hover:bg-[#F8FAFB]'
                            }`}
                            tabIndex={0}
                            onKeyDown={(ev) => { if (ev.key === 'Enter') selectReport(r) }}
                          >
                            <td className="px-3 py-2.5">
                              <div className="text-[11px] font-medium text-[#18232D]">{r.source_name || '—'}</div>
                              <div className="text-[9px] mono text-[#7A8794]">{r.source_id?.slice(0, 16)}</div>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="text-[10px] text-[#526170]">{SRC_TYPE_LABEL[r.source_type] || r.source_type}</span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="text-[11px] text-[#18232D]">{CAT[r.event_category] || r.event_category}</span>
                            </td>
                            <td className="px-3 py-2.5">
                              <div className="text-[11px] text-[#18232D]">{r.city || '—'}</div>
                              <div className="text-[9px] text-[#7A8794]">{r.state || ''}</div>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="text-[10px] font-medium" style={{ color: SEV_COLOR[r.severity] }}>
                                {SEV_LABEL[r.severity] || '—'}
                              </span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="text-[11px] mono text-[#526170]">{fmtPct(r.credibility_score)}</span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="text-[11px] mono" style={{ color: isHighDup ? '#B84848' : '#526170' }}>
                                {fmtPct(r.duplicate_score)}
                              </span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="inline-flex items-center gap-1.5 text-[10px] font-medium" style={{ color: VER_COLOR[r.verification_status] }}>
                                <span className="w-[4px] h-[4px] rounded-full" style={{ background: VER_COLOR[r.verification_status] }} />
                                {VER_LABEL[r.verification_status]}
                              </span>
                            </td>
                            <td className="px-3 py-2.5">
                              {r.canonical_event_id ? (
                                <button
                                  onClick={(e) => { e.stopPropagation(); navigate(`/events/${r.canonical_event_id}`) }}
                                  className="text-[10px] text-[#477D96] hover:text-[#3B6FA0] font-medium mono"
                                >
                                  {r.canonical_event_id.slice(0, 8)}…
                                </button>
                              ) : (
                                <span className="text-[10px] text-[#7A8794]">—</span>
                              )}
                            </td>
                            <td className="px-3 py-2.5 text-right">
                              <span className="text-[10px] text-[#477D96] hover:text-[#3B6FA0] font-medium">Review →</span>
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

            {/* Error banner */}
            {error && reports.length > 0 && (
              <div className="mt-2 px-3 py-2 bg-[#F8E7E7] border border-[#F8E7E7] rounded text-[11px] text-[#B84848]">
                Data refresh delayed. Last successful update: {lastUpdated ? ago(lastUpdated) : '—'}
              </div>
            )}
          </div>

          {/* Right: Detail Panel */}
          {selectedReport && (
            <ReportDetailPanel
              detail={selectedReportDetail}
              loading={detailLoading}
              onClose={clearSelection}
              navigate={navigate}
            />
          )}
        </div>
      </div>
    </div>
  )
}
