import React, { useState, useRef, useEffect } from 'react'
import Sidebar from '../components/command-center/Sidebar'
import Header from '../components/command-center/Header'

/* ═══════════════════════════════════════════════════════════════
   Event Types with Icons & Descriptions
   ═══════════════════════════════════════════════════════════════ */
const EVENT_TYPES = [
  { value: 'heavy_rainfall', label: 'Heavy Rainfall', icon: '🌧️', hint: 'Intense or continuous downpour' },
  { value: 'flooding', label: 'Flooding', icon: '🌊', hint: 'Water accumulation, inundated roads or premises' },
  { value: 'lightning', label: 'Lightning', icon: '⚡', hint: 'Ground strikes or dangerous electrical activity' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: '⛈️', hint: 'Squall winds with thunder and rain' },
  { value: 'strong_wind', label: 'Strong Wind', icon: '💨', hint: 'Gale force gusts, tree or structure hazards' },
  { value: 'hailstorm', label: 'Hailstorm', icon: '🌨️', hint: 'Falling ice pellets or hailstones' },
  { value: 'fog', label: 'Fog', icon: '🌫️', hint: 'Dense haze or zero visibility conditions' },
  { value: 'heatwave', label: 'Heatwave', icon: '☀️', hint: 'Abnormally high ambient temperature' },
  { value: 'dust_storm', label: 'Dust Storm', icon: '🏜️', hint: 'Blowing dust or reduced visibility' },
  { value: 'other', label: 'Other', icon: '⚠️', hint: 'Unusual localized weather observation' },
]

const TIME_PRESETS = [
  { id: 'now', label: 'Happening right now' },
  { id: '30m', label: 'Past 30 minutes' },
  { id: '1h', label: '1–2 hours ago' },
  { id: 'earlier', label: 'Earlier today' },
]

function getFormattedCurrentTime() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60000
  return new Date(now.getTime() - offset).toISOString().slice(0, 16)
}

export default function CitizenReport() {
  // Form State (Client-Side Only)
  const [eventType, setEventType] = useState('')
  const [location, setLocation] = useState('')
  const [timePreset, setTimePreset] = useState('now')
  const [datetime, setDatetime] = useState(getFormattedCurrentTime())
  const [description, setDescription] = useState('')
  const [reporterName, setReporterName] = useState('')
  const [contactNumber, setContactNumber] = useState('')
  const [imageFile, setImageFile] = useState(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState(null)

  // Interaction State
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submittedData, setSubmittedData] = useState(null)
  const [showSuccessModal, setShowSuccessModal] = useState(false)

  const fileInputRef = useRef(null)

  // Handle local image selection without network upload
  const handleImageChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setErrors((prev) => ({ ...prev, image: 'Please select an image file (JPEG, PNG, WebP).' }))
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrors((prev) => ({ ...prev, image: 'Photo size should be under 10MB.' }))
      return
    }

    setErrors((prev) => {
      const copy = { ...prev }
      delete copy.image
      return copy
    })

    // Revoke previous URL if any to avoid browser memory leaks
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl)
    }

    setImageFile({
      name: file.name,
      size: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
      type: file.type,
    })
    setImagePreviewUrl(URL.createObjectURL(file))
  }

  const handleRemoveImage = () => {
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl)
    }
    setImageFile(null)
    setImagePreviewUrl(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Cleanup object URL on unmount
  useEffect(() => {
    return () => {
      if (imagePreviewUrl) {
        URL.revokeObjectURL(imagePreviewUrl)
      }
    }
  }, [imagePreviewUrl])

  // Update datetime based on preset
  const handlePresetChange = (presetId) => {
    setTimePreset(presetId)
    const now = new Date()
    let target = new Date(now)

    if (presetId === '30m') {
      target = new Date(now.getTime() - 30 * 60 * 1000)
    } else if (presetId === '1h') {
      target = new Date(now.getTime() - 90 * 60 * 1000)
    } else if (presetId === 'earlier') {
      target = new Date(now.getTime() - 4 * 60 * 60 * 1000)
    }

    const offset = target.getTimezoneOffset() * 60000
    setDatetime(new Date(target.getTime() - offset).toISOString().slice(0, 16))
    if (errors.datetime) {
      setErrors((prev) => {
        const copy = { ...prev }
        delete copy.datetime
        return copy
      })
    }
  }

  // Validate form client-side
  const validateForm = () => {
    const newErrors = {}

    if (!eventType) {
      newErrors.eventType = 'Please select the type of weather event.'
    }

    if (!location.trim()) {
      newErrors.location = 'Please specify your location (e.g. Dadar Circle, Mumbai).'
    } else if (location.trim().length < 3) {
      newErrors.location = 'Location name must be at least 3 characters.'
    }

    if (!datetime) {
      newErrors.datetime = 'Please specify when the event occurred.'
    }

    if (!description.trim()) {
      newErrors.description = 'Please describe what you observed around you.'
    } else if (description.trim().length < 10) {
      newErrors.description = 'Description should be at least 10 characters to provide useful context.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Form submission (100% frontend only)
  const handleSubmit = (e) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)

    // Simulate realistic UI processing delay (550ms), strictly in-memory
    setTimeout(() => {
      setIsSubmitting(false)
      const selectedEventObj = EVENT_TYPES.find((et) => et.value === eventType)

      const submissionSnapshot = {
        eventName: selectedEventObj?.label || 'Weather Event',
        eventIcon: selectedEventObj?.icon || '⚠️',
        location: location.trim(),
        datetime: datetime,
        timePreset: TIME_PRESETS.find((p) => p.id === timePreset)?.label || 'Recent',
        description: description.trim(),
        reporterName: reporterName.trim() || 'Anonymous Citizen',
        contactNumber: contactNumber.trim() || 'Not provided',
        hasPhoto: Boolean(imageFile),
        photoName: imageFile?.name,
        photoSize: imageFile?.size,
        photoPreviewUrl: imagePreviewUrl,
        timestamp: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        referenceCode: `CIT-${Math.floor(100000 + Math.random() * 900000)}`,
      }

      setSubmittedData(submissionSnapshot)
      setShowSuccessModal(true)
    }, 550)
  }

  // Reset form for demo
  const handleResetForm = () => {
    handleRemoveImage()
    setEventType('')
    setLocation('')
    setTimePreset('now')
    setDatetime(getFormattedCurrentTime())
    setDescription('')
    setReporterName('')
    setContactNumber('')
    setErrors({})
    setSubmittedData(null)
    setShowSuccessModal(false)
  }

  return (
    <div className="flex min-h-screen bg-[#F8FAFC]">
      {/* Unified Platform Sidebar */}
      <Sidebar />

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#F8FAFC]">
        <Header />

        {/* Page Content Viewport */}
        <div className="flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <div className="max-w-6xl mx-auto space-y-6">

            {/* Page Header Strip */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="badge badge-info text-[10px] font-mono tracking-wider uppercase">
                    CITIZEN INTELLIGENCE DESK
                  </span>
                  <span className="badge badge-pending text-[10px] font-mono tracking-wider">
                    DEMO INTERFACE
                  </span>
                </div>
                <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                  Report What's Happening Around You
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                  Your local observation can help identify weather events faster and improve situational awareness.
                </p>
              </div>

              {/* Security & Non-Persistence Trust Badge */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs shadow-2xs self-start sm:self-auto">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="font-medium text-slate-700">Client-Side Demo</span>
                <span className="text-slate-300">•</span>
                <span className="text-slate-500 text-[11px]">No data stored</span>
              </div>
            </div>

            {/* Two-Column Layout (Desktop) / Stacked (Mobile) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">

              {/* ──────────────────────────────────────────────────
                  LEFT COLUMN: Citizen Report Form (7 cols)
                  ────────────────────────────────────────────────── */}
              <div className="lg:col-span-7 space-y-4">
                <div className="card-white p-6 sm:p-7 border border-slate-200 shadow-sm bg-white rounded-2xl">
                  
                  {/* Card Header */}
                  <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100">
                    <div>
                      <span className="text-[10px] font-bold tracking-wider text-brand-blue-700 uppercase font-mono">
                        SECTION: CITIZEN REPORT
                      </span>
                      <h2 className="text-base font-bold text-slate-900 mt-0.5">
                        Observation Form
                      </h2>
                    </div>
                    <span className="text-xs text-slate-400 font-medium">
                      * Required fields
                    </span>
                  </div>

                  <form onSubmit={handleSubmit} noValidate className="space-y-5">

                    {/* 1. Event Type Field */}
                    <div>
                      <label htmlFor="event-type-select" className="block text-xs font-bold text-slate-800 mb-1.5">
                        1. Event Type <span className="text-rose-500">*</span>
                      </label>
                      <div className="relative">
                        <select
                          id="event-type-select"
                          value={eventType}
                          onChange={(e) => {
                            setEventType(e.target.value)
                            if (errors.eventType) {
                              setErrors((prev) => {
                                const c = { ...prev }
                                delete c.eventType
                                return c
                              })
                            }
                          }}
                          className={`w-full h-10 px-3 py-2 text-xs font-medium rounded-xl border bg-white appearance-none cursor-pointer transition-colors focus:outline-none focus:ring-2 ${
                            errors.eventType
                              ? 'border-rose-300 ring-rose-200 text-slate-900'
                              : 'border-slate-200 focus:border-brand-blue-500 focus:ring-brand-blue-100 text-slate-800'
                          }`}
                        >
                          <option value="">Select weather event type...</option>
                          {EVENT_TYPES.map((et) => (
                            <option key={et.value} value={et.value}>
                              {et.icon} {et.label} — {et.hint}
                            </option>
                          ))}
                        </select>
                        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400">
                          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                          </svg>
                        </div>
                      </div>
                      {errors.eventType ? (
                        <p className="mt-1 text-[11px] text-rose-600 font-medium flex items-center gap-1">
                          <span>⚠</span> {errors.eventType}
                        </p>
                      ) : (
                        <p className="mt-1 text-[11px] text-slate-400">
                          Select the dominant weather hazard observed in your area.
                        </p>
                      )}
                    </div>

                    {/* 2. Location Field (No GPS/API) */}
                    <div>
                      <label htmlFor="location-input" className="block text-xs font-bold text-slate-800 mb-1.5">
                        2. Location <span className="text-rose-500">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                          <svg className="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                            <circle cx="12" cy="10" r="3" />
                          </svg>
                        </div>
                        <input
                          id="location-input"
                          type="text"
                          value={location}
                          onChange={(e) => {
                            setLocation(e.target.value)
                            if (errors.location) {
                              setErrors((prev) => {
                                const c = { ...prev }
                                delete c.location
                                return c
                              })
                            }
                          }}
                          placeholder="Village, city, district (e.g. Dadar TT Circle, Mumbai)"
                          className={`w-full h-10 pl-9 pr-3 text-xs font-medium rounded-xl border bg-white transition-colors focus:outline-none focus:ring-2 ${
                            errors.location
                              ? 'border-rose-300 ring-rose-200 text-slate-900'
                              : 'border-slate-200 focus:border-brand-blue-500 focus:ring-brand-blue-100 text-slate-800'
                          }`}
                        />
                      </div>
                      {errors.location ? (
                        <p className="mt-1 text-[11px] text-rose-600 font-medium flex items-center gap-1">
                          <span>⚠</span> {errors.location}
                        </p>
                      ) : (
                        <p className="mt-1 text-[11px] text-slate-400">
                          Enter your village, city, district, or landmark. Browser GPS is disabled for your privacy.
                        </p>
                      )}
                    </div>

                    {/* 3. Date / Time Field */}
                    <div>
                      <label htmlFor="datetime-input" className="block text-xs font-bold text-slate-800 mb-1.5">
                        3. Date & Time <span className="text-rose-500">*</span>
                      </label>
                      
                      {/* Presets */}
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {TIME_PRESETS.map((p) => {
                          const active = timePreset === p.id
                          return (
                            <button
                              key={p.id}
                              type="button"
                              onClick={() => handlePresetChange(p.id)}
                              className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg border transition-all ${
                                active
                                  ? 'bg-brand-blue-50 text-brand-blue-700 border-brand-blue-300 shadow-2xs'
                                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                              }`}
                            >
                              {p.label}
                            </button>
                          )
                        })}
                      </div>

                      {/* Precise datetime picker */}
                      <input
                        id="datetime-input"
                        type="datetime-local"
                        value={datetime}
                        onChange={(e) => {
                          setDatetime(e.target.value)
                          setTimePreset('custom')
                          if (errors.datetime) {
                            setErrors((prev) => {
                              const c = { ...prev }
                              delete c.datetime
                              return c
                            })
                          }
                        }}
                        className={`w-full h-10 px-3 text-xs font-medium rounded-xl border bg-white transition-colors focus:outline-none focus:ring-2 ${
                          errors.datetime
                            ? 'border-rose-300 ring-rose-200 text-slate-900'
                            : 'border-slate-200 focus:border-brand-blue-500 focus:ring-brand-blue-100 text-slate-800'
                        }`}
                      />
                      {errors.datetime && (
                        <p className="mt-1 text-[11px] text-rose-600 font-medium flex items-center gap-1">
                          <span>⚠</span> {errors.datetime}
                        </p>
                      )}
                    </div>

                    {/* 4. Description Field */}
                    <div>
                      <label htmlFor="description-textarea" className="block text-xs font-bold text-slate-800 mb-1.5">
                        4. Description <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        id="description-textarea"
                        rows={3}
                        value={description}
                        onChange={(e) => {
                          setDescription(e.target.value)
                          if (errors.description) {
                            setErrors((prev) => {
                              const c = { ...prev }
                              delete c.description
                              return c
                            })
                          }
                        }}
                        placeholder="Describe what you observed (e.g., Heavy rainfall has been continuing for the last 30 minutes and water is accumulating near the main road)..."
                        className={`w-full p-3 text-xs font-medium rounded-xl border bg-white transition-colors focus:outline-none focus:ring-2 resize-y min-h-[88px] ${
                          errors.description
                            ? 'border-rose-300 ring-rose-200 text-slate-900'
                            : 'border-slate-200 focus:border-brand-blue-500 focus:ring-brand-blue-100 text-slate-800'
                        }`}
                      />
                      <div className="flex justify-between items-center mt-1">
                        {errors.description ? (
                          <p className="text-[11px] text-rose-600 font-medium flex items-center gap-1">
                            <span>⚠</span> {errors.description}
                          </p>
                        ) : (
                          <p className="text-[11px] text-slate-400">
                            Mention intensity, duration, visibility, or water accumulation.
                          </p>
                        )}
                        <span className="text-[10px] font-mono text-slate-400 ml-auto">
                          {description.length} chars
                        </span>
                      </div>
                    </div>

                    {/* 5. Optional Image Upload (Browser-Only Preview) */}
                    <div>
                      <label className="block text-xs font-bold text-slate-800 mb-1.5">
                        5. Add Photo (Optional)
                      </label>

                      {!imagePreviewUrl ? (
                        <div
                          onClick={() => fileInputRef.current?.click()}
                          className="border-2 border-dashed border-slate-200 hover:border-brand-blue-400 rounded-xl p-4 text-center cursor-pointer bg-slate-50/50 hover:bg-brand-blue-50/20 transition-all group"
                        >
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleImageChange}
                            className="hidden"
                          />
                          <div className="flex flex-col items-center justify-center gap-1.5">
                            <div className="w-8 h-8 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-500 group-hover:text-brand-blue-600 shadow-2xs transition-colors">
                              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                                <circle cx="8.5" cy="8.5" r="1.5" />
                                <polyline points="21 15 16 10 5 21" />
                              </svg>
                            </div>
                            <div className="text-xs font-semibold text-slate-700 group-hover:text-brand-blue-600">
                              Click to select an image from your device
                            </div>
                            <div className="text-[11px] text-slate-400">
                              PNG, JPG, or WebP up to 10MB • <span className="text-slate-500 font-medium">Never uploaded to server</span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="rounded-xl border border-slate-200 p-3 bg-white flex items-center gap-3">
                          <img
                            src={imagePreviewUrl}
                            alt="Local preview"
                            className="w-16 h-16 object-cover rounded-lg border border-slate-200 shadow-2xs"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-bold text-slate-800 truncate">
                                {imageFile?.name}
                              </span>
                              <span className="badge badge-info text-[9px]">LOCAL PREVIEW</span>
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5">
                              Size: {imageFile?.size} • Client memory only
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={handleRemoveImage}
                            className="btn-pill text-xs text-rose-600 border-rose-200 hover:bg-rose-50 hover:border-rose-300"
                            title="Remove photo"
                          >
                            Remove
                          </button>
                        </div>
                      )}

                      {errors.image && (
                        <p className="mt-1 text-[11px] text-rose-600 font-medium">
                          ⚠ {errors.image}
                        </p>
                      )}
                    </div>

                    {/* 6 & 7: Reporter Name & Contact Number (Optional) */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
                      <div>
                        <label htmlFor="reporter-name-input" className="block text-xs font-bold text-slate-800 mb-1.5">
                          6. Your Name (Optional)
                        </label>
                        <input
                          id="reporter-name-input"
                          type="text"
                          value={reporterName}
                          onChange={(e) => setReporterName(e.target.value)}
                          placeholder="e.g., Rajesh Sharma"
                          className="w-full h-10 px-3 text-xs font-medium rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:border-brand-blue-500 focus:ring-brand-blue-100 text-slate-800"
                        />
                      </div>

                      <div>
                        <label htmlFor="contact-number-input" className="block text-xs font-bold text-slate-800 mb-1.5">
                          7. Contact Number (Optional)
                        </label>
                        <input
                          id="contact-number-input"
                          type="tel"
                          value={contactNumber}
                          onChange={(e) => setContactNumber(e.target.value)}
                          placeholder="e.g., +91 98765 43210"
                          className="w-full h-10 px-3 text-xs font-medium rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:border-brand-blue-500 focus:ring-brand-blue-100 text-slate-800"
                        />
                      </div>
                    </div>

                    <div className="text-[10px] text-slate-400 italic">
                      Note: Name and contact values are optional and will not be transmitted, stored, or indexed anywhere.
                    </div>

                    {/* Submit Button & Clear */}
                    <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="btn-primary w-full sm:w-auto px-6 py-2.5 text-xs font-bold shadow-sm flex items-center justify-center gap-2"
                      >
                        {isSubmitting ? (
                          <>
                            <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            <span>Processing Report...</span>
                          </>
                        ) : (
                          <>
                            <span>Submit Report</span>
                            <span>→</span>
                          </>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={handleResetForm}
                        className="text-xs text-slate-500 hover:text-slate-800 font-semibold underline-offset-4 hover:underline"
                      >
                        Clear form
                      </button>
                    </div>

                    {/* Mandatory Subtle Note Below Form */}
                    <div className="pt-2 text-center text-[11px] text-slate-400">
                      Demo interface • Reports submitted here are not stored.
                    </div>

                  </form>
                </div>
              </div>

              {/* ──────────────────────────────────────────────────
                  RIGHT COLUMN: Guidance & Info Cards (5 cols)
                  ────────────────────────────────────────────────── */}
              <div className="lg:col-span-5 space-y-5">

                {/* Card 1: Why Citizen Reports Matter */}
                <div className="card-white p-5 sm:p-6 border border-slate-200 shadow-sm bg-white rounded-2xl">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-7 h-7 rounded-lg bg-brand-blue-50 text-brand-blue-600 flex items-center justify-center text-sm font-bold">
                      💡
                    </div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Why citizen reports matter
                    </h3>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed mb-4">
                    In high-impact convective storms and localized flash floods, ground truth reports from residents provide hyper-local visibility before official station telemetry is logged.
                  </p>

                  <div className="space-y-3">
                    <div className="flex items-start gap-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                      <span className="text-base leading-none mt-0.5">⏱️</span>
                      <div>
                        <div className="text-xs font-bold text-slate-800">
                          Detect local weather conditions faster
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          Identify cloudbursts and sudden squalls the moment they develop.
                        </div>
                      </div>
                    </div>

                    <div className="flex items-start gap-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                      <span className="text-base leading-none mt-0.5">🛰️</span>
                      <div>
                        <div className="text-xs font-bold text-slate-800">
                          Complement official observations
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          Corroborate satellite radar reflectivity with direct human observation.
                        </div>
                      </div>
                    </div>

                    <div className="flex items-start gap-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                      <span className="text-base leading-none mt-0.5">🛡️</span>
                      <div>
                        <div className="text-xs font-bold text-slate-800">
                          Improve situational awareness
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          Help response teams anticipate street-level water-logging or hazards.
                        </div>
                      </div>
                    </div>

                    <div className="flex items-start gap-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                      <span className="text-base leading-none mt-0.5">📍</span>
                      <div>
                        <div className="text-xs font-bold text-slate-800">
                          Help identify events at local scale
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          Pinpoint micro-climate events that may miss distant automatic weather stations.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 2: Reporting Guidelines */}
                <div className="card-white p-5 border border-slate-200 shadow-sm bg-white rounded-2xl">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2.5 flex items-center gap-2">
                    <span>📋</span>
                    <span>Reporting Best Practices</span>
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-600">
                    <li className="flex items-start gap-2">
                      <span className="text-brand-blue-600 font-bold">•</span>
                      <span><strong>Safety First:</strong> Never put yourself in danger to take photos or record observations.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-brand-blue-600 font-bold">•</span>
                      <span><strong>Be Specific:</strong> Mention visible landmarks, road intersections, or colony names.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-brand-blue-600 font-bold">•</span>
                      <span><strong>Note Trends:</strong> Indicate if rainfall or water levels are rising, steady, or receding.</span>
                    </li>
                  </ul>
                </div>

                {/* Card 3: Demonstration Notice Banner */}
                <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200 text-amber-900 text-xs">
                  <div className="flex items-center gap-2 font-bold mb-1">
                    <span>ℹ️</span>
                    <span>Demo Environment Notice</span>
                  </div>
                  <p className="text-[11px] text-amber-800 leading-relaxed">
                    This reporting page is an interactive demonstration designed for UI evaluation. No network requests, API calls, or backend storage transactions take place.
                  </p>
                </div>

              </div>

            </div>

          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────
          SUCCESS CONFIRMATION MODAL / DIALOG (Client-side)
          ────────────────────────────────────────────────── */}
      {showSuccessModal && submittedData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in-0 duration-150">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 text-slate-900 animate-in zoom-in-95 duration-150">
            
            {/* Modal Icon & Header */}
            <div className="text-center pb-4 border-b border-slate-100">
              <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mx-auto text-xl mb-3 shadow-2xs">
                ✓
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Thank you for your report.
              </h3>
              <p className="text-xs text-slate-600 mt-1">
                Your observation has been recorded for this demonstration.
              </p>
              <div className="inline-block mt-2 px-2.5 py-1 rounded-md bg-slate-100 border border-slate-200 text-slate-600 text-[11px] font-mono font-medium">
                Demo submission — no data is stored.
              </div>
            </div>

            {/* Observation Summary Snapshot */}
            <div className="py-4 space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-400">Reference:</span>
                <span className="font-mono font-bold text-slate-800">{submittedData.referenceCode}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-400">Event:</span>
                <span className="font-semibold text-slate-800 flex items-center gap-1">
                  <span>{submittedData.eventIcon}</span>
                  <span>{submittedData.eventName}</span>
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-400">Location:</span>
                <span className="font-medium text-slate-800 truncate max-w-[200px]">{submittedData.location}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-400">Observation Time:</span>
                <span className="font-mono text-slate-700">{submittedData.datetime.replace('T', ' ')}</span>
              </div>
              {submittedData.hasPhoto && (
                <div className="flex justify-between py-1 border-b border-slate-100 items-center">
                  <span className="text-slate-400">Attached Photo:</span>
                  <span className="text-[11px] text-emerald-700 font-medium">Previewed Locally</span>
                </div>
              )}
              <div className="pt-1 text-[11px] text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-100">
                <span className="font-semibold text-slate-700">Observation: </span>
                <span>"{submittedData.description}"</span>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="pt-2 flex flex-col gap-2">
              <button
                type="button"
                onClick={handleResetForm}
                className="btn-primary w-full py-2.5 text-xs font-bold"
              >
                Submit another report
              </button>
              <button
                type="button"
                onClick={() => setShowSuccessModal(false)}
                className="btn-secondary w-full py-2 text-xs font-semibold text-slate-600"
              >
                Close dialog
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  )
}
