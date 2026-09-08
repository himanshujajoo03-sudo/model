import React from 'react'

export default function EmergingEvents() {
  return (
    <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 flex items-center justify-between shadow-xs">
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-wider text-slate-500 uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Emerging Activity
        </span>
        <span className="text-xs font-semibold text-slate-700">No active anomaly clusters</span>
      </div>
      <span className="text-[10px] text-slate-400 font-medium hidden sm:inline">
        Continuous atmospheric anomaly scanning across Maharashtra grid
      </span>
    </div>
  )
}

