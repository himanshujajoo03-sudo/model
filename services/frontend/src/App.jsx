import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import CommandCenter from './pages/CommandCenter'
import EventIntelligence from './pages/EventIntelligence'
import LiveEvents from './pages/LiveEvents'
import VerificationCenter from './pages/VerificationCenter'
import GeospatialIntelligence from './pages/GeospatialIntelligence'
import AnalyticsLayout from './pages/analytics/AnalyticsLayout'
import EventTrends from './pages/analytics/EventTrends'
import GeographicAnalysis from './pages/analytics/GeographicAnalysis'
import SourceIntelligence from './pages/analytics/SourceIntelligence'
import EmergingEvents from './pages/EmergingEvents'
import ReportReview from './pages/ReportReview'
import SystemMonitoring from './pages/SystemMonitoring'
import CitizenReport from './pages/CitizenReport'
import ComingSoonModal from './components/common/ComingSoonModal'
import CommandPaletteModal from './components/common/CommandPaletteModal'
import AlertNotificationDrawer from './components/common/AlertNotificationDrawer'
import CitizenReportModal from './components/common/CitizenReportModal'

function App() {
  return (
    <BrowserRouter>
      <ComingSoonModal />
      <CommandPaletteModal />
      <AlertNotificationDrawer />
      <CitizenReportModal />
      <Routes>
        <Route path="/" element={<CommandCenter />} />
        <Route path="/events" element={<LiveEvents />} />
        <Route path="/events/:eventId" element={<EventIntelligence />} />
        <Route path="/verification" element={<VerificationCenter />} />
        <Route path="/geospatial" element={<GeospatialIntelligence />} />
        <Route path="/citizen-report" element={<CitizenReport />} />
        <Route path="/citizen" element={<Navigate to="/citizen-report" replace />} />
        <Route path="/analytics" element={<AnalyticsLayout />}>
          <Route index element={<Navigate to="/analytics/events" replace />} />
          <Route path="events" element={<EventTrends />} />
          <Route path="geographic" element={<GeographicAnalysis />} />
          <Route path="sources" element={<SourceIntelligence />} />
        </Route>
        <Route path="/emerging" element={<EmergingEvents />} />
        <Route path="/report-review" element={<ReportReview />} />
        <Route path="/system-monitoring" element={<SystemMonitoring />} />
        <Route path="/command-center" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
