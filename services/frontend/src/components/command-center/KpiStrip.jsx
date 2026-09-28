import React from 'react'
import { useNavigate } from 'react-router-dom'

function formatNumber(n) {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString()
}

function KpiCard({
  label,
  value,
  sub,
  color,
  badgeText,
  badgeBg,
  badgeColor,
  icon,
  onClick,
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick?.()
        }
      }}
      aria-label={`${label}: ${formatNumber(value)}. Click to view filtered live events.`}
      className="card-white p-3.5 sm:p-4 rounded-2xl flex flex-col justify-between min-w-0 cursor-pointer transition-all duration-200 shadow-xs hover:border-blue-400 hover:shadow-card hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 group select-none"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0 truncate">
          <div
            className="w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0 shadow-2xs border border-slate-100 group-hover:scale-105 transition-transform"
            style={{ backgroundColor: `${color}12`, color: color }}
          >
            {icon}
          </div>
          <span className="text-[11px] font-bold tracking-wider text-slate-500 uppercase truncate group-hover:text-slate-900 transition-colors">
            {label}
          </span>
        </div>

        {badgeText && (
          <span
            className="text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 font-mono shadow-2xs group-hover:opacity-90 transition-opacity"
            style={{ backgroundColor: badgeBg, color: badgeColor }}
          >
            {badgeText}
          </span>
        )}
      </div>

      <div className="flex items-baseline justify-between mt-1">
        <div className="text-2xl sm:text-[26px] font-black text-slate-900 mono tracking-tight leading-none group-hover:text-blue-600 transition-colors">
          {formatNumber(value)}
        </div>
        <div className="text-[10.5px] font-semibold text-slate-400 truncate text-right ml-2 group-hover:text-blue-600 transition-colors flex items-center justify-end gap-1">
          <span>{sub}</span>
          <span className="text-xs opacity-0 group-hover:opacity-100 transition-opacity">→</span>
        </div>
      </div>
    </div>
  )
}

export default function KpiStrip({ stats }) {
  const navigate = useNavigate()
  const totalEvents = stats?.total_events ?? null
  const bySeverity = stats?.by_severity || {}
  const byVerification = stats?.by_verification_status || {}

  const highRisk =
    (bySeverity.high || 0) +
    (bySeverity.extreme || 0) +
    (bySeverity.critical || 0)
  const verified = byVerification.verified || 0
  const pending = byVerification.pending || 0
  const underReview = (byVerification.needs_review || 0) + pending
  const verifiedPct =
    totalEvents > 0 ? `${Math.round((verified / totalEvents) * 100)}% verified` : '—'

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-3 select-none">
      {/* 1. Active Events -> Live Events (All) */}
      <KpiCard
        label="Active Events"
        value={totalEvents}
        sub="Pan-India Grid"
        color="#2563EB"
        badgeText="Live"
        badgeBg="#EFF6FF"
        badgeColor="#1D4ED8"
        icon={
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
        }
        onClick={() => navigate('/events')}
      />

      {/* 2. High Risk / Critical Threat -> Live Events (severity=critical) */}
      <KpiCard
        label="High Risk Threat"
        value={highRisk}
        sub="Immediate Alert"
        color="#DC2626"
        badgeText="Alert"
        badgeBg="#FEF2F2"
        badgeColor="#B91C1C"
        icon={
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        }
        onClick={() => navigate('/events?severity=critical')}
      />

      {/* 3. Verified Events -> Live Events (verification_status=verified) */}
      <KpiCard
        label="Verified Events"
        value={verified}
        sub={verifiedPct}
        color="#059669"
        badgeText="Confirmed"
        badgeBg="#ECFDF5"
        badgeColor="#047857"
        icon={
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        }
        onClick={() => navigate('/events?verification_status=verified')}
      />

      {/* 4. Under Review / Pending -> Live Events (verification_status=pending) */}
      <KpiCard
        label="Under Review"
        value={underReview}
        sub="Analyst Queue"
        color="#EA580C"
        badgeText="Review"
        badgeBg="#FFF7ED"
        badgeColor="#C2410C"
        icon={
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        }
        onClick={() => navigate('/events?verification_status=pending')}
      />
    </div>
  )
}
