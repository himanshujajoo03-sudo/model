import React, { useRef, useState, useEffect } from 'react'
import { ACTIVE_CITIES } from '../../constants/cities'

export default function CityPreviewStrip({
  selectedCity,
  onSelectCity,
  onOpenUpcomingModal,
}) {
  const scrollRef = useRef(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(true)
  const [activeZone, setActiveZone] = useState('All')

  const ZONES = ['All', 'West', 'North', 'South', 'East', 'Central', 'Northeast']

  const filteredCities = activeZone === 'All'
    ? ACTIVE_CITIES
    : ACTIVE_CITIES.filter((c) => c.zone === activeZone)

  const checkScroll = () => {
    if (scrollRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current
      setCanScrollLeft(scrollLeft > 10)
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 10)
    }
  }

  useEffect(() => {
    checkScroll()
    window.addEventListener('resize', checkScroll)
    return () => window.removeEventListener('resize', checkScroll)
  }, [filteredCities])

  const scroll = (direction) => {
    if (scrollRef.current) {
      const offset = direction === 'left' ? -320 : 320
      scrollRef.current.scrollBy({ left: offset, behavior: 'smooth' })
      setTimeout(checkScroll, 350)
    }
  }

  const CITY_ICONS = {
    Mumbai: '🌆',
    Nagpur: '🏙️',
    Nashik: '🏞️',
    Pune: '🏛️',
    Delhi: '🏛️',
    Bengaluru: '🌳',
    Chennai: '🏖️',
    Kolkata: '🌉',
    Hyderabad: '🏰',
    Ahmedabad: '🕌',
    Jaipur: '🏰',
    Lucknow: '🏛️',
    Srinagar: '🏔️',
    Shimla: '❄️',
    Kochi: '🌴',
    Guwahati: '🌊',
  }

  return (
    <div className="w-full select-none">
      {/* Header Label + Zone Filters + Scroll Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[11px] font-bold text-slate-900 uppercase tracking-wider">
            Pan-India Weather Corridors ({ACTIVE_CITIES.length} Cities)
          </span>
          <span className="text-[10px] text-slate-400 font-medium hidden sm:inline">
            · Live & 1-Month Historical Telemetry
          </span>
        </div>

        {/* Zone Filter Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {ZONES.map((zone) => (
            <button
              key={zone}
              type="button"
              onClick={() => setActiveZone(zone)}
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full transition-all ${
                activeZone === zone
                  ? 'bg-brand-blue-600 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {zone}
            </button>
          ))}
        </div>

        {/* Scroll Chevrons + Search Explorer Button */}
        <div className="flex items-center gap-2">
          {onOpenUpcomingModal && (
            <button
              type="button"
              onClick={onOpenUpcomingModal}
              className="text-[11px] text-brand-blue-600 hover:text-brand-blue-700 font-semibold flex items-center gap-1.5 transition-colors mr-1"
            >
              <span>🔍 City Explorer</span>
            </button>
          )}

          {/* Left/Right Scroll Arrows */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={!canScrollLeft}
              onClick={() => scroll('left')}
              className="w-6 h-6 rounded-md border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center text-xs font-bold text-slate-700 shadow-2xs transition-all"
              title="Scroll left"
              aria-label="Scroll left"
            >
              ‹
            </button>
            <button
              type="button"
              disabled={!canScrollRight}
              onClick={() => scroll('right')}
              className="w-6 h-6 rounded-md border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center text-xs font-bold text-slate-700 shadow-2xs transition-all"
              title="Scroll right"
              aria-label="Scroll right"
            >
              ›
            </button>
          </div>
        </div>
      </div>

      {/* Horizontal Scroll Strip */}
      <div
        ref={scrollRef}
        onScroll={checkScroll}
        className="flex items-stretch gap-3 overflow-x-auto pb-2 scrollbar-thin scroll-smooth"
      >
        {filteredCities.map((city) => {
          const isSelected =
            Boolean(selectedCity) &&
            (selectedCity.toLowerCase() === city.name.toLowerCase() ||
              (city.aliases && city.aliases.includes(selectedCity.toLowerCase())))
          const cityIcon = CITY_ICONS[city.name] || '📍'

          return (
            <div
              key={city.name}
              onClick={() => onSelectCity(isSelected ? null : city.name)}
              className={`flex-shrink-0 w-[280px] sm:w-[300px] cursor-pointer rounded-2xl border bg-white overflow-hidden transition-all duration-200 shadow-xs hover:shadow-card-hover group ${
                isSelected
                  ? 'border-brand-blue-600 ring-2 ring-brand-blue-500/20'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              {/* Photo Banner */}
              <div className="relative h-24 w-full overflow-hidden bg-slate-800">
                <img
                  src={city.photo}
                  alt={city.name}
                  className="w-full h-full object-cover object-center transition-transform duration-300 group-hover:scale-105 opacity-75"
                  onError={(e) => {
                    e.target.onerror = null
                    e.target.src = '/city_mumbai.jpg'
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/40 to-transparent" />

                {/* Top Floating Badges */}
                <div className="absolute top-2 left-2 right-2 flex items-center justify-between">
                  {/* City Icon Container */}
                  <div className="w-6 h-6 rounded-md bg-white/90 backdrop-blur-xs border border-white/60 flex items-center justify-center text-xs shadow-xs">
                    <span>{cityIcon}</span>
                  </div>

                  {/* Live Status Pill */}
                  <span className="text-[9.5px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/90 text-white backdrop-blur-xs shadow-xs flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    Live & Past 30D
                  </span>
                </div>

                {/* Bottom Overlay: City Name & Region */}
                <div className="absolute bottom-2 left-3 right-3 flex items-end justify-between text-white">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span
                        className="w-2 h-2 rounded-full ring-2 ring-white/60"
                        style={{ backgroundColor: city.color }}
                      />
                      <span className="font-bold text-sm tracking-tight text-white drop-shadow-sm">
                        {city.name}
                      </span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-white/20 backdrop-blur-xs font-semibold text-white/90">
                        {city.tagline}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-200 font-medium block mt-0.5">
                      {city.state} · {city.zone} India
                    </span>
                  </div>

                  <span
                    className={`text-[9.5px] font-bold px-2 py-0.5 rounded-md backdrop-blur-xs transition-colors shadow-2xs ${
                      isSelected
                        ? 'bg-brand-blue-600 text-white'
                        : 'bg-white/90 text-slate-900 group-hover:bg-white'
                    }`}
                  >
                    {isSelected ? 'Selected' : 'Filter'}
                  </span>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-2.5">
                <p className="text-[10.5px] text-slate-600 line-clamp-2 leading-relaxed mb-2">
                  {city.description}
                </p>

                {/* Weather tags */}
                <div className="flex flex-wrap gap-1 mb-2">
                  {city.weatherTypes.map((type) => (
                    <span
                      key={type}
                      className="text-[9px] font-medium px-1.5 py-0.5 bg-slate-50 text-slate-700 rounded border border-slate-200"
                    >
                      {type}
                    </span>
                  ))}
                </div>

                {/* Bottom sensors meta */}
                <div className="pt-1.5 border-t border-slate-100 flex items-center justify-between text-[9.5px] text-slate-400">
                  <span className="truncate">{city.sensors}</span>
                  <span className="text-emerald-700 font-bold flex items-center gap-1 flex-shrink-0 ml-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    Active Hub
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
