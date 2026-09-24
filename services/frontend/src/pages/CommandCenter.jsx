import React, { useEffect } from 'react'
import useCommandCenterStore from '../stores/commandCenterStore'
import useLayoutStore from '../stores/layoutStore'
import Sidebar from '../components/command-center/Sidebar'
import Header from '../components/command-center/Header'
import KpiStrip from '../components/command-center/KpiStrip'
import IndiaEventMap from '../components/command-center/IndiaEventMap'
import MapControls from '../components/command-center/MapControls'
import LiveEventFeed from '../components/command-center/LiveEventFeed'
import CityPreviewStrip from '../components/common/CityPreviewStrip'
import SelectedCityInfo from '../components/command-center/SelectedCityInfo'

export default function CommandCenter() {
  const stats = useCommandCenterStore((s) => s.stats)
  const health = useCommandCenterStore((s) => s.health)
  const filters = useCommandCenterStore((s) => s.filters)
  const timeHorizon = useCommandCenterStore((s) => s.timeHorizon)
  const setTimeHorizon = useCommandCenterStore((s) => s.setTimeHorizon)
  const setFilters = useCommandCenterStore((s) => s.setFilters)
  const startPolling = useCommandCenterStore((s) => s.startPolling)
  const stopPolling = useCommandCenterStore((s) => s.stopPolling)
  const openUpcomingModal = useLayoutStore((s) => s.openUpcomingModal)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  return (
    <div className="flex min-h-screen bg-slate-50/70">
      {/* Responsive Collapsible Sidebar */}
      <Sidebar health={health} />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 bg-slate-50/70">
        <Header />

        <div className="flex-1 flex flex-col px-4 lg:px-6 py-4 gap-4 bg-slate-50/70">
          {/* Top Row: Page Title + Time Horizon Selector */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 flex-shrink-0 bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                  Pan-India Weather Command Center
                </h1>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 shadow-2xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live & 30D Past Telemetry
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Atmospheric intelligence, radar beacons & historical observations across all Indian states
              </p>
            </div>

            {/* Time Horizon Selector (Live vs Past 7D vs Past 30D) */}
            <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200 self-start sm:self-auto">
              <button
                type="button"
                onClick={() => setTimeHorizon('live')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                  timeHorizon === 'live'
                    ? 'bg-emerald-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${timeHorizon === 'live' ? 'bg-white animate-pulse' : 'bg-emerald-500'}`} />
                Live Real-Time
              </button>

              <button
                type="button"
                onClick={() => setTimeHorizon('7d')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                  timeHorizon === '7d'
                    ? 'bg-brand-blue-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <span>📅 Past 7 Days</span>
              </button>

              <button
                type="button"
                onClick={() => setTimeHorizon('30d')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                  timeHorizon === '30d'
                    ? 'bg-purple-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <span>📊 Past 30 Days (1 Month)</span>
              </button>
            </div>
          </div>

          {/* KPI Strip */}
          <div className="flex-shrink-0">
            <KpiStrip stats={stats} />
          </div>

          {/* Pan-India Cities Preview Strip */}
          <div className="flex-shrink-0 bg-white p-3.5 rounded-2xl border border-slate-200 shadow-xs">
            <CityPreviewStrip
              selectedCity={filters.city}
              onSelectCity={(cityName) => setFilters({ city: cityName })}
              onOpenUpcomingModal={openUpcomingModal}
            />
          </div>

          {/* Selected City Latest Information */}
          {filters.city && (
            <div className="flex-shrink-0">
              <SelectedCityInfo
                cityName={filters.city}
                onClose={() => setFilters({ city: null })}
              />
            </div>
          )}

          {/* Main GIS Event Workspace: Full-Width Map + Full-Width Feed Below */}
          <div className="flex flex-col gap-4 flex-1">
            {/* Interactive India Geospatial Event Map (Full-Width) */}
            <div className="w-full h-[520px] lg:h-[580px] min-h-[440px] relative rounded-2xl border border-slate-200 overflow-hidden bg-white shadow-xs flex-shrink-0">
              <IndiaEventMap />
              <MapControls />
            </div>

            {/* Real-time / Historical Event Feed (Full-Width Below Map) */}
            <div className="w-full flex flex-col rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden flex-shrink-0">
              <LiveEventFeed />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
