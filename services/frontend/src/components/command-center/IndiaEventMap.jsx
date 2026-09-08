import React, { useEffect, useState, useMemo, useRef } from 'react'
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
  useMap,
} from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import useCommandCenterStore from '../../stores/commandCenterStore'
import EventPopover from './EventPopover'
import { ACTIVE_CITIES, UPCOMING_CITIES } from '../../constants/cities'
import {
  getStateColor,
  SURROUNDING_LAND_STYLE,
  DEFAULT_STATE_STYLE,
  HOVER_STATE_STYLE,
} from '../../constants/mapTheme'

const CATEGORY_COLORS = {
  heavy_rainfall: '#0284C7',
  rainfall: '#0284C7',
  urban_flooding: '#1D4ED8',
  flood: '#1E3A8A',
  heatwave: '#EA580C',
  thunderstorm: '#DC2626',
  lightning: '#D97706',
  strong_wind: '#475569',
  hailstorm: '#0D9488',
  dust_storm: '#B45309',
  cyclone: '#B91C1C',
  fog: '#64748B',
}

const SEVERITY_SIZES = {
  low: 9,
  moderate: 12,
  high: 16,
  extreme: 20,
  critical: 24,
}

function createEventIcon(category, severity) {
  const color = CATEGORY_COLORS[category] || '#0284C7'
  const size = SEVERITY_SIZES[severity] || 12
  const isCritical = severity === 'extreme' || severity === 'critical'

  return L.divIcon({
    className: '',
    html: `<div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:${color};
      border:2px solid #FFFFFF;
      box-shadow:0 2px 6px rgba(15,23,42,0.25)${isCritical ? `, 0 0 10px ${color}80` : ''};
      ${isCritical ? 'animation: livePulse 2s ease-in-out infinite;' : ''}
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

// Simulated Doppler Radar Reflectivity concentric rings
function createRadarSimulationIcon(city) {
  return L.divIcon({
    className: 'radar-simulation-ring',
    html: `
      <div style="position:relative;width:160px;height:160px;margin-left:-80px;margin-top:-80px;pointer-events:none;">
        <div style="position:absolute;inset:0;border-radius:50%;border:1.5px dashed ${city.color}88;animation:spin 12s linear infinite;"></div>
        <div style="position:absolute;inset:28px;border-radius:50%;border:1.5px solid ${city.color}44;"></div>
        <div style="position:absolute;inset:56px;border-radius:50%;border:1px dotted ${city.color}99;"></div>
        <div style="position:absolute;top:50%;left:50%;width:50%;height:2px;background:linear-gradient(to right, ${city.color}, transparent);transform-origin:0 0;animation:spin 3s linear infinite;"></div>
        <div style="position:absolute;top:6px;right:6px;background:#FFFFFF;border:1.5px solid ${city.color};border-radius:5px;padding:1.5px 5px;font-size:8.5px;font-weight:800;color:${city.color};box-shadow:0 2px 5px rgba(0,0,0,0.12);font-family:sans-serif;">
          ${city.name} DWR · 48dBZ
        </div>
      </div>
    `,
    iconSize: [160, 160],
    iconAnchor: [80, 80],
  })
}

// Custom Beacon Icon for the 3 active cities: Mumbai, Nagpur, Nashik
function createCityBeaconIcon(city, isSelected) {
  const iconEmoji = city.name === 'Mumbai' ? '🌆' : city.name === 'Nagpur' ? '🏙️' : '🏞️'
  const regionLabel = city.name === 'Nagpur' ? 'Vidarbha' : (city.name === 'Nashik' || city.name === 'Nasik') ? 'Ghats' : 'Konkan'
  const haloColor = isSelected ? '#2563EB' : city.color
  const activeBorder = isSelected ? '2px solid #2563EB' : '1px solid #CBD5E1'

  return L.divIcon({
    className: 'city-leaflet-marker',
    html: `
      <div style="position:relative;display:flex;flex-direction:column;align-items:center;pointer-events:auto;cursor:pointer;">
        <!-- Pulsing Ripple -->
        <div class="beacon-wave" style="
          position:absolute;
          top:-6px;
          width:28px;
          height:28px;
          border-radius:50%;
          border:2px solid ${haloColor};
          pointer-events:none;
        "></div>
        
        <!-- Central City Pin with Icon -->
        <div style="
          width:26px;
          height:26px;
          border-radius:50%;
          background:#FFFFFF;
          border:2.5px solid ${city.color};
          box-shadow:0 3px 8px rgba(15,23,42,0.25);
          display:flex;
          align-items:center;
          justify-content:center;
          font-size:13px;
          z-index:2;
        ">
          <span>${iconEmoji}</span>
        </div>
        
        <!-- City Label Badge -->
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
          box-shadow:0 2px 6px rgba(15,23,42,0.1);
          white-space:nowrap;
          display:flex;
          flex-direction:column;
          align-items:center;
          line-height:1.2;
          z-index:2;
        ">
          <div style="display:flex;align-items:center;gap:3px;">
            <span style="width:4px;height:4px;border-radius:50%;background:${city.color};"></span>
            <span>${city.name}</span>
          </div>
          <span style="font-size:8.5px;color:#64748B;font-weight:600;">Maharashtra · ${regionLabel}</span>
        </div>
      </div>
    `,
    iconSize: [84, 56],
    iconAnchor: [42, 13],
  })
}

// Controller component to reset map view
function MapController({ resetTrigger, centerCity }) {
  const map = useMap()

  useEffect(() => {
    map.invalidateSize()
  }, [map])

  useEffect(() => {
    if (resetTrigger > 0) {
      map.setView([22.5, 82.0], 5, { animate: true })
    }
  }, [resetTrigger, map])

  useEffect(() => {
    if (centerCity) {
      map.setView([centerCity.lat, centerCity.lon], 9, { animate: true })
    }
  }, [centerCity, map])

  return null
}

function MapBoundsHandler() {
  const map = useMap()
  const setMapBounds = useCommandCenterStore((s) => s.setMapBounds)

  useEffect(() => {
    const update = () => {
      const b = map.getBounds()
      setMapBounds({
        min_lat: b.getSouth(),
        max_lat: b.getNorth(),
        min_lon: b.getWest(),
        max_lon: b.getEast(),
      })
    }
    map.on('moveend', update)
    map.on('zoomend', update)
    return () => {
      map.off('moveend', update)
      map.off('zoomend', update)
    }
  }, [map, setMapBounds])

  return null
}

export default function IndiaEventMap() {
  const mapEvents = useCommandCenterStore((s) => s.mapEvents)
  const lastUpdated = useCommandCenterStore((s) => s.lastUpdated)
  const setFilters = useCommandCenterStore((s) => s.setFilters)

  const mapContainerRef = useRef(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Map GeoJSON Datasets
  const [indiaGeoData, setIndiaGeoData] = useState(null)
  const [surroundingGeoData, setSurroundingGeoData] = useState(null)

  // Interactive Map Controls State
  const [showStateBorders, setShowStateBorders] = useState(true)
  const [showCityBeacons, setShowCityBeacons] = useState(true)
  const [showUpcomingPins, setShowUpcomingPins] = useState(false)
  const [showRadarSimulation, setShowRadarSimulation] = useState(false)
  const [severityFilter, setSeverityFilter] = useState('all') // 'all', 'critical', 'high', 'moderate'
  const [timelineStep, setTimelineStep] = useState('realtime') // '24h', '12h', '6h', '1h', 'realtime'
  const [isPlayingTimeline, setIsPlayingTimeline] = useState(false)
  const [resetTrigger, setResetTrigger] = useState(0)
  const [focusedCity, setFocusedCity] = useState(null)
  const [hoveredState, setHoveredState] = useState(null)

  const TIMELINE_STEPS = ['24h', '12h', '6h', '1h', 'realtime']

  // Automated timeline playback ticker
  useEffect(() => {
    let interval = null
    if (isPlayingTimeline) {
      interval = setInterval(() => {
        setTimelineStep((prev) => {
          const idx = TIMELINE_STEPS.indexOf(prev)
          const nextIdx = (idx + 1) % TIMELINE_STEPS.length
          return TIMELINE_STEPS[nextIdx]
        })
      }, 2000)
    }
    return () => clearInterval(interval)
  }, [isPlayingTimeline])

  // Fullscreen event listener
  useEffect(() => {
    const handleFs = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handleFs)
    return () => document.removeEventListener('fullscreenchange', handleFs)
  }, [])

  const toggleFullscreen = () => {
    if (!mapContainerRef.current) return
    if (!document.fullscreenElement) {
      mapContainerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {})
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {})
    }
  }

  // Load GeoJSON files from /public
  useEffect(() => {
    fetch('/india_states.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setIndiaGeoData(data))
      .catch((err) => console.warn('Failed to load india_states.json:', err))

    fetch('/surrounding_countries.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setSurroundingGeoData(data))
      .catch((err) =>
        console.warn('Failed to load surrounding_countries.json:', err)
      )
  }, [])

  // Filtered Events based on Severity and Timeline
  const filteredEvents = useMemo(() => {
    let list = mapEvents
    if (severityFilter === 'critical') {
      list = list.filter((e) => e.severity === 'critical' || e.severity === 'extreme')
    } else if (severityFilter === 'high') {
      list = list.filter((e) => e.severity === 'high' || e.severity === 'critical' || e.severity === 'extreme')
    } else if (severityFilter === 'moderate') {
      list = list.filter((e) => e.severity === 'moderate')
    }

    if (timelineStep === '1h') {
      return list.slice(0, Math.max(2, Math.floor(list.length * 0.45)))
    } else if (timelineStep === '6h') {
      return list.slice(0, Math.max(3, Math.floor(list.length * 0.7)))
    } else if (timelineStep === '12h') {
      return list.slice(0, Math.max(4, Math.floor(list.length * 0.85)))
    }
    return list
  }, [mapEvents, severityFilter, timelineStep])

  // Event count per state for tooltips
  const eventsByState = useMemo(() => {
    const counts = {}
    filteredEvents.forEach((ev) => {
      const st = ev.state || 'Unknown'
      counts[st] = (counts[st] || 0) + 1
    })
    return counts
  }, [filteredEvents])

  // Style function for individual Indian states
  const stateStyle = (feature) => {
    const stateName =
      feature?.properties?.NAME_1 ||
      feature?.properties?.st_nm ||
      feature?.properties?.State_Name ||
      'Unknown'

    const isHovered = hoveredState === stateName

    return {
      fillColor: getStateColor(stateName),
      fillOpacity: isHovered ? 0.95 : 0.82,
      color: isHovered ? HOVER_STATE_STYLE.color : DEFAULT_STATE_STYLE.color,
      weight: isHovered ? HOVER_STATE_STYLE.weight : DEFAULT_STATE_STYLE.weight,
      opacity: isHovered ? 1 : 0.9,
    }
  }

  // State interaction handler
  const onEachState = (feature, layer) => {
    const stateName =
      feature?.properties?.NAME_1 ||
      feature?.properties?.st_nm ||
      feature?.properties?.State_Name ||
      'State'

    const count = eventsByState[stateName] || 0

    layer.on({
      mouseover: () => setHoveredState(stateName),
      mouseout: () => setHoveredState(null),
    })

    layer.bindTooltip(
      `<div style="font-family:'Plus Jakarta Sans',sans-serif;padding:3px 8px;font-size:11px;font-weight:700;color:#0F172A;background:#FFFFFF;border-radius:6px;border:1px solid #CBD5E1;box-shadow:0 4px 12px rgba(15,23,42,0.1);">
        <span>${stateName}</span>
        ${count > 0 ? `<span style="margin-left:6px;padding:1px 5px;border-radius:4px;background:#EFF6FF;color:#1D4ED8;font-size:10px;font-weight:800;">${count} event${count !== 1 ? 's' : ''}</span>` : ''}
      </div>`,
      { sticky: true, className: 'state-tooltip' }
    )
  }

  const fmt = (iso) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  }

  return (
    <div ref={mapContainerRef} className="h-full bg-white border border-slate-200 rounded-2xl overflow-hidden flex flex-col shadow-xs">
      {/* Map Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between px-3.5 py-2.5 border-b border-slate-200 bg-white flex-shrink-0 gap-2">
        <div className="flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.6)]" />
          <span className="text-[11px] font-bold tracking-wider text-slate-900 uppercase">
            National Event Intelligence Map
          </span>
          <span className="text-[10px] text-slate-400 font-medium hidden sm:inline">
            · Real-Time Geospatial Telemetry
          </span>
        </div>

        {/* Toolbar Controls */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {/* Quick Severity Filter Chips */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-xl border border-slate-200 text-[10px] font-bold">
            {[
              { id: 'all', label: `All (${mapEvents.length})` },
              { id: 'critical', label: 'Critical' },
              { id: 'high', label: 'High+' },
              { id: 'moderate', label: 'Moderate' },
            ].map((chip) => (
              <button
                key={chip.id}
                type="button"
                onClick={() => setSeverityFilter(chip.id)}
                className={`px-2 py-0.5 rounded-lg transition-colors ${
                  severityFilter === chip.id
                    ? 'bg-white text-blue-700 shadow-2xs font-extrabold border border-blue-200'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {chip.label}
              </button>
            ))}
          </div>

          {/* Layer Toggles */}
          <button
            type="button"
            onClick={() => setShowRadarSimulation(!showRadarSimulation)}
            className={`btn-node text-[10.5px] py-1 px-2.5 ${
              showRadarSimulation
                ? 'bg-purple-50 text-purple-700 border-purple-300 font-bold'
                : 'text-slate-500'
            }`}
            title="Toggle Doppler Weather Radar Simulation Overlays"
          >
            <span
              className={`node-dot ${
                showRadarSimulation ? 'bg-purple-600 animate-pulse' : 'bg-slate-300'
              }`}
            />
            <span>Doppler Radar</span>
          </button>

          <button
            type="button"
            onClick={() => setShowStateBorders(!showStateBorders)}
            className={`btn-node text-[10.5px] py-1 px-2.5 ${
              showStateBorders
                ? 'bg-brand-blue-50 text-brand-blue-700 border-brand-blue-300'
                : 'text-slate-500'
            }`}
            title="Toggle Indian State Boundaries"
          >
            <span
              className={`node-dot ${
                showStateBorders ? 'bg-brand-blue-600' : 'bg-slate-300'
              }`}
            />
            <span>States</span>
          </button>

          <button
            type="button"
            onClick={() => setShowCityBeacons(!showCityBeacons)}
            className={`btn-node text-[10.5px] py-1 px-2.5 ${
              showCityBeacons
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                : 'text-slate-500'
            }`}
            title="Toggle 3 MVP City Beacons"
          >
            <span
              className={`node-dot ${
                showCityBeacons ? 'bg-emerald-600' : 'bg-slate-300'
              }`}
            />
            <span>3 Hubs</span>
          </button>

          <button
            type="button"
            onClick={() => setShowUpcomingPins(!showUpcomingPins)}
            className={`btn-node text-[10.5px] py-1 px-2.5 ${
              showUpcomingPins
                ? 'bg-amber-50 text-amber-800 border-amber-300'
                : 'text-slate-500'
            }`}
            title="Toggle Upcoming Cities"
          >
            <span
              className={`node-dot ${
                showUpcomingPins ? 'bg-amber-500' : 'bg-slate-300'
              }`}
            />
            <span>{showUpcomingPins ? 'Phase II On' : 'Phase II'}</span>
          </button>

          {/* Reset View Button */}
          <button
            type="button"
            onClick={() => {
              setFocusedCity(null)
              setResetTrigger((c) => c + 1)
            }}
            className="btn-secondary text-[10.5px] py-1 px-2"
            title="Reset to Full India Overview"
          >
            ↺ Reset
          </button>

          {/* Fullscreen Button */}
          <button
            type="button"
            onClick={toggleFullscreen}
            className="btn-secondary text-[10.5px] py-1 px-2"
            title="Toggle Map Fullscreen"
          >
            {isFullscreen ? '✕ Exit' : '⛶ Full'}
          </button>

          {/* Telemetry Counter */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-50 border border-slate-200 text-[10px] text-slate-700 font-semibold shadow-xs">
            <span className="text-brand-blue-600 font-extrabold">
              {filteredEvents.length}
            </span>
            <span>Shown</span>
            <span className="text-slate-300 mx-0.5">|</span>
            <span className="flex items-center gap-1 text-[9.5px] text-slate-500">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              {fmt(lastUpdated)}
            </span>
          </div>
        </div>
      </div>

      {/* Interactive Map Container */}
      <div className="flex-1 relative bg-white">
        <MapContainer
          center={[22.5, 82.0]}
          zoom={5}
          minZoom={4}
          maxZoom={14}
          style={{ height: '100%', width: '100%', background: '#FFFFFF' }}
          zoomControl={true}
          attributionControl={false}
        >
          {/* Light CartoDB Positron Base Tiles */}
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png"
            maxZoom={19}
            subdomains="abcd"
            opacity={0.9}
          />

          {/* Surrounding Countries */}
          {surroundingGeoData && (
            <GeoJSON
              key="surrounding-countries"
              data={surroundingGeoData}
              style={() => SURROUNDING_LAND_STYLE}
            />
          )}

          {/* Indian States */}
          {showStateBorders && indiaGeoData && (
            <GeoJSON
              key={`india-states-${hoveredState || 'idle'}`}
              data={indiaGeoData}
              style={stateStyle}
              onEachFeature={onEachState}
            />
          )}

          {/* Clean CartoDB Geographic Boundary Labels */}
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png"
            maxZoom={19}
            subdomains="abcd"
            opacity={0.7}
          />

          {/* Handlers */}
          <MapController
            resetTrigger={resetTrigger}
            centerCity={focusedCity}
          />
          <MapBoundsHandler />

          {/* Doppler Radar Simulation Rings (Over Mumbai, Nagpur, Nashik) */}
          {showRadarSimulation &&
            ACTIVE_CITIES.map((city) => (
              <Marker
                key={`radar-${city.name}`}
                position={[city.lat, city.lon]}
                icon={createRadarSimulationIcon(city)}
                interactive={false}
              />
            ))}

          {/* 3 Active MVP City Beacons: Mumbai, Nagpur, Nashik */}
          {showCityBeacons &&
            ACTIVE_CITIES.map((city) => (
              <Marker
                key={city.name}
                position={[city.lat, city.lon]}
                icon={createCityBeaconIcon(city)}
                eventHandlers={{
                  click: () => {
                    setFocusedCity(city)
                    setFilters({ city: city.name })
                  },
                }}
              >
                <Popup>
                  <div className="p-3 w-64">
                    {/* Photo */}
                    <div className="relative h-20 w-full rounded-lg overflow-hidden mb-2 bg-slate-100">
                      <img
                        src={city.photo}
                        alt={city.name}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 to-transparent" />
                      <div className="absolute bottom-1.5 left-2 text-white font-bold text-xs">
                        {city.name} · {city.state}
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-600 mb-2 leading-relaxed">
                      {city.description}
                    </p>

                    <div className="flex items-center justify-between text-[10px] pt-1.5 border-t border-slate-100">
                      <span className="text-emerald-600 font-semibold">
                        ● Active Telemetry
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          setFocusedCity(city)
                          setFilters({ city: city.name })
                        }}
                        className="text-brand-blue-600 hover:text-brand-blue-700 font-bold"
                      >
                        Select & View Latest Data →
                      </button>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}

          {/* Upcoming Cities Pins (Optional preview) */}
          {showUpcomingPins &&
            UPCOMING_CITIES.map((city) => (
              <Marker
                key={city.name}
                position={[city.lat, city.lon]}
                icon={L.divIcon({
                  className: '',
                  html: `
                    <div style="display:flex;align-items:center;gap:3px;background:#FFF7ED;border:1px solid #FED7AA;color:#C2410C;font-family:'Plus Jakarta Sans',sans-serif;font-size:9.5px;font-weight:700;padding:1px 5px;border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,0.06);white-space:nowrap;">
                      <span style="width:4px;height:4px;border-radius:50%;background:#F97316;"></span>
                      ${city.name} (Soon)
                    </div>
                  `,
                  iconSize: [80, 20],
                })}
              />
            ))}

          {/* Filtered Weather Events Markers */}
          {filteredEvents.map((event) => {
            if (!event.latitude || !event.longitude) return null
            return (
              <Marker
                key={event.event_id}
                position={[event.latitude, event.longitude]}
                icon={createEventIcon(event.event_category, event.severity)}
                eventHandlers={{
                  click: () =>
                    useCommandCenterStore.getState().setSelectedEvent(event),
                }}
              >
                <Popup>
                  <EventPopover event={event} />
                </Popup>
              </Marker>
            )
          })}
        </MapContainer>

        {/* Floating Timeline Playback Scrubber (Top-Right) */}
        <div className="absolute top-3 right-3 z-[400] bg-white/95 backdrop-blur-xs border border-slate-200 rounded-xl px-3 py-2 shadow-md flex items-center gap-2.5 text-xs select-none pointer-events-auto">
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setIsPlayingTimeline(!isPlayingTimeline)}
              className={`px-2 py-1 rounded-lg font-bold text-[10.5px] border transition-colors flex items-center gap-1 ${
                isPlayingTimeline
                  ? 'bg-amber-50 border-amber-300 text-amber-800'
                  : 'bg-slate-100 hover:bg-slate-200/80 border-slate-200 text-slate-700'
              }`}
              title="Simulate Event Propagation Over Time"
            >
              <span>{isPlayingTimeline ? '⏸ Pause' : '▶ Play'}</span>
            </button>
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-[10px] font-bold">
            {['24h', '12h', '6h', '1h', 'realtime'].map((step) => (
              <button
                key={step}
                type="button"
                onClick={() => {
                  setIsPlayingTimeline(false)
                  setTimelineStep(step)
                }}
                className={`px-1.5 py-0.5 rounded transition-colors ${
                  timelineStep === step
                    ? 'bg-blue-600 text-white font-extrabold shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {step === 'realtime' ? 'Now' : step}
              </button>
            ))}
          </div>
        </div>

        {/* Floating Map Legend (Bottom-Left) */}
        <div className="absolute bottom-3 left-3 z-[400] bg-white/95 backdrop-blur-xs border border-slate-200 rounded-xl p-3 shadow-md text-xs select-none max-w-[260px] pointer-events-auto">
          <div className="text-[10px] font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Map Legend</span>
            <span className="text-[9px] font-semibold text-brand-blue-600">
              India Grid
            </span>
          </div>

          {/* City Beacons */}
          <div className="mb-2.5 pb-2 border-b border-slate-100">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Active Hubs
            </span>
            <div className="flex items-center gap-2.5 text-[11px] font-semibold text-slate-700">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#0284C7]" />
                Mumbai
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#EA580C]" />
                Nagpur
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#059669]" />
                Nashik
              </span>
            </div>
          </div>

          {/* Event Severity Dots */}
          <div>
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Event Severity
            </span>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[10.5px] text-slate-600 font-medium">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#DC2626]" />
                Critical / Extreme
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#EA580C]" />
                High Severity
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#0284C7]" />
                Moderate
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#64748B]" />
                Low / Routine
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
