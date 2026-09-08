import React from 'react'

/**
 * ═══════════════════════════════════════════════════════════════════
 * PLATFORM BRAND LOGOS & EMBLEMS
 * ═══════════════════════════════════════════════════════════════════
 */

/**
 * Main Platform Brand Logo: MeteoRadar / National Weather Early Warning
 */
export function PlatformLogo({ size = 'md', collapsed = false, className = '' }) {
  const sizeMap = {
    sm: { box: 'w-7 h-7', icon: 28, text: 'text-[11px] leading-[1.2]' },
    md: { box: 'w-9 h-9', icon: 36, text: 'text-[13px] leading-[1.2]' },
    lg: { box: 'w-11 h-11', icon: 44, text: 'text-sm leading-snug' },
  }
  const s = sizeMap[size] || sizeMap.md

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {/* High-Resolution Dynamic Radar Emblem */}
      <div className={`${s.box} rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-blue-800 p-0.5 shadow-md shadow-blue-500/20 flex items-center justify-center flex-shrink-0 relative overflow-hidden group`}>
        <svg
          viewBox="0 0 40 40"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Outer Atmospheric Isobar Rings */}
          <circle cx="20" cy="20" r="17" stroke="rgba(255,255,255,0.25)" strokeWidth="1" strokeDasharray="2 2" />
          <circle cx="20" cy="20" r="12" stroke="rgba(255,255,255,0.4)" strokeWidth="1.2" />
          <circle cx="20" cy="20" r="7" stroke="rgba(255,255,255,0.6)" strokeWidth="1.2" />

          {/* Dynamic Radar Sweep Beam */}
          <path
            d="M20 20 L35 12 A17 17 0 0 0 20 3 Z"
            fill="url(#radarSweepGrad)"
            opacity="0.75"
          />

          {/* Crosshairs */}
          <line x1="20" y1="3" x2="20" y2="37" stroke="rgba(255,255,255,0.3)" strokeWidth="0.8" />
          <line x1="3" y1="20" x2="37" y2="20" stroke="rgba(255,255,255,0.3)" strokeWidth="0.8" />

          {/* Center Weather Early-Warning Core */}
          <circle cx="20" cy="20" r="3.5" fill="#38BDF8" />
          <circle cx="20" cy="20" r="1.8" fill="#FFFFFF" />

          {/* Lightning / Energy Pulse */}
          <path
            d="M22 6 L18 13 L23 13 L19 20"
            stroke="#FDE047"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          <defs>
            <linearGradient id="radarSweepGrad" x1="20" y1="20" x2="35" y2="3" gradientUnits="userSpaceOnUse">
              <stop stopColor="#38BDF8" stopOpacity="0.8" />
              <stop offset="1" stopColor="#38BDF8" stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {!collapsed && (
        <div className="min-w-0 flex flex-col justify-center">
          <span className={`font-bold tracking-tight text-slate-900 ${s.text}`}>
            National Weather Intelligence
          </span>
        </div>
      )}
    </div>
  )
}

/**
 * Official Meteorological Trust Crest (IMD / MoES Alignment)
 */
export function MeteorologicalTrustBadge({ className = '' }) {
  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-1 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 ${className}`}>
      <svg className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L4 6v6c0 5.55 3.84 10.74 8 12 4.16-1.26 8-6.45 8-12V6l-8-4zm-1 15l-4-4 1.41-1.41L11 14.17l6.59-6.59L19 9l-8 8z" />
      </svg>
      <div className="text-[10px] leading-none">
        <span className="font-bold text-slate-800">MoES / IMD</span>
        <span className="text-slate-500 ml-1">Corridor Telemetry</span>
      </div>
    </div>
  )
}

/**
 * ═══════════════════════════════════════════════════════════════════
 * CITY EMBLEMS & CRESTS (Mumbai, Nagpur, Nashik)
 * ═══════════════════════════════════════════════════════════════════
 */

export function CityCrest({ city, size = 'md', className = '' }) {
  const norm = (city || '').toLowerCase().trim()

  const sizeMap = {
    xs: { box: 'w-4 h-4', icon: 16 },
    sm: { box: 'w-5 h-5', icon: 20 },
    md: { box: 'w-6 h-6', icon: 24 },
    lg: { box: 'w-8 h-8', icon: 32 },
  }
  const s = sizeMap[size] || sizeMap.md

  if (norm === 'mumbai') {
    return (
      <div
        className={`${s.box} rounded-lg bg-sky-50 border border-sky-300 p-0.5 flex items-center justify-center flex-shrink-0 shadow-2xs ${className}`}
        title="Mumbai Metro Corridor"
      >
        <svg viewBox="0 0 24 24" className="w-full h-full text-sky-600" fill="currentColor">
          {/* Gateway Arch + Sea Waves */}
          <path d="M4 21V9l8-6 8 6v12h-3v-7a5 5 0 0 0-10 0v7H4z" opacity="0.9" />
          <path d="M2 22h20v2H2z" fill="#0284C7" />
          <path d="M12 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4z" fill="#38BDF8" />
        </svg>
      </div>
    )
  }

  if (norm === 'nagpur') {
    return (
      <div
        className={`${s.box} rounded-lg bg-orange-50 border border-orange-300 p-0.5 flex items-center justify-center flex-shrink-0 shadow-2xs ${className}`}
        title="Nagpur Zero-Mile Corridor"
      >
        <svg viewBox="0 0 24 24" className="w-full h-full text-orange-600" fill="currentColor">
          {/* Zero Mile Stone Obelisk / Central Geo Pillar */}
          <path d="M12 2L8 9h8l-4-7zm-3 8l-2 11h10l-2-11H9z" opacity="0.9" />
          <circle cx="12" cy="15" r="2" fill="#FFFFFF" />
          <path d="M4 22h16v2H4z" fill="#EA580C" />
        </svg>
      </div>
    )
  }

  if (norm === 'nasik' || norm === 'nashik') {
    return (
      <div
        className={`${s.box} rounded-lg bg-emerald-50 border border-emerald-300 p-0.5 flex items-center justify-center flex-shrink-0 shadow-2xs ${className}`}
        title="Nashik Western Ghats Corridor"
      >
        <svg viewBox="0 0 24 24" className="w-full h-full text-emerald-600" fill="currentColor">
          {/* Ghats Mountains + Godavari River Curves */}
          <path d="M14 6l6 12H2l5-10 3 6 4-8z" opacity="0.85" />
          <path d="M2 20c4-2 8 2 12 0s6 1 8 0v2c-2 1-5-1-8 0s-8-2-12 0v-2z" fill="#059669" />
        </svg>
      </div>
    )
  }

  // Generic Sector Crest
  return (
    <div className={`${s.box} rounded-lg bg-slate-100 border border-slate-200 p-0.5 flex items-center justify-center flex-shrink-0 ${className}`}>
      <svg viewBox="0 0 24 24" className="w-full h-full text-slate-500" fill="currentColor">
        <circle cx="12" cy="12" r="9" opacity="0.3" />
        <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm1 15h-2v-6h2zm0-8h-2V7h2z" />
      </svg>
    </div>
  )
}

/**
 * ═══════════════════════════════════════════════════════════════════
 * INGESTION SOURCE CHANNEL LOGOS
 * ═══════════════════════════════════════════════════════════════════
 */

export function SourceChannelLogo({ source, className = '' }) {
  const norm = (source || '').toLowerCase().trim()

  if (norm.includes('radar') || norm.includes('doppler')) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 bg-blue-50 border border-blue-200 rounded-md text-blue-700 ${className}`}>
        <svg className="w-3.5 h-3.5 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2a10 10 0 0 1 10 10" />
          <path d="M12 6a6 6 0 0 1 6 6" />
          <circle cx="12" cy="12" r="2" fill="currentColor" />
        </svg>
        <span className="text-[10px] font-extrabold uppercase tracking-wide">DWR RADAR</span>
      </div>
    )
  }

  if (norm.includes('satellite') || norm.includes('insat')) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 bg-indigo-50 border border-indigo-200 rounded-md text-indigo-700 ${className}`}>
        <svg className="w-3.5 h-3.5 text-indigo-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
        </svg>
        <span className="text-[10px] font-extrabold uppercase tracking-wide">INSAT-3D</span>
      </div>
    )
  }

  if (norm.includes('imd') || norm.includes('gov') || norm.includes('official')) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 bg-amber-50 border border-amber-200 rounded-md text-amber-800 ${className}`}>
        <svg className="w-3.5 h-3.5 text-amber-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z" />
        </svg>
        <span className="text-[10px] font-extrabold uppercase tracking-wide">IMD OFFICIAL</span>
      </div>
    )
  }

  if (norm.includes('aws') || norm.includes('sensor') || norm.includes('iot')) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 border border-emerald-200 rounded-md text-emerald-700 ${className}`}>
        <svg className="w-3.5 h-3.5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <rect x="9" y="9" width="6" height="6" />
          <line x1="9" y1="1" x2="9" y2="4" />
          <line x1="15" y1="1" x2="15" y2="4" />
          <line x1="9" y1="20" x2="9" y2="23" />
          <line x1="15" y1="20" x2="15" y2="23" />
        </svg>
        <span className="text-[10px] font-extrabold uppercase tracking-wide">AWS SENSOR</span>
      </div>
    )
  }

  if (norm.includes('twitter') || norm.includes('social') || norm.includes('x')) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 bg-slate-100 border border-slate-300 rounded-md text-slate-800 ${className}`}>
        <svg className="w-3 h-3 text-slate-800" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
        <span className="text-[10px] font-extrabold uppercase tracking-wide">OSINT / X</span>
      </div>
    )
  }

  // Citizen / Crowdsourced
  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 bg-purple-50 border border-purple-200 rounded-md text-purple-700 ${className}`}>
      <svg className="w-3.5 h-3.5 text-purple-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
      <span className="text-[10px] font-extrabold uppercase tracking-wide">CITIZEN FEED</span>
    </div>
  )
}
