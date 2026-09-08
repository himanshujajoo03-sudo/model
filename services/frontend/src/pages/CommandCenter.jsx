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
  const setFilters = useCommandCenterStore((s) => s.setFilters)
  const startPolling = useCommandCenterStore((s) => s.startPolling)
  const stopPolling = useCommandCenterStore((s) => s.stopPolling)
  const openUpcomingModal = useLayoutStore((s) => s.openUpcomingModal)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  return (
    <div className="flex h-screen bg-slate-50/70 overflow-hidden">
      {/* Responsive Collapsible Sidebar */}
      <Sidebar health={health} />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 bg-slate-50/70 overflow-hidden">
        <Header />

        <div className="flex-1 flex flex-col overflow-y-auto px-4 lg:px-6 py-4 gap-4 scrollbar-thin bg-slate-50/70">
          {/* Top Row: Page Title + Operational Status Badge */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 flex-shrink-0">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                  National Weather Command Center
                </h1>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 shadow-2xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live Feeds Active
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Multi-source atmospheric intelligence & GIS boundary telemetry
              </p>
            </div>
          </div>

          {/* KPI Strip */}
          <div className="flex-shrink-0">
            <KpiStrip stats={stats} />
          </div>

          {/* 3 Active Cities + Phase II Preview Strip */}
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

            {/* Real-time Event Feed (Full-Width Below Map) */}
            <div className="w-full h-[480px] min-h-[380px] flex flex-col rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden flex-shrink-0">
              <LiveEventFeed />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
