import React, { useEffect } from 'react'
import { Link, useLocation, Outlet } from 'react-router-dom'
import useAnalyticsStore from '../../stores/analyticsStore'
import Sidebar from '../../components/command-center/Sidebar'
import Header from '../../components/command-center/Header'
import SelectDropdown from '../../components/common/SelectDropdown'

const TIME_RANGES = [
  { value: '1h', label: 'Last 1h' },
  { value: '6h', label: 'Last 6h' },
  { value: '24h', label: 'Last 24h' },
  { value: '7d', label: 'Last 7d' },
  { value: 'all', label: 'All Time' },
]

const CATEGORIES = [
  { value: '', label: 'All Categories', icon: '🌐' },
  { value: 'heavy_rainfall', label: 'Heavy Rain', icon: '🌧️', subtitle: 'Monsoon deluge' },
  { value: 'rainfall', label: 'Rain', icon: '🌦️', subtitle: 'Precipitation' },
  { value: 'flood', label: 'Flood', icon: '🌊', subtitle: 'Hydrological' },
  { value: 'heatwave', label: 'Heatwave', icon: '🔥', subtitle: 'Thermal stress' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: '⛈️', subtitle: 'Convective storm' },
  { value: 'strong_wind', label: 'Strong Wind', icon: '💨', subtitle: 'Gale / Squall' },
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
  { value: 'verified', label: 'Verified', icon: '✓', status: 'Verified', statusColor: 'bg-emerald-50 text-emerald-700' },
  { value: 'pending', label: 'Pending', icon: '⏳', status: 'Pending', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'needs_review', label: 'Needs Review', icon: '🔍', status: 'Review', statusColor: 'bg-amber-50 text-amber-700' },
  { value: 'suspicious', label: 'Suspicious', icon: '⚠️', status: 'Flagged', statusColor: 'bg-rose-50 text-rose-700' },
]

export default function AnalyticsLayout() {
  const location = useLocation()
  const {
    filters, timeRange, lastUpdated,
    setFilters, clearFilters, setTimeRange, startPolling, stopPolling,
  } = useAnalyticsStore()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  const activeFilterCount = Object.values(filters).filter(Boolean).length + (timeRange !== '24h' ? 1 : 0)

  const analyticsLinks = [
    { name: 'Event Trends', href: '/analytics/events', icon: '📈', desc: 'Temporal anomalies' },
    { name: 'Geographic Analysis', href: '/analytics/geographic', icon: '🗺️', desc: 'Regional distribution' },
    { name: 'Source Intelligence', href: '/analytics/sources', icon: '📡', desc: 'Sensor triangulation' },
  ]

  const isActive = (href) => location.pathname === href

  return (
    <div className="flex min-h-screen bg-white">
      {/* Unified Sidebar */}
      <Sidebar />

      {/* Main Area */}
      <div className="flex flex-col flex-1 min-w-0 bg-white">
        {/* Unified Header */}
        <Header />

        {/* Analytics Sub-Nav and Filter Bar */}
        <div className="px-4 lg:px-6 py-2.5 border-b border-slate-200/80 bg-white flex-shrink-0 space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            {/* Section 8: Premium Navigation Tabs */}
            <div className="flex items-center gap-1.5 p-1 bg-slate-100/70 rounded-2xl border border-slate-200/80 overflow-x-auto scrollbar-none flex-nowrap w-full sm:w-fit">
              {analyticsLinks.map((tab) => {
                const active = isActive(tab.href)
                return (
                  <Link
                    key={tab.name}
                    to={tab.href}
                    className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all duration-150 whitespace-nowrap ${
                      active
                        ? 'bg-white text-brand-blue-700 shadow-xs border border-slate-200/80 ring-1 ring-slate-900/5'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-white/60 border border-transparent'
                    }`}
                  >
                    <span className="text-sm">{tab.icon}</span>
                    <span>{tab.name}</span>
                    {active && (
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-blue-600 ml-0.5 animate-pulse" />
                    )}
                  </Link>
                )
              })}
            </div>

            {/* Freshness Timestamp */}
            {lastUpdated && (
              <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono self-end sm:self-center">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>Updated {new Date(lastUpdated).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}</span>
              </div>
            )}
          </div>

          {/* Section 2 & 4: Filters Row with Universal Dropdowns */}
          <div className="flex items-center gap-2 flex-wrap pt-1 border-t border-slate-100">
            {/* Time range pills */}
            <div className="flex items-center gap-1 bg-slate-50 rounded-xl border border-slate-200 p-0.5 shadow-2xs">
              {TIME_RANGES.map((tr) => (
                <button
                  key={tr.value}
                  type="button"
                  onClick={() => setTimeRange(tr.value)}
                  className={`px-2.5 py-1 text-xs rounded-lg font-bold transition-all ${
                    timeRange === tr.value
                      ? 'bg-brand-blue-600 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {tr.label}
                </button>
              ))}
            </div>

            {/* Category Dropdown */}
            <div className="w-44">
              <SelectDropdown
                options={CATEGORIES}
                value={filters.category || ''}
                onChange={(v) => setFilters({ category: v || null })}
                placeholder="All Categories"
                compact={true}
              />
            </div>

            {/* Severity Dropdown */}
            <div className="w-40">
              <SelectDropdown
                options={SEVERITIES}
                value={filters.severity || ''}
                onChange={(v) => setFilters({ severity: v || null })}
                placeholder="All Severities"
                compact={true}
              />
            </div>

            {/* Verification Dropdown */}
            <div className="w-40">
              <SelectDropdown
                options={VERIFICATIONS}
                value={filters.verification_status || ''}
                onChange={(v) => setFilters({ verification_status: v || null })}
                placeholder="All Status"
                compact={true}
              />
            </div>

            {/* Clear Button */}
            {activeFilterCount > 0 && (
              <button
                type="button"
                onClick={clearFilters}
                className="h-8 px-2.5 text-xs text-rose-600 hover:text-rose-700 font-bold bg-rose-50 border border-rose-200 rounded-xl shadow-xs transition-colors"
              >
                Clear ({activeFilterCount})
              </button>
            )}
          </div>
        </div>

        {/* Content Outlet */}
        <div className="flex-1 px-4 lg:px-6 py-4 bg-white">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
