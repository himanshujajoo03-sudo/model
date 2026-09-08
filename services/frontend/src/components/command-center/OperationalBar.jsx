import React from 'react'
import useCommandCenterStore from '../../stores/commandCenterStore'

export default function OperationalBar({ health }) {
  const lastUpdated = useCommandCenterStore((s) => s.lastUpdated)
  const isHealthy = health?.status === 'healthy'

  const fmtTime = () => {
    if (!lastUpdated) return '—'
    return new Date(lastUpdated).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 flex flex-wrap items-center gap-4 sm:gap-6 shadow-xs select-none">
      {/* Pipeline stages */}
      <div className="flex items-center gap-3 sm:gap-4">
        {['INGEST', 'PROCESS', 'CLASSIFY', 'STORE'].map((stage, i) => (
          <React.Fragment key={stage}>
            {i > 0 && <span className="text-slate-300 text-[10px]">→</span>}
            <div className="flex items-center gap-1.5">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  isHealthy ? 'bg-emerald-500 ring-2 ring-emerald-100' : 'bg-slate-400'
                }`}
              />
              <span className="text-[9.5px] font-bold text-slate-700 tracking-wider">
                {stage}
              </span>
            </div>
          </React.Fragment>
        ))}
      </div>

      {/* Separator */}
      <div className="hidden sm:block w-px h-4 bg-slate-200" />

      {/* System status */}
      <div className="flex items-center gap-1.5">
        <div
          className={`w-2 h-2 rounded-full ${
            isHealthy
              ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]'
              : 'bg-rose-500'
          }`}
        />
        <span className="text-[10px] font-bold text-slate-800 uppercase tracking-wider">
          {isHealthy ? 'Operational' : 'Degraded'}
        </span>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Data freshness */}
      <div className="flex items-center gap-2">
        <span className="text-[9.5px] font-bold text-slate-400 uppercase tracking-wider">
          Last Telemetry
        </span>
        <span className="text-[10.5px] font-mono font-semibold text-slate-600 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
          {fmtTime()}
        </span>
      </div>
    </div>
  )
}

