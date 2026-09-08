import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Sidebar from '../components/command-center/Sidebar'
import Header from '../components/command-center/Header'
import useSystemMonitoringStore from '../stores/systemMonitoringStore'

function StatusBadge({ status }) {
  const colors = {
    healthy: { bg: '#DCFCE7', text: '#166534', dot: '#22C55E' },
    connected: { bg: '#DCFCE7', text: '#166534', dot: '#22C55E' },
    degraded: { bg: '#FEF3C7', text: '#92400E', dot: '#F59E0B' },
    unavailable: { bg: '#FEE2E2', text: '#991B1B', dot: '#EF4444' },
    disconnected: { bg: '#FEE2E2', text: '#991B1B', dot: '#EF4444' },
    unknown: { bg: '#F1F5F9', text: '#475569', dot: '#94A3B8' },
  }
  const s = colors[status] || colors.unknown
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide"
      style={{ backgroundColor: s.bg, color: s.text }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: s.dot }} />
      {status}
    </span>
  )
}

function formatTimestamp(ts) {
  if (!ts) return 'N/A'
  try {
    const d = new Date(ts)
    return d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false })
  } catch {
    return ts
  }
}

function formatDuration(seconds) {
  if (!seconds) return 'N/A'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${Math.floor(seconds % 60)}s`
}

function ServiceCard({ title, children }) {
  return (
    <div className="card-white rounded-xl overflow-hidden border border-slate-200 shadow-sm">
      <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/70">
        <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">{title}</h3>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

function DataRow({ label, value, mono = false }) {
  return (
    <div className="flex justify-between items-start py-2 border-b border-slate-100 last:border-0">
      <span className="text-xs text-slate-500 font-medium">{label}</span>
      <span className={`text-xs text-slate-800 font-semibold text-right ${mono ? 'font-mono' : ''}`}>
        {value ?? 'N/A'}
      </span>
    </div>
  )
}

export default function SystemMonitoring() {
  const navigate = useNavigate()
  const {
    systemStatus, health, dataStats,
    loading, error, lastUpdated,
    startPolling, stopPolling, refresh,
  } = useSystemMonitoringStore()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  const db = systemStatus?.database
  const api = systemStatus?.api
  const kafka = systemStatus?.kafka
  const data = systemStatus?.data
  const uptime = systemStatus?.uptime_seconds

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 bg-white overflow-hidden">
        <Header health={health} />

        {/* Page header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-xl shadow-sm">
                🖥️
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-base font-bold text-slate-900">System Monitoring</h1>
                  <span className="badge-live text-[10px]">OPERATIONAL</span>
                </div>
                <p className="text-xs text-slate-500 font-medium">
                  Real-time platform health, telemetry ingestion queues, and database performance
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {lastUpdated && (
                <span className="text-xs text-slate-500 font-medium">
                  Updated: {formatTimestamp(lastUpdated)}
                </span>
              )}
              <button
                onClick={refresh}
                className="btn-secondary text-xs px-3.5 py-1.5"
              >
                ↻ Refresh Telemetry
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && !systemStatus ? (
            <div className="flex items-center justify-center h-40">
              <div className="text-xs text-slate-400 font-medium">Loading system status...</div>
            </div>
          ) : error && !systemStatus ? (
            <div className="card-white rounded-xl border border-rose-200 p-8 text-center">
              <div className="text-sm font-bold text-rose-700 mb-1">Unable to load system status</div>
              <div className="text-xs text-slate-500 mb-4">{error}</div>
              <button
                onClick={refresh}
                className="btn-primary text-xs px-4 py-2"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="space-y-5">
              {/* KPI strip */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="card-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">API Gateway</div>
                  <StatusBadge status={api?.status || 'unknown'} />
                </div>
                <div className="card-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">MySQL Database</div>
                  <StatusBadge status={db?.connected ? 'connected' : 'disconnected'} />
                </div>
                <div className="card-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Source Records</div>
                  <div className="text-xl font-extrabold text-blue-700 mono">{data?.total_source_records ?? db?.events_count ?? 0}</div>
                </div>
                <div className="card-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Canonical Events</div>
                  <div className="text-xl font-extrabold text-indigo-700 mono">{data?.total_canonical_events ?? db?.canonical_events_count ?? 0}</div>
                </div>
              </div>

              {/* Main grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

                {/* API Health */}
                <ServiceCard title="API Health">
                  <DataRow label="Status" value={<StatusBadge status={api?.status || 'unknown'} />} />
                  <DataRow label="Message" value={api?.message} />
                  <DataRow label="Last Checked" value={formatTimestamp(api?.last_checked)} />
                  <DataRow label="API Uptime" value={formatDuration(uptime)} />
                </ServiceCard>

                {/* Database Health */}
                <ServiceCard title="Database Health">
                  <DataRow label="Status" value={<StatusBadge status={db?.connected ? 'connected' : 'disconnected'} />} />
                  <DataRow label="Source Records" value={db?.events_count} />
                  <DataRow label="Canonical Events" value={db?.canonical_events_count} />
                  <DataRow label="Verification Actions (raw count)" value={db?.verification_log_count} />
                  <DataRow label="Latest Ingestion" value={formatTimestamp(db?.latest_ingestion)} />
                  <DataRow label="Earliest Ingestion" value={formatTimestamp(db?.earliest_ingestion)} />
                  <DataRow label="Last Checked" value={formatTimestamp(db?.last_checked)} />
                </ServiceCard>

                {/* Kafka Topics */}
                <ServiceCard title="Kafka Topics">
                  <div className="text-[10px] text-[#7A8794] mb-2">Configured topics reported by the application.</div>
                  <DataRow
                    label="Total Topics"
                    value={kafka ? kafka.topic_count : 'Unknown'}
                  />
                  {kafka?.available_topics?.map((topic) => (
                    <div key={topic} className="flex items-center gap-2 py-0.5">
                      <span className="w-1 h-1 rounded-full bg-[#477D96]" />
                      <span className="text-[10px] text-[#526170] font-mono">{topic}</span>
                    </div>
                  ))}
                  <DataRow label="Last Checked" value={formatTimestamp(kafka?.last_checked)} />
                </ServiceCard>

                {/* Data Statistics */}
                <ServiceCard title="Data Statistics">
                  <DataRow label="Source Records" value={data?.total_source_records} />
                  <DataRow label="Canonical Events" value={data?.total_canonical_events} />
                  <DataRow label="Verification Actions" value={data?.total_verification_actions} />
                  <DataRow label="Latest Event" value={formatTimestamp(data?.latest_event_timestamp)} />

                  {data?.records_by_source_type && Object.keys(data.records_by_source_type).length > 0 && (
                    <div className="mt-2 pt-2 border-t border-[#EEF1F4]">
                      <div className="text-[10px] font-semibold text-[#7A8794] uppercase tracking-wide mb-1">
                        Records by Source Type
                      </div>
                      {Object.entries(data.records_by_source_type).map(([type, count]) => (
                        <div key={type} className="flex justify-between py-0.5">
                          <span className="text-[11px] text-[#526170]">{type}</span>
                          <span className="text-[11px] text-[#18232D] font-semibold">{count}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {data?.events_by_status && Object.keys(data.events_by_status).length > 0 && (
                    <div className="mt-2 pt-2 border-t border-[#EEF1F4]">
                      <div className="text-[10px] font-semibold text-[#7A8794] uppercase tracking-wide mb-1">
                        Events by Verification Status
                      </div>
                      {Object.entries(data.events_by_status).map(([status, count]) => (
                        <div key={status} className="flex justify-between py-0.5">
                          <span className="text-[11px] text-[#526170]">{status}</span>
                          <span className="text-[11px] text-[#18232D] font-semibold">{count}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </ServiceCard>
              </div>

              {/* Metrics NOT displayed */}
              <div className="bg-[#FAFBFC] border border-[#EEF1F4] rounded-lg px-4 py-3">
                <div className="text-[10px] font-semibold text-[#7A8794] uppercase tracking-wide mb-1">
                  Metrics Not Displayed
                </div>
                <div className="text-[10px] text-[#7A8794] leading-relaxed">
                  The following metrics are not shown because they cannot be truthfully verified
                  from the API process: CPU usage, memory usage, disk I/O, network throughput,
                  Kafka consumer lag, Spark executor status, MinIO storage, and individual service
                  uptime. These would require dedicated monitoring infrastructure (Prometheus, Grafana, etc.).
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
