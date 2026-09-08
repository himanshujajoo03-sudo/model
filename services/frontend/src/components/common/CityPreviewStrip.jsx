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
  }, [])

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
    Nasik: '🏞️',
  }

  return (
    <div className="w-full select-none">
      {/* Header Label + Scroll Controls */}
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[11px] font-bold text-slate-900 uppercase tracking-wider">
            Active City Corridors (3 MVP Hubs)
          </span>
          <span className="text-[10px] text-slate-400 font-medium hidden sm:inline">
            · High-Precision Doppler Telemetry
          </span>
        </div>

        {/* Scroll Chevrons + Other Cities Button */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenUpcomingModal}
            className="text-[11px] text-brand-blue-600 hover:text-brand-blue-700 font-semibold flex items-center gap-1.5 transition-colors mr-1"
          >
            <span>Other Indian Cities</span>
            <span className="text-[10px] font-bold px-1.5 py-0.2 bg-amber-50 text-amber-700 border border-amber-200 rounded">
              Updated Soon
            </span>
          </button>

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
        {ACTIVE_CITIES.map((city) => {
          const isSelected =
            Boolean(selectedCity) &&
            (selectedCity.toLowerCase() === city.name.toLowerCase() ||
              (city.aliases && city.aliases.includes(selectedCity.toLowerCase())))
          const cityIcon = CITY_ICONS[city.name] || '📍'

          return (
            <div
              key={city.name}
              onClick={() => onSelectCity(isSelected ? null : city.name)}
              className={`flex-shrink-0 w-[280px] sm:w-[310px] cursor-pointer rounded-2xl border bg-white overflow-hidden transition-all duration-200 shadow-xs hover:shadow-card-hover group ${
                isSelected
                  ? 'border-brand-blue-600 ring-2 ring-brand-blue-500/20'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              {/* Photo Banner */}
              <div className="relative h-28 w-full overflow-hidden bg-slate-100">
                <img
                  src={city.photo}
                  alt={city.name}
                  className="w-full h-full object-cover object-center transition-transform duration-300 group-hover:scale-105"
                  onError={(e) => {
                    e.target.onerror = null
                    e.target.src = ''
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-slate-950/30 to-transparent" />

                {/* Top Floating Badges */}
                <div className="absolute top-2 left-2 right-2 flex items-center justify-between">
                  {/* City Icon Container */}
                  <div className="w-7 h-7 rounded-lg bg-white/90 backdrop-blur-xs border border-white/60 flex items-center justify-center text-sm shadow-xs">
                    <span>{cityIcon}</span>
                  </div>

                  {/* Live Status Pill */}
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/90 text-white backdrop-blur-xs shadow-xs flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    Live MVP
                  </span>
                </div>

                {/* Bottom Overlay: City Name & Region */}
                <div className="absolute bottom-2.5 left-3 right-3 flex items-end justify-between text-white">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span
                        className="w-2.5 h-2.5 rounded-full ring-2 ring-white/60"
                        style={{ backgroundColor: city.color }}
                      />
                      <span className="font-bold text-sm tracking-tight text-white drop-shadow-sm">
                        {city.name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-white/20 backdrop-blur-xs font-semibold text-white/90">
                        {city.tagline}
                      </span>
                    </div>
                    <span className="text-[10.5px] text-slate-200 font-medium block mt-0.5">
                      {city.state} · {city.region}
                    </span>
                  </div>

                  <span
                    className={`text-[10px] font-bold px-2.5 py-1 rounded-lg backdrop-blur-xs transition-colors shadow-2xs ${
                      isSelected
                        ? 'bg-brand-blue-600 text-white'
                        : 'bg-white/90 text-slate-900 group-hover:bg-white'
                    }`}
                  >
                    {isSelected ? 'Filtered' : 'Filter'}
                  </span>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-3">
                <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed mb-2.5">
                  {city.description}
                </p>

                {/* Weather tags */}
                <div className="flex flex-wrap gap-1 mb-2.5">
                  {city.weatherTypes.map((type) => (
                    <span
                      key={type}
                      className="text-[9.5px] font-medium px-1.5 py-0.5 bg-slate-50 text-slate-700 rounded-md border border-slate-200"
                    >
                      {type}
                    </span>
                  ))}
                </div>

                {/* Bottom sensors meta */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
                  <span className="truncate">{city.sensors}</span>
                  <span className="text-emerald-700 font-bold flex items-center gap-1 flex-shrink-0 ml-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    Active
                  </span>
                </div>
              </div>
            </div>
          )
        })}

        {/* Teaser Card: Other Indian Cities (Phase II) */}
        <div
          onClick={onOpenUpcomingModal}
          className="flex-shrink-0 w-[240px] sm:w-[260px] cursor-pointer rounded-2xl border border-dashed border-amber-300 bg-amber-50/40 p-4 flex flex-col justify-between hover:bg-amber-50/80 transition-all group"
        >
          <div>
            <div className="w-8 h-8 rounded-xl bg-amber-100 border border-amber-200 flex items-center justify-center text-amber-800 text-sm mb-2.5 shadow-2xs">
              <span>🔒</span>
            </div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              <span className="text-xs font-bold text-amber-950">
                15+ More Indian Cities
              </span>
            </div>
            <p className="text-[11px] text-amber-800/80 leading-relaxed mb-3">
              Pune, Delhi NCR, Bengaluru, Hyderabad, Chennai, Kolkata & more scheduled for Phase II radar telemetry integration.
            </p>
          </div>

          <div className="pt-2.5 border-t border-amber-200/60 flex items-center justify-between">
            <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">
              Updated Soon
            </span>
            <span className="text-xs text-amber-700 font-bold group-hover:translate-x-0.5 transition-transform">
              Explore →
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
