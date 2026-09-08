import React from 'react'

/**
 * ═══════════════════════════════════════════════════════════════════
 * ATMOSPHERIC PHENOMENON SVG SYMBOLS
 * ═══════════════════════════════════════════════════════════════════
 */

export function HeavyRainIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" stroke="#0284C7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M16 14v6" stroke="#0284C7" strokeWidth="2" strokeLinecap="round" />
      <path d="M8 14v6" stroke="#0284C7" strokeWidth="2" strokeLinecap="round" />
      <path d="M12 16v6" stroke="#0284C7" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function RainfallIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" stroke="#38BDF8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 16v4" stroke="#38BDF8" strokeWidth="2" strokeLinecap="round" />
      <path d="M14 16v4" stroke="#38BDF8" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function ThunderstormIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" stroke="#DC2626" strokeWidth="2" strokeLinejoin="round" />
      <path d="M13 11l-3 5h3l-1 6 5-7h-3l2-4z" fill="#F59E0B" stroke="#B45309" strokeWidth="1" strokeLinejoin="round" />
    </svg>
  )
}

export function LightningIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#EAB308" stroke="#CA8A04" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function CycloneIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <circle cx="12" cy="12" r="3" fill="#E11D48" />
      <path d="M12 2a10 10 0 0 1 8.66 5l-2.6 1.5A7 7 0 0 0 12 5z" fill="#E11D48" opacity="0.9" />
      <path d="M22 12a10 10 0 0 1-5 8.66l-1.5-2.6A7 7 0 0 0 19 12z" fill="#E11D48" opacity="0.8" />
      <path d="M12 22a10 10 0 0 1-8.66-5l2.6-1.5A7 7 0 0 0 12 19z" fill="#E11D48" opacity="0.7" />
      <path d="M2 12a10 10 0 0 1 5-8.66l1.5 2.6A7 7 0 0 0 5 12z" fill="#E11D48" opacity="0.6" />
    </svg>
  )
}

export function FloodIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M2 12c3-1.5 6 1.5 9 0s6-1.5 9 0 4-1.5 4-1.5" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" />
      <path d="M2 16c3-1.5 6 1.5 9 0s6-1.5 9 0 4-1.5 4-1.5" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" />
      <path d="M2 20c3-1.5 6 1.5 9 0s6-1.5 9 0 4-1.5 4-1.5" stroke="#1D4ED8" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="6" r="3" fill="#38BDF8" stroke="#0284C7" strokeWidth="1.5" />
    </svg>
  )
}

export function HeatwaveIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <circle cx="12" cy="12" r="4.5" fill="#F59E0B" stroke="#D97706" strokeWidth="1.5" />
      <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41m14.14-14.14l-1.41 1.41" stroke="#F59E0B" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function StrongWindIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M17.7 7.7A2.5 2.5 0 1 1 19.5 12H2" stroke="#0D9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12.6 19.4A2 2 0 1 0 14 16H2" stroke="#0D9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9.8 4.6A2 2 0 1 1 11 8H2" stroke="#0D9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function FogIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M4 8h16" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
      <path d="M2 12h20" stroke="#64748B" strokeWidth="2" strokeLinecap="round" />
      <path d="M6 16h12" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
      <path d="M4 20h16" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function DustStormIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M3 8c4-1 8 1 12 0s6-2 7-1" stroke="#D97706" strokeWidth="2" strokeLinecap="round" />
      <path d="M2 12c3-1 7 1 11 0s7-1 9 0" stroke="#B45309" strokeWidth="2" strokeLinecap="round" />
      <path d="M4 16c4-1 8 1 12 0s5-1 6 0" stroke="#92400E" strokeWidth="2" strokeLinecap="round" />
      <circle cx="7" cy="5" r="1" fill="#D97706" />
      <circle cx="16" cy="5" r="1.5" fill="#D97706" />
      <circle cx="12" cy="19" r="1.2" fill="#B45309" />
    </svg>
  )
}

export function HailstormIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" stroke="#64748B" strokeWidth="2" strokeLinejoin="round" />
      <rect x="7" y="16" width="3" height="3" rx="0.5" fill="#38BDF8" transform="rotate(45 8.5 17.5)" />
      <rect x="13" y="16" width="3" height="3" rx="0.5" fill="#38BDF8" transform="rotate(45 14.5 17.5)" />
      <rect x="10" y="20" width="3" height="3" rx="0.5" fill="#38BDF8" transform="rotate(45 11.5 21.5)" />
    </svg>
  )
}

/**
 * ═══════════════════════════════════════════════════════════════════
 * STATUS & SEVERITY SYMBOLS
 * ═══════════════════════════════════════════════════════════════════
 */

export function VerifiedShield({ size = 16, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={`text-emerald-600 ${className}`}>
      <path d="M12 2L4 6v6c0 5.55 3.84 10.74 8 12 4.16-1.26 8-6.45 8-12V6l-8-4zm-1 15l-4-4 1.41-1.41L11 14.17l6.59-6.59L19 9l-8 8z" />
    </svg>
  )
}

export function UnderReviewGlass({ size = 16, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`text-amber-600 ${className}`}>
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <circle cx="11" cy="11" r="2.5" fill="#F59E0B" />
    </svg>
  )
}

export function AlertTriangle({ size = 16, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`text-rose-600 ${className}`}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" fill="#FEE2E2" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" strokeWidth="2.5" />
    </svg>
  )
}

export function CriticalDiamond({ size = 16, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={`text-red-700 ${className}`}>
      <polygon points="12 2 22 12 12 22 2 12 12 2" />
      <circle cx="12" cy="12" r="3" fill="#FFFFFF" />
    </svg>
  )
}

export function LiveRadarPulse({ size = 16, className = '' }) {
  return (
    <span className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
      <span className="relative inline-flex rounded-full bg-blue-600" style={{ width: size * 0.6, height: size * 0.6 }} />
    </span>
  )
}

/**
 * Weather Phenomenon Symbol Resolver Helper
 */
export function WeatherPhenomenonSymbol({ category, size = 18, className = '' }) {
  const norm = (category || '').toLowerCase().trim()

  switch (norm) {
    case 'heavy_rainfall':
      return <HeavyRainIcon size={size} className={className} />
    case 'rainfall':
    case 'rain':
      return <RainfallIcon size={size} className={className} />
    case 'thunderstorm':
      return <ThunderstormIcon size={size} className={className} />
    case 'lightning':
      return <LightningIcon size={size} className={className} />
    case 'cyclone':
      return <CycloneIcon size={size} className={className} />
    case 'flood':
      return <FloodIcon size={size} className={className} />
    case 'heatwave':
      return <HeatwaveIcon size={size} className={className} />
    case 'strong_wind':
    case 'wind':
      return <StrongWindIcon size={size} className={className} />
    case 'fog':
      return <FogIcon size={size} className={className} />
    case 'dust_storm':
      return <DustStormIcon size={size} className={className} />
    case 'hailstorm':
    case 'hail':
      return <HailstormIcon size={size} className={className} />
    default:
      return <HeavyRainIcon size={size} className={className} />
  }
}
