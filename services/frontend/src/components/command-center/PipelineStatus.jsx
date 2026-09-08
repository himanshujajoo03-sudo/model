import React from 'react'
import useCommandCenterStore from '../../stores/commandCenterStore'

const PIPELINE_STAGES = [
  { key: 'ingest', label: 'INGEST', desc: 'Sources → Kafka' },
  { key: 'process', label: 'PROCESS', desc: 'Spark Streaming' },
  { key: 'classify', label: 'CLASSIFY', desc: 'ML Enrichment' },
  { key: 'store', label: 'STORE', desc: 'PostgreSQL' },
]

export default function PipelineStatus() {
  const health = useCommandCenterStore((s) => s.health)
  const isHealthy = health?.status === 'healthy'

  return (
    <div className="panel px-5 py-3">
      <div className="flex items-center justify-between">
        {PIPELINE_STAGES.map((stage) => (
          <div key={stage.key} className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-success' : 'bg-text-muted'}`} />
            <div>
              <div className="text-[10px] font-semibold tracking-wide text-text-primary uppercase">
                {stage.label}
              </div>
              <div className="text-[10px] text-text-muted">
                {isHealthy ? 'Healthy' : 'Checking...'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
