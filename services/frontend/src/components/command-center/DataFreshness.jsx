import React from 'react'
import useCommandCenterStore from '../../stores/commandCenterStore'

export default function DataFreshness() {
  const lastUpdated = useCommandCenterStore((s) => s.lastUpdated)

  const getAge = () => {
    if (!lastUpdated) return '—'
    const diff = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 1000)
    if (diff < 5) return 'just now'
    if (diff < 60) return `${diff} seconds ago`
    return `${Math.floor(diff / 60)} minutes ago`
  }

  return (
    <div className="flex items-center gap-2 text-[11px] text-text-muted">
      <span className="font-medium uppercase tracking-wide">Data Freshness</span>
      <span className="mono text-text-secondary">{getAge()}</span>
    </div>
  )
}
