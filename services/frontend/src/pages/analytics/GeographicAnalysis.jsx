import React, { useEffect, useMemo } from 'react'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend,
} from 'chart.js'
import useAnalyticsStore from '../../stores/analyticsStore'
import { ACTIVE_CITIES } from '../../constants/cities'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

/* ═══════════════════════════════════════════════════════════════
   Section 11: Bright, High-Contrast Analytics Palette
   ═══════════════════════════════════════════════════════════════ */

const CAT = {
  heavy_rainfall: 'Heavy Rain', rainfall: 'Rain', flood: 'Flood',
  heatwave: 'Heatwave', thunderstorm: 'Thunderstorm', lightning: 'Lightning',
  strong_wind: 'Strong Wind', hailstorm: 'Hail', dust_storm: 'Dust Storm',
  cyclone: 'Cyclone', fog: 'Fog',
}

const CAT_COLOR = {
  heavy_rainfall: '#2563EB',
  rainfall: '#06B6D4',
  flood: '#1D4ED8',
  heatwave: '#F97316',
  thunderstorm: '#DC2626',
  lightning: '#F59E0B',
  strong_wind: '#64748B',
  hailstorm: '#14B8A6',
  dust_storm: '#D97706',
  cyclone: '#B91C1C',
  fog: '#94A3B8',
}

const SEV_COLOR = {
  low: '#64748B',
  moderate: '#2563EB',
  high: '#F59E0B',
  extreme: '#DC2626',
  critical: '#DC2626',
}

const VER_COLOR = {
  verified: '#10B981',
  pending: '#F59E0B',
  needs_review: '#F97316',
  suspicious: '#DC2626',
  duplicate: '#94A3B8',
}

const VER_LABEL = {
  verified: 'Verified', pending: 'Pending', needs_review: 'Needs Review',
  suspicious: 'Suspicious', duplicate: 'Duplicate',
}

const CITY_COLORS = {
  Mumbai: '#0284C7',
  Nagpur: '#EA580C',
  Nasik: '#059669',
  Nashik: '#059669',
}

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

function ChartCard({ title, icon = '🗺️', children, className = '' }) {
  return (
    <div className={`card-white overflow-hidden ${className}`}>
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">{icon}</span>
          <span className="text-xs font-bold tracking-tight text-slate-800 uppercase">{title}</span>
        </div>
        <span className="text-[10px] font-mono text-slate-400">GIS Telemetry</span>
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
  indexAxis: 'y',
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
      grid: { color: '#F1F5F9' },
      ticks: { font: { family: 'IBM Plex Mono', size: 10 }, color: '#94A3B8', stepSize: 1 },
      beginAtZero: true,
    },
    y: {
      grid: { display: false },
      ticks: { font: { family: 'Plus Jakarta Sans', size: 11, weight: '700' }, color: '#0F172A' },
    },
  },
}

const STACKED_BAR_OPTS = {
  ...BAR_OPTS,
  indexAxis: 'x',
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
    x: { ...BAR_OPTS.scales.y, stacked: true },
    y: { ...BAR_OPTS.scales.x, stacked: true, indexAxis: undefined },
  },
}

/* ═══════════════════════════════════════════════════════════════
   Geographic Analysis Page
   ═══════════════════════════════════════════════════════════════ */

export default function GeographicAnalysis() {
  const { events, stats, lastUpdated } = useAnalyticsStore()

  // ── City event count with bright distinct colors ──
  const cityData = useMemo(() => {
    const bc = stats?.by_city || {}
    const entries = Object.entries(bc).sort((a, b) => b[1] - a[1])
    if (entries.length === 0) return null
    return {
      labels: entries.map(([k]) => k),
      datasets: [{
        label: 'Canonical Events',
        data: entries.map(([, v]) => v),
        backgroundColor: entries.map(([k]) => CITY_COLORS[k] || '#2563EB'),
        borderRadius: 6,
        barThickness: 26,
      }],
    }
  }, [stats])

  // ── Category by City (grouped bar) ──
  const categoryByCityData = useMemo(() => {
    if (!events || events.length === 0) return null
    const cityCat = {}
    const cats = new Set()
    for (const e of events) {
      const city = e.city || 'Unknown'
      if (!cityCat[city]) cityCat[city] = {}
      cityCat[city][e.event_category] = (cityCat[city][e.event_category] || 0) + 1
      cats.add(e.event_category)
    }
    const cities = Object.keys(cityCat).sort((a, b) => {
      const totalA = Object.values(cityCat[a]).reduce((s, v) => s + v, 0)
      const totalB = Object.values(cityCat[b]).reduce((s, v) => s + v, 0)
      return totalB - totalA
    })
    const catList = [...cats]
    if (cities.length === 0 || catList.length === 0) return null

    return {
      labels: cities,
      datasets: catList.map((cat, i) => ({
        label: CAT[cat] || cat,
        data: cities.map((c) => cityCat[c][cat] || 0),
        backgroundColor: CAT_COLOR[cat] || CHART_COLORS[i % CHART_COLORS.length],
        borderRadius: 4,
      })),
    }
  }, [events])

  // ── Severity by City (stacked bar) ──
  const severityByCityData = useMemo(() => {
    if (!events || events.length === 0) return null
    const citySev = {}
    const sevs = ['low', 'moderate', 'high', 'extreme', 'critical']
    for (const e of events) {
      const city = e.city || 'Unknown'
      if (!citySev[city]) citySev[city] = {}
      citySev[city][e.severity] = (citySev[city][e.severity] || 0) + 1
    }
    const cities = Object.keys(citySev).sort((a, b) => {
      const totalA = Object.values(citySev[a]).reduce((s, v) => s + v, 0)
      const totalB = Object.values(citySev[b]).reduce((s, v) => s + v, 0)
      return totalB - totalA
    })
    const activeSevs = sevs.filter((s) => events.some((e) => e.severity === s))
    if (cities.length === 0 || activeSevs.length === 0) return null

    return {
      labels: cities,
      datasets: activeSevs.map((sev) => ({
        label: sev.charAt(0).toUpperCase() + sev.slice(1),
        data: cities.map((c) => citySev[c][sev] || 0),
        backgroundColor: SEV_COLOR[sev],
        borderRadius: 4,
      })),
    }
  }, [events])

  // ── Verification by City (stacked bar) ──
  const verificationByCityData = useMemo(() => {
    if (!events || events.length === 0) return null
    const cityVer = {}
    for (const e of events) {
      const city = e.city || 'Unknown'
      if (!cityVer[city]) cityVer[city] = {}
      cityVer[city][e.verification_status] = (cityVer[city][e.verification_status] || 0) + 1
    }
    const cities = Object.keys(cityVer).sort((a, b) => {
      const totalA = Object.values(cityVer[a]).reduce((s, v) => s + v, 0)
      const totalB = Object.values(cityVer[b]).reduce((s, v) => s + v, 0)
      return totalB - totalA
    })
    const allStatuses = [...new Set(events.map((e) => e.verification_status))]
    if (cities.length === 0 || allStatuses.length === 0) return null

    return {
      labels: cities,
      datasets: allStatuses.map((status) => ({
        label: VER_LABEL[status] || status,
        data: cities.map((c) => cityVer[c][status] || 0),
        backgroundColor: VER_COLOR[status] || '#94A3B8',
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
              Geographic Intelligence
            </h1>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              3-Hub Corridor Live
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Spatial distribution and atmospheric concentration across active hubs (Mumbai, Nagpur, Nashik)
          </p>
        </div>
        {lastUpdated && (
          <span className="text-xs text-slate-400 font-mono self-start sm:self-auto">
            Synced {ago(lastUpdated)}
          </span>
        )}
      </div>

      {/* 3-City MVP Live Banner */}
      <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-2xs">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
          <div>
            <div className="text-xs font-bold text-slate-800">
              Active Urban Corridors: Mumbai, Nagpur & Nashik
            </div>
            <div className="text-[11px] text-slate-500">
              High-frequency multi-sensor coverage and Doppler fusion is currently operational across 3 core hubs.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
            Phase II: +15 Cities Updated Soon
          </span>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { label: 'Active Hubs Covered', value: `${Object.keys(stats?.by_city || {}).length} Hubs`, icon: '🏙️', color: '#2563EB', desc: 'Live Telemetry' },
          { label: 'Highest Atmospheric Volume', value: Object.entries(stats?.by_city || {}).sort((a, b) => b[1] - a[1])[0]?.[0] || 'Mumbai', icon: '📍', color: '#EA580C', desc: 'Precipitation Epicenter' },
          { label: 'Total Regional Events', value: stats?.total_events ?? 0, icon: '⚡', color: '#0F172A', desc: 'Validated Detections' },
        ].map(({ label, value, icon, color, desc }) => (
          <div key={label} className="card-white p-3.5 space-y-1 border border-slate-200 shadow-2xs hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">{label}</span>
              <span className="text-base">{icon}</span>
            </div>
            <div className="font-mono text-2xl font-extrabold tracking-tight" style={{ color }}>{value}</div>
            <div className="text-[11px] text-slate-500 font-medium">{desc}</div>
          </div>
        ))}
      </div>

      {/* City Distribution (Horizontal Bar with custom hub colors) */}
      <ChartCard title="Atmospheric Events by Active City" icon="📍">
        <div className="h-[220px]">
          {cityData ? (
            <Bar data={cityData} options={BAR_OPTS} />
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              No city telemetry available
            </div>
          )}
        </div>
      </ChartCard>

      {/* Category by City */}
      <ChartCard title="Category Distribution by Urban Corridor" icon="🌧️">
        <div className="h-[250px]">
          {categoryByCityData ? (
            <Bar data={categoryByCityData} options={STACKED_BAR_OPTS} />
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              No category-by-city data available
            </div>
          )}
        </div>
      </ChartCard>

      {/* Severity + Verification Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Severity Composition by Hub" icon="⚡">
          <div className="h-[240px]">
            {severityByCityData ? (
              <Bar data={severityByCityData} options={STACKED_BAR_OPTS} />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No severity-by-city data available
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard title="Verification Distribution by Hub" icon="🛡️">
          <div className="h-[240px]">
            {verificationByCityData ? (
              <Bar data={verificationByCityData} options={STACKED_BAR_OPTS} />
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No verification-by-city data available
              </div>
            )}
          </div>
        </ChartCard>
      </div>
    </div>
  )
}
