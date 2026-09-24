import React, { useEffect, useMemo } from 'react'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend,
} from 'chart.js'
import useAnalyticsStore from '../../stores/analyticsStore'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

/* ═══════════════════════════════════════════════════════════════
   Section 11: Bright, High-Contrast Analytics Palette
   ═══════════════════════════════════════════════════════════════ */

const VER_COLOR = {
  verified: '#10B981',    // Emerald
  pending: '#F59E0B',     // Amber
  needs_review: '#F97316', // Orange
  suspicious: '#DC2626',   // Red
  duplicate: '#94A3B8',   // Slate
}

const VER_LABEL = {
  verified: 'Verified', pending: 'Pending', needs_review: 'Needs Review',
  suspicious: 'Suspicious', duplicate: 'Duplicate',
}

const SRC_TYPE_LABEL = {
  weather_api: 'Open-Meteo Synoptic AWS',
  synoptic_telemetry: 'Open-Meteo Synoptic Telemetry',
  reanalysis_archive: 'ECMWF ERA5 Reanalysis',
  government_dataset: 'Data.gov.in Open Data',
  government_warning: 'NDMA SACHET Disaster Warning',
  open_government_data: 'Data.gov.in Open Data',
  website: 'NDMA SACHET Portal',
  rss: 'GDACS Global Disaster System',
  global_alert: 'GDACS Global Disaster System',
  citizen: 'Citizen Reports (Mastodon)',
  citizen_report: 'Citizen Reports (Mastodon)',
  social: 'Social Reports (Mastodon)',
  social_media: 'Social Reports (Mastodon)',
  simulated_social: 'Citizen Reports (Mastodon)',
  synthetic: 'Open-Meteo Synoptic AWS',
  canonical: 'Consolidated Meteorological Event',
}

const SRC_COLORS = [
  '#2563EB', '#06B6D4', '#10B981', '#F97316',
  '#8B5CF6', '#EC4899', '#F59E0B', '#14B8A6',
]

function ago(iso) {
  if (!iso) return ''
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function ChartCard({ title, icon = '📡', children, className = '' }) {
  return (
    <div className={`card-white overflow-hidden ${className}`}>
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">{icon}</span>
          <span className="text-xs font-bold tracking-tight text-slate-800 uppercase">{title}</span>
        </div>
        <span className="text-[10px] font-mono text-slate-400">Sensor Verification</span>
      </div>
      <div className="p-4 bg-white">{children}</div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Section 12: Graph Bar Design & Clean Tooltip Styling
   ═══════════════════════════════════════════════════════════════ */

const BAR_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#FFFFFF',
      titleColor: '#0F172A',
      bodyColor: '#334155',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      padding: 10,
      cornerRadius: 8,
      titleFont: { family: 'Plus Jakarta Sans', size: 12, weight: '700' },
      bodyFont: { family: 'Plus Jakarta Sans', size: 11, weight: '500' },
      boxPadding: 4,
      usePointStyle: true,
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' }, color: '#64748B' },
    },
    y: {
      grid: { color: '#F1F5F9' },
      ticks: { font: { family: 'IBM Plex Mono', size: 10 }, color: '#94A3B8', stepSize: 1 },
      beginAtZero: true,
    },
  },
}

/* ═══════════════════════════════════════════════════════════════
   Source Intelligence Page
   ═══════════════════════════════════════════════════════════════ */

export default function SourceIntelligence() {
  const { events, stats, lastUpdated, startPolling, stopPolling } = useAnalyticsStore()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  // ── Source type distribution (canonical events) with bright bars ──
  const sourceTypeData = useMemo(() => {
    if (!events || events.length === 0) return null
    const typeCounts = {}
    for (const e of events) {
      const srcType = e.source_type || 'unknown'
      typeCounts[srcType] = (typeCounts[srcType] || 0) + 1
    }
    const entries = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])
    if (entries.length === 0) return null

    return {
      labels: entries.map(([k]) => SRC_TYPE_LABEL[k] || k),
      datasets: [{
        label: 'Canonical Events',
        data: entries.map(([, v]) => v),
        backgroundColor: entries.map((_, i) => SRC_COLORS[i % SRC_COLORS.length]),
        borderRadius: 6,
        barThickness: 32,
      }],
    }
  }, [events])

  // ── Verification by source type with semantic bright colors ──
  const verificationBySourceData = useMemo(() => {
    if (!events || events.length === 0) return null
    const srcVer = {}
    for (const e of events) {
      const srcType = e.source_type || 'unknown'
      if (!srcVer[srcType]) srcVer[srcType] = {}
      srcVer[srcType][e.verification_status] = (srcVer[srcType][e.verification_status] || 0) + 1
    }
    const srcTypes = Object.keys(srcVer).sort((a, b) => {
      const totalA = Object.values(srcVer[a]).reduce((s, v) => s + v, 0)
      const totalB = Object.values(srcVer[b]).reduce((s, v) => s + v, 0)
      return totalB - totalA
    })
    const allStatuses = [...new Set(events.map((e) => e.verification_status))]
    if (srcTypes.length === 0 || allStatuses.length === 0) return null

    return {
      labels: srcTypes.map((k) => SRC_TYPE_LABEL[k] || k),
      datasets: allStatuses.map((status) => ({
        label: VER_LABEL[status] || status,
        data: srcTypes.map((s) => srcVer[s][status] || 0),
        backgroundColor: VER_COLOR[status] || '#94A3B8',
        borderRadius: 4,
      })),
    }
  }, [events])

  // ── Credibility by source with semantic performance colors ──
  const credibilityData = useMemo(() => {
    if (!events || events.length === 0) return null
    const srcCred = {}
    for (const e of events) {
      const srcType = e.source_type || 'unknown'
      if (!srcCred[srcType]) srcCred[srcType] = { total: 0, count: 0 }
      if (e.credibility_score != null) {
        srcCred[srcType].total += e.credibility_score
        srcCred[srcType].count++
      }
    }
    const entries = Object.entries(srcCred)
      .filter(([, v]) => v.count > 0)
      .map(([k, v]) => [k, v.total / v.count])
      .sort((a, b) => b[1] - a[1])

    if (entries.length === 0) return null

    return {
      labels: entries.map(([k]) => SRC_TYPE_LABEL[k] || k),
      datasets: [{
        label: 'Observed Credibility Score (%)',
        data: entries.map(([, v]) => Math.round(v * 100)),
        backgroundColor: entries.map(([, v]) => v >= 0.7 ? '#10B981' : v >= 0.4 ? '#F59E0B' : '#DC2626'),
        borderRadius: 6,
        barThickness: 32,
      }],
    }
  }, [events])

  // ── Source contribution: Canonical Events vs Reports by City ──
  const sourceContributionData = useMemo(() => {
    if (!events || events.length === 0) return null
    const citySrc = {}
    for (const e of events) {
      const city = e.city || 'Unknown'
      if (!citySrc[city]) citySrc[city] = { reports: 0, sources: 0 }
      citySrc[city].reports += (e.report_count || 1)
      citySrc[city].sources += (e.source_count || 1)
    }
    const cities = Object.keys(citySrc).sort((a, b) => citySrc[b].reports - citySrc[a].reports)
    if (cities.length === 0) return null

    return {
      labels: cities,
      datasets: [
        {
          label: 'Canonical Consolidated Events',
          data: cities.map((c) => events.filter((e) => e.city === c).length),
          backgroundColor: '#2563EB',
          borderRadius: 6,
        },
        {
          label: 'Raw Contributing Reports',
          data: cities.map((c) => citySrc[c].reports),
          backgroundColor: '#06B6D4',
          borderRadius: 6,
        },
      ],
    }
  }, [events])

  return (
    <div className="space-y-4 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-extrabold text-slate-900 tracking-tight">
              Source Intelligence Analytics
            </h1>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200">
              Multi-Source Triangulation
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Information source distribution, verification outcomes, and automated credibility scoring
          </p>
        </div>
        {lastUpdated && (
          <span className="text-xs text-slate-400 font-mono self-start sm:self-auto">
            Synced {ago(lastUpdated)}
          </span>
        )}
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Canonical Events', value: stats?.total_events ?? 0, icon: '⚡', color: '#2563EB', badge: 'Synthesized', badgeStyle: 'bg-blue-50 text-blue-700 border-blue-200' },
          { label: 'Source Ingestion Types', value: Object.keys(stats?.by_source_type || {}).length || 1, icon: '📡', color: '#06B6D4', badge: 'Active Channels', badgeStyle: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
          { label: 'Avg Credibility Score', value: stats?.average_credibility_score != null ? `${Math.round(stats.average_credibility_score * 100)}%` : '—', icon: '🛡️', color: '#10B981', badge: 'Quality Index', badgeStyle: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
          { label: 'Corridors Monitored', value: '3 Cities', icon: '📍', color: '#8B5CF6', badge: 'Live Scope', badgeStyle: 'bg-purple-50 text-purple-700 border-purple-200' },
        ].map(({ label, value, icon, color, badge, badgeStyle }) => (
          <div
            key={label}
            className="card-white p-3.5 space-y-2 border border-slate-200 shadow-2xs hover:shadow-sm transition-all"
          >
            <div className="flex items-center justify-between">
              <span className="text-base">{icon}</span>
              <span className={`text-[9.5px] font-bold px-1.5 py-0.2 rounded border uppercase tracking-wider ${badgeStyle}`}>
                {badge}
              </span>
            </div>
            <div>
              <div className="mono text-2xl font-extrabold tracking-tight" style={{ color }}>
                {value}
              </div>
              <div className="text-xs font-bold text-slate-600 mt-0.5">{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Source Type Distribution */}
        <ChartCard title="Canonical Events by Source Type" icon="📡">
          <div className="h-[240px]">
            {sourceTypeData ? (
              <Bar data={sourceTypeData} options={BAR_OPTS} />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No source type data available
              </div>
            )}
          </div>
        </ChartCard>

        {/* Source Contribution: Events vs Reports by City */}
        <ChartCard title="Consolidated Events vs Contributing Reports by City" icon="🏙️">
          <div className="h-[240px]">
            {sourceContributionData ? (
              <Bar
                data={sourceContributionData}
                options={{
                  ...BAR_OPTS,
                  plugins: {
                    ...BAR_OPTS.plugins,
                    legend: {
                      display: true,
                      position: 'top',
                      labels: {
                        font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
                        boxWidth: 12,
                        padding: 12,
                        usePointStyle: true,
                      },
                    },
                  },
                }}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No source contribution data available
              </div>
            )}
          </div>
        </ChartCard>

        {/* Verification by Source */}
        <ChartCard title="Verification Status by Source Type" icon="🛡️">
          <div className="h-[240px]">
            {verificationBySourceData ? (
              <Bar
                data={verificationBySourceData}
                options={{
                  ...BAR_OPTS,
                  plugins: {
                    ...BAR_OPTS.plugins,
                    legend: {
                      display: true,
                      position: 'top',
                      labels: {
                        font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
                        boxWidth: 12,
                        padding: 12,
                        usePointStyle: true,
                      },
                    },
                  },
                  scales: {
                    ...BAR_OPTS.scales,
                    x: { ...BAR_OPTS.scales.x, stacked: true },
                    y: { ...BAR_OPTS.scales.y, stacked: true },
                  },
                }}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No verification-by-source data available
              </div>
            )}
          </div>
        </ChartCard>

        {/* Credibility Score by Source */}
        <ChartCard title="Automated Credibility Score by Source Type" icon="✨">
          <div className="h-[240px]">
            {credibilityData ? (
              <Bar data={credibilityData} options={BAR_OPTS} />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No credibility data available
              </div>
            )}
          </div>
        </ChartCard>
      </div>
    </div>
  )
}
