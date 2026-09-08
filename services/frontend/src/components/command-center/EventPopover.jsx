import React from 'react'
import { useNavigate } from 'react-router-dom'

const SEVERITY_LABELS = {
  low: 'LOW',
  moderate: 'MODERATE',
  high: 'HIGH',
  extreme: 'CRITICAL',
  critical: 'CRITICAL',
}

const SEVERITY_COLORS = {
  low: 'text-[#7A8794]',
  moderate: 'text-[#477D96]',
  high: 'text-[#B56F20]',
  extreme: 'text-[#B84848]',
  critical: 'text-[#B84848]',
}

const CATEGORY_LABELS = {
  heavy_rainfall: 'Heavy Rainfall',
  rainfall: 'Rainfall',
  flood: 'Flood',
  heatwave: 'Heatwave',
  thunderstorm: 'Thunderstorm',
  lightning: 'Lightning',
  strong_wind: 'Strong Wind',
  hailstorm: 'Hailstorm',
  dust_storm: 'Dust Storm',
  cyclone: 'Cyclone',
  fog: 'Fog',
}

const VERIFICATION_STYLES = {
  verified: 'text-[#31845D]',
  pending: 'text-[#526170]',
  rejected: 'text-[#B84848]',
  suspicious: 'text-[#B56F20]',
  duplicate: 'text-[#7A8794]',
}

export default function EventPopover({ event }) {
  const navigate = useNavigate()

  const formatTime = (iso) => {
    if (!iso) return '—'
    const d = new Date(iso)
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  const formatPct = (val) => {
    if (val === null || val === undefined) return '—'
    return `${Math.round(val * 100)}%`
  }

  return (
    <div className="min-w-[220px] p-3 text-[12px]">
      {/* Category + Severity */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="font-semibold text-[#18232D] text-[13px]">
          {CATEGORY_LABELS[event.event_category] || event.event_category}
        </div>
        <span className={`text-[10px] font-bold tracking-wide ${SEVERITY_COLORS[event.severity] || 'text-[#526170]'}`}>
          {SEVERITY_LABELS[event.severity] || (event.severity || '—').toUpperCase()}
        </span>
      </div>

      {/* Location */}
      <div className="text-[#526170] mb-3">
        {event.city || 'Unknown location'}
      </div>

      {/* AI Metrics */}
      <div className="space-y-1.5 mb-3">
        <div className="flex justify-between">
          <span className="text-[#7A8794]">Confidence</span>
          <span className="mono text-[#526170]">{formatPct(event.classification_confidence)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#7A8794]">Credibility</span>
          <span className="mono text-[#526170]">{formatPct(event.credibility_score)}</span>
        </div>
      </div>

      {/* Verification */}
      <div className="mb-3">
        <span className={`text-[11px] font-medium ${VERIFICATION_STYLES[event.verification_status] || 'text-[#526170]'}`}>
          ● {event.verification_status === 'verified' ? 'Verified' :
             event.verification_status === 'pending' ? 'Pending Review' :
             event.verification_status === 'rejected' ? 'Rejected' :
             event.verification_status === 'suspicious' ? 'Suspicious' :
             event.verification_status}
        </span>
      </div>

      {/* Timestamps */}
      <div className="space-y-1 mb-3 text-[11px]">
        <div className="flex justify-between">
          <span className="text-[#7A8794]">Detected</span>
          <span className="mono text-[#526170]">{formatTime(event.event_timestamp)}</span>
        </div>
      </div>

      {/* Action */}
      <button
        onClick={() => event.event_id && navigate(`/events/${event.event_id}`)}
        className="w-full text-left text-[12px] text-[#477D96] hover:text-[#3B6FA0] font-medium transition-colors"
      >
        View Event Intelligence →
      </button>
    </div>
  )
}
