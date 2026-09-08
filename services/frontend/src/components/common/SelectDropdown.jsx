import React, { useState, useRef, useEffect, useMemo } from 'react'

/**
 * Universal SaaS Premium Dropdown Component
 * Features:
 * - Clean white foundation with subtle border and focus ring
 * - Icon/logo + Title + Subtitle + Status Badge + Checkmark (✓)
 * - Search filter when options length > 5 or searchable=true
 * - Full keyboard navigation: ArrowUp, ArrowDown, Enter, Escape
 * - Click outside to close
 * - Compact and standard size variants
 */
export default function SelectDropdown({
  options = [],
  value,
  onChange,
  placeholder = 'Select option...',
  label,
  icon,
  className = '',
  compact = false,
  searchable = false,
  disabled = false,
  error = false,
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const containerRef = useRef(null)
  const listRef = useRef(null)

  // Normalize options to uniform format: { value, label, icon, subtitle, status, statusColor, disabled }
  const normalizedOptions = useMemo(() => {
    return options.map((opt) => {
      if (typeof opt === 'string' || typeof opt === 'number') {
        return { value: opt, label: String(opt), icon: null, subtitle: null, status: null }
      }
      return {
        value: opt.value !== undefined ? opt.value : opt.id,
        label: opt.label !== undefined ? opt.label : opt.name || String(opt.value),
        icon: opt.icon || null,
        subtitle: opt.subtitle || opt.desc || opt.state || null,
        status: opt.status || null,
        statusColor: opt.statusColor || null,
        disabled: Boolean(opt.disabled),
      }
    })
  }, [options])

  // Current selected option
  const selectedOption = useMemo(() => {
    return normalizedOptions.find((o) => o.value === value || (value === '' && o.value === '')) || null
  }, [normalizedOptions, value])

  // Filtered options based on search
  const filteredOptions = useMemo(() => {
    if (!search.trim()) return normalizedOptions
    const term = search.toLowerCase()
    return normalizedOptions.filter((o) => {
      return (
        o.label.toLowerCase().includes(term) ||
        (o.subtitle && o.subtitle.toLowerCase().includes(term))
      )
    })
  }, [normalizedOptions, search])

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (disabled) return

    if (!isOpen) {
      if (e.key === 'Enter' || e.key === 'ArrowDown' || e.key === ' ') {
        e.preventDefault()
        setIsOpen(true)
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex((prev) => (prev < filteredOptions.length - 1 ? prev + 1 : 0))
        break
      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : filteredOptions.length - 1))
        break
      case 'Enter':
        e.preventDefault()
        if (highlightedIndex >= 0 && highlightedIndex < filteredOptions.length) {
          const opt = filteredOptions[highlightedIndex]
          if (!opt.disabled) {
            onChange(opt.value)
            setIsOpen(false)
            setSearch('')
          }
        }
        break
      case 'Escape':
        e.preventDefault()
        setIsOpen(false)
        setSearch('')
        break
      default:
        break
    }
  }

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[data-dropdown-item]')
      if (items[highlightedIndex]) {
        items[highlightedIndex].scrollIntoView({ block: 'nearest' })
      }
    }
  }, [highlightedIndex, isOpen])

  const shouldShowSearch = searchable || normalizedOptions.length > 7

  return (
    <div
      ref={containerRef}
      className={`relative select-none ${className}`}
      onKeyDown={handleKeyDown}
    >
      {/* Trigger Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => {
          if (!disabled) {
            setIsOpen(!isOpen)
            setHighlightedIndex(-1)
          }
        }}
        className={`w-full flex items-center justify-between gap-2 bg-white border rounded-xl text-left transition-all duration-150 shadow-2xs ${
          compact ? 'h-8 px-2.5 text-xs' : 'h-9 px-3 text-xs'
        } ${
          error
            ? 'border-rose-400 ring-2 ring-rose-100'
            : isOpen
            ? 'border-brand-blue-500 ring-2 ring-brand-blue-500/10'
            : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/60'
        } ${disabled ? 'opacity-60 cursor-not-allowed bg-slate-50' : 'cursor-pointer'}`}
      >
        <div className="flex items-center gap-2 min-w-0 truncate">
          {icon && <span className="text-slate-500 flex-shrink-0">{icon}</span>}
          {label && (
            <span className="text-slate-400 font-semibold flex-shrink-0">
              {label}:
            </span>
          )}

          {selectedOption ? (
            <div className="flex items-center gap-1.5 min-w-0 truncate">
              {selectedOption.icon && (
                <span className="flex-shrink-0 text-sm">
                  {typeof selectedOption.icon === 'string' ? (
                    selectedOption.icon
                  ) : (
                    selectedOption.icon
                  )}
                </span>
              )}
              <span className="font-semibold text-slate-800 truncate">
                {selectedOption.label}
              </span>
              {selectedOption.subtitle && (
                <span className="text-[10px] text-slate-400 font-normal truncate hidden sm:inline">
                  ({selectedOption.subtitle})
                </span>
              )}
            </div>
          ) : (
            <span className="text-slate-400 font-medium truncate">{placeholder}</span>
          )}
        </div>

        {/* Chevron Icon */}
        <div className="flex items-center gap-1 flex-shrink-0 ml-1">
          <svg
            className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${
              isOpen ? 'rotate-180 text-brand-blue-600' : ''
            }`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </button>

      {/* Popup Menu */}
      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-slate-200 rounded-2xl shadow-dropdown z-50 overflow-hidden min-w-[200px] max-h-[320px] flex flex-col animate-in fade-in-0 zoom-in-95 duration-100">
          {/* Optional Search Input */}
          {shouldShowSearch && (
            <div className="p-2 border-b border-slate-100 bg-slate-50/80 flex-shrink-0">
              <div className="relative">
                <input
                  type="text"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value)
                    setHighlightedIndex(0)
                  }}
                  placeholder="Filter options..."
                  className="w-full h-7 pl-7 pr-6 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-brand-blue-500 shadow-2xs"
                  autoFocus
                />
                <span className="absolute left-2 top-1.5 text-[11px] text-slate-400">🔍</span>
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch('')}
                    className="absolute right-2 top-1.5 text-xs text-slate-400 hover:text-slate-700"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Option List */}
          <div ref={listRef} className="overflow-y-auto p-1.5 space-y-0.5 scrollbar-thin">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-center text-xs text-slate-400">
                No matching options
              </div>
            ) : (
              filteredOptions.map((opt, idx) => {
                const isSelected = selectedOption?.value === opt.value
                const isHighlighted = highlightedIndex === idx

                return (
                  <div
                    key={String(opt.value)}
                    data-dropdown-item
                    onClick={() => {
                      if (!opt.disabled) {
                        onChange(opt.value)
                        setIsOpen(false)
                        setSearch('')
                      }
                    }}
                    onMouseEnter={() => setHighlightedIndex(idx)}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs cursor-pointer transition-all ${
                      opt.disabled
                        ? 'opacity-40 cursor-not-allowed text-slate-400'
                        : isSelected
                        ? 'bg-brand-blue-50 text-brand-blue-900 font-bold border border-brand-blue-100'
                        : isHighlighted
                        ? 'bg-slate-50 text-slate-900 border border-transparent'
                        : 'text-slate-700 hover:bg-slate-50 border border-transparent'
                    }`}
                  >
                    {/* Option Details: Icon + Label + Subtitle */}
                    <div className="flex items-center gap-2 min-w-0 truncate">
                      {opt.icon && (
                        <span className="flex-shrink-0 text-sm">{opt.icon}</span>
                      )}
                      <div className="truncate min-w-0">
                        <div className="truncate font-medium">{opt.label}</div>
                        {opt.subtitle && (
                          <div className="text-[10px] text-slate-400 truncate">
                            {opt.subtitle}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Status Badge & Checkmark */}
                    <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                      {opt.status && (
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase tracking-wider ${
                            opt.statusColor || 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {opt.status}
                        </span>
                      )}
                      {isSelected && (
                        <span className="text-brand-blue-600 font-bold text-xs ml-1">
                          ✓
                        </span>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
