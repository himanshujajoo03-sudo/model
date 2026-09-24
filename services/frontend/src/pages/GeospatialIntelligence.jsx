import React, { useEffect, useMemo, useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Marker, GeoJSON, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import useGeospatialStore from '../stores/geospatialStore'
import useLayoutStore from '../stores/layoutStore'
import Sidebar from '../components/command-center/Sidebar'
import Header from '../components/command-center/Header'
import ModelSelect from '../components/common/ModelSelect'
import SelectDropdown from '../components/common/SelectDropdown'
import { ACTIVE_CITIES, UPCOMING_CITIES, getCityMetadata } from '../constants/cities'
import {
  getStateColor,
  SURROUNDING_LAND_STYLE,
} from '../constants/mapTheme'
import { CityCrest } from '../components/common/BrandLogos'
import { playNotificationChime } from '../utils/audioAlerts'

/* ═══════════════════════════════════════════════════════════════
   Category & Severity Metadata
   ═══════════════════════════════════════════════════════════════ */

const CAT = {
  heavy_rainfall: 'Heavy Rain', rainfall: 'Rainfall', flood: 'Flood',
  heatwave: 'Heatwave', thunderstorm: 'Thunderstorm', lightning: 'Lightning',
  strong_wind: 'Strong Wind', hailstorm: 'Hailstorm', dust_storm: 'Dust Storm',
  cyclone: 'Cyclone', fog: 'Dense Fog',
}

const CAT_ICONS = {
  heavy_rainfall: '🌧️', rainfall: '🌦️', flood: '🌊',
  heatwave: '🔥', thunderstorm: '⛈️', lightning: '⚡',
  strong_wind: '💨', hailstorm: '🌨️', dust_storm: '🌪️',
  cyclone: '🌀', fog: '🌫️',
}

const CAT_COLOR = {
  heavy_rainfall: '#0284C7', rainfall: '#0284C7', flood: '#1E3A8A',
  heatwave: '#EA580C', thunderstorm: '#DC2626', lightning: '#D97706',
  strong_wind: '#475569', hailstorm: '#0D9488', dust_storm: '#B45309',
  cyclone: '#B91C1C', fog: '#64748B',
}

const SEV_COLOR = {
  low: '#64748B', moderate: '#0284C7', high: '#D97706',
  extreme: '#DC2626', critical: '#DC2626',
}

const SEV_SIZE = { low: 8, moderate: 11, high: 15, extreme: 20, critical: 24 }

const SEV_LABEL = { low: 'Low', moderate: 'Moderate', high: 'High', extreme: 'Critical', critical: 'Critical' }

const VER_COLOR = {
  verified: '#059669', pending: '#64748B', needs_review: '#D97706',
  suspicious: '#DC2626', duplicate: '#64748B',
}

const VER_LABEL = {
  verified: 'Verified', pending: 'Pending', needs_review: 'Needs Review',
  suspicious: 'Suspicious', duplicate: 'Duplicate',
}

const TIME_RANGES = [
  { value: '1h', label: '1h' },
  { value: '6h', label: '6h' },
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: 'all', label: 'All' },
]

const LAYERS = [
  { id: 'events', label: 'Events', desc: 'All canonical weather events' },
  { id: 'density', label: 'Event Density', desc: 'Spatial concentration of events' },
  { id: 'risk', label: 'Relative Risk Index', desc: 'Composite severity/credibility/verification score' },
  { id: 'category', label: 'By Category', desc: 'Events colored by weather category' },
  { id: 'verification', label: 'Verification Status', desc: 'Event verification distribution' },
]

const CATEGORIES = [
  { value: '', label: 'All Categories', icon: '🌐' },
  { value: 'heavy_rainfall', label: 'Heavy Rain', icon: '🌧️', subtitle: 'Monsoon deluge' },
  { value: 'rainfall', label: 'Rainfall', icon: '🌦️', subtitle: 'Precipitation' },
  { value: 'flood', label: 'Flood', icon: '🌊', subtitle: 'Hydrological' },
  { value: 'heatwave', label: 'Heatwave', icon: '🔥', subtitle: 'Thermal stress' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: '⛈️', subtitle: 'Convective storm' },
  { value: 'strong_wind', label: 'Strong Wind', icon: '💨', subtitle: 'Gale force' },
  { value: 'cyclone', label: 'Cyclone', icon: '🌀', subtitle: 'Vortex system' },
  { value: 'fog', label: 'Dense Fog', icon: '🌫️', subtitle: 'Low visibility' },
  { value: 'dust_storm', label: 'Dust Storm', icon: '🌪️', subtitle: 'Particulate front' },
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

function fmtPct(v) {
  if (v === null || v === undefined) return '—'
  return `${Math.round(v * 100)}%`
}

function ago(iso) {
  if (!iso) return ''
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function computeRiskScore(event) {
  const sevMap = { low: 0.2, moderate: 0.4, high: 0.7, extreme: 1.0, critical: 1.0 }
  const verMap = { verified: 0.15, pending: 0, needs_review: 0.1, suspicious: -0.2, duplicate: 0 }
  const sev = sevMap[event.severity] || 0.4
  const cred = (event.credibility_score || 0) * 0.2
  const ver = verMap[event.verification_status] || 0
  return Math.max(0, Math.min(1, sev * 0.6 + cred + ver))
}

function riskColor(score) {
  if (score >= 0.7) return '#DC2626'
  if (score >= 0.5) return '#EA580C'
  if (score >= 0.3) return '#D97706'
  return '#0284C7'
}

/* ═══════════════════════════════════════════════════════════════
   Section 3: Custom City Markers with Logos & Information Pills
   ═══════════════════════════════════════════════════════════════ */

function createCityMarkerIcon(city, isSelected) {
  const iconEmoji =
    city.zone === 'North'
      ? '🏔️'
      : city.zone === 'South'
      ? '🌴'
      : city.zone === 'East'
      ? '🌊'
      : city.zone === 'Northeast'
      ? '🌿'
      : city.zone === 'Central'
      ? '🏛️'
      : '🌆'
  const stateLabel = city.state || 'India'
  const regionLabel = city.region || city.district || `${city.zone || 'Metropolitan'} Zone`
  const haloColor = isSelected ? '#2563EB' : city.color || '#0284C7'
  const activeBorder = isSelected ? '2px solid #2563EB' : '1px solid #CBD5E1'
  const scale = isSelected ? 'scale(1.08)' : 'scale(1)'

  return L.divIcon({
    className: 'city-leaflet-marker',
    html: `
      <div style="position:relative;display:flex;flex-direction:column;align-items:center;cursor:pointer;transform:${scale};transition:transform 0.2s ease;">
        <!-- Pulsing Halo -->
        <div class="beacon-wave" style="
          position:absolute;
          top:-6px;
          width:28px;
          height:28px;
          border-radius:50%;
          border:2.5px solid ${haloColor};
          pointer-events:none;
        "></div>

        <!-- City Pin with Icon/Logo -->
        <div style="
          position:relative;
          display:flex;
          align-items:center;
          justify-content:center;
          width:28px;
          height:28px;
          border-radius:50%;
          background:#FFFFFF;
          border:2.5px solid ${city.color || '#2563EB'};
          box-shadow:0 3px 10px rgba(15,23,42,0.25);
          font-size:14px;
          z-index:2;
        ">
          <span>${iconEmoji}</span>
        </div>

        <!-- City Information Pill -->
        <div style="
          margin-top:3px;
          background:#FFFFFF;
          border:${activeBorder};
          color:#0F172A;
          font-family:'Plus Jakarta Sans',sans-serif;
          font-weight:700;
          font-size:10px;
          padding:2px 7px;
          border-radius:7px;
          box-shadow:0 3px 8px rgba(15,23,42,0.12);
          white-space:nowrap;
          display:flex;
          flex-direction:column;
          align-items:center;
          line-height:1.2;
          z-index:2;
        ">
          <div style="display:flex;align-items:center;gap:3.5px;">
            <span style="width:5px;height:5px;border-radius:50%;background:${city.color || '#2563EB'};"></span>
            <span style="font-weight:800;color:#0F172A;">${city.name}</span>
          </div>
          <span style="font-size:8.5px;color:#64748B;font-weight:600;">${stateLabel} · ${regionLabel}</span>
        </div>
      </div>
    `,
    iconSize: [94, 60],
    iconAnchor: [47, 14],
  })
}

/* ═══════════════════════════════════════════════════════════════
   Map Sub-Components: Handlers, Controls & Legend
   ═══════════════════════════════════════════════════════════════ */

function MapBoundsHandler() {
  const map = useMap()
  const setMapBounds = useGeospatialStore((s) => s.setMapBounds)

  useEffect(() => {
    const update = () => {
      const b = map.getBounds()
      setMapBounds({
        min_lat: b.getSouth(), max_lat: b.getNorth(),
        min_lon: b.getWest(), max_lon: b.getEast(),
      })
    }
    map.on('moveend', update)
    map.on('zoomend', update)
    return () => { map.off('moveend', update); map.off('zoomend', update) }
  }, [map, setMapBounds])

  return null
}

function MapFlightController({ targetCenter, targetZoom }) {
  const map = useMap()
  useEffect(() => {
    if (targetCenter && targetZoom) {
      map.flyTo(targetCenter, targetZoom, { duration: 1.2 })
    }
  }, [map, targetCenter, targetZoom])
  return null
}

function LayerControl({ selectedLayer, onSelectLayer }) {
  return (
    <div className="absolute top-3 right-3 z-[1000] bg-white border border-slate-200 rounded-xl shadow-dropdown max-w-[200px] overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/80">
        <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">Analytical Layer</span>
      </div>
      <div className="p-1.5 space-y-0.5">
        {LAYERS.map((l) => (
          <button
            key={l.id}
            onClick={() => onSelectLayer(l.id)}
            className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              selectedLayer === l.id
                ? 'bg-brand-blue-50 text-brand-blue-700 border border-brand-blue-200'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
            title={l.desc}
          >
            {l.label}
          </button>
        ))}
      </div>
    </div>
  )
}

function MapLegend({ layer, selectedCity, selectedState }) {
  return (
    <div className="absolute bottom-4 left-4 z-[1000] bg-white/95 backdrop-blur-xs border border-slate-200 rounded-2xl p-3.5 shadow-card max-w-[240px]">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">Map Legend</span>
        <span className="text-[9px] font-bold text-slate-400 font-mono">GIS v2.4</span>
      </div>

      {/* Core Boundaries & City Types (Section 15) */}
      <div className="space-y-1.5 pb-2.5 mb-2.5 border-b border-slate-100 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-white shadow-xs flex-shrink-0" />
          <span className="text-slate-700 font-semibold text-[11px]">Active City Hub (3 Live)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80 border border-white shadow-xs flex-shrink-0" />
          <span className="text-slate-600 font-medium text-[11px]">Updated Soon (+15 Planned)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-0.5 bg-slate-400 rounded flex-shrink-0" />
          <span className="text-slate-600 font-medium text-[11px]">State Boundary (Medium)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-1 bg-brand-blue-600 rounded flex-shrink-0" />
          <span className="text-brand-blue-700 font-bold text-[11px]">Selected State / Region</span>
        </div>
      </div>

      {/* Dynamic Layer Legend */}
      <div className="space-y-1.5">
        <div className="text-[9.5px] font-bold text-slate-400 uppercase tracking-wider">
          {layer === 'category' ? 'Phenomenon Category' : layer === 'verification' ? 'Verification Status' : layer === 'risk' ? 'Relative Risk Index' : 'Severity Scale'}
        </div>

        {layer === 'category' && (
          Object.entries(CAT_COLOR).slice(0, 6).map(([cat, color]) => (
            <div key={cat} className="flex items-center gap-2">
              <span className="text-xs">{CAT_ICONS[cat] || '🌧️'}</span>
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
              <span className="text-[11px] text-slate-700 font-medium">{CAT[cat]}</span>
            </div>
          ))
        )}

        {layer === 'verification' && (
          Object.entries(VER_COLOR).map(([status, color]) => (
            <div key={status} className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
              <span className="text-[11px] text-slate-700 font-medium">{VER_LABEL[status]}</span>
            </div>
          ))
        )}

        {layer === 'risk' && (
          [
            { label: 'Critical Risk (>0.7)', color: '#DC2626' },
            { label: 'High Risk (0.5–0.7)', color: '#EA580C' },
            { label: 'Moderate Risk (0.3–0.5)', color: '#D97706' },
            { label: 'Observed Risk (<0.3)', color: '#0284C7' },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
              <span className="text-[11px] text-slate-700 font-medium">{item.label}</span>
            </div>
          ))
        )}

        {(layer === 'events' || layer === 'density') && (
          [
            { label: 'Critical / Extreme', color: '#DC2626' },
            { label: 'High Severity', color: '#D97706' },
            { label: 'Moderate Severity', color: '#0284C7' },
            { label: 'Low Severity', color: '#64748B' },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
              <span className="text-[11px] text-slate-700 font-medium">{item.label}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function EventMarkers({ events, layer, onSelectEvent }) {
  return events.map((event) => {
    if (!event.latitude || !event.longitude) return null

    let fillColor, radius
    if (layer === 'risk') {
      const risk = computeRiskScore(event)
      fillColor = riskColor(risk)
      radius = 6 + risk * 14
    } else if (layer === 'category') {
      fillColor = CAT_COLOR[event.event_category] || '#0284C7'
      radius = SEV_SIZE[event.severity] || 11
    } else if (layer === 'verification') {
      fillColor = VER_COLOR[event.verification_status] || '#64748B'
      radius = SEV_SIZE[event.severity] || 11
    } else {
      fillColor = SEV_COLOR[event.severity] || '#0284C7'
      radius = SEV_SIZE[event.severity] || 11
    }

    return (
      <CircleMarker
        key={event.event_id}
        center={[event.latitude, event.longitude]}
        radius={radius}
        pathOptions={{
          fillColor,
          fillOpacity: 0.85,
          color: '#FFFFFF',
          weight: 2,
        }}
        eventHandlers={{
          click: () => onSelectEvent(event),
        }}
      >
        <Tooltip direction="top" offset={[0, -radius]}>
          <div className="text-xs">
            <div className="font-bold text-slate-900 flex items-center gap-1">
              <span>{CAT_ICONS[event.event_category] || '🌧️'}</span>
              <span>{CAT[event.event_category] || event.event_category}</span>
            </div>
            <div className="text-slate-600 font-medium">
              {event.city || event.district || 'National Grid'} · {event.state || 'India'}
            </div>
            <div className="text-[10px] text-slate-400">{ago(event.last_seen)}</div>
          </div>
        </Tooltip>
      </CircleMarker>
    )
  })
}

/* ═══════════════════════════════════════════════════════════════
   Section 14: Split Layout Information Panel
   - Selected City Details (Pan-India Cities)
   - Selected Event Record
   - National Scope Overview (All India)
   ═══════════════════════════════════════════════════════════════ */

function InformationPanel({
  events,
  selectedEvent,
  selectedCity,
  onSelectCity,
  onClearSelection,
  onOpenUpcomingModal,
}) {
  const navigate = useNavigate()
  const cityMeta = useMemo(() => getCityMetadata(selectedCity), [selectedCity])

  // Filter events by selected city if any
  const cityEvents = useMemo(() => {
    if (!selectedCity || !events) return []
    const clean = selectedCity.toLowerCase()
    return events.filter((e) => (e.city || '').toLowerCase() === clean)
  }, [selectedCity, events])

  // Aggregate stats
  const analysis = useMemo(() => {
    if (!events || events.length === 0) return null
    const total = events.length
    const highCritical = events.filter((e) => e.severity === 'high' || e.severity === 'extreme' || e.severity === 'critical').length

    const catCounts = {}
    for (const e of events) {
      catCounts[e.event_category] = (catCounts[e.event_category] || 0) + 1
    }
    const topCategories = Object.entries(catCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([cat, count]) => ({ cat, count, pct: Math.round((count / total) * 100) }))

    return { total, highCritical, categories: topCategories }
  }, [events])

  return (
    <div className="w-full lg:w-[380px] xl:w-[420px] flex-shrink-0 border-t lg:border-t-0 lg:border-l border-slate-200 bg-white overflow-y-auto p-4 space-y-4 scrollbar-thin">
      {/* ── CASE 1: Specific Event is Inspected ── */}
      {selectedEvent && (
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-brand-blue-700 bg-brand-blue-50 border border-brand-blue-200 px-2 py-0.5 rounded uppercase tracking-wider">
              Inspected Event
            </span>
            <button
              onClick={() => useGeospatialStore.getState().clearSelectedEvent()}
              className="text-xs text-slate-400 hover:text-slate-700 p-1"
              title="Close event details"
            >
              ✕
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xl">{CAT_ICONS[selectedEvent.event_category] || '🌧️'}</span>
            <div>
              <div className="font-bold text-sm text-slate-900 leading-tight">
                {CAT[selectedEvent.event_category] || selectedEvent.event_category}
              </div>
              <div className="text-xs text-slate-500 font-medium">
                {selectedEvent.city || selectedEvent.district || 'National Meteorological Grid'} · {selectedEvent.state || 'India'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-200/70">
            <div className="bg-white p-2 rounded-lg border border-slate-200/80">
              <span className="text-slate-400 block text-[10px] font-medium">Severity</span>
              <span className="font-bold text-slate-900 capitalize flex items-center gap-1 mt-0.5">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: SEV_COLOR[selectedEvent.severity] || '#0284C7' }}
                />
                {SEV_LABEL[selectedEvent.severity] || selectedEvent.severity}
              </span>
            </div>
            <div className="bg-white p-2 rounded-lg border border-slate-200/80">
              <span className="text-slate-400 block text-[10px] font-medium">Confidence</span>
              <span className="font-bold text-slate-900 block mt-0.5">
                {fmtPct(selectedEvent.classification_confidence)}
              </span>
            </div>
          </div>

          <div className="text-xs text-slate-500 space-y-1">
            <div className="flex justify-between">
              <span>Coordinates:</span>
              <span className="font-mono text-slate-700">
                {selectedEvent.latitude?.toFixed(4)}° N, {selectedEvent.longitude?.toFixed(4)}° E
              </span>
            </div>
            <div className="flex justify-between">
              <span>Detection Pipeline:</span>
              <span className="font-semibold text-emerald-700">Multi-Sensor Validated</span>
            </div>
            <div className="flex justify-between">
              <span>Last Reported:</span>
              <span className="text-slate-700">{ago(selectedEvent.last_seen)}</span>
            </div>
          </div>

          <button
            onClick={() => navigate(`/events/${selectedEvent.event_id}`)}
            className="w-full btn-primary text-xs py-2 shadow-xs"
          >
            Open Full Event Details →
          </button>
        </div>
      )}

      {/* ── CASE 2: Specific City is Selected (Mumbai, Nagpur, Nashik) ── */}
      {selectedCity && cityMeta && (
        <div className="space-y-3.5">
          {/* City Details Header Card */}
          <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-xs">
            {/* City Photo with Gradient Overlay & Status Badge */}
            <div className="relative h-36 w-full bg-slate-100 overflow-hidden">
              <img
                src={cityMeta.photo}
                alt={cityMeta.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.onerror = null
                  e.target.src = '/weather_radar_hero.jpg'
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950/70 via-slate-950/20 to-transparent" />
              
              {/* Status Badge */}
              <div className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded-full bg-emerald-500 text-white font-bold text-[10px] flex items-center gap-1 shadow-md">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                Live Telemetry Hub
              </div>

              {/* City Title on Image */}
              <div className="absolute bottom-2.5 left-3 right-3 text-white">
                <div className="text-lg font-extrabold flex items-center gap-1.5 leading-none drop-shadow-sm">
                  <span>📍</span>
                  <span>{cityMeta.name}</span>
                </div>
                <div className="text-xs text-slate-200 font-medium mt-0.5 drop-shadow-sm">
                  {cityMeta.state} · {cityMeta.region}
                </div>
              </div>
            </div>

            {/* City Description & Sensor Spec */}
            <div className="p-3.5 space-y-2.5 text-xs">
              <p className="text-slate-600 leading-relaxed">
                {cityMeta.description}
              </p>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100">
                <div className="p-2 bg-slate-50 rounded-xl border border-slate-200/80">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Sensor Grid
                  </span>
                  <span className="font-semibold text-slate-800 text-[11px] block mt-0.5">
                    {cityMeta.sensors}
                  </span>
                </div>
                <div className="p-2 bg-slate-50 rounded-xl border border-slate-200/80">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Coordinates
                  </span>
                  <span className="font-mono font-semibold text-slate-800 text-[11px] block mt-0.5">
                    {cityMeta.lat.toFixed(4)}° N, {cityMeta.lon.toFixed(4)}° E
                  </span>
                </div>
              </div>

              {/* Monitored Phenomenon Tags */}
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Targeted Phenomena:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {cityMeta.weatherTypes.map((t) => (
                    <span
                      key={t}
                      className="px-2 py-0.5 rounded-md bg-brand-blue-50 text-brand-blue-800 border border-brand-blue-200/60 text-[10.5px] font-medium"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => navigate(`/events?city=${cityMeta.name}`)}
                  className="flex-1 btn-primary text-xs py-2 shadow-xs"
                >
                  Explore {cityMeta.name} Events in Feed →
                </button>
                <button
                  onClick={onClearSelection}
                  className="px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  Reset View
                </button>
              </div>
            </div>
          </div>

          {/* Active Events in this City */}
          <div className="rounded-2xl border border-slate-200 bg-white p-3.5 space-y-2.5 shadow-xs">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {cityMeta.name} Live Events ({cityEvents.length})
              </h4>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                Active Stream
              </span>
            </div>

            {cityEvents.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-500 bg-slate-50 rounded-xl border border-slate-200/80">
                <span className="text-base block mb-1">✨</span>
                All atmospheric parameters within nominal safety thresholds in {cityMeta.name}.
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[220px] overflow-y-auto scrollbar-thin">
                {cityEvents.map((evt) => (
                  <div
                    key={evt.event_id}
                    onClick={() => useGeospatialStore.getState().setSelectedEvent(evt)}
                    className="p-2 rounded-xl border border-slate-200/80 hover:border-brand-blue-300 hover:bg-brand-blue-50/30 cursor-pointer transition-all flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-base flex-shrink-0">{CAT_ICONS[evt.event_category] || '🌧️'}</span>
                      <div className="min-w-0 truncate">
                        <div className="text-xs font-bold text-slate-900 truncate">
                          {CAT[evt.event_category] || evt.event_category}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {ago(evt.last_seen)} · {fmtPct(evt.classification_confidence)} conf
                        </div>
                      </div>
                    </div>
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded capitalize flex-shrink-0"
                      style={{
                        backgroundColor: `${SEV_COLOR[evt.severity] || '#0284C7'}15`,
                        color: SEV_COLOR[evt.severity] || '#0284C7',
                      }}
                    >
                      {evt.severity}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── CASE 3: National Overview (No city or event selected) ── */}
      {!selectedCity && !selectedEvent && (
        <div className="space-y-4">
          {/* Coverage Overview Cards */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                National Coverage Scope
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                3 Hubs Live
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-center shadow-2xs">
                <div className="text-base font-bold text-slate-900">{analysis?.total || 0}</div>
                <div className="text-[10px] text-slate-500 font-medium">Events</div>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-center shadow-2xs">
                <div className="text-base font-bold text-rose-600">{analysis?.highCritical || 0}</div>
                <div className="text-[10px] text-slate-500 font-medium">Elevated</div>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-center shadow-2xs">
                <div className="text-base font-bold text-brand-blue-600">3 Hubs</div>
                <div className="text-[10px] text-slate-500 font-medium">Active MVP</div>
              </div>
            </div>
          </div>

          {/* 3 Active Monitoring Corridors */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Active Monitoring Corridors
              </h3>
              <span className="text-[10px] text-slate-400 font-mono">Maharashtra</span>
            </div>

            <div className="space-y-2">
              {ACTIVE_CITIES.map((c) => (
                <div
                  key={c.name}
                  onClick={() => onSelectCity(c.name)}
                  className="p-2.5 bg-white border border-slate-200 rounded-xl shadow-xs hover:border-brand-blue-400 hover:shadow-sm transition-all cursor-pointer flex items-center justify-between group"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-9 h-9 rounded-lg overflow-hidden bg-slate-100 border border-slate-200 flex-shrink-0">
                      <img
                        src={c.photo}
                        alt={c.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        onError={(e) => {
                          e.target.onerror = null
                          e.target.src = '/weather_logo.jpg'
                        }}
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-slate-900 group-hover:text-brand-blue-700 transition-colors flex items-center gap-1.5">
                        <span>{c.name}</span>
                        <span className="text-[9.5px] font-normal text-slate-400">({c.region})</span>
                      </div>
                      <div className="text-[10px] text-slate-500 truncate">
                        {c.sensors}
                      </div>
                    </div>
                  </div>

                  <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded flex-shrink-0">
                    Focus →
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Category Breakdown */}
          {analysis?.categories && analysis.categories.length > 0 && (
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
                Phenomenon Distribution
              </h3>
              <div className="space-y-2 bg-slate-50 p-3 rounded-xl border border-slate-200">
                {analysis.categories.slice(0, 5).map(({ cat, count, pct }) => (
                  <div key={cat}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-700 font-medium flex items-center gap-1">
                        <span>{CAT_ICONS[cat] || '🌧️'}</span>
                        <span>{CAT[cat] || cat}</span>
                      </span>
                      <span className="font-mono text-slate-500">{count} ({pct}%)</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-200/80 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{ width: `${pct}%`, backgroundColor: CAT_COLOR[cat] || '#0284C7' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Phase II Expansion Scope Callout */}
          <div className="p-3 bg-amber-50/70 border border-amber-200/80 rounded-xl space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm">🔒</span>
              <span className="text-xs font-bold text-amber-900">
                Phase II Geographic Coverage
              </span>
            </div>
            <p className="text-[11px] text-amber-800/90 leading-relaxed">
              15 additional Indian hubs (Delhi NCR, Bengaluru, Chennai, Kolkata, Hyderabad, Pune, etc.) are scheduled for sensor deployment.
            </p>
            <button
              onClick={onOpenUpcomingModal}
              className="w-full py-1.5 text-xs font-bold text-amber-800 bg-white border border-amber-300 hover:bg-amber-50 rounded-lg transition-colors shadow-2xs"
            >
              View Geographic Coverage Scope →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Main Geospatial Intelligence Component
   ═══════════════════════════════════════════════════════════════ */

export default function GeospatialIntelligence() {
  const {
    mapEvents, allEvents, stats,
    filters, timeRange, selectedLayer, selectedEvent,
    selectedCity, selectedState,
    loading, error, lastUpdated,
    setFilters, clearFilters, setTimeRange, setSelectedLayer,
    setSelectedEvent, clearSelectedEvent, setSelectedCity, setSelectedState,
    startPolling, stopPolling, refreshAll,
  } = useGeospatialStore()

  const openUpcomingModal = useLayoutStore((s) => s.openUpcomingModal)

  const [geoData, setGeoData] = useState(null)
  const [surroundingData, setSurroundingData] = useState(null)
  const [flyTarget, setFlyTarget] = useState({ center: [22.5, 82.0], zoom: 5 })
  const [showComparisonModal, setShowComparisonModal] = useState(false)

  // One-Click Geospatial Operational Brief Exporter
  const exportGeospatialBrief = () => {
    const brief = {
      title: 'National Meteorological Geospatial Briefing Report',
      timestamp: new Date().toISOString(),
      active_hubs: ACTIVE_CITIES.map((c) => ({
        city: c.name,
        state: c.state,
        coordinates: [c.lat, c.lon],
        sensors: c.sensors,
        events_count: mapEvents.filter((e) => (e.city || '').toLowerCase() === c.name.toLowerCase()).length,
      })),
      total_plotted_events: mapEvents.length,
      active_layer: selectedLayer,
    }
    const blob = new Blob([JSON.stringify(brief, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `geospatial_operational_brief_${Date.now()}.json`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    playNotificationChime()
  }

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  useEffect(() => {
    fetch('/india_states.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data) setGeoData(data) })
      .catch((err) => console.warn('GeoJSON states load warning:', err))

    fetch('/surrounding_countries.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data) setSurroundingData(data) })
      .catch((err) => console.warn('GeoJSON surrounding load warning:', err))
  }, [])

  // City selection handler that updates camera and filters
  const handleSelectCity = useCallback((cityName) => {
    if (!cityName) {
      setSelectedCity(null)
      setSelectedState(null)
      setFlyTarget({ center: [22.5, 82.0], zoom: 5 })
      return
    }

    const city = ACTIVE_CITIES.find((c) => c.name.toLowerCase() === cityName.toLowerCase())
    if (city) {
      setSelectedCity(city.name)
      setSelectedState('Maharashtra')
      setFlyTarget({ center: [city.lat, city.lon], zoom: 10 })
    }
  }, [setSelectedCity, setSelectedState])

  const handleClearSelection = useCallback(() => {
    setSelectedCity(null)
    setSelectedState(null)
    clearSelectedEvent()
    setFlyTarget({ center: [22.5, 82.0], zoom: 5 })
  }, [setSelectedCity, setSelectedState, clearSelectedEvent])

  // State styling with selected-state highlighting (Section 2)
  const stateStyle = useCallback((feature) => {
    const stateName = feature?.properties?.ST_NM || feature?.properties?.name || ''
    const isMaharashtra = stateName.toLowerCase() === 'maharashtra'
    const isSelected = selectedState && stateName.toLowerCase() === selectedState.toLowerCase()

    // Highlight Maharashtra when selected, or when Mumbai/Nagpur/Nashik is active
    if (isSelected || (selectedCity && isMaharashtra)) {
      return {
        fillColor: '#3B82F6',
        weight: 2.8,
        opacity: 1,
        color: '#1D4ED8', // Strong prominent boundary
        dashArray: '',
        fillOpacity: 0.35,
      }
    }

    const color = getStateColor(stateName)
    return {
      fillColor: color,
      weight: 1.3,
      opacity: 0.85,
      color: '#94A3B8', // Clean medium boundary
      dashArray: '',
      fillOpacity: 0.22,
    }
  }, [selectedState, selectedCity])

  return (
    <div className="flex h-screen bg-slate-50/70 overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Container */}
      <div className="flex flex-col flex-1 min-w-0 bg-slate-50/70 overflow-hidden">
        <Header />

        {/* ── Section 13: Geospatial Intelligence Header ── */}
        <div className="px-4 lg:px-6 py-2.5 bg-white border-b border-slate-200 flex-shrink-0 space-y-2 select-none">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base">🌐</span>
                <h1 className="text-base font-extrabold text-slate-900 tracking-tight">
                  Geospatial Intelligence Engine
                </h1>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  National Pipeline Live
                </span>
              </div>
              <p className="text-xs text-slate-500">
                National Weather Intelligence Pipeline · Satellite, Doppler Radar & Ground Sensor Array
              </p>
            </div>

            {/* Quick Hub Focus Selector Pills (Section 13) */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs text-slate-400 font-semibold mr-1">Focus Hub:</span>
              
              <button
                type="button"
                onClick={handleClearSelection}
                className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all ${
                  !selectedCity
                    ? 'bg-brand-blue-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                🇮🇳 All India
              </button>

              {ACTIVE_CITIES.map((c) => {
                const isSelected = selectedCity === c.name
                const emoji = c.name === 'Mumbai' ? '🌆' : c.name === 'Nagpur' ? '🏙️' : '🏞️'

                return (
                  <button
                    key={c.name}
                    type="button"
                    onClick={() => handleSelectCity(c.name)}
                    className={`px-2.5 py-1 text-xs font-bold rounded-lg border transition-all flex items-center gap-1.5 shadow-xs ${
                      isSelected
                        ? 'border-brand-blue-600 bg-brand-blue-50 text-brand-blue-900 ring-1 ring-brand-blue-600'
                        : 'border-slate-200 bg-white hover:border-slate-300 text-slate-800'
                    }`}
                  >
                    <span>{emoji}</span>
                    <span>{c.name}</span>
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ backgroundColor: c.color }}
                    />
                  </button>
                )
              })}

              <button
                type="button"
                onClick={openUpcomingModal}
                className="px-2.5 py-1 text-xs font-bold rounded-lg bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition-colors"
              >
                +15 Cities (Updated Soon)
              </button>
            </div>
          </div>

          {/* Controls & Filter Toolbar */}
          <div className="flex items-center gap-2 flex-wrap pt-1.5 border-t border-slate-100">
            {/* Integrated ModelSelect Dropdown (Section 4 & 5) */}
            <div className="w-52">
              <ModelSelect
                value={selectedCity}
                onChange={handleSelectCity}
                onSelectUpcoming={() => openUpcomingModal()}
                placeholder="Select City Corridor..."
                compact={true}
              />
            </div>

            {/* Time Ranges */}
            <div className="flex items-center gap-1 bg-slate-50 rounded-lg border border-slate-200 p-0.5">
              {TIME_RANGES.map((tr) => (
                <button
                  key={tr.value}
                  type="button"
                  onClick={() => setTimeRange(tr.value)}
                  className={`px-2 py-1 text-xs rounded-md font-semibold transition-colors ${
                    timeRange === tr.value
                      ? 'bg-brand-blue-600 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {tr.label}
                </button>
              ))}
            </div>

            {/* Category Select */}
            <div className="w-44">
              <SelectDropdown
                options={CATEGORIES}
                value={filters.category || ''}
                onChange={(v) => setFilters({ category: v || null })}
                placeholder="All Categories"
                compact={true}
              />
            </div>

            {/* Severity Select */}
            <div className="w-40">
              <SelectDropdown
                options={SEVERITIES}
                value={filters.severity || ''}
                onChange={(v) => setFilters({ severity: v || null })}
                placeholder="All Severities"
                compact={true}
              />
            </div>

            {/* Verification Status */}
            <div className="w-40">
              <SelectDropdown
                options={VERIFICATIONS}
                value={filters.verification_status || ''}
                onChange={(v) => setFilters({ verification_status: v || null })}
                placeholder="All Status"
                compact={true}
              />
            </div>

            {/* Clear Filters Button */}
            {(Object.values(filters).filter(Boolean).length > 0 || selectedCity) && (
              <button
                type="button"
                onClick={() => {
                  clearFilters()
                  handleClearSelection()
                }}
                className="h-8 px-2.5 text-xs text-rose-600 hover:text-rose-700 font-semibold bg-rose-50 border border-rose-200 rounded-lg shadow-xs transition-colors"
              >
                Clear Filters
              </button>
            )}

            {/* Compare 3 Hubs Button */}
            <button
              type="button"
              onClick={() => setShowComparisonModal(true)}
              className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-2xs font-bold"
              title="Compare live meteorological metrics between Mumbai, Nagpur and Nashik"
            >
              <span>⚖️</span>
              <span>Compare 3 Hubs</span>
            </button>

            {/* Export Brief Button */}
            <button
              type="button"
              onClick={exportGeospatialBrief}
              className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-2xs font-bold"
              title="Export Regional Geospatial Brief"
            >
              <span>📑</span>
              <span>Export Brief</span>
            </button>

            <div className="ml-auto text-xs text-slate-400 font-mono hidden md:block">
              {mapEvents.length} events plotted
            </div>
          </div>
        </div>

        {/* ── Section 14: Split Layout (Map on Left, Information Panel on Right) ── */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden bg-white">
          {/* Map Left Container */}
          <div className="flex-1 relative bg-white min-h-[380px] lg:min-h-0">
            <MapContainer
              center={flyTarget.center}
              zoom={flyTarget.zoom}
              style={{ height: '100%', width: '100%', backgroundColor: '#FFFFFF' }}
              zoomControl={true}
              attributionControl={false}
            >
              {/* MapTiler Streets Base Tiles */}
              <TileLayer
                url={`https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${import.meta.env.VITE_MAPTILER_API_KEY}`}
                maxZoom={19}
                tileSize={512}
                zoomOffset={-1}
                attribution='&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
              />

              {/* Surrounding countries landmass layer */}
              {surroundingData && (
                <GeoJSON
                  data={surroundingData}
                  style={() => SURROUNDING_LAND_STYLE}
                  interactive={false}
                />
              )}

              {/* Indian state boundary polygons layer (Section 2) */}
              {geoData && (
                <GeoJSON
                  data={geoData}
                  style={stateStyle}
                  onEachFeature={(feature, layer) => {
                    const stName = feature?.properties?.ST_NM || feature?.properties?.name || ''
                    const isMaha = stName.toLowerCase() === 'maharashtra'

                    layer.bindTooltip(
                      `<div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:11px;font-weight:700;color:#0F172A;">
                        📍 ${stName} ${isMaha ? '<span style="color:#059669;font-size:9.5px;font-weight:800;">(● 3 Hubs Active)</span>' : '<span style="color:#D97706;font-size:9.5px;">(Phase II)</span>'}
                      </div>`,
                      { sticky: true, className: 'map-state-tooltip' }
                    )

                    layer.on({
                      mouseover: (e) => {
                        const l = e.target
                        l.setStyle({
                          weight: 2.5,
                          color: '#0284C7',
                          fillOpacity: 0.45,
                        })
                      },
                      mouseout: (e) => {
                        const l = e.target
                        l.setStyle(stateStyle(feature))
                      },
                      click: () => {
                        if (isMaha) {
                          setSelectedState('Maharashtra')
                          setFlyTarget({ center: [19.7515, 75.7139], zoom: 7 })
                        } else {
                          openUpcomingModal()
                        }
                      },
                    })
                  }}
                />
              )}

              {/* Section 3: Distinct City Markers with Logos & Halos for Mumbai, Nagpur, Nashik */}
              {ACTIVE_CITIES.map((city) => (
                <Marker
                  key={city.name}
                  position={[city.lat, city.lon]}
                  icon={createCityMarkerIcon(city, selectedCity === city.name)}
                  eventHandlers={{
                    click: () => handleSelectCity(city.name),
                  }}
                />
              ))}

              <MapBoundsHandler />
              <MapFlightController targetCenter={flyTarget.center} targetZoom={flyTarget.zoom} />
              
              {/* Event Pins */}
              <EventMarkers
                events={mapEvents}
                layer={selectedLayer}
                onSelectEvent={(event) => setSelectedEvent(event)}
              />
            </MapContainer>

            {/* Layer Control */}
            <LayerControl selectedLayer={selectedLayer} onSelectLayer={setSelectedLayer} />

            {/* Map Legend (Section 15) */}
            <MapLegend
              layer={selectedLayer}
              selectedCity={selectedCity}
              selectedState={selectedState}
            />

            {/* Reset Camera Floating Button */}
            <button
              type="button"
              onClick={handleClearSelection}
              className="absolute top-3 left-14 z-[1000] bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold px-2.5 py-1.5 rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
              title="Reset view to whole India"
            >
              <span>🇮🇳</span>
              <span>All India</span>
            </button>

            {/* Section 16: Loading State */}
            {loading && mapEvents.length === 0 && (
              <div className="absolute inset-0 bg-white/90 backdrop-blur-xs z-[1001] flex flex-col items-center justify-center select-none">
                <div className="w-9 h-9 border-3 border-brand-blue-200 border-t-brand-blue-600 rounded-full animate-spin mb-3" />
                <div className="text-sm font-bold text-slate-900">Loading Geospatial Intelligence...</div>
                <div className="text-xs text-slate-500 mt-1">Synthesizing state boundaries & satellite telemetry</div>
              </div>
            )}

            {/* Section 17: Error State with Retry Button */}
            {error && mapEvents.length === 0 && (
              <div className="absolute inset-0 bg-white z-[1001] flex flex-col items-center justify-center p-6 text-center select-none">
                <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 text-xl font-bold mb-3 shadow-xs">
                  ⚠
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-1">
                  Geospatial Intelligence unavailable
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mb-4">
                  We couldn't load the geographic telemetry. The background services may be syncing.
                </p>
                <button
                  type="button"
                  onClick={() => refreshAll()}
                  className="btn-primary text-xs px-4 py-2 flex items-center gap-2 shadow-xs"
                >
                  <span>↻</span>
                  <span>Retry</span>
                </button>
              </div>
            )}
          </div>

          {/* Section 14: Right Information Panel */}
          <InformationPanel
            events={allEvents}
            selectedEvent={selectedEvent}
            selectedCity={selectedCity}
            onSelectCity={handleSelectCity}
            onClearSelection={handleClearSelection}
            onOpenUpcomingModal={openUpcomingModal}
          />
        </div>
      </div>

      {/* Multi-City Telemetry Comparison Matrix Modal */}
      {showComparisonModal && (
        <div
          className="fixed inset-0 z-[9995] bg-slate-900/40 backdrop-blur-2xs flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowComparisonModal(false)
          }}
        >
          <div className="w-full max-w-4xl bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150 flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-200 bg-white flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700 font-bold">
                  ⚖️
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">
                    Active Telemetry Corridors — Comparative Matrix
                  </h2>
                  <p className="text-[11px] text-slate-500">
                    Live meteorological synchronization across Mumbai, Nagpur & Nashik
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowComparisonModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            {/* Modal Body: 3-column Comparison Grid */}
            <div className="p-4 overflow-y-auto grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50/50 flex-1 scrollbar-thin">
              {ACTIVE_CITIES.map((city) => {
                const cityEvents = mapEvents.filter(
                  (e) => (e.city || '').toLowerCase() === city.name.toLowerCase()
                )
                const criticalCount = cityEvents.filter(
                  (e) => e.severity === 'critical' || e.severity === 'extreme'
                ).length

                return (
                  <div
                    key={city.name}
                    className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs flex flex-col"
                  >
                    {/* City Crest & Name */}
                    <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                      <CityCrest city={city.name} size="md" />
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">{city.name}</h3>
                        <p className="text-[11px] text-slate-400 font-medium">
                          {city.state} · {city.region}
                        </p>
                      </div>
                    </div>

                    {/* Sensor Array & Telemetry */}
                    <div className="py-3 space-y-2 text-xs flex-1">
                      <div className="flex justify-between py-1 border-b border-slate-100/80">
                        <span className="text-slate-500">Radar Reflectivity:</span>
                        <span className="font-bold text-slate-800">45–50 dBZ (Active)</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-100/80">
                        <span className="text-slate-500">Sensor Network:</span>
                        <span className="font-semibold text-slate-800">{city.sensors}</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-100/80">
                        <span className="text-slate-500">Plotted Events:</span>
                        <span className="font-bold font-mono text-blue-600">{cityEvents.length} events</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-100/80">
                        <span className="text-slate-500">Critical Hazards:</span>
                        <span className={`font-bold font-mono ${criticalCount > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                          {criticalCount} critical
                        </span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-100/80">
                        <span className="text-slate-500">Coordinates:</span>
                        <span className="font-mono text-slate-700 text-[11px]">
                          {city.lat.toFixed(2)}°N, {city.lon.toFixed(2)}°E
                        </span>
                      </div>
                      <div className="pt-1">
                        <span className="text-[10.5px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                          Phenomena Tracked:
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {city.weatherTypes.map((t) => (
                            <span
                              key={t}
                              className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 text-[10px] font-semibold"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Focus Button */}
                    <button
                      type="button"
                      onClick={() => {
                        handleSelectCity(city.name)
                        setShowComparisonModal(false)
                      }}
                      className="w-full btn-primary text-xs py-1.5 mt-2"
                    >
                      Focus {city.name} Map →
                    </button>
                  </div>
                )
              })}
            </div>

            {/* Modal Footer */}
            <div className="p-3 bg-white border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 flex-shrink-0">
              <span>Telemetry Corridors: Mumbai (Konkan) · Nagpur (Vidarbha) · Nashik (Ghats)</span>
              <button
                type="button"
                onClick={() => setShowComparisonModal(false)}
                className="btn-secondary text-xs py-1 px-3"
              >
                Close Matrix
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
