import React, { useEffect, useMemo } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Bar, Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, Title, Tooltip, Legend, Filler,
} from 'chart.js'
import useAnalyticsStore from '../../stores/analyticsStore'

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend, Filler)

/* ═══════════════════════════════════════════════════════════════
   Section 11: Bright, High-Contrast Analytics Palette
   ═══════════════════════════════════════════════════════════════ */

const CAT = {
  heavy_rainfall: 'Heavy Rain', rainfall: 'Rain', flood: 'Flood',
  heatwave: 'Heatwave', thunderstorm: 'Thunderstorm', lightning: 'Lightning',
  strong_wind: 'Strong Wind', hailstorm: 'Hail', dust_storm: 'Dust Storm',
  cyclone: 'Cyclone', fog: 'Fog',
}

const CAT_ICONS = {
  heavy_rainfall: '🌧️', rainfall: '🌦️', flood: '🌊',
  heatwave: '🔥', thunderstorm: '⛈️', lightning: '⚡',
  strong_wind: '💨', hailstorm: '🌨️', dust_storm: '🌪️',
  cyclone: '🌀', fog: '🌫️',
}

const CAT_COLOR = {
  heavy_rainfall: '#2563EB', // Bright Blue
  rainfall: '#06B6D4',       // Cyan
  flood: '#1D4ED8',          // Deep Azure
  heatwave: '#F97316',       // Bright Orange
  thunderstorm: '#DC2626',   // Bright Red
  lightning: '#F59E0B',      // Amber
  strong_wind: '#64748B',    // Slate
  hailstorm: '#14B8A6',      // Teal
  dust_storm: '#D97706',     // Saffron
  cyclone: '#B91C1C',        // Crimson
  fog: '#94A3B8',            // Light Slate
}

const SEV_COLOR = {
  low: '#64748B',      // Slate
  moderate: '#2563EB', // Bright Blue
  high: '#F59E0B',     // Amber
  extreme: '#DC2626',  // Red
  critical: '#DC2626', // Red
}

const VER_COLOR = {
  verified: '#10B981',   // Emerald
  pending: '#F59E0B',    // Amber
  needs_review: '#F97316',// Orange
  suspicious: '#DC2626',  // Red
  duplicate: '#94A3B8',  // Slate
}

const VER_LABEL = {
  verified: 'Verified', pending: 'Pending', needs_review: 'Needs Review',
  suspicious: 'Suspicious', duplicate: 'Duplicate',
}

// Section 11: Bright analytics progression: Blue, Cyan, Green, Orange, Purple, Pink, Yellow, Teal
const CHART_COLORS = [
  '#2563EB', '#06B6D4', '#10B981', '#F97316',
  '#8B5CF6', '#EC4899', '#F59E0B', '#14B8A6',
  '#3B82F6', '#6366F1',
]

function ago(iso) {
  if (!iso) return ''
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function ChartCard({ title, icon = '📊', children, className = '' }) {
  return (
    <div className={`card-white overflow-hidden ${className}`}>
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">{icon}</span>
          <span className="text-xs font-bold tracking-tight text-slate-800 uppercase">{title}</span>
        </div>
        <span className="text-[10px] font-mono text-slate-400">Telemetry Stream</span>
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
      callbacks: {
        label: (context) => ` Value: ${context.parsed.y ?? context.parsed.x}`,
      },
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

const LINE_OPTS = {
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
   Event Trends Page
   ═══════════════════════════════════════════════════════════════ */

export default function EventTrends() {
  const {
    stats, events,
    startPolling, stopPolling,
    lastUpdated,
  } = useAnalyticsStore()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  // ── Event volume over time ──
  const timeSeriesData = useMemo(() => {
    const ot = stats?.events_over_time || []
    if (ot.length === 0) return null
    return {
      labels: ot.map((d) => d.date),
      datasets: [{
        label: 'Canonical Events',
        data: ot.map((d) => d.count),
        borderColor: '#2563EB',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: '#2563EB',
        pointBorderColor: '#FFFFFF',
        pointBorderWidth: 2,
      }],
    }
  }, [stats])

  // ── Category distribution with bright bar colors ──
  const categoryData = useMemo(() => {
    const bc = stats?.by_category || {}
    const entries = Object.entries(bc).sort((a, b) => b[1] - a[1])
    if (entries.length === 0) return null
    return {
      labels: entries.map(([k]) => CAT[k] || k),
      datasets: [{
        label: 'Canonical Events',
        data: entries.map(([, v]) => v),
        backgroundColor: entries.map(([k], i) => CAT_COLOR[k] || CHART_COLORS[i % CHART_COLORS.length]),
        borderRadius: 6,
        barThickness: 28,
        hoverBackgroundColor: '#1D4ED8',
      }],
    }
  }, [stats])

  // ── Severity distribution with semantic bright colors ──
  const severityData = useMemo(() => {
    const bs = stats?.by_severity || {}
    const order = ['low', 'moderate', 'high', 'extreme', 'critical']
    const entries = order.filter((k) => bs[k] !== undefined).map((k) => [k, bs[k]])
    if (entries.length === 0) return null
    return {
      labels: entries.map(([k]) => k.charAt(0).toUpperCase() + k.slice(1)),
      datasets: [{
        label: 'Canonical Events',
        data: entries.map(([, v]) => v),
        backgroundColor: entries.map(([k]) => SEV_COLOR[k]),
        borderRadius: 6,
        barThickness: 32,
        hoverBackgroundColor: '#0F172A',
      }],
    }
  }, [stats])

  // ── Verification distribution ──
  const verificationData = useMemo(() => {
    const bv = stats?.by_verification_status || {}
    const entries = Object.entries(bv).sort((a, b) => b[1] - a[1])
    if (entries.length === 0) return null
    return {
      labels: entries.map(([k]) => VER_LABEL[k] || k),
      datasets: [{
        label: 'Canonical Events',
        data: entries.map(([, v]) => v),
        backgroundColor: entries.map(([k]) => VER_COLOR[k] || '#94A3B8'),
        borderRadius: 6,
        barThickness: 32,
      }],
    }
  }, [stats])

  // ── Category trend over time (stacked) ──
  const categoryTrendData = useMemo(() => {
    if (!events || events.length === 0) return null
    const cats = new Set()
    const dateMap = {}
    for (const e of events) {
      const date = e.event_timestamp ? new Date(e.event_timestamp).toLocaleDateString('en-CA') : 'unknown'
      if (!dateMap[date]) dateMap[date] = {}
      dateMap[date][e.event_category] = (dateMap[date][e.event_category] || 0) + 1
      cats.add(e.event_category)
    }
    const dates = Object.keys(dateMap).sort()
    const catList = [...cats]
    if (dates.length === 0 || catList.length === 0) return null

    return {
      labels: dates,
      datasets: catList.map((cat, i) => ({
        label: CAT[cat] || cat,
        data: dates.map((d) => dateMap[d][cat] || 0),
        backgroundColor: CAT_COLOR[cat] || CHART_COLORS[i % CHART_COLORS.length],
        borderRadius: 4,
      })),
    }
  }, [events])

  return (
    <div className="space-y-4 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-extrabold text-slate-900 tracking-tight">
              Event Trend Analytics
            </h1>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              Temporal Radar
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Temporal patterns and phenomenon concentration across the national atmospheric pipeline
          </p>
        </div>
        {lastUpdated && (
          <span className="text-xs text-slate-400 font-mono self-start sm:self-auto">
            Synced {ago(lastUpdated)}
          </span>
        )}
      </div>

      {/* Summary KPI Cards (Section 16) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Total Events', value: stats?.total_events ?? 0, icon: '⚡', color: '#2563EB', badge: 'Active Stream', badgeStyle: 'bg-blue-50 text-blue-700 border-blue-200' },
          { label: 'Categories', value: Object.keys(stats?.by_category || {}).length, icon: '🌧️', color: '#06B6D4', badge: 'Phenomena', badgeStyle: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
          { label: 'Active Hubs', value: '3 Cities', icon: '📍', color: '#10B981', badge: 'MVP Live', badgeStyle: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
          { label: 'Avg Credibility', value: stats?.average_credibility_score != null ? `${Math.round(stats.average_credibility_score * 100)}%` : '—', icon: '🛡️', color: '#8B5CF6', badge: 'Verified Grid', badgeStyle: 'bg-purple-50 text-purple-700 border-purple-200' },
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

      {/* Charts Grid (Section 11 & 12: Bright Bars, Rounded Corners) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Event Volume Over Time */}
        <ChartCard title="Event Volume Over Time" icon="📈">
          <div className="h-[240px]">
            {timeSeriesData ? (
              <Line data={timeSeriesData} options={LINE_OPTS} />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No time-series data available for selected period
              </div>
            )}
          </div>
        </ChartCard>

        {/* Category Distribution */}
        <ChartCard title="Events by Category" icon="🌧️">
          <div className="h-[240px]">
            {categoryData ? (
              <Bar data={categoryData} options={BAR_OPTS} />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No category data available
              </div>
            )}
          </div>
        </ChartCard>

        {/* Severity Distribution */}
        <ChartCard title="Events by Severity Scale" icon="⚡">
          <div className="h-[240px]">
            {severityData ? (
              <Bar data={severityData} options={BAR_OPTS} />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No severity data available
              </div>
            )}
          </div>
        </ChartCard>

        {/* Verification Distribution */}
        <ChartCard title="Events by Verification Status" icon="🛡️">
          <div className="h-[240px]">
            {verificationData ? (
              <Bar data={verificationData} options={BAR_OPTS} />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No verification data available
              </div>
            )}
          </div>
        </ChartCard>
      </div>

      {/* Category Trend Over Time (Stacked) */}
      {categoryTrendData && (
        <ChartCard title="Multi-Phenomenon Composition Over Time" icon="📊">
          <div className="h-[260px]">
            <Bar
              data={categoryTrendData}
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
          </div>
        </ChartCard>
      )}
    </div>
  )
}
