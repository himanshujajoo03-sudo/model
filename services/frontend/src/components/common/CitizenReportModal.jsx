import React, { useState, useRef, useEffect } from 'react'
import useLayoutStore from '../../stores/layoutStore'

const EVENT_OPTIONS = [
  { value: 'heavy_rain', label: 'Heavy Rain', icon: '🌧️', hint: 'Intense or continuous downpour' },
  { value: 'flood', label: 'Flood', icon: '🌊', hint: 'Waterlogging or inundated streets/premises' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: '⛈️', hint: 'Thunder, lightning with rain gusts' },
  { value: 'strong_wind', label: 'Strong Wind', icon: '💨', hint: 'High-speed squalls or gale gusts' },
  { value: 'lightning', label: 'Lightning', icon: '⚡', hint: 'Cloud-to-ground electrical strikes' },
  { value: 'landslide', label: 'Landslide', icon: '⛰️', hint: 'Slope failure, rockfall, or mudflow' },
  { value: 'heatwave', label: 'Heatwave', icon: '☀️', hint: 'Severe high temperature conditions' },
  { value: 'fog', label: 'Fog', icon: '🌫️', hint: 'Dense fog or near-zero visibility' },
  { value: 'other', label: 'Other', icon: '⚠️', hint: 'Other localized weather hazard' },
]

function getLocalDatetimeString() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

export default function CitizenReportModal() {
  const isOpen = useLayoutStore((s) => s.citizenReportModalOpen)
  const closeCitizenReportModal = useLayoutStore((s) => s.closeCitizenReportModal)

  // Form State
  const [eventType, setEventType] = useState('')
  const [description, setDescription] = useState('')
  const [manualLocation, setManualLocation] = useState('')
  const [coords, setCoords] = useState(null)
  const [geoStatus, setGeoStatus] = useState('idle') // 'idle' | 'locating' | 'success' | 'error'
  const [geoError, setGeoError] = useState('')
  const [datetime, setDatetime] = useState(getLocalDatetimeString())
  const [imageFile, setImageFile] = useState(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState(null)
  const [reporterName, setReporterName] = useState('')
  const [reporterContact, setReporterContact] = useState('')

  // Submission & Validation State
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submittedReport, setSubmittedReport] = useState(null)

  const fileInputRef = useRef(null)

  // Reset form to clean state
  const resetForm = () => {
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl)
    }
    setEventType('')
    setDescription('')
    setManualLocation('')
    setCoords(null)
    setGeoStatus('idle')
    setGeoError('')
    setDatetime(getLocalDatetimeString())
    setImageFile(null)
    setImagePreviewUrl(null)
    setReporterName('')
    setReporterContact('')
    setErrors({})
    setIsSubmitting(false)
    setSubmittedReport(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Handle modal close
  const handleClose = () => {
    closeCitizenReportModal()
    // Small timeout to avoid content flash during fade-out
    setTimeout(() => {
      resetForm()
    }, 200)
  }

  // Escape key handler
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        handleClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  // Background scroll lock only while modal is open, reliably restored on close or unmount
  useEffect(() => {
    if (!isOpen) return
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prevOverflow || ''
    }
  }, [isOpen])

  // Cleanup image URL on unmount
  useEffect(() => {
    return () => {
      if (imagePreviewUrl) {
        URL.revokeObjectURL(imagePreviewUrl)
      }
    }
  }, [imagePreviewUrl])

  // Geolocation Handler
  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      setGeoStatus('error')
      setGeoError('Geolocation is not supported by your browser. You can enter the location manually.')
      return
    }

    setGeoStatus('locating')
    setGeoError('')

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude
        const lng = position.coords.longitude
        setCoords({ lat, lng })
        setGeoStatus('success')
        if (errors.location) {
          setErrors((prev) => {
            const next = { ...prev }
            delete next.location
            return next
          })
        }
      },
      (err) => {
        console.warn('Geolocation error:', err)
        setGeoStatus('error')
        setGeoError('Unable to access your location. You can enter the location manually.')
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    )
  }

  // Handle Image Selection
  const handleImageChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setErrors((prev) => ({ ...prev, image: 'Please select a valid image file (JPEG, PNG, WebP).' }))
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrors((prev) => ({ ...prev, image: 'Image size should be under 10MB.' }))
      return
    }

    setErrors((prev) => {
      const next = { ...prev }
      delete next.image
      return next
    })

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

  // Remove Image
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

  // Client-Side Validation
  const validate = () => {
    const newErrors = {}

    if (!eventType) {
      newErrors.eventType = 'Please select an event type.'
    }

    if (!description.trim()) {
      newErrors.description = 'Please describe what you observed.'
    } else if (description.trim().length < 5) {
      newErrors.description = 'Description should be at least 5 characters.'
    }

    if (!manualLocation.trim() && !coords) {
      newErrors.location = 'Please provide a location name or use "Use My Location".'
    }

    if (!datetime) {
      newErrors.datetime = 'Please specify the date and time of observation.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Form Submission
  const handleSubmit = (e) => {
    e.preventDefault()

    if (!validate()) {
      return
    }

    setIsSubmitting(true)

    // Simulate brief processing delay (500ms)
    setTimeout(() => {
      setIsSubmitting(false)
      const selectedOption = EVENT_OPTIONS.find((opt) => opt.value === eventType)

      const snapshot = {
        referenceCode: `CIT-${Math.floor(100000 + Math.random() * 900000)}`,
        eventLabel: selectedOption?.label || 'Weather Event',
        eventIcon: selectedOption?.icon || '⚠️',
        manualLocation: manualLocation.trim(),
        coords: coords ? { lat: coords.lat.toFixed(4), lng: coords.lng.toFixed(4) } : null,
        datetime: datetime,
        description: description.trim(),
        reporterName: reporterName.trim() || 'Anonymous Citizen',
        reporterContact: reporterContact.trim() || 'None',
        hasPhoto: Boolean(imageFile),
        photoName: imageFile?.name,
        photoSize: imageFile?.size,
        photoPreviewUrl: imagePreviewUrl,
        submittedAt: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      }

      setSubmittedReport(snapshot)
    }, 500)
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/50 backdrop-blur-xs animate-in fade-in-0 duration-150"
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="citizen-report-title"
    >
      <div
        className="bg-white rounded-2xl sm:rounded-3xl border border-slate-200 shadow-2xl w-full max-w-xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 sm:px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-base shadow-2xs">
              <span>📢</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="citizen-report-title" className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
                  Report a Weather Event
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                  Citizen Desk
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                Ground observation for meteorological verification
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleClose}
            id="close-citizen-report-modal"
            className="w-8 h-8 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 flex items-center justify-center text-sm font-semibold transition-colors"
            title="Close dialog (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-4 scrollbar-thin">
          {submittedReport ? (
            /* Success Confirmation Screen */
            <div className="py-4 space-y-5 text-center animate-in fade-in-0 zoom-in-95 duration-200">
              <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mx-auto text-2xl shadow-xs">
                ✓
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Report submitted successfully.
                </h3>
                <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">
                  Your report has been received for verification by the meteorological response desk.
                </p>
              </div>

              {/* Reference Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-700 text-xs font-mono">
                <span className="text-slate-400">Ref:</span>
                <span className="font-bold text-slate-900">{submittedReport.referenceCode}</span>
                <span className="text-slate-300">•</span>
                <span className="text-slate-500">{submittedReport.submittedAt}</span>
              </div>

              {/* Submission Details Summary Card */}
              <div className="text-left bg-slate-50 rounded-xl p-4 border border-slate-200 text-xs space-y-2.5">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200/80">
                  <span className="text-slate-500 font-medium">Event Type</span>
                  <span className="font-bold text-slate-900 flex items-center gap-1.5">
                    <span>{submittedReport.eventIcon}</span>
                    <span>{submittedReport.eventLabel}</span>
                  </span>
                </div>

                <div className="flex items-start justify-between pb-2 border-b border-slate-200/80 gap-4">
                  <span className="text-slate-500 font-medium">Location</span>
                  <div className="text-right">
                    {submittedReport.manualLocation && (
                      <div className="font-bold text-slate-900">{submittedReport.manualLocation}</div>
                    )}
                    {submittedReport.coords && (
                      <div className="text-[11px] font-mono text-emerald-700">
                        GPS: {submittedReport.coords.lat}°, {submittedReport.coords.lng}°
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between pb-2 border-b border-slate-200/80">
                  <span className="text-slate-500 font-medium">Observed At</span>
                  <span className="font-bold text-slate-900 font-mono">
                    {submittedReport.datetime.replace('T', ' ')}
                  </span>
                </div>

                <div className="flex items-start justify-between pb-2 border-b border-slate-200/80 gap-4">
                  <span className="text-slate-500 font-medium">Observation</span>
                  <span className="font-medium text-slate-800 text-right max-w-[280px] break-words">
                    {submittedReport.description}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Photo Attached</span>
                  <span className="font-bold text-slate-900">
                    {submittedReport.hasPhoto ? `✓ Yes (${submittedReport.photoName})` : 'None'}
                  </span>
                </div>
              </div>

              {/* Notice Banner */}
              <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200 text-blue-900 text-[11px] text-left leading-relaxed">
                <strong>Demo Mode:</strong> This report is held in client session memory for demonstration. The report has been acknowledged for verification and will not appear in the Live Events feed.
              </div>

              {/* Actions */}
              <div className="pt-2 flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  Submit Another Report
                </button>
                <button
                  type="button"
                  onClick={handleClose}
                  id="done-citizen-report-btn"
                  className="px-6 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white shadow-sm transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          ) : (
            /* Active Form */
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              {/* Event Type */}
              <div>
                <label htmlFor="modal-event-type" className="block text-xs font-bold text-slate-800 mb-1">
                  Event Type <span className="text-rose-500">*</span>
                </label>
                <select
                  id="modal-event-type"
                  value={eventType}
                  onChange={(e) => {
                    setEventType(e.target.value)
                    if (errors.eventType) {
                      setErrors((prev) => {
                        const next = { ...prev }
                        delete next.eventType
                        return next
                      })
                    }
                  }}
                  className={`w-full h-9.5 px-3 py-1.5 text-xs font-medium rounded-xl border bg-white cursor-pointer transition-colors focus:outline-none focus:ring-2 ${
                    errors.eventType
                      ? 'border-rose-400 ring-rose-200 text-slate-900'
                      : 'border-slate-300 focus:border-blue-500 focus:ring-blue-100 text-slate-800'
                  }`}
                >
                  <option value="">Select weather event type...</option>
                  {EVENT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.icon} {opt.label} — {opt.hint}
                    </option>
                  ))}
                </select>
                {errors.eventType && (
                  <p className="mt-1 text-[11px] text-rose-600 font-medium">
                    ⚠ {errors.eventType}
                  </p>
                )}
              </div>

              {/* Description */}
              <div>
                <label htmlFor="modal-description" className="block text-xs font-bold text-slate-800 mb-1">
                  Description <span className="text-rose-500">*</span>
                </label>
                <textarea
                  id="modal-description"
                  rows={3}
                  value={description}
                  onChange={(e) => {
                    setDescription(e.target.value)
                    if (errors.description) {
                      setErrors((prev) => {
                        const next = { ...prev }
                        delete next.description
                        return next
                      })
                    }
                  }}
                  placeholder="Briefly describe what you observed (e.g. sudden cloudburst, heavy street waterlogging, fallen trees, wind speed)..."
                  className={`w-full p-2.5 text-xs font-medium rounded-xl border bg-white transition-colors focus:outline-none focus:ring-2 resize-y min-h-[72px] ${
                    errors.description
                      ? 'border-rose-400 ring-rose-200 text-slate-900'
                      : 'border-slate-300 focus:border-blue-500 focus:ring-blue-100 text-slate-800'
                  }`}
                />
                <div className="flex justify-between items-center mt-1">
                  {errors.description ? (
                    <p className="text-[11px] text-rose-600 font-medium">
                      ⚠ {errors.description}
                    </p>
                  ) : (
                    <p className="text-[11px] text-slate-400">
                      Include observations on intensity, water accumulation, or hazards.
                    </p>
                  )}
                  <span className="text-[10px] font-mono text-slate-400 ml-auto">
                    {description.length} chars
                  </span>
                </div>
              </div>

              {/* Location (Manual + Geolocation) */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label htmlFor="modal-location" className="block text-xs font-bold text-slate-800">
                    Location <span className="text-rose-500">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={handleUseMyLocation}
                    disabled={geoStatus === 'locating'}
                    id="use-my-location-btn"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition-colors cursor-pointer disabled:opacity-60"
                  >
                    {geoStatus === 'locating' ? (
                      <>
                        <svg className="w-3 h-3 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span>Locating...</span>
                      </>
                    ) : (
                      <>
                        <span>📍</span>
                        <span>Use My Location</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Geolocation Feedback Message */}
                {geoStatus === 'success' && coords && (
                  <div className="mb-2 p-2 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between animate-in fade-in-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-600 font-bold">✓</span>
                      <span className="font-semibold">Location captured</span>
                      <span className="text-[11px] text-emerald-700 font-mono">
                        ({coords.lat.toFixed(4)}°, {coords.lng.toFixed(4)}°)
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setCoords(null)
                        setGeoStatus('idle')
                      }}
                      className="text-emerald-700 hover:text-emerald-900 text-[11px] underline font-medium"
                      title="Clear GPS location"
                    >
                      Clear
                    </button>
                  </div>
                )}

                {geoStatus === 'error' && (
                  <div className="mb-2 p-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between animate-in fade-in-0">
                    <div className="flex items-center gap-1.5">
                      <span>ℹ</span>
                      <span className="text-[11px] leading-tight">
                        {geoError || 'Unable to access your location. You can enter the location manually.'}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setGeoStatus('idle')}
                      className="text-amber-700 hover:text-amber-900 text-xs font-semibold ml-2"
                    >
                      ✕
                    </button>
                  </div>
                )}

                {/* Manual Address Input */}
                <input
                  id="modal-location"
                  type="text"
                  value={manualLocation}
                  onChange={(e) => {
                    setManualLocation(e.target.value)
                    if (errors.location) {
                      setErrors((prev) => {
                        const next = { ...prev }
                        delete next.location
                        return next
                      })
                    }
                  }}
                  placeholder="Address, area, landmark, or city (e.g., Dadar Circle, Mumbai)"
                  className={`w-full h-9.5 px-3 text-xs font-medium rounded-xl border bg-white transition-colors focus:outline-none focus:ring-2 ${
                    errors.location
                      ? 'border-rose-400 ring-rose-200 text-slate-900'
                      : 'border-slate-300 focus:border-blue-500 focus:ring-blue-100 text-slate-800'
                  }`}
                />
                {errors.location ? (
                  <p className="mt-1 text-[11px] text-rose-600 font-medium">
                    ⚠ {errors.location}
                  </p>
                ) : (
                  <p className="mt-1 text-[11px] text-slate-400">
                    Enter manual address, click 'Use My Location', or provide both.
                  </p>
                )}
              </div>

              {/* Date & Time */}
              <div>
                <label htmlFor="modal-datetime" className="block text-xs font-bold text-slate-800 mb-1">
                  Date / Time <span className="text-rose-500">*</span>
                </label>
                <input
                  id="modal-datetime"
                  type="datetime-local"
                  value={datetime}
                  onChange={(e) => {
                    setDatetime(e.target.value)
                    if (errors.datetime) {
                      setErrors((prev) => {
                        const next = { ...prev }
                        delete next.datetime
                        return next
                      })
                    }
                  }}
                  className={`w-full h-9.5 px-3 text-xs font-medium rounded-xl border bg-white transition-colors focus:outline-none focus:ring-2 ${
                    errors.datetime
                      ? 'border-rose-400 ring-rose-200 text-slate-900'
                      : 'border-slate-300 focus:border-blue-500 focus:ring-blue-100 text-slate-800'
                  }`}
                />
                {errors.datetime && (
                  <p className="mt-1 text-[11px] text-rose-600 font-medium">
                    ⚠ {errors.datetime}
                  </p>
                )}
              </div>

              {/* Photo Upload (Optional, Client-side only) */}
              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">
                  Photo <span className="text-slate-400 font-normal">(Optional)</span>
                </label>

                {!imagePreviewUrl ? (
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-xl p-3.5 text-center cursor-pointer bg-slate-50/50 hover:bg-blue-50/30 transition-all group"
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleImageChange}
                      className="hidden"
                    />
                    <div className="flex items-center justify-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-500 group-hover:text-blue-600 shadow-2xs">
                        📷
                      </div>
                      <div className="text-left">
                        <div className="text-xs font-semibold text-slate-700 group-hover:text-blue-600">
                          Click to select a photo from your device
                        </div>
                        <div className="text-[10px] text-slate-400">
                          PNG, JPG, WebP up to 10MB • Handled entirely in browser memory
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-slate-200 p-2.5 bg-white flex items-center gap-3">
                    <img
                      src={imagePreviewUrl}
                      alt="Selected photo preview"
                      className="w-14 h-14 object-cover rounded-lg border border-slate-200 shadow-2xs flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-slate-800 truncate">
                          {imageFile?.name}
                        </span>
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 flex-shrink-0">
                          PREVIEW
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        Size: {imageFile?.size} • Client-side only
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleRemoveImage}
                      className="px-2.5 py-1 text-xs text-rose-600 border border-rose-200 rounded-lg hover:bg-rose-50 font-medium transition-colors"
                      title="Remove image"
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

              {/* Reporter Info (Optional) */}
              <div className="pt-2 border-t border-slate-100">
                <div className="text-[11px] font-bold text-slate-600 mb-2">
                  Reporter Information <span className="text-slate-400 font-normal">(Optional)</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="modal-reporter-name" className="block text-[11px] text-slate-500 mb-0.5">
                      Your Name
                    </label>
                    <input
                      id="modal-reporter-name"
                      type="text"
                      value={reporterName}
                      onChange={(e) => setReporterName(e.target.value)}
                      placeholder="e.g. Rajesh Sharma"
                      className="w-full h-8.5 px-2.5 text-xs font-medium rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:border-blue-500 focus:ring-blue-100 text-slate-800"
                    />
                  </div>

                  <div>
                    <label htmlFor="modal-reporter-contact" className="block text-[11px] text-slate-500 mb-0.5">
                      Phone / Email
                    </label>
                    <input
                      id="modal-reporter-contact"
                      type="text"
                      value={reporterContact}
                      onChange={(e) => setReporterContact(e.target.value)}
                      placeholder="e.g. +91 98765 43210"
                      className="w-full h-8.5 px-2.5 text-xs font-medium rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:border-blue-500 focus:ring-blue-100 text-slate-800"
                    />
                  </div>
                </div>
                <p className="text-[10px] text-slate-400 mt-1 italic">
                  Personal information is purely optional. Reports can be submitted anonymously.
                </p>
              </div>

              {/* Form Actions */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-800 font-semibold transition-colors"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  id="submit-citizen-report-btn"
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white shadow-sm flex items-center gap-2 transition-all disabled:opacity-60 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span>Submitting Report...</span>
                    </>
                  ) : (
                    <>
                      <span>Submit Report</span>
                      <span>→</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
